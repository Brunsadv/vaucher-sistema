"""
Rotas Admin - Cadastros e Acesso de Clientes
Refatorado em 24/01/2026
"""

import os
import secrets
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from psycopg2.extras import RealDictCursor

from modules.config import logger, UPLOADS_DIR, RESEND_API_KEY
from modules.auth import verificar_admin
from modules.security import criar_email_html
from modules.email import enviar_email_resend
from modules.database import (
    get_db,
    buscar_cadastro,
    carregar_cadastros,
    salvar_cadastro,
    criar_cliente_auth,
    buscar_cliente_auth,
    buscar_processo_info,
    salvar_processo_info,
    # Documentos
    criar_documento_admin,
    listar_documentos_admin,
    buscar_documento_admin,
    deletar_documento_admin,
    listar_documentos_extras,
    buscar_documento_extra,
    deletar_documento_extra,
)


router = APIRouter(prefix="/api/admin", tags=["Admin - Cadastros"])


# ============================================
# MODELOS
# ============================================

class ClienteManual(BaseModel):
    """Dados para criação manual de cliente pelo admin."""
    nome: str
    email: EmailStr
    cpf: str
    telefone: str
    nacionalidade: str = "brasileiro(a)"
    estado_civil: str = ""
    profissao: str = ""
    data_nascimento: str = ""
    endereco_completo: str = ""
    rg: str = ""
    tipo_demanda: str = ""
    objeto_contrato: str = ""
    poderes_especificos: str = ""
    observacoes: str = ""
    habilitar_portal: bool = False


class ProcessoInfoModel(BaseModel):
    numero_processo: str = ""
    vara_tribunal: str = ""
    fase: str = "Inicial"
    data_distribuicao: str = None
    valor_causa: float = 0
    reu: str = ""
    observacoes: str = ""


# ============================================
# GERENCIAR ACESSO CLIENTE
# ============================================

@router.post("/clientes/{cadastro_id}/habilitar-acesso")
async def admin_habilitar_acesso_cliente(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin habilita acesso ao portal para um cliente."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")

    senha_temporaria = secrets.token_urlsafe(8)

    if not criar_cliente_auth(cadastro_id, senha_temporaria):
        raise HTTPException(status_code=500, detail="Erro ao criar acesso")

    dados = cadastro["dados"]
    email_cliente = dados.get("email")

    if email_cliente and RESEND_API_KEY:
        try:
            conteudo = f"""
                <p style="font-size: 16px;">Olá, <strong>{dados['nome']}</strong>!</p>

                <p>Seu acesso ao Portal do Cliente foi habilitado.</p>

                <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Email:</strong> {email_cliente}</p>
                    <p style="margin: 10px 0;"><strong>Senha temporária:</strong> <code style="background: #e0e0e0; padding: 3px 8px; border-radius: 4px; font-size: 18px;">{senha_temporaria}</code></p>
                </div>

                <p>Acesse o portal em: <a href="https://appcliente.vaucherealvares.com" style="color: #8B1538;">appcliente.vaucherealvares.com</a></p>

                <p style="color: #666; font-size: 14px;">
                    <strong>Importante:</strong> Recomendamos que você altere sua senha no primeiro acesso.
                </p>
            """
            corpo_html = criar_email_html(conteudo)

            await enviar_email_resend(
                email_cliente,
                "Seu acesso ao Portal do Cliente - Vaucher e Alvares",
                corpo_html
            )

            return {
                "success": True,
                "message": f"Acesso habilitado! Senha enviada para {email_cliente}",
                "senha_temporaria": senha_temporaria
            }
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return {
                "success": True,
                "message": "Acesso habilitado, mas houve erro ao enviar email.",
                "senha_temporaria": senha_temporaria
            }

    return {
        "success": True,
        "message": "Acesso habilitado!",
        "senha_temporaria": senha_temporaria
    }


