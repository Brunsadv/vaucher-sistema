"""
Rotas de Integração DataJud CNJ
Refatorado em 23/01/2026
"""

from fastapi import APIRouter, HTTPException, Depends
import httpx
from psycopg2.extras import RealDictCursor

import os
from modules.config import logger
from modules.database import get_db
from modules.prazos import processar_andamentos_para_prazos
from modules.auth import verificar_admin

router = APIRouter(prefix="/api/admin/datajud", tags=["DataJud CNJ"])

# ============================================
# CONFIGURAÇÕES DATAJUD
# ============================================

TRIBUNAIS_DATAJUD = {
    # Justiça Estadual (8)
    "8.01": "tjac", "8.02": "tjal", "8.03": "tjap", "8.04": "tjam", "8.05": "tjba",
    "8.06": "tjce", "8.07": "tjdft", "8.08": "tjes", "8.09": "tjgo", "8.10": "tjma",
    "8.11": "tjmt", "8.12": "tjms", "8.13": "tjmg", "8.14": "tjpa", "8.15": "tjpb",
    "8.16": "tjpr", "8.17": "tjpe", "8.18": "tjpi", "8.19": "tjrj", "8.20": "tjrn",
    "8.21": "tjrs", "8.22": "tjro", "8.23": "tjrr", "8.24": "tjsc", "8.25": "tjsp",
    "8.26": "tjsp", "8.27": "tjse", "8.28": "tjto",
    # Justiça Federal (4)
    "4.01": "trf1", "4.02": "trf2", "4.03": "trf3", "4.04": "trf4", "4.05": "trf5",
    # Justiça do Trabalho (5)
    "5.01": "trt1", "5.02": "trt2", "5.03": "trt3", "5.04": "trt4", "5.05": "trt5",
    "5.06": "trt6", "5.07": "trt7", "5.08": "trt8", "5.09": "trt9", "5.10": "trt10",
    "5.11": "trt11", "5.12": "trt12", "5.13": "trt13", "5.14": "trt14", "5.15": "trt15",
    "5.16": "trt16", "5.17": "trt17", "5.18": "trt18", "5.19": "trt19", "5.20": "trt20",
    "5.21": "trt21", "5.22": "trt22", "5.23": "trt23", "5.24": "trt24",
}

DATAJUD_API_KEY = os.getenv("DATAJUD_API_KEY", "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw==")
DATAJUD_BASE_URL = "https://api-publica.datajud.cnj.jus.br"


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def extrair_codigo_tribunal(numero_processo: str) -> str:
    """
    Extrai o código do tribunal do número do processo.
    Formato CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
    J = Justiça (posição 16), TR = Tribunal (posição 18-19)
    """
    numero_limpo = numero_processo.replace(" ", "")
    partes = numero_limpo.split(".")
    if len(partes) >= 4:
        justica = partes[2]
        tribunal = partes[3]
        return f"{justica}.{tribunal.zfill(2)}"
    return None


async def consultar_datajud(numero_processo: str) -> dict:
    """
    Consulta a API pública do DataJud do CNJ.
    Retorna dados do processo e movimentações.
    """
    codigo_tribunal = extrair_codigo_tribunal(numero_processo)
    if not codigo_tribunal:
        return {"erro": "Não foi possível identificar o tribunal pelo número do processo"}

    tribunal_alias = TRIBUNAIS_DATAJUD.get(codigo_tribunal)
    if not tribunal_alias:
        return {"erro": f"Tribunal não encontrado para código {codigo_tribunal}"}

    url = f"{DATAJUD_BASE_URL}/api_publica_{tribunal_alias}/_search"

    headers = {
        "Authorization": f"APIKey {DATAJUD_API_KEY}",
        "Content-Type": "application/json"
    }

    # Limpar número do processo (remover formatação CNJ)
    numero_limpo = numero_processo.replace("-", "").replace(".", "").replace(" ", "")

    body = {
        "query": {
            "match": {
                "numeroProcesso": numero_limpo
            }
        },
        "size": 1
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=body, headers=headers)

            if response.status_code != 200:
                logger.error(f"Erro DataJud: {response.status_code} - {response.text}")
                return {"erro": f"Erro na API DataJud: {response.status_code}"}

            data = response.json()
            hits = data.get("hits", {}).get("hits", [])

            if not hits:
                return {"erro": "Processo não encontrado no DataJud"}

            processo_cnj = hits[0].get("_source", {})
            return {
                "sucesso": True,
                "dados": processo_cnj,
                "tribunal": tribunal_alias.upper()
            }

    except Exception as e:
        logger.error(f"Erro ao consultar DataJud: {e}")
        return {"erro": f"Erro ao consultar DataJud: {str(e)}"}


# ============================================
# ROTAS
# ============================================

@router.get("/consultar/{numero_processo:path}")
async def consultar_processo_datajud(
    numero_processo: str,
    admin=Depends(verificar_admin)
):
    """
    Consulta um processo na API pública do DataJud do CNJ.
    """
    resultado = await consultar_datajud(numero_processo)

    if "erro" in resultado:
        raise HTTPException(status_code=400, detail=resultado["erro"])

    return resultado


