"""
Rotas de Banners e Notícias
Refatorado em 23/01/2026
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional

from modules.config import logger
from modules.database import (
    listar_banners,
    buscar_banner,
    criar_banner,
    atualizar_banner,
    deletar_banner,
)
from modules.security import decodificar_token_cliente
from routes.auth import verificar_admin

router = APIRouter(tags=["Banners e Notícias"])


# ============================================
# MODELOS
# ============================================

class BannerModel(BaseModel):
    tipo: str = "info"  # info, warning, alert, success
    titulo: str
    conteudo: str
    link_url: Optional[str] = None
    link_texto: Optional[str] = None
    ativo: bool = True
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    ordem: int = 0


# ============================================
# ROTAS ADMIN
# ============================================

@router.get("/api/admin/banners")
async def listar_banners_admin(admin=Depends(verificar_admin)):
    """Lista todos os banners (admin)."""
    try:
        banners = listar_banners(apenas_ativos=False)
        return {"banners": banners}
    except Exception as e:
        logger.error(f"Erro ao listar banners: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/admin/banners/{banner_id}")
async def obter_banner_admin(banner_id: int, admin=Depends(verificar_admin)):
    """Obtém um banner específico (admin)."""
    banner = buscar_banner(banner_id)
    if not banner:
        raise HTTPException(status_code=404, detail="Banner não encontrado")
    return {"banner": banner}


@router.post("/api/admin/banners")
async def criar_banner_endpoint(banner: BannerModel, admin=Depends(verificar_admin)):
    """Cria um novo banner."""
    try:
        dados = banner.dict()
        dados["criado_por"] = admin.get("nome", "Admin")

        banner_id = criar_banner(dados)
        if not banner_id:
            raise HTTPException(status_code=500, detail="Erro ao criar banner")

        logger.info(f"Banner '{banner.titulo}' criado por {admin.get('nome')}")
        return {"sucesso": True, "id": banner_id, "mensagem": "Banner criado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar banner: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api/admin/banners/{banner_id}")
async def atualizar_banner_endpoint(banner_id: int, banner: BannerModel, admin=Depends(verificar_admin)):
    """Atualiza um banner existente."""
    try:
        banner_existente = buscar_banner(banner_id)
        if not banner_existente:
            raise HTTPException(status_code=404, detail="Banner não encontrado")

        dados = banner.dict()
        sucesso = atualizar_banner(banner_id, dados)

        if not sucesso:
            raise HTTPException(status_code=500, detail="Erro ao atualizar banner")

        logger.info(f"Banner {banner_id} atualizado por {admin.get('nome')}")
        return {"sucesso": True, "mensagem": "Banner atualizado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar banner: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/admin/banners/{banner_id}")
async def deletar_banner_endpoint(banner_id: int, admin=Depends(verificar_admin)):
    """Deleta um banner."""
    try:
        banner_existente = buscar_banner(banner_id)
        if not banner_existente:
            raise HTTPException(status_code=404, detail="Banner não encontrado")

        sucesso = deletar_banner(banner_id)
        if not sucesso:
            raise HTTPException(status_code=500, detail="Erro ao deletar banner")

        logger.info(f"Banner {banner_id} deletado por {admin.get('nome')}")
        return {"sucesso": True, "mensagem": "Banner deletado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar banner: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ROTAS CLIENTE
# ============================================

@router.get("/api/cliente/banners")
async def listar_banners_cliente(authorization: str = Header(None)):
    """Lista banners ativos para o portal do cliente."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token não fornecido")

    token = authorization.replace("Bearer ", "")
    cliente = decodificar_token_cliente(token)
    if not cliente:
        raise HTTPException(status_code=401, detail="Token inválido")

    try:
        banners = listar_banners(apenas_ativos=True)
        return {"banners": banners}
    except Exception as e:
        logger.error(f"Erro ao listar banners para cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))
