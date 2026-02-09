"""
Configurações do Sistema Vaucher e Álvares
Migrado do main.py em 18/01/2026

Este arquivo contém todas as constantes e configurações do sistema.
"""

import os
import logging
from datetime import timezone

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# RATE LIMITER (Compartilhado)
# ============================================

from slowapi import Limiter
from slowapi.util import get_remote_address

# Instância compartilhada do rate limiter
limiter = Limiter(key_func=get_remote_address)

# ============================================
# FUSO HORÁRIO
# ============================================

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# Fuso horário de Cuiabá (usado em todo o sistema)
FUSO_CUIABA = ZoneInfo("America/Cuiaba")

def converter_para_cuiaba(dt) -> str:
    """Converte datetime para fuso horário de Cuiabá e retorna como ISO string."""
    if not dt:
        return None
    try:
        # Se o datetime não tem timezone, assume que é UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Converte para Cuiabá
        dt_cuiaba = dt.astimezone(FUSO_CUIABA)
        return dt_cuiaba.isoformat()
    except Exception as e:
        logger.warning(f"Erro ao converter timezone: {e}")
        return dt.isoformat() if dt else None

# ============================================
# DIRETÓRIOS
# ============================================

# BASE_DIR aponta para a pasta backend/ (pai da pasta modules/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELOS_DIR = os.path.join(BASE_DIR, "modelos")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
GERADOS_DIR = os.path.join(UPLOADS_DIR, "documentos_gerados")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ============================================
# VARIÁVEIS DE AMBIENTE
# ============================================

# Banco de dados
DATABASE_URL = os.getenv("DATABASE_URL")

# E-mail (Resend)
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")

# Segurança - OBRIGATÓRIOS (sem defaults para forçar configuração)
TOKEN_SECRET = os.getenv("TOKEN_SECRET")
ADMIN_INICIAL_SENHA = os.getenv("ADMIN_INICIAL_SENHA")


def validar_configuracao():
    """
    Valida que todas as variáveis obrigatórias estão configuradas.
    Deve ser chamada no startup da aplicação.
    Raises ValueError se alguma variável obrigatória não estiver configurada.
    """
    erros = []
    if not DATABASE_URL:
        erros.append("DATABASE_URL")
    if not TOKEN_SECRET:
        erros.append("TOKEN_SECRET")
    if not ADMIN_INICIAL_SENHA:
        erros.append("ADMIN_INICIAL_SENHA")

    if erros:
        raise ValueError(
            f"Variáveis de ambiente obrigatórias não configuradas: {', '.join(erros)}. "
            "Configure no arquivo .env ou nas variáveis de ambiente do servidor (Railway)."
        )

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI_ADMIN = os.getenv("GOOGLE_REDIRECT_URI_ADMIN", "https://vaucher-sistema-production.up.railway.app/api/auth/google/callback")
GOOGLE_REDIRECT_URI_CLIENTE = os.getenv("GOOGLE_REDIRECT_URI_CLIENTE", "https://vaucher-sistema-production.up.railway.app/api/cliente/auth/google/callback")

# Escavador API V2
ESCAVADOR_API_TOKEN = os.getenv("ESCAVADOR_API_TOKEN")
ESCAVADOR_API_URL = "https://api.escavador.com/api"
ESCAVADOR_CALLBACK_URL = os.getenv(
    "ESCAVADOR_CALLBACK_URL",
    "https://vaucher-sistema-production.up.railway.app/api/webhook/escavador"
)

# URL da logo para e-mails
LOGO_URL = "https://raw.githubusercontent.com/Brunsadv/vaucher-sistema/main/backend/static/Vaucher_e_Alvares-06.jpg"

# ============================================
# CORS - ORIGENS PERMITIDAS
# ============================================

ALLOWED_ORIGINS = [
    # Desenvolvimento local
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    # Landing Page (site principal)
    "https://vaucherealvares.com",
    "https://www.vaucherealvares.com",
    # Domínios de produção
    "https://cadastro.vaucherealvares.com",
    "https://painel.vaucherealvares.com",
    "https://portal.vaucherealvares.com",
    "https://appcliente.vaucherealvares.com",
    # Vercel
    "https://vaucher-cliente.vercel.app",
    "https://vaucher-admin.vercel.app",
    "https://vaucher-portal.vercel.app",
    "https://portal-cliente-five.vercel.app",
    "https://portal-cliente-git-main-brunsadvs-projects.vercel.app",
    # Portal Cliente V2 (novo design)
    "https://portal-cliente-v2-liard.vercel.app",
    # Admin V2 (novo painel administrativo)
    "https://appadmin.vaucherealvares.com",
    "https://admin-v2-brunsadvs-projects.vercel.app",
    "https://admin-v2-two.vercel.app",
]
