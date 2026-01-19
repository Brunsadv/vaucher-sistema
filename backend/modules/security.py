"""
Funções de Segurança do Sistema Vaucher e Álvares
Migrado do main.py em 19/01/2026

Este arquivo contém funções de hash, tokens e templates de e-mail.
"""

import hashlib
import base64
from modules.config import TOKEN_SECRET, LOGO_URL

# ============================================
# FUNÇÕES DE HASH DE SENHA
# ============================================

def hash_senha(senha: str) -> str:
    """Cria hash da senha usando SHA-256 com salt."""
    salt = "vaucher_alvares_2024"
    return hashlib.sha256(f"{senha}{salt}".encode()).hexdigest()

def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    return hash_senha(senha) == hash_armazenado

# ============================================
# FUNÇÕES DE TOKEN - USUÁRIOS (ADMIN)
# ============================================

def gerar_token(user_id: int, email: str, is_admin: bool) -> str:
    """Gera um token que contém informações do usuário."""
    payload = f"{user_id}:{email}:{is_admin}"
    signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
    token_data = base64.b64encode(f"{payload}:{signature}".encode()).decode()
    return token_data

def decodificar_token(token: str) -> dict:
    """Decodifica e valida um token."""
    try:
        decoded = base64.b64decode(token.encode()).decode()
        parts = decoded.rsplit(":", 1)
        if len(parts) != 2:
            return None

        payload, signature = parts

        expected_signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
        if signature != expected_signature:
            return None

        user_id, email, is_admin = payload.split(":")
        return {
            "id": int(user_id),
            "email": email,
            "is_admin": is_admin == "True"
        }
    except Exception:
        return None

# ============================================
# FUNÇÕES DE TOKEN - CLIENTES (PORTAL)
# ============================================

def gerar_token_cliente(cadastro_id: str, email: str) -> str:
    """Gera um token específico para clientes."""
    payload = f"cliente:{cadastro_id}:{email}"
    signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
    token_data = base64.b64encode(f"{payload}:{signature}".encode()).decode()
    return token_data

def decodificar_token_cliente(token: str) -> dict:
    """Decodifica e valida um token de cliente."""
    try:
        decoded = base64.b64decode(token.encode()).decode()
        parts = decoded.rsplit(":", 1)
        if len(parts) != 2:
            return None

        payload, signature = parts

        expected_signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
        if signature != expected_signature:
            return None

        tipo, cadastro_id, email = payload.split(":")
        if tipo != "cliente":
            return None

        return {
            "cadastro_id": cadastro_id,
            "email": email,
            "tipo": "cliente"
        }
    except Exception:
        return None

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
