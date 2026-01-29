"""
Rotas do Portal do Cliente
Refatorado em 24/01/2026
"""

import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from modules.config import logger, limiter, UPLOADS_DIR
from modules.auth import verificar_token_cliente
from modules.security import (
    verificar_senha,
    hash_senha,
    senha_precisa_atualizacao,
    gerar_token_cliente,
    criar_email_html,
)
from modules.email import enviar_email_resend
from modules.database import (
    get_db,
    buscar_cadastro,
    buscar_cliente_por_email,
    buscar_cliente_auth,
    registrar_acesso_cliente,
    atualizar_senha_cliente,
    # Processos
    listar_processos,
    # Andamentos
    listar_andamentos_processo,
    listar_andamentos,
    # Contratos
    listar_contratos,
    # Mensagens
    listar_mensagens,
    criar_mensagem,
    marcar_mensagens_lidas,
    contar_mensagens_nao_lidas,
    # Documentos
    criar_documento_extra,
    listar_documentos_extras,
    buscar_documento_extra,
    deletar_documento_extra,
    listar_documentos_admin,
    buscar_documento_admin,
    # Comprovantes
    criar_comprovante,
)

from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/api/cliente", tags=["Portal do Cliente"])


# ============================================
# MODELOS
# ============================================

class ClienteLogin(BaseModel):
    email: str
    senha: str


class ClienteAlterarSenha(BaseModel):
    senha_atual: str
    nova_senha: str


class MensagemEnvio(BaseModel):
    texto: str


# ============================================
# AUTENTICAÇÃO DO CLIENTE
# ============================================

@router.post("/login")
@limiter.limit("5/minute")
async def portal_cliente_login(request: Request, dados: ClienteLogin):
    """Login do cliente no portal."""
    logger.info(f"Tentativa de login cliente: {dados.email}")

    cliente = buscar_cliente_por_email(dados.email)
    logger.info(f"Cliente encontrado: {cliente}")

    if not cliente:
        raise HTTPException(status_code=401, detail="Email não encontrado")

    if not cliente.get("senha_hash"):
        logger.info(f"Senha hash não encontrada para cliente: {cliente.get('cadastro_id')}")
        raise HTTPException(status_code=401, detail="Acesso não habilitado. Entre em contato com o escritório.")

    if not verificar_senha(dados.senha, cliente["senha_hash"]):
        raise HTTPException(status_code=401, detail="Senha incorreta")

    if not cliente.get("ativo", True):
        raise HTTPException(status_code=401, detail="Acesso desativado")

    # Migra senha legada para bcrypt se necessário
    if senha_precisa_atualizacao(cliente["senha_hash"]):
        conn = None
        cur = None
        try:
            novo_hash = hash_senha(dados.senha)
            conn = get_db()
            if conn:
                cur = conn.cursor()
                cur.execute("UPDATE clientes_acesso SET senha_hash = %s WHERE cadastro_id = %s",
                            (novo_hash, cliente['cadastro_id']))
                conn.commit()
                logger.info(f"Senha cliente migrada para bcrypt: {cliente['cadastro_id']}")
        except Exception as e:
            logger.error(f"Erro ao migrar senha cliente: {e}")
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()

    registrar_acesso_cliente(cliente["cadastro_id"])
    token = gerar_token_cliente(cliente["cadastro_id"], cliente["email"])

    return {
        "success": True,
        "token": token,
        "cadastro_id": cliente["cadastro_id"],
        "nome": cliente["nome"],
        "email": cliente["email"],
        "primeiro_acesso": cliente.get("primeiro_acesso", False)
    }


