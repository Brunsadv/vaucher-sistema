"""
Funções de Autenticação para FastAPI
Criado em 23/01/2026

Este módulo centraliza as funções de verificação de token
para uso como dependências do FastAPI (Depends).
"""

from fastapi import HTTPException, Header
from modules.security import decodificar_token, decodificar_token_cliente
from modules.database import buscar_usuario_por_email


def verificar_token(authorization: str = Header(None)) -> dict:
    """
    Verifica se o token é válido e retorna o usuário.
    Usado como dependência do FastAPI: Depends(verificar_token)
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Token não fornecido")

    token = authorization.replace("Bearer ", "")

    usuario = decodificar_token(token)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    usuario_db = buscar_usuario_por_email(usuario["email"])
    if not usuario_db or not usuario_db.get("ativo", True):
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")

    return {
        "id": usuario_db["id"],
        "email": usuario_db["email"],
        "nome": usuario_db["nome"],
        "is_admin": usuario_db["is_admin"],
        "papel": usuario_db.get("papel", "admin")
    }


def verificar_admin(authorization: str = Header(None)) -> dict:
    """
    Verifica se o usuário é admin.
    Usado como dependência do FastAPI: Depends(verificar_admin)
    """
    usuario = verificar_token(authorization)
    if usuario.get("papel") != "admin" and not usuario.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores.")
    return usuario


def verificar_papel(*papeis_permitidos):
    """
    Factory de dependência que verifica se o papel do usuário está na lista permitida.
    Uso: Depends(verificar_papel("admin", "advogado"))
    """
    def dependency(authorization: str = Header(None)) -> dict:
        usuario = verificar_token(authorization)
        papel = usuario.get("papel", "admin")
        if papel not in papeis_permitidos:
            raise HTTPException(status_code=403, detail="Sem permissão para esta ação")
        return usuario
    return dependency


def verificar_nao_estagiario(authorization: str = Header(None)) -> dict:
    """
    Bloqueia estagiários em rotas de exclusão (DELETE).
    Todos os outros papéis podem deletar.
    """
    usuario = verificar_token(authorization)
    if usuario.get("papel") == "estagiario":
        raise HTTPException(status_code=403, detail="Estagiários não podem deletar registros")
    return usuario


def verificar_token_cliente(authorization: str = Header(None)) -> dict:
    """
    Verifica se o token de cliente é válido.
    Usado como dependência do FastAPI: Depends(verificar_token_cliente)
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Token não fornecido")

    token = authorization.replace("Bearer ", "")

    cliente = decodificar_token_cliente(token)
    if not cliente:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")

    return cliente
