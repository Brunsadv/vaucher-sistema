"""
Rotas de Insights (Blog, Artigos, Jurisprudência, Alertas)
Criado em 25/01/2026
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from datetime import datetime
from typing import Optional, List
import os
import uuid
import json

from modules.config import logger, UPLOADS_DIR
from modules.auth import verificar_admin
from modules.security import validar_arquivo, validar_mime_type, sanitizar_nome_arquivo

router = APIRouter(prefix="/api", tags=["Insights"])

# ============================================
# CONFIGURAÇÕES
# ============================================

INSIGHTS_UPLOAD_DIR = os.path.join(UPLOADS_DIR, "insights")
os.makedirs(INSIGHTS_UPLOAD_DIR, exist_ok=True)

# Categorias válidas
CATEGORIAS_VALIDAS = ["artigo", "jurisprudencia", "alerta", "noticia"]

# ============================================
# FUNÇÕES AUXILIARES (serão movidas para database.py)
# ============================================

def get_db():
    """Importa conexão do módulo database."""
    from modules.database import get_db as db_get
    return db_get()

def gerar_slug(titulo: str) -> str:
    """Gera slug a partir do título."""
    import re
    slug = titulo.lower()
    slug = re.sub(r'[àáâãäå]', 'a', slug)
    slug = re.sub(r'[èéêë]', 'e', slug)
    slug = re.sub(r'[ìíîï]', 'i', slug)
    slug = re.sub(r'[òóôõö]', 'o', slug)
    slug = re.sub(r'[ùúûü]', 'u', slug)
    slug = re.sub(r'[ç]', 'c', slug)
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug[:100]

# ============================================
# ROTAS ADMIN - CRUD DE INSIGHTS
# ============================================

@router.get("/admin/insights")
async def listar_insights_admin(
    categoria: Optional[str] = None,
    status: Optional[str] = None,
    limite: int = 50,
    offset: int = 0,
    admin=Depends(verificar_admin)
):
    """Lista todos os insights para o admin."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Construir query com filtros
        query = "SELECT * FROM insights WHERE 1=1"
        params = []

        if categoria:
            query += " AND categoria = %s"
            params.append(categoria)

        if status:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY destaque DESC, data_publicacao DESC LIMIT %s OFFSET %s"
        params.extend([limite, offset])

        cur.execute(query, params)
        insights = cur.fetchall()

        # Contar total
        count_query = "SELECT COUNT(*) FROM insights WHERE 1=1"
        count_params = []
        if categoria:
            count_query += " AND categoria = %s"
            count_params.append(categoria)
        if status:
            count_query += " AND status = %s"
            count_params.append(status)

        cur.execute(count_query, count_params)
        total = cur.fetchone()['count']

        cur.close()

        return {
            "sucesso": True,
            "insights": [dict(i) for i in insights],
            "total": total,
            "limite": limite,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Erro ao listar insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/admin/insights")
async def criar_insight(
    titulo: str = Form(...),
    titulo_en: Optional[str] = Form(None),
    titulo_es: Optional[str] = Form(None),
    categoria: str = Form(...),
    resumo: str = Form(...),
    resumo_en: Optional[str] = Form(None),
    resumo_es: Optional[str] = Form(None),
    conteudo: str = Form(...),
    conteudo_en: Optional[str] = Form(None),
    conteudo_es: Optional[str] = Form(None),
    fonte: Optional[str] = Form(None),
    fonte_url: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    destaque: str = Form("false"),
    status: str = Form("rascunho"),
    imagem: Optional[UploadFile] = File(None),
    admin=Depends(verificar_admin)
):
    """Cria um novo insight."""

    # Converter destaque de string para boolean
    destaque_bool = destaque.lower() in ("true", "1", "yes", "sim")

    # Validar categoria
    if categoria not in CATEGORIAS_VALIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria inválida. Use: {', '.join(CATEGORIAS_VALIDAS)}"
        )

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        # Processar imagem se enviada
        imagem_path = None
        if imagem and imagem.filename:
            # Validar extensão e tamanho
            is_valid, error = validar_arquivo(imagem.filename, imagem.size or 0)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error)

            content = await imagem.read()

            # Validar tipo real do arquivo (magic bytes)
            valido_mime, erro_mime = validar_mime_type(content, imagem.filename)
            if not valido_mime:
                raise HTTPException(status_code=400, detail=f"Imagem rejeitada: {erro_mime}")

            # Salvar imagem
            ext = os.path.splitext(imagem.filename)[1]
            nome_arquivo = f"{uuid.uuid4().hex}{ext}"
            caminho_completo = os.path.join(INSIGHTS_UPLOAD_DIR, nome_arquivo)

            with open(caminho_completo, "wb") as f:
                f.write(content)

            imagem_path = f"insights/{nome_arquivo}"

        # Gerar ID e slug
        insight_id = f"INS-{uuid.uuid4().hex[:8].upper()}"
        slug = gerar_slug(titulo)

        # Processar tags
        tags_list = [t.strip() for t in tags.split(",")] if tags else []

        cur = conn.cursor()
        cur.execute("""
            INSERT INTO insights (
                id, slug, categoria,
                titulo, titulo_en, titulo_es,
                resumo, resumo_en, resumo_es,
                conteudo, conteudo_en, conteudo_es,
                fonte, fonte_url, imagem_path, tags,
                destaque, status, autor_id, autor_nome,
                criado_em, atualizado_em
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                NOW(), NOW()
            )
        """, (
            insight_id, slug, categoria,
            titulo, titulo_en, titulo_es,
            resumo, resumo_en, resumo_es,
            conteudo, conteudo_en, conteudo_es,
            fonte, fonte_url, imagem_path, json.dumps(tags_list),
            destaque_bool, status, admin.get('id'), admin.get('nome')
        ))

        conn.commit()
        cur.close()

        logger.info(f"Insight criado: {insight_id} por {admin.get('nome')}")

        return {
            "sucesso": True,
            "id": insight_id,
            "slug": slug,
            "mensagem": "Insight criado com sucesso"
        }
    except Exception as e:
        logger.error(f"Erro ao criar insight: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/admin/insights/{insight_id}")
