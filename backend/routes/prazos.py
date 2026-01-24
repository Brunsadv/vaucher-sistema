"""
Rotas de Prazos Processuais
Refatorado em 23/01/2026
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime as dt

from modules.prazos import (
    criar_prazo,
    listar_prazos_processo,
    listar_prazos_pendentes,
    listar_todos_prazos,
    atualizar_prazo,
    concluir_prazo,
    cancelar_prazo,
    deletar_prazo,
    processar_andamentos_para_prazos,
    obter_resumo_prazos,
    calcular_data_prazo,
)
from routes.auth import verificar_admin

router = APIRouter(prefix="/api/admin", tags=["Prazos Processuais"])


# ============================================
# ROTAS DE PRAZOS
# ============================================

@router.get("/prazos")
async def listar_prazos_admin(
    status: str = None,
    admin=Depends(verificar_admin)
):
    """Lista todos os prazos, opcionalmente filtrados por status."""
    prazos = listar_todos_prazos(status)
    return {"prazos": prazos}


@router.get("/prazos/pendentes")
async def listar_prazos_pendentes_admin(
    dias: int = 30,
    admin=Depends(verificar_admin)
):
    """Lista prazos pendentes nos próximos X dias."""
    prazos = listar_prazos_pendentes(dias_limite=dias)
    return {"prazos": prazos}


@router.get("/prazos/resumo")
async def obter_resumo_prazos_admin(admin=Depends(verificar_admin)):
    """Retorna resumo estatístico dos prazos."""
    resumo = obter_resumo_prazos()
    return resumo


@router.get("/processos/{processo_id}/prazos")
async def listar_prazos_processo_admin(
    processo_id: int,
    admin=Depends(verificar_admin)
):
    """Lista prazos de um processo específico."""
    prazos = listar_prazos_processo(processo_id)
    return {"prazos": prazos}


@router.post("/processos/{processo_id}/prazos")
async def criar_prazo_admin(
    processo_id: int,
    dados: dict,
    admin=Depends(verificar_admin)
):
    """Cria um novo prazo manualmente."""
    data_inicio = dados.get("data_inicio")
    if isinstance(data_inicio, str):
        data_inicio = dt.strptime(data_inicio, "%Y-%m-%d").date()

    # Calcular data_fim se não fornecida
    data_fim = dados.get("data_fim")
    if data_fim:
        if isinstance(data_fim, str):
            data_fim = dt.strptime(data_fim, "%Y-%m-%d").date()
    else:
        dias = dados.get("dias", 15)
        dias_uteis = dados.get("dias_uteis", True)
        data_fim = calcular_data_prazo(data_inicio, dias, dias_uteis)

    prazo_id = criar_prazo(
        processo_id=processo_id,
        tipo=dados.get("tipo", "Manual"),
        descricao=dados.get("descricao", ""),
        data_inicio=data_inicio,
        data_fim=data_fim,
        dias_uteis=dados.get("dias_uteis", True),
        prioridade=dados.get("prioridade", "normal"),
        origem="manual",
        observacoes=dados.get("observacoes")
    )

    if not prazo_id:
        raise HTTPException(status_code=500, detail="Erro ao criar prazo")

    return {
        "sucesso": True,
        "id": prazo_id,
        "data_fim": data_fim.isoformat(),
        "mensagem": "Prazo criado com sucesso"
    }


@router.put("/prazos/{prazo_id}")
async def atualizar_prazo_admin(
    prazo_id: int,
    dados: dict,
    admin=Depends(verificar_admin)
):
    """Atualiza um prazo existente."""
    sucesso = atualizar_prazo(prazo_id, dados)
    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao atualizar prazo")

    return {"sucesso": True, "mensagem": "Prazo atualizado"}


@router.post("/prazos/{prazo_id}/concluir")
async def concluir_prazo_admin(
    prazo_id: int,
    admin=Depends(verificar_admin)
):
    """Marca um prazo como concluído."""
    usuario = admin.get("nome", "Admin")
    sucesso = concluir_prazo(prazo_id, usuario)

    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao concluir prazo")

    return {"sucesso": True, "mensagem": "Prazo marcado como concluído"}


@router.post("/prazos/{prazo_id}/cancelar")
async def cancelar_prazo_admin(
    prazo_id: int,
    dados: dict = None,
    admin=Depends(verificar_admin)
):
    """Cancela um prazo."""
    motivo = dados.get("motivo") if dados else None
    sucesso = cancelar_prazo(prazo_id, motivo)

    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao cancelar prazo")

    return {"sucesso": True, "mensagem": "Prazo cancelado"}


@router.delete("/prazos/{prazo_id}")
async def deletar_prazo_admin(
    prazo_id: int,
    admin=Depends(verificar_admin)
):
    """Deleta um prazo."""
    sucesso = deletar_prazo(prazo_id)

    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao deletar prazo")

    return {"sucesso": True, "mensagem": "Prazo excluído"}


@router.post("/processos/{processo_id}/gerar-prazos")
async def gerar_prazos_processo_admin(
    processo_id: int,
    admin=Depends(verificar_admin)
):
    """Processa andamentos de um processo e gera prazos automáticos."""
    resultado = processar_andamentos_para_prazos(processo_id)

    if "erro" in resultado:
        raise HTTPException(status_code=500, detail=resultado["erro"])

    return resultado


@router.get("/clientes/{cadastro_id}/prazos")
async def listar_prazos_cliente_admin(
    cadastro_id: str,
    admin=Depends(verificar_admin)
):
    """Lista prazos pendentes de um cliente específico."""
    prazos = listar_prazos_pendentes(cadastro_id=cadastro_id, dias_limite=365)
    return {"prazos": prazos}
