'use client'

import { useState, useRef, useEffect } from 'react'
import { User, FileText, CheckCircle, Upload, ChevronRight, ChevronLeft, Briefcase, Phone, Mail, MapPin, Calendar, CreditCard, Users, FileCheck, AlertCircle, X, Check, Save, Building, GraduationCap, Stethoscope, Clock, FileQuestion, BadgeDollarSign, Landmark } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const LOGO_URL = "/logo.jpg"

const Logo = ({ size = 'normal' }: { size?: 'small' | 'normal' | 'large' }) => {
  const sizes = {
    small: 'h-24',
    normal: 'h-48',
    large: 'h-64'
  }
  return (
    <img 
      src={LOGO_URL} 
      alt="Vaucher e Álvares Advogados" 
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

const maskCurrency = (value: string) => {
  const numericValue = value.replace(/\D/g, '')
  const numberValue = parseInt(numericValue || '0', 10) / 100
  return numberValue.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

// Validação matemática de CPF (algoritmo oficial)
const validarCPF = (cpf: string): boolean => {
  const cpfLimpo = cpf.replace(/\D/g, '')
  if (cpfLimpo.length !== 11) return false
  if (/^(\d)\1+$/.test(cpfLimpo)) return false
  
  let soma = 0
  for (let i = 0; i < 9; i++) {
    soma += parseInt(cpfLimpo[i]) * (10 - i)
  }
  let resto = (soma * 10) % 11
  if (resto === 10 || resto === 11) resto = 0
  if (resto !== parseInt(cpfLimpo[9])) return false
  
  soma = 0
  for (let i = 0; i < 10; i++) {
    soma += parseInt(cpfLimpo[i]) * (11 - i)
  }
  resto = (soma * 10) % 11
  if (resto === 10 || resto === 11) resto = 0
  if (resto !== parseInt(cpfLimpo[10])) return false
  
  return true
}

// Tipos de demanda com textos pré-definidos
const tiposDemanda = [
  { value: 'adicional_insalubridade', label: 'Adicional de Insalubridade', texto: 'propor ação judicial visando o reconhecimento do direito ao adicional de insalubridade, bem como as diferenças remuneratórias decorrentes', temFormulario: false },
  { value: 'adicional_periculosidade', label: 'Adicional de Periculosidade', texto: 'propor ação judicial visando o reconhecimento do direito ao adicional de periculosidade, bem como as diferenças remuneratórias decorrentes', temFormulario: false },
  { value: 'desvio_funcao', label: 'Desvio de Função', texto: 'propor ação judicial visando o reconhecimento do desvio de função e pagamento das diferenças salariais correspondentes', temFormulario: false },
  { value: 'progressao_funcional', label: 'Progressão Funcional', texto: 'propor ação judicial visando o reconhecimento do direito à progressão funcional e seus efeitos financeiros', temFormulario: false },
  { value: 'revisao_aposentadoria', label: 'Revisão de Aposentadoria', texto: 'propor ação judicial visando a revisão dos proventos de aposentadoria e pagamento das diferenças devidas', temFormulario: false },
  { value: 'licenca_premio', label: 'Licença Prêmio', texto: 'propor ação judicial visando o reconhecimento do direito à licença prêmio ou sua conversão em pecúnia', temFormulario: false },
  { value: 'ferias_nao_gozadas', label: 'Férias Não Gozadas', texto: 'propor ação judicial visando a indenização por férias não gozadas e seus reflexos', temFormulario: false },
  { value: 'horas_extras', label: 'Horas Extras', texto: 'propor ação judicial visando o pagamento de horas extras laboradas e seus reflexos legais', temFormulario: false },
  { value: 'reintegracao', label: 'Reintegração', texto: 'propor ação judicial visando a reintegração ao cargo público e pagamento dos vencimentos do período de afastamento', temFormulario: false },
  { value: 'auxilio_moradia_residencia', label: 'Auxílio-moradia Residência Médica', texto: 'propor ação judicial visando o reconhecimento do direito ao auxílio-moradia durante o período de residência médica e pagamento dos valores devidos', temFormulario: true },
  { value: 'isencao_imposto_renda', label: 'Isenção de Imposto de Renda', texto: 'propor ação judicial visando o reconhecimento do direito à isenção de imposto de renda sobre proventos de aposentadoria ou pensão em razão de moléstia grave, bem como a restituição dos valores indevidamente recolhidos', temFormulario: false },
  { value: 'outro', label: 'Outro (especificar)', texto: '', temFormulario: false },
]

// Documentos específicos para Auxílio Moradia Residência Médica
const documentosAuxilioMoradia = [
  { id: 'doc_pessoais', nome: 'Documentos Pessoais', descricao: 'RG e CPF (ou CNH) e Comprovante de Residência atualizado', obrigatorio: false },
  { id: 'certificado_residencia', nome: 'Certificado/Declaração de Conclusão da Residência', descricao: 'Documento emitido pela COREME ou retirado do SISCNRM com data de início, fim e especialidade', obrigatorio: false },
  { id: 'historico_financeiro', nome: 'Histórico Financeiro / Contracheques', descricao: 'Fichas financeiras ou extratos bancários de todo o período da residência', obrigatorio: false },
  { id: 'processo_anterior', nome: 'Cópia do Processo Anterior', descricao: 'Se houver processo anterior, anexar petição inicial e decisão de extinção', obrigatorio: false },
]

// Interface para dados específicos do Auxílio Moradia
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

interface FormData {
  nome: string
  cpf: string
  documento_identificacao: string
  data_nascimento: string
  estado_civil: string
  nacionalidade: string
  profissao: string
  matricula_funcional: string
  orgao_vinculacao: string
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
  documento_identificacao: '',
  data_nascimento: '',
  estado_civil: '',
  nacionalidade: 'brasileiro(a)',
  profissao: '',
  matricula_funcional: '',
  orgao_vinculacao: '',
  endereco_completo: '',
  email: '',
  telefone: '',
  tipo_demanda: '',
  objeto_contrato: '',
  poderes_especificos: '',
  observacoes: '',
}

const initialDadosAuxilioMoradia: DadosAuxilioMoradia = {
  instituicao_ensino: '',
  unidade_hospitalar: '',
  especialidade_medica: '',
  data_inicio_residencia: '',
  data_termino_residencia: '',
  valor_bolsa_mensal: '',
  recebeu_moradia: false,
  processo_anterior: false,
  numero_processo_anterior: '',
  vara_juizado_anterior: '',
  data_protocolo_anterior: '',
  data_citacao_anterior: '',
  dados_bancarios: '',
}

export default function CadastroCliente() {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState<FormData>(initialFormData)
  const [dadosAuxilioMoradia, setDadosAuxilioMoradia] = useState<DadosAuxilioMoradia>(initialDadosAuxilioMoradia)
  const [arquivos, setArquivos] = useState<File[]>([])
  const [arquivosDemanda, setArquivosDemanda] = useState<{[key: string]: File[]}>({})
  const [enviando, setEnviando] = useState(false)
  const [salvandoRascunho, setSalvandoRascunho] = useState(false)
  const [cadastroId, setCadastroId] = useState<string | null>(null)
  const [sucesso, setSucesso] = useState(false)
  const [erro, setErro] = useState('')
  const [rascunhoSalvo, setRascunhoSalvo] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // Estados para Termos de Uso e Privacidade
  const [termosAceitos, setTermosAceitos] = useState(false)
  const [termosUso, setTermosUso] = useState<any>(null)
  const [politicaPrivacidade, setPoliticaPrivacidade] = useState<any>(null)
  const [modalTermos, setModalTermos] = useState<'termos' | 'privacidade' | null>(null)
  const [carregandoTermos, setCarregandoTermos] = useState(true)

  // Verificar se o tipo de demanda atual tem formulário específico
  const demandaAtual = tiposDemanda.find(t => t.value === formData.tipo_demanda)
  const temFormularioEspecifico = demandaAtual?.temFormulario || false
  
  // Calcular número total de steps
  const totalSteps = temFormularioEspecifico ? 5 : 4

  // Carregar termos ao montar o componente
  useEffect(() => {
    const carregarTermos = async () => {
      try {
        const [termosRes, privacidadeRes] = await Promise.all([
          fetch(`${API_URL}/api/termos/termos_uso`),
          fetch(`${API_URL}/api/termos/politica_privacidade`)
        ])
        
        if (termosRes.ok) {
          const termosData = await termosRes.json()
          setTermosUso(termosData)
        }
        if (privacidadeRes.ok) {
          const privacidadeData = await privacidadeRes.json()
          setPoliticaPrivacidade(privacidadeData)
        }
      } catch (error) {
        console.error('Erro ao carregar termos:', error)
      } finally {
        setCarregandoTermos(false)
      }
    }
    
    carregarTermos()
  }, [])

  // Tentar recuperar rascunho do localStorage
  useEffect(() => {
    const rascunho = localStorage.getItem('cadastro_rascunho')
    if (rascunho) {
      try {
        const dados = JSON.parse(rascunho)
        if (dados.formData) setFormData(dados.formData)
        if (dados.dadosAuxilioMoradia) setDadosAuxilioMoradia(dados.dadosAuxilioMoradia)
        if (dados.step) setStep(dados.step)
        setRascunhoSalvo(true)
      } catch (e) {
        console.error('Erro ao recuperar rascunho:', e)
      }
    }
  }, [])

  const updateField = (field: keyof FormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    setRascunhoSalvo(false)
  }

  const updateAuxilioMoradiaField = (field: keyof DadosAuxilioMoradia, value: any) => {
    setDadosAuxilioMoradia(prev => ({ ...prev, [field]: value }))
    setRascunhoSalvo(false)
  }

  const handleTipoDemandaChange = (tipo: string) => {
    const demanda = tiposDemanda.find(t => t.value === tipo)
    setFormData(prev => ({
      ...prev,
      tipo_demanda: tipo,
      objeto_contrato: demanda?.texto || '',
      poderes_especificos: demanda?.texto || ''
    }))
    setRascunhoSalvo(false)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setArquivos(prev => [...prev, ...Array.from(e.target.files!)])
    }
  }

  const handleDocumentoDemandaSelect = (docId: string, files: FileList | null) => {
  if (files && files.length > 0) {
    setArquivosDemanda(prev => ({
      ...prev,
      [docId]: [...(prev[docId] || []), ...Array.from(files)]
    }))
  }
}

const removeDocumentoDemanda = (docId: string, index: number) => {
  setArquivosDemanda(prev => ({
    ...prev,
    [docId]: (prev[docId] || []).filter((_, i) => i !== index)
  }))
}

  const removeFile = (index: number) => {
    setArquivos(prev => prev.filter((_, i) => i !== index))
  }

  // Salvar rascunho localmente
  const salvarRascunhoLocal = () => {
    setSalvandoRascunho(true)
    try {
      const rascunho = {
        formData,
        dadosAuxilioMoradia,
        step,
        timestamp: new Date().toISOString()
      }
      localStorage.setItem('cadastro_rascunho', JSON.stringify(rascunho))
      setRascunhoSalvo(true)
      setTimeout(() => setSalvandoRascunho(false), 1000)
    } catch (e) {
      console.error('Erro ao salvar rascunho:', e)
      setSalvandoRascunho(false)
    }
  }

  const limparRascunho = () => {
    localStorage.removeItem('cadastro_rascunho')
    setRascunhoSalvo(false)
  }

  const validateStep = (currentStep: number): boolean => {
    switch (currentStep) {
      case 1:
        if (!formData.nome || !formData.cpf || !formData.data_nascimento || 
            !formData.estado_civil || !formData.profissao || !formData.endereco_completo || 
            !formData.email || !formData.telefone) {
          return false
        }
        if (!validarCPF(formData.cpf)) {
          return false
        }
        return true
      case 2:
        return !!(formData.tipo_demanda && formData.objeto_contrato)
      case 3:
        // Se tem formulário específico, validar campos obrigatórios
        if (temFormularioEspecifico && formData.tipo_demanda === 'auxilio_moradia_residencia') {
          if (!dadosAuxilioMoradia.instituicao_ensino || 
              !dadosAuxilioMoradia.especialidade_medica ||
              !dadosAuxilioMoradia.data_inicio_residencia ||
              !dadosAuxilioMoradia.data_termino_residencia) {
            return false
          }
        }
        return true
      case 4:
        return true // Documentos são opcionais
      case 5:
        return termosAceitos
      default:
        return true
    }
  }

  const nextStep = () => {
    if (step === 1) {
      if (!formData.nome || !formData.cpf || !formData.data_nascimento || 
          !formData.estado_civil || !formData.profissao || !formData.endereco_completo || 
          !formData.email || !formData.telefone) {
        setErro('Por favor, preencha todos os campos obrigatórios.')
        return
      }
      if (!validarCPF(formData.cpf)) {
        setErro('CPF inválido. Por favor, verifique o número digitado.')
        return
      }
    }
    
    if (step === 3 && temFormularioEspecifico && formData.tipo_demanda === 'auxilio_moradia_residencia') {
      if (!dadosAuxilioMoradia.instituicao_ensino || 
          !dadosAuxilioMoradia.especialidade_medica ||
          !dadosAuxilioMoradia.data_inicio_residencia ||
          !dadosAuxilioMoradia.data_termino_residencia) {
        setErro('Por favor, preencha os campos obrigatórios da residência médica.')
        return
      }
    }
    
    if (validateStep(step)) {
      setStep(prev => Math.min(prev + 1, totalSteps))
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
    if (!termosAceitos) {
      setErro('É necessário aceitar os Termos de Uso e a Política de Privacidade para continuar.')
      return
    }
    
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

      // 2. Registrar aceite dos termos
      if (termosUso?.id || politicaPrivacidade?.id) {
        try {
          await fetch(`${API_URL}/api/aceitar-termos`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              cadastro_id: novoId,
              termos_uso_versao_id: termosUso?.id,
              privacidade_versao_id: politicaPrivacidade?.id
            })
          })
        } catch (errTermos) {
          console.error('Erro ao registrar aceite dos termos:', errTermos)
        }
      }

      // 3. Salvar dados específicos da demanda (se aplicável)
      if (temFormularioEspecifico && formData.tipo_demanda === 'auxilio_moradia_residencia') {
        try {
          // Converter valor da bolsa para número
          const valorBolsa = dadosAuxilioMoradia.valor_bolsa_mensal
            ? parseFloat(dadosAuxilioMoradia.valor_bolsa_mensal.replace(/[^\d,]/g, '').replace(',', '.'))
            : 0

          await fetch(`${API_URL}/api/cadastros/${novoId}/demanda-especifica`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              tipo_demanda: formData.tipo_demanda,
              dados: {
                ...dadosAuxilioMoradia,
                valor_bolsa_mensal: valorBolsa
              }
            })
          })
        } catch (errDemanda) {
          console.error('Erro ao salvar dados da demanda:', errDemanda)
        }
      }

      // 4. Upload de arquivos gerais
      for (const arquivo of arquivos) {
        const formDataUpload = new FormData()
        formDataUpload.append('arquivo', arquivo)

        await fetch(`${API_URL}/api/cadastros/${novoId}/upload`, {
          method: 'POST',
          body: formDataUpload
        })
      }

      // 5. Upload de documentos específicos da demanda
      for (const [docId, arquivosDoc] of Object.entries(arquivosDemanda)) {
  if (arquivosDoc && arquivosDoc.length > 0) {
    for (const arquivo of arquivosDoc) {
      const formDataUpload = new FormData()
      formDataUpload.append('arquivo', arquivo)
      // ...
    }
  }
}

      // Limpar rascunho após envio bem-sucedido
      limparRascunho()
      setSucesso(true)
    } catch (err: any) {
      setErro(err.message || 'Erro ao enviar cadastro. Tente novamente.')
    } finally {
      setEnviando(false)
    }
  }

  // Calcular valor estimado da causa para auxílio moradia
  const calcularValorCausa = () => {
    if (!dadosAuxilioMoradia.data_inicio_residencia || !dadosAuxilioMoradia.data_termino_residencia) {
      return null
    }
    
    try {
      const inicio = new Date(dadosAuxilioMoradia.data_inicio_residencia)
      const termino = new Date(dadosAuxilioMoradia.data_termino_residencia)
      const meses = (termino.getFullYear() - inicio.getFullYear()) * 12 + (termino.getMonth() - inicio.getMonth())
      
      let valorBolsa = 3330.43 // Valor padrão
      if (dadosAuxilioMoradia.valor_bolsa_mensal) {
        const parsed = parseFloat(dadosAuxilioMoradia.valor_bolsa_mensal.replace(/[^\d,]/g, '').replace(',', '.'))
        if (!isNaN(parsed)) valorBolsa = parsed
      }
      
      const valorCausa = valorBolsa * 0.30 * meses
      return { meses, valorBolsa, valorCausa }
    } catch {
      return null
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

  // Determinar labels dos steps baseado no tipo de demanda
  const getStepLabels = () => {
    if (temFormularioEspecifico) {
      return ['Dados Pessoais', 'Demanda', 'Dados Específicos', 'Documentos', 'Confirmação']
    }
    return ['Dados Pessoais', 'Demanda', 'Documentos', 'Confirmação']
  }

  const stepLabels = getStepLabels()

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
            {Array.from({ length: totalSteps }, (_, i) => i + 1).map((s) => (
              <div key={s} className="flex items-center">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-all ${
                  s < step ? 'bg-green-500 text-white' :
                  s === step ? 'bg-red-800 text-white' :
                  'bg-gray-200 text-gray-500'
                }`}>
                  {s < step ? <Check className="w-5 h-5" /> : s}
                </div>
                {s < totalSteps && (
                  <div className={`w-12 sm:w-20 h-1 mx-2 rounded ${
                    s < step ? 'bg-green-500' : 'bg-gray-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between text-xs sm:text-sm text-gray-500">
            {stepLabels.map((label, i) => (
              <span key={i} className={step === i + 1 ? 'text-red-800 font-medium' : ''}>{label}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Form Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl shadow-lg p-6 sm:p-8">
          
          {/* Botão Salvar Rascunho */}
          {step < totalSteps && (
            <div className="flex justify-end mb-4">
              <button
                onClick={salvarRascunhoLocal}
                disabled={salvandoRascunho}
                className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-all ${
                  rascunhoSalvo 
                    ? 'bg-green-100 text-green-700' 
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <Save className="w-4 h-4" />
                {salvandoRascunho ? 'Salvando...' : rascunhoSalvo ? 'Rascunho salvo!' : 'Salvar rascunho'}
              </button>
            </div>
          )}
          
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
                    Documento de Identificação
                    <span className="text-gray-400 text-xs ml-1">(opcional)</span>
                  </label>
                  <input
                    type="text"
                    value={formData.documento_identificacao}
                    onChange={(e) => updateField('documento_identificacao', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    placeholder="RG, OAB, CRM, CRO, CREA, etc."
                  />
                  <p className="text-xs text-gray-500 mt-1">RG, registro profissional ou outro documento</p>
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
                    <option value="separado(a)">Separado(a)</option>
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
                    placeholder="Ex: Médico(a), Enfermeiro(a)"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Matrícula Funcional
                    <span className="text-gray-400 text-xs ml-1">(opcional)</span>
                  </label>
                  <input
                    type="text"
                    value={formData.matricula_funcional}
                    onChange={(e) => updateField('matricula_funcional', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    placeholder="Número da matrícula"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Órgão de Vinculação
                    <span className="text-gray-400 text-xs ml-1">(opcional)</span>
                  </label>
                  <input
                    type="text"
                    value={formData.orgao_vinculacao}
                    onChange={(e) => updateField('orgao_vinculacao', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    placeholder="Ex: Hospital Geral Universitário"
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

              {/* Aviso para demandas com formulário específico */}
              {temFormularioEspecifico && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <div className="flex items-start gap-3">
                    <FileQuestion className="w-5 h-5 text-blue-600 mt-0.5" />
                    <div>
                      <p className="text-sm text-blue-800 font-medium">
                        Formulário adicional necessário
                      </p>
                      <p className="text-sm text-blue-700 mt-1">
                        Este tipo de demanda requer informações específicas. Na próxima etapa, você preencherá dados adicionais sobre a residência médica.
                      </p>
                    </div>
                  </div>
                </div>
              )}

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

          {/* Step 3: Formulário Específico - Auxílio Moradia (apenas se tem formulário específico) */}
          {step === 3 && temFormularioEspecifico && formData.tipo_demanda === 'auxilio_moradia_residencia' && (
            <div className="space-y-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 bg-red-100 rounded-xl flex items-center justify-center">
                  <Stethoscope className="w-6 h-6 text-red-700" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-800">Dados da Residência Médica</h2>
                  <p className="text-gray-500 text-sm">Informações necessárias para fundamentar o direito</p>
                </div>
              </div>

              {/* Dados da Residência */}
              <div className="bg-gray-50 rounded-xl p-5 space-y-4">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                  <GraduationCap className="w-5 h-5" /> Dados da Residência
                </h3>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Instituição de Ensino (Universidade vinculada) <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={dadosAuxilioMoradia.instituicao_ensino}
                      onChange={(e) => updateAuxilioMoradiaField('instituicao_ensino', e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                      placeholder="Ex: Universidade Federal de São Paulo - UNIFESP"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Unidade Hospitalar (Local de atuação)
                    </label>
                    <input
                      type="text"
                      value={dadosAuxilioMoradia.unidade_hospitalar}
                      onChange={(e) => updateAuxilioMoradiaField('unidade_hospitalar', e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                      placeholder="Ex: Hospital Geral Universitário"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Especialidade Médica cursada <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={dadosAuxilioMoradia.especialidade_medica}
                      onChange={(e) => updateAuxilioMoradiaField('especialidade_medica', e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                      placeholder="Ex: Otorrinolaringologia, Medicina de Família e Comunidade"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Data de Início da Residência <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="date"
                      value={dadosAuxilioMoradia.data_inicio_residencia}
                      onChange={(e) => updateAuxilioMoradiaField('data_inicio_residencia', e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Data de Término da Residência <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="date"
                      value={dadosAuxilioMoradia.data_termino_residencia}
                      onChange={(e) => updateAuxilioMoradiaField('data_termino_residencia', e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Valor bruto da bolsa recebida mensalmente
                    </label>
                    <input
                      type="text"
                      value={dadosAuxilioMoradia.valor_bolsa_mensal}
                      onChange={(e) => updateAuxilioMoradiaField('valor_bolsa_mensal', maskCurrency(e.target.value))}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                      placeholder="R$ 3.330,43"
                    />
                    <p className="text-xs text-gray-500 mt-1">Geralmente R$ 3.330,43 ou R$ 4.106,09</p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Recebeu moradia in natura ou auxílio?
                    </label>
                    <select
                      value={dadosAuxilioMoradia.recebeu_moradia ? 'sim' : 'nao'}
                      onChange={(e) => updateAuxilioMoradiaField('recebeu_moradia', e.target.value === 'sim')}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    >
                      <option value="nao">Não</option>
                      <option value="sim">Sim</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Cálculo estimado do valor da causa */}
              {calcularValorCausa() && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4">
                  <div className="flex items-start gap-3">
                    <BadgeDollarSign className="w-5 h-5 text-green-600 mt-0.5" />
                    <div>
                      <p className="text-sm text-green-800 font-medium">Estimativa do Valor da Causa</p>
                      <p className="text-lg font-bold text-green-700 mt-1">
                        {calcularValorCausa()?.valorCausa.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                      </p>
                      <p className="text-xs text-green-600 mt-1">
                        ({calcularValorCausa()?.meses} meses × 30% de {calcularValorCausa()?.valorBolsa.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })})
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Histórico Processual */}
              <div className="bg-gray-50 rounded-xl p-5 space-y-4">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                  <Clock className="w-5 h-5" /> Histórico Processual
                </h3>
                
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                  <p className="text-xs text-amber-800">
                    <strong>Atenção:</strong> Preencha esta seção apenas se você já ingressou com esta ação anteriormente e ela foi extinta/arquivada.
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Já ingressou com esta ação anteriormente?
                  </label>
                  <select
                    value={dadosAuxilioMoradia.processo_anterior ? 'sim' : 'nao'}
                    onChange={(e) => updateAuxilioMoradiaField('processo_anterior', e.target.value === 'sim')}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                  >
                    <option value="nao">Não</option>
                    <option value="sim">Sim</option>
                  </select>
                </div>

                {dadosAuxilioMoradia.processo_anterior && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
                    <div className="sm:col-span-2">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Número do Processo Anterior
                      </label>
                      <input
                        type="text"
                        value={dadosAuxilioMoradia.numero_processo_anterior}
                        onChange={(e) => updateAuxilioMoradiaField('numero_processo_anterior', e.target.value)}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                        placeholder="Ex: 0000000-00.0000.0.00.0000"
                      />
                    </div>

                    <div className="sm:col-span-2">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Vara/Juizado Anterior
                      </label>
                      <input
                        type="text"
                        value={dadosAuxilioMoradia.vara_juizado_anterior}
                        onChange={(e) => updateAuxilioMoradiaField('vara_juizado_anterior', e.target.value)}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                        placeholder="Ex: 1ª Vara Federal de Cuiabá"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Data de Protocolo da ação anterior
                      </label>
                      <input
                        type="date"
                        value={dadosAuxilioMoradia.data_protocolo_anterior}
                        onChange={(e) => updateAuxilioMoradiaField('data_protocolo_anterior', e.target.value)}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Data da Citação/Despacho inicial
                      </label>
                      <input
                        type="date"
                        value={dadosAuxilioMoradia.data_citacao_anterior}
                        onChange={(e) => updateAuxilioMoradiaField('data_citacao_anterior', e.target.value)}
                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Dados Bancários */}
              <div className="bg-gray-50 rounded-xl p-5 space-y-4">
                <h3 className="font-semibold text-gray-800 flex items-center gap-2">
                  <Landmark className="w-5 h-5" /> Dados Bancários
                </h3>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Banco, Agência e Conta
                  </label>
                  <input
                    type="text"
                    value={dadosAuxilioMoradia.dados_bancarios}
                    onChange={(e) => updateAuxilioMoradiaField('dados_bancarios', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-800 focus:border-transparent"
                    placeholder="Ex: Banco do Brasil, Ag. 1234-5, CC 12345-6"
                  />
                  <p className="text-xs text-gray-500 mt-1">Para fins de recebimento futuro</p>
                </div>
              </div>
            </div>
          )}

          {/* Step 4 (ou 3 se não tem formulário específico): Documentos */}
          {((step === 3 && !temFormularioEspecifico) || (step === 4 && temFormularioEspecifico)) && (
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

              {/* Documentos específicos para Auxílio Moradia */}
              {formData.tipo_demanda === 'auxilio_moradia_residencia' && (
                <div className="space-y-4">
                  <h3 className="font-semibold text-gray-800">Documentos específicos para Auxílio Moradia</h3>
                  <p className="text-sm text-gray-600">
                    Todos os documentos são opcionais neste momento. Você pode enviá-los posteriormente.
                  </p>
                  
                  <div className="space-y-3">
                    {documentosAuxilioMoradia.map((doc) => (
                      <div key={doc.id} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <label className="block text-sm font-medium text-gray-700">
                              {doc.nome}
                              {doc.obrigatorio && <span className="text-red-500 ml-1">*</span>}
                            </label>
                            <p className="text-xs text-gray-500 mt-1">{doc.descricao}</p>
                          </div>
                          <div className="ml-4">
                            <input
                              type="file"
                              id={`doc-${doc.id}`}
                              onChange={(e) => handleDocumentoDemandaSelect(doc.id, e.target.files)}
                              multiple
                              accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                              className="hidden"
                            />
                            <label
                              htmlFor={`doc-${doc.id}`}
                              className={`cursor-pointer inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                                arquivosDemanda[doc.id]
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                              }`}
                            >
                              {arquivosDemanda[doc.id] && arquivosDemanda[doc.id].length > 0 ? (
  <>
    <FileCheck className="w-4 h-4" />
    {arquivosDemanda[doc.id].length} arquivo(s)
  </>
) : (
  <>
    <Upload className="w-4 h-4" />
    Anexar
  </>
)}
                            </label>
                          </div>
                        </div>
                        {arquivosDemanda[doc.id] && arquivosDemanda[doc.id].length > 0 && (
  <div className="mt-2 space-y-1">
    {arquivosDemanda[doc.id].map((file, idx) => (
      <div key={idx} className="flex items-center justify-between bg-gray-50 rounded px-3 py-2">
        <span className="text-sm text-gray-600 truncate">
          {file.name}
        </span>
        <button
          onClick={() => removeDocumentoDemanda(doc.id, idx)}
          className="text-red-500 hover:text-red-700"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    ))}
  </div>
)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Documentos gerais */}
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <h3 className="font-medium text-amber-800 mb-2">Documentos adicionais (opcionais):</h3>
                <ul className="text-sm text-amber-700 space-y-1">
                  <li>• Documento de identidade (RG ou CNH)</li>
                  <li>• Comprovante de residência atualizado</li>
                  <li>• Outros documentos relevantes</li>
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
                    <p className="font-medium">Clique para selecionar arquivos adicionais</p>
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

          {/* Step Final: Confirmação */}
          {step === totalSteps && (
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
                    <div><span className="text-gray-500">Nascimento:</span> <strong>{formData.data_nascimento}</strong></div>
                    <div><span className="text-gray-500">Estado Civil:</span> <strong className="capitalize">{formData.estado_civil}</strong></div>
                    <div><span className="text-gray-500">Profissão:</span> <strong>{formData.profissao}</strong></div>
                    <div><span className="text-gray-500">E-mail:</span> <strong>{formData.email}</strong></div>
                    <div><span className="text-gray-500">Telefone:</span> <strong>{formData.telefone}</strong></div>
                    <div className="col-span-2"><span className="text-gray-500">Endereço:</span> <strong>{formData.endereco_completo}</strong></div>
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

                {/* Dados específicos do Auxílio Moradia */}
                {formData.tipo_demanda === 'auxilio_moradia_residencia' && (
                  <div className="bg-gray-50 rounded-xl p-4">
                    <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                      <Stethoscope className="w-4 h-4" /> Dados da Residência Médica
                    </h3>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="col-span-2"><span className="text-gray-500">Instituição:</span> <strong>{dadosAuxilioMoradia.instituicao_ensino}</strong></div>
                      {dadosAuxilioMoradia.unidade_hospitalar && (
                        <div className="col-span-2"><span className="text-gray-500">Hospital:</span> <strong>{dadosAuxilioMoradia.unidade_hospitalar}</strong></div>
                      )}
                      <div><span className="text-gray-500">Especialidade:</span> <strong>{dadosAuxilioMoradia.especialidade_medica}</strong></div>
                      <div><span className="text-gray-500">Período:</span> <strong>{dadosAuxilioMoradia.data_inicio_residencia} a {dadosAuxilioMoradia.data_termino_residencia}</strong></div>
                      {dadosAuxilioMoradia.valor_bolsa_mensal && (
                        <div><span className="text-gray-500">Bolsa:</span> <strong>{dadosAuxilioMoradia.valor_bolsa_mensal}</strong></div>
                      )}
                      {calcularValorCausa() && (
                        <div><span className="text-gray-500">Valor estimado:</span> <strong className="text-green-700">{calcularValorCausa()?.valorCausa.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</strong></div>
                      )}
                    </div>
                  </div>
                )}

                <div className="bg-gray-50 rounded-xl p-4">
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                    <FileText className="w-4 h-4" /> Documentos
                  </h3>
                  {(arquivos.length > 0 || Object.values(arquivosDemanda).some(f => f && f.length > 0)) ? (
                    <ul className="text-sm space-y-1">
                      {/* Documentos específicos da demanda */}
                      {Object.entries(arquivosDemanda).map(([docId, files]) => {
  if (!files || files.length === 0) return null
  const doc = documentosAuxilioMoradia.find(d => d.id === docId)
  return files.map((file, idx) => (
    <li key={`${docId}-${idx}`} className="flex items-center gap-2">
      <FileCheck className="w-4 h-4 text-green-600" />
      <span className="text-gray-600">{doc?.nome}:</span> {file.name}
    </li>
  ))
})}
                      {/* Documentos gerais */}
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

              {/* Checkbox de Aceite dos Termos */}
              <div className="bg-gray-50 rounded-xl p-4">
                <div className="flex items-start gap-3">
                  <input
                    type="checkbox"
                    id="aceite-termos"
                    checked={termosAceitos}
                    onChange={(e) => setTermosAceitos(e.target.checked)}
                    className="mt-1 h-5 w-5 rounded border-gray-300 text-red-800 focus:ring-red-800 cursor-pointer"
                  />
                  <label htmlFor="aceite-termos" className="text-sm text-gray-700 cursor-pointer">
                    Li e aceito os{' '}
                    <button
                      type="button"
                      onClick={() => setModalTermos('termos')}
                      className="text-red-800 hover:text-red-900 underline font-semibold"
                    >
                      Termos de Uso
                    </button>
                    {' '}e a{' '}
                    <button
                      type="button"
                      onClick={() => setModalTermos('privacidade')}
                      className="text-red-800 hover:text-red-900 underline font-semibold"
                    >
                      Política de Privacidade
                    </button>
                    {' '}do escritório Vaucher & Álvares Sociedade de Advogados.
                    <span className="text-red-500 ml-1">*</span>
                  </label>
                </div>
                {!termosAceitos && (
                  <p className="text-xs text-gray-500 mt-2 ml-8">
                    É necessário aceitar os termos para prosseguir com o cadastro.
                  </p>
                )}
              </div>

              <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                <p className="text-sm text-red-800">
                  <strong>Importante:</strong> Ao enviar este cadastro, você declara que todas as informações fornecidas são verdadeiras e autoriza o escritório Vaucher & Álvares a entrar em contato para dar andamento à sua demanda.
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

            {step < totalSteps ? (
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
                disabled={enviando || !termosAceitos}
                className="flex items-center gap-2 px-8 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
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

        {/* Modal de Termos */}
        {modalTermos && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl">
              <div className="p-4 border-b flex justify-between items-center bg-gray-50 rounded-t-2xl">
                <h3 className="text-lg font-bold text-gray-800">
                  {modalTermos === 'termos' ? 'Termos de Uso' : 'Política de Privacidade'}
                </h3>
                <button
                  onClick={() => setModalTermos(null)}
                  className="text-gray-500 hover:text-gray-700 p-1 rounded-full hover:bg-gray-200 transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              <div className="p-6 overflow-y-auto flex-1">
                {carregandoTermos ? (
                  <div className="flex items-center justify-center py-8">
                    <div className="w-8 h-8 border-4 border-red-800 border-t-transparent rounded-full animate-spin"></div>
                  </div>
                ) : (
                  <div 
                    className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-h1:text-xl prose-h2:text-lg prose-h2:mt-6 prose-h2:mb-3 prose-p:text-gray-600 prose-li:text-gray-600 prose-table:text-sm"
                    dangerouslySetInnerHTML={{ 
                      __html: modalTermos === 'termos' 
                        ? (termosUso?.conteudo || '<p>Termos não disponíveis.</p>')
                        : (politicaPrivacidade?.conteudo || '<p>Política não disponível.</p>')
                    }} 
                  />
                )}
              </div>
              
              <div className="p-4 border-t flex justify-between items-center bg-gray-50 rounded-b-2xl">
                <span className="text-xs text-gray-500">
                  Versão {modalTermos === 'termos' ? termosUso?.versao : politicaPrivacidade?.versao}
                </span>
                <button
                  onClick={() => setModalTermos(null)}
                  className="px-6 py-2 bg-red-800 text-white rounded-lg hover:bg-red-900 transition-colors font-medium"
                >
                  Fechar
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <p className="text-center text-gray-400 text-xs mt-8">
          © {new Date().getFullYear()} Vaucher e Álvares Sociedade de Advogados — Todos os direitos reservados
        </p>
      </main>
    </div>
  )
}
