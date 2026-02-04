"""
Rotas de Autenticação - Admin e Cliente
Refatorado em 23/01/2026
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode

from modules.config import logger, limiter
from modules.security import (
    hash_senha,
    verificar_senha,
    senha_precisa_atualizacao,
    gerar_token,
)
from modules.auth import verificar_admin, verificar_token
from modules.oauth import get_google_auth_url, verify_google_token, validate_oauth_state
from modules.database import (
    get_db,
    buscar_usuario_por_email,
    buscar_usuario_por_google_id,
    vincular_google_usuario,
    verificar_termos_aceitos,
    registrar_aceite_termos,
    listar_usuarios,
    criar_usuario,
    atualizar_usuario,
    deletar_usuario,
    registrar_auditoria,
)
from modules.models import (
    LoginRequest,
    LoginResponse,
    NovoUsuario,
    AtualizarUsuario,
    AlterarSenha,
)

router = APIRouter(prefix="/api", tags=["Autenticação"])


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
            conn = None
            cur = None
            try:
                novo_hash = hash_senha(data.senha)
                conn = get_db()
                if conn:
                    cur = conn.cursor()
                    cur.execute("UPDATE usuarios SET senha_hash = %s WHERE id = %s",
                                (novo_hash, usuario['id']))
                    conn.commit()
                    logger.info(f"Senha migrada para bcrypt: {usuario['email']}")
            except Exception as e:
                logger.error(f"Erro ao migrar senha: {e}")
            finally:
                if cur:
                    cur.close()
                if conn:
                    conn.close()

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


# ============================================
# AUTENTICAÇÃO GOOGLE - ADMIN
# ============================================

@router.get("/auth/google")
def google_login():
    """Inicia o fluxo de autenticação com Google para admin."""
    auth_url = get_google_auth_url(user_type="admin")
    if not auth_url:
        raise HTTPException(status_code=500, detail="Google OAuth não configurado")
    return {"auth_url": auth_url}


@router.get("/auth/google/callback")
async def google_callback(code: str = None, state: str = None, error: str = None):
    """Callback do Google OAuth para admin."""
    frontend_url = "https://appadmin.vaucherealvares.com/login"

    if error:
        return RedirectResponse(f"{frontend_url}?error=google_auth_failed")

    if not code or not state:
        return RedirectResponse(f"{frontend_url}?error=invalid_request")

    # Validar state (proteção CSRF)
    user_type = validate_oauth_state(state)
    if user_type != "admin":
        return RedirectResponse(f"{frontend_url}?error=invalid_state")

    # Verificar token do Google
    google_user = await verify_google_token(code, user_type="admin")
    if not google_user:
        return RedirectResponse(f"{frontend_url}?error=google_verification_failed")

    email = google_user["email"]
    google_id = google_user["google_id"]

    # Estratégia 1: Verificar se Google ID já está vinculado
    usuario = buscar_usuario_por_google_id(google_id)

    if not usuario:
        # Estratégia 2: Verificar se email existe no banco
        usuario = buscar_usuario_por_email(email)

        if usuario:
            # Vincular conta Google ao usuário existente
            vincular_google_usuario(usuario["id"], google_id)
            logger.info(f"Google vinculado ao usuário: {email}")
        else:
            # Usuário não encontrado - rejeitar
            params = urlencode({"error": "user_not_found", "email": email})
            return RedirectResponse(f"{frontend_url}?{params}")

    # Gerar token JWT
    token = gerar_token(usuario["id"], usuario["email"], usuario["is_admin"])
    termos_aceitos = verificar_termos_aceitos(usuario["id"])

    # Redirecionar para frontend com token
    params = urlencode({
        "token": token,
        "nome": usuario["nome"],
        "email": usuario["email"],
        "is_admin": str(usuario["is_admin"]).lower(),
        "termos_aceitos": str(termos_aceitos).lower(),
        "google_login": "true"
    })
    return RedirectResponse(f"{frontend_url}?{params}")


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

@router.get("/usuarios")
def listar_usuarios_api(usuario: dict = Depends(verificar_admin)):
    """Lista todos os usuários do sistema."""
    return listar_usuarios()


@router.post("/usuarios")
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


@router.put("/usuarios/{user_id}")
def atualizar_usuario_api(user_id: int, dados: AtualizarUsuario, usuario: dict = Depends(verificar_admin)):
    """Atualiza dados de um usuário."""
    if atualizar_usuario(user_id, dados.nome, dados.email, dados.is_admin, dados.ativo):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Usuário não encontrado")


@router.delete("/usuarios/{user_id}")
def deletar_usuario_api(user_id: int, usuario: dict = Depends(verificar_admin)):
    """Remove um usuário do sistema (soft delete - desativa)."""
    if user_id == usuario["id"]:
        raise HTTPException(status_code=400, detail="Você não pode remover seu próprio usuário")

    # Buscar dados antes para auditoria
    usuario_alvo = buscar_usuario_por_email(None)  # Precisamos buscar por ID
    conn = get_db()
    if conn:
        try:
            from psycopg2.extras import RealDictCursor
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("SELECT id, email, nome, is_admin FROM usuarios WHERE id = %s", (user_id,))
            usuario_alvo = cur.fetchone()
            cur.close()
            conn.close()
        except:
            pass

    if deletar_usuario(user_id):
        # Registrar auditoria
        registrar_auditoria(
            acao="DELETE",
            tabela="usuarios",
            registro_id=user_id,
            dados_anteriores=dict(usuario_alvo) if usuario_alvo else None,
            usuario_id=usuario.get("id"),
            usuario_email=usuario.get("email"),
            detalhes=f"Usuário {usuario_alvo.get('email') if usuario_alvo else user_id} desativado"
        )
        return {"success": True}
    raise HTTPException(status_code=404, detail="Usuário não encontrado")


@router.post("/usuarios/{user_id}/alterar-senha")
def alterar_senha_usuario(user_id: int, dados: AlterarSenha, usuario: dict = Depends(verificar_admin)):
    """Altera a senha de um usuário."""
    senha_hash = hash_senha(dados.nova_senha)
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")

    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET senha_hash = %s WHERE id = %s", (senha_hash, user_id))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        conn.commit()
        return {"success": True, "message": "Senha alterada com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao alterar senha: {e}")
        raise HTTPException(status_code=500, detail="Erro ao alterar senha")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


@router.post("/alterar-senha")
@limiter.limit("5/minute")
def alterar_minha_senha(request: Request, dados: AlterarSenha, usuario: dict = Depends(verificar_token)):
    """Permite ao usuário alterar sua própria senha."""
    usuario_db = buscar_usuario_por_email(usuario["email"])

    if not usuario_db or not verificar_senha(dados.senha_atual, usuario_db["senha_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    novo_hash = hash_senha(dados.nova_senha)
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")

    cur = None
    try:
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET senha_hash = %s WHERE id = %s", (novo_hash, usuario["id"]))
        conn.commit()
        return {"success": True, "message": "Senha alterada com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao alterar senha: {e}")
        raise HTTPException(status_code=500, detail="Erro ao alterar senha")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
