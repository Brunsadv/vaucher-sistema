'use client'

import { useState } from 'react'
import { ChevronRight, ChevronLeft, Upload, FileText, Check, User, Briefcase, FolderOpen, X, Mail, Send } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const tiposDemanda = [
  { value: 'adicional_insalubridade', label: 'Adicional de Insalubridade', poderes: 'propor ação judicial visando o reconhecimento do direito ao adicional de insalubridade, bem como as diferenças remuneratórias decorrentes' },
  { value: 'adicional_periculosidade', label: 'Adicional de Periculosidade', poderes: 'propor ação judicial visando o reconhecimento do direito ao adicional de periculosidade, bem como as diferenças remuneratórias decorrentes' },
  { value: 'desvio_funcao', label: 'Desvio de Função', poderes: 'propor ação judicial visando o reconhecimento do desvio de função e pagamento das diferenças salariais correspondentes' },
  { value: 'progressao_funcional', label: 'Progressão Funcional', poderes: 'propor ação judicial visando o reconhecimento do direito à progressão funcional e seus efeitos financeiros' },
  { value: 'revisao_aposentadoria', label: 'Revisão de Aposentadoria', poderes: 'propor ação judicial visando a revisão dos proventos de aposentadoria e pagamento das diferenças devidas' },
  { value: 'licenca_premio', label: 'Licença Prêmio', poderes: 'propor ação judicial visando o reconhecimento do direito à licença prêmio ou sua conversão em pecúnia' },
  { value: 'ferias_nao_gozadas', label: 'Férias Não Gozadas', poderes: 'propor ação judicial visando a indenização por férias não gozadas e seus reflexos' },
  { value: 'horas_extras', label: 'Horas Extras', poderes: 'propor ação judicial visando o pagamento de horas extras laboradas e seus reflexos legais' },
  { value: 'reintegracao', label: 'Reintegração', poderes: 'propor ação judicial visando a reintegração ao cargo público e pagamento dos vencimentos do período de afastamento' },
  { value: 'outro', label: 'Outro (especificar)', poderes: '' }
]

const estadosCivis = [
  { value: 'solteiro(a)', label: 'Solteiro(a)' },
  { value: 'casado(a)', label: 'Casado(a)' },
  { value: 'divorciado(a)', label: 'Divorciado(a)' },
  { value: 'viúvo(a)', label: 'Viúvo(a)' },
  { value: 'união estável', label: 'União Estável' }
]

const nacionalidades = [
  { value: 'brasileiro(a)', label: 'Brasileiro(a)' },
  { value: 'estrangeiro(a)', label: 'Estrangeiro(a)' }
]

function formatCPF(value: string) {
  const nums = value.replace(/\D/g, '').slice(0, 11)
  if (nums.length <= 3) return nums
  if (nums.length <= 6) return nums.replace(/(\d{3})(\d+)/, '$1.$2')
  if (nums.length <= 9) return nums.replace(/(\d{3})(\d{3})(\d+)/, '$1.$2.$3')
  return nums.replace(/(\d{3})(\d{3})(\d{3})(\d+)/, '$1.$2.$3-$4')
}

function formatPhone(value: string) {
  const nums = value.replace(/\D/g, '').slice(0, 11)
  if (nums.length <= 2) return nums
  if (nums.length <= 6) return nums.replace(/(\d{2})(\d+)/, '($1) $2')
  if (nums.length <= 10) return nums.replace(/(\d{2})(\d{4})(\d+)/, '($1) $2-$3')
  return nums.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3')
}