async def obter_insight_admin(insight_id: str, admin=Depends(verificar_admin)):
    """Obtém um insight específico para edição."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("SELECT * FROM insights WHERE id = %s", (insight_id,))
        insight = cur.fetchone()
        cur.close()

        if not insight:
            raise HTTPException(status_code=404, detail="Insight não encontrado")

        return {"sucesso": True, "insight": dict(insight)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter insight: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.put("/admin/insights/{insight_id}")
async def atualizar_insight(
    insight_id: str,
    titulo: str = Form(...),
    titulo_en: Optional[str] = Form(None),
    titulo_es: Optional[str] = Form(None),
    categoria: str = Form(...),
    resumo: str = Form(...),
    resumo_en: Optional[str] = Form(None),
    resumo_es: Optional[str] = Form(None),
    conteudo: str = Form(...),
    conteudo_en: Optional[str] = Form(None),
    conteudo_es: Optional[str] = Form(None),
    fonte: Optional[str] = Form(None),
    fonte_url: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    destaque: str = Form("false"),
    status: str = Form("rascunho"),
    imagem: Optional[UploadFile] = File(None),
    admin=Depends(verificar_admin)
):
    """Atualiza um insight existente."""

    # Converter destaque de string para boolean
    destaque_bool = destaque.lower() in ("true", "1", "yes", "sim")

    if categoria not in CATEGORIAS_VALIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria inválida. Use: {', '.join(CATEGORIAS_VALIDAS)}"
        )

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar se existe
        cur.execute("SELECT * FROM insights WHERE id = %s", (insight_id,))
        insight_atual = cur.fetchone()

        if not insight_atual:
            raise HTTPException(status_code=404, detail="Insight não encontrado")

        # Processar nova imagem se enviada
        imagem_path = insight_atual.get('imagem_path')
        if imagem and imagem.filename:
            is_valid, error = validar_arquivo(imagem.filename, imagem.size or 0)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error)

            content = await imagem.read()

            # Validar tipo real do arquivo (magic bytes)
            valido_mime, erro_mime = validar_mime_type(content, imagem.filename)
            if not valido_mime:
                raise HTTPException(status_code=400, detail=f"Imagem rejeitada: {erro_mime}")

            # Deletar imagem antiga
            if imagem_path:
                old_path = os.path.join(UPLOADS_DIR, imagem_path)
                if os.path.exists(old_path):
                    os.remove(old_path)

            # Salvar nova
            ext = os.path.splitext(imagem.filename)[1]
            nome_arquivo = f"{uuid.uuid4().hex}{ext}"
            caminho_completo = os.path.join(INSIGHTS_UPLOAD_DIR, nome_arquivo)

            with open(caminho_completo, "wb") as f:
                f.write(content)

            imagem_path = f"insights/{nome_arquivo}"

        # Atualizar slug se título mudou
        slug = insight_atual.get('slug')
        if titulo != insight_atual.get('titulo'):
            slug = gerar_slug(titulo)

        # Processar tags
        tags_list = [t.strip() for t in tags.split(",")] if tags else []

        # Verificar se está publicando pela primeira vez
        data_publicacao = insight_atual.get('data_publicacao')
        if status == 'publicado' and not data_publicacao:
            data_publicacao = datetime.now()

        cur.execute("""
            UPDATE insights SET
                slug = %s, categoria = %s,
                titulo = %s, titulo_en = %s, titulo_es = %s,
                resumo = %s, resumo_en = %s, resumo_es = %s,
                conteudo = %s, conteudo_en = %s, conteudo_es = %s,
                fonte = %s, fonte_url = %s, imagem_path = %s, tags = %s,
                destaque = %s, status = %s,
                data_publicacao = %s, atualizado_em = NOW()
            WHERE id = %s
        """, (
            slug, categoria,
            titulo, titulo_en, titulo_es,
            resumo, resumo_en, resumo_es,
            conteudo, conteudo_en, conteudo_es,
            fonte, fonte_url, imagem_path, json.dumps(tags_list),
            destaque_bool, status,
            data_publicacao, insight_id
        ))

        conn.commit()
        cur.close()

        logger.info(f"Insight atualizado: {insight_id} por {admin.get('nome')}")

        return {
            "sucesso": True,
            "mensagem": "Insight atualizado com sucesso"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar insight: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.delete("/admin/insights/{insight_id}")
async def deletar_insight(insight_id: str, admin=Depends(verificar_admin)):
    """Deleta um insight."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Buscar para deletar imagem
        cur.execute("SELECT imagem_path FROM insights WHERE id = %s", (insight_id,))
        insight = cur.fetchone()

        if not insight:
            raise HTTPException(status_code=404, detail="Insight não encontrado")

        # Deletar imagem se existir
        if insight.get('imagem_path'):
            img_path = os.path.join(UPLOADS_DIR, insight['imagem_path'])
            if os.path.exists(img_path):
                os.remove(img_path)

        # Deletar do banco
        cur.execute("DELETE FROM insights WHERE id = %s", (insight_id,))
        conn.commit()
        cur.close()

        # Registrar auditoria
        from modules.database import registrar_auditoria
        registrar_auditoria(
            acao="DELETE",
            tabela="insights",
            registro_id=insight_id,
            usuario_id=admin.get("id"),
            usuario_email=admin.get("email"),
            detalhes=f"Insight {insight_id} deletado"
        )

        logger.info(f"Insight deletado: {insight_id} por {admin.get('nome')}")

        return {"sucesso": True, "mensagem": "Insight deletado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar insight: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/admin/insights/{insight_id}/publicar")
