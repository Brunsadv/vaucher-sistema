"""
Rotas da API Vaucher e Álvares
Refatorado em 23/01/2026
"""

from .auth import router as auth_router
# from .datajud import router as datajud_router  # Substituído pelo Escavador
from .escavador import router as escavador_router
from .prazos import router as prazos_router
from .banners import router as banners_router
