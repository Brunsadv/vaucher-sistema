"""
Módulo de Auditoria - Sistema Vaucher e Álvares
Criado em 09/02/2026

Helper para registrar ações de forma consistente em todas as rotas.
Usa a função registrar_auditoria() de database.py.
"""

from fastapi import Request
from modules.database import registrar_auditoria
from modules.config import logger


def auditar(
    request: Request,
    usuario: dict,
    acao: str,
    tabela: str = None,
    registro_id=None,
    dados_anteriores: dict = None,
    dados_novos: dict = None,
    detalhes: str = None
):
    """
    Registra uma ação no log de auditoria com dados do request e do usuário.

    Args:
        request: FastAPI Request object
        usuario: Dict do usuário autenticado (de verificar_token/verificar_admin)
        acao: Tipo de ação (CREATE, UPDATE, DELETE, LOGIN, etc)
        tabela: Nome da tabela afetada
        registro_id: ID do registro afetado
        dados_anteriores: Estado anterior (para UPDATE/DELETE)
        dados_novos: Novo estado (para CREATE/UPDATE)
        detalhes: Informações adicionais
    """
    try:
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")

        registrar_auditoria(
            acao=acao,
            tabela=tabela,
            registro_id=registro_id,
            dados_anteriores=dados_anteriores,
            dados_novos=dados_novos,
            usuario_id=usuario.get("id"),
            usuario_email=usuario.get("email"),
            ip_address=ip,
            user_agent=user_agent,
            detalhes=detalhes
        )
    except Exception as e:
        logger.error(f"Erro ao registrar auditoria: {e}")
