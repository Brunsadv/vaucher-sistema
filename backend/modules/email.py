"""
Módulo de E-mail do Sistema Vaucher e Álvares
Migrado do main.py em 19/01/2026
Atualizado em 22/01/2026 - Novos templates e URLs

Este arquivo contém funções para envio de e-mails via API do Resend.
"""

import httpx
from typing import List, Optional

from modules.config import RESEND_API_KEY, FROM_EMAIL, logger

# URLs do sistema
PORTAL_URL = "https://appcliente.vaucherealvares.com"
CADASTRO_URL = "https://cadastro.vaucherealvares.com"
SITE_URL = "https://vaucherealvares.com"

# Logo do escritório (GitHub raw)
LOGO_URL = "https://raw.githubusercontent.com/Brunsadv/vaucher-sistema/main/backend/static/Vaucher_e_Alvares-06.jpg"


def get_email_header() -> str:
    """Retorna o cabeçalho padrão dos e-mails."""
    return f"""
    <div style="background: linear-gradient(135deg, #8B1538 0%, #6B0F2B 100%); padding: 30px 20px; text-align: center;">
        <img src="{LOGO_URL}" alt="Vaucher e Álvares" style="height: 60px; width: auto; margin-bottom: 10px;">
        <h1 style="color: white; margin: 0; font-size: 22px; font-weight: 600;">Vaucher e Álvares</h1>
        <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0; font-size: 13px;">Sociedade de Advogados</p>
    </div>
    """


def get_email_footer() -> str:
    """Retorna o rodapé padrão dos e-mails."""
    return f"""
    <div style="padding: 25px 20px; background-color: #f8f9fa; border-top: 1px solid #e9ecef;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td style="text-align: center;">
                    <p style="color: #6c757d; font-size: 13px; margin: 0 0 10px 0; line-height: 1.5;">
                        <strong>Vaucher e Álvares Sociedade de Advogados</strong><br>
                        OAB/MT 669 | CNPJ 21.336.697/0001-46
                    </p>
                    <p style="color: #868e96; font-size: 12px; margin: 0 0 15px 0;">
                        Rua Lima, nº 106, Jardim das Américas<br>
                        Cuiabá - MT | CEP 78060-760
                    </p>
                    <p style="margin: 0;">
                        <a href="tel:+556530251223" style="color: #8B1538; text-decoration: none; font-size: 12px; margin-right: 15px;">(65) 3025-1223</a>
                        <a href="mailto:atendimento@vaucherealvares.com" style="color: #8B1538; text-decoration: none; font-size: 12px;">atendimento@vaucherealvares.com</a>
                    </p>
                </td>
            </tr>
        </table>
    </div>
    <div style="padding: 15px 20px; background-color: #1a1a2e; text-align: center;">
        <a href="{PORTAL_URL}" style="color: rgba(255,255,255,0.7); text-decoration: none; font-size: 11px; margin-right: 20px;">Portal do Cliente</a>
        <a href="{SITE_URL}" style="color: rgba(255,255,255,0.7); text-decoration: none; font-size: 11px;">Site Institucional</a>
    </div>
    """


