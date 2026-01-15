'use client'

import { useState, useRef, useEffect } from 'react'
import { Upload, FileCheck, CheckCircle, AlertCircle, X, FileText, Send, ArrowLeft } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const LOGO_URL = "https://raw.githubusercontent.com/Brunsadv/vaucher-sistema/main/backend/static/Vaucher%20e%20Alvares-06.jpg"

const Logo = () => (
  <img 
    src={LOGO_URL} 
    alt="Vaucher & Álvares Advogados" 
    className="h-20 w-auto"
  />
)

interface CadastroInfo {
  id: string
  nome: string
  email: string
  status: string
  data: string
  tipo_demanda: string
  documentos_assinados: string[]
}

export default function EnviarAssinados() {
  const [cadastroId, setCadastroId] = useState('')
  const [cadastro, setCadastro] = useState<CadastroInfo | null>(null)
  const [arquivos, setArquivos] = useState<File[]>([])
  const [enviando, setEnviando] = useState(false)
  const [sucesso, setSucesso] = useState(false)
  const [erro, setErro] = useState('')
  const [buscando, setBuscando] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Verificar se tem ID na URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const id = params.get('id')
    if (id) {
      setCadastroId(id)
      buscarCadastro(id)
    }
  }, [])

  const buscarCadastro = async (id: string) => {
    setBuscando(true)
    setErro('')
    setCadastro(null)

    try {
      const response = await fetch(`${API_URL}/api/cadastros/${id}`)
      
      if (!response.ok) {
        throw new Error('Cadastro não encontrado')
      }

      const data = await response.json()
      setCadastro({
  id: data.id,
  nome: data.dados?.nome || '',
  email: data.dados?.email || '',
  status: data.status,
  data: data.data,
  tipo_demanda: data.dados?.tipo_demanda || '',
  documentos_assinados: data.documentos_assinados || []
})

      if (data.status !== 'enviado' && data.status !== 'assinado') {
        setErro('Você ainda não recebeu os documentos para assinar. Aguarde o envio pelo escritório.')
      }
    } catch (err: any) {
      setErro('Cadastro não encontrado. Verifique o código informado.')
    } finally {
      setBuscando(false)
    }
  }

  const handleBuscar = (e: React.FormEvent) => {
    e.preventDefault()
    if (cadastroId.trim()) {
      buscarCadastro(cadastroId.trim())
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setArquivos(prev => [...prev, ...Array.from(e.target.files!)])
    }
  }

  const removeFile = (index: number) => {
    setArquivos(prev => prev.filter((_, i) => i !== index))
  }

  const handleEnviar = async () => {
    if (!cadastro || arquivos.length === 0) return

    setEnviando(true)
    setErro('')

    try {
      const formData = new FormData()
      arquivos.forEach(file => {
        formData.append('arquivos', file)
      })

      const response = await fetch(`${API_URL}/api/cadastros/${cadastro.id}/enviar-assinados`, {
        body: formData
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setSucesso(true)
      } else {
        setErro(data.detail || 'Erro ao enviar documentos')
      }
    } catch (err) {
      setErro('Erro de conexão. Tente novamente.')
    } finally {
      setEnviando(false)
    }
  }

  // Tela de sucesso
  if (sucesso) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
        <div className="max-w-lg w-full bg-white rounded-2xl shadow-xl p-8 text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-10 h-10 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Documentos Enviados!</h1>
          <p className="text-gray-600 mb-6">
            Seus documentos assinados foram recebidos com sucesso. O escritório entrará em contato em breve.
          </p>
          <p className="text-sm text-gray-500">
            Obrigado pela confiança!
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-center">
            <Logo />
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl shadow-lg p-6 sm:p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
              <Upload className="w-6 h-6 text-red-700" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-800">Enviar Documentos Assinados</h1>
              <p className="text-gray-500 text-sm">Devolva seus documentos assinados para o escritório</p>
            </div>
          </div>

          {/* Buscar cadastro */}
          {!cadastro && (
            <form onSubmit={handleBuscar} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Código do Cadastro
                </label>
                <p className="text-xs text-gray-500 mb-2">
                  O código foi enviado no e-mail de confirmação do cadastro
                </p>
                <input
                  type="text"
                  value={cadastroId}
                  onChange={(e) => setCadastroId(e.target.value)}
                  placeholder="Ex: abc123def456"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                />
              </div>

              {erro && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  {erro}
                </div>
              )}

              <button
                type="submit"
                disabled={buscando || !cadastroId.trim()}
                className="w-full bg-red-800 hover:bg-red-900 text-white font-semibold py-3 px-6 rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {buscando ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Buscando...
                  </>
                ) : (
                  'Buscar Cadastro'
                )}
              </button>
            </form>
          )}

          {/* Cadastro encontrado */}
          {cadastro && (
            <div className="space-y-6">
              {/* Info do cadastro */}
              <div className="bg-gray-50 rounded-xl p-4">
                <h3 className="font-semibold text-gray-800 mb-2">Dados do Cadastro</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><span className="text-gray-500">Nome:</span> <strong>{cadastro.nome}</strong></div>
                  <div><span className="text-gray-500">E-mail:</span> <strong>{cadastro.email}</strong></div>
                  <div><span className="text-gray-500">Data:</span> <strong>{cadastro.data}</strong></div>
                  <div><span className="text-gray-500">Status:</span> <strong className="capitalize">{cadastro.status}</strong></div>
                </div>
                <button
                  onClick={() => { setCadastro(null); setArquivos([]); setErro(''); }}
                  className="text-sm text-red-600 hover:text-red-800 mt-3 flex items-center gap-1"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Buscar outro cadastro
                </button>
              </div>

              {/* Já enviou documentos */}
              {cadastro.documentos_assinados && cadastro.documentos_assinados.length > 0 && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                  <h3 className="font-semibold text-green-800 mb-2 flex items-center gap-2">
                    <CheckCircle className="w-5 h-5" />
                    Documentos já enviados
                  </h3>
                  <ul className="text-sm text-green-700 space-y-1">
                    {cadastro.documentos_assinados.map((doc, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <FileCheck className="w-4 h-4" />
                        {doc}
                      </li>
                    ))}
                  </ul>
                  <p className="text-sm text-green-600 mt-3">
                    Você pode enviar mais documentos se necessário.
                  </p>
                </div>
              )}

              {/* Erro de status */}
              {erro && (
                <div className="bg-amber-50 border border-amber-200 text-amber-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  {erro}
                </div>
              )}

              {/* Upload de arquivos */}
              {(cadastro.status === 'enviado' || cadastro.status === 'assinado') && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Selecione os documentos assinados
                    </label>
                    <p className="text-xs text-gray-500 mb-3">
                      Envie o Contrato de Honorários e a Procuração devidamente assinados
                    </p>

                    <input
                      type="file"
                      multiple
                      ref={fileInputRef}
                      onChange={handleFileSelect}
                      accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                      className="hidden"
                    />

                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full flex items-center justify-center gap-3 px-6 py-8 border-2 border-dashed border-gray-300 rounded-xl text-gray-600 hover:border-red-400 hover:text-red-600 hover:bg-red-50 transition-all"
                    >
                      <Upload className="w-8 h-8" />
                      <div className="text-left">
                        <p className="font-medium">Clique para selecionar arquivos</p>
                        <p className="text-sm text-gray-500">PDF, JPG, PNG, DOC ou DOCX</p>
                      </div>
                    </button>
                  </div>

                  {/* Lista de arquivos */}
                  {arquivos.length > 0 && (
                    <div className="space-y-2">
                      <p className="font-medium text-gray-700">Arquivos selecionados ({arquivos.length}):</p>
                      {arquivos.map((file, index) => (
                        <div key={index} className="flex items-center justify-between bg-green-50 border border-green-200 rounded-lg px-4 py-3">
                          <div className="flex items-center gap-3">
                            <FileText className="w-5 h-5 text-green-600" />
                            <span className="text-sm font-medium truncate max-w-xs">{file.name}</span>
                            <span className="text-xs text-gray-500">
                              {(file.size / 1024 / 1024).toFixed(2)} MB
                            </span>
                          </div>
                          <button
                            onClick={() => removeFile(index)}
                            className="text-gray-400 hover:text-red-600"
                          >
                            <X className="w-5 h-5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Botão enviar */}
                  <button
                    onClick={handleEnviar}
                    disabled={enviando || arquivos.length === 0}
                    className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-6 rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    {enviando ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Enviando...
                      </>
                    ) : (
                      <>
                        <Send className="w-5 h-5" />
                        Enviar Documentos Assinados
                      </>
                    )}
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        {/* Dica de e-mail */}
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-xl p-4">
          <p className="text-sm text-blue-800">
            <strong>Preferir enviar por e-mail?</strong><br />
            Você também pode responder o e-mail que recebeu com os documentos anexados, ou enviar diretamente para <strong>atendimento@vaucherealvares.com</strong>
          </p>
        </div>

        <p className="text-center text-gray-400 text-xs mt-8">
          © {new Date().getFullYear()} Vaucher & Álvares Sociedade de Advogados
        </p>
      </main>
    </div>
  )
}