@router.post("/alterar-senha")
@limiter.limit("5/minute")
async def portal_cliente_alterar_senha(
    request: Request,
    dados: ClienteAlterarSenha,
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente altera sua própria senha."""
    auth = buscar_cliente_auth(cliente["cadastro_id"])
    if not verificar_senha(dados.senha_atual, auth["senha_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    if len(dados.nova_senha) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter no mínimo 6 caracteres")

    if atualizar_senha_cliente(cliente["cadastro_id"], dados.nova_senha):
        return {"success": True, "message": "Senha alterada com sucesso"}

    raise HTTPException(status_code=500, detail="Erro ao alterar senha")


# ============================================
# DADOS DO CLIENTE
# ============================================

@router.get("/meus-dados")
async def portal_cliente_meus_dados(cliente: dict = Depends(verificar_token_cliente)):
    """Retorna dados pessoais do cliente logado."""
    logger.info(f"MEUS-DADOS: cadastro_id={cliente['cadastro_id']}")

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM cadastros WHERE id = %s", (cliente["cadastro_id"],))
        row = cur.fetchone()
        logger.info(f"MEUS-DADOS: row encontrado={row is not None}")
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"Cadastro {cliente['cadastro_id']} não encontrado")

        dados = row["dados"] if isinstance(row["dados"], dict) else json.loads(row["dados"])

        return {
            "cadastro_id": cliente["cadastro_id"],
            "nome": dados.get("nome", ""),
            "email": dados.get("email", ""),
            "telefone": dados.get("telefone", ""),
            "cpf": dados.get("cpf", ""),
            "endereco": dados.get("endereco_completo", ""),
            "primeiro_acesso": cliente.get("primeiro_acesso", False)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro em meus-dados: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# PROCESSOS
# ============================================

@router.get("/meus-processos")
async def portal_cliente_meus_processos(cliente: dict = Depends(verificar_token_cliente)):
    """Retorna todos os processos do cliente logado."""
    logger.info(f"MEUS-PROCESSOS: cadastro_id={cliente['cadastro_id']}")

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, cadastro_id, numero_processo, tipo_acao, vara_tribunal,
                   fase, reu, valor_causa, data_distribuicao, status, observacoes
            FROM processos
            WHERE cadastro_id = %s
            ORDER BY criado_em DESC
        """, (cliente["cadastro_id"],))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        processos = []
        for row in rows:
            processos.append({
                "id": row["id"],
                "cadastro_id": row["cadastro_id"],
                "numero_processo": row["numero_processo"],
                "tipo_acao": row["tipo_acao"],
                "vara_tribunal": row["vara_tribunal"],
                "fase": row["fase"],
                "reu": row["reu"],
                "valor_causa": float(row["valor_causa"]) if row["valor_causa"] else 0,
                "data_distribuicao": row["data_distribuicao"].isoformat() if row["data_distribuicao"] else None,
                "status": row["status"],
                "observacoes": row["observacoes"]
            })

        logger.info(f"MEUS-PROCESSOS: encontrados {len(processos)} processos")
        return {"processos": processos}

    except Exception as e:
        logger.error(f"Erro ao buscar processos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar processos")


@router.get("/processo/{processo_id}/andamentos")
async def portal_cliente_andamentos_processo(processo_id: int, cliente: dict = Depends(verificar_token_cliente)):
    """Retorna andamentos de um processo (apenas visíveis ao cliente)."""
    logger.info(f"ANDAMENTOS: processo_id={processo_id}, cadastro_id={cliente['cadastro_id']}")

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Verificar se o processo pertence ao cliente
        cur.execute("""
            SELECT id FROM processos
            WHERE id = %s AND cadastro_id = %s
        """, (processo_id, cliente["cadastro_id"]))

        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Processo não encontrado")

        # Buscar andamentos visíveis ao cliente
        cur.execute("""
            SELECT id, processo_id, data, descricao
            FROM processo_andamentos
            WHERE processo_id = %s AND visivel_cliente = true
            ORDER BY data DESC, criado_em DESC
        """, (processo_id,))

        rows = cur.fetchall()
        cur.close()
        conn.close()

        andamentos = []
        for row in rows:
            andamentos.append({
                "id": row["id"],
                "processo_id": row["processo_id"],
                "data": row["data"].isoformat() if row["data"] else None,
                "descricao": row["descricao"]
            })

        logger.info(f"ANDAMENTOS: encontrados {len(andamentos)} andamentos")
        return {"andamentos": andamentos}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar andamentos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar andamentos")


@router.get("/andamentos")
async def portal_cliente_andamentos(cliente: dict = Depends(verificar_token_cliente)):
    """Lista andamentos visíveis para o cliente (legacy)."""
    andamentos = listar_andamentos(cliente["cadastro_id"], apenas_visiveis=True)
    return {"andamentos": andamentos}


# ============================================
# CONTRATOS
# ============================================

