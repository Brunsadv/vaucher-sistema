'use client'

import { useState, useEffect, useRef } from 'react'
import { FileText, Check, User, Briefcase, FolderOpen, Clock, CheckCircle, Eye, Send, Users, Filter, Search, ArrowLeft, LogOut, FileCheck, AlertCircle, Download, Lock, Mail, Shield, Paperclip, X, FileUp, Upload, Plus, Trash2, Edit, Key, UserPlus, Settings, FileSpreadsheet, DollarSign, Calculator, Receipt, Scale, MessageSquare, Calendar, Gavel, CreditCard, Building, ChevronDown, ChevronUp, HardDrive, Archive, RefreshCw } from 'lucide-react'
import PWAInstallPrompt from '@/components/PWAInstallPrompt'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const LOGO_URL = "https://raw.githubusercontent.com/Brunsadv/vaucher-sistema/main/backend/static/Vaucher_e_Alvares-06.jpg"

const Logo = ({ size = 'normal' }: { size?: 'small' | 'normal' | 'large' }) => {
  const sizes = {
    small: 'h-20',
    normal: 'h-40',
    large: 'h-56'
  }
  return (
    <img 
      src={LOGO_URL} 
      alt="Vaucher e Álvares Advogados" 
      className={`${sizes[size]} w-auto`}
    />
  )
}

interface UserData {
  nome: string
  email: string
  token: string
  is_admin: boolean
}

interface Usuario {
  id: number
  email: string
  nome: string
  is_admin: boolean
  ativo: boolean
  criado_em: string
}

interface Cadastro {
  id: string
  data: string
  status: string
  dados: {
    nome: string
    cpf: string
    rg: string
    email: string
    telefone: string
    tipo_demanda: string
    profissao: string
    endereco_completo: string
    estado_civil: string
    nacionalidade: string
    data_nascimento: string
    objeto_contrato: string
    poderes_especificos: string
    observacoes?: string
  }
  documentos: string[]
  arquivos_gerados?: {
    contrato?: string
    procuracao?: string
    peticao_auxilio_moradia?: string
  }
  documentos_assinados?: string[]
  data_assinatura?: string
  assinaturas_digitais?: {
    contrato?: {
      doc_id: string
      signer_token: string
      url_assinatura: string
      status: string
      data_envio: string
    }
    procuracao?: {
      doc_id: string
      signer_token: string
      url_assinatura: string
      status: string
      data_envio: string
    }
  }
  documentos_finais?: {
    contrato?: string
    procuracao?: string
  }
}

interface DadosAuxilioMoradia {
  instituicao_ensino: string
  unidade_hospitalar: string
  especialidade_medica: string
  data_inicio_residencia: string
  data_termino_residencia: string
  valor_bolsa_mensal: string
  recebeu_moradia: boolean
  processo_anterior: boolean
  numero_processo_anterior: string
  vara_juizado_anterior: string
  data_protocolo_anterior: string
  data_citacao_anterior: string
  dados_bancarios: string
}

interface DadosDemanda {
  id: number
  cadastro_id: string
  tipo_demanda: string
  dados: DadosAuxilioMoradia
  status: string
  criado_em: string
}

interface Processo {
  id: number
  cadastro_id: string
  numero_processo: string
  tipo_acao: string
  vara_tribunal: string
  fase: string
  reu: string
  valor_causa: number
  data_distribuicao: string | null
  status: string
  observacoes: string
  andamentos?: Andamento[]
}

interface Andamento {
  id: number
  processo_id: number
  data: string
  descricao: string
  visivel_cliente: boolean
}

interface Contrato {
  id: number
  cadastro_id: string
  processo_id: number | null
  processo_numero: string
  tipo: string
  descricao: string
  valor_total: number
  num_parcelas: number
  valor_mensal: number
  dia_vencimento: number
  percentual_exito: number
  data_inicio: string | null
  status: string
  observacoes: string
  parcelas: Parcela[]
}

interface Parcela {
  id: number
  contrato_id: number
  numero: number
  valor: number
  vencimento: string
  status: string
  data_pagamento: string | null
  tem_comprovante: boolean
}

interface Mensagem {
  id: number
  cadastro_id: string
  remetente: string
  texto: string
  lida: boolean
  criado_em: string
}

interface DepositoItem {
  data: string
  origem: string
  valor: number
}

interface SucumbenciaItem {
  descricao: string
  valor: number
}

interface RetencaoItem {
  descricao: string
  valor: number
}

interface Financeiro {
  cadastro_id: string
  numero_processo: string
  vara_tribunal: string
  percentual_honorarios: number
  valor_credito_cliente: number
  depositos: DepositoItem[]
  sucumbencias: SucumbenciaItem[]
  retencoes: RetencaoItem[]
  observacoes: string
}

interface AcessoPortal {
  tem_acesso: boolean
  primeiro_acesso: boolean | null
  ultimo_acesso: string | null
}
interface DocumentoBackup {
  id: string
  db_id?: number
  tipo: string
  nome: string
  arquivo?: string
  descricao?: string
  caminho: string
  existe: boolean
  tamanho: number
  status?: string
  data?: string
}

interface ClienteDocumentos {
  cadastro_id: string
  nome_cliente: string
  documentos: DocumentoBackup[]
  total_documentos: number
  documentos_existentes: number
  tamanho_total: number
}

interface BackupResumo {
  total_clientes: number
  total_documentos: number
  documentos_existentes: number
  tamanho_total: number
  tamanho_formatado: string
}

interface AtualizacaoCadastral {
  id: number
  cadastro_id: string
  tipo: string
  status: string
  motivo_solicitacao: string | null
  solicitado_em: string | null
  solicitado_por: string | null
  dados_novos: Record<string, any> | null
  documentos_novos: any[] | null
  enviado_em: string | null
  analisado_em: string | null
  analisado_por: string | null
  motivo_rejeicao: string | null
  nome_cliente?: string
  email_cliente?: string
  cpf_cliente?: string
  dados_atuais?: Record<string, any>
}
// Tela de Login
const LoginScreen = ({ onLogin }: { onLogin: (user: UserData) => void }) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, senha: password })
      })

      const data = await response.json()

      if (data.success) {
        onLogin({ nome: data.nome, email, token: data.token, is_admin: data.is_admin })
      } else {
        setError(data.message || 'E-mail ou senha incorretos')
      }
    } catch (err) {
      setError('Erro de conexão. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-red-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
              <Logo />
            </div>
            <p className="text-gray-500 text-sm">Painel Administrativo</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
              <div className="relative">
                <Mail className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="seu@email.com"
                  required
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
              <div className="relative">
                <Lock className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                />
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-red-800 hover:bg-red-900 text-white font-semibold py-3 px-6 rounded-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Entrando...
                </>
              ) : 'Entrar'}
            </button>
          </form>
        </div>

        <p className="text-center text-gray-400 text-xs mt-6">
          © {new Date().getFullYear()} Vaucher e Álvares Sociedade de Advogados
        </p>
      </div>
    </div>
  )
}

