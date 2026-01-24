"""
Rotas de Autenticação - Admin e Cliente
Refatorado em 23/01/2026
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from modules.config import logger
from modules.security import (
    hash_senha,
    verificar_senha,
    senha_precisa_atualizacao,
    gerar_token,
)
from modules.auth import verificar_admin
from modules.database import (
    get_db,
    buscar_usuario_por_email,
    verificar_termos_aceitos,
    registrar_aceite_termos,
    listar_usuarios,
    criar_usuario,
    atualizar_usuario,
    deletar_usuario,
)
from modules.models import (
    LoginRequest,
    LoginResponse,
    NovoUsuario,
    AtualizarUsuario,
    AlterarSenha,
)

router = APIRouter(prefix="/api", tags=["Autenticação"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


# ============================================
# ROTAS DE AUTENTICAÇÃO ADMIN
# ============================================

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
def login(request: Request, data: LoginRequest):
    """Autenticação do painel administrativo."""
    usuario = buscar_usuario_por_email(data.email)

    if usuario and verificar_senha(data.senha, usuario['senha_hash']):
        # Migra senha legada para bcrypt se necessário
        if senha_precisa_atualizacao(usuario['senha_hash']):
            try:
                novo_hash = hash_senha(data.senha)
                conn = get_db()
                if conn:
                    cur = conn.cursor()
                    cur.execute("UPDATE usuarios SET senha_hash = %s WHERE id = %s",
                                (novo_hash, usuario['id']))
                    conn.commit()
                    cur.close()
                    conn.close()
                    logger.info(f"Senha migrada para bcrypt: {usuario['email']}")
            except Exception as e:
                logger.error(f"Erro ao migrar senha: {e}")

        token = gerar_token(usuario["id"], usuario["email"], usuario["is_admin"])
        termos_aceitos = verificar_termos_aceitos(usuario["id"])
        return LoginResponse(
            success=True,
            token=token,
            nome=usuario['nome'],
            is_admin=usuario['is_admin'],
            termos_aceitos=termos_aceitos
        )

    return LoginResponse(success=False, message="E-mail ou senha incorretos")


@router.post("/logout")
def logout():
    """Encerra a sessão do usuário."""
    return {"success": True}


@router.post("/aceitar-termos")
def aceitar_termos(usuario: dict = Depends(verificar_admin)):
    """Registra o aceite dos termos de uso pelo usuário."""
    if registrar_aceite_termos(usuario["id"]):
        return {"success": True, "message": "Termos aceitos com sucesso"}
    raise HTTPException(status_code=500, detail="Erro ao registrar aceite dos termos")


@router.get("/verificar-termos")
def verificar_termos(usuario: dict = Depends(verificar_admin)):
    """Verifica se o usuário já aceitou os termos de uso."""
    aceitos = verificar_termos_aceitos(usuario["id"])
    return {"termos_aceitos": aceitos}


# ============================================
# GERENCIAMENTO DE USUÁRIOS (APENAS ADMIN)
# ============================================

@router.get("/admin/usuarios")
def listar_usuarios_api(usuario: dict = Depends(verificar_admin)):
    """Lista todos os usuários do sistema."""
    return listar_usuarios()


@router.post("/admin/usuarios")
def criar_usuario_api(dados: NovoUsuario, usuario: dict = Depends(verificar_admin)):
    """Cria um novo usuário."""
    existente = buscar_usuario_por_email(dados.email)
    if existente:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    senha_hash = hash_senha(dados.senha)
    novo_id = criar_usuario(dados.nome, dados.email, senha_hash, dados.is_admin)

    if novo_id:
        return {"success": True, "id": novo_id}
    raise HTTPException(status_code=500, detail="Erro ao criar usuário")


@router.put("/admin/usuarios/{user_id}")
def atualizar_usuario_api(user_id: int, dados: AtualizarUsuario, usuario: dict = Depends(verificar_admin)):
    """Atualiza dados de um usuário."""
    if atualizar_usuario(user_id, dados.nome, dados.email, dados.is_admin, dados.ativo):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Usuário não encontrado")


@router.delete("/admin/usuarios/{user_id}")
def deletar_usuario_api(user_id: int, usuario: dict = Depends(verificar_admin)):
    """Remove um usuário do sistema."""
    if user_id == usuario["id"]:
        raise HTTPException(status_code=400, detail="Você não pode remover seu próprio usuário")

    if deletar_usuario(user_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Usuário não encontrado")


@router.post("/admin/usuarios/{user_id}/alterar-senha")
def alterar_senha_usuario(user_id: int, dados: AlterarSenha, usuario: dict = Depends(verificar_admin)):
    """Altera a senha de um usuário."""
    senha_hash = hash_senha(dados.nova_senha)
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")

    try:
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET senha_hash = %s WHERE id = %s", (senha_hash, user_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "message": "Senha alterada com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao alterar senha: {e}")
        raise HTTPException(status_code=500, detail="Erro ao alterar senha")
