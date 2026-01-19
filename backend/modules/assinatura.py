"""
Módulo de Assinatura Digital do Sistema Vaucher e Álvares
Criado em 19/01/2026

Este arquivo contém funções para:
- Link direto para Assinador Gov.br
- Integração com ZapSign API para assinatura digital
"""

import os
import httpx
import base64
from typing import Optional, List, Dict
from datetime import datetime

from modules.config import logger

# Configurações ZapSign
ZAPSIGN_API_TOKEN = os.getenv("ZAPSIGN_API_TOKEN", "")
ZAPSIGN_API_URL = "https://api.zapsign.com.br/api/v1"
ZAPSIGN_SANDBOX_URL = "https://sandbox.api.zapsign.com.br/api/v1"

# URL do Assinador Gov.br
GOVBR_ASSINADOR_URL = "https://sso.acesso.gov.br/login?client_id=assinador.iti.br"
GOVBR_VALIDADOR_URL = "https://validar.iti.gov.br/"


def get_zapsign_url() -> str:
    """Retorna a URL da API ZapSign (sandbox ou produção)."""
    # Se não há token ou é token de sandbox, usa sandbox
    if not ZAPSIGN_API_TOKEN or ZAPSIGN_API_TOKEN.startswith("sandbox_"):
        return ZAPSIGN_SANDBOX_URL
    return ZAPSIGN_API_URL


def gerar_link_govbr() -> dict:
    """
    Gera informações para assinatura via Gov.br.

    Returns:
        dict com URL do assinador e instruções
    """
    return {
        "url_assinador": GOVBR_ASSINADOR_URL,
        "url_validador": GOVBR_VALIDADOR_URL,
        "instrucoes": [
            "1. Clique no link para acessar o Assinador Gov.br",
            "2. Faça login com sua conta Gov.br (nível Prata ou Ouro)",
            "3. Faça upload do documento PDF que deseja assinar",
            "4. Assine o documento digitalmente",
            "5. Baixe o documento assinado",
            "6. Faça upload do documento assinado no portal do escritório"
        ],
        "requisitos": "Conta Gov.br nível Prata ou Ouro"
    }


