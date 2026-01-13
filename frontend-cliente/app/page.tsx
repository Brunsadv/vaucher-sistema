'use client'

import { useState, useRef } from 'react'
import { User, FileText, CheckCircle, Upload, ChevronRight, ChevronLeft, Briefcase, Phone, Mail, MapPin, Calendar, CreditCard, Users, FileCheck, AlertCircle, X, Check } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const LOGO_URL = "https://raw.githubusercontent.com/Brunsadv/vaucher-sistema/main/backend/static/Vaucher%20e%20Alvares-06.jpg"

const Logo = ({ size = 'normal' }: { size?: 'small' | 'normal' | 'large' }) => {
  const sizes = {
    small: 'h-12',
    normal: 'h-20',
    large: 'h-28'
  }
  return (
    <img 
      src={LOGO_URL} 
      alt="Vaucher & Álvares Advogados" 
      className={`${sizes[size]} w-auto`}
    />
  )
}

// Máscaras de input
const maskCPF = (value: string) => {
  return value
    .replace(/\D/g, '')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d{1,2})/, '$1-$2')
    .replace(/(-\d{2})\d+?$/, '$1')
}

const maskPhone = (value: string) => {
  return value
    .replace(/\D/g, '')
    .replace(/(\d{2})(\d)/, '($1) $2')
    .replace(/(\d{5})(\d)/, '$1-$2')
    .replace(/(-\d{4})\d+?$/, '$1')
}

// Tipos de demanda com textos pré-definidos
const tiposDemanda = [
  { value: 'adicional_insalubridade', label: 'Adicional de Insalubridade', texto: 'propor ação judicial visando o reconhecimento do direito ao adicional de insalubridade, bem como as diferenças remuneratórias decorrentes' },
  { value: 'adicional_periculosidade', label: 'Adicional de Periculosidade', texto: 'propor ação judicial visando o reconhecimento do direito ao adicional de periculosidade, bem como as diferenças remuneratórias decorrentes' },
  { value: 'desvio_funcao', label: 'Desvio de Função', texto: 'propor ação judicial visando o reconhecimento do desvio de função e pagamento das diferenças salariais correspondentes' },
  { value: 'progressao_funcional', label: 'Progressão Funcional', texto: 'propor ação judicial visando o reconhecimento do direito à progressão funcional e seus efeitos financeiros' },
  { value: 'revisao_aposentadoria', label: 'Revisão de Aposentadoria', texto: 'propor ação judicial visando a revisão dos proventos de aposentadoria e pagamento das diferenças devidas' },
  { value: 'licenca_premio', label: 'Licença Prêmio', texto: 'propor ação judicial visando o reconhecimento do direito à licença prêmio ou sua conversão em pecúnia' },
  { value: 'ferias_nao_gozadas', label: 'Férias Não Gozadas', texto: 'propor ação judicial visando a indenização por férias não gozadas e seus reflexos' },
  { value: 'horas_extras', label: 'Horas Extras', texto: 'propor ação judicial visando o pagamento de horas extras laboradas e seus reflexos legais' },
  { value: 'reintegracao', label: 'Reintegração', texto: 'propor ação judicial visando a reintegração ao cargo público e pagamento dos vencimentos do período de afastamento' },
  { value: 'outro', label: 'Outro (especificar)', texto: '' },
]

interface FormData {
  nome: string
  cpf: string
  rg: string
  data_nascimento: string
  estado_civil: string
  nacionalidade: string
  profissao: string
  endereco_completo: string
  email: string
  telefone: string
  tipo_demanda: string
  objeto_contrato: string
  poderes_especificos: string
  observacoes: string
}

const initialFormData: FormData = {
  nome: '',
  cpf: '',
  rg: '',
  data_nascimento: '',
  estado_civil: '',
  nacionalidade: 'brasileiro(a)',
  profissao: '',
  endereco_completo: '',
  email: '',
  telefone: '',
  tipo_demanda: '',
  objeto_contrato: '',
  poderes_especificos: '',
  observacoes: '',
}