def get_button(text: str, url: str, color: str = "#8B1538") -> str:
    """Retorna um botão estilizado para e-mail."""
    return f"""
    <a href="{url}" style="display: inline-block; background-color: {color}; color: white;
       padding: 14px 32px; text-decoration: none; border-radius: 8px;
       font-weight: 600; font-size: 14px; text-align: center;">
        {text}
    </a>
    """


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
    assunto = "Bem-vindo(a) ao Portal do Cliente - Vaucher e Álvares"

    corpo_html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        {get_email_header()}

        <div style="padding: 40px 30px;">
            <h2 style="color: #1a1a2e; margin: 0 0 20px 0; font-size: 24px; font-weight: 600;">
                Olá, {nome}!
            </h2>

            <p style="color: #4a5568; font-size: 16px; line-height: 1.6; margin: 0 0 25px 0;">
                Seja bem-vindo(a) ao nosso escritório! Seu cadastro foi realizado com sucesso e você já pode acessar o <strong>Portal do Cliente</strong>.
            </p>

            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 25px; border-radius: 12px; margin: 25px 0; border-left: 4px solid #8B1538;">
                <p style="margin: 0 0 10px 0; color: #6c757d; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">Suas credenciais de acesso</p>
                <p style="margin: 0 0 8px 0; color: #1a1a2e; font-size: 15px;">
                    <strong>E-mail:</strong> {destinatario}
                </p>
                <p style="margin: 0; color: #1a1a2e; font-size: 15px;">
                    <strong>Senha temporária:</strong> <code style="background: #fff; padding: 4px 8px; border-radius: 4px; font-family: monospace;">{senha_temporaria}</code>
                </p>
            </div>

            <div style="background-color: #fff3cd; padding: 15px 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #ffc107;">
                <p style="margin: 0; color: #856404; font-size: 14px;">
                    <strong>Importante:</strong> Por segurança, você deverá alterar sua senha no primeiro acesso ao portal.
                </p>
            </div>

            <div style="text-align: center; margin: 35px 0;">
                {get_button("Acessar Portal do Cliente", PORTAL_URL)}
            </div>

            <p style="color: #6c757d; font-size: 14px; line-height: 1.6; margin: 25px 0 0 0;">
                Pelo portal você poderá:
            </p>
            <ul style="color: #4a5568; font-size: 14px; line-height: 1.8; margin: 10px 0 0 0; padding-left: 20px;">
                <li>Acompanhar seus processos em tempo real</li>
                <li>Visualizar e baixar documentos</li>
                <li>Enviar mensagens diretamente para sua equipe jurídica</li>
                <li>Acompanhar honorários e parcelas</li>
            </ul>
        </div>

        {get_email_footer()}
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
    assunto = "Seus Documentos - Vaucher e Álvares"

    # Lista de documentos anexados
    docs_lista = ""
    for anexo in anexos:
        docs_lista += f'<li style="margin-bottom: 8px;">{anexo.get("filename", "Documento")}</li>'

    corpo_html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        {get_email_header()}

        <div style="padding: 40px 30px;">
            <h2 style="color: #1a1a2e; margin: 0 0 20px 0; font-size: 24px; font-weight: 600;">
                Olá, {nome}!
            </h2>

            <p style="color: #4a5568; font-size: 16px; line-height: 1.6; margin: 0 0 25px 0;">
                Seguem em anexo os documentos solicitados. Por favor, revise-os com atenção e entre em contato conosco caso tenha alguma dúvida.
            </p>

            <div style="background-color: #f8f9fa; padding: 20px 25px; border-radius: 12px; margin: 25px 0;">
                <p style="margin: 0 0 15px 0; color: #6c757d; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">
                    Documentos anexados
                </p>
                <ul style="color: #1a1a2e; font-size: 15px; line-height: 1.6; margin: 0; padding-left: 20px;">
                    {docs_lista}
                </ul>
            </div>

            <div style="background-color: #e8f4fd; padding: 15px 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #2196F3;">
                <p style="margin: 0; color: #1565c0; font-size: 14px;">
                    <strong>Dica:</strong> Você também pode acessar todos os seus documentos pelo Portal do Cliente.
                </p>
            </div>

            <div style="text-align: center; margin: 35px 0;">
                {get_button("Acessar Portal do Cliente", PORTAL_URL)}
            </div>
        </div>

        {get_email_footer()}
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
    assunto = "Nova Mensagem no Portal - Vaucher e Álvares"

    corpo_html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        {get_email_header()}

        <div style="padding: 40px 30px;">
            <h2 style="color: #1a1a2e; margin: 0 0 20px 0; font-size: 24px; font-weight: 600;">
                Olá, {nome}!
            </h2>

            <p style="color: #4a5568; font-size: 16px; line-height: 1.6; margin: 0 0 25px 0;">
                Você recebeu uma nova mensagem de <strong style="color: #8B1538;">{remetente}</strong> no Portal do Cliente.
            </p>

            <div style="background-color: #f8f9fa; padding: 25px; border-radius: 12px; margin: 25px 0; text-align: center;">
                <div style="width: 60px; height: 60px; background-color: #8B1538; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
                    <span style="font-size: 24px; color: white;">✉️</span>
                </div>
                <p style="margin: 0; color: #6c757d; font-size: 14px;">
                    Acesse o portal para visualizar a mensagem completa e responder.
                </p>
            </div>

            <div style="text-align: center; margin: 35px 0;">
                {get_button("Ver Mensagem", f"{PORTAL_URL}/portal/mensagens")}
            </div>
        </div>

        {get_email_footer()}
    </div>
    """

    return await enviar_email_resend(destinatario, assunto, corpo_html)


async def enviar_email_assinatura_digital(
    destinatario: str,
    nome: str,
    documentos: list,
    anexos: Optional[List[dict]] = None,
    portal_url: str = PORTAL_URL
) -> bool:
    """
    Envia e-mail com links para assinatura digital dos documentos.

    Args:
        destinatario: E-mail do cliente
        nome: Nome do cliente
        documentos: Lista de dicts com {tipo, nome, url_assinatura}
        anexos: Lista de anexos em base64 (opcional)
        portal_url: URL do portal do cliente

    Returns:
        bool: True se enviado com sucesso
    """
    assunto = "Documentos para Assinatura Digital - Vaucher e Álvares"

    logger.info(f"Gerando e-mail de assinatura para {destinatario} com documentos: {documentos}")
    logger.info(f"Anexos: {len(anexos) if anexos else 0}")

    # Gerar HTML dos botões de assinatura
    botoes_html = ""
    for doc in documentos:
        url_zapsign = doc.get("url_assinatura")
        nome_doc = doc.get('nome', 'Documento')
        logger.info(f"Processando documento: {nome_doc}, URL ZapSign: {url_zapsign}")

        botoes_html += f"""
        <div style="background-color: #f8f9fa; padding: 20px 25px; border-radius: 12px; margin: 15px 0; border-left: 4px solid #8B1538;">
            <p style="font-weight: 600; color: #1a1a2e; margin: 0 0 15px 0; font-size: 16px;">
                📄 {nome_doc}
            </p>
            <p style="color: #6c757d; margin: 0 0 15px 0; font-size: 14px;">
                Escolha uma das opções abaixo para assinar:
            </p>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        """

        # Botão ZapSign (se tiver URL)
        if url_zapsign:
            botoes_html += f"""
                <a href="{url_zapsign}"
                   style="display: inline-block; background-color: #8B1538; color: white;
                          padding: 12px 24px; text-decoration: none; border-radius: 8px;
                          font-weight: 600; font-size: 13px; margin-right: 10px;">
                    ✍️ Assinar via ZapSign
                </a>
            """

        # Botão Gov.br (sempre)
        botoes_html += f"""
                <a href="https://assinador.iti.br"
                   style="display: inline-block; background-color: #1351B4; color: white;
                          padding: 12px 24px; text-decoration: none; border-radius: 8px;
                          font-weight: 600; font-size: 13px;">
                    🏛️ Assinar via Gov.br
                </a>
            </div>
        </div>
        """

    corpo_html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        {get_email_header()}

        <div style="padding: 40px 30px;">
            <h2 style="color: #1a1a2e; margin: 0 0 20px 0; font-size: 24px; font-weight: 600;">
                Olá, {nome}!
            </h2>

            <p style="color: #4a5568; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
                Seus documentos estão prontos para assinatura digital.
            </p>

            <p style="color: #6c757d; font-size: 14px; line-height: 1.6; margin: 0 0 25px 0;">
                Você pode assinar de duas formas: via <strong>ZapSign</strong> (mais rápido e prático) ou via <strong>Gov.br</strong> (gratuito, requer conta nível Prata ou Ouro).
            </p>

            <div style="background-color: #d4edda; padding: 15px 20px; border-radius: 8px; margin: 0 0 25px 0; border-left: 4px solid #28a745;">
                <p style="margin: 0; color: #155724; font-size: 14px;">
                    <strong>✓ Os documentos também estão anexados</strong> neste e-mail para sua conveniência.
                </p>
            </div>

            {botoes_html}

            <div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; margin: 25px 0;">
                <p style="margin: 0 0 10px 0; color: #856404; font-size: 14px; font-weight: 600;">
                    📝 Instruções para Gov.br:
                </p>
                <ol style="margin: 0; padding-left: 20px; color: #856404; font-size: 13px; line-height: 1.6;">
                    <li>Baixe o documento anexo neste e-mail</li>
                    <li>Acesse o assinador Gov.br</li>
                    <li>Faça upload do documento e assine</li>
                    <li>Envie o documento assinado pelo Portal do Cliente</li>
                </ol>
            </div>

            <div style="background-color: #e8f4fd; padding: 20px; border-radius: 8px; margin: 25px 0; text-align: center;">
                <p style="margin: 0 0 15px 0; color: #1565c0; font-size: 14px;">
                    <strong>Portal do Cliente:</strong> Acesse seus documentos a qualquer momento
                </p>
                {get_button("Acessar Portal", portal_url, "#1565c0")}
            </div>

            <p style="color: #6c757d; font-size: 14px; line-height: 1.6; margin: 25px 0 0 0;">
                Em caso de dúvidas, entre em contato conosco pelo telefone <strong>(65) 3025-1223</strong> ou responda este e-mail.
            </p>
        </div>

        {get_email_footer()}
    </div>
    """

    return await enviar_email_resend(destinatario, assunto, corpo_html, anexos)


