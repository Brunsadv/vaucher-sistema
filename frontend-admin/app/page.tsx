'use client'

import { useState, useEffect, useRef } from 'react'
import { FileText, Check, User, Briefcase, FolderOpen, Clock, CheckCircle, Eye, Send, Users, Filter, Search, ArrowLeft, LogOut, FileCheck, AlertCircle, Download, Lock, Mail, Shield, Paperclip, X, FileUp, Upload } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const Logo = () => (
  <div className="flex items-center justify-center gap-1">
    <span className="text-2xl font-bold tracking-wider text-gray-800">VAUCHER</span>
    <svg viewBox="0 0 60 50" className="w-10 h-8">
      <path d="M15 40 Q5 30 15 20 L25 30 Q20 35 15 40 Z" fill="#8B1538"/>
      <path d="M25 30 L35 20 Q45 30 35 40 L25 30 Z" fill="#B91C3C"/>
      <path d="M20 25 Q15 20 20 15 L30 25 Q25 28 20 25 Z" fill="#991B2E"/>
      <path d="M30 25 L40 15 Q45 20 40 25 L30 25 Z" fill="#C92243"/>
    </svg>
    <span className="text-2xl font-bold tracking-wider text-gray-800">ÁLVARES</span>
  </div>
)

interface User {
  nome: string
  email: string
  token: string
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
  }
}

// Tela de Login
const LoginScreen = ({ onLogin }: { onLogin: (user: User) => void }) => {
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
        onLogin({ nome: data.nome, email, token: data.token })
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
            <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-2xl mb-4">
              <Shield className="w-8 h-8 text-red-700" />
            </div>
            <Logo />
            <p className="text-gray-500 text-sm mt-2">Painel Administrativo</p>
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

          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500 text-center mb-2">Credenciais de demonstração:</p>
            <div className="text-xs text-gray-600 space-y-1">
              <p><strong>E-mail:</strong> admin@vaucherealvares.com.br</p>
              <p><strong>Senha:</strong> admin123</p>
            </div>
          </div>
        </div>

        <p className="text-center text-gray-400 text-xs mt-6">
          © {new Date().getFullYear()} Vaucher & Álvares Sociedade de Advogados
        </p>
      </div>
    </div>
  )
}

