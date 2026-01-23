"""
Modelos Pydantic do Sistema Vaucher e Álvares
Migrado do main.py em 19/01/2026

Este arquivo contém todos os modelos de dados (schemas) do sistema.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List


# ============================================
# MODELOS - CLIENTE/CADASTRO
# ============================================

class DadosCliente(BaseModel):
    nome: str
    nacionalidade: str = "brasileiro(a)"
    estado_civil: str
    profissao: str
    cpf: str
    data_nascimento: str
    endereco_completo: str
    email: EmailStr
    telefone: str
    tipo_demanda: str
    objeto_contrato: str
    poderes_especificos: str
    # Campos opcionais
    rg: Optional[str] = ""
    documento_identificacao: Optional[str] = ""
    matricula_funcional: Optional[str] = ""
    orgao_vinculacao: Optional[str] = ""
    honorarios: Optional[str] = ""
    observacoes: Optional[str] = ""


# ============================================
# MODELOS - AUTENTICAÇÃO/USUÁRIOS
# ============================================

class LoginRequest(BaseModel):
    email: str
    senha: str


class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    nome: Optional[str] = None
    is_admin: Optional[bool] = None
    message: Optional[str] = None
    termos_aceitos: Optional[bool] = None


class NovoUsuario(BaseModel):
    email: EmailStr
    senha: str
    nome: str
    is_admin: bool = False


class AtualizarUsuario(BaseModel):
    nome: Optional[str] = None
    senha: Optional[str] = None
    is_admin: Optional[bool] = None
    ativo: Optional[bool] = None


class AlterarSenha(BaseModel):
    senha_atual: str
    nova_senha: str


# ============================================
# MODELOS - FINANCEIRO
# ============================================

class DepositoItem(BaseModel):
    data: str = ""
    origem: str = ""
    valor: float = 0


class SucumbenciaItem(BaseModel):
    descricao: str = ""
    valor: float = 0


class RetencaoItem(BaseModel):
    descricao: str = ""
    valor: float = 0


class FinanceiroData(BaseModel):
    numero_processo: Optional[str] = ""
    vara_tribunal: Optional[str] = ""
    percentual_honorarios: Optional[float] = 20
    valor_credito_cliente: Optional[float] = 0
    depositos: Optional[List[dict]] = []
    sucumbencias: Optional[List[dict]] = []
    retencoes: Optional[List[dict]] = []
    observacoes: Optional[str] = ""


# ============================================
# MODELOS - DEMANDAS ESPECÍFICAS
# ============================================

class DadosResidenciaMedica(BaseModel):
    # Dados da Residência Médica
    instituicao_ensino: str = ""
    unidade_hospitalar: str = ""
    especialidade_medica: str = ""
    data_inicio_residencia: str = ""
    data_termino_residencia: str = ""
    valor_bolsa_mensal: float = 0
    recebeu_moradia: bool = False

    # Histórico Processual
    processo_anterior: bool = False
    numero_processo_anterior: Optional[str] = ""
    vara_juizado_anterior: Optional[str] = ""
    data_protocolo_anterior: Optional[str] = ""
    data_citacao_anterior: Optional[str] = ""

    # Dados Bancários
    dados_bancarios: str = ""


class SalvarRascunhoDemanda(BaseModel):
    tipo_demanda: str
    dados: dict


# ============================================
# MODELOS - PORTAL DO CLIENTE
# ============================================

class ClienteLogin(BaseModel):
    email: str
    senha: str


class ClienteAlterarSenha(BaseModel):
    senha_atual: str
    nova_senha: str


class ProcessoInfoModel(BaseModel):
    numero_processo: Optional[str] = ""
    vara_tribunal: Optional[str] = ""
    fase: Optional[str] = "Inicial"
    data_distribuicao: Optional[str] = None
    valor_causa: Optional[float] = 0
    reu: Optional[str] = ""
    observacoes: Optional[str] = ""


class AndamentoModel(BaseModel):
    data: str
    descricao: str
    visivel_cliente: Optional[bool] = True


class MensagemEnvio(BaseModel):
    texto: str


# ============================================
# MODELOS - ATUALIZAÇÃO CADASTRAL
# ============================================

class SolicitacaoAtualizacao(BaseModel):
    motivo: str = ""


class EnvioAtualizacao(BaseModel):
    atualizacao_id: Optional[int] = None
    dados: dict = {}
    documentos: list = []


class RejeicaoAtualizacao(BaseModel):
    motivo: str = ""
