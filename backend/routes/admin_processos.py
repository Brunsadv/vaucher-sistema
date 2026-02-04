"""
Rotas Admin - Processos, Andamentos, Contratos
Refatorado em 24/01/2026
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from modules.config import logger
from modules.auth import verificar_admin
from modules.email import enviar_email_resend
from modules.database import (
    get_db,
    buscar_cadastro,
    # Processos
    criar_processo,
    listar_processos,
    buscar_processo,
    atualizar_processo,
    deletar_processo,
    # Andamentos de processo
    criar_andamento_processo,
    listar_andamentos_processo,
    deletar_andamento_processo,
    # Andamentos legacy
    listar_andamentos,
    criar_andamento,
    deletar_andamento,
    # Contratos
    listar_contratos,
    buscar_contrato,
    criar_contrato_honorarios,
    atualizar_contrato,
    deletar_contrato,
    # Parcelas
    atualizar_parcela,
    marcar_parcela_paga,
    # Comprovantes
    listar_comprovantes_pendentes,
    aprovar_comprovante,
    rejeitar_comprovante,
    # Mensagens
    listar_mensagens,
    criar_mensagem,
    marcar_mensagens_lidas,
    contar_mensagens_nao_lidas,
    # Auditoria
    registrar_auditoria,
)

router = APIRouter(prefix="/api/admin", tags=["Admin - Processos"])


# ============================================
# MODELOS
# ============================================

class AndamentoModel(BaseModel):
    data: str
    descricao: str
    visivel_cliente: bool = True


class MensagemEnvio(BaseModel):
    texto: str


# ============================================
# PROCESSOS (MÚLTIPLOS POR CLIENTE)
# ============================================

@router.get("/clientes/{cadastro_id}/processos")
async def admin_listar_processos(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista todos os processos de um cliente."""
    processos = listar_processos(cadastro_id)
    return {"processos": processos}


@router.post("/clientes/{cadastro_id}/processos")
async def admin_criar_processo(
    cadastro_id: str,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin cria novo processo para o cliente."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")

    processo_id = criar_processo(cadastro_id, dados)
    if processo_id:
        return {"success": True, "processo_id": processo_id}

    raise HTTPException(status_code=500, detail="Erro ao criar processo")