// Modal de Envio de E-mail
const EmailModal = ({ cadastro, onClose, onSuccess }: { cadastro: Cadastro, onClose: () => void, onSuccess: () => void }) => {
  const [assunto, setAssunto] = useState('Seus Documentos - Vaucher & Álvares Advogados')
  const [mensagem, setMensagem] = useState('')
  const [arquivosParaEnviar, setArquivosParaEnviar] = useState<File[]>([])
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setArquivosParaEnviar(prev => [...prev, ...Array.from(e.target.files!)])
    }
  }

  const removeArquivo = (index: number) => {
    setArquivosParaEnviar(prev => prev.filter((_, i) => i !== index))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const handleEnviar = async () => {
    if (arquivosParaEnviar.length === 0) {
      setErro('Selecione pelo menos um arquivo para enviar')
      return
    }

    setEnviando(true)
    setErro('')

    try {
      const formData = new FormData()
      formData.append('assunto', assunto)
      formData.append('mensagem', mensagem)
      
      arquivosParaEnviar.forEach(file => {
        formData.append('arquivos', file)
      })

      const response = await fetch(`${API_URL}/api/cadastros/${cadastro.id}/enviar-email`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (response.ok && data.success) {
        onSuccess()
        onClose()
      } else {
        setErro(data.detail || data.message || 'Erro ao enviar e-mail')
      }
    } catch (err) {
      setErro('Erro de conexão. Tente novamente.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-gray-800">Enviar Documentos por E-mail</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <X className="w-6 h-6" />
            </button>
          </div>
          <p className="text-gray-500 text-sm mt-1">Para: <strong>{cadastro.dados.email}</strong></p>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Assunto</label>
            <input
              type="text"
              value={assunto}
              onChange={(e) => setAssunto(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Mensagem adicional (opcional)</label>
            <textarea
              value={mensagem}
              onChange={(e) => setMensagem(e.target.value)}
              placeholder="Adicione uma mensagem personalizada..."
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Arquivos para enviar <span className="text-red-600">*</span>
            </label>
            <p className="text-xs text-gray-500 mb-3">
              Faça o download dos documentos acima, edite se necessário, e depois anexe aqui para enviar.
            </p>
            
            <input
              type="file"
              multiple
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept=".doc,.docx,.pdf,.jpg,.jpeg,.png"
              className="hidden"
            />
            
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-2 px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-red-400 hover:text-red-600 w-full justify-center bg-gray-50"
            >
              <Upload className="w-5 h-5" />
              Selecionar arquivos para enviar
            </button>

            {arquivosParaEnviar.length > 0 && (
              <div className="mt-3 space-y-2">
                <p className="text-sm font-medium text-gray-700">Arquivos selecionados ({arquivosParaEnviar.length}):</p>
                {arquivosParaEnviar.map((file, index) => (
                  <div key={index} className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-green-600" />
                      <div>
                        <span className="text-sm text-green-800">{file.name}</span>
                        <span className="text-xs text-green-600 ml-2">{formatFileSize(file.size)}</span>
                      </div>
                    </div>
                    <button onClick={() => removeArquivo(index)} className="text-green-600 hover:text-red-600">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {erro && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {erro}
            </div>
          )}
        </div>

        <div className="p-6 border-t bg-gray-50 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-100"
          >
            Cancelar
          </button>
          <button
            onClick={handleEnviar}
            disabled={enviando || arquivosParaEnviar.length === 0}
            className="flex-1 bg-red-800 hover:bg-red-900 text-white font-semibold px-4 py-2 rounded-lg flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {enviando ? (
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
  )
}

// Dashboard Administrativo
const AdminDashboard = ({ user, onLogout }: { user: User, onLogout: () => void }) => {
  const [cadastros, setCadastros] = useState<Cadastro[]>([])
  const [selectedCadastro, setSelectedCadastro] = useState<Cadastro | null>(null)
  const [filterStatus, setFilterStatus] = useState('todos')
  const [searchTerm, setSearchTerm] = useState('')
  const [gerandoDocs, setGerandoDocs] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [mensagemSucesso, setMensagemSucesso] = useState('')

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
    'outro': 'Outro'
  }

  useEffect(() => {
    carregarCadastros()
  }, [])

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
      enviado: 'bg-green-100 text-green-800 border-green-200'
    }
    const labels: Record<string, string> = {
      pendente: 'Pendente',
      validado: 'Validado',
      documentos_gerados: 'Docs Prontos',
      enviado: 'Enviado'
    }
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${styles[status] || styles.pendente}`}>
        {labels[status] || status}
      </span>
    )
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
        setMensagemSucesso('Documentos gerados com sucesso! Faça o download, edite se necessário, e envie por e-mail.')
        setTimeout(() => setMensagemSucesso(''), 5000)
      }
    } catch (err) {
      console.error('Erro ao gerar:', err)
    } finally {
      setGerandoDocs(false)
    }
  }

  const handleEmailEnviado = () => {
    if (selectedCadastro) {
      setCadastros(prev => prev.map(c => c.id === selectedCadastro.id ? { ...c, status: 'enviado' } : c))
      setSelectedCadastro(prev => prev ? { ...prev, status: 'enviado' } : null)
      setMensagemSucesso('E-mail enviado com sucesso!')
      setTimeout(() => setMensagemSucesso(''), 3000)
    }
  }

  // Visualização de detalhes
  if (selectedCadastro) {
    const c = selectedCadastro
    return (
      <div className="min-h-screen bg-gray-100 py-6 px-4">
        <div className="max-w-4xl mx-auto">
          <button 
            onClick={() => setSelectedCadastro(null)}
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

          <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
            <div className="bg-gradient-to-r from-gray-800 to-gray-900 text-white p-6">
              <div className="flex justify-between items-start">
                <div>
                  <h1 className="text-2xl font-bold">{c.dados.nome}</h1>
                  <p className="text-gray-300 mt-1">{c.dados.email}</p>
                </div>
                {getStatusBadge(c.status)}
              </div>
            </div>

            <div className="p-6 space-y-6">
              {/* Dados Pessoais */}
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

              {/* Demanda */}
              <div className="bg-gray-50 rounded-xl p-6">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <Briefcase className="w-5 h-5 text-gray-600" />
                  Demanda
                </h3>
                <div className="space-y-4 text-sm">
                  <div><p className="text-gray-500">Tipo</p><p className="font-medium">{tiposDemanda[c.dados.tipo_demanda]}</p></div>
                  <div><p className="text-gray-500">Objeto do Contrato / Poderes</p><p className="font-medium mt-1">{c.dados.objeto_contrato || c.dados.poderes_especificos}</p></div>
                  {c.dados.observacoes && <div><p className="text-gray-500">Observações</p><p className="font-medium mt-1">{c.dados.observacoes}</p></div>}
                </div>
              </div>

              {/* Documentos do Cliente */}
              <div className="bg-gray-50 rounded-xl p-6">
                <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <FolderOpen className="w-5 h-5 text-gray-600" />
                  Documentos do Cliente ({c.documentos.length})
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

              {/* Documentos Gerados */}
              {c.arquivos_gerados && (c.arquivos_gerados.contrato || c.arquivos_gerados.procuracao) && (
                <div className="bg-purple-50 rounded-xl p-6">
                  <h3 className="font-semibold text-gray-800 mb-4 flex items-center gap-2">
                    <FileCheck className="w-5 h-5 text-purple-600" />
                    Documentos Gerados
                  </h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Baixe os documentos, edite no Word se necessário, e depois envie por e-mail.
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {c.arquivos_gerados.contrato && (
                      <a
                        href={`${API_URL}/api/cadastros/${c.id}/download/contrato`}
                        className="flex items-center gap-2 bg-white border border-purple-200 text-purple-700 font-medium px-4 py-2 rounded-lg hover:bg-purple-100"
                      >
                        <Download className="w-4 h-4" />
                        Baixar Contrato
                      </a>
                    )}
                    {c.arquivos_gerados.procuracao && (
                      <a
                        href={`${API_URL}/api/cadastros/${c.id}/download/procuracao`}
                        className="flex items-center gap-2 bg-white border border-purple-200 text-purple-700 font-medium px-4 py-2 rounded-lg hover:bg-purple-100"
                      >
                        <Download className="w-4 h-4" />
                        Baixar Procuração
                      </a>
                    )}
                  </div>
                </div>
              )}

              {/* Ações */}
              <div className="border-t pt-6">
                <h3 className="font-semibold text-gray-800 mb-4">Ações</h3>
                <div className="flex flex-wrap gap-3">
                  {c.status === 'pendente' && (
                    <button
                      onClick={() => handleValidar(c.id)}
                      className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-6 py-3 rounded-xl"
                    >
                      <CheckCircle className="w-5 h-5" />
                      Validar Cadastro
                    </button>
                  )}
                  
                  {(c.status === 'validado' || c.status === 'pendente') && !c.arquivos_gerados?.contrato && (
                    <button
                      onClick={() => handleGerarDocumentos(c.id)}
                      disabled={gerandoDocs}
                      className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white font-medium px-6 py-3 rounded-xl disabled:opacity-50"
                    >
                      {gerandoDocs ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          Gerando...
                        </>
                      ) : (
                        <>
                          <FileCheck className="w-5 h-5" />
                          Gerar Documentos
                        </>
                      )}
                    </button>
                  )}

                  {c.status !== 'pendente' && (
                    <button
                      onClick={() => setShowEmailModal(true)}
                      className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white font-medium px-6 py-3 rounded-xl"
                    >
                      <Send className="w-5 h-5" />
                      Enviar por E-mail
                    </button>
                  )}

                  {c.status === 'enviado' && (
                    <div className="flex items-center gap-2 bg-green-100 text-green-800 px-6 py-3 rounded-xl">
                      <CheckCircle className="w-5 h-5" />
                      Documentos enviados para {c.dados.email}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {showEmailModal && (
          <EmailModal
            cadastro={c}
            onClose={() => setShowEmailModal(false)}
            onSuccess={handleEmailEnviado}
          />
        )}
      </div>
    )
  }

  // Lista de cadastros
  return (
    <div className="min-h-screen bg-gray-100">
      <div className="bg-white border-b shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Logo />
              <span className="text-gray-300">|</span>
              <span className="text-gray-600 font-medium">Painel Administrativo</span>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600 hidden sm:block">
                Olá, <strong>{user.nome}</strong>
              </span>
              <button onClick={onLogout} className="flex items-center gap-2 text-gray-500 hover:text-red-700">
                <LogOut className="w-5 h-5" />
                <span className="hidden sm:inline">Sair</span>
              </button>
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
                <p className="text-2xl font-bold">{cadastros.filter(c => c.status === 'enviado').length}</p>
                <p className="text-gray-500 text-sm">Enviados</p>
              </div>
            </div>
          </div>
        </div>

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
              </select>
            </div>
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
          © {new Date().getFullYear()} Vaucher & Álvares Sociedade de Advogados — Painel Administrativo
        </p>
      </div>
    </div>
  )
}

// Página Principal
export default function Home() {
  const [user, setUser] = useState<User | null>(null)

  const handleLogin = (userData: User) => {
    setUser(userData)
    localStorage.setItem('vaucher_user', JSON.stringify(userData))
  }

  const handleLogout = () => {
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
    return <LoginScreen onLogin={handleLogin} />
  }

  return <AdminDashboard user={user} onLogout={handleLogout} />
}