@router.get("/meus-contratos")
async def portal_cliente_meus_contratos(cliente: dict = Depends(verificar_token_cliente)):
    """Retorna todos os contratos de honorários do cliente."""
    logger.info(f"MEUS-CONTRATOS: cadastro_id={cliente['cadastro_id']}")

    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Buscar contratos
        cur.execute("""
            SELECT c.id, c.cadastro_id, c.processo_id, c.tipo, c.descricao,
                   c.valor_total, c.num_parcelas, c.valor_mensal, c.dia_vencimento,
                   c.percentual_exito, c.data_inicio, c.status, c.observacoes,
                   p.numero_processo
            FROM contratos_honorarios c
            LEFT JOIN processos p ON c.processo_id = p.id
            WHERE c.cadastro_id = %s
            ORDER BY c.criado_em DESC
        """, (cliente["cadastro_id"],))

        rows = cur.fetchall()

        contratos = []
        for row in rows:
            contrato_id = row["id"]

            # Buscar parcelas do contrato
            cur.execute("""
                SELECT id, contrato_id, numero, valor, vencimento, status, data_pagamento
                FROM parcelas
                WHERE contrato_id = %s
                ORDER BY numero
            """, (contrato_id,))

            parcelas_rows = cur.fetchall()
            parcelas = []
            for p in parcelas_rows:
                parcelas.append({
                    "id": p["id"],
                    "contrato_id": p["contrato_id"],
                    "numero": p["numero"],
                    "valor": float(p["valor"]) if p["valor"] else 0,
                    "vencimento": p["vencimento"].isoformat() if p["vencimento"] else None,
                    "status": p["status"],
                    "data_pagamento": p["data_pagamento"].isoformat() if p["data_pagamento"] else None
                })

            contratos.append({
                "id": contrato_id,
                "cadastro_id": row["cadastro_id"],
                "processo_id": row["processo_id"],
                "tipo": row["tipo"],
                "descricao": row["descricao"],
                "valor_total": float(row["valor_total"]) if row["valor_total"] else 0,
                "num_parcelas": row["num_parcelas"] or 1,
                "valor_mensal": float(row["valor_mensal"]) if row["valor_mensal"] else 0,
                "dia_vencimento": row["dia_vencimento"],
                "percentual_exito": float(row["percentual_exito"]) if row["percentual_exito"] else 0,
                "data_inicio": row["data_inicio"].isoformat() if row["data_inicio"] else None,
                "status": row["status"],
                "observacoes": row["observacoes"],
                "processo_numero": row["numero_processo"],
                "parcelas": parcelas
            })

        cur.close()
        conn.close()

        logger.info(f"MEUS-CONTRATOS: encontrados {len(contratos)} contratos")
        return {"contratos": contratos}

    except Exception as e:
        logger.error(f"Erro ao buscar contratos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar contratos")


