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


async def enviar_email_assinatura_digital(
    destinatario: str,
    nome: str,
    documentos: list,
    portal_url: str = "https://portal-cliente-vaucher.onrender.com"
) -> bool:
    """
    Envia e-mail com links para assinatura digital dos documentos.

    Args:
        destinatario: E-mail do cliente
        nome: Nome do cliente
        documentos: Lista de dicts com {tipo, nome, url_assinatura}
        portal_url: URL do portal do cliente

    Returns:
        bool: True se enviado com sucesso
    """
    assunto = "Documentos para Assinatura Digital - Vaucher e Álvares"

    logger.info(f"Gerando e-mail de assinatura para {destinatario} com documentos: {documentos}")

    # Gerar HTML dos botões de assinatura
    botoes_html = ""
    for doc in documentos:
        url = doc.get("url_assinatura")
        nome_doc = doc.get('nome', 'Documento')
        logger.info(f"Processando documento: {nome_doc}, URL: {url}")

        if url:
            botoes_html += f"""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #8B1538;">
                <p style="font-weight: bold; color: #333; margin: 0 0 15px 0; font-size: 16px;">
                    {nome_doc}
                </p>
                <a href="{url}"
                   style="display: inline-block; background-color: #8B1538; color: white;
                          padding: 12px 30px; text-decoration: none; border-radius: 5px;
                          font-weight: bold; font-size: 14px;">
                    ASSINAR DOCUMENTO (ZapSign)
                </a>
            </div>
            """
        else:
            # Se não tem URL do ZapSign, mostrar opção do portal
            botoes_html += f"""
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #8B1538;">
                <p style="font-weight: bold; color: #333; margin: 0 0 15px 0; font-size: 16px;">
                    {nome_doc}
                </p>
                <p style="color: #666; margin: 0 0 15px 0;">
                    Acesse o Portal do Cliente para assinar este documento.
                </p>
            </div>
            """

    corpo_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #8B1538; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 24px;">Vaucher e Alvares</h1>
            <p style="color: #f0f0f0; margin: 5px 0 0 0; font-size: 14px;">Sociedade de Advogados</p>
        </div>

        <div style="padding: 30px 20px;">
            <h2 style="color: #2c3e50; margin-top: 0;">Ola, {nome}!</h2>

            <p style="font-size: 16px; color: #333; line-height: 1.6;">
                Seus documentos estao prontos para assinatura digital.
                Clique nos botoes abaixo para assinar cada documento de forma rapida e segura.
            </p>

            {botoes_html}

            <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 25px 0;">
                <p style="margin: 0; color: #1565c0; font-size: 14px;">
                    <strong>Dica:</strong> Voce tambem pode acessar seus documentos pelo Portal do Cliente:
                </p>
                <p style="margin: 10px 0 0 0; text-align: center;">
                    <a href="{portal_url}"
                       style="display: inline-block; background-color: #1565c0; color: white;
                              padding: 10px 25px; text-decoration: none; border-radius: 5px;
                              font-size: 14px;">
                        Acessar Portal do Cliente
                    </a>
                </p>
            </div>

            <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 25px 0;">
                <p style="margin: 0; color: #e65100; font-size: 14px;">
                    <strong>Alternativa gratuita:</strong> Voce tambem pode assinar via
                    <a href="https://sso.acesso.gov.br/login?client_id=assinador.iti.br" style="color: #1565c0;">Gov.br</a>
                    (requer conta nivel Prata ou Ouro). Neste caso, baixe o documento,
                    assine pelo Gov.br e envie de volta pelo Portal.
                </p>
            </div>

            <p style="font-size: 14px; color: #666; margin-top: 30px;">
                Em caso de duvidas, entre em contato conosco.
            </p>
        </div>

        <hr style="border: none; border-top: 1px solid #eee; margin: 0;">

        <div style="padding: 20px; background-color: #f8f9fa;">
            <p style="color: #666; font-size: 12px; margin: 0; text-align: center;">
                Vaucher e Alvares Sociedade de Advogados<br>
                OAB/MT 669 | CNPJ 21.336.697/0001-46<br>
                Rua Lima, n. 106, Jardim das Americas - Cuiaba/MT<br>
                <a href="mailto:atendimento@vaucherealvares.com" style="color: #8B1538;">atendimento@vaucherealvares.com</a>
            </p>
        </div>
    </div>
    """

    return await enviar_email_resend(destinatario, assunto, corpo_html)