@router.post("/atualizar-processo/{processo_id}")
async def atualizar_processo_datajud(
    processo_id: int,
    admin=Depends(verificar_admin)
):
    """
    Atualiza um processo com dados do DataJud do CNJ.
    """
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")

    cur = None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM processos WHERE id = %s", (processo_id,))
        processo = cur.fetchone()

        if not processo:
            raise HTTPException(status_code=404, detail="Processo não encontrado no sistema")

        numero_processo = processo["numero_processo"]
        resultado = await consultar_datajud(numero_processo)

        if "erro" in resultado:
            erro_msg = resultado["erro"]
            # Mensagem mais clara para o usuário
            if "não encontrado" in erro_msg.lower():
                erro_msg = f"Processo {numero_processo} não encontrado no DataJud. Verifique se o número está correto ou se o processo já foi indexado pelo CNJ."
            raise HTTPException(status_code=400, detail=erro_msg)

        dados_cnj = resultado["dados"]

        # Extrair dados relevantes
        classe = dados_cnj.get("classe", {}).get("nome", "")
        orgao = dados_cnj.get("orgaoJulgador", {}).get("nome", "")
        movimentos = dados_cnj.get("movimentos", [])

        # Atualizar processo
        updates = []
        params = []

        if classe and not processo.get("tipo_acao"):
            updates.append("tipo_acao = %s")
            params.append(classe)

        if orgao and not processo.get("vara_tribunal"):
            updates.append("vara_tribunal = %s")
            params.append(orgao)

        if movimentos:
            ultimo_movimento = movimentos[0] if movimentos else {}
            nome_movimento = ultimo_movimento.get("nome", "")
            if nome_movimento:
                updates.append("fase = %s")
                params.append(nome_movimento[:100])

        if updates:
            params.append(processo_id)
            cur.execute(f"""
                UPDATE processos SET {', '.join(updates)}
                WHERE id = %s
            """, params)

        # Adicionar movimentos como andamentos
        andamentos_adicionados = 0
        for movimento in movimentos[:20]:
            data_mov = movimento.get("dataHora", "")[:10]
            descricao = movimento.get("nome", "")
            complementos = movimento.get("complementosTabelados", [])

            if complementos:
                complemento_texto = ", ".join([c.get("nome", "") for c in complementos if c.get("nome")])
                if complemento_texto:
                    descricao = f"{descricao}: {complemento_texto}"

            if not data_mov or not descricao:
                continue

            cur.execute("""
                SELECT id FROM processo_andamentos
                WHERE processo_id = %s AND data = %s AND descricao = %s
            """, (processo_id, data_mov, descricao[:500]))

            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO processo_andamentos (processo_id, data, descricao, visivel_cliente)
                    VALUES (%s, %s, %s, %s)
                """, (processo_id, data_mov, descricao[:500], True))
                andamentos_adicionados += 1

        conn.commit()

        # Gerar prazos automáticos (após fechar conexão principal)
        prazos_resultado = processar_andamentos_para_prazos(processo_id)
        prazos_criados = prazos_resultado.get("prazos_criados", 0)

        return {
            "sucesso": True,
            "processo_atualizado": True,
            "andamentos_adicionados": andamentos_adicionados,
            "prazos_criados": prazos_criados,
            "tribunal": resultado.get("tribunal"),
            "mensagem": f"Processo atualizado com {andamentos_adicionados} andamentos e {prazos_criados} prazos do CNJ"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar processo do DataJud: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@router.post("/atualizar-todos")
async def atualizar_todos_processos_datajud(admin=Depends(verificar_admin)):
    """
    Atualiza todos os processos cadastrados com dados do DataJud.
    """
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, numero_processo FROM processos WHERE status = 'ativo'")
        processos = cur.fetchall()
        cur.close()
        conn.close()

        resultados = {
            "total": len(processos),
            "atualizados": 0,
            "erros": 0,
            "detalhes": []
        }

        for processo in processos:
            try:
                resultado = await consultar_datajud(processo["numero_processo"])
                if "sucesso" in resultado:
                    await atualizar_processo_datajud(processo["id"], admin)
                    resultados["atualizados"] += 1
                    resultados["detalhes"].append({
                        "numero": processo["numero_processo"],
                        "status": "atualizado"
                    })
                else:
                    resultados["erros"] += 1
                    resultados["detalhes"].append({
                        "numero": processo["numero_processo"],
                        "status": "erro",
                        "mensagem": resultado.get("erro", "Erro desconhecido")
                    })
            except Exception as e:
                resultados["erros"] += 1
                resultados["detalhes"].append({
                    "numero": processo["numero_processo"],
                    "status": "erro",
                    "mensagem": str(e)
                })

        return resultados

    except Exception as e:
        logger.error(f"Erro ao atualizar todos processos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