function Logo() {
  return (
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
}

function StepIndicator({ step }: { step: number }) {
  return (
    <div className="flex items-center justify-center mb-6">
      {[1, 2, 3, 4].map((s) => (
        <div key={s} className="flex items-center">
          <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all duration-300 ${
            step >= s ? 'bg-red-800 border-red-800 text-white' : 'border-gray-300 text-gray-400'
          }`}>
            {step > s ? <Check className="w-5 h-5" /> : s}
          </div>
          {s < 4 && (
            <div className={`w-12 sm:w-16 h-1 mx-1 sm:mx-2 rounded transition-all duration-300 ${
              step > s ? 'bg-red-800' : 'bg-gray-200'
            }`} />
          )}
        </div>
      ))}
    </div>
  )
}

export default function Home() {
  const [step, setStep] = useState(1)
  const [files, setFiles] = useState<File[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  
  const [nome, setNome] = useState('')
  const [nacionalidade, setNacionalidade] = useState('brasileiro(a)')
  const [estadoCivil, setEstadoCivil] = useState('')
  const [profissao, setProfissao] = useState('')
  const [rg, setRg] = useState('')
  const [cpf, setCpf] = useState('')
  const [dataNascimento, setDataNascimento] = useState('')
  const [enderecoCompleto, setEnderecoCompleto] = useState('')
  const [email, setEmail] = useState('')
  const [telefone, setTelefone] = useState('')
  const [tipoDemanda, setTipoDemanda] = useState('')
  const [poderesEspecificos, setPoderesEspecificos] = useState('')
  const [observacoes, setObservacoes] = useState('')

  const handleTipoDemandaChange = (value: string) => {
    setTipoDemanda(value)
    const demanda = tiposDemanda.find(t => t.value === value)
    if (demanda && demanda.poderes) {
      setPoderesEspecificos(demanda.poderes)
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files)
      setFiles(prev => [...prev, ...newFiles])
    }
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setError('')
    
    // OBJETO DO CONTRATO = PODERES ESPECÍFICOS (conforme solicitado)
    const formData = {
      nome,
      nacionalidade,
      estado_civil: estadoCivil,
      profissao,
      rg,
      cpf,
      data_nascimento: dataNascimento,
      endereco_completo: enderecoCompleto,
      email,
      telefone,
      tipo_demanda: tipoDemanda,
      objeto_contrato: poderesEspecificos,  // IGUAL aos poderes específicos
      poderes_especificos: poderesEspecificos,
      observacoes
    }
    
    try {
      // 1. Criar o cadastro
      const response = await fetch(`${API_URL}/api/cadastros`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      
      if (!response.ok) {
        const data = await response.json()
        setError(data.detail || 'Erro ao enviar cadastro')
        setSubmitting(false)
        return
      }

      const result = await response.json()
      const cadastroId = result.id

      // 2. Enviar os arquivos (se houver)
      if (files.length > 0) {
        for (const file of files) {
          const uploadData = new FormData()
          uploadData.append('arquivo', file)
          
          try {
            await fetch(`${API_URL}/api/cadastros/${cadastroId}/upload`, {
              method: 'POST',
              body: uploadData
            })
          } catch (uploadErr) {
            console.error('Erro ao enviar arquivo:', file.name)
          }
        }
      }

      setSubmitted(true)
    } catch (err) {
      setError('Erro de conexão. Tente novamente.')
    } finally {
      setSubmitting(false)
    }
  }

  const canProceed = () => {
    switch(step) {
      case 1:
        return nome && cpf && rg && dataNascimento && estadoCivil && profissao && enderecoCompleto && email && telefone
      case 2:
        return tipoDemanda && poderesEspecificos
      case 3:
        return true
      default:
        return true
    }
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-gray-50 to-red-50 py-6 px-4">
        <div className="max-w-xl mx-auto">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Mail className="w-10 h-10 text-green-600" />
            </div>
            
            <h1 className="text-2xl font-bold text-gray-800 mb-4">Cadastro Enviado com Sucesso!</h1>
            
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
              <p className="text-green-800">
                Enviamos um e-mail de confirmação para:<br/>
                <strong>{email}</strong>
              </p>
            </div>

            <div className="text-left bg-gray-50 rounded-xl p-6 mb-6">
              <h3 className="font-semibold text-gray-800 mb-4">Próximos passos:</h3>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-red-700 font-bold text-sm">1</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-800">Análise dos Dados</p>
                    <p className="text-sm text-gray-500">Nossa equipe verificará as informações enviadas</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-red-700 font-bold text-sm">2</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-800">Geração dos Documentos</p>
                    <p className="text-sm text-gray-500">Contrato e Procuração serão preparados</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-red-700 font-bold text-sm">3</span>
                  </div>
                  <div>
                    <p className="font-medium text-gray-800">Envio por E-mail</p>
                    <p className="text-sm text-gray-500">Você receberá os documentos para assinatura</p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
              <p className="text-amber-800 text-sm">
                <strong>⏱ Prazo estimado:</strong> Até 2 dias úteis para receber os documentos
              </p>
            </div>

            <p className="text-gray-500 text-sm">
              Dúvidas? Entre em contato: <a href="mailto:atendimento@vaucherealvares.com" className="text-red-700 hover:underline">atendimento@vaucherealvares.com</a>
            </p>
          </div>

          <p className="text-center text-gray-400 text-xs mt-6">
            © {new Date().getFullYear()} Vaucher & Álvares Sociedade de Advogados
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-gray-50 to-red-50 py-6 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-6">
          <div className="bg-white rounded-2xl shadow-sm p-6 mb-4 inline-block">
            <Logo />
            <p className="text-xs tracking-widest text-gray-500 mt-1">SOCIEDADE DE ADVOGADOS</p>
          </div>
          <h1 className="text-xl font-bold text-gray-800 mt-4">Cadastro de Cliente</h1>
          <p className="text-gray-500 text-sm mt-1">Preencha seus dados para iniciar o atendimento</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl p-6 sm:p-8">
          <StepIndicator step={step} />
          
          <div className="flex justify-between text-xs text-gray-500 mb-8 px-2">
            <span className={step >= 1 ? 'text-red-800 font-medium' : ''}>Dados Pessoais</span>
            <span className={step >= 2 ? 'text-red-800 font-medium' : ''}>Demanda</span>
            <span className={step >= 3 ? 'text-red-800 font-medium' : ''}>Documentos</span>
            <span className={step >= 4 ? 'text-red-800 font-medium' : ''}>Enviar</span>
          </div>
          
          {step === 1 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-6">
                <User className="w-5 h-5 text-red-800" />
                <h2 className="text-xl font-semibold text-gray-800">Dados Pessoais</h2>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Nome Completo <span className="text-red-600">*</span>
                </label>
                <input
                  type="text"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  placeholder="Digite seu nome completo"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white"
                />
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    CPF <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={cpf}
                    onChange={(e) => setCpf(formatCPF(e.target.value))}
                    placeholder="000.000.000-00"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    RG <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={rg}
                    onChange={(e) => setRg(e.target.value)}
                    placeholder="Número do RG"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Data de Nascimento <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="date"
                    value={dataNascimento}
                    onChange={(e) => setDataNascimento(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Estado Civil <span className="text-red-600">*</span>
                  </label>
                  <select
                    value={estadoCivil}
                    onChange={(e) => setEstadoCivil(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white"
                  >
                    <option value="">Selecione...</option>
                    {estadosCivis.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nacionalidade
                  </label>
                  <select
                    value={nacionalidade}
                    onChange={(e) => setNacionalidade(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white"
                  >
                    {nacionalidades.map((opt) => (
                      <option key={opt.value} value={opt.value}>{opt.label}</option>
                    ))}
                  </select>
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Profissão/Cargo <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={profissao}
                    onChange={(e) => setProfissao(e.target.value)}
                    placeholder="Ex: Técnico de Enfermagem"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white"
                  />
                </div>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Endereço Completo <span className="text-red-600">*</span>
                </label>
                <input
                  type="text"
                  value={enderecoCompleto}
                  onChange={(e) => setEnderecoCompleto(e.target.value)}
                  placeholder="Rua, número, bairro, cidade - UF, CEP"
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white"
                />
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    E-mail <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="seu@email.com"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Telefone <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={telefone}
                    onChange={(e) => setTelefone(formatPhone(e.target.value))}
                    placeholder="(00) 00000-0000"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white"
                  />
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-6">
                <Briefcase className="w-5 h-5 text-red-800" />
                <h2 className="text-xl font-semibold text-gray-800">Informações da Demanda</h2>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo de Demanda <span className="text-red-600">*</span>
                </label>
                <select
                  value={tipoDemanda}
                  onChange={(e) => handleTipoDemandaChange(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white"
                >
                  <option value="">Selecione...</option>
                  {tiposDemanda.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Objeto do Contrato e Poderes da Procuração <span className="text-red-600">*</span>
                </label>
                <textarea
                  value={poderesEspecificos}
                  onChange={(e) => setPoderesEspecificos(e.target.value)}
                  placeholder="Preenchido automaticamente conforme o tipo de demanda. Você pode editar se necessário."
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white resize-none"
                />
                <p className="text-xs text-gray-500 mt-1">Este texto será usado tanto no Contrato quanto na Procuração.</p>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Observações Adicionais
                </label>
                <textarea
                  value={observacoes}
                  onChange={(e) => setObservacoes(e.target.value)}
                  placeholder="Informações complementares que considere relevantes..."
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent transition-all duration-200 bg-white resize-none"
                />
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-6">
                <FolderOpen className="w-5 h-5 text-red-800" />
                <h2 className="text-xl font-semibold text-gray-800">Documentos</h2>
              </div>
              
              <p className="text-gray-600 mb-4">
                Anexe os documentos necessários para análise do caso.
              </p>
              
              <div className="border-2 border-dashed border-gray-300 rounded-xl p-8 text-center hover:border-red-400 transition-colors duration-200 cursor-pointer">
                <input
                  type="file"
                  multiple
                  accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-600 font-medium">Clique para selecionar arquivos</p>
                  <p className="text-gray-400 text-sm mt-1">PDF, JPG, PNG, DOC ou DOCX</p>
                </label>
              </div>
              
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <p className="text-sm font-medium text-amber-800 mb-3">📋 Documentos necessários:</p>
                <ul className="text-sm text-amber-700 space-y-1">
                  <li>• Documento de identidade (RG ou CNH)</li>
                  <li>• Comprovante de residência atualizado</li>
                  <li>• Últimos 3 contracheques</li>
                  <li>• Documentos relacionados à demanda</li>
                </ul>
              </div>
              
              {files.length > 0 && (
                <div className="space-y-2 mt-4">
                  <p className="text-sm font-medium text-gray-700">Arquivos selecionados ({files.length}):</p>
                  {files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between bg-white border border-gray-200 rounded-lg px-4 py-3">
                      <div className="flex items-center gap-3">
                        <FileText className="w-5 h-5 text-red-700" />
                        <div>
                          <p className="text-sm font-medium text-gray-700">{file.name}</p>
                          <p className="text-xs text-gray-400">{formatFileSize(file.size)}</p>
                        </div>
                      </div>
                      <button onClick={() => removeFile(index)} className="text-gray-400 hover:text-red-600">
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {step === 4 && (
            <div className="space-y-6">
              <div className="flex items-center gap-2 mb-6">
                <Send className="w-5 h-5 text-red-800" />
                <h2 className="text-xl font-semibold text-gray-800">Confirmar Envio</h2>
              </div>
              
              <div className="bg-gray-50 rounded-xl p-6 space-y-4">
                <h3 className="font-semibold text-gray-800 border-b border-gray-200 pb-2">Resumo do Cadastro</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                  <div><span className="text-gray-500">Nome:</span> <span className="font-medium block">{nome}</span></div>
                  <div><span className="text-gray-500">CPF:</span> <span className="font-medium">{cpf}</span></div>
                  <div><span className="text-gray-500">E-mail:</span> <span className="font-medium block break-all">{email}</span></div>
                  <div><span className="text-gray-500">Telefone:</span> <span className="font-medium">{telefone}</span></div>
                  <div className="sm:col-span-2">
                    <span className="text-gray-500">Tipo de Demanda:</span> 
                    <span className="font-medium ml-1">{tiposDemanda.find(t => t.value === tipoDemanda)?.label}</span>
                  </div>
                  <div className="sm:col-span-2">
                    <span className="text-gray-500">Documentos anexados:</span> 
                    <span className="font-medium ml-1">{files.length} arquivo(s)</span>
                  </div>
                </div>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <p className="text-red-800 text-sm">{error}</p>
                </div>
              )}

              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                <p className="text-blue-800 text-sm">
                  <strong>📧 Confirmação por e-mail:</strong> Após o envio, você receberá um e-mail confirmando o recebimento do cadastro.
                </p>
              </div>
              
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="w-full bg-red-800 hover:bg-red-900 text-white font-semibold py-4 px-6 rounded-xl transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {submitting ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Enviando cadastro...
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" />
                    Enviar Cadastro
                  </>
                )}
              </button>
            </div>
          )}
          
          {step < 4 && (
            <div className="flex justify-between mt-8 pt-6 border-t">
              <button
                onClick={() => setStep(s => Math.max(1, s - 1))}
                disabled={step === 1}
                className="flex items-center gap-2 px-4 sm:px-6 py-3 text-gray-600 hover:text-gray-800 disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-5 h-5" />
                <span className="hidden sm:inline">Voltar</span>
              </button>
              <button
                onClick={() => setStep(s => Math.min(4, s + 1))}
                disabled={!canProceed()}
                className="flex items-center gap-2 bg-red-800 hover:bg-red-900 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-semibold px-6 py-3 rounded-xl transition-all duration-200"
              >
                Continuar
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          )}
          
          {step === 4 && (
            <div className="flex justify-start mt-8 pt-6 border-t">
              <button
                onClick={() => setStep(3)}
                className="flex items-center gap-2 px-6 py-3 text-gray-600 hover:text-gray-800"
              >
                <ChevronLeft className="w-5 h-5" />
                Voltar
              </button>
            </div>
          )}
        </div>
        
        <p className="text-center text-gray-400 text-xs mt-6">
          🔒 Seus dados estão protegidos conforme a LGPD
        </p>
      </div>
    </div>
  )
}
