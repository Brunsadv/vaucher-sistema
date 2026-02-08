"""
Rotas de Newsletter
Criado em 08/02/2026
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
import re

from modules.config import logger
from modules.database import get_db
from modules.auth import verificar_admin

router = APIRouter(prefix="/api", tags=["Newsletter"])


# ============================================
# MODELOS
# ============================================

class NewsletterInscricao(BaseModel):
    email: EmailStr
    nome: Optional[str] = None
    idioma: Optional[str] = "pt"


# ============================================
# ROTAS PUBLICAS
# ============================================

@router.post("/public/newsletter/inscrever")
async def inscrever_newsletter(dados: NewsletterInscricao, request: Request):
    """Inscreve um email na newsletter."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexao com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar se email ja existe
        cur.execute("SELECT id, ativo FROM newsletter_inscricoes WHERE email = %s", (dados.email.lower(),))
        existente = cur.fetchone()

        if existente:
            if existente['ativo']:
                return {"sucesso": True, "mensagem": "Email ja inscrito na newsletter"}
            else:
                # Reativar inscricao
                cur.execute("""
                    UPDATE newsletter_inscricoes
                    SET ativo = TRUE, atualizado_em = NOW(), cancelado_em = NULL
                    WHERE id = %s
                """, (existente['id'],))
                conn.commit()
                return {"sucesso": True, "mensagem": "Inscricao reativada com sucesso"}

        # Capturar IP e User-Agent
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500]

        # Inserir nova inscricao
        cur.execute("""
            INSERT INTO newsletter_inscricoes (email, nome, idioma, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            dados.email.lower(),
            dados.nome,
            dados.idioma or "pt",
            ip_address,
            user_agent
        ))

        novo_id = cur.fetchone()['id']
        conn.commit()
        cur.close()

        logger.info(f"Nova inscricao newsletter: {dados.email}")

        return {
            "sucesso": True,
            "mensagem": "Inscrito com sucesso na newsletter",
            "id": novo_id
        }

    except Exception as e:
        logger.error(f"Erro ao inscrever na newsletter: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar inscricao")
    finally:
        conn.close()


@router.post("/public/newsletter/cancelar")
async def cancelar_newsletter(email: str):
    """Cancela inscricao na newsletter."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexao com banco")

    try:
        cur = conn.cursor()

        cur.execute("""
            UPDATE newsletter_inscricoes
            SET ativo = FALSE, cancelado_em = NOW(), atualizado_em = NOW()
            WHERE email = %s AND ativo = TRUE
        """, (email.lower(),))

        if cur.rowcount == 0:
            return {"sucesso": False, "mensagem": "Email nao encontrado ou ja cancelado"}

        conn.commit()
        cur.close()

        logger.info(f"Cancelamento newsletter: {email}")

        return {"sucesso": True, "mensagem": "Inscricao cancelada com sucesso"}

    except Exception as e:
        logger.error(f"Erro ao cancelar newsletter: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar cancelamento")
    finally:
        conn.close()


# ============================================
# ROTAS ADMIN
# ============================================

@router.get("/admin/newsletter/inscricoes")
async def listar_inscricoes(
    admin=Depends(verificar_admin),
    ativo: Optional[bool] = None,
    limite: int = 50,
    offset: int = 0,
    busca: Optional[str] = None
):
    """Lista inscricoes da newsletter (admin)."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexao com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT * FROM newsletter_inscricoes WHERE 1=1"
        params = []

        if ativo is not None:
            query += " AND ativo = %s"
            params.append(ativo)

        if busca:
            query += " AND (email ILIKE %s OR nome ILIKE %s)"
            params.extend([f"%{busca}%", f"%{busca}%"])

        # Contar total
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cur.execute(count_query, params)
        total = cur.fetchone()['count']

        # Buscar com paginacao
        query += " ORDER BY criado_em DESC LIMIT %s OFFSET %s"
        params.extend([limite, offset])

        cur.execute(query, params)
        inscricoes = cur.fetchall()

        cur.close()

        # Formatar datas
        for i in inscricoes:
            if i.get('criado_em'):
                i['criado_em'] = i['criado_em'].isoformat()
            if i.get('atualizado_em'):
                i['atualizado_em'] = i['atualizado_em'].isoformat()
            if i.get('cancelado_em'):
                i['cancelado_em'] = i['cancelado_em'].isoformat()

        return {
            "inscricoes": inscricoes,
            "total": total,
            "pagina": (offset // limite) + 1,
            "paginas": (total + limite - 1) // limite
        }

    except Exception as e:
        logger.error(f"Erro ao listar inscricoes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/admin/newsletter/estatisticas")
async def estatisticas_newsletter(admin=Depends(verificar_admin)):
    """Retorna estatisticas da newsletter."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexao com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Total de inscritos ativos
        cur.execute("SELECT COUNT(*) as total FROM newsletter_inscricoes WHERE ativo = TRUE")
        ativos = cur.fetchone()['total']

        # Total de cancelados
        cur.execute("SELECT COUNT(*) as total FROM newsletter_inscricoes WHERE ativo = FALSE")
        cancelados = cur.fetchone()['total']

        # Inscricoes nos ultimos 30 dias
        cur.execute("""
            SELECT COUNT(*) as total FROM newsletter_inscricoes
            WHERE criado_em >= NOW() - INTERVAL '30 days'
        """)
        ultimos_30_dias = cur.fetchone()['total']

        # Por idioma
        cur.execute("""
            SELECT idioma, COUNT(*) as total
            FROM newsletter_inscricoes
            WHERE ativo = TRUE
            GROUP BY idioma
        """)
        por_idioma = {row['idioma']: row['total'] for row in cur.fetchall()}

        cur.close()

        return {
            "ativos": ativos,
            "cancelados": cancelados,
            "total": ativos + cancelados,
            "ultimos_30_dias": ultimos_30_dias,
            "por_idioma": por_idioma
        }

    except Exception as e:
        logger.error(f"Erro ao obter estatisticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/admin/newsletter/exportar")
async def exportar_newsletter(admin=Depends(verificar_admin), apenas_ativos: bool = True):
    """Exporta lista de emails da newsletter."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexao com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT email, nome, idioma, criado_em FROM newsletter_inscricoes"
        if apenas_ativos:
            query += " WHERE ativo = TRUE"
        query += " ORDER BY criado_em DESC"

        cur.execute(query)
        inscricoes = cur.fetchall()

        cur.close()

        # Formatar para CSV
        csv_lines = ["email,nome,idioma,data_inscricao"]
        for i in inscricoes:
            nome = (i.get('nome') or '').replace(',', ' ')
            data = i['criado_em'].strftime('%Y-%m-%d') if i.get('criado_em') else ''
            csv_lines.append(f"{i['email']},{nome},{i.get('idioma', 'pt')},{data}")

        return {
            "csv": "\n".join(csv_lines),
            "total": len(inscricoes)
        }

    except Exception as e:
        logger.error(f"Erro ao exportar newsletter: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.delete("/admin/newsletter/{inscricao_id}")
async def remover_inscricao(inscricao_id: int, admin=Depends(verificar_admin)):
    """Remove uma inscricao da newsletter (admin)."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexao com banco")

    try:
        cur = conn.cursor()

        cur.execute("DELETE FROM newsletter_inscricoes WHERE id = %s", (inscricao_id,))

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Inscricao nao encontrada")

        conn.commit()
        cur.close()

        return {"sucesso": True, "mensagem": "Inscricao removida"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover inscricao: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
