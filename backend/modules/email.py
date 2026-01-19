"""
Módulo de E-mail do Sistema Vaucher e Álvares
Migrado do main.py em 19/01/2026

Este arquivo contém funções para envio de e-mails via API do Resend.
"""

import httpx
from typing import List, Optional

from modules.config import RESEND_API_KEY, FROM_EMAIL, logger


async def enviar_email_resend(
    destinatario: str,
    assunto: str,
    corpo_html: str,
    anexos: Optional[List[dict]] = None
) -> bool:
    """
    Envia e-mail usando a API do Resend.

    Args:
        destinatario: E-mail do destinatário
        assunto: Assunto do e-mail
        corpo_html: Corpo do e-mail em HTML
        anexos: Lista de anexos (opcional)
            Cada anexo deve ser um dict com:
            - filename: nome do arquivo
            - content: conteúdo em base64

    Returns:
        bool: True se o e-mail foi enviado com sucesso, False caso contrário
    """
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY não configurada!")
        return False

    logger.info(f"Enviando e-mail via Resend para {destinatario}")

    payload = {
        "from": f"Vaucher e Álvares <{FROM_EMAIL}>",
        "to": [destinatario],
        "subject": assunto,
        "html": corpo_html
    }

    if anexos:
        payload["attachments"] = anexos

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30.0
            )

            logger.info(f"Resend response status: {response.status_code}")
            logger.info(f"Resend response body: {response.text}")

            if response.status_code == 200:
                logger.info(f"E-mail enviado com sucesso para {destinatario}")
                return True
            else:
                logger.error(f"Erro do Resend: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail: {e}")
        return False


async def enviar_email_boas_vindas(destinatario: str, nome: str, senha_temporaria: str) -> bool:
    """
    Envia e-mail de boas-vindas com credenciais de acesso.

    Args:
        destinatario: E-mail do cliente
        nome: Nome do cliente
        senha_temporaria: Senha temporária gerada

    Returns:
        bool: True se enviado com sucesso
    """
    assunto = "Bem-vindo(a) ao Portal Vaucher e Álvares"

    corpo_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2c3e50;">Bem-vindo(a), {nome}!</h2>

        <p>Seu cadastro foi realizado com sucesso em nosso escritório.</p>

        <p>Acesse o Portal do Cliente para acompanhar seus processos:</p>

        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p><strong>E-mail:</strong> {destinatario}</p>
            <p><strong>Senha temporária:</strong> {senha_temporaria}</p>
        </div>

        <p style="color: #e74c3c;"><strong>Importante:</strong> Por segurança, altere sua senha no primeiro acesso.</p>

        <p>Acesse: <a href="https://vaucher-sistema.onrender.com/cliente">Portal do Cliente</a></p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

        <p style="color: #666; font-size: 12px;">
            Vaucher e Álvares Sociedade de Advogados<br>
            OAB/MT 669 | CNPJ 21.336.697/0001-46<br>
            Rua Lima, n. 106, Jardim das Américas - Cuiabá/MT
        </p>
    </div>
    """

    return await enviar_email_resend(destinatario, assunto, corpo_html)


async def enviar_email_documentos(
    destinatario: str,
    nome: str,
    anexos: List[dict]
) -> bool:
    """
    Envia e-mail com documentos gerados anexados.

    Args:
        destinatario: E-mail do cliente
        nome: Nome do cliente
        anexos: Lista de anexos em formato base64

    Returns:
        bool: True se enviado com sucesso
    """
    assunto = "Seus documentos - Vaucher e Álvares"

    corpo_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2c3e50;">Olá, {nome}!</h2>

        <p>Seguem anexos os documentos solicitados.</p>

        <p>Por favor, revise os documentos e entre em contato conosco em caso de dúvidas.</p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

        <p style="color: #666; font-size: 12px;">
            Vaucher e Álvares Sociedade de Advogados<br>
            OAB/MT 669 | CNPJ 21.336.697/0001-46<br>
            Rua Lima, n. 106, Jardim das Américas - Cuiabá/MT
        </p>
    </div>
    """

    return await enviar_email_resend(destinatario, assunto, corpo_html, anexos)


async def enviar_email_nova_mensagem(
    destinatario: str,
    nome: str,
    remetente: str = "Vaucher e Álvares"
) -> bool:
    """
    Notifica o cliente sobre uma nova mensagem no portal.

    Args:
        destinatario: E-mail do cliente
        nome: Nome do cliente
        remetente: Quem enviou a mensagem

    Returns:
        bool: True se enviado com sucesso
    """
    assunto = "Nova mensagem no Portal - Vaucher e Álvares"

    corpo_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #2c3e50;">Olá, {nome}!</h2>

        <p>Você recebeu uma nova mensagem de <strong>{remetente}</strong>.</p>

        <p>Acesse o <a href="https://vaucher-sistema.onrender.com/cliente">Portal do Cliente</a> para visualizar.</p>

        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">

        <p style="color: #666; font-size: 12px;">
            Vaucher e Álvares Sociedade de Advogados<br>
            OAB/MT 669 | CNPJ 21.336.697/0001-46<br>
            Rua Lima, n. 106, Jardim das Américas - Cuiabá/MT
        </p>
    </div>
    """

    return await enviar_email_resend(destinatario, assunto, corpo_html)