// Modal de Gerenciamento de Usuários
const UsuariosModal = ({ user, onClose }: { user: UserData, onClose: () => void }) => {
  const [usuarios, setUsuarios] = useState<Usuario[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editando, setEditando] = useState<Usuario | null>(null)
  const [form, setForm] = useState({ email: '', nome: '', senha: '', is_admin: false })
  const [erro, setErro] = useState('')
  const [sucesso, setSucesso] = useState('')

  useEffect(() => {
    carregarUsuarios()
  }, [])

  const carregarUsuarios = async () => {
    try {
      const response = await fetch(`${API_URL}/api/usuarios`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setUsuarios(data)
      }
    } catch (err) {
      console.error('Erro ao carregar usuários:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErro('')
    setSucesso('')

    try {
      if (editando) {
        const response = await fetch(`${API_URL}/api/usuarios/${editando.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({
            nome: form.nome,
            senha: form.senha || undefined,
            is_admin: form.is_admin
          })
        })
        if (response.ok) {
          setSucesso('Usuário atualizado com sucesso!')
          carregarUsuarios()
          setShowForm(false)
          setEditando(null)
          setForm({ email: '', nome: '', senha: '', is_admin: false })
        } else {
          const data = await response.json()
          setErro(data.detail || 'Erro ao atualizar')
        }
      } else {
        const response = await fetch(`${API_URL}/api/usuarios`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify(form)
        })
        if (response.ok) {
          setSucesso('Usuário criado com sucesso!')
          carregarUsuarios()
          setShowForm(false)
          setForm({ email: '', nome: '', senha: '', is_admin: false })
        } else {
          const data = await response.json()
          setErro(data.detail || 'Erro ao criar usuário')
        }
      }
    } catch (err) {
      setErro('Erro de conexão')
    }
  }

  const handleDesativar = async (id: number) => {
    if (!confirm('Deseja desativar este usuário?')) return

    try {
      const response = await fetch(`${API_URL}/api/usuarios/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        setSucesso('Usuário desativado!')
        carregarUsuarios()
      } else {
        const data = await response.json()
        setErro(data.detail || 'Erro ao desativar')
      }
    } catch (err) {
      setErro('Erro de conexão')
    }
  }

  const handleEditar = (usuario: Usuario) => {
    setEditando(usuario)
    setForm({ email: usuario.email, nome: usuario.nome, senha: '', is_admin: usuario.is_admin })
    setShowForm(true)
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Users className="w-6 h-6 text-red-700" />
            <h2 className="text-xl font-bold text-gray-800">Gerenciar Usuários</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[70vh]">
          {sucesso && (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm mb-4 flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              {sucesso}
            </div>
          )}

          {erro && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-4">
              {erro}
            </div>
          )}

          {!showForm ? (
            <>
              <button
                onClick={() => { setShowForm(true); setEditando(null); setForm({ email: '', nome: '', senha: '', is_admin: false }); }}
                className="flex items-center gap-2 bg-red-800 hover:bg-red-900 text-white font-medium px-4 py-2 rounded-lg mb-4"
              >
                <UserPlus className="w-5 h-5" />
                Novo Usuário
              </button>

              {loading ? (
                <div className="text-center py-8">
                  <div className="w-8 h-8 border-2 border-red-800 border-t-transparent rounded-full animate-spin mx-auto" />
                </div>
              ) : (
                <div className="space-y-3">
                  {usuarios.map((u) => (
                    <div key={u.id} className={`border rounded-lg p-4 ${!u.ativo ? 'opacity-50 bg-gray-50' : ''}`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-semibold text-gray-800">{u.nome}</p>
                            {u.is_admin && (
                              <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full font-medium">
                                Admin
                              </span>
                            )}
                            {!u.ativo && (
                              <span className="px-2 py-0.5 bg-gray-200 text-gray-600 text-xs rounded-full font-medium">
                                Inativo
                              </span>
                            )}
                          </div>
                          <p className="text-sm text-gray-500">{u.email}</p>
                        </div>
                        {u.ativo && (
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleEditar(u)}
                              className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                              title="Editar"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleDesativar(u.id)}
                              className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                              title="Desativar"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <h3 className="font-semibold text-gray-800 mb-4">
                {editando ? 'Editar Usuário' : 'Novo Usuário'}
              </h3>

              {!editando && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm({ ...form, email: e.target.value })}
                    required
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
                <input
                  type="text"
                  value={form.nome}
                  onChange={(e) => setForm({ ...form, nome: e.target.value })}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {editando ? 'Nova Senha (deixe em branco para manter)' : 'Senha'}
                </label>
                <input
                  type="password"
                  value={form.senha}
                  onChange={(e) => setForm({ ...form, senha: e.target.value })}
                  required={!editando}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_admin"
                  checked={form.is_admin}
                  onChange={(e) => setForm({ ...form, is_admin: e.target.checked })}
                  className="w-4 h-4 text-red-800 rounded"
                />
                <label htmlFor="is_admin" className="text-sm text-gray-700">
                  Administrador (pode gerenciar outros usuários)
                </label>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setEditando(null); }}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 bg-red-800 hover:bg-red-900 text-white font-semibold px-4 py-2 rounded-lg"
                >
                  {editando ? 'Salvar' : 'Criar'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

// Modal de Alterar Senha
const AlterarSenhaModal = ({ user, onClose }: { user: UserData, onClose: () => void }) => {
  const [senhaAtual, setSenhaAtual] = useState('')
  const [novaSenha, setNovaSenha] = useState('')
  const [confirmarSenha, setConfirmarSenha] = useState('')
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')
  const [sucesso, setSucesso] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErro('')

    if (novaSenha !== confirmarSenha) {
      setErro('As senhas não conferem')
      return
    }

    if (novaSenha.length < 6) {
      setErro('A nova senha deve ter pelo menos 6 caracteres')
      return
    }

    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/alterar-senha`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify({
          senha_atual: senhaAtual,
          nova_senha: novaSenha
        })
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setSucesso(true)
        setTimeout(() => onClose(), 2000)
      } else {
        setErro(data.detail || 'Erro ao alterar senha')
      }
    } catch (err) {
      setErro('Erro de conexão. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full">
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Key className="w-6 h-6 text-red-700" />
            <h2 className="text-xl font-bold text-gray-800">Alterar Senha</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6">
          {sucesso ? (
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <p className="text-lg font-medium text-gray-800">Senha alterada com sucesso!</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Senha Atual</label>
                <input
                  type="password"
                  value={senhaAtual}
                  onChange={(e) => setSenhaAtual(e.target.value)}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nova Senha</label>
                <input
                  type="password"
                  value={novaSenha}
                  onChange={(e) => setNovaSenha(e.target.value)}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar Nova Senha</label>
                <input
                  type="password"
                  value={confirmarSenha}
                  onChange={(e) => setConfirmarSenha(e.target.value)}
                  required
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                />
              </div>

              {erro && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                  {erro}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 bg-red-800 hover:bg-red-900 text-white font-semibold px-4 py-2 rounded-lg disabled:opacity-50"
                >
                  {loading ? 'Alterando...' : 'Alterar'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}

// Modal de Novo/Editar Processo
const ProcessoModal = ({ 
  cadastroId, 
  processo, 
  user, 
  onClose, 
  onSave 
}: { 
  cadastroId: string
  processo: Processo | null
  user: UserData
  onClose: () => void
  onSave: () => void 
}) => {
  const [form, setForm] = useState({
    numero_processo: processo?.numero_processo || '',
    tipo_acao: processo?.tipo_acao || '',
    vara_tribunal: processo?.vara_tribunal || '',
    fase: processo?.fase || 'Inicial',
    reu: processo?.reu || '',
    valor_causa: processo?.valor_causa || 0,
    data_distribuicao: processo?.data_distribuicao || '',
    status: processo?.status || 'ativo',
    observacoes: processo?.observacoes || ''
  })
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setErro('')

    try {
      const url = processo 
        ? `${API_URL}/api/admin/processos/${processo.id}`
        : `${API_URL}/api/admin/clientes/${cadastroId}/processos`
      
      const response = await fetch(url, {
        method: processo ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify(form)
      })

      if (response.ok) {
        onSave()
        onClose()
      } else {
        const data = await response.json()
        setErro(data.detail || 'Erro ao salvar processo')
      }
    } catch (err) {
      setErro('Erro de conexão')
    } finally {
      setLoading(false)
    }
  }

  const tiposAcao = [
    'Trabalhista',
    'Cível',
    'Previdenciário',
    'Administrativo',
    'Tributário',
    'Consumidor',
    'Família',
    'Outro'
  ]

  const fases = [
    'Inicial',
    'Citação',
    'Contestação',
    'Instrução',
    'Sentença',
    'Recurso',
    'Execução',
    'Cumprimento de Sentença',
    'Arquivado'
  ]

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Gavel className="w-6 h-6 text-red-700" />
            <h2 className="text-xl font-bold text-gray-800">
              {processo ? 'Editar Processo' : 'Novo Processo'}
            </h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Número do Processo</label>
              <input
                type="text"
                value={form.numero_processo}
                onChange={(e) => setForm({ ...form, numero_processo: e.target.value })}
                placeholder="0001234-12.2026.5.23.0001"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Ação</label>
              <select
                value={form.tipo_acao}
                onChange={(e) => setForm({ ...form, tipo_acao: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
              >
                <option value="">Selecione...</option>
                {tiposAcao.map(tipo => (
                  <option key={tipo} value={tipo}>{tipo}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Vara / Tribunal</label>
            <input
              type="text"
              value={form.vara_tribunal}
              onChange={(e) => setForm({ ...form, vara_tribunal: e.target.value })}
              placeholder="1ª Vara do Trabalho de Cuiabá / TRT23"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fase</label>
              <select
                value={form.fase}
                onChange={(e) => setForm({ ...form, fase: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
              >
                {fases.map(fase => (
                  <option key={fase} value={fase}>{fase}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
              >
                <option value="ativo">Ativo</option>
                <option value="arquivado">Arquivado</option>
                <option value="encerrado">Encerrado</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Réu / Reclamada</label>
            <input
              type="text"
              value={form.reu}
              onChange={(e) => setForm({ ...form, reu: e.target.value })}
              placeholder="Nome do réu ou empresa"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Valor da Causa (R$)</label>
              <input
                type="number"
                step="0.01"
                value={form.valor_causa || ''}
                onChange={(e) => setForm({ ...form, valor_causa: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data de Distribuição</label>
              <input
                type="date"
                value={form.data_distribuicao || ''}
                onChange={(e) => setForm({ ...form, data_distribuicao: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
            <textarea
              value={form.observacoes}
              onChange={(e) => setForm({ ...form, observacoes: e.target.value })}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 resize-none"
            />
          </div>

          {erro && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {erro}
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-red-800 hover:bg-red-900 text-white font-semibold px-4 py-2 rounded-lg disabled:opacity-50"
            >
              {loading ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Modal de Novo/Editar Contrato
const ContratoModal = ({ 
  cadastroId, 
  processos,
  contrato, 
  user, 
  onClose, 
  onSave 
}: { 
  cadastroId: string
  processos: Processo[]
  contrato: Contrato | null
  user: UserData
  onClose: () => void
  onSave: () => void 
}) => {
  const [form, setForm] = useState({
    processo_id: contrato?.processo_id || null,
    tipo: contrato?.tipo || 'parcelado',
    descricao: contrato?.descricao || '',
    valor_total: contrato?.valor_total || 0,
    num_parcelas: contrato?.num_parcelas || 1,
    valor_mensal: contrato?.valor_mensal || 0,
    dia_vencimento: contrato?.dia_vencimento || 10,
    percentual_exito: contrato?.percentual_exito || 0,
    data_inicio: contrato?.data_inicio || new Date().toISOString().split('T')[0],
    status: contrato?.status || 'ativo',
    observacoes: contrato?.observacoes || ''
  })
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setErro('')

    try {
      const url = contrato 
        ? `${API_URL}/api/admin/contratos/${contrato.id}`
        : `${API_URL}/api/admin/clientes/${cadastroId}/contratos`
      
      const response = await fetch(url, {
        method: contrato ? 'PUT' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify(form)
      })

      if (response.ok) {
        onSave()
        onClose()
      } else {
        const data = await response.json()
        setErro(data.detail || 'Erro ao salvar contrato')
      }
    } catch (err) {
      setErro('Erro de conexão')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CreditCard className="w-6 h-6 text-red-700" />
            <h2 className="text-xl font-bold text-gray-800">
              {contrato ? 'Editar Contrato' : 'Novo Contrato de Honorários'}
            </h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Processo Vinculado (opcional)</label>
            <select
              value={form.processo_id || ''}
              onChange={(e) => setForm({ ...form, processo_id: e.target.value ? parseInt(e.target.value) : null })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
            >
              <option value="">Nenhum (Assessoria Geral)</option>
              {processos.map(p => (
                <option key={p.id} value={p.id}>
                  {p.numero_processo || 'Sem número'} - {p.tipo_acao}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Contrato</label>
            <select
              value={form.tipo}
              onChange={(e) => setForm({ ...form, tipo: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
            >
              <option value="fixo">Fixo (À Vista)</option>
              <option value="parcelado">Parcelado</option>
              <option value="mensal">Mensal (Assessoria)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
            <input
              type="text"
              value={form.descricao}
              onChange={(e) => setForm({ ...form, descricao: e.target.value })}
              placeholder="Ex: Honorários Processo Trabalhista"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
            />
          </div>

          {(form.tipo === 'fixo' || form.tipo === 'parcelado') && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Valor Total (R$)</label>
                <input
                  type="number"
                  step="0.01"
                  value={form.valor_total || ''}
                  onChange={(e) => setForm({ ...form, valor_total: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
                />
              </div>
              {form.tipo === 'parcelado' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Número de Parcelas</label>
                  <input
                    type="number"
                    min="1"
                    value={form.num_parcelas}
                    onChange={(e) => setForm({ ...form, num_parcelas: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
                  />
                </div>
              )}
            </div>
          )}

          {form.tipo === 'mensal' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Valor Mensal (R$)</label>
              <input
                type="number"
                step="0.01"
                value={form.valor_mensal || ''}
                onChange={(e) => setForm({ ...form, valor_mensal: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
              />
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Dia de Vencimento</label>
              <input
                type="number"
                min="1"
                max="31"
                value={form.dia_vencimento}
                onChange={(e) => setForm({ ...form, dia_vencimento: parseInt(e.target.value) || 10 })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data de Início</label>
              <input
                type="date"
                value={form.data_inicio || ''}
                onChange={(e) => setForm({ ...form, data_inicio: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
              />
            </div>
          </div>

          <div className="bg-amber-50 rounded-lg p-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Percentual de Êxito (%) - Opcional
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              value={form.percentual_exito || ''}
              onChange={(e) => setForm({ ...form, percentual_exito: parseFloat(e.target.value) || 0 })}
              placeholder="Ex: 20"
              className="w-full px-3 py-2 border border-amber-300 rounded-lg focus:ring-2 focus:ring-amber-500"
            />
            <p className="text-xs text-amber-700 mt-1">
              Percentual sobre o resultado do processo, se houver
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Observações</label>
            <textarea
              value={form.observacoes}
              onChange={(e) => setForm({ ...form, observacoes: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 resize-none"
            />
          </div>

          {erro && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {erro}
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-red-800 hover:bg-red-900 text-white font-semibold px-4 py-2 rounded-lg disabled:opacity-50"
            >
              {loading ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Modal de Andamento
const AndamentoModal = ({ 
  processoId, 
  user, 
  onClose, 
  onSave 
}: { 
  processoId: number
  user: UserData
  onClose: () => void
  onSave: () => void 
}) => {
  const [form, setForm] = useState({
    data: new Date().toISOString().split('T')[0],
    descricao: '',
    visivel_cliente: true
  })
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.descricao.trim()) {
      setErro('Descrição é obrigatória')
      return
    }

    setLoading(true)
    setErro('')

    try {
      const response = await fetch(`${API_URL}/api/admin/processos/${processoId}/andamentos`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify(form)
      })

      if (response.ok) {
        onSave()
        onClose()
      } else {
        const data = await response.json()
        setErro(data.detail || 'Erro ao salvar andamento')
      }
    } catch (err) {
      setErro('Erro de conexão')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full">
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Calendar className="w-6 h-6 text-red-700" />
            <h2 className="text-xl font-bold text-gray-800">Novo Andamento</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data</label>
            <input
              type="date"
              value={form.data}
              onChange={(e) => setForm({ ...form, data: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Descrição</label>
            <textarea
              value={form.descricao}
              onChange={(e) => setForm({ ...form, descricao: e.target.value })}
              rows={4}
              placeholder="Descreva o andamento processual..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 resize-none"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="visivel_cliente"
              checked={form.visivel_cliente}
              onChange={(e) => setForm({ ...form, visivel_cliente: e.target.checked })}
              className="w-4 h-4 text-red-800 rounded"
            />
            <label htmlFor="visivel_cliente" className="text-sm text-gray-700">
              Visível para o cliente no Portal
            </label>
          </div>

          {erro && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {erro}
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-red-800 hover:bg-red-900 text-white font-semibold px-4 py-2 rounded-lg disabled:opacity-50"
            >
              {loading ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Modal de Envio de Email com Documentos
const EnviarEmailModal = ({ 
  cadastro,
  onClose, 
  onSuccess 
}: { 
  cadastro: Cadastro
  onClose: () => void
  onSuccess: (msg: string) => void 
}) => {
  const [assunto, setAssunto] = useState('Seus Documentos - Vaucher e Álvares Advogados')
  const [mensagem, setMensagem] = useState('')
  const [arquivosSelecionados, setArquivosSelecionados] = useState<{[key: string]: boolean}>({
    contrato: true,
    procuracao: true
  })
  const [arquivosExtras, setArquivosExtras] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')
  const inputFileRef = useRef<HTMLInputElement>(null)

  const temDocumentosGerados = cadastro.arquivos_gerados && 
    (cadastro.arquivos_gerados.contrato || cadastro.arquivos_gerados.procuracao)

  const handleAdicionarArquivos = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setArquivosExtras(prev => [...prev, ...Array.from(e.target.files!)])
    }
  }

  const removerArquivoExtra = (index: number) => {
    setArquivosExtras(prev => prev.filter((_, i) => i !== index))
  }

  const handleEnviar = async () => {
    const temContrato = arquivosSelecionados.contrato && cadastro.arquivos_gerados?.contrato
    const temProcuracao = arquivosSelecionados.procuracao && cadastro.arquivos_gerados?.procuracao
    
    if (!temContrato && !temProcuracao && arquivosExtras.length === 0) {
      setErro('Selecione pelo menos um documento para enviar')
      return
    }

    setLoading(true)
    setErro('')

    try {
      const formData = new FormData()
      formData.append('assunto', assunto)
      formData.append('mensagem', mensagem)
      
      if (temContrato) {
        const response = await fetch(`${API_URL}/api/cadastros/${cadastro.id}/download/contrato`)
        if (response.ok) {
          const blob = await response.blob()
          formData.append('arquivos', blob, 'Contrato_Honorarios.docx')
        }
      }
      
      if (temProcuracao) {
        const response = await fetch(`${API_URL}/api/cadastros/${cadastro.id}/download/procuracao`)
        if (response.ok) {
          const blob = await response.blob()
          formData.append('arquivos', blob, 'Procuracao.docx')
        }
      }
      
      arquivosExtras.forEach(arquivo => {
        formData.append('arquivos', arquivo, arquivo.name)
      })

      const response = await fetch(`${API_URL}/api/cadastros/${cadastro.id}/enviar-email`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (response.ok) {
        onSuccess(data.message || 'E-mail enviado com sucesso!')
        onClose()
      } else {
        setErro(data.detail || 'Erro ao enviar e-mail')
      }
    } catch (err) {
      setErro('Erro de conexão. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Mail className="w-6 h-6 text-red-700" />
            <h2 className="text-xl font-bold text-gray-800">Enviar Documentos por E-mail</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-sm text-gray-500 mb-1">Destinatário</p>
            <p className="font-medium">{cadastro.dados.nome}</p>
            <p className="text-gray-600">{cadastro.dados.email}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Assunto do E-mail</label>
            <input
              type="text"
              value={assunto}
              onChange={(e) => setAssunto(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Mensagem Adicional (opcional)</label>
            <textarea
              value={mensagem}
              onChange={(e) => setMensagem(e.target.value)}
              rows={3}
              placeholder="Adicione uma mensagem personalizada..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 resize-none"
            />
          </div>

          {temDocumentosGerados && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Documentos Gerados</label>
              <div className="space-y-2">
                {cadastro.arquivos_gerados?.contrato && (
                  <label className="flex items-center gap-3 p-3 bg-purple-50 border border-purple-200 rounded-lg cursor-pointer hover:bg-purple-100">
                    <input
                      type="checkbox"
                      checked={arquivosSelecionados.contrato}
                      onChange={(e) => setArquivosSelecionados(prev => ({...prev, contrato: e.target.checked}))}
                      className="w-4 h-4 text-red-800 rounded"
                    />
                    <FileText className="w-5 h-5 text-purple-600" />
                    <span className="font-medium">Contrato de Honorários</span>
                  </label>
                )}
                {cadastro.arquivos_gerados?.procuracao && (
                  <label className="flex items-center gap-3 p-3 bg-purple-50 border border-purple-200 rounded-lg cursor-pointer hover:bg-purple-100">
                    <input
                      type="checkbox"
                      checked={arquivosSelecionados.procuracao}
                      onChange={(e) => setArquivosSelecionados(prev => ({...prev, procuracao: e.target.checked}))}
                      className="w-4 h-4 text-red-800 rounded"
                    />
                    <FileText className="w-5 h-5 text-purple-600" />
                    <span className="font-medium">Procuração</span>
                  </label>
                )}
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Outros Arquivos (opcional)</label>
            <input
              type="file"
              ref={inputFileRef}
              onChange={handleAdicionarArquivos}
              multiple
              className="hidden"
            />
            <button
              type="button"
              onClick={() => inputFileRef.current?.click()}
              className="flex items-center gap-2 px-4 py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-red-800 hover:text-red-800 w-full justify-center"
            >
              <Upload className="w-5 h-5" />
              Adicionar Arquivos
            </button>
            {arquivosExtras.length > 0 && (
              <div className="mt-3 space-y-2">
                {arquivosExtras.map((arquivo, index) => (
                  <div key={index} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Paperclip className="w-4 h-4 text-gray-500" />
                      <span className="text-sm">{arquivo.name}</span>
                    </div>
                    <button onClick={() => removerArquivoExtra(index)} className="text-red-600 hover:text-red-800">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              <strong>📤 Link automático:</strong> O cliente receberá um link para devolver os documentos assinados.
            </p>
          </div>

          {erro && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">{erro}</div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100"
            >
              Cancelar
            </button>
            <button
              onClick={handleEnviar}
              disabled={loading}
              className="flex-1 bg-red-800 hover:bg-red-900 text-white font-semibold px-4 py-2 rounded-lg disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Enviando...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Enviar E-mail
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
// Modal de Backup e Gerenciamento de Documentos
const BackupModal = ({ user, onClose }: { user: UserData, onClose: () => void }) => {
  const [loading, setLoading] = useState(true)
  const [clientes, setClientes] = useState<ClienteDocumentos[]>([])
  const [resumo, setResumo] = useState<BackupResumo | null>(null)
  const [selecionados, setSelecionados] = useState<Set<string>>(new Set())
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set())
  const [baixandoBackup, setBaixandoBackup] = useState(false)
  const [deletando, setDeletando] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [filtroCliente, setFiltroCliente] = useState('')

  useEffect(() => {
    carregarDocumentos()
  }, [])

  const carregarDocumentos = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/admin/backup/listar-documentos`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setClientes(data.clientes || [])
        setResumo(data.resumo || null)
      }
    } catch (err) {
      console.error('Erro ao carregar documentos:', err)
    } finally {
      setLoading(false)
    }
  }

  const toggleCliente = (cadastroId: string) => {
    const novos = new Set(expandidos)
    if (novos.has(cadastroId)) {
      novos.delete(cadastroId)
    } else {
      novos.add(cadastroId)
    }
    setExpandidos(novos)
  }

  const toggleDocumento = (docId: string) => {
    const novos = new Set(selecionados)
    if (novos.has(docId)) {
      novos.delete(docId)
    } else {
      novos.add(docId)
    }
    setSelecionados(novos)
  }

  const selecionarTodosCliente = (cliente: ClienteDocumentos) => {
    const novos = new Set(selecionados)
    const docsExistentes = cliente.documentos.filter(d => d.existe)
    const todosJaSelecionados = docsExistentes.every(d => selecionados.has(d.id))
    
    if (todosJaSelecionados) {
      docsExistentes.forEach(d => novos.delete(d.id))
    } else {
      docsExistentes.forEach(d => novos.add(d.id))
    }
    setSelecionados(novos)
  }

  const selecionarTodos = () => {
    if (selecionados.size > 0) {
      setSelecionados(new Set())
    } else {
      const todos = new Set<string>()
      clientes.forEach(c => {
        c.documentos.filter(d => d.existe).forEach(d => todos.add(d.id))
      })
      setSelecionados(todos)
    }
  }

  const handleBackupCompleto = async () => {
    setBaixandoBackup(true)
    try {
      const response = await fetch(`${API_URL}/api/admin/backup/download-completo`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `backup_completo_${new Date().toISOString().split('T')[0]}.zip`
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      } else {
        alert('Erro ao gerar backup completo')
      }
    } catch (err) {
      alert('Erro de conexão')
    } finally {
      setBaixandoBackup(false)
    }
  }

  const handleBackupSelecionados = async () => {
    if (selecionados.size === 0) {
      alert('Selecione pelo menos um documento')
      return
    }

    setBaixandoBackup(true)
    try {
      const response = await fetch(`${API_URL}/api/admin/backup/download`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${user.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          documentos_ids: Array.from(selecionados),
          incluir_dados_json: true
        })
      })
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `backup_selecionados_${new Date().toISOString().split('T')[0]}.zip`
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      } else {
        alert('Erro ao gerar backup')
      }
    } catch (err) {
      alert('Erro de conexão')
    } finally {
      setBaixandoBackup(false)
    }
  }

  const handleDeletarSelecionados = async () => {
    if (selecionados.size === 0) {
      alert('Selecione pelo menos um documento')
      return
    }

    setDeletando(true)
    try {
      const response = await fetch(`${API_URL}/api/admin/backup/deletar-documentos`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${user.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          documentos_ids: Array.from(selecionados)
        })
      })
      if (response.ok) {
        const data = await response.json()
        alert(`${data.deletados || 0} documento(s) deletado(s) com sucesso`)
        setSelecionados(new Set())
        setConfirmDelete(false)
        carregarDocumentos()
      } else {
        alert('Erro ao deletar documentos')
      }
    } catch (err) {
      alert('Erro de conexão')
    } finally {
      setDeletando(false)
    }
  }

  const formatarTamanho = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getTipoLabel = (tipo: string) => {
    const tipos: Record<string, string> = {
      'documento_cadastro': 'Doc. Cadastro',
      'contrato': 'Contrato',
      'procuracao': 'Procuração',
      'documento_assinado': 'Doc. Assinado',
      'documento_extra': 'Doc. Extra',
      'documento_admin': 'Doc. Escritório',
      'comprovante': 'Comprovante'
    }
    return tipos[tipo] || tipo
  }

  const clientesFiltrados = clientes.filter(c => 
    c.nome_cliente.toLowerCase().includes(filtroCliente.toLowerCase()) ||
    c.cadastro_id.toLowerCase().includes(filtroCliente.toLowerCase())
  )

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <Archive className="w-5 h-5 text-red-700" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Backup e Gerenciamento de Documentos</h2>
              {resumo && (
                <p className="text-sm text-gray-500">
                  {resumo.total_documentos} documentos • {resumo.tamanho_formatado}
                </p>
              )}
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Toolbar */}
        <div className="p-4 border-b bg-gray-50 flex flex-wrap gap-3 items-center">
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              placeholder="Filtrar por cliente..."
              value={filtroCliente}
              onChange={(e) => setFiltroCliente(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
            />
          </div>
          <button
            onClick={selecionarTodos}
            className="px-3 py-2 text-sm border rounded-lg hover:bg-gray-100"
          >
            {selecionados.size > 0 ? 'Limpar seleção' : 'Selecionar todos'}
          </button>
          <button
            onClick={handleBackupSelecionados}
            disabled={selecionados.size === 0 || baixandoBackup}
            className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Baixar selecionados ({selecionados.size})
          </button>
          <button
            onClick={handleBackupCompleto}
            disabled={baixandoBackup}
            className="px-3 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
          >
            <HardDrive className="w-4 h-4" />
            Backup completo
          </button>
          {selecionados.size > 0 && (
            <button
              onClick={() => setConfirmDelete(true)}
              className="px-3 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Deletar ({selecionados.size})
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="text-center py-12">
              <div className="w-8 h-8 border-2 border-red-800 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-gray-500">Carregando documentos...</p>
            </div>
          ) : clientesFiltrados.length === 0 ? (
            <div className="text-center py-12">
              <Archive className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">Nenhum documento encontrado</p>
            </div>
          ) : (
            <div className="space-y-3">
              {clientesFiltrados.map(cliente => (
                <div key={cliente.cadastro_id} className="border rounded-lg overflow-hidden">
                  <div 
                    className="p-3 bg-gray-50 flex items-center justify-between cursor-pointer hover:bg-gray-100"
                    onClick={() => toggleCliente(cliente.cadastro_id)}
                  >
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={cliente.documentos.filter(d => d.existe).every(d => selecionados.has(d.id))}
                        onChange={(e) => {
                          e.stopPropagation()
                          selecionarTodosCliente(cliente)
                        }}
                        className="w-4 h-4"
                      />
                      <User className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="font-medium">{cliente.nome_cliente}</p>
                        <p className="text-xs text-gray-500">
                          ID: {cliente.cadastro_id} • {cliente.documentos_existentes} docs • {formatarTamanho(cliente.tamanho_total)}
                        </p>
                      </div>
                    </div>
                    {expandidos.has(cliente.cadastro_id) ? (
                      <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                  </div>
                  
                  {expandidos.has(cliente.cadastro_id) && (
                    <div className="p-3 border-t bg-white">
                      {cliente.documentos.length === 0 ? (
                        <p className="text-sm text-gray-500 text-center py-2">Nenhum documento</p>
                      ) : (
                        <div className="space-y-2">
                          {cliente.documentos.map(doc => (
                            <div 
                              key={doc.id}
                              className={`flex items-center gap-3 p-2 rounded ${doc.existe ? 'hover:bg-gray-50' : 'opacity-50'}`}
                            >
                              <input
                                type="checkbox"
                                checked={selecionados.has(doc.id)}
                                onChange={() => toggleDocumento(doc.id)}
                                disabled={!doc.existe}
                                className="w-4 h-4"
                              />
                              <FileText className="w-4 h-4 text-gray-400" />
                              <div className="flex-1 min-w-0">
                                <p className="text-sm truncate">{doc.nome}</p>
                                <p className="text-xs text-gray-500">
                                  {getTipoLabel(doc.tipo)} • {formatarTamanho(doc.tamanho)}
                                  {!doc.existe && ' • Arquivo não encontrado'}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Confirm Delete Modal */}
        {confirmDelete && (
          <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
            <div className="bg-white rounded-lg p-6 max-w-md mx-4">
              <h3 className="text-lg font-semibold mb-2">Confirmar exclusão</h3>
              <p className="text-gray-600 mb-4">
                Tem certeza que deseja deletar {selecionados.size} documento(s)? Esta ação não pode ser desfeita.
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleDeletarSelecionados}
                  disabled={deletando}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                >
                  {deletando ? 'Deletando...' : 'Deletar'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Dashboard Administrativo Principal
const AdminDashboard = ({ user, onLogout }: { user: UserData, onLogout: () => void }) => {
  const [cadastros, setCadastros] = useState<Cadastro[]>([])
  const [selectedCadastro, setSelectedCadastro] = useState<Cadastro | null>(null)
  const [filterStatus, setFilterStatus] = useState('todos')
  const [searchTerm, setSearchTerm] = useState('')
  const [gerandoDocs, setGerandoDocs] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showUsuariosModal, setShowUsuariosModal] = useState(false)
  const [showAlterarSenhaModal, setShowAlterarSenhaModal] = useState(false)
  const [mensagemSucesso, setMensagemSucesso] = useState('')
  const [mensagemErro, setMensagemErro] = useState('')
  
  // Estados do Portal do Cliente
  const [activeTab, setActiveTab] = useState<'dados' | 'processos' | 'contratos' | 'documentos' | 'mensagens'>('dados')
  const [activeDocTab, setActiveDocTab] = useState<'gerar' | 'cliente' | 'demanda' | 'assinados'>('gerar')
  const [acessoPortal, setAcessoPortal] = useState<AcessoPortal | null>(null)
  const [habilitandoAcesso, setHabilitandoAcesso] = useState(false)
  
  // Estados de Processos
  const [processos, setProcessos] = useState<Processo[]>([])
  const [showProcessoModal, setShowProcessoModal] = useState(false)
  const [processoSelecionado, setProcessoSelecionado] = useState<Processo | null>(null)
  const [processoExpandido, setProcessoExpandido] = useState<number | null>(null)
  const [showAndamentoModal, setShowAndamentoModal] = useState(false)
  const [processoParaAndamento, setProcessoParaAndamento] = useState<number | null>(null)
  
  // Estados de Contratos
  const [contratos, setContratos] = useState<Contrato[]>([])
  const [showContratoModal, setShowContratoModal] = useState(false)
  const [contratoSelecionado, setContratoSelecionado] = useState<Contrato | null>(null)
  
  // Estados de Mensagens
  const [mensagens, setMensagens] = useState<Mensagem[]>([])
  const [novaMensagem, setNovaMensagem] = useState('')
  const [enviandoMensagem, setEnviandoMensagem] = useState(false)
  
  // Estados de Documentos Extras
  const [documentosExtras, setDocumentosExtras] = useState<{id: number, nome_original: string, descricao: string, criado_em: string}[]>([])
  
  // Estados para dados da demanda específica (Auxílio Moradia)
  const [dadosDemanda, setDadosDemanda] = useState<DadosDemanda | null>(null)
  const [gerandoPeticao, setGerandoPeticao] = useState(false)
  const [documentosDemanda, setDocumentosDemanda] = useState<{id: number, tipo_documento: string, nome_original: string, descricao: string, criado_em: string}[]>([])
  
  // Estados de Envio de Email
  const [showEnviarEmailModal, setShowEnviarEmailModal] = useState(false)
// Estado do Modal de Backup
  const [showBackupModal, setShowBackupModal] = useState(false)

  // Estados de Assinatura Digital
  const [enviandoParaAssinatura, setEnviandoParaAssinatura] = useState(false)
  const [statusAssinatura, setStatusAssinatura] = useState<{contrato?: string, procuracao?: string} | null>(null)

  // Estados de Upload de Documentos Finais (editados)
  const [documentosFinais, setDocumentosFinais] = useState<{contrato?: any, procuracao?: any}>({})
  const [uploadandoDocumento, setUploadandoDocumento] = useState(false)
  const contratoFinalRef = useRef<HTMLInputElement>(null)
  const procuracaoFinalRef = useRef<HTMLInputElement>(null)

  // Estados de Verificação de Assinatura
  const [verificandoAssinatura, setVerificandoAssinatura] = useState(false)
  const [statusAssinaturaDetalhado, setStatusAssinaturaDetalhado] = useState<{contrato?: {status: string, assinado?: boolean}, procuracao?: {status: string, assinado?: boolean}}>({})

  // Estados de Atualização Cadastral
  const [atualizacoesPendentes, setAtualizacoesPendentes] = useState<AtualizacaoCadastral[]>([])
  const [showModalSolicitarAtualizacao, setShowModalSolicitarAtualizacao] = useState(false)
  const [motivoSolicitacao, setMotivoSolicitacao] = useState('')
  const [loadingSolicitacao, setLoadingSolicitacao] = useState(false)
  const [showModalVerAtualizacao, setShowModalVerAtualizacao] = useState(false)
  const [atualizacaoSelecionada, setAtualizacaoSelecionada] = useState<AtualizacaoCadastral | null>(null)
  const [showModalRejeitar, setShowModalRejeitar] = useState(false)
  const [motivoRejeicao, setMotivoRejeicao] = useState('')
  
  const tiposDemanda: Record<string, string> = {
    'adicional_insalubridade': 'Adicional de Insalubridade',
    'adicional_periculosidade': 'Adicional de Periculosidade',
    'desvio_funcao': 'Desvio de Função',
    'progressao_funcional': 'Progressão Funcional',
    'revisao_aposentadoria': 'Revisão de Aposentadoria',
    'licenca_premio': 'Licença Prêmio',
    'ferias_nao_gozadas': 'Férias Não Gozadas',
    'horas_extras': 'Horas Extras',
    'reintegracao': 'Reintegração',
    'auxilio_moradia_residencia': 'Auxílio-moradia Residência Médica',
    'isencao_imposto_renda': 'Isenção de Imposto de Renda',
    'outro': 'Outro'
  }

  useEffect(() => {
    carregarCadastros()
    buscarAtualizacoesPendentes()
  }, [])

  useEffect(() => {
    if (selectedCadastro) {
      carregarDadosCliente(selectedCadastro.id)
    }
  }, [selectedCadastro])

  const carregarCadastros = async () => {
    try {
      const response = await fetch(`${API_URL}/api/cadastros`)
      const data = await response.json()
      setCadastros(data)
    } catch (err) {
      console.error('Erro ao carregar cadastros:', err)
    } finally {
      setLoading(false)
    }
  }

  // ===== FUNÇÕES DE ATUALIZAÇÃO CADASTRAL =====

  const buscarAtualizacoesPendentes = async () => {
    try {
      const response = await fetch(`${API_URL}/api/admin/atualizacoes-pendentes`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setAtualizacoesPendentes(data.atualizacoes || [])
      }
    } catch (error) {
      console.error('Erro ao buscar atualizações pendentes:', error)
    }
  }

  const solicitarAtualizacaoCadastral = async () => {
    if (!selectedCadastro) return
    
    setLoadingSolicitacao(true)
    try {
      const response = await fetch(
        `${API_URL}/api/admin/clientes/${selectedCadastro.id}/solicitar-atualizacao`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({ motivo: motivoSolicitacao })
        }
      )
      
      const data = await response.json()
      
      if (response.ok) {
        alert(`Solicitação enviada com sucesso!${data.email_enviado ? ' O cliente foi notificado por e-mail.' : ''}`)
        setShowModalSolicitarAtualizacao(false)
        setMotivoSolicitacao('')
      } else {
        alert(data.detail || 'Erro ao solicitar atualização')
      }
    } catch (error) {
      console.error('Erro:', error)
      alert('Erro ao solicitar atualização')
    } finally {
      setLoadingSolicitacao(false)
    }
  }

  const verDetalhesAtualizacao = async (atualizacao: AtualizacaoCadastral) => {
    try {
      const response = await fetch(
        `${API_URL}/api/admin/atualizacoes/${atualizacao.id}`,
        { headers: { 'Authorization': `Bearer ${user.token}` } }
      )
      
      if (response.ok) {
        const data = await response.json()
        setAtualizacaoSelecionada(data)
        setShowModalVerAtualizacao(true)
      }
    } catch (error) {
      console.error('Erro ao buscar detalhes:', error)
    }
  }

  const aprovarAtualizacao = async (atualizacaoId: number) => {
    if (!confirm('Confirma a aprovação desta atualização? Os dados do cliente serão atualizados.')) {
      return
    }
    
    try {
      const response = await fetch(
        `${API_URL}/api/admin/atualizacoes/${atualizacaoId}/aprovar`,
        {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${user.token}` }
        }
      )
      
      if (response.ok) {
        alert('Atualização aprovada com sucesso!')
        setShowModalVerAtualizacao(false)
        setAtualizacaoSelecionada(null)
        buscarAtualizacoesPendentes()
        if (selectedCadastro) {
          carregarDadosCliente(selectedCadastro.id)
          // Recarregar cadastros para atualizar a lista
          carregarCadastros()
        }
      } else {
        const data = await response.json()
        alert(data.detail || 'Erro ao aprovar atualização')
      }
    } catch (error) {
      console.error('Erro:', error)
      alert('Erro ao aprovar atualização')
    }
  }

  const rejeitarAtualizacao = async () => {
    if (!atualizacaoSelecionada) return
    
    try {
      const response = await fetch(
        `${API_URL}/api/admin/atualizacoes/${atualizacaoSelecionada.id}/rejeitar`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${user.token}`
          },
          body: JSON.stringify({ motivo: motivoRejeicao })
        }
      )
      
      if (response.ok) {
        alert('Atualização rejeitada. O cliente foi notificado.')
        setShowModalRejeitar(false)
        setShowModalVerAtualizacao(false)
        setMotivoRejeicao('')
        setAtualizacaoSelecionada(null)
        buscarAtualizacoesPendentes()
      } else {
        const data = await response.json()
        alert(data.detail || 'Erro ao rejeitar atualização')
      }
    } catch (error) {
      console.error('Erro:', error)
      alert('Erro ao rejeitar atualização')
    }
  }

  // Carregar dados específicos da demanda
  const carregarDadosDemanda = async (cadastroId: string, tipoDemanda: string) => {
    try {
      const response = await fetch(`${API_URL}/api/cadastros/${cadastroId}/demanda-especifica/${tipoDemanda}`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        const data = await response.json()
        if (data.success && data.dados) {
          setDadosDemanda(data.dados)
        } else {
          setDadosDemanda(null)
        }
      } else {
        setDadosDemanda(null)
      }
    } catch (err) {
      console.error('Erro ao carregar dados da demanda:', err)
      setDadosDemanda(null)
    }
  }

  // Gerar petição de auxílio moradia
  const gerarPeticaoAuxilioMoradia = async (cadastroId: string) => {
    setGerandoPeticao(true)
    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${cadastroId}/gerar-peticao/auxilio_moradia_residencia`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      
      if (response.ok) {
        const data = await response.json()
        setMensagemSucesso('Petição inicial gerada com sucesso!')
        // Recarregar cadastros para atualizar arquivos_gerados
        await carregarCadastros()
      } else {
        const data = await response.json()
        setMensagemErro(data.detail || 'Erro ao gerar petição')
      }
    } catch (err) {
      console.error('Erro ao gerar petição:', err)
      setMensagemErro('Erro ao gerar petição')
    } finally {
      setGerandoPeticao(false)
    }
  }

  // Baixar petição de auxílio moradia
  const baixarPeticaoAuxilioMoradia = (cadastroId: string) => {
    window.open(`${API_URL}/api/cadastros/${cadastroId}/download/peticao_auxilio_moradia`, '_blank')
  }

  const carregarDadosCliente = async (cadastroId: string) => {
    // Carregar acesso portal
    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${cadastroId}/acesso`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setAcessoPortal(data)
      }
    } catch (err) {
      console.error('Erro ao carregar acesso:', err)
    }

    // Carregar processos
    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${cadastroId}/processos`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setProcessos(data.processos || [])
      }
    } catch (err) {
      console.error('Erro ao carregar processos:', err)
    }

    // Carregar contratos
    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${cadastroId}/contratos`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setContratos(data.contratos || [])
      }
    } catch (err) {
      console.error('Erro ao carregar contratos:', err)
    }

    // Carregar mensagens
    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${cadastroId}/mensagens`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setMensagens(data.mensagens || [])
      }
    } catch (err) {
      console.error('Erro ao carregar mensagens:', err)
    }

    // Carregar documentos extras enviados pelo cliente
    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${cadastroId}/documentos-extras`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setDocumentosExtras(data.documentos || [])
      }
    } catch (err) {
      console.error('Erro ao carregar documentos extras:', err)
    }

    // Carregar documentos específicos da demanda
    try {
      const response = await fetch(`${API_URL}/api/cadastros/${cadastroId}/documentos-demanda`)
      if (response.ok) {
        const data = await response.json()
        setDocumentosDemanda(data.documentos || [])
      }
    } catch (err) {
      console.error('Erro ao carregar documentos da demanda:', err)
    }

    // Carregar dados específicos da demanda (se for auxílio moradia)
    // Usa selectedCadastro se disponível, senão busca no array
    const cadastro = selectedCadastro?.id === cadastroId ? selectedCadastro : cadastros.find(c => c.id === cadastroId)
    console.log('Tipo demanda:', cadastro?.dados?.tipo_demanda) // Debug
    if (cadastro?.dados?.tipo_demanda === 'auxilio_moradia_residencia') {
      await carregarDadosDemanda(cadastroId, 'auxilio_moradia_residencia')
    } else {
      setDadosDemanda(null)
    }

    // Carregar documentos finais (editados) para assinatura
    await carregarDocumentosFinais(cadastroId)
  }

  const carregarAndamentos = async (processoId: number) => {
    try {
      const response = await fetch(`${API_URL}/api/admin/processos/${processoId}/andamentos`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setProcessos(prev => prev.map(p => 
          p.id === processoId ? { ...p, andamentos: data.andamentos || [] } : p
        ))
      }
    } catch (err) {
      console.error('Erro ao carregar andamentos:', err)
    }
  }

  const handleHabilitarAcesso = async () => {
    if (!selectedCadastro) return
    setHabilitandoAcesso(true)

    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${selectedCadastro.id}/habilitar-acesso`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      
      if (response.ok) {
        const data = await response.json()
        setAcessoPortal({ tem_acesso: true, primeiro_acesso: true, ultimo_acesso: null })
        setMensagemSucesso(`Acesso habilitado! Senha: ${data.senha_temporaria}`)
        setTimeout(() => setMensagemSucesso(''), 10000)
      }
    } catch (err) {
      console.error('Erro ao habilitar acesso:', err)
    } finally {
      setHabilitandoAcesso(false)
    }
  }

  const handleDesabilitarAcesso = async () => {
    if (!selectedCadastro) return
    if (!confirm('Deseja desabilitar o acesso do cliente ao portal?')) return

    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${selectedCadastro.id}/desabilitar-acesso`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      
      if (response.ok) {
        setAcessoPortal({ tem_acesso: false, primeiro_acesso: null, ultimo_acesso: null })
        setMensagemSucesso('Acesso desabilitado!')
        setTimeout(() => setMensagemSucesso(''), 3000)
      }
    } catch (err) {
      console.error('Erro ao desabilitar acesso:', err)
    }
  }

  const handleEnviarMensagem = async () => {
    if (!selectedCadastro || !novaMensagem.trim()) return
    setEnviandoMensagem(true)

    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${selectedCadastro.id}/mensagens`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${user.token}`
        },
        body: JSON.stringify({ texto: novaMensagem.trim() })
      })

      if (response.ok) {
        setNovaMensagem('')
        // Recarregar mensagens
        const msgResponse = await fetch(`${API_URL}/api/admin/clientes/${selectedCadastro.id}/mensagens`, {
          headers: { 'Authorization': `Bearer ${user.token}` }
        })
        if (msgResponse.ok) {
          const data = await msgResponse.json()
          setMensagens(data.mensagens || [])
        }
      }
    } catch (err) {
      console.error('Erro ao enviar mensagem:', err)
    } finally {
      setEnviandoMensagem(false)
    }
  }

  const handleMarcarParcela = async (parcelaId: number) => {
    try {
      const response = await fetch(`${API_URL}/api/admin/parcelas/${parcelaId}/marcar-pago`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })

      if (response.ok) {
        // Recarregar contratos
        if (selectedCadastro) {
          const contratosResponse = await fetch(`${API_URL}/api/admin/clientes/${selectedCadastro.id}/contratos`, {
            headers: { 'Authorization': `Bearer ${user.token}` }
          })
          if (contratosResponse.ok) {
            const data = await contratosResponse.json()
            setContratos(data.contratos || [])
          }
        }
        setMensagemSucesso('Parcela marcada como paga!')
        setTimeout(() => setMensagemSucesso(''), 3000)
      }
    } catch (err) {
      console.error('Erro ao marcar parcela:', err)
    }
  }

  const handleDeletarProcesso = async (processoId: number) => {
    if (!confirm('Deseja excluir este processo? Esta ação não pode ser desfeita.')) return

    try {
      const response = await fetch(`${API_URL}/api/admin/processos/${processoId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })

      if (response.ok) {
        setProcessos(prev => prev.filter(p => p.id !== processoId))
        setMensagemSucesso('Processo excluído!')
        setTimeout(() => setMensagemSucesso(''), 3000)
      }
    } catch (err) {
      console.error('Erro ao excluir processo:', err)
    }
  }

  const handleDeletarContrato = async (contratoId: number) => {
    if (!confirm('Deseja excluir este contrato? Todas as parcelas serão excluídas também.')) return

    try {
      const response = await fetch(`${API_URL}/api/admin/contratos/${contratoId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })

      if (response.ok) {
        setContratos(prev => prev.filter(c => c.id !== contratoId))
        setMensagemSucesso('Contrato excluído!')
        setTimeout(() => setMensagemSucesso(''), 3000)
      }
    } catch (err) {
      console.error('Erro ao excluir contrato:', err)
    }
  }

  const handleDeletarAndamento = async (andamentoId: number, processoId: number) => {
    if (!confirm('Deseja excluir este andamento?')) return

    try {
      const response = await fetch(`${API_URL}/api/admin/processo-andamentos/${andamentoId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })

      if (response.ok) {
        carregarAndamentos(processoId)
        setMensagemSucesso('Andamento excluído!')
        setTimeout(() => setMensagemSucesso(''), 3000)
      }
    } catch (err) {
      console.error('Erro ao excluir andamento:', err)
    }
  }

  const filteredCadastros = cadastros.filter(c => {
    const matchesStatus = filterStatus === 'todos' || c.status === filterStatus
    const matchesSearch = c.dados.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         c.dados.cpf.includes(searchTerm)
    return matchesStatus && matchesSearch
  })

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      pendente: 'bg-amber-100 text-amber-800 border-amber-200',
      validado: 'bg-blue-100 text-blue-800 border-blue-200',
      documentos_gerados: 'bg-purple-100 text-purple-800 border-purple-200',
      enviado: 'bg-green-100 text-green-800 border-green-200',
      assinado: 'bg-emerald-100 text-emerald-800 border-emerald-200'
    }
    const labels: Record<string, string> = {
      pendente: 'Pendente',
      validado: 'Validado',
      documentos_gerados: 'Docs Prontos',
      enviado: 'Enviado',
      assinado: '✅ Assinado'
    }
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${styles[status] || styles.pendente}`}>
        {labels[status] || status}
      </span>
    )
  }

  const formatMoney = (value: number) => {
    return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  }

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-'
    const date = new Date(dateStr)
    return date.toLocaleDateString('pt-BR')
  }

  const handleValidar = async (id: string) => {
    try {
      await fetch(`${API_URL}/api/cadastros/${id}/validar`, { method: 'PUT' })
      setCadastros(prev => prev.map(c => c.id === id ? { ...c, status: 'validado' } : c))
      if (selectedCadastro?.id === id) {
        setSelectedCadastro(prev => prev ? { ...prev, status: 'validado' } : null)
      }
    } catch (err) {
      console.error('Erro ao validar:', err)
    }
  }

  const handleGerarDocumentos = async (id: string) => {
    setGerandoDocs(true)
    try {
      const response = await fetch(`${API_URL}/api/cadastros/${id}/gerar-documentos`, { method: 'POST' })
      const data = await response.json()
      
      if (data.success) {
        setCadastros(prev => prev.map(c => c.id === id ? { ...c, status: 'documentos_gerados', arquivos_gerados: data.arquivos } : c))
        if (selectedCadastro?.id === id) {
          setSelectedCadastro(prev => prev ? { ...prev, status: 'documentos_gerados', arquivos_gerados: data.arquivos } : null)
        }
        setMensagemSucesso('Documentos gerados com sucesso!')
        setTimeout(() => setMensagemSucesso(''), 5000)
      }
    } catch (err) {
      console.error('Erro ao gerar:', err)
    } finally {
      setGerandoDocs(false)
    }
  }

  // === Funções de Assinatura Digital ===
  const handleEnviarParaAssinatura = async (id: string, tipoDocumento: 'contrato' | 'procuracao') => {
    setEnviandoParaAssinatura(true)
    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${id}/enviar-assinatura/${tipoDocumento}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      const data = await response.json()

      if (data.success) {
        setMensagemSucesso(`Documento enviado para assinatura! Link enviado para o cliente por e-mail.`)
        setTimeout(() => setMensagemSucesso(''), 5000)

        // Recarregar cadastro completo para atualizar todos os estados
        const cadastroResponse = await fetch(`${API_URL}/api/cadastros/${id}`, {
          headers: { 'Authorization': `Bearer ${user.token}` }
        })
        if (cadastroResponse.ok) {
          const cadastroData = await cadastroResponse.json()
          setSelectedCadastro(cadastroData)
          setCadastros(prev => prev.map(c => c.id === id ? cadastroData : c))
        }

        // Também atualizar documentos finais
        await carregarDocumentosFinais(id)
      } else {
        setMensagemErro(data.detail || data.error || 'Erro ao enviar para assinatura')
        setTimeout(() => setMensagemErro(''), 5000)
      }
    } catch (err) {
      console.error('Erro ao enviar para assinatura:', err)
      setMensagemErro('Erro de conexão. Tente novamente.')
      setTimeout(() => setMensagemErro(''), 5000)
    } finally {
      setEnviandoParaAssinatura(false)
    }
  }

  const handleVerificarStatusAssinatura = async (id: string, tipoDocumento: 'contrato' | 'procuracao') => {
    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${id}/status-assinatura/${tipoDocumento}`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      const data = await response.json()

      if (data.success) {
        setStatusAssinatura(prev => ({
          ...prev,
          [tipoDocumento]: data.status
        }))
      }
    } catch (err) {
      console.error('Erro ao verificar status:', err)
    }
  }

  const handleEnviarEmailAssinatura = async (id: string) => {
    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${id}/enviar-email-assinatura`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      const data = await response.json()

      if (data.success) {
        setMensagemSucesso('E-mail com links de assinatura enviado!')
        setTimeout(() => setMensagemSucesso(''), 5000)
      } else {
        setMensagemErro(data.error || 'Erro ao enviar e-mail')
        setTimeout(() => setMensagemErro(''), 5000)
      }
    } catch (err) {
      console.error('Erro ao enviar e-mail de assinatura:', err)
    }
  }

  // === Funções de Upload de Documentos Finais ===
  const carregarDocumentosFinais = async (id: string) => {
    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${id}/documentos-finais`, {
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      const data = await response.json()
      if (data.success) {
        setDocumentosFinais(data.documentos_finais || {})
      }
    } catch (err) {
      console.error('Erro ao carregar documentos finais:', err)
    }
  }

  const handleUploadDocumentoFinal = async (id: string, tipo: 'contrato' | 'procuracao', arquivo: File) => {
    setUploadandoDocumento(true)
    try {
      const formData = new FormData()
      formData.append('arquivo', arquivo)

      const response = await fetch(`${API_URL}/api/admin/clientes/${id}/upload-documento-final/${tipo}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${user.token}` },
        body: formData
      })
      const data = await response.json()

      if (data.success) {
        setMensagemSucesso(`${tipo === 'contrato' ? 'Contrato' : 'Procuração'} final enviado com sucesso! Agora você pode enviar para assinatura.`)
        setTimeout(() => setMensagemSucesso(''), 5000)

        // Recarregar documentos finais
        await carregarDocumentosFinais(id)

        // Recarregar cadastro completo para atualizar a UI
        const cadastroResponse = await fetch(`${API_URL}/api/cadastros/${id}`, {
          headers: { 'Authorization': `Bearer ${user.token}` }
        })
        if (cadastroResponse.ok) {
          const cadastroData = await cadastroResponse.json()
          setSelectedCadastro(cadastroData)
          setCadastros(prev => prev.map(c => c.id === id ? cadastroData : c))
        }
      } else {
        setMensagemErro(data.detail || 'Erro ao enviar documento')
        setTimeout(() => setMensagemErro(''), 5000)
      }
    } catch (err) {
      console.error('Erro ao fazer upload:', err)
      setMensagemErro('Erro de conexão ao enviar documento')
      setTimeout(() => setMensagemErro(''), 5000)
    } finally {
      setUploadandoDocumento(false)
    }
  }

  const handleVerificarEBaixarAssinatura = async (id: string, tipo: 'contrato' | 'procuracao') => {
    setVerificandoAssinatura(true)
    try {
      const response = await fetch(`${API_URL}/api/admin/clientes/${id}/verificar-e-baixar-assinatura/${tipo}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
      const data = await response.json()

      if (response.ok && data.success) {
        const assinado = data.status === 'signed'
        setStatusAssinaturaDetalhado(prev => ({
          ...prev,
          [tipo]: { status: data.status, assinado }
        }))

        if (assinado && data.arquivo) {
          setMensagemSucesso(`${tipo === 'contrato' ? 'Contrato' : 'Procuração'} assinado(a)! Documento salvo com sucesso.`)
          setTimeout(() => setMensagemSucesso(''), 5000)
          // Recarregar cadastro para atualizar lista de arquivos
          const cadastroResponse = await fetch(`${API_URL}/api/cadastros/${id}`, {
            headers: { 'Authorization': `Bearer ${user.token}` }
          })
          if (cadastroResponse.ok) {
            const cadastroData = await cadastroResponse.json()
            setSelectedCadastro(cadastroData)
            setCadastros(prev => prev.map(c => c.id === id ? cadastroData : c))
          }
        } else if (assinado) {
          setMensagemSucesso(`${tipo === 'contrato' ? 'Contrato' : 'Procuração'} foi assinado(a)!`)
          setTimeout(() => setMensagemSucesso(''), 5000)
        } else {
          setMensagemErro(`Documento ainda não foi assinado. Status: ${data.status}`)
          setTimeout(() => setMensagemErro(''), 5000)
        }
      } else {
        setMensagemErro(data.message || data.detail || 'Erro ao verificar status da assinatura')
        setTimeout(() => setMensagemErro(''), 5000)
      }
    } catch (err) {
      console.error('Erro ao verificar assinatura:', err)
      setMensagemErro('Erro de conexão ao verificar assinatura')
      setTimeout(() => setMensagemErro(''), 5000)
    } finally {
      setVerificandoAssinatura(false)
    }
  }

  const handleDeletar = async (id: string) => {
    if (!confirm('⚠️ ATENÇÃO: Esta ação é irreversível!\n\nDeseja realmente EXCLUIR este cadastro permanentemente?')) {
      return
    }

    try {
      const response = await fetch(`${API_URL}/api/cadastros/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setCadastros(prev => prev.filter(c => c.id !== id))
        setSelectedCadastro(null)
        setMensagemSucesso('Cadastro excluído com sucesso!')
        setTimeout(() => setMensagemSucesso(''), 3000)
      } else {
        alert(data.detail || 'Erro ao excluir cadastro')
      }
    } catch (err) {
      console.error('Erro ao deletar:', err)
      alert('Erro de conexão. Tente novamente.')
    }
  }

  // Visualização de detalhes do cliente
  if (selectedCadastro) {
    const c = selectedCadastro
    return (
      <div className="min-h-screen bg-gray-100 py-6 px-4">
        <div className="max-w-5xl mx-auto">
          <button 
            onClick={() => {
              setSelectedCadastro(null)
              setActiveTab('dados')
              setProcessos([])
              setContratos([])
              setMensagens([])
              setDocumentosExtras([])
              setDocumentosDemanda([])
              setDadosDemanda(null)
            }}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-800 mb-6"
          >
            <ArrowLeft className="w-5 h-5" />
            Voltar para lista
          </button>

          {mensagemSucesso && (
            <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg mb-4 flex items-center gap-2">
              <CheckCircle className="w-5 h-5" />
              {mensagemSucesso}
            </div>
          )}

          {mensagemErro && (
            <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg mb-4 flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              {mensagemErro}
              <button 
                onClick={() => setMensagemErro('')}
                className="ml-auto text-red-600 hover:text-red-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white p-6">
              <div className="flex justify-between items-start">
                <div>
                <h1 className="text-2xl font-bold">{c.dados.nome}</h1>
<p className="text-gray-300 mt-1">{c.dados.email}</p>
<div className="flex items-center gap-2 mt-2">
  <span className="text-gray-400 text-sm">Código:</span>
  <code className="bg-white/20 px-2 py-1 rounded text-sm font-mono">{c.id}</code>
  <button
    onClick={() => {
      navigator.clipboard.writeText(c.id)
      setMensagemSucesso('Código copiado!')
      setTimeout(() => setMensagemSucesso(''), 2000)
    }}
    className="text-xs bg-white/20 hover:bg-white/30 px-2 py-1 rounded"
    title="Copiar código"
  >
    Copiar
  </button>
</div>
                </div>
                <div className="flex items-center gap-3">
                  {getStatusBadge(c.status)}
                  {acessoPortal?.tem_acesso ? (
                    <button
                      onClick={handleDesabilitarAcesso}
                      className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded-full flex items-center gap-1"
                    >
                      <CheckCircle className="w-3 h-3" />
                      Portal Ativo
                    </button>
                  ) : (
                    <button
                      onClick={handleHabilitarAcesso}
                      disabled={habilitandoAcesso}
                      className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-full flex items-center gap-1 disabled:opacity-50"
                    >
                      <Key className="w-3 h-3" />
                      {habilitandoAcesso ? 'Habilitando...' : 'Habilitar Portal'}
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Tabs */}
            <div className="border-b bg-gray-50">
              <div className="flex overflow-x-auto">
                {[
                  { id: 'dados', label: 'Dados', icon: User },
                  { id: 'processos', label: 'Processos', icon: Gavel, count: processos.length },
                  { id: 'contratos', label: 'Honorários', icon: CreditCard, count: contratos.length },
                  { id: 'documentos', label: 'Documentos', icon: FolderOpen },
                  { id: 'mensagens', label: 'Mensagens', icon: MessageSquare, count: mensagens.filter(m => m.remetente === 'cliente' && !m.lida).length }
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex items-center gap-2 px-6 py-4 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                      activeTab === tab.id 
                        ? 'border-red-800 text-red-800 bg-white' 
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    <tab.icon className="w-4 h-4" />
                    {tab.label}
                    {tab.count !== undefined && tab.count > 0 && (
                      <span className={`px-2 py-0.5 text-xs rounded-full ${
                        activeTab === tab.id ? 'bg-red-100 text-red-800' : 'bg-gray-200 text-gray-600'
                      }`}>
                        {tab.count}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-6">
              {/* Tab: Dados Pessoais */}
              {activeTab === 'dados' && (
                <div className="space-y-6">
                  <div className="bg-gray-50 rounded-xl p-6">
                    <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                      <User className="w-5 h-5 text-gray-600" />
                      Dados Pessoais
                    </h3>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                      <div><p className="text-gray-500">CPF</p><p className="font-medium">{c.dados.cpf}</p></div>
                      <div><p className="text-gray-500">RG</p><p className="font-medium">{c.dados.rg}</p></div>
                      <div><p className="text-gray-500">Nascimento</p><p className="font-medium">{c.dados.data_nascimento}</p></div>
                      <div><p className="text-gray-500">Telefone</p><p className="font-medium">{c.dados.telefone}</p></div>
                      <div><p className="text-gray-500">Estado Civil</p><p className="font-medium capitalize">{c.dados.estado_civil}</p></div>
                      <div><p className="text-gray-500">Profissão</p><p className="font-medium">{c.dados.profissao}</p></div>
                      <div className="md:col-span-3"><p className="text-gray-500">Endereço</p><p className="font-medium">{c.dados.endereco_completo}</p></div>
                    </div>
                  </div>

                  <div className="bg-gray-50 rounded-xl p-6">
                    <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                      <Briefcase className="w-5 h-5 text-gray-600" />
                      Demanda Original
                    </h3>
                    <div className="space-y-4 text-sm">
                      <div><p className="text-gray-500">Tipo</p><p className="font-medium">{tiposDemanda[c.dados.tipo_demanda]}</p></div>
                      <div><p className="text-gray-500">Objeto do Contrato</p><p className="font-medium mt-1">{c.dados.objeto_contrato || c.dados.poderes_especificos}</p></div>
                      {c.dados.observacoes && <div><p className="text-gray-500">Observações</p><p className="font-medium mt-1">{c.dados.observacoes}</p></div>}
                    </div>
                  </div>

                  {/* Dados da Residência Médica - Apenas para Auxílio Moradia */}
                  {c.dados.tipo_demanda === 'auxilio_moradia_residencia' && (
                    <div className="bg-blue-50 rounded-xl p-6">
                      <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                        <Building className="w-5 h-5 text-blue-600" />
                        Dados da Residência Médica
                      </h3>
                      {dadosDemanda && dadosDemanda.dados ? (
                        <>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                            <div>
                              <p className="text-gray-500">Instituição de Ensino</p>
                              <p className="font-medium">{dadosDemanda.dados.instituicao_ensino || '-'}</p>
                            </div>
                            <div>
                              <p className="text-gray-500">Unidade Hospitalar</p>
                              <p className="font-medium">{dadosDemanda.dados.unidade_hospitalar || '-'}</p>
                            </div>
                            <div>
                              <p className="text-gray-500">Especialidade</p>
                              <p className="font-medium">{dadosDemanda.dados.especialidade_medica || '-'}</p>
                            </div>
                            <div>
                              <p className="text-gray-500">Início da Residência</p>
                              <p className="font-medium">{dadosDemanda.dados.data_inicio_residencia || '-'}</p>
                            </div>
                            <div>
                              <p className="text-gray-500">Término da Residência</p>
                              <p className="font-medium">{dadosDemanda.dados.data_termino_residencia || '-'}</p>
                            </div>
                            <div>
                              <p className="text-gray-500">Valor da Bolsa</p>
                              <p className="font-medium">{dadosDemanda.dados.valor_bolsa_mensal || '-'}</p>
                            </div>
                            <div>
                              <p className="text-gray-500">Recebeu Moradia?</p>
                              <p className="font-medium">{dadosDemanda.dados.recebeu_moradia ? 'Sim' : 'Não'}</p>
                            </div>
                            {dadosDemanda.dados.processo_anterior && (
                              <>
                                <div>
                                  <p className="text-gray-500">Processo Anterior</p>
                                  <p className="font-medium">{dadosDemanda.dados.numero_processo_anterior}</p>
                                </div>
                                <div>
                                  <p className="text-gray-500">Vara/Juizado Anterior</p>
                                  <p className="font-medium">{dadosDemanda.dados.vara_juizado_anterior}</p>
                                </div>
                              </>
                            )}
                            {dadosDemanda.dados.dados_bancarios && (
                              <div className="md:col-span-3">
                                <p className="text-gray-500">Dados Bancários</p>
                                <p className="font-medium">{dadosDemanda.dados.dados_bancarios}</p>
                              </div>
                            )}
                          </div>
                          
                          {/* Botão de Gerar Petição */}
                          <div className="mt-6 pt-4 border-t border-blue-200">
                            <div className="flex flex-wrap gap-3">
                              {!c.arquivos_gerados?.peticao_auxilio_moradia ? (
                                <button
                                  onClick={() => gerarPeticaoAuxilioMoradia(c.id)}
                                  disabled={gerandoPeticao}
                                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg disabled:opacity-50"
                                >
                                  {gerandoPeticao ? (
                                    <>
                                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                      Gerando Petição...
                                    </>
                                  ) : (
                                    <>
                                      <Scale className="w-4 h-4" />
                                      Gerar Petição Inicial
                                    </>
                                  )}
                                </button>
                              ) : (
                                <>
                                  <button
                                    onClick={() => baixarPeticaoAuxilioMoradia(c.id)}
                                    className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white font-medium px-4 py-2 rounded-lg"
                                  >
                                    <Download className="w-4 h-4" />
                                    Baixar Petição
                                  </button>
                                  <button
                                    onClick={() => gerarPeticaoAuxilioMoradia(c.id)}
                                    disabled={gerandoPeticao}
                                    className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white font-medium px-4 py-2 rounded-lg disabled:opacity-50"
                                  >
                                    {gerandoPeticao ? (
                                      <>
                                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                        Gerando...
                                      </>
                                    ) : (
                                      <>
                                        <RefreshCw className="w-4 h-4" />
                                        Regerar Petição
                                      </>
                                    )}
                                  </button>
                                </>
                              )}
                            </div>
                          </div>
                        </>
                      ) : (
                        <div className="text-center py-4">
                          <p className="text-gray-500">Carregando dados da residência médica...</p>
                          <p className="text-xs text-gray-400 mt-2">Se os dados não aparecerem, verifique se foram preenchidos no cadastro.</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Ações */}
                  <div className="flex flex-wrap gap-3">
                    {c.status === 'pendente' && (
                      <button
                        onClick={() => handleValidar(c.id)}
                        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg"
                      >
                        <Check className="w-4 h-4" />
                        Validar Cadastro
                      </button>
                    )}
                    {(c.status === 'validado' || c.status === 'pendente') && (
                      <button
                        onClick={() => handleGerarDocumentos(c.id)}
                        disabled={gerandoDocs}
                        className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-medium px-4 py-2 rounded-lg disabled:opacity-50"
                      >
                        {gerandoDocs ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            Gerando...
                          </>
                        ) : (
                          <>
                            <FileText className="w-4 h-4" />
                            Gerar Documentos
                          </>
                        )}
                                      </button>
                    )}
                    <button
                      onClick={() => setShowModalSolicitarAtualizacao(true)}
                      className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white font-medium px-4 py-2 rounded-lg"
                    >
                      <RefreshCw className="w-4 h-4" />
                      Solicitar Atualização
                    </button>
                    <button
                      onClick={() => handleDeletar(c.id)}
                      className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white font-medium px-4 py-2 rounded-lg"
                    >
                      <Trash2 className="w-4 h-4" />
                      Excluir Cadastro
                    </button>
                  </div>
                </div>
              )}

              {/* Tab: Processos */}
              {activeTab === 'processos' && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold text-gray-800">Processos do Cliente</h3>
                    <button
                      onClick={() => { setProcessoSelecionado(null); setShowProcessoModal(true); }}
                      className="flex items-center gap-2 bg-red-800 hover:bg-red-900 text-white font-medium px-4 py-2 rounded-lg"
                    >
                      <Plus className="w-4 h-4" />
                      Novo Processo
                    </button>
                  </div>

                  {processos.length === 0 ? (
                    <div className="text-center py-12 bg-gray-50 rounded-xl">
                      <Gavel className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                      <p className="text-gray-500">Nenhum processo cadastrado</p>
                      <p className="text-gray-400 text-sm mt-1">Clique em "Novo Processo" para adicionar</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {processos.map((processo) => (
                        <div key={processo.id} className="border rounded-xl overflow-hidden">
                          <div 
                            className="bg-gray-50 p-4 cursor-pointer hover:bg-gray-100"
                            onClick={() => {
                              if (processoExpandido === processo.id) {
                                setProcessoExpandido(null)
                              } else {
                                setProcessoExpandido(processo.id)
                                if (!processo.andamentos) {
                                  carregarAndamentos(processo.id)
                                }
                              }
                            }}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex-1">
                                <div className="flex items-center gap-3">
                                  <span className="font-mono text-sm bg-white px-2 py-1 rounded border">
                                    {processo.numero_processo || 'Sem número'}
                                  </span>
                                  <span className={`px-2 py-1 text-xs rounded-full ${
                                    processo.status === 'ativo' ? 'bg-green-100 text-green-800' :
                                    processo.status === 'arquivado' ? 'bg-gray-100 text-gray-800' :
                                    'bg-red-100 text-red-800'
                                  }`}>
                                    {processo.status}
                                  </span>
                                </div>
                                <div className="mt-2 text-sm text-gray-600">
                                  <span className="font-medium">{processo.tipo_acao}</span>
                                  {processo.vara_tribunal && <span> • {processo.vara_tribunal}</span>}
                                </div>
                                <div className="mt-1 text-sm text-gray-500">
                                  Fase: <span className="font-medium">{processo.fase}</span>
                                  {processo.valor_causa > 0 && (
                                    <span> • Valor: <span className="font-medium">{formatMoney(processo.valor_causa)}</span></span>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={(e) => { e.stopPropagation(); setProcessoSelecionado(processo); setShowProcessoModal(true); }}
                                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                                  title="Editar"
                                >
                                  <Edit className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={(e) => { e.stopPropagation(); handleDeletarProcesso(processo.id); }}
                                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                                  title="Excluir"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                                {processoExpandido === processo.id ? (
                                  <ChevronUp className="w-5 h-5 text-gray-400" />
                                ) : (
                                  <ChevronDown className="w-5 h-5 text-gray-400" />
                                )}
                              </div>
                            </div>
                          </div>

                          {processoExpandido === processo.id && (
                            <div className="p-4 border-t bg-white">
                              <div className="flex justify-between items-center mb-4">
                                <h4 className="font-medium text-gray-700">Andamentos</h4>
                                <button
                                  onClick={() => { setProcessoParaAndamento(processo.id); setShowAndamentoModal(true); }}
                                  className="flex items-center gap-1 text-sm text-red-700 hover:text-red-800"
                                >
                                  <Plus className="w-4 h-4" />
                                  Novo Andamento
                                </button>
                              </div>

                              {processo.andamentos && processo.andamentos.length > 0 ? (
                                <div className="space-y-3">
                                  {processo.andamentos.map((and) => (
                                    <div key={and.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                                      <div className="flex-shrink-0 w-20 text-sm text-gray-500">
                                        {formatDate(and.data)}
                                      </div>
                                      <div className="flex-1">
                                        <p className="text-sm text-gray-700">{and.descricao}</p>
                                        {!and.visivel_cliente && (
                                          <span className="text-xs text-amber-600 mt-1 inline-block">
                                            (Oculto para o cliente)
                                          </span>
                                        )}
                                      </div>
                                      <button
                                        onClick={() => handleDeletarAndamento(and.id, processo.id)}
                                        className="p-1 text-gray-400 hover:text-red-600"
                                      >
                                        <X className="w-4 h-4" />
                                      </button>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className="text-gray-500 text-sm text-center py-4">Nenhum andamento registrado</p>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab: Contratos */}
              {activeTab === 'contratos' && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <h3 className="font-semibold text-gray-800">Contratos de Honorários</h3>
                    <button
                      onClick={() => { setContratoSelecionado(null); setShowContratoModal(true); }}
                      className="flex items-center gap-2 bg-red-800 hover:bg-red-900 text-white font-medium px-4 py-2 rounded-lg"
                    >
                      <Plus className="w-4 h-4" />
                      Novo Contrato
                    </button>
                  </div>

                  {contratos.length === 0 ? (
                    <div className="text-center py-12 bg-gray-50 rounded-xl">
                      <CreditCard className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                      <p className="text-gray-500">Nenhum contrato cadastrado</p>
                      <p className="text-gray-400 text-sm mt-1">Clique em "Novo Contrato" para adicionar</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {contratos.map((contrato) => (
                        <div key={contrato.id} className="border rounded-xl overflow-hidden">
                          <div className="bg-gray-50 p-4">
                            <div className="flex items-start justify-between">
                              <div>
                                <div className="flex items-center gap-2">
                                  <h4 className="font-medium text-gray-800">{contrato.descricao || 'Contrato de Honorários'}</h4>
                                  <span className={`px-2 py-0.5 text-xs rounded-full ${
                                    contrato.tipo === 'fixo' ? 'bg-blue-100 text-blue-800' :
                                    contrato.tipo === 'parcelado' ? 'bg-purple-100 text-purple-800' :
                                    'bg-green-100 text-green-800'
                                  }`}>
                                    {contrato.tipo === 'fixo' ? 'À Vista' : contrato.tipo === 'parcelado' ? 'Parcelado' : 'Mensal'}
                                  </span>
                                </div>
                                {contrato.processo_numero && (
                                  <p className="text-sm text-gray-500 mt-1">
                                    Processo: {contrato.processo_numero}
                                  </p>
                                )}
                                <div className="flex items-center gap-4 mt-2 text-sm">
                                  {contrato.tipo === 'mensal' ? (
                                    <span className="font-medium text-gray-700">
                                      {formatMoney(contrato.valor_mensal)}/mês
                                    </span>
                                  ) : (
                                    <span className="font-medium text-gray-700">
                                      {formatMoney(contrato.valor_total)}
                                      {contrato.tipo === 'parcelado' && ` em ${contrato.num_parcelas}x`}
                                    </span>
                                  )}
                                  {contrato.percentual_exito > 0 && (
                                    <span className="text-amber-700">
                                      + {contrato.percentual_exito}% êxito
                                    </span>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => { setContratoSelecionado(contrato); setShowContratoModal(true); }}
                                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                                  title="Editar"
                                >
                                  <Edit className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleDeletarContrato(contrato.id)}
                                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                                  title="Excluir"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </div>
                          </div>

                          {/* Parcelas */}
                          {contrato.parcelas && contrato.parcelas.length > 0 && (
                            <div className="p-4 border-t">
                              <h5 className="text-sm font-medium text-gray-700 mb-3">Parcelas</h5>
                              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                                {contrato.parcelas.map((parcela) => (
                                  <div 
                                    key={parcela.id} 
                                    className={`flex items-center justify-between p-3 rounded-lg border ${
                                      parcela.status === 'pago' ? 'bg-green-50 border-green-200' :
                                      new Date(parcela.vencimento) < new Date() ? 'bg-red-50 border-red-200' :
                                      'bg-gray-50 border-gray-200'
                                    }`}
                                  >
                                    <div>
                                      <div className="flex items-center gap-2">
                                        <span className="text-sm font-medium">Parcela {parcela.numero}</span>
                                        {parcela.status === 'pago' && <CheckCircle className="w-4 h-4 text-green-600" />}
                                      </div>
                                      <p className="text-xs text-gray-500">
                                        {formatDate(parcela.vencimento)} • {formatMoney(parcela.valor)}
                                      </p>
                                    </div>
                                    {parcela.status !== 'pago' && (
                                      <button
                                        onClick={() => handleMarcarParcela(parcela.id)}
                                        className="text-xs text-green-700 hover:text-green-800 font-medium"
                                      >
                                        Marcar Pago
                                      </button>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab: Documentos */}
              {activeTab === 'documentos' && (
                <div className="space-y-6">
                  {/* Sub-abas horizontais de Documentos */}
                  <div className="border-b border-gray-200">
                    <nav className="flex space-x-1 -mb-px" aria-label="Sub-abas de documentos">
                      <button
                        onClick={() => setActiveDocTab('gerar')}
                        className={`px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
                          activeDocTab === 'gerar'
                            ? 'border-red-800 text-red-800 bg-red-50'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <span className="flex items-center gap-2">
                          <FileCheck className="w-4 h-4" />
                          Gerar / Assinar
                        </span>
                      </button>
                      <button
                        onClick={() => setActiveDocTab('cliente')}
                        className={`px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
                          activeDocTab === 'cliente'
                            ? 'border-red-800 text-red-800 bg-red-50'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <span className="flex items-center gap-2">
                          <FolderOpen className="w-4 h-4" />
                          Do Cliente
                        </span>
                      </button>
                      <button
                        onClick={() => setActiveDocTab('demanda')}
                        className={`px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
                          activeDocTab === 'demanda'
                            ? 'border-red-800 text-red-800 bg-red-50'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <span className="flex items-center gap-2">
                          <Briefcase className="w-4 h-4" />
                          Da Demanda
                        </span>
                      </button>
                      <button
                        onClick={() => setActiveDocTab('assinados')}
                        className={`px-4 py-2.5 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
                          activeDocTab === 'assinados'
                            ? 'border-red-800 text-red-800 bg-red-50'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        <span className="flex items-center gap-2">
                          <CheckCircle className="w-4 h-4" />
                          Assinados
                          {c.documentos_assinados && c.documentos_assinados.length > 0 && (
                            <span className="bg-emerald-500 text-white text-xs rounded-full px-2 py-0.5">
                              {c.documentos_assinados.length}
                            </span>
                          )}
                        </span>
                      </button>
                    </nav>
                  </div>

                  {/* Sub-aba: Gerar / Assinar */}
                  {activeDocTab === 'gerar' && (
                    <div className="space-y-6">
                      {/* Ações */}
                      <div className="flex flex-wrap gap-3">
                    {c.status === 'validado' && (
                      <button
                        onClick={() => handleGerarDocumentos(c.id)}
                        disabled={gerandoDocs}
                        className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-medium px-4 py-2 rounded-lg disabled:opacity-50"
                      >
                        {gerandoDocs ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                            Gerando...
                          </>
                        ) : (
                          <>
                            <FileText className="w-4 h-4" />
                            Gerar Documentos
                          </>
                        )}
                      </button>
                    )}
                    {c.arquivos_gerados && (c.arquivos_gerados.contrato || c.arquivos_gerados.procuracao) && (
                      <button
                        onClick={() => setShowEnviarEmailModal(true)}
                        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg"
                      >
                        <Mail className="w-4 h-4" />
                        Enviar por E-mail
                      </button>
                    )}
                  </div>

                  {/* Seção de Assinatura Digital */}
                  {c.arquivos_gerados && (c.arquivos_gerados.contrato || c.arquivos_gerados.procuracao) && (
                    <div className="bg-green-50 rounded-xl p-6">
                      <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                        <FileCheck className="w-5 h-5 text-green-600" />
                        Assinatura Digital
                      </h3>

                      {/* Aviso se não tiver documentos finais */}
                      {(!documentosFinais.contrato && c.arquivos_gerados.contrato) || (!documentosFinais.procuracao && c.arquivos_gerados.procuracao) ? (
                        <div className="bg-amber-100 border border-amber-300 rounded-lg p-4 mb-4">
                          <p className="text-amber-800 text-sm flex items-start gap-2">
                            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                            <span>
                              <strong>Atenção:</strong> Antes de enviar para assinatura, você deve:
                              <br />1. Baixar o documento gerado
                              <br />2. Editar (preencher honorários, etc.)
                              <br />3. Fazer upload da versão final na seção "Documentos Gerados" acima
                            </span>
                          </p>
                        </div>
                      ) : null}

                      <p className="text-sm text-gray-600 mb-4">
                        Envie os documentos finais para assinatura digital via ZapSign.
                      </p>
                      <div className="flex flex-wrap gap-3">
                        {c.arquivos_gerados.contrato && (
                          <button
                            onClick={() => handleEnviarParaAssinatura(c.id, 'contrato')}
                            disabled={enviandoParaAssinatura || !documentosFinais.contrato}
                            title={!documentosFinais.contrato ? 'Faça upload da versão final do contrato primeiro' : 'Enviar contrato para assinatura'}
                            className={`flex items-center gap-2 font-medium px-4 py-2 rounded-lg disabled:opacity-50 ${
                              documentosFinais.contrato
                                ? 'bg-red-800 hover:bg-red-900 text-white'
                                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            }`}
                          >
                            {enviandoParaAssinatura ? (
                              <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                Enviando...
                              </>
                            ) : (
                              <>
                                <FileCheck className="w-4 h-4" />
                                {documentosFinais.contrato ? 'Enviar Contrato (ZapSign)' : 'Contrato (aguardando upload)'}
                              </>
                            )}
                          </button>
                        )}
                        {c.arquivos_gerados.procuracao && (
                          <button
                            onClick={() => handleEnviarParaAssinatura(c.id, 'procuracao')}
                            disabled={enviandoParaAssinatura || !documentosFinais.procuracao}
                            title={!documentosFinais.procuracao ? 'Faça upload da versão final da procuração primeiro' : 'Enviar procuração para assinatura'}
                            className={`flex items-center gap-2 font-medium px-4 py-2 rounded-lg disabled:opacity-50 ${
                              documentosFinais.procuracao
                                ? 'bg-red-800 hover:bg-red-900 text-white'
                                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            }`}
                          >
                            {enviandoParaAssinatura ? (
                              <>
                                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                Enviando...
                              </>
                            ) : (
                              <>
                                <FileCheck className="w-4 h-4" />
                                {documentosFinais.procuracao ? 'Enviar Procuração (ZapSign)' : 'Procuração (aguardando upload)'}
                              </>
                            )}
                          </button>
                        )}
                        <a
                          href="https://sso.acesso.gov.br/login?client_id=assinador.iti.br"
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-2 bg-blue-700 hover:bg-blue-800 text-white font-medium px-4 py-2 rounded-lg"
                        >
                          <Shield className="w-4 h-4" />
                          Assinar via Gov.br
                        </a>
                      </div>
                      <p className="text-xs text-gray-500 mt-3">
                        <strong>Gov.br:</strong> Requer conta nível Prata ou Ouro. O cliente faz upload do documento, assina e envia de volta.
                      </p>

                      {/* Seção de Verificação de Assinatura */}
                      {(c.assinaturas_digitais?.contrato || c.assinaturas_digitais?.procuracao) && (
                        <div className="mt-6 pt-6 border-t border-green-200">
                          <h4 className="font-medium text-gray-700 mb-3 flex items-center gap-2">
                            <RefreshCw className="w-4 h-4" />
                            Verificar Status da Assinatura
                          </h4>
                          <p className="text-sm text-gray-600 mb-3">
                            Clique para verificar se o cliente já assinou. Se assinado, o documento será baixado automaticamente.
                          </p>
                          <div className="flex flex-wrap gap-3">
                            {c.assinaturas_digitais?.contrato && (
                              <button
                                onClick={() => handleVerificarEBaixarAssinatura(c.id, 'contrato')}
                                disabled={verificandoAssinatura}
                                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-lg disabled:opacity-50"
                              >
                                {verificandoAssinatura ? (
                                  <>
                                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                    Verificando...
                                  </>
                                ) : (
                                  <>
                                    <RefreshCw className="w-4 h-4" />
                                    Verificar Contrato
                                  </>
                                )}
                              </button>
                            )}
                            {c.assinaturas_digitais?.procuracao && (
                              <button
                                onClick={() => handleVerificarEBaixarAssinatura(c.id, 'procuracao')}
                                disabled={verificandoAssinatura}
                                className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-lg disabled:opacity-50"
                              >
                                {verificandoAssinatura ? (
                                  <>
                                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                    Verificando...
                                  </>
                                ) : (
                                  <>
                                    <RefreshCw className="w-4 h-4" />
                                    Verificar Procuração
                                  </>
                                )}
                              </button>
                            )}
                          </div>
                          {/* Mostrar status se disponível */}
                          {(statusAssinaturaDetalhado.contrato || statusAssinaturaDetalhado.procuracao) && (
                            <div className="mt-3 space-y-2">
                              {statusAssinaturaDetalhado.contrato && (
                                <p className={`text-sm flex items-center gap-2 ${statusAssinaturaDetalhado.contrato.assinado ? 'text-green-700' : 'text-amber-600'}`}>
                                  {statusAssinaturaDetalhado.contrato.assinado ? (
                                    <><CheckCircle className="w-4 h-4" /> Contrato: Assinado</>
                                  ) : (
                                    <><Clock className="w-4 h-4" /> Contrato: {statusAssinaturaDetalhado.contrato.status}</>
                                  )}
                                </p>
                              )}
                              {statusAssinaturaDetalhado.procuracao && (
                                <p className={`text-sm flex items-center gap-2 ${statusAssinaturaDetalhado.procuracao.assinado ? 'text-green-700' : 'text-amber-600'}`}>
                                  {statusAssinaturaDetalhado.procuracao.assinado ? (
                                    <><CheckCircle className="w-4 h-4" /> Procuração: Assinado</>
                                  ) : (
                                    <><Clock className="w-4 h-4" /> Procuração: {statusAssinaturaDetalhado.procuracao.status}</>
                                  )}
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                    </div>
                  )}

                  {/* Sub-aba: Do Cliente */}
                  {activeDocTab === 'cliente' && (
                    <div className="space-y-6">
                  {/* Documentos do Cliente */}
                  <div className="bg-gray-50 rounded-xl p-6">
                    <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                      <FolderOpen className="w-5 h-5 text-gray-600" />
                      Documentos Enviados pelo Cliente ({c.documentos.length})
                    </h3>
                    {c.documentos.length > 0 ? (
                      <div className="space-y-2">
                        {c.documentos.map((doc, i) => (
                          <div key={i} className="flex items-center justify-between bg-white border rounded-lg px-4 py-3">
                            <div className="flex items-center gap-3">
                              <FileText className="w-5 h-5 text-red-600" />
                              <span className="text-sm font-medium">{doc}</span>
                            </div>
                            <a 
                              href={`${API_URL}/api/cadastros/${c.id}/uploads/${encodeURIComponent(doc)}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-blue-600 hover:text-blue-800 text-sm font-medium"
                            >
                              <Download className="w-4 h-4" />
                              Baixar
                            </a>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-gray-500 text-sm">Nenhum documento enviado pelo cliente</p>
                    )}
                  </div>
                    </div>
                  )}

                  {/* Sub-aba: Da Demanda */}
                  {activeDocTab === 'demanda' && (
                    <div className="space-y-6">
                  {/* Documentos Específicos da Demanda */}
                  <div className="bg-blue-50 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                        <Briefcase className="w-5 h-5 text-blue-600" />
                        Documentos Específicos da Demanda ({documentosDemanda.length})
                      </h3>
                      
                      {/* Botão para importar documentos existentes */}
                      {c.documentos && c.documentos.length > 0 && documentosDemanda.length === 0 && (
                        <button
                          onClick={async () => {
                            if (!confirm('Deseja importar os documentos existentes do cliente para a seção de Documentos da Demanda?')) return
                            try {
                              const response = await fetch(`${API_URL}/api/admin/clientes/${c.id}/importar-documentos-demanda`, {
                                method: 'POST',
                                headers: { 'Authorization': `Bearer ${user.token}` }
                              })
                              const data = await response.json()
                              if (response.ok) {
                                setMensagemSucesso(`${data.total_importados} documento(s) importado(s)!`)
                                // Recarregar documentos da demanda
                                const docsResponse = await fetch(`${API_URL}/api/cadastros/${c.id}/documentos-demanda`)
                                if (docsResponse.ok) {
                                  const docsData = await docsResponse.json()
                                  setDocumentosDemanda(docsData.documentos || [])
                                }
                              } else {
                                alert(data.detail || 'Erro ao importar documentos')
                              }
                            } catch (error) {
                              console.error('Erro:', error)
                              alert('Erro ao importar documentos')
                            }
                          }}
                          className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg flex items-center gap-1"
                        >
                          <RefreshCw className="w-3 h-3" />
                          Importar Docs Existentes
                        </button>
                      )}
                    </div>
                    
                    {/* Lista de documentos existentes */}
                    {documentosDemanda.length > 0 ? (
                      <div className="space-y-2 mb-4">
                        {documentosDemanda.map((doc) => (
                          <div key={doc.id} className="flex items-center justify-between bg-white border border-blue-200 rounded-lg px-4 py-3">
                            <div className="flex items-center gap-3">
                              <FileText className="w-5 h-5 text-blue-600" />
                              <div>
                                <span className="text-sm font-medium">{doc.nome_original}</span>
                                {doc.descricao && (
                                  <p className="text-xs text-gray-500">{doc.descricao}</p>
                                )}
                                <p className="text-xs text-gray-400">Tipo: {doc.tipo_documento}</p>
                              </div>
                            </div>
                            <a 
                              href={`${API_URL}/api/cadastros/${c.id}/documentos-demanda/${doc.id}/download`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-blue-600 hover:text-blue-800 text-sm font-medium"
                            >
                              <Download className="w-4 h-4" />
                              Baixar
                            </a>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-gray-500 text-sm mb-4">Nenhum documento específico da demanda cadastrado</p>
                    )}
                    
                    {/* Upload de novos documentos da demanda */}
                    <div className="border-t border-blue-200 pt-4 mt-4">
                      <p className="text-sm text-gray-600 mb-3">Adicionar documento específico da demanda (contracheques, comprovantes de residência, etc.):</p>
                      <div className="flex flex-col sm:flex-row gap-2">
                        <select
                          id="tipo-doc-demanda"
                          className="border border-blue-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          defaultValue=""
                        >
                          <option value="" disabled>Tipo do documento</option>
                          <option value="documentos_pessoais">Documentos Pessoais (RG/CPF/CNH)</option>
                          <option value="certificado_residencia">Certificado/Declaração de Residência Médica</option>
                          <option value="contracheque">Contracheque/Holerite</option>
                          <option value="comprovante_residencia">Comprovante de Endereço</option>
                          <option value="processo_anterior">Cópia de Processo Anterior</option>
                          <option value="declaracao">Declaração</option>
                          <option value="outro">Outro</option>
                        </select>
                        <input
                          type="file"
                          id="upload-doc-demanda"
                          className="hidden"
                          multiple
                          onChange={async (e) => {
                            if (!e.target.files || e.target.files.length === 0) return
                            const tipoDoc = (document.getElementById('tipo-doc-demanda') as HTMLSelectElement).value
                            if (!tipoDoc) {
                              alert('Selecione o tipo do documento')
                              return
                            }
                            
                            for (const file of Array.from(e.target.files)) {
                              const formData = new FormData()
                              formData.append('arquivo', file)
                              formData.append('descricao', tipoDoc === 'outro' ? 'Documento adicional' : tipoDoc)
                              
                              try {
                                const response = await fetch(`${API_URL}/api/cadastros/${c.id}/documento-demanda/${tipoDoc}`, {
                                  method: 'POST',
                                  body: formData
                                })
                                const data = await response.json()
                                if (!response.ok) {
                                  alert(data.detail || 'Erro ao enviar documento')
                                }
                              } catch (error) {
                                console.error('Erro:', error)
                                alert('Erro ao enviar documento')
                              }
                            }
                            
                            // Recarregar documentos da demanda
                            try {
                              const response = await fetch(`${API_URL}/api/cadastros/${c.id}/documentos-demanda`)
                              if (response.ok) {
                                const data = await response.json()
                                setDocumentosDemanda(data.documentos || [])
                              }
                            } catch (err) {
                              console.error('Erro ao recarregar documentos:', err)
                            }
                            
                            e.target.value = ''
                            setMensagemSucesso('Documento(s) enviado(s) com sucesso!')
                          }}
                        />
                        <label
                          htmlFor="upload-doc-demanda"
                          className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg cursor-pointer text-sm"
                        >
                          <Upload className="w-4 h-4" />
                          Selecionar Arquivos
                        </label>
                      </div>
                    </div>
                  </div>
                    </div>
                  )}

                  {/* Documentos Gerados - pertence à sub-aba Gerar/Assinar */}
                  {activeDocTab === 'gerar' && c.arquivos_gerados && (c.arquivos_gerados.contrato || c.arquivos_gerados.procuracao || c.arquivos_gerados.peticao_auxilio_moradia) && (
                    <div className="bg-purple-50 rounded-xl p-6">
                      <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                        <FileCheck className="w-5 h-5 text-purple-600" />
                        Documentos Gerados
                      </h3>
                      <p className="text-sm text-gray-600 mb-4">
                        1. Baixe o documento, 2. Edite (preencha honorários), 3. Faça upload da versão final
                      </p>
                      <div className="space-y-4">
                        {/* Contrato */}
                        {c.arquivos_gerados.contrato && (
                          <div className="bg-white border border-purple-200 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-gray-800">Contrato de Honorários</span>
                              {documentosFinais.contrato ? (
                                <span className="flex items-center gap-1 text-green-600 text-sm">
                                  <CheckCircle className="w-4 h-4" /> Versão final enviada
                                </span>
                              ) : (
                                <span className="flex items-center gap-1 text-amber-600 text-sm">
                                  <AlertCircle className="w-4 h-4" /> Aguardando versão final
                                </span>
                              )}
                            </div>
                            <div className="flex flex-wrap gap-2">
                              <a
                                href={`${API_URL}/api/cadastros/${c.id}/download/contrato`}
                                className="flex items-center gap-2 bg-purple-100 text-purple-700 font-medium px-3 py-1.5 rounded text-sm hover:bg-purple-200"
                              >
                                <Download className="w-4 h-4" />
                                1. Baixar
                              </a>
                              <input
                                type="file"
                                ref={contratoFinalRef}
                                onChange={(e) => e.target.files?.[0] && handleUploadDocumentoFinal(c.id, 'contrato', e.target.files[0])}
                                className="hidden"
                                accept=".pdf,.docx,.doc"
                              />
                              <button
                                onClick={() => contratoFinalRef.current?.click()}
                                disabled={uploadandoDocumento}
                                className="flex items-center gap-2 bg-amber-100 text-amber-700 font-medium px-3 py-1.5 rounded text-sm hover:bg-amber-200 disabled:opacity-50"
                              >
                                <Upload className="w-4 h-4" />
                                {uploadandoDocumento ? 'Enviando...' : '3. Upload Final'}
                              </button>
                            </div>
                          </div>
                        )}
                        {/* Procuração */}
                        {c.arquivos_gerados.procuracao && (
                          <div className="bg-white border border-purple-200 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-gray-800">Procuração</span>
                              {documentosFinais.procuracao ? (
                                <span className="flex items-center gap-1 text-green-600 text-sm">
                                  <CheckCircle className="w-4 h-4" /> Versão final enviada
                                </span>
                              ) : (
                                <span className="flex items-center gap-1 text-amber-600 text-sm">
                                  <AlertCircle className="w-4 h-4" /> Aguardando versão final
                                </span>
                              )}
                            </div>
                            <div className="flex flex-wrap gap-2">
                              <a
                                href={`${API_URL}/api/cadastros/${c.id}/download/procuracao`}
                                className="flex items-center gap-2 bg-purple-100 text-purple-700 font-medium px-3 py-1.5 rounded text-sm hover:bg-purple-200"
                              >
                                <Download className="w-4 h-4" />
                                1. Baixar
                              </a>
                              <input
                                type="file"
                                ref={procuracaoFinalRef}
                                onChange={(e) => e.target.files?.[0] && handleUploadDocumentoFinal(c.id, 'procuracao', e.target.files[0])}
                                className="hidden"
                                accept=".pdf,.docx,.doc"
                              />
                              <button
                                onClick={() => procuracaoFinalRef.current?.click()}
                                disabled={uploadandoDocumento}
                                className="flex items-center gap-2 bg-amber-100 text-amber-700 font-medium px-3 py-1.5 rounded text-sm hover:bg-amber-200 disabled:opacity-50"
                              >
                                <Upload className="w-4 h-4" />
                                {uploadandoDocumento ? 'Enviando...' : '3. Upload Final'}
                              </button>
                            </div>
                          </div>
                        )}
                        {/* Petição Auxílio Moradia */}
                        {c.arquivos_gerados.peticao_auxilio_moradia && (
                          <div className="bg-white border border-purple-200 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-gray-800">Petição Auxílio Moradia</span>
                            </div>
                            <a
                              href={`${API_URL}/api/cadastros/${c.id}/download/peticao_auxilio_moradia`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-2 bg-purple-100 text-purple-700 font-medium px-3 py-1.5 rounded text-sm hover:bg-purple-200"
                            >
                              <Download className="w-4 h-4" />
                              Baixar Petição
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Sub-aba: Assinados */}
                  {activeDocTab === 'assinados' && (
                    <div className="space-y-6">
                      {/* Documentos Assinados */}
                      {c.documentos_assinados && c.documentos_assinados.length > 0 ? (
                        <div className="bg-emerald-50 rounded-xl p-6">
                      <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                        <CheckCircle className="w-5 h-5 text-emerald-600" />
                        Documentos Assinados Recebidos
                      </h3>
                      <div className="space-y-2">
                        {c.documentos_assinados.map((doc, i) => (
                          <div key={i} className="flex items-center justify-between bg-white border border-emerald-200 rounded-lg px-4 py-3">
                            <div className="flex items-center gap-3">
                              <FileCheck className="w-5 h-5 text-emerald-600" />
                              <span className="text-sm font-medium">{doc}</span>
                            </div>
                            <a 
                              href={`${API_URL}/api/cadastros/${c.id}/assinados/${encodeURIComponent(doc)}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-emerald-600 hover:text-emerald-800 text-sm font-medium"
                            >
                              <Download className="w-4 h-4" />
                              Baixar
                            </a>
                          </div>
                        ))}
                      </div>
                        </div>
                      ) : (
                        <div className="bg-gray-50 rounded-xl p-6 text-center">
                          <CheckCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                          <p className="text-gray-500">Nenhum documento assinado recebido ainda</p>
                          <p className="text-sm text-gray-400 mt-1">Os documentos assinados pelo cliente aparecerão aqui</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Documentos Extras - pertence à sub-aba Do Cliente */}
                  {activeDocTab === 'cliente' && documentosExtras.length > 0 && (
                    <div className="bg-amber-50 rounded-xl p-6">
                      <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                        <Upload className="w-5 h-5 text-amber-600" />
                        Documentos Extras Enviados pelo Cliente ({documentosExtras.length})
                      </h3>
                      <div className="space-y-2">
                        {documentosExtras.map((doc) => (
                          <div key={doc.id} className="flex items-center justify-between bg-white border border-amber-200 rounded-lg px-4 py-3">
                            <div className="flex items-center gap-3">
                              <FileText className="w-5 h-5 text-amber-600" />
                              <div>
                                <span className="text-sm font-medium">{doc.nome_original}</span>
                                {doc.descricao && (
                                  <p className="text-xs text-gray-500">{doc.descricao}</p>
                                )}
                                <p className="text-xs text-gray-400">
                                  {new Date(doc.criado_em).toLocaleString('pt-BR')}
                                </p>
                              </div>
                            </div>
                            <a 
                              href={`${API_URL}/api/admin/documentos-extras/${doc.id}/download`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-amber-600 hover:text-amber-800 text-sm font-medium"
                            >
                              <Download className="w-4 h-4" />
                              Baixar
                            </a>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Enviar Documentos - pertence à sub-aba Da Demanda */}
                  {activeDocTab === 'demanda' && (
                    <div className="bg-indigo-50 rounded-xl p-6">
                      <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                        <Upload className="w-5 h-5 text-indigo-600" />
                        Enviar Documentos para o Cliente
                      </h3>
                    <p className="text-sm text-gray-600 mb-4">
                      Envie documentos extras que ficarão disponíveis no portal do cliente.
                    </p>
                    <input
                      type="file"
                      multiple
                      id="upload-docs-admin"
                      className="hidden"
                      onChange={async (e) => {
                        if (!e.target.files || e.target.files.length === 0) return
                        const formData = new FormData()
                        Array.from(e.target.files).forEach(file => {
                          formData.append('arquivos', file)
                        })
                        try {
                          const response = await fetch(`${API_URL}/api/admin/clientes/${c.id}/enviar-documentos`, {
                            method: 'POST',
                            headers: { 'Authorization': `Bearer ${user.token}` },
                            body: formData
                          })
                          const data = await response.json()
                          if (response.ok && data.success) {
                            setMensagemSucesso(`${data.arquivos.length} documento(s) enviado(s)!`)
                            // Recarregar cadastro
                            const cadResponse = await fetch(`${API_URL}/api/cadastros/${c.id}`)
                            if (cadResponse.ok) {
                              const cadData = await cadResponse.json()
                              setSelectedCadastro(cadData)
                            }
                          } else {
                            alert(data.detail || 'Erro ao enviar')
                          }
                        } catch (err) {
                          alert('Erro de conexão')
                        }
                        e.target.value = ''
                      }}
                    />
                    <label
                      htmlFor="upload-docs-admin"
                      className="flex items-center justify-center gap-2 cursor-pointer border-2 border-dashed border-indigo-300 rounded-lg p-4 hover:border-indigo-500 hover:bg-indigo-100 transition-colors"
                    >
                      <Upload className="w-5 h-5 text-indigo-600" />
                      <span className="text-indigo-700 font-medium">Clique para selecionar arquivos</span>
                    </label>
                    </div>
                  )}
                </div>
              )}

              {/* Tab: Mensagens */}
              {activeTab === 'mensagens' && (
                <div className="space-y-4">
                  <h3 className="font-semibold text-gray-800">Mensagens com o Cliente</h3>
                  
                  <div className="bg-gray-50 rounded-xl p-4 h-96 overflow-y-auto">
                    {mensagens.length === 0 ? (
                      <div className="flex items-center justify-center h-full text-gray-500">
                        Nenhuma mensagem ainda
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {mensagens.map((msg) => (
                          <div 
                            key={msg.id} 
                            className={`flex ${msg.remetente === 'escritorio' ? 'justify-end' : 'justify-start'}`}
                          >
                            <div className={`max-w-[80%] rounded-lg p-3 ${
                              msg.remetente === 'escritorio' 
                                ? 'bg-red-800 text-white' 
                                : 'bg-white border'
                            }`}>
                              <p className="text-sm">{msg.texto}</p>
                              <p className={`text-xs mt-1 ${
                                msg.remetente === 'escritorio' ? 'text-red-200' : 'text-gray-400'
                              }`}>
                                {new Date(msg.criado_em).toLocaleString('pt-BR')}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={novaMensagem}
                      onChange={(e) => setNovaMensagem(e.target.value)}
                      placeholder="Digite sua mensagem..."
                      className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800"
                      onKeyPress={(e) => e.key === 'Enter' && handleEnviarMensagem()}
                    />
                    <button
                      onClick={handleEnviarMensagem}
                      disabled={enviandoMensagem || !novaMensagem.trim()}
                      className="bg-red-800 hover:bg-red-900 text-white font-medium px-6 py-2 rounded-lg disabled:opacity-50 flex items-center gap-2"
                    >
                      <Send className="w-4 h-4" />
                      Enviar
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Modais */}
        {showProcessoModal && (
          <ProcessoModal
            cadastroId={c.id}
            processo={processoSelecionado}
            user={user}
            onClose={() => { setShowProcessoModal(false); setProcessoSelecionado(null); }}
            onSave={() => carregarDadosCliente(c.id)}
          />
        )}

        {showContratoModal && (
          <ContratoModal
            cadastroId={c.id}
            processos={processos}
            contrato={contratoSelecionado}
            user={user}
            onClose={() => { setShowContratoModal(false); setContratoSelecionado(null); }}
            onSave={() => carregarDadosCliente(c.id)}
          />
        )}

        {showAndamentoModal && processoParaAndamento && (
          <AndamentoModal
            processoId={processoParaAndamento}
            user={user}
            onClose={() => { setShowAndamentoModal(false); setProcessoParaAndamento(null); }}
            onSave={() => carregarAndamentos(processoParaAndamento)}
          />
        )}

        {showEnviarEmailModal && (
          <EnviarEmailModal
            cadastro={c}
            onClose={() => setShowEnviarEmailModal(false)}
            onSuccess={(msg) => { setMensagemSucesso(msg); setTimeout(() => setMensagemSucesso(''), 8000); }}
          />
        )}

        {/* Modal Solicitar Atualização Cadastral */}
        {showModalSolicitarAtualizacao && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl max-w-md w-full shadow-xl">
              <div className="p-6 border-b">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <RefreshCw className="w-5 h-5 text-amber-500" />
                  Solicitar Atualização Cadastral
                </h3>
              </div>
              <div className="p-6">
                <p className="text-gray-600 mb-4">
                  O cliente <strong>{c.dados.nome}</strong> receberá um e-mail solicitando que atualize seus dados cadastrais.
                </p>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Motivo da solicitação (opcional)
                  </label>
                  <textarea
                    value={motivoSolicitacao}
                    onChange={(e) => setMotivoSolicitacao(e.target.value)}
                    className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                    rows={3}
                    placeholder="Ex: Documento vencido, endereço desatualizado..."
                  />
                </div>
              </div>
              <div className="p-6 border-t bg-gray-50 flex gap-3 justify-end rounded-b-xl">
                <button
                  onClick={() => {
                    setShowModalSolicitarAtualizacao(false)
                    setMotivoSolicitacao('')
                  }}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-100"
                >
                  Cancelar
                </button>
                <button
                  onClick={async () => {
                    setLoadingSolicitacao(true)
                    try {
                      const response = await fetch(
                        `${API_URL}/api/admin/clientes/${c.id}/solicitar-atualizacao`,
                        {
                          method: 'POST',
                          headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${user.token}`
                          },
                          body: JSON.stringify({ motivo: motivoSolicitacao })
                        }
                      )
                      
                      const data = await response.json()
                      
                      if (response.ok) {
                        setMensagemSucesso(`Solicitação enviada com sucesso!${data.email_enviado ? ' O cliente foi notificado por e-mail.' : ''}`)
                        setShowModalSolicitarAtualizacao(false)
                        setMotivoSolicitacao('')
                        setTimeout(() => setMensagemSucesso(''), 5000)
                      } else {
                        alert(data.detail || 'Erro ao solicitar atualização')
                      }
                    } catch (error) {
                      console.error('Erro:', error)
                      alert('Erro ao solicitar atualização. Verifique sua conexão.')
                    } finally {
                      setLoadingSolicitacao(false)
                    }
                  }}
                  disabled={loadingSolicitacao}
                  className="px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50 flex items-center gap-2"
                >
                  {loadingSolicitacao ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    'Enviar Solicitação'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  // Lista de cadastros
  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white shadow-lg">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Logo size="small" />
              <div className="hidden md:block">
                <h1 className="text-xl font-bold">Painel Administrativo</h1>
                <p className="text-gray-300 text-sm">Gestão de Clientes</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right hidden sm:block">
                <p className="font-semibold">{user.nome}</p>
                <p className="text-gray-300 text-sm">{user.email}</p>
              </div>
              <div className="flex items-center gap-2">
                {user.is_admin && (
                  <button
                    onClick={() => setShowBackupModal(true)}
                    className="p-2 bg-white/10 hover:bg-white/20 rounded-lg"
                    title="Backup e Documentos"
                  >
                    <HardDrive className="w-5 h-5" />
                  </button>
                )}
                {user.is_admin && (
                  <button
                    onClick={() => setShowUsuariosModal(true)}
                    className="p-2 bg-white/10 hover:bg-white/20 rounded-lg"
                    title="Gerenciar Usuários"
                  >
                    <Users className="w-5 h-5" />
                  </button>
                )}
                <button
                  onClick={() => setShowAlterarSenhaModal(true)}
                  className="p-2 bg-white/10 hover:bg-white/20 rounded-lg"
                  title="Alterar Senha"
                >
                  <Key className="w-5 h-5" />
                </button>
                <button
                  onClick={onLogout}
                  className="p-2 bg-white/10 hover:bg-white/20 rounded-lg"
                  title="Sair"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                <Users className="w-5 h-5 text-gray-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{cadastros.length}</p>
                <p className="text-gray-500 text-sm">Total</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                <Clock className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{cadastros.filter(c => c.status === 'pendente').length}</p>
                <p className="text-gray-500 text-sm">Pendentes</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <FileCheck className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{cadastros.filter(c => c.status === 'validado').length}</p>
                <p className="text-gray-500 text-sm">Validados</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{cadastros.filter(c => c.status === 'documentos_gerados').length}</p>
                <p className="text-gray-500 text-sm">Docs Prontos</p>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{cadastros.filter(c => c.status === 'enviado' || c.status === 'assinado').length}</p>
                <p className="text-gray-500 text-sm">Concluídos</p>
              </div>
            </div>
          </div>
        </div>

        {/* Card de Atualizações Cadastrais Pendentes */}
        {atualizacoesPendentes.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
            <h3 className="font-semibold text-amber-800 flex items-center gap-2 mb-3">
              <RefreshCw className="w-5 h-5" />
              Atualizações Cadastrais Pendentes
              <span className="bg-amber-500 text-white text-xs px-2 py-1 rounded-full">
                {atualizacoesPendentes.length}
              </span>
            </h3>
            <div className="space-y-2">
              {atualizacoesPendentes.slice(0, 5).map((atualizacao) => (
                <div 
                  key={atualizacao.id}
                  className="bg-white rounded-lg p-3 flex justify-between items-center shadow-sm"
                >
                  <div>
                    <p className="font-medium text-gray-800">{atualizacao.nome_cliente}</p>
                    <p className="text-xs text-gray-500">
                      {atualizacao.tipo === 'solicitada' ? 'Solicitada pelo escritório' : 'Espontânea'} • 
                      {atualizacao.enviado_em ? new Date(atualizacao.enviado_em).toLocaleDateString('pt-BR') : ''}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => verDetalhesAtualizacao(atualizacao)}
                      className="p-2 bg-blue-100 text-blue-600 rounded hover:bg-blue-200"
                      title="Ver detalhes"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => aprovarAtualizacao(atualizacao.id)}
                      className="p-2 bg-green-100 text-green-600 rounded hover:bg-green-200"
                      title="Aprovar"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => {
                        setAtualizacaoSelecionada(atualizacao)
                        setShowModalRejeitar(true)
                      }}
                      className="p-2 bg-red-100 text-red-600 rounded hover:bg-red-200"
                      title="Rejeitar"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
              {atualizacoesPendentes.length > 5 && (
                <p className="text-center text-amber-700 text-sm pt-2">
                  + {atualizacoesPendentes.length - 5} atualizações pendentes
                </p>
              )}
            </div>
          </div>
        )}

        {/* Filtros */}
        <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="w-5 h-5 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Buscar por nome ou CPF..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-400" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
              >
                <option value="todos">Todos os status</option>
                <option value="pendente">Pendentes</option>
                <option value="validado">Validados</option>
                <option value="documentos_gerados">Docs Prontos</option>
                <option value="enviado">Enviados</option>
                <option value="assinado">Assinados</option>
              </select>
            </div>
            <a
              href={`${API_URL}/api/cadastros/exportar/excel`}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white font-medium px-4 py-2 rounded-lg transition-colors"
            >
              <FileSpreadsheet className="w-5 h-5" />
              <span className="hidden sm:inline">Exportar Excel</span>
              <span className="sm:hidden">Excel</span>
            </a>
          </div>
        </div>

        {/* Lista */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          {loading ? (
            <div className="text-center py-12">
              <div className="w-8 h-8 border-2 border-red-800 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-gray-500">Carregando...</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Cliente</th>
                    <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600 hidden md:table-cell">Tipo de Demanda</th>
                    <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600 hidden sm:table-cell">Data</th>
                    <th className="text-left px-6 py-4 text-sm font-semibold text-gray-600">Status</th>
                    <th className="text-right px-6 py-4 text-sm font-semibold text-gray-600">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {filteredCadastros.map((c) => (
                    <tr key={c.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div>
                          <p className="font-medium text-gray-800">{c.dados.nome}</p>
                          <p className="text-sm text-gray-500">{c.dados.email}</p>
                        </div>
                      </td>
                      <td className="px-6 py-4 hidden md:table-cell">
                        <span className="text-sm text-gray-600">{tiposDemanda[c.dados.tipo_demanda]}</span>
                      </td>
                      <td className="px-6 py-4 hidden sm:table-cell">
                        <span className="text-sm text-gray-600">{c.data}</span>
                      </td>
                      <td className="px-6 py-4">{getStatusBadge(c.status)}</td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => setSelectedCadastro(c)}
                          className="inline-flex items-center gap-1 text-red-700 hover:text-red-800 font-medium text-sm"
                        >
                          <Eye className="w-4 h-4" />
                          Ver detalhes
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {filteredCadastros.length === 0 && (
                <div className="text-center py-12">
                  <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">Nenhum cadastro encontrado</p>
                </div>
              )}
            </div>
          )}
        </div>

        <p className="text-center text-gray-400 text-xs mt-8">
          © {new Date().getFullYear()} Vaucher e Álvares Sociedade de Advogados — Painel Administrativo
        </p>
      </div>

      {/* Modais */}
      {showUsuariosModal && (
        <UsuariosModal user={user} onClose={() => setShowUsuariosModal(false)} />
      )}

      {showAlterarSenhaModal && (
        <AlterarSenhaModal user={user} onClose={() => setShowAlterarSenhaModal(false)} />
      )}
      {showBackupModal && (
        <BackupModal user={user} onClose={() => setShowBackupModal(false)} />
      )}

      {/* Modal Ver Atualização */}
      {showModalVerAtualizacao && atualizacaoSelecionada && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-auto shadow-xl">
            <div className="p-6 border-b flex justify-between items-center sticky top-0 bg-white">
              <h3 className="text-lg font-semibold">Detalhes da Atualização Cadastral</h3>
              <button 
                onClick={() => setShowModalVerAtualizacao(false)} 
                className="p-2 hover:bg-gray-100 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6">
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <p className="font-medium text-gray-800">{atualizacaoSelecionada.nome_cliente}</p>
                <p className="text-sm text-gray-500">
                  {atualizacaoSelecionada.tipo === 'solicitada' ? 'Solicitada pelo escritório' : 'Atualização espontânea'}
                  {atualizacaoSelecionada.enviado_em && (
                    <> • Enviada em {new Date(atualizacaoSelecionada.enviado_em).toLocaleDateString('pt-BR')}</>
                  )}
                </p>
              </div>
              
              {atualizacaoSelecionada.motivo_solicitacao && (
                <div className="mb-4">
                  <h4 className="font-medium text-gray-700 mb-2">Motivo da Solicitação:</h4>
                  <p className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-amber-800">
                    {atualizacaoSelecionada.motivo_solicitacao}
                  </p>
                </div>
              )}
              
              <h4 className="font-medium text-gray-700 mb-3">Dados Novos Informados:</h4>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
                {atualizacaoSelecionada.dados_novos && Object.keys(atualizacaoSelecionada.dados_novos).length > 0 ? (
                  <div className="space-y-2">
                    {Object.entries(atualizacaoSelecionada.dados_novos).map(([key, value]) => (
                      value && (
                        <div key={key} className="flex justify-between py-1 border-b border-green-100 last:border-0">
                          <span className="text-gray-600 capitalize">{key.replace(/_/g, ' ')}:</span>
                          <span className="font-medium text-gray-800">{String(value)}</span>
                        </div>
                      )
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500">Nenhum dado informado</p>
                )}
              </div>

              {atualizacaoSelecionada.dados_atuais && (
                <>
                  <h4 className="font-medium text-gray-700 mb-3">Dados Atuais (para comparação):</h4>
                  <div className="bg-gray-100 border border-gray-200 rounded-lg p-4 mb-4">
                    <div className="space-y-2 text-sm">
                      {['telefone', 'celular', 'email', 'endereco', 'numero', 'complemento', 'bairro', 'cidade', 'estado', 'cep'].map((campo) => (
                        atualizacaoSelecionada.dados_atuais?.[campo] && (
                          <div key={campo} className="flex justify-between py-1 border-b border-gray-200 last:border-0">
                            <span className="text-gray-500 capitalize">{campo.replace(/_/g, ' ')}:</span>
                            <span className="text-gray-700">{atualizacaoSelecionada.dados_atuais[campo]}</span>
                          </div>
                        )
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
            <div className="p-6 border-t bg-gray-50 flex justify-end gap-3 sticky bottom-0">
              <button
                onClick={() => {
                  setShowModalRejeitar(true)
                }}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
              >
                Rejeitar
              </button>
              <button
                onClick={() => aprovarAtualizacao(atualizacaoSelecionada.id)}
                className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
              >
                Aprovar e Atualizar Dados
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Rejeitar Atualização */}
      {showModalRejeitar && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
          <div className="bg-white rounded-xl max-w-md w-full shadow-xl">
            <div className="p-6 border-b">
              <h3 className="text-lg font-semibold text-red-600">Rejeitar Atualização</h3>
            </div>
            <div className="p-6">
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Motivo da rejeição (será enviado ao cliente)
                </label>
                <textarea
                  value={motivoRejeicao}
                  onChange={(e) => setMotivoRejeicao(e.target.value)}
                  className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-red-500"
                  rows={3}
                  placeholder="Informe o motivo da rejeição..."
                />
              </div>
            </div>
            <div className="p-6 border-t bg-gray-50 flex gap-3 justify-end rounded-b-xl">
              <button
                onClick={() => {
                  setShowModalRejeitar(false)
                  setMotivoRejeicao('')
                }}
                className="px-4 py-2 border rounded-lg hover:bg-gray-100"
              >
                Cancelar
              </button>
              <button
                onClick={rejeitarAtualizacao}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
              >
                Confirmar Rejeição
              </button>
            </div>
          </div>
        </div>
      )}
        </div>
  )
}

// Página Principal
export default function Home() {
  const [user, setUser] = useState<UserData | null>(null)

  const handleLogin = (userData: UserData) => {
    setUser(userData)
    localStorage.setItem('vaucher_user', JSON.stringify(userData))
  }

  const handleLogout = () => {
    if (user?.token) {
      fetch(`${API_URL}/api/logout`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${user.token}` }
      })
    }
    setUser(null)
    localStorage.removeItem('vaucher_user')
  }

  useEffect(() => {
    const savedUser = localStorage.getItem('vaucher_user')
    if (savedUser) {
      setUser(JSON.parse(savedUser))
    }
  }, [])

  if (!user) {
    return (
      <>
        <LoginScreen onLogin={handleLogin} />
        <PWAInstallPrompt />
      </>
    )
  }

  return (
    <>
      <AdminDashboard user={user} onLogout={handleLogout} />
      <PWAInstallPrompt />
    </>
  )
}