@router.post("/parcelas/{parcela_id}/comprovante")
async def portal_cliente_enviar_comprovante(
    parcela_id: int,
    arquivo: UploadFile = File(...),
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente envia comprovante de pagamento."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT p.*, c.cadastro_id
            FROM parcelas p
            JOIN contratos_honorarios c ON p.contrato_id = c.id
            WHERE p.id = %s
        """, (parcela_id,))
        parcela = cur.fetchone()
        cur.close()
        conn.close()

        if not parcela or parcela["cadastro_id"] != cliente["cadastro_id"]:
            raise HTTPException(status_code=404, detail="Parcela não encontrada")

        if parcela["status"] == "pago":
            raise HTTPException(status_code=400, detail="Parcela já está paga")

        # Salvar arquivo
        comprovantes_dir = os.path.join(UPLOADS_DIR, "comprovantes", cliente["cadastro_id"])
        os.makedirs(comprovantes_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"parcela_{parcela_id}_{timestamp}_{arquivo.filename}"
        caminho_arquivo = os.path.join(comprovantes_dir, nome_arquivo)

        with open(caminho_arquivo, "wb") as f:
            conteudo = await arquivo.read()
            f.write(conteudo)

        # Criar registro do comprovante
        comprovante_id = criar_comprovante(parcela_id, arquivo.filename, caminho_arquivo)

        if comprovante_id:
            return {
                "success": True,
                "message": "Comprovante enviado! Aguarde verificação do escritório.",
                "comprovante_id": comprovante_id
            }

        raise HTTPException(status_code=500, detail="Erro ao salvar comprovante")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar comprovante: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# MENSAGENS
# ============================================

@router.get("/mensagens")
async def portal_cliente_mensagens(cliente: dict = Depends(verificar_token_cliente)):
    """Lista mensagens do cliente."""
    marcar_mensagens_lidas(cliente["cadastro_id"], "cliente")
    mensagens = listar_mensagens(cliente["cadastro_id"])
    return {"mensagens": mensagens}


@router.post("/mensagens")
async def portal_cliente_enviar_mensagem(
    dados: MensagemEnvio,
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente envia mensagem para o escritório."""
    if not dados.texto.strip():
        raise HTTPException(status_code=400, detail="Mensagem não pode ser vazia")

    msg_id = criar_mensagem(cliente["cadastro_id"], "cliente", dados.texto.strip())
    if msg_id:
        # Enviar e-mail notificando o escritório
        nome_cliente = cliente.get("nome", "Cliente")

        conteudo_email = f"""
            <h2 style="color: #8B1538;">Nova Mensagem Recebida</h2>

            <p>O cliente <strong>{nome_cliente}</strong> enviou uma nova mensagem pelo Portal do Cliente.</p>

            <div style="background-color: #f8f8f8; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #8B1538;">
                <p style="margin: 0; white-space: pre-wrap;">{dados.texto.strip()}</p>
            </div>

            <p><strong>Cliente:</strong> {nome_cliente}<br>
            <strong>Código:</strong> {cliente["cadastro_id"]}</p>

            <p>Acesse o <strong>Painel Administrativo</strong> para responder:</p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="https://painel.vaucherealvares.com"
                   style="background-color: #8B1538; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Acessar Painel Administrativo
                </a>
            </p>
        """

        email_html = criar_email_html(conteudo_email)

        try:
            await enviar_email_resend(
                "atendimento@vaucherealvares.com",
                f"Nova mensagem de {nome_cliente}",
                email_html
            )
            logger.info(f"E-mail de notificação de mensagem enviado - cliente {nome_cliente}")
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de notificação de mensagem: {e}")

        return {"success": True, "message_id": msg_id}

    raise HTTPException(status_code=500, detail="Erro ao enviar mensagem")


@router.get("/mensagens/nao-lidas")
async def portal_cliente_mensagens_nao_lidas(cliente: dict = Depends(verificar_token_cliente)):
    """Conta mensagens não lidas do escritório."""
    count = contar_mensagens_nao_lidas(cliente["cadastro_id"], "escritorio")
    return {"nao_lidas": count}


# ============================================
# DOCUMENTOS EXTRAS
# ============================================

@router.post("/documentos-extras")
async def portal_cliente_enviar_documento_extra(
    arquivo: UploadFile = File(...),
    descricao: str = Form(""),
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente envia documento extra para o escritório."""
    # Criar diretório para documentos extras
    docs_dir = os.path.join(UPLOADS_DIR, "documentos_extras", cliente["cadastro_id"])
    os.makedirs(docs_dir, exist_ok=True)

    # Salvar arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"{timestamp}_{arquivo.filename}"
    caminho_arquivo = os.path.join(docs_dir, nome_arquivo)

    with open(caminho_arquivo, "wb") as f:
        conteudo = await arquivo.read()
        f.write(conteudo)

    # Criar registro no banco
    doc_id = criar_documento_extra(
        cadastro_id=cliente["cadastro_id"],
        nome_arquivo=nome_arquivo,
        nome_original=arquivo.filename,
        arquivo_path=caminho_arquivo,
        descricao=descricao
    )

    if doc_id:
        # Enviar e-mail notificando o escritório
        cadastro = buscar_cadastro(cliente["cadastro_id"])
        nome_cliente = cliente.get("nome", "Cliente")

        conteudo_email = f"""
            <h2 style="color: #8B1538;">Novo Documento Recebido</h2>

            <p>O cliente <strong>{nome_cliente}</strong> enviou um novo documento pelo Portal do Cliente.</p>

            <div style="background-color: #f8f8f8; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Documento:</strong> {arquivo.filename}</p>
                {f'<p><strong>Descrição:</strong> {descricao}</p>' if descricao else ''}
                <p><strong>Cliente:</strong> {nome_cliente}</p>
                <p><strong>Código:</strong> {cliente["cadastro_id"]}</p>
            </div>

            <p>Acesse o <strong>Painel Administrativo</strong> para visualizar e baixar o documento:</p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="https://painel.vaucherealvares.com"
                   style="background-color: #8B1538; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Acessar Painel Administrativo
                </a>
            </p>
        """

        email_html = criar_email_html(conteudo_email)

        try:
            await enviar_email_resend(
                "atendimento@vaucherealvares.com",
                f"Novo documento recebido de {nome_cliente}",
                email_html
            )
            logger.info(f"E-mail de notificação enviado para o escritório - documento de {nome_cliente}")
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de notificação: {e}")

        return {
            "success": True,
            "message": "Documento enviado com sucesso",
            "documento_id": doc_id
        }

    raise HTTPException(status_code=500, detail="Erro ao salvar documento")


@router.get("/meus-documentos-extras")
async def portal_cliente_listar_documentos_extras(
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente lista seus documentos extras enviados."""
    documentos = listar_documentos_extras(cliente["cadastro_id"])
    return {"documentos": documentos}


@router.delete("/documentos-extras/{doc_id}")
async def portal_cliente_deletar_documento_extra(
    doc_id: int,
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente deleta um documento extra enviado."""
    # Verificar se o documento pertence ao cliente
    doc = buscar_documento_extra(doc_id)
    if not doc or doc["cadastro_id"] != cliente["cadastro_id"]:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if deletar_documento_extra(doc_id):
        return {"success": True, "message": "Documento deletado"}

    raise HTTPException(status_code=500, detail="Erro ao deletar documento")