async def publicar_insight(insight_id: str, admin=Depends(verificar_admin)):
    """Publica um insight (muda status para publicado)."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE insights
            SET status = 'publicado',
                data_publicacao = COALESCE(data_publicacao, NOW()),
                atualizado_em = NOW()
            WHERE id = %s
        """, (insight_id,))

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Insight não encontrado")

        conn.commit()
        cur.close()

        return {"sucesso": True, "mensagem": "Insight publicado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao publicar insight: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.post("/admin/insights/{insight_id}/despublicar")
async def despublicar_insight(insight_id: str, admin=Depends(verificar_admin)):
    """Despublica um insight (volta para rascunho)."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE insights
            SET status = 'rascunho', atualizado_em = NOW()
            WHERE id = %s
        """, (insight_id,))

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Insight não encontrado")

        conn.commit()
        cur.close()

        return {"sucesso": True, "mensagem": "Insight despublicado"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao despublicar insight: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


# ============================================
# ROTAS PÚBLICAS - PARA A LANDING PAGE
# ============================================

@router.get("/public/insights")
async def listar_insights_publico(
    categoria: Optional[str] = None,
    tag: Optional[str] = None,
    limite: int = 12,
    offset: int = 0,
    lang: str = "pt"
):
    """Lista insights publicados para a landing page."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Apenas publicados
        query = "SELECT * FROM insights WHERE status = 'publicado'"
        params = []

        if categoria:
            query += " AND categoria = %s"
            params.append(categoria)

        if tag:
            query += " AND tags::text ILIKE %s"
            params.append(f'%"{tag}"%')

        query += " ORDER BY destaque DESC, data_publicacao DESC LIMIT %s OFFSET %s"
        params.extend([limite, offset])

        cur.execute(query, params)
        insights_raw = cur.fetchall()

        # Formatar para o idioma solicitado
        insights = []
        for i in insights_raw:
            insight = {
                "id": i['id'],
                "slug": i['slug'],
                "categoria": i['categoria'],
                "titulo": i.get(f'titulo_{lang}') or i['titulo'],
                "resumo": i.get(f'resumo_{lang}') or i['resumo'],
                "imagem_url": f"/api/public/insights/imagem/{i['imagem_path'].split('/')[-1]}" if i.get('imagem_path') else None,
                "fonte": i['fonte'],
                "fonte_url": i['fonte_url'],
                "tags": json.loads(i['tags']) if i.get('tags') else [],
                "destaque": i['destaque'],
                "data_publicacao": i['data_publicacao'].isoformat() if i.get('data_publicacao') else None
            }
            insights.append(insight)

        # Contar total
        count_query = "SELECT COUNT(*) FROM insights WHERE status = 'publicado'"
        count_params = []
        if categoria:
            count_query += " AND categoria = %s"
            count_params.append(categoria)
        if tag:
            count_query += " AND tags::text ILIKE %s"
            count_params.append(f'%"{tag}"%')

        cur.execute(count_query, count_params)
        total = cur.fetchone()['count']

        cur.close()

        return {
            "insights": insights,
            "total": total,
            "paginas": (total + limite - 1) // limite
        }
    except Exception as e:
        logger.error(f"Erro ao listar insights públicos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/public/insights/destaque")
async def listar_insights_destaque(lang: str = "pt", limite: int = 3):
    """Lista insights em destaque para a landing page."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT * FROM insights
            WHERE status = 'publicado' AND destaque = true
            ORDER BY data_publicacao DESC
            LIMIT %s
        """, (limite,))

        insights_raw = cur.fetchall()
        cur.close()

        insights = []
        for i in insights_raw:
            insight = {
                "id": i['id'],
                "slug": i['slug'],
                "categoria": i['categoria'],
                "titulo": i.get(f'titulo_{lang}') or i['titulo'],
                "resumo": i.get(f'resumo_{lang}') or i['resumo'],
                "imagem_url": f"/api/public/insights/imagem/{i['imagem_path'].split('/')[-1]}" if i.get('imagem_path') else None,
                "data_publicacao": i['data_publicacao'].isoformat() if i.get('data_publicacao') else None
            }
            insights.append(insight)

        return {"insights": insights}
    except Exception as e:
        logger.error(f"Erro ao listar destaques: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/public/insights/alertas")
async def listar_alertas_ativos(lang: str = "pt"):
    """Lista alertas de golpe ativos para exibição na landing."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT * FROM insights
            WHERE status = 'publicado' AND categoria = 'alerta'
            ORDER BY data_publicacao DESC
            LIMIT 5
        """)

        alertas_raw = cur.fetchall()
        cur.close()

        alertas = []
        for a in alertas_raw:
            alerta = {
                "id": a['id'],
                "titulo": a.get(f'titulo_{lang}') or a['titulo'],
                "resumo": a.get(f'resumo_{lang}') or a['resumo'],
                "data_publicacao": a['data_publicacao'].isoformat() if a.get('data_publicacao') else None
            }
            alertas.append(alerta)

        return {"alertas": alertas}
    except Exception as e:
        logger.error(f"Erro ao listar alertas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/public/insights/{slug}")
async def obter_insight_publico(slug: str, lang: str = "pt"):
    """Obtém um insight específico pelo slug."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT * FROM insights
            WHERE (slug = %s OR id = %s) AND status = 'publicado'
        """, (slug, slug))

        i = cur.fetchone()
        cur.close()

        if not i:
            raise HTTPException(status_code=404, detail="Insight não encontrado")

        insight = {
            "id": i['id'],
            "slug": i['slug'],
            "categoria": i['categoria'],
            "titulo": i.get(f'titulo_{lang}') or i['titulo'],
            "resumo": i.get(f'resumo_{lang}') or i['resumo'],
            "conteudo": i.get(f'conteudo_{lang}') or i['conteudo'],
            "imagem_url": f"/api/public/insights/imagem/{i['imagem_path'].split('/')[-1]}" if i.get('imagem_path') else None,
            "fonte": i['fonte'],
            "fonte_url": i['fonte_url'],
            "tags": json.loads(i['tags']) if i.get('tags') else [],
            "autor_nome": i['autor_nome'],
            "data_publicacao": i['data_publicacao'].isoformat() if i.get('data_publicacao') else None
        }

        return {"insight": insight}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter insight: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/public/insights/imagem/{filename}")
async def servir_imagem_insight(filename: str):
    """Serve imagens dos insights."""
    file_path = os.path.join(INSIGHTS_UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Imagem não encontrada")

    return FileResponse(file_path)


# ============================================
# ESTATÍSTICAS
# ============================================

@router.get("/admin/insights/estatisticas")
async def estatisticas_insights(admin=Depends(verificar_admin)):
    """Retorna estatísticas dos insights."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        from psycopg2.extras import RealDictCursor
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Total por status
        cur.execute("""
            SELECT status, COUNT(*) as total
            FROM insights GROUP BY status
        """)
        por_status = {r['status']: r['total'] for r in cur.fetchall()}

        # Total por categoria
        cur.execute("""
            SELECT categoria, COUNT(*) as total
            FROM insights GROUP BY categoria
        """)
        por_categoria = {r['categoria']: r['total'] for r in cur.fetchall()}

        # Total geral
        cur.execute("SELECT COUNT(*) as total FROM insights")
        total = cur.fetchone()['total']

        cur.close()

        return {
            "total": total,
            "por_status": por_status,
            "por_categoria": por_categoria
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
