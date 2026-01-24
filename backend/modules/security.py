"""
Funções de Segurança do Sistema Vaucher e Álvares
Atualizado em 23/01/2026 - Implementação de bcrypt e JWT

Este arquivo contém funções de hash, tokens e templates de e-mail.
"""

import hashlib
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional
from modules.config import TOKEN_SECRET, LOGO_URL

# ============================================
# CONFIGURAÇÕES DE SEGURANÇA
# ============================================

# Tempo de expiração dos tokens
TOKEN_EXPIRATION_HOURS = 24  # Tokens de admin expiram em 24 horas
CLIENT_TOKEN_EXPIRATION_HOURS = 72  # Tokens de cliente expiram em 72 horas

# Algoritmo JWT
JWT_ALGORITHM = "HS256"

# Extensões permitidas para upload de arquivos
ALLOWED_FILE_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.xls', '.xlsx'}
MAX_FILE_SIZE_MB = 10

# ============================================
# FUNÇÕES DE HASH DE SENHA (BCRYPT)
# ============================================

def hash_senha(senha: str) -> str:
    """Cria hash da senha usando bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(senha.encode(), salt).decode()

def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    try:
        # Primeiro, tenta verificar com bcrypt (novo formato)
        if hash_armazenado.startswith('$2'):
            return bcrypt.checkpw(senha.encode(), hash_armazenado.encode())

        # Fallback para SHA-256 legado (migração gradual)
        salt_legado = "vaucher_alvares_2024"
        hash_legado = hashlib.sha256(f"{senha}{salt_legado}".encode()).hexdigest()
        return hash_legado == hash_armazenado
    except Exception:
        return False

def senha_precisa_atualizacao(hash_armazenado: str) -> bool:
    """Verifica se a senha usa hash legado e precisa ser atualizada."""
    return not hash_armazenado.startswith('$2')

# ============================================
# FUNÇÕES DE TOKEN JWT - USUÁRIOS (ADMIN)
# ============================================

def gerar_token(user_id: int, email: str, is_admin: bool) -> str:
    """Gera um token JWT com informações do usuário e expiração."""
    payload = {
        "user_id": user_id,
        "email": email,
        "is_admin": is_admin,
        "type": "admin",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, TOKEN_SECRET, algorithm=JWT_ALGORITHM)

def decodificar_token(token: str) -> Optional[dict]:
    """Decodifica e valida um token JWT."""
    try:
        payload = jwt.decode(token, TOKEN_SECRET, algorithms=[JWT_ALGORITHM])

        # Verifica se é um token de admin
        if payload.get("type") != "admin":
            return None

        return {
            "id": payload["user_id"],
            "email": payload["email"],
            "is_admin": payload["is_admin"]
        }
    except jwt.ExpiredSignatureError:
        # Token expirado
        return None
    except jwt.InvalidTokenError:
        # Token inválido
        return None

# ============================================
# FUNÇÕES DE TOKEN JWT - CLIENTES (PORTAL)
# ============================================

def gerar_token_cliente(cadastro_id: str, email: str) -> str:
    """Gera um token JWT específico para clientes."""
    payload = {
        "cadastro_id": cadastro_id,
        "email": email,
        "type": "cliente",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=CLIENT_TOKEN_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, TOKEN_SECRET, algorithm=JWT_ALGORITHM)

def decodificar_token_cliente(token: str) -> Optional[dict]:
    """Decodifica e valida um token JWT de cliente."""
    try:
        payload = jwt.decode(token, TOKEN_SECRET, algorithms=[JWT_ALGORITHM])

        # Verifica se é um token de cliente
        if payload.get("type") != "cliente":
            return None

        return {
            "cadastro_id": payload["cadastro_id"],
            "email": payload["email"],
            "tipo": "cliente"
        }
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

# ============================================
# VALIDAÇÃO DE ARQUIVOS
# ============================================

def validar_arquivo(filename: str, content_length: int = 0) -> tuple[bool, str]:
    """
    Valida um arquivo para upload.
    Retorna (válido, mensagem_erro).
    """
    import os

    if not filename:
        return False, "Nome do arquivo não fornecido"

    # Verifica extensão
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        return False, f"Extensão não permitida. Use: {', '.join(ALLOWED_FILE_EXTENSIONS)}"

    # Verifica tamanho (se fornecido)
    max_size = MAX_FILE_SIZE_MB * 1024 * 1024  # Converte para bytes
    if content_length > max_size:
        return False, f"Arquivo muito grande. Máximo: {MAX_FILE_SIZE_MB}MB"

    # Verifica caracteres perigosos no nome
    dangerous_chars = ['..', '/', '\\', '\x00']
    for char in dangerous_chars:
        if char in filename:
            return False, "Nome do arquivo contém caracteres inválidos"

    return True, ""

def sanitizar_nome_arquivo(filename: str) -> str:
    """Sanitiza o nome do arquivo para evitar path traversal."""
    import os
    import re

    # Remove path e mantém apenas o nome
    filename = os.path.basename(filename)

    # Remove caracteres especiais exceto ponto, hífen e underscore
    filename = re.sub(r'[^\w\-\.]', '_', filename)

    # Remove múltiplos underscores
    filename = re.sub(r'_+', '_', filename)

    return filename

# ============================================
# TEMPLATE DE E-MAIL
# ============================================

def criar_email_html(conteudo: str) -> str:
    """Cria o HTML do e-mail com logo e rodapé padrão."""
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; background-color: #f5f5f5; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <!-- Cabeçalho com Logo -->
            <div style="background-color: #ffffff; padding: 30px; text-align: center; border-bottom: 3px solid #8B1538;">
                <img src="{LOGO_URL}" alt="Vaucher e Álvares Advogados" style="max-width: 300px; height: auto;" />
            </div>

            <!-- Conteúdo -->
            <div style="padding: 30px;">
                {conteudo}
            </div>

            <!-- Rodapé -->
            <div style="background-color: #f8f8f8; padding: 20px; text-align: center; border-top: 1px solid #eee;">
                <p style="font-size: 12px; color: #666; margin: 0;">
                    <strong>Vaucher e Álvares Sociedade de Advogados</strong><br>
                    Rua Lima, nº 106, Bairro Jardim das Américas, Cuiabá-MT<br>
                    (65) 3025-1223 – email: atendimento@vaucherealvares.com
                </p>
            </div>
        </div>
    </body>
    </html>
    """