async def criar_documento_zapsign(
    nome_documento: str,
    arquivo_path: str = None,
    arquivo_base64: str = None,
    arquivo_url: str = None,
    signatarios: List[Dict] = None,
    enviar_email_automatico: bool = True,
    mensagem_email: str = None
) -> dict:
    """
    Cria um documento na ZapSign para assinatura.

    Args:
        nome_documento: Nome/título do documento
        arquivo_path: Caminho local do arquivo PDF
        arquivo_base64: Arquivo em base64
        arquivo_url: URL pública do arquivo
        signatarios: Lista de signatários com nome, email, etc.
        enviar_email_automatico: Se True, ZapSign envia e-mail para signatários
        mensagem_email: Mensagem personalizada para o e-mail

    Returns:
        dict com token do documento e links de assinatura
    """
    if not ZAPSIGN_API_TOKEN:
        logger.error("ZAPSIGN_API_TOKEN não configurado!")
        return {"error": "API Token não configurado", "success": False}

    # Preparar o arquivo
    pdf_data = None

    if arquivo_path and os.path.exists(arquivo_path):
        with open(arquivo_path, "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode("utf-8")
    elif arquivo_base64:
        pdf_data = arquivo_base64
    elif arquivo_url:
        pass  # Usar url_pdf diretamente
    else:
        return {"error": "Nenhum arquivo fornecido", "success": False}

    # Preparar signatários
    if not signatarios:
        return {"error": "Nenhum signatário informado", "success": False}

    signers = []
    for sig in signatarios:
        signer = {
            "name": sig.get("nome", ""),
            "email": sig.get("email", ""),
            "auth_mode": sig.get("auth_mode", "assinaturaTela"),
            "send_automatic_email": enviar_email_automatico,
            "send_automatic_whatsapp": False
        }

        if sig.get("telefone"):
            signer["phone_country"] = "55"
            signer["phone_number"] = sig["telefone"].replace("-", "").replace(" ", "")

        signers.append(signer)

    # Montar payload
    payload = {
        "name": nome_documento,
        "signers": signers,
        "lang": "pt-br",
        "disable_signer_emails": not enviar_email_automatico
    }

    if pdf_data:
        payload["base64_pdf"] = pdf_data
    elif arquivo_url:
        payload["url_pdf"] = arquivo_url

    if mensagem_email:
        payload["brand_primary_color"] = "#8B1538"  # Cor do escritório
        payload["external_id"] = f"vaucher_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Fazer requisição
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{get_zapsign_url()}/docs/",
                headers={
                    "Authorization": f"Bearer {ZAPSIGN_API_TOKEN}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=60.0
            )

            logger.info(f"ZapSign response status: {response.status_code}")

            if response.status_code in [200, 201]:
                data = response.json()

                # Processar resposta
                resultado = {
                    "success": True,
                    "documento_token": data.get("token"),
                    "documento_id": data.get("open_id"),
                    "status": data.get("status"),
                    "signatarios": []
                }

                for signer in data.get("signers", []):
                    resultado["signatarios"].append({
                        "token": signer.get("token"),
                        "url_assinatura": signer.get("sign_url"),
                        "status": signer.get("status", "pending")
                    })

                logger.info(f"Documento criado na ZapSign: {resultado['documento_token']}")
                return resultado
            else:
                error_msg = response.text
                logger.error(f"Erro ZapSign: {error_msg}")
                return {"error": error_msg, "success": False}

    except Exception as e:
        logger.error(f"Erro ao criar documento ZapSign: {e}")
        return {"error": str(e), "success": False}


async def verificar_status_documento(documento_token: str) -> dict:
    """
    Verifica o status de um documento na ZapSign.

    Args:
        documento_token: Token do documento

    Returns:
        dict com status do documento e signatários
    """
    if not ZAPSIGN_API_TOKEN:
        return {"error": "API Token não configurado", "success": False}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{get_zapsign_url()}/docs/{documento_token}/",
                headers={
                    "Authorization": f"Bearer {ZAPSIGN_API_TOKEN}"
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()

                resultado = {
                    "success": True,
                    "status": data.get("status"),
                    "nome": data.get("name"),
                    "criado_em": data.get("created_at"),
                    "atualizado_em": data.get("last_update_at"),
                    "signatarios": []
                }

                for signer in data.get("signers", []):
                    resultado["signatarios"].append({
                        "nome": signer.get("name"),
                        "email": signer.get("email"),
                        "status": signer.get("status"),
                        "assinado_em": signer.get("signed_at"),
                        "url_assinatura": signer.get("sign_url")
                    })

                # Verificar se todos assinaram
                todos_assinaram = all(
                    s["status"] == "signed"
                    for s in resultado["signatarios"]
                )
                resultado["todos_assinaram"] = todos_assinaram

                return resultado
            else:
                return {"error": response.text, "success": False}

    except Exception as e:
        logger.error(f"Erro ao verificar documento ZapSign: {e}")
        return {"error": str(e), "success": False}


async def obter_documento_assinado(documento_token: str) -> dict:
    """
    Obtém o documento assinado da ZapSign.

    Args:
        documento_token: Token do documento

    Returns:
        dict com URL do documento assinado
    """
    if not ZAPSIGN_API_TOKEN:
        return {"error": "API Token não configurado", "success": False}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{get_zapsign_url()}/docs/{documento_token}/",
                headers={
                    "Authorization": f"Bearer {ZAPSIGN_API_TOKEN}"
                },
                timeout=30.0
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("status") == "signed":
                    return {
                        "success": True,
                        "url_documento_assinado": data.get("signed_file"),
                        "url_documento_original": data.get("original_file")
                    }
                else:
                    return {
                        "success": False,
                        "error": "Documento ainda não foi assinado por todos",
                        "status": data.get("status")
                    }
            else:
                return {"error": response.text, "success": False}

    except Exception as e:
        logger.error(f"Erro ao obter documento assinado: {e}")
        return {"error": str(e), "success": False}


async def cancelar_documento(documento_token: str) -> dict:
    """
    Cancela um documento na ZapSign.

    Args:
        documento_token: Token do documento

    Returns:
        dict com resultado da operação
    """
    if not ZAPSIGN_API_TOKEN:
        return {"error": "API Token não configurado", "success": False}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{get_zapsign_url()}/docs/{documento_token}/",
                headers={
                    "Authorization": f"Bearer {ZAPSIGN_API_TOKEN}"
                },
                timeout=30.0
            )

            if response.status_code in [200, 204]:
                logger.info(f"Documento cancelado: {documento_token}")
                return {"success": True, "message": "Documento cancelado"}
            else:
                return {"error": response.text, "success": False}

    except Exception as e:
        logger.error(f"Erro ao cancelar documento: {e}")
        return {"error": str(e), "success": False}


def gerar_html_botoes_assinatura(
    url_zapsign: str = None,
    documento_nome: str = "documento"
) -> str:
    """
    Gera HTML com botões de assinatura para e-mail.

    Args:
        url_zapsign: URL de assinatura da ZapSign (opcional)
        documento_nome: Nome do documento

    Returns:
        HTML com os botões
    """
    botoes_html = f"""
    <div style="margin: 30px 0; text-align: center;">
        <p style="font-size: 16px; color: #333; margin-bottom: 20px;">
            <strong>Escolha como deseja assinar o {documento_nome}:</strong>
        </p>

        <table cellpadding="0" cellspacing="0" border="0" style="margin: 0 auto;">
            <tr>
    """

    # Botão ZapSign (se tiver URL)
    if url_zapsign:
        botoes_html += f"""
                <td style="padding: 10px;">
                    <a href="{url_zapsign}"
                       style="display: inline-block;
                              background-color: #8B1538;
                              color: white;
                              padding: 15px 30px;
                              text-decoration: none;
                              border-radius: 5px;
                              font-weight: bold;
                              font-size: 14px;">
                        Assinar Digitalmente (ZapSign)
                    </a>
                </td>
        """

    # Botão Gov.br
    botoes_html += f"""
                <td style="padding: 10px;">
                    <a href="{GOVBR_ASSINADOR_URL}"
                       style="display: inline-block;
                              background-color: #1351B4;
                              color: white;
                              padding: 15px 30px;
                              text-decoration: none;
                              border-radius: 5px;
                              font-weight: bold;
                              font-size: 14px;">
                        Assinar via Gov.br
                    </a>
                </td>
            </tr>
        </table>

        <p style="font-size: 12px; color: #666; margin-top: 20px;">
            <strong>Gov.br:</strong> Requer conta nível Prata ou Ouro.
            Faça upload do documento, assine e envie de volta pelo portal.
        </p>
    </div>
    """

    return botoes_html
