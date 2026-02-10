"""
Rotas de Integração Escavador API V2
Criado em 09/02/2026

Substitui DataJud para monitoramento de processos.
Funcionalidades:
- Monitoramento semanal com callbacks automáticos
- Atualização sob demanda nos tribunais
- Resumo IA dos processos
- Consulta de capa + movimentações
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, date
from typing import Optional

import httpx
from psycopg2.extras import RealDictCursor

from modules.config import (
    logger,
    ESCAVADOR_API_TOKEN,
    ESCAVADOR_API_URL,
    ESCAVADOR_CALLBACK_URL,
)
from modules.database import (
    get_db,
    buscar_processo,
    buscar_processo_por_numero,
    criar_andamento_processo,
    verificar_andamento_existente,
)
from modules.prazos import (
    detectar_prazo_movimento,
    calcular_data_prazo,
    extrair_data_audiencia,
    prazo_ja_existe,
    criar_prazo,
)
from modules.auth import verificar_admin

router = APIRouter(tags=["Escavador"])


# ============================================
# FUNÇÃO AUXILIAR — CHAMADAS À API ESCAVADOR
# ============================================

async def escavador_request(method: str, endpoint: str, data: dict = None, params: dict = None) -> dict:
    """
    Faz requisição à API do Escavador V2.
    Retorna o JSON de resposta ou levanta HTTPException.
    """
    if not ESCAVADOR_API_TOKEN:
        raise HTTPException(status_code=500, detail="ESCAVADOR_API_TOKEN não configurado")

    url = f"{ESCAVADOR_API_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {ESCAVADOR_API_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                resp = await client.delete(url, headers=headers)
            else:
                raise HTTPException(status_code=400, detail=f"Método HTTP inválido: {method}")

        if resp.status_code >= 400:
            logger.error(f"Escavador API erro {resp.status_code}: {resp.text}")
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"Erro na API Escavador: {resp.text}"
            )

        return resp.json()
    except httpx.RequestError as e:
        logger.error(f"Erro de conexão com Escavador: {e}")
        raise HTTPException(status_code=502, detail=f"Erro de conexão com Escavador: {str(e)}")


# ============================================
# GERAÇÃO DE PRAZOS — WRAPPER ESCAVADOR
# ============================================

def gerar_prazos_escavador(processo_id: int, data_movimento: date, descricao_movimento: str) -> list:
    """
    Wrapper que gera prazos com origem='escavador_auto'.
    Reutiliza as funções de cálculo de modules/prazos.py.
    """
    prazos_criados = []

    resultado = detectar_prazo_movimento(descricao_movimento)
    if not resultado:
        return prazos_criados

    dias, tipo_prazo, prioridade, dias_uteis = resultado

    if "audiência" in tipo_prazo.lower():
        data_audiencia = extrair_data_audiencia(descricao_movimento)
        if data_audiencia:
            if not prazo_ja_existe(processo_id, tipo_prazo, data_movimento):
                prazo_id = criar_prazo(
                    processo_id=processo_id,
                    tipo=tipo_prazo,
                    descricao=f"Audiência: {descricao_movimento[:200]}",
                    data_inicio=data_movimento,
                    data_fim=data_audiencia,
                    dias_uteis=False,
                    prioridade="alta",
                    origem="escavador_auto",
                    movimento_origem=descricao_movimento[:500],
                )
                if prazo_id:
                    prazos_criados.append(prazo_id)
    else:
        data_fim = calcular_data_prazo(data_movimento, dias, dias_uteis)
        if not prazo_ja_existe(processo_id, tipo_prazo, data_movimento):
            prazo_id = criar_prazo(
                processo_id=processo_id,
                tipo=tipo_prazo,
                descricao=f"{tipo_prazo}: {descricao_movimento[:200]}",
                data_inicio=data_movimento,
                data_fim=data_fim,
                dias_uteis=dias_uteis,
                prioridade=prioridade,
                origem="escavador_auto",
                movimento_origem=descricao_movimento[:500],
            )
            if prazo_id:
                prazos_criados.append(prazo_id)

    return prazos_criados


# ============================================
# 6.1 — WEBHOOK (sem autenticação)
# ============================================

@router.post("/api/webhook/escavador")
async def webhook_escavador(request: Request):
    """
    Recebe callbacks do Escavador quando há atualizações em processos monitorados.
    SEM autenticação — endpoint público para o Escavador chamar.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body inválido")

    logger.info(f"[ESCAVADOR WEBHOOK] Callback recebido: {body}")

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # O Escavador pode enviar diferentes formatos de callback.
        # Formato esperado: { "numero_processo": "...", "movimentacoes": [...] }
        numero_processo = body.get("numero_processo") or body.get("numero_cnj")
        movimentacoes = body.get("movimentacoes") or body.get("movimentos") or []

        if not numero_processo:
            logger.warning("[ESCAVADOR WEBHOOK] Callback sem número de processo")
            return {"status": "ignorado", "motivo": "sem número de processo"}

        # Buscar processo no sistema
        processo = buscar_processo_por_numero(numero_processo)
        if not processo:
            logger.warning(f"[ESCAVADOR WEBHOOK] Processo {numero_processo} não encontrado no sistema")
            return {"status": "ignorado", "motivo": "processo não encontrado"}

        processo_id = processo["id"]
        andamentos_inseridos = 0
        prazos_gerados = 0

        for mov in movimentacoes:
            data_mov = mov.get("data") or mov.get("data_hora", "")[:10]
            descricao = mov.get("descricao") or mov.get("texto") or mov.get("conteudo", "")

            if not data_mov or not descricao:
                continue

            # Deduplicar
            if verificar_andamento_existente(processo_id, data_mov, descricao):
                continue

            # Inserir andamento
            and_id = criar_andamento_processo(processo_id, data_mov, descricao, True)
            if and_id:
                andamentos_inseridos += 1

                # Gerar prazos automáticos
                try:
                    data_mov_date = datetime.strptime(data_mov, "%Y-%m-%d").date()
                    ids_prazos = gerar_prazos_escavador(processo_id, data_mov_date, descricao)
                    prazos_gerados += len(ids_prazos)
                except Exception as e:
                    logger.warning(f"[ESCAVADOR WEBHOOK] Erro ao gerar prazos: {e}")

        # Marcar callback como recebido no monitoramento
        cur.execute("""
            UPDATE escavador_monitoramentos
            SET ultima_atualizacao = NOW()
            WHERE numero_processo = %s AND status = 'ativo'
        """, (numero_processo,))
        conn.commit()
        cur.close()
        conn.close()

        logger.info(
            f"[ESCAVADOR WEBHOOK] Processo {numero_processo}: "
            f"{andamentos_inseridos} andamentos inseridos, {prazos_gerados} prazos gerados"
        )

        return {
            "status": "ok",
            "processo": numero_processo,
            "andamentos_inseridos": andamentos_inseridos,
            "prazos_gerados": prazos_gerados,
        }

    except Exception as e:
        conn.close()
        logger.error(f"[ESCAVADOR WEBHOOK] Erro ao processar callback: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar callback: {str(e)}")