export default function CadastroCliente() {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState<FormData>(initialFormData)
  const [arquivos, setArquivos] = useState<File[]>([])
  const [enviando, setEnviando] = useState(false)
  const [cadastroId, setCadastroId] = useState<string | null>(null)
  const [sucesso, setSucesso] = useState(false)
  const [erro, setErro] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  const updateField = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleTipoDemandaChange = (tipo: string) => {
    const demanda = tiposDemanda.find(t => t.value === tipo)
    setFormData(prev => ({
      ...prev,
      tipo_demanda: tipo,
      objeto_contrato: demanda?.texto || '',
      poderes_especificos: demanda?.texto || ''
    }))
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setArquivos(prev => [...prev, ...Array.from(e.target.files!)])
    }
  }

  const removeFile = (index: number) => {
    setArquivos(prev => prev.filter((_, i) => i !== index))
  }

  const validateStep = (currentStep: number): boolean => {
    switch (currentStep) {
      case 1:
        return !!(formData.nome && formData.cpf && formData.rg && formData.data_nascimento && 
                  formData.estado_civil && formData.profissao && formData.endereco_completo && 
                  formData.email && formData.telefone)
      case 2:
        return !!(formData.tipo_demanda && formData.objeto_contrato)
      case 3:
        return true // Documentos são opcionais
      default:
        return true
    }
  }

  const nextStep = () => {
    if (validateStep(step)) {
      setStep(prev => Math.min(prev + 1, 4))
      setErro('')
    } else {
      setErro('Por favor, preencha todos os campos obrigatórios.')
    }
  }

  const prevStep = () => {
    setStep(prev => Math.max(prev - 1, 1))
    setErro('')
  }

  const handleSubmit = async () => {
    setEnviando(true)
    setErro('')

    try {
      // 1. Criar cadastro
      const response = await fetch(`${API_URL}/api/cadastros`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })

      const data = await response.json()

      if (!response.ok || !data.success) {
        throw new Error(data.detail || 'Erro ao enviar cadastro')
      }

      const novoId = data.id
      setCadastroId(novoId)

      // 2. Upload de arquivos (se houver)
      for (const arquivo of arquivos) {
        const formDataUpload = new FormData()
        formDataUpload.append('arquivo', arquivo)

        await fetch(`${API_URL}/api/cadastros/${novoId}/upload`, {
          method: 'POST',
          body: formDataUpload
        })
      }

      setSucesso(true)
    } catch (err: any) {
      setErro(err.message || 'Erro ao enviar cadastro. Tente novamente.')
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
          <h1 className="text-2xl font-bold text-gray-800 mb-2">Cadastro Enviado com Sucesso!</h1>
          <p className="text-gray-600 mb-6">
            Recebemos suas informações. Em breve você receberá um e-mail com os documentos para assinatura.
          </p>
          <div className="bg-gray-50 rounded-xl p-4 mb-6">
            <p className="text-sm text-gray-500">Protocolo de cadastro:</p>
            <p className="text-lg font-mono font-bold text-red-800">{cadastroId}</p>
          </div>
          <p className="text-sm text-gray-500">
            Prazo estimado de retorno: <strong>até 2 dias úteis</strong>
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
            <Logo size="normal" />
          </div>
        </div>
      </header>

      {/* Progress Bar */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-2">
            {[1, 2, 3, 4].map((s) => (
              <div key={s} className="flex items-center">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${
                  s < step ? 'bg-green-500 text-white' :
                  s === step ? 'bg-red-800 text-white' :
                  'bg-gray-200 text-gray-500'
                }`}>
                  {s < step ? <Check className="w-5 h-5" /> : s}
                </div>
                {s < 4 && (
                  <div className={`w-16 sm:w-24 h-1 mx-2 rounded ${
                    s < step ? 'bg-green-500' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between text-xs sm:text-sm text-gray-500">
            <span className={step === 1 ? 'text-red-800 font-medium' : ''}>Dados Pessoais</span>
            <span className={step === 2 ? 'text-red-800 font-medium' : ''}>Demanda</span>
            <span className={step === 3 ? 'text-red-800 font-medium' : ''}>Documentos</span>
            <span className={step === 4 ? 'text-red-800 font-medium' : ''}>Confirmação</span>
          </div>
        </div>
      </div>

      {/* Form Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl shadow-lg p-6 sm:p-8">
          
          {/* Erro */}
          {erro && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              {erro}
            </div>
          )}

          {/* Step 1: Dados Pessoais */}
          {step === 1 && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
                  <User className="w-6 h-6 text-red-700" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-800">Dados Pessoais</h2>
                  <p className="text-gray-500 text-sm">Preencha suas informações básicas</p>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nome Completo <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.nome}
                    onChange={(e) => updateField('nome', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    placeholder="Digite seu nome completo"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    CPF <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.cpf}
                    onChange={(e) => updateField('cpf', maskCPF(e.target.value))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    placeholder="000.000.000-00"
                    maxLength={14}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    RG <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.rg}
                    onChange={(e) => updateField('rg', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    placeholder="Digite seu RG"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Data de Nascimento <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="date"
                    value={formData.data_nascimento}
                    onChange={(e) => updateField('data_nascimento', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Estado Civil <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.estado_civil}
                    onChange={(e) => updateField('estado_civil', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                  >
                    <option value="">Selecione...</option>
                    <option value="solteiro(a)">Solteiro(a)</option>
                    <option value="casado(a)">Casado(a)</option>
                    <option value="divorciado(a)">Divorciado(a)</option>
                    <option value="viúvo(a)">Viúvo(a)</option>
                    <option value="união estável">União Estável</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nacionalidade <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={formData.nacionalidade}
                    onChange={(e) => updateField('nacionalidade', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                  >
                    <option value="brasileiro(a)">Brasileiro(a)</option>
                    <option value="estrangeiro(a)">Estrangeiro(a)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Profissão/Cargo <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.profissao}
                    onChange={(e) => updateField('profissao', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    placeholder="Ex: Enfermeiro(a), Técnico(a) de Enfermagem"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Endereço Completo <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.endereco_completo}
                    onChange={(e) => updateField('endereco_completo', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    placeholder="Rua, número, bairro, cidade - UF, CEP"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    E-mail <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => updateField('email', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    placeholder="seu@email.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Telefone/WhatsApp <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.telefone}
                    onChange={(e) => updateField('telefone', maskPhone(e.target.value))}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    placeholder="(00) 00000-0000"
                    maxLength={15}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Demanda */}
          {step === 2 && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
                  <Briefcase className="w-6 h-6 text-red-700" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-800">Informações da Demanda</h2>
                  <p className="text-gray-500 text-sm">Selecione o tipo de ação desejada</p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tipo de Demanda <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.tipo_demanda}
                  onChange={(e) => handleTipoDemandaChange(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                >
                  <option value="">Selecione o tipo de demanda...</option>
                  {tiposDemanda.map(tipo => (
                    <option key={tipo.value} value={tipo.value}>{tipo.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Objeto do Contrato / Poderes da Procuração <span className="text-red-500">*</span>
                </label>
                <p className="text-xs text-gray-500 mb-2">
                  Este texto será usado no Contrato de Honorários e na Procuração. Você pode editar se necessário.
                </p>
                <textarea
                  value={formData.objeto_contrato}
                  onChange={(e) => {
                    updateField('objeto_contrato', e.target.value)
                    updateField('poderes_especificos', e.target.value)
                  }}
                  rows={4}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent resize-none"
                  placeholder="Descreva o objeto do contrato e os poderes a serem concedidos..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Observações Adicionais
                </label>
                <textarea
                  value={formData.observacoes}
                  onChange={(e) => updateField('observacoes', e.target.value)}
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent resize-none"
                  placeholder="Informações adicionais que julgar relevantes (opcional)"
                />
              </div>
            </div>
          )}

          {/* Step 3: Documentos */}
          {step === 3 && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
                  <FileText className="w-6 h-6 text-red-700" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-800">Documentos</h2>
                  <p className="text-gray-500 text-sm">Anexe os documentos necessários</p>
                </div>
              </div>

              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <h3 className="font-medium text-amber-800 mb-2">Documentos recomendados:</h3>
                <ul className="text-sm text-amber-700 space-y-1">
                  <li>• Documento de identidade (RG ou CNH)</li>
                  <li>• Comprovante de residência atualizado</li>
                  <li>• Últimos 3 contracheques</li>
                  <li>• Documentos relacionados à demanda</li>
                </ul>
              </div>

              <div>
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

              {arquivos.length > 0 && (
                <div className="space-y-2">
                  <p className="font-medium text-gray-700">Arquivos selecionados ({arquivos.length}):</p>
                  {arquivos.map((file, index) => (
                    <div key={index} className="flex items-center justify-between bg-gray-50 border rounded-lg px-4 py-3">
                      <div className="flex items-center gap-3">
                        <FileCheck className="w-5 h-5 text-green-600" />
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
            </div>
          )}

          {/* Step 4: Confirmação */}
          {step === 4 && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
                  <CheckCircle className="w-6 h-6 text-red-700" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-800">Confirmação</h2>
                  <p className="text-gray-500 text-sm">Revise suas informações antes de enviar</p>
                </div>
              </div>

              {/* Resumo dos dados */}
              <div className="space-y-4">
                <div className="bg-gray-50 rounded-xl p-4">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <User className="w-4 h-4" /> Dados Pessoais
                  </h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div><span className="text-gray-500">Nome:</span> <strong>{formData.nome}</strong></div>
                    <div><span className="text-gray-500">CPF:</span> <strong>{formData.cpf}</strong></div>
                    <div><span className="text-gray-500">RG:</span> <strong>{formData.rg}</strong></div>
                    <div><span className="text-gray-500">Nascimento:</span> <strong>{formData.data_nascimento}</strong></div>
                    <div><span className="text-gray-500">Estado Civil:</span> <strong className="capitalize">{formData.estado_civil}</strong></div>
                    <div><span className="text-gray-500">Profissão:</span> <strong>{formData.profissao}</strong></div>
                    <div className="col-span-2"><span className="text-gray-500">Endereço:</span> <strong>{formData.endereco_completo}</strong></div>
                    <div><span className="text-gray-500">E-mail:</span> <strong>{formData.email}</strong></div>
                    <div><span className="text-gray-500">Telefone:</span> <strong>{formData.telefone}</strong></div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-xl p-4">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <Briefcase className="w-4 h-4" /> Demanda
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div><span className="text-gray-500">Tipo:</span> <strong>{tiposDemanda.find(t => t.value === formData.tipo_demanda)?.label}</strong></div>
                    <div><span className="text-gray-500">Objeto:</span> <strong>{formData.objeto_contrato}</strong></div>
                    {formData.observacoes && <div><span className="text-gray-500">Observações:</span> <strong>{formData.observacoes}</strong></div>}
                  </div>
                </div>

                <div className="bg-gray-50 rounded-xl p-4">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <FileText className="w-4 h-4" /> Documentos
                  </h3>
                  {arquivos.length > 0 ? (
                    <ul className="text-sm space-y-1">
                      {arquivos.map((file, i) => (
                        <li key={i} className="flex items-center gap-2">
                          <FileCheck className="w-4 h-4 text-green-600" />
                          {file.name}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500">Nenhum documento anexado</p>
                  )}
                </div>
              </div>

              <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                <p className="text-sm text-red-800">
                  <strong>Importante:</strong> Ao enviar este cadastro, você declara que todas as informações fornecidas são verdadeiras e autoriza o escritório Vaucher & Álvares a representá-lo na demanda especificada.
                </p>
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between mt-8 pt-6 border-t">
            {step > 1 ? (
              <button
                onClick={prevStep}
                className="flex items-center gap-2 px-6 py-3 border border-gray-300 rounded-xl text-gray-700 hover:bg-gray-50 transition-all"
              >
                <ChevronLeft className="w-5 h-5" />
                Voltar
              </button>
            ) : (
              <div />
            )}

            {step < 4 ? (
              <button
                onClick={nextStep}
                className="flex items-center gap-2 px-6 py-3 bg-red-800 hover:bg-red-900 text-white font-semibold rounded-xl transition-all"
              >
                Próximo
                <ChevronRight className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={enviando}
                className="flex items-center gap-2 px-8 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl transition-all disabled:opacity-50"
              >
                {enviando ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Enviando...
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-5 h-5" />
                    Enviar Cadastro
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-gray-400 text-xs mt-8">
          © {new Date().getFullYear()} Vaucher & Álvares Sociedade de Advogados — Todos os direitos reservados
        </p>
      </main>
    </div>
  )
}