async def enviar_email_atualizacao_solicitada(
    destinatario: str,
    nome: str,
    motivo: str = ""
) -> bool:
    """
    Notifica o cliente que foi solicitada uma atualização de dados.

    Args:
        destinatario: E-mail do cliente
        nome: Nome do cliente
        motivo: Motivo da solicitação (opcional)

    Returns:
        bool: True se enviado com sucesso
    """
    assunto = "Solicitação de Atualização de Dados - Vaucher e Álvares"

    motivo_html = ""
    if motivo:
        motivo_html = f"""
        <div style="background-color: #f8f9fa; padding: 20px 25px; border-radius: 12px; margin: 25px 0; border-left: 4px solid #8B1538;">
            <p style="margin: 0 0 10px 0; color: #6c757d; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">
                Motivo da solicitação
            </p>
            <p style="margin: 0; color: #1a1a2e; font-size: 15px; line-height: 1.6;">
                {motivo}
            </p>
        </div>
        """

    corpo_html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        {get_email_header()}

        <div style="padding: 40px 30px;">
            <h2 style="color: #1a1a2e; margin: 0 0 20px 0; font-size: 24px; font-weight: 600;">
                Olá, {nome}!
            </h2>

            <p style="color: #4a5568; font-size: 16px; line-height: 1.6; margin: 0 0 25px 0;">
                Precisamos que você atualize seus dados cadastrais. Por favor, acesse o Portal do Cliente para realizar a atualização.
            </p>

            {motivo_html}

            <div style="text-align: center; margin: 35px 0;">
                {get_button("Atualizar Meus Dados", f"{PORTAL_URL}/portal/dados")}
            </div>

            <p style="color: #6c757d; font-size: 14px; line-height: 1.6; margin: 25px 0 0 0;">
                Se você tiver alguma dúvida, entre em contato conosco.
            </p>
        </div>

        {get_email_footer()}
    </div>
    """

    return await enviar_email_resend(destinatario, assunto, corpo_html)


async def enviar_email_parcela_vencendo(
    destinatario: str,
    nome: str,
    valor: float,
    vencimento: str,
    contrato_descricao: str = "Honorários Advocatícios"
) -> bool:
    """
    Notifica o cliente sobre parcela próxima do vencimento.

    Args:
        destinatario: E-mail do cliente
        nome: Nome do cliente
        valor: Valor da parcela
        vencimento: Data de vencimento
        contrato_descricao: Descrição do contrato

    Returns:
        bool: True se enviado com sucesso
    """
    assunto = "Lembrete de Parcela - Vaucher e Álvares"

    corpo_html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #ffffff;">
        {get_email_header()}

        <div style="padding: 40px 30px;">
            <h2 style="color: #1a1a2e; margin: 0 0 20px 0; font-size: 24px; font-weight: 600;">
                Olá, {nome}!
            </h2>

            <p style="color: #4a5568; font-size: 16px; line-height: 1.6; margin: 0 0 25px 0;">
                Este é um lembrete sobre sua próxima parcela de <strong>{contrato_descricao}</strong>.
            </p>

            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 25px; border-radius: 12px; margin: 25px 0; text-align: center;">
                <p style="margin: 0 0 10px 0; color: #6c757d; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">
                    Valor da Parcela
                </p>
                <p style="margin: 0 0 20px 0; color: #8B1538; font-size: 32px; font-weight: 700;">
                    R$ {valor:,.2f}
                </p>
                <p style="margin: 0; color: #1a1a2e; font-size: 15px;">
                    <strong>Vencimento:</strong> {vencimento}
                </p>
            </div>

            <div style="text-align: center; margin: 35px 0;">
                {get_button("Ver Detalhes no Portal", f"{PORTAL_URL}/portal/honorarios")}
            </div>

            <p style="color: #6c757d; font-size: 14px; line-height: 1.6; margin: 25px 0 0 0;">
                Após o pagamento, você pode enviar o comprovante pelo Portal do Cliente para agilizar a baixa.
            </p>
        </div>

        {get_email_footer()}
    </div>
    """

    return await enviar_email_resend(destinatario, assunto, corpo_html)