# ============================================
# 6.2 — MONITORAR 1 PROCESSO
# ============================================

@router.post("/api/admin/escavador/monitorar/{processo_id}")
async def monitorar_processo(processo_id: int, admin=Depends(verificar_admin)):
    """Cadastra monitoramento semanal de um processo no Escavador."""
    processo = buscar_processo(processo_id)
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    numero = processo["numero_processo"]

    # Verificar se já está monitorado
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT id FROM escavador_monitoramentos WHERE processo_id = %s AND status = 'ativo'",
            (processo_id,),
        )
        existente = cur.fetchone()
        if existente:
            cur.close()
            conn.close()
            raise HTTPException(status_code=409, detail="Processo já está sendo monitorado")

        # Solicitar primeira atualização no Escavador
        resp = await escavador_request("POST", f"/v2/processos/numero_cnj/{numero}/solicitar-atualizacao")

        escavador_id = str(resp.get("id", resp.get("processo_id", "")))

        # Salvar no banco local
        cur.execute("""
            INSERT INTO escavador_monitoramentos (processo_id, numero_processo, escavador_id, frequencia, status)
            VALUES (%s, %s, %s, 'semanal', 'ativo')
            RETURNING id
        """, (processo_id, numero, escavador_id))
        mon_id = cur.fetchone()["id"]
        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"[ESCAVADOR] Monitoramento criado: processo_id={processo_id}, escavador_id={escavador_id}")

        return {
            "sucesso": True,
            "monitoramento_id": mon_id,
            "escavador_id": escavador_id,
            "numero_processo": numero,
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        logger.error(f"[ESCAVADOR] Erro ao monitorar processo {processo_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao monitorar processo: {str(e)}")


# ============================================
# 6.3 — MONITORAR TODOS OS PROCESSOS ATIVOS
# ============================================

@router.post("/api/admin/escavador/monitorar-todos")
async def monitorar_todos(admin=Depends(verificar_admin)):
    """Monitora todos os processos ativos que ainda não estão monitorados."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Buscar processos ativos sem monitoramento ativo
        cur.execute("""
            SELECT p.id, p.numero_processo
            FROM processos p
            WHERE p.status = 'ativo'
              AND p.id NOT IN (
                  SELECT processo_id FROM escavador_monitoramentos WHERE status = 'ativo'
              )
        """)
        processos = cur.fetchall()
        cur.close()
        conn.close()

        total = len(processos)
        sucesso = 0
        erros = []

        for proc in processos:
            try:
                resp = await escavador_request("POST", f"/v2/processos/numero_cnj/{proc['numero_processo']}/solicitar-atualizacao")

                escavador_id = str(resp.get("id", resp.get("processo_id", "")))

                conn2 = get_db()
                if conn2:
                    cur2 = conn2.cursor()
                    cur2.execute("""
                        INSERT INTO escavador_monitoramentos (processo_id, numero_processo, escavador_id, frequencia, status)
                        VALUES (%s, %s, %s, 'semanal', 'ativo')
                    """, (proc["id"], proc["numero_processo"], escavador_id))
                    conn2.commit()
                    cur2.close()
                    conn2.close()

                sucesso += 1
            except Exception as e:
                erros.append({"processo": proc["numero_processo"], "erro": str(e)})
                logger.warning(f"[ESCAVADOR] Erro ao monitorar {proc['numero_processo']}: {e}")

        return {
            "total_processos": total,
            "monitorados_com_sucesso": sucesso,
            "erros": erros,
        }

    except Exception as e:
        logger.error(f"[ESCAVADOR] Erro ao monitorar todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 6.4 — ATUALIZAR 1 PROCESSO (sob demanda)
# ============================================

@router.post("/api/admin/escavador/atualizar/{processo_id}")
async def atualizar_processo_escavador(processo_id: int, admin=Depends(verificar_admin)):
    """Solicita atualização imediata de um processo no tribunal via Escavador e sincroniza andamentos."""
    processo = buscar_processo(processo_id)
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    numero = processo["numero_processo"]

    # 1. Solicitar atualização no tribunal
    await escavador_request("POST", f"/v2/processos/numero_cnj/{numero}/solicitar-atualizacao")

    logger.info(f"[ESCAVADOR] Atualização solicitada para {numero}")

    # 2. Buscar dados atuais e sincronizar movimentações
    resp = await escavador_request("GET", f"/v2/processos/numero_cnj/{numero}/movimentacoes")
    movimentacoes = resp.get("items") or resp.get("movimentacoes") or resp.get("movimentos") or []
    andamentos_inseridos = 0
    prazos_gerados = 0

    for mov in movimentacoes:
        data_mov = mov.get("data") or mov.get("data_hora", "")[:10]
        descricao = mov.get("descricao") or mov.get("texto") or mov.get("conteudo", "")

        if not data_mov or not descricao:
            continue

        if verificar_andamento_existente(processo_id, data_mov, descricao):
            continue

        and_id = criar_andamento_processo(processo_id, data_mov, descricao, True)
        if and_id:
            andamentos_inseridos += 1
            try:
                data_mov_date = datetime.strptime(data_mov, "%Y-%m-%d").date()
                ids_prazos = gerar_prazos_escavador(processo_id, data_mov_date, descricao)
                prazos_gerados += len(ids_prazos)
            except Exception as e:
                logger.warning(f"[ESCAVADOR] Erro ao gerar prazos: {e}")

    return {
        "sucesso": True,
        "numero_processo": numero,
        "andamentos_inseridos": andamentos_inseridos,
        "prazos_gerados": prazos_gerados,
        "total_movimentacoes_escavador": len(movimentacoes),
    }


# ============================================
# 6.5 — ATUALIZAR TODOS OS PROCESSOS ATIVOS
# ============================================

@router.post("/api/admin/escavador/atualizar-todos")
async def atualizar_todos(admin=Depends(verificar_admin)):
    """Atualiza todos os processos ativos: solicita ao tribunal e sincroniza andamentos."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, numero_processo FROM processos WHERE status = 'ativo'")
        processos = cur.fetchall()
        cur.close()
        conn.close()

        total = len(processos)
        sucesso = 0
        total_andamentos = 0
        total_prazos = 0
        erros = []

        for proc in processos:
            try:
                # Solicitar atualização no tribunal
                await escavador_request("POST", f"/v2/processos/numero_cnj/{proc['numero_processo']}/solicitar-atualizacao")

                # Buscar movimentações atuais
                resp = await escavador_request("GET", f"/v2/processos/numero_cnj/{proc['numero_processo']}/movimentacoes")
                movimentacoes = resp.get("items") or resp.get("movimentacoes") or resp.get("movimentos") or []
                for mov in movimentacoes:
                    data_mov = mov.get("data") or mov.get("data_hora", "")[:10]
                    descricao = mov.get("descricao") or mov.get("texto") or mov.get("conteudo", "")

                    if not data_mov or not descricao:
                        continue
                    if verificar_andamento_existente(proc["id"], data_mov, descricao):
                        continue

                    and_id = criar_andamento_processo(proc["id"], data_mov, descricao, True)
                    if and_id:
                        total_andamentos += 1
                        try:
                            data_mov_date = datetime.strptime(data_mov, "%Y-%m-%d").date()
                            ids_prazos = gerar_prazos_escavador(proc["id"], data_mov_date, descricao)
                            total_prazos += len(ids_prazos)
                        except Exception:
                            pass

                sucesso += 1
            except Exception as e:
                erros.append({"processo": proc["numero_processo"], "erro": str(e)})

        return {
            "total_processos": total,
            "atualizados_com_sucesso": sucesso,
            "andamentos_inseridos": total_andamentos,
            "prazos_gerados": total_prazos,
            "erros": erros,
        }

    except Exception as e:
        logger.error(f"[ESCAVADOR] Erro ao atualizar todos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 6.6 — CONSULTAR PROCESSO (capa + movimentações)
# ============================================

@router.get("/api/admin/escavador/processo/{numero_cnj:path}")
async def consultar_processo_escavador(numero_cnj: str, admin=Depends(verificar_admin)):
    """Consulta capa e movimentações de um processo no Escavador."""
    resp = await escavador_request("GET", f"/v2/processos/numero_cnj/{numero_cnj}")

    return {
        "sucesso": True,
        "numero_cnj": numero_cnj,
        "dados": resp,
    }


# ============================================
# 6.7 — RESUMO IA
# ============================================

@router.get("/api/admin/escavador/resumo-ia/{numero_cnj:path}")
async def resumo_ia_processo(numero_cnj: str, admin=Depends(verificar_admin)):
    """Busca ou solicita resumo IA de um processo no Escavador."""
    resp = await escavador_request("GET", f"/v2/processos/numero_cnj/{numero_cnj}/resumo-ia")

    return {
        "sucesso": True,
        "numero_cnj": numero_cnj,
        "resumo": resp,
    }


# ============================================
# 6.8 — LISTAR MONITORAMENTOS ATIVOS
# ============================================

@router.get("/api/admin/escavador/monitoramentos")
async def listar_monitoramentos(admin=Depends(verificar_admin)):
    """Lista todos os monitoramentos ativos com dados do processo e cadastro."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT
                em.id,
                em.processo_id,
                em.numero_processo,
                em.escavador_id,
                em.frequencia,
                em.status,
                em.ultima_atualizacao,
                em.criado_em,
                p.tipo_acao,
                p.fase,
                p.status AS processo_status,
                p.cadastro_id,
                c.dados->>'nome' AS cliente_nome
            FROM escavador_monitoramentos em
            JOIN processos p ON em.processo_id = p.id
            LEFT JOIN cadastros c ON p.cadastro_id = c.id
            WHERE em.status = 'ativo'
            ORDER BY em.criado_em DESC
        """)
        monitoramentos = [dict(row) for row in cur.fetchall()]
        cur.close()
        conn.close()

        return {
            "total": len(monitoramentos),
            "monitoramentos": monitoramentos,
        }

    except Exception as e:
        logger.error(f"[ESCAVADOR] Erro ao listar monitoramentos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 6.9 — REMOVER MONITORAMENTO
# ============================================

@router.delete("/api/admin/escavador/monitorar/{processo_id}")
async def remover_monitoramento(processo_id: int, admin=Depends(verificar_admin)):
    """Remove monitoramento de um processo (local + API Escavador)."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT id, escavador_id FROM escavador_monitoramentos WHERE processo_id = %s AND status = 'ativo'",
            (processo_id,),
        )
        mon = cur.fetchone()

        if not mon:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Monitoramento não encontrado")

        # Nota: A API V2 do Escavador não tem endpoint de remoção de monitoramento.
        # O monitoramento é apenas local — controlamos quais processos acompanhamos.

        # Marcar como inativo no banco local
        cur.execute(
            "UPDATE escavador_monitoramentos SET status = 'inativo' WHERE id = %s",
            (mon["id"],),
        )
        conn.commit()
        cur.close()
        conn.close()

        logger.info(f"[ESCAVADOR] Monitoramento removido: processo_id={processo_id}")

        return {"sucesso": True, "processo_id": processo_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.close()
        logger.error(f"[ESCAVADOR] Erro ao remover monitoramento: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 6.10 — SINCRONIZAR ANDAMENTOS MANUALMENTE
# ============================================

@router.post("/api/admin/escavador/sincronizar/{processo_id}")
async def sincronizar_processo(processo_id: int, admin=Depends(verificar_admin)):
    """Busca movimentações no Escavador e sincroniza com o banco local."""
    processo = buscar_processo(processo_id)
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")

    numero = processo["numero_processo"]

    # Buscar movimentações no Escavador
    resp = await escavador_request("GET", f"/v2/processos/numero_cnj/{numero}/movimentacoes")

    movimentacoes = resp.get("items") or resp.get("movimentacoes") or resp.get("movimentos") or []

    andamentos_inseridos = 0
    prazos_gerados = 0

    for mov in movimentacoes:
        data_mov = mov.get("data") or mov.get("data_hora", "")[:10]
        descricao = mov.get("descricao") or mov.get("texto") or mov.get("conteudo", "")

        if not data_mov or not descricao:
            continue

        if verificar_andamento_existente(processo_id, data_mov, descricao):
            continue

        and_id = criar_andamento_processo(processo_id, data_mov, descricao, True)
        if and_id:
            andamentos_inseridos += 1

            try:
                data_mov_date = datetime.strptime(data_mov, "%Y-%m-%d").date()
                ids_prazos = gerar_prazos_escavador(processo_id, data_mov_date, descricao)
                prazos_gerados += len(ids_prazos)
            except Exception as e:
                logger.warning(f"[ESCAVADOR] Erro ao gerar prazos para sync: {e}")

    logger.info(
        f"[ESCAVADOR] Sincronização {numero}: "
        f"{andamentos_inseridos} andamentos, {prazos_gerados} prazos"
    )

    return {
        "sucesso": True,
        "numero_processo": numero,
        "andamentos_inseridos": andamentos_inseridos,
        "prazos_gerados": prazos_gerados,
        "total_movimentacoes_escavador": len(movimentacoes),
    }


# ============================================
# 6.11 — SALDO DE CRÉDITOS
# ============================================

@router.get("/api/admin/escavador/saldo")
async def saldo_escavador(admin=Depends(verificar_admin)):
    """Consulta o saldo de créditos da conta Escavador (via API v1)."""
    resp = await escavador_request("GET", "/saldo")

    return {
        "sucesso": True,
        "saldo": resp,
    }