@router.get("/processos/{processo_id}")
async def admin_obter_processo_por_id(
    processo_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin obtém um processo específico."""
    processo = buscar_processo(processo_id)
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return processo


@router.put("/processos/{processo_id}")
async def admin_atualizar_processo(
    processo_id: int,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin atualiza um processo."""
    if atualizar_processo(processo_id, dados):
        return {"success": True, "message": "Processo atualizado"}

    raise HTTPException(status_code=500, detail="Erro ao atualizar processo")


@router.delete("/processos/{processo_id}")
async def admin_deletar_processo(
    processo_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um processo."""
    # Buscar dados antes de deletar para auditoria
    processo_existente = buscar_processo(processo_id)

    if deletar_processo(processo_id):
        # Registrar auditoria
        registrar_auditoria(
            acao="DELETE",
            tabela="processos",
            registro_id=processo_id,
            dados_anteriores=processo_existente,
            usuario_id=usuario.get("id"),
            usuario_email=usuario.get("email"),
            detalhes=f"Processo {processo_existente.get('numero_processo') if processo_existente else processo_id} deletado"
        )
        return {"success": True, "message": "Processo deletado"}

    raise HTTPException(status_code=500, detail="Erro ao deletar processo")


# ============================================
# ANDAMENTOS DE PROCESSO
# ============================================

@router.get("/processos/{processo_id}/andamentos")
async def admin_listar_andamentos_processo(
    processo_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista andamentos de um processo."""
    andamentos = listar_andamentos_processo(processo_id, apenas_visiveis=False)
    return {"andamentos": andamentos}


@router.post("/processos/{processo_id}/andamentos")
async def admin_criar_andamento_processo(
    processo_id: int,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin cria andamento para um processo."""
    andamento_id = criar_andamento_processo(
        processo_id,
        dados.get("data"),
        dados.get("descricao"),
        dados.get("visivel_cliente", True)
    )
    if andamento_id:
        return {"success": True, "andamento_id": andamento_id}

    raise HTTPException(status_code=500, detail="Erro ao criar andamento")


@router.delete("/processo-andamentos/{andamento_id}")
async def admin_deletar_andamento_processo(
    andamento_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um andamento de processo."""
    if deletar_andamento_processo(andamento_id):
        return {"success": True, "message": "Andamento deletado"}

    raise HTTPException(status_code=500, detail="Erro ao deletar andamento")


# ============================================
# ANDAMENTOS LEGACY (POR CADASTRO)
# ============================================

@router.get("/clientes/{cadastro_id}/andamentos")
async def admin_listar_andamentos(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista todos os andamentos."""
    andamentos = listar_andamentos(cadastro_id, apenas_visiveis=False)
    return {"andamentos": andamentos}


@router.post("/clientes/{cadastro_id}/andamentos")
async def admin_criar_andamento(
    cadastro_id: str,
    dados: AndamentoModel,
    usuario: dict = Depends(verificar_admin)
):
    """Admin cria novo andamento."""
    if criar_andamento(cadastro_id, dados.data, dados.descricao, dados.visivel_cliente):
        return {"success": True, "message": "Andamento criado"}

    raise HTTPException(status_code=500, detail="Erro ao criar andamento")


@router.delete("/andamentos/{andamento_id}")
async def admin_deletar_andamento(
    andamento_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um andamento."""
    if deletar_andamento(andamento_id):
        return {"success": True, "message": "Andamento deletado"}

    raise HTTPException(status_code=500, detail="Erro ao deletar andamento")


# ============================================
# CONTRATOS DE HONORÁRIOS
# ============================================

@router.get("/clientes/{cadastro_id}/contratos")
async def admin_listar_contratos(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista contratos de um cliente."""
    contratos = listar_contratos(cadastro_id)
    return {"contratos": contratos}


@router.post("/clientes/{cadastro_id}/contratos")
async def admin_criar_contrato(
    cadastro_id: str,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin cria novo contrato de honorarios."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro nao encontrado")

    contrato_id = criar_contrato_honorarios(cadastro_id, dados)
    if contrato_id:
        return {"success": True, "contrato_id": contrato_id}

    raise HTTPException(status_code=500, detail="Erro ao criar contrato")


@router.get("/contratos/{contrato_id}")
async def admin_obter_contrato(
    contrato_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin obtém um contrato específico."""
    contrato = buscar_contrato(contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    return contrato


@router.put("/contratos/{contrato_id}")
async def admin_atualizar_contrato(
    contrato_id: int,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin atualiza um contrato."""
    if atualizar_contrato(contrato_id, dados):
        return {"success": True, "message": "Contrato atualizado"}

    raise HTTPException(status_code=500, detail="Erro ao atualizar contrato")


@router.delete("/contratos/{contrato_id}")
async def admin_deletar_contrato(
    contrato_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um contrato."""
    # Buscar dados antes de deletar para auditoria
    contrato_existente = buscar_contrato(contrato_id)

    if deletar_contrato(contrato_id):
        # Registrar auditoria
        registrar_auditoria(
            acao="DELETE",
            tabela="contratos_honorarios",
            registro_id=contrato_id,
            dados_anteriores=contrato_existente,
            usuario_id=usuario.get("id"),
            usuario_email=usuario.get("email"),
            detalhes=f"Contrato {contrato_id} deletado"
        )
        return {"success": True, "message": "Contrato deletado"}

    raise HTTPException(status_code=500, detail="Erro ao deletar contrato")


# ============================================
# PARCELAS
# ============================================

@router.put("/parcelas/{parcela_id}")
async def admin_atualizar_parcela(
    parcela_id: int,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin atualiza uma parcela."""
    if atualizar_parcela(parcela_id, dados):
        return {"success": True, "message": "Parcela atualizada"}

    raise HTTPException(status_code=500, detail="Erro ao atualizar parcela")


@router.post("/parcelas/{parcela_id}/marcar-pago")
async def admin_marcar_parcela_paga(
    parcela_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin marca uma parcela como paga."""
    if marcar_parcela_paga(parcela_id):
        return {"success": True, "message": "Parcela marcada como paga"}

    raise HTTPException(status_code=500, detail="Erro ao marcar parcela")


# ============================================
# COMPROVANTES
# ============================================

@router.get("/comprovantes/pendentes")
async def admin_listar_comprovantes_pendentes(
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista comprovantes pendentes de verificação."""
    comprovantes = listar_comprovantes_pendentes()
    return {"comprovantes": comprovantes}


@router.post("/comprovantes/{comprovante_id}/aprovar")
async def admin_aprovar_comprovante(
    comprovante_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin aprova um comprovante e marca parcela como paga."""
    if aprovar_comprovante(comprovante_id, usuario["email"]):
        return {"success": True, "message": "Comprovante aprovado e parcela marcada como paga"}

    raise HTTPException(status_code=500, detail="Erro ao aprovar comprovante")


@router.post("/comprovantes/{comprovante_id}/rejeitar")
async def admin_rejeitar_comprovante(
    comprovante_id: int,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin rejeita um comprovante."""
    if rejeitar_comprovante(comprovante_id, usuario["email"], dados.get("motivo")):
        return {"success": True, "message": "Comprovante rejeitado"}

    raise HTTPException(status_code=500, detail="Erro ao rejeitar comprovante")


# ============================================
# MENSAGENS
# ============================================

@router.get("/clientes/{cadastro_id}/mensagens")
async def admin_listar_mensagens(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista mensagens de um cliente."""
    marcar_mensagens_lidas(cadastro_id, "escritorio")
    mensagens = listar_mensagens(cadastro_id)
    return {"mensagens": mensagens}


@router.post("/clientes/{cadastro_id}/mensagens")
async def admin_enviar_mensagem(
    cadastro_id: str,
    dados: MensagemEnvio,
    usuario: dict = Depends(verificar_admin)
):
    """Admin envia mensagem para o cliente."""
    if not dados.texto.strip():
        raise HTTPException(status_code=400, detail="Mensagem não pode ser vazia")

    msg_id = criar_mensagem(cadastro_id, "escritorio", dados.texto.strip())
    if msg_id:
        # Enviar notificacao por e-mail para o cliente
        try:
            cadastro = buscar_cadastro(cadastro_id)
            if cadastro and cadastro.get("dados"):
                cliente_dados = cadastro["dados"]
                email_cliente = cliente_dados.get("email")
                nome_cliente = cliente_dados.get("nome", "Cliente")

                if email_cliente:
                    assunto = "Nova mensagem do escritorio Vaucher e Alvares"
                    corpo_html = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #8B0000 0%, #5C0000 100%); padding: 30px; text-align: center;">
                            <h1 style="color: white; margin: 0; font-size: 24px;">Vaucher e Alvares</h1>
                            <p style="color: rgba(255,255,255,0.8); margin: 10px 0 0 0;">Sociedade de Advogados</p>
                        </div>
                        <div style="padding: 30px; background: #f9f9f9;">
                            <h2 style="color: #333; margin-top: 0;">Ola, {nome_cliente}!</h2>
                            <p style="color: #666; font-size: 16px; line-height: 1.6;">
                                Voce recebeu uma nova mensagem do escritorio Vaucher e Alvares.
                            </p>
                            <div style="background: white; border-left: 4px solid #8B0000; padding: 15px; margin: 20px 0; border-radius: 4px;">
                                <p style="color: #333; margin: 0; white-space: pre-wrap;">{dados.texto.strip()[:500]}{'...' if len(dados.texto.strip()) > 500 else ''}</p>
                            </div>
                            <p style="color: #666; font-size: 14px;">
                                Para responder ou ver todas as mensagens, acesse o Portal do Cliente:
                            </p>
                            <a href="https://portal-cliente-v2-three.vercel.app/portal/mensagens"
                               style="display: inline-block; background: #8B0000; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin-top: 10px;">
                                Acessar Portal
                            </a>
                        </div>
                        <div style="padding: 20px; text-align: center; color: #999; font-size: 12px;">
                            <p>Este e um e-mail automatico. Por favor, nao responda diretamente.</p>
                        </div>
                    </div>
                    """
                    await enviar_email_resend(email_cliente, assunto, corpo_html)
                    logger.info(f"E-mail de nova mensagem enviado para {email_cliente}")
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de notificacao de mensagem: {e}")

        return {"success": True, "message_id": msg_id}

    raise HTTPException(status_code=500, detail="Erro ao enviar mensagem")


@router.get("/mensagens/nao-lidas")
async def admin_mensagens_nao_lidas(usuario: dict = Depends(verificar_admin)):
    """Conta total de mensagens não lidas de clientes."""
    count = contar_mensagens_nao_lidas(remetente="cliente")
    return {"nao_lidas": count}


@router.get("/clientes/{cadastro_id}/mensagens/nao-lidas")
async def admin_mensagens_nao_lidas_cliente(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Conta mensagens não lidas de um cliente específico."""
    count = contar_mensagens_nao_lidas(cadastro_id, "cliente")
    return {"nao_lidas": count}