@router.post("/clientes/{cadastro_id}/desabilitar-acesso")
async def admin_desabilitar_acesso_cliente(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin desabilita acesso ao portal de um cliente."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")

    try:
        cur = conn.cursor()
        cur.execute("UPDATE clientes_auth SET ativo = FALSE WHERE cadastro_id = %s", (cadastro_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "message": "Acesso desabilitado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clientes/{cadastro_id}/acesso")
async def admin_verificar_acesso_cliente(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Verifica se o cliente tem acesso ao portal."""
    auth = buscar_cliente_auth(cadastro_id)
    return {
        "tem_acesso": bool(auth and auth.get("ativo")),
        "primeiro_acesso": auth.get("primeiro_acesso") if auth else None,
        "ultimo_acesso": auth.get("ultimo_acesso") if auth else None
    }


# ============================================
# CRIAR/IMPORTAR CLIENTES
# ============================================

@router.post("/clientes")
async def admin_criar_cliente(
    dados: ClienteManual,
    usuario: dict = Depends(verificar_admin)
):
    """Admin cria um novo cliente manualmente."""
    logger.info(f"Admin {usuario['email']} criando cliente: {dados.nome}")

    # Verificar se já existe cliente com mesmo CPF
    cadastros = carregar_cadastros()
    cpf_limpo = dados.cpf.replace(".", "").replace("-", "")
    for c in cadastros:
        cpf_existente = c.get("dados", {}).get("cpf", "").replace(".", "").replace("-", "")
        if cpf_existente == cpf_limpo:
            raise HTTPException(status_code=400, detail=f"Já existe um cliente com o CPF {dados.cpf}")

    # Criar cadastro
    novo_cadastro = {
        "id": uuid.uuid4().hex[:12],
        "data": datetime.now().isoformat(),
        "data_cadastro_br": datetime.now().strftime("%d/%m/%Y"),
        "status": "validado",
        "dados": {
            "nome": dados.nome,
            "email": dados.email,
            "cpf": dados.cpf,
            "telefone": dados.telefone,
            "nacionalidade": dados.nacionalidade,
            "estado_civil": dados.estado_civil,
            "profissao": dados.profissao,
            "data_nascimento": dados.data_nascimento,
            "endereco_completo": dados.endereco_completo,
            "rg": dados.rg,
            "tipo_demanda": dados.tipo_demanda,
            "objeto_contrato": dados.objeto_contrato,
            "poderes_especificos": dados.poderes_especificos,
            "observacoes": dados.observacoes,
        },
        "documentos": [],
        "arquivos_gerados": {}
    }

    if not salvar_cadastro(novo_cadastro):
        raise HTTPException(status_code=500, detail="Erro ao salvar cadastro")

    resultado = {
        "success": True,
        "id": novo_cadastro["id"],
        "message": f"Cliente {dados.nome} criado com sucesso",
        "portal_habilitado": False
    }

    # Habilitar portal se solicitado
    if dados.habilitar_portal:
        senha_temporaria = secrets.token_urlsafe(8)
        if criar_cliente_auth(novo_cadastro["id"], senha_temporaria):
            resultado["portal_habilitado"] = True
            resultado["senha_temporaria"] = senha_temporaria

            # Enviar email com credenciais
            if RESEND_API_KEY:
                try:
                    conteudo = f"""
                        <p style="font-size: 16px;">Olá, <strong>{dados.nome}</strong>!</p>

                        <p>Seu cadastro foi criado e seu acesso ao Portal do Cliente foi habilitado.</p>

                        <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <p style="margin: 0;"><strong>Email:</strong> {dados.email}</p>
                            <p style="margin: 10px 0;"><strong>Senha temporária:</strong> <code style="background: #e0e0e0; padding: 3px 8px; border-radius: 4px; font-size: 18px;">{senha_temporaria}</code></p>
                        </div>

                        <p>Acesse o portal em: <a href="https://appcliente.vaucherealvares.com" style="color: #8B1538;">appcliente.vaucherealvares.com</a></p>

                        <p style="color: #666; font-size: 14px;">
                            <strong>Importante:</strong> Recomendamos que você altere sua senha no primeiro acesso.
                        </p>
                    """
                    corpo_html = criar_email_html(conteudo)
                    await enviar_email_resend(
                        dados.email,
                        "Acesso ao Portal do Cliente - Vaucher e Alvares",
                        corpo_html
                    )
                    resultado["email_enviado"] = True
                except Exception as e:
                    logger.error(f"Erro ao enviar email: {e}")
                    resultado["email_enviado"] = False

    return resultado


# ============================================
# PROCESSO INFO (LEGACY)
# ============================================

@router.get("/clientes/{cadastro_id}/processo")
async def admin_obter_processo(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin obtém informações do processo."""
    processo = buscar_processo_info(cadastro_id)
    return processo or {
        "cadastro_id": cadastro_id,
        "numero_processo": "",
        "vara_tribunal": "",
        "fase": "Inicial",
        "data_distribuicao": None,
        "valor_causa": 0,
        "reu": "",
        "observacoes": ""
    }


@router.post("/clientes/{cadastro_id}/processo")
async def admin_salvar_processo(
    cadastro_id: str,
    dados: ProcessoInfoModel,
    usuario: dict = Depends(verificar_admin)
):
    """Admin salva informações do processo."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")

    if salvar_processo_info(cadastro_id, dados.dict()):
        return {"success": True, "message": "Informações do processo salvas"}

    raise HTTPException(status_code=500, detail="Erro ao salvar")


# ============================================
# DOCUMENTOS (ADMIN -> CLIENTE)
# ============================================

@router.post("/clientes/{cadastro_id}/enviar-documentos")
async def admin_enviar_documentos(
    cadastro_id: str,
    arquivos: List[UploadFile] = File(...),
    usuario: dict = Depends(verificar_admin)
):
    """Admin envia documentos para o cliente."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")

    # Criar diretório para documentos do admin
    docs_dir = os.path.join(UPLOADS_DIR, "documentos_admin", cadastro_id)
    os.makedirs(docs_dir, exist_ok=True)

    arquivos_salvos = []

    for arquivo in arquivos:
        # Salvar arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"{timestamp}_{arquivo.filename}"
        caminho_arquivo = os.path.join(docs_dir, nome_arquivo)

        with open(caminho_arquivo, "wb") as f:
            conteudo = await arquivo.read()
            f.write(conteudo)

        # Criar registro no banco
        doc_id = criar_documento_admin(
            cadastro_id=cadastro_id,
            nome_arquivo=nome_arquivo,
            nome_original=arquivo.filename,
            arquivo_path=caminho_arquivo,
            descricao="",
            admin_email=usuario["email"]
        )

        if doc_id:
            arquivos_salvos.append({
                "id": doc_id,
                "nome": arquivo.filename
            })

    if arquivos_salvos:
        # Enviar e-mail notificando o cliente
        dados_cliente = cadastro.get("dados", {})
        email_cliente = dados_cliente.get("email")
        nome_cliente = dados_cliente.get("nome", "Cliente")

        if email_cliente:
            lista_arquivos = "".join([f"<li>{arq['nome']}</li>" for arq in arquivos_salvos])

            conteudo_email = f"""
                <h2 style="color: #8B1538;">Novos Documentos Disponíveis</h2>

                <p>Olá, <strong>{nome_cliente}</strong>!</p>

                <p>O escritório <strong>Vaucher e Álvares Sociedade de Advogados</strong> enviou novos documentos para você:</p>

                <ul style="background-color: #f8f8f8; padding: 15px 30px; border-radius: 8px;">
                    {lista_arquivos}
                </ul>

                <p>Para visualizar e baixar os documentos, acesse o <strong>Portal do Cliente</strong>:</p>

                <p style="text-align: center; margin: 30px 0;">
                    <a href="https://appcliente.vaucherealvares.com"
                       style="background-color: #8B1538; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Acessar Portal do Cliente
                    </a>
                </p>

                <p style="color: #666; font-size: 14px;">
                    Caso tenha dúvidas, entre em contato conosco pelo portal ou pelos nossos canais de atendimento.
                </p>
            """

            email_html = criar_email_html(conteudo_email)

            try:
                await enviar_email_resend(
                    email_cliente,
                    "Novos documentos disponíveis - Vaucher e Alvares",
                    email_html
                )
                logger.info(f"E-mail de notificação enviado para {email_cliente}")
            except Exception as e:
                logger.error(f"Erro ao enviar e-mail de notificação: {e}")

        return {
            "success": True,
            "message": f"{len(arquivos_salvos)} documento(s) enviado(s)",
            "arquivos": arquivos_salvos,
            "email_enviado": bool(email_cliente)
        }

    raise HTTPException(status_code=500, detail="Erro ao salvar documentos")


@router.post("/clientes/{cadastro_id}/documentos")
async def admin_upload_documento(
    cadastro_id: str,
    arquivo: UploadFile = File(...),
    descricao: str = Form(""),
    usuario: dict = Depends(verificar_admin)
):
    """Admin envia documento para o cliente (endpoint alternativo)."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")

    # Criar diretório para documentos do admin
    docs_dir = os.path.join(UPLOADS_DIR, "documentos_admin", cadastro_id)
    os.makedirs(docs_dir, exist_ok=True)

    # Salvar arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"{timestamp}_{arquivo.filename}"
    caminho_arquivo = os.path.join(docs_dir, nome_arquivo)

    with open(caminho_arquivo, "wb") as f:
        conteudo = await arquivo.read()
        f.write(conteudo)

    # Criar registro no banco
    doc_id = criar_documento_admin(
        cadastro_id=cadastro_id,
        nome_arquivo=nome_arquivo,
        nome_original=arquivo.filename,
        arquivo_path=caminho_arquivo,
        descricao=descricao,
        admin_email=usuario["email"]
    )

    if doc_id:
        # Enviar notificação por e-mail para o cliente
        try:
            if cadastro.get("dados"):
                cliente_dados = cadastro["dados"]
                email_cliente = cliente_dados.get("email")
                nome_cliente = cliente_dados.get("nome", "Cliente")

                if email_cliente:
                    assunto = "Novo documento disponível - Vaucher e Alvares"
                    corpo_html = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #8B0000 0%, #5C0000 100%); padding: 30px; text-align: center;">
                            <h1 style="color: white; margin: 0; font-size: 24px;">Vaucher e Alvares</h1>
                            <p style="color: rgba(255,255,255,0.8); margin: 10px 0 0 0;">Sociedade de Advogados</p>
                        </div>
                        <div style="padding: 30px; background: #f9f9f9;">
                            <h2 style="color: #333; margin-top: 0;">Olá, {nome_cliente}!</h2>
                            <p style="color: #666; font-size: 16px; line-height: 1.6;">
                                Um novo documento foi disponibilizado para você no Portal do Cliente.
                            </p>
                            <div style="background: white; border: 1px solid #ddd; padding: 15px; margin: 20px 0; border-radius: 4px;">
                                <p style="color: #333; margin: 0;"><strong>{arquivo.filename}</strong></p>
                                {f'<p style="color: #666; margin: 5px 0 0 0; font-size: 14px;">{descricao}</p>' if descricao else ''}
                            </div>
                            <p style="color: #666; font-size: 14px;">
                                Para visualizar e baixar o documento, acesse o Portal do Cliente:
                            </p>
                            <a href="https://appcliente.vaucherealvares.com/portal/documentos"
                               style="display: inline-block; background: #8B0000; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px;">
                                Acessar Portal
                            </a>
                        </div>
                        <div style="padding: 20px; text-align: center; color: #999; font-size: 12px;">
                            <p>Este é um e-mail automático. Por favor, não responda diretamente.</p>
                        </div>
                    </div>
                    """
                    await enviar_email_resend(email_cliente, assunto, corpo_html)
                    logger.info(f"E-mail de novo documento enviado para {email_cliente}")
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de notificação de documento: {e}")

        return {
            "success": True,
            "message": "Documento enviado com sucesso",
            "documento_id": doc_id
        }

    raise HTTPException(status_code=500, detail="Erro ao salvar documento")


@router.get("/clientes/{cadastro_id}/documentos-enviados")
async def admin_listar_documentos_enviados(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista documentos enviados para o cliente."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")

    documentos = listar_documentos_admin(cadastro_id)
    return {"documentos": documentos}


@router.delete("/documentos/{doc_id}")
async def admin_deletar_documento(
    doc_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um documento enviado."""
    if deletar_documento_admin(doc_id):
        return {"success": True, "message": "Documento deletado"}

    raise HTTPException(status_code=500, detail="Erro ao deletar documento")


@router.get("/documentos/{doc_id}/download")
async def admin_download_documento(
    doc_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin baixa um documento enviado."""
    doc = buscar_documento_admin(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if not os.path.exists(doc["arquivo_path"]):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        doc["arquivo_path"],
        filename=doc["nome_original"],
        media_type="application/octet-stream"
    )


# ============================================
# DOCUMENTOS EXTRAS (CLIENTE -> ADMIN)
# ============================================

@router.get("/clientes/{cadastro_id}/documentos-extras")
async def admin_listar_documentos_extras(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista documentos extras enviados pelo cliente."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")

    documentos = listar_documentos_extras(cadastro_id)
    return {"documentos": documentos}


@router.get("/documentos-extras/{doc_id}/download")
async def admin_download_documento_extra(
    doc_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin baixa um documento extra enviado pelo cliente."""
    doc = buscar_documento_extra(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    if not os.path.exists(doc["arquivo_path"]):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    return FileResponse(
        doc["arquivo_path"],
        filename=doc["nome_original"],
        media_type="application/octet-stream"
    )


@router.delete("/documentos-extras/{doc_id}")
async def admin_deletar_documento_extra(
    doc_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um documento extra."""
    if deletar_documento_extra(doc_id):
        return {"success": True, "message": "Documento deletado"}

    raise HTTPException(status_code=500, detail="Erro ao deletar documento")
