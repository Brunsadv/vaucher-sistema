'use client'

import { useState, useEffect } from 'react'
import {
  Plus, Edit, Trash2, Eye, EyeOff, Search, Filter,
  FileText, AlertTriangle, Scale, Newspaper, Star,
  Upload, X, Save, ArrowLeft, ExternalLink
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Insight {
  id: string
  slug: string
  categoria: string
  titulo: string
  titulo_en?: string
  titulo_es?: string
  resumo: string
  resumo_en?: string
  resumo_es?: string
  conteudo: string
  conteudo_en?: string
  conteudo_es?: string
  fonte?: string
  fonte_url?: string
  imagem_path?: string
  tags: string[]
  destaque: boolean
  status: string
  autor_nome?: string
  data_publicacao?: string
  criado_em: string
  atualizado_em: string
}

interface InsightsManagerProps {
  token: string
  onClose: () => void
}

const CATEGORIAS = [
  { id: 'artigo', label: 'Artigo', icon: FileText, color: 'blue' },
  { id: 'jurisprudencia', label: 'Jurisprudência', icon: Scale, color: 'purple' },
  { id: 'alerta', label: 'Alerta de Golpe', icon: AlertTriangle, color: 'yellow' },
  { id: 'noticia', label: 'Notícia', icon: Newspaper, color: 'green' },
]

export default function InsightsManager({ token, onClose }: InsightsManagerProps) {
  const [insights, setInsights] = useState<Insight[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Filtros
  const [filtroCategoria, setFiltroCategoria] = useState('')
  const [filtroStatus, setFiltroStatus] = useState('')
  const [busca, setBusca] = useState('')

  // Modal de edição
  const [showModal, setShowModal] = useState(false)
  const [editando, setEditando] = useState<Insight | null>(null)
  const [salvando, setSalvando] = useState(false)

  // Formulário
  const [form, setForm] = useState({
    titulo: '',
    titulo_en: '',
    titulo_es: '',
    categoria: 'artigo',
    resumo: '',
    resumo_en: '',
    resumo_es: '',
    conteudo: '',
    conteudo_en: '',
    conteudo_es: '',
    fonte: '',
    fonte_url: '',
    tags: '',
    destaque: false,
    status: 'rascunho'
  })
  const [imagemFile, setImagemFile] = useState<File | null>(null)
  const [imagemPreview, setImagemPreview] = useState<string | null>(null)

  // Aba ativa no formulário (PT/EN/ES)
  const [idiomaAtivo, setIdiomaAtivo] = useState<'pt' | 'en' | 'es'>('pt')

  // Estatísticas
  const [stats, setStats] = useState({
    total: 0,
    por_status: {} as Record<string, number>,
    por_categoria: {} as Record<string, number>
  })

  useEffect(() => {
    carregarInsights()
    carregarEstatisticas()
  }, [filtroCategoria, filtroStatus])

  const carregarInsights = async () => {
    setLoading(true)
    try {
      let url = `${API_URL}/api/admin/insights?limite=100`
      if (filtroCategoria) url += `&categoria=${filtroCategoria}`
      if (filtroStatus) url += `&status=${filtroStatus}`

      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!res.ok) throw new Error('Erro ao carregar insights')

      const data = await res.json()
      setInsights(data.insights || [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const carregarEstatisticas = async () => {
    try {
      const res = await fetch(`${API_URL}/api/admin/insights/estatisticas`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Erro ao carregar estatísticas:', err)
    }
  }

  const abrirNovoInsight = () => {
    setEditando(null)
    setForm({
      titulo: '',
      titulo_en: '',
      titulo_es: '',
      categoria: 'artigo',
      resumo: '',
      resumo_en: '',
      resumo_es: '',
      conteudo: '',
      conteudo_en: '',
      conteudo_es: '',
      fonte: '',
      fonte_url: '',
      tags: '',
      destaque: false,
      status: 'rascunho'
    })
    setImagemFile(null)
    setImagemPreview(null)
    setIdiomaAtivo('pt')
    setShowModal(true)
  }

  const abrirEditarInsight = (insight: Insight) => {
    setEditando(insight)
    setForm({
      titulo: insight.titulo || '',
      titulo_en: insight.titulo_en || '',
      titulo_es: insight.titulo_es || '',
      categoria: insight.categoria,
      resumo: insight.resumo || '',
      resumo_en: insight.resumo_en || '',
      resumo_es: insight.resumo_es || '',
      conteudo: insight.conteudo || '',
      conteudo_en: insight.conteudo_en || '',
      conteudo_es: insight.conteudo_es || '',
      fonte: insight.fonte || '',
      fonte_url: insight.fonte_url || '',
      tags: (insight.tags || []).join(', '),
      destaque: insight.destaque,
      status: insight.status
    })
    setImagemFile(null)
    setImagemPreview(insight.imagem_path ? `${API_URL}/api/public/insights/imagem/${insight.imagem_path.split('/').pop()}` : null)
    setIdiomaAtivo('pt')
    setShowModal(true)
  }

  const handleImagemChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setImagemFile(file)
      setImagemPreview(URL.createObjectURL(file))
    }
  }

  const salvarInsight = async () => {
    if (!form.titulo || !form.resumo || !form.conteudo) {
      setError('Preencha título, resumo e conteúdo')
      return
    }

    setSalvando(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('titulo', form.titulo)
      formData.append('titulo_en', form.titulo_en)
      formData.append('titulo_es', form.titulo_es)
      formData.append('categoria', form.categoria)
      formData.append('resumo', form.resumo)
      formData.append('resumo_en', form.resumo_en)
      formData.append('resumo_es', form.resumo_es)
      formData.append('conteudo', form.conteudo)
      formData.append('conteudo_en', form.conteudo_en)
      formData.append('conteudo_es', form.conteudo_es)
      formData.append('fonte', form.fonte)
      formData.append('fonte_url', form.fonte_url)
      formData.append('tags', form.tags)
      formData.append('destaque', String(form.destaque))
      formData.append('status', form.status)

      if (imagemFile) {
        formData.append('imagem', imagemFile)
      }

      const url = editando
        ? `${API_URL}/api/admin/insights/${editando.id}`
        : `${API_URL}/api/admin/insights`

      const method = editando ? 'PUT' : 'POST'

      const res = await fetch(url, {
        method,
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      })

      if (!res.ok) {
        const errData = await res.json()
        throw new Error(errData.detail || 'Erro ao salvar')
      }

      setSuccess(editando ? 'Insight atualizado!' : 'Insight criado!')
      setShowModal(false)
      carregarInsights()
      carregarEstatisticas()

      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSalvando(false)
    }
  }

  const alternarPublicacao = async (insight: Insight) => {
    try {
      const endpoint = insight.status === 'publicado' ? 'despublicar' : 'publicar'
      const res = await fetch(`${API_URL}/api/admin/insights/${insight.id}/${endpoint}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!res.ok) throw new Error('Erro ao alterar status')

      setSuccess(insight.status === 'publicado' ? 'Insight despublicado' : 'Insight publicado!')
      carregarInsights()
      carregarEstatisticas()

      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      setError(err.message)
    }
  }

  const deletarInsight = async (insight: Insight) => {
    if (!confirm(`Tem certeza que deseja excluir "${insight.titulo}"?`)) return

    try {
      const res = await fetch(`${API_URL}/api/admin/insights/${insight.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!res.ok) throw new Error('Erro ao excluir')

      setSuccess('Insight excluído!')
      carregarInsights()
      carregarEstatisticas()

      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      setError(err.message)
    }
  }

  const getCategoriaInfo = (cat: string) => {
    return CATEGORIAS.find(c => c.id === cat) || CATEGORIAS[0]
  }

  const insightsFiltrados = insights.filter(i => {
    if (busca) {
      const termo = busca.toLowerCase()
      return i.titulo.toLowerCase().includes(termo) ||
             i.resumo.toLowerCase().includes(termo)
    }
    return true
  })

  return (
    <div className="fixed inset-0 bg-gray-100 z-50 overflow-auto">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Gestão de Insights</h1>
              <p className="text-sm text-gray-500">Blog, Artigos, Jurisprudência e Alertas</p>
            </div>
          </div>

          <button
            onClick={abrirNovoInsight}
            className="flex items-center gap-2 px-4 py-2 bg-red-800 text-white rounded-lg hover:bg-red-700 transition"
          >
            <Plus className="w-4 h-4" />
            Novo Insight
          </button>
        </div>
      </div>

      {/* Alertas */}
      {error && (
        <div className="max-w-7xl mx-auto px-4 mt-4">
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError('')}><X className="w-4 h-4" /></button>
          </div>
        </div>
      )}

      {success && (
        <div className="max-w-7xl mx-auto px-4 mt-4">
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
            {success}
          </div>
        </div>
      )}

      {/* Estatísticas */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white rounded-xl p-4 border">
            <div className="text-2xl font-bold text-gray-900">{stats.total}</div>
            <div className="text-sm text-gray-500">Total</div>
          </div>
          <div className="bg-white rounded-xl p-4 border">
            <div className="text-2xl font-bold text-green-600">{stats.por_status?.publicado || 0}</div>
            <div className="text-sm text-gray-500">Publicados</div>
          </div>
          <div className="bg-white rounded-xl p-4 border">
            <div className="text-2xl font-bold text-yellow-600">{stats.por_status?.rascunho || 0}</div>
            <div className="text-sm text-gray-500">Rascunhos</div>
          </div>
          <div className="bg-white rounded-xl p-4 border">
            <div className="text-2xl font-bold text-purple-600">{stats.por_categoria?.jurisprudencia || 0}</div>
            <div className="text-sm text-gray-500">Jurisprudência</div>
          </div>
          <div className="bg-white rounded-xl p-4 border">
            <div className="text-2xl font-bold text-red-600">{stats.por_categoria?.alerta || 0}</div>
            <div className="text-sm text-gray-500">Alertas</div>
          </div>
        </div>
      </div>

      {/* Filtros */}
      <div className="max-w-7xl mx-auto px-4 pb-4">
        <div className="bg-white rounded-xl p-4 border flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar por título ou resumo..."
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500"
              />
            </div>
          </div>

          <select
            value={filtroCategoria}
            onChange={(e) => setFiltroCategoria(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-500"
          >
            <option value="">Todas categorias</option>
            {CATEGORIAS.map(cat => (
              <option key={cat.id} value={cat.id}>{cat.label}</option>
            ))}
          </select>

          <select
            value={filtroStatus}
            onChange={(e) => setFiltroStatus(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-red-500"
          >
            <option value="">Todos status</option>
            <option value="publicado">Publicado</option>
            <option value="rascunho">Rascunho</option>
          </select>
        </div>
      </div>

      {/* Lista de Insights */}
      <div className="max-w-7xl mx-auto px-4 pb-8">
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin w-8 h-8 border-4 border-red-800 border-t-transparent rounded-full mx-auto"></div>
            <p className="mt-2 text-gray-500">Carregando...</p>
          </div>
        ) : insightsFiltrados.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl border">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">Nenhum insight encontrado</p>
            <button
              onClick={abrirNovoInsight}
              className="mt-4 text-red-800 hover:underline"
            >
              Criar primeiro insight
            </button>
          </div>
        ) : (
          <div className="grid gap-4">
            {insightsFiltrados.map(insight => {
              const catInfo = getCategoriaInfo(insight.categoria)
              const CatIcon = catInfo.icon

              return (
                <div
                  key={insight.id}
                  className="bg-white rounded-xl border p-4 hover:shadow-md transition"
                >
                  <div className="flex gap-4">
                    {/* Imagem */}
                    <div className="w-24 h-24 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
                      {insight.imagem_path ? (
                        <img
                          src={`${API_URL}/api/public/insights/imagem/${insight.imagem_path.split('/').pop()}`}
                          alt={insight.titulo}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <CatIcon className="w-8 h-8 text-gray-400" />
                        </div>
                      )}
                    </div>

                    {/* Conteúdo */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
                              ${catInfo.color === 'blue' ? 'bg-blue-100 text-blue-800' : ''}
                              ${catInfo.color === 'purple' ? 'bg-purple-100 text-purple-800' : ''}
                              ${catInfo.color === 'yellow' ? 'bg-yellow-100 text-yellow-800' : ''}
                              ${catInfo.color === 'green' ? 'bg-green-100 text-green-800' : ''}
                            `}>
                              <CatIcon className="w-3 h-3" />
                              {catInfo.label}
                            </span>
                            {insight.destaque && (
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
                                <Star className="w-3 h-3" />
                                Destaque
                              </span>
                            )}
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium
                              ${insight.status === 'publicado' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}
                            `}>
                              {insight.status === 'publicado' ? 'Publicado' : 'Rascunho'}
                            </span>
                          </div>
                          <h3 className="font-semibold text-gray-900 truncate">{insight.titulo}</h3>
                          <p className="text-sm text-gray-500 line-clamp-2">{insight.resumo}</p>
                        </div>
                      </div>

                      <div className="flex items-center justify-between mt-3">
                        <div className="text-xs text-gray-400">
                          {insight.data_publicacao
                            ? `Publicado em ${new Date(insight.data_publicacao).toLocaleDateString('pt-BR')}`
                            : `Criado em ${new Date(insight.criado_em).toLocaleDateString('pt-BR')}`
                          }
                          {insight.autor_nome && ` por ${insight.autor_nome}`}
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => alternarPublicacao(insight)}
                            className={`p-2 rounded-lg transition ${
                              insight.status === 'publicado'
                                ? 'hover:bg-yellow-100 text-yellow-600'
                                : 'hover:bg-green-100 text-green-600'
                            }`}
                            title={insight.status === 'publicado' ? 'Despublicar' : 'Publicar'}
                          >
                            {insight.status === 'publicado' ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </button>
                          <button
                            onClick={() => abrirEditarInsight(insight)}
                            className="p-2 hover:bg-blue-100 text-blue-600 rounded-lg transition"
                            title="Editar"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => deletarInsight(insight)}
                            className="p-2 hover:bg-red-100 text-red-600 rounded-lg transition"
                            title="Excluir"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Modal de Edição */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Header do Modal */}
            <div className="px-6 py-4 border-b flex items-center justify-between">
              <h2 className="text-lg font-bold">
                {editando ? 'Editar Insight' : 'Novo Insight'}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Corpo do Modal */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Categoria e Status */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Categoria *
                  </label>
                  <select
                    value={form.categoria}
                    onChange={(e) => setForm({...form, categoria: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500"
                  >
                    {CATEGORIAS.map(cat => (
                      <option key={cat.id} value={cat.id}>{cat.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Status
                  </label>
                  <select
                    value={form.status}
                    onChange={(e) => setForm({...form, status: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500"
                  >
                    <option value="rascunho">Rascunho</option>
                    <option value="publicado">Publicado</option>
                  </select>
                </div>

                <div className="flex items-end">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={form.destaque}
                      onChange={(e) => setForm({...form, destaque: e.target.checked})}
                      className="w-5 h-5 rounded border-gray-300 text-red-800 focus:ring-red-500"
                    />
                    <span className="text-sm font-medium text-gray-700">Destaque</span>
                  </label>
                </div>
              </div>

              {/* Abas de Idioma */}
              <div className="flex gap-2 mb-4 border-b">
                {(['pt', 'en', 'es'] as const).map(lang => (
                  <button
                    key={lang}
                    onClick={() => setIdiomaAtivo(lang)}
                    className={`px-4 py-2 font-medium transition border-b-2 -mb-px ${
                      idiomaAtivo === lang
                        ? 'border-red-800 text-red-800'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {lang === 'pt' ? 'Português' : lang === 'en' ? 'English' : 'Español'}
                  </button>
                ))}
              </div>

              {/* Campos do idioma ativo */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Título {idiomaAtivo === 'pt' && '*'}
                  </label>
                  <input
                    type="text"
                    value={idiomaAtivo === 'pt' ? form.titulo : idiomaAtivo === 'en' ? form.titulo_en : form.titulo_es}
                    onChange={(e) => setForm({
                      ...form,
                      [idiomaAtivo === 'pt' ? 'titulo' : idiomaAtivo === 'en' ? 'titulo_en' : 'titulo_es']: e.target.value
                    })}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500"
                    placeholder={`Título em ${idiomaAtivo === 'pt' ? 'Português' : idiomaAtivo === 'en' ? 'Inglês' : 'Espanhol'}`}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Resumo {idiomaAtivo === 'pt' && '*'}
                  </label>
                  <textarea
                    value={idiomaAtivo === 'pt' ? form.resumo : idiomaAtivo === 'en' ? form.resumo_en : form.resumo_es}
                    onChange={(e) => setForm({
                      ...form,
                      [idiomaAtivo === 'pt' ? 'resumo' : idiomaAtivo === 'en' ? 'resumo_en' : 'resumo_es']: e.target.value
                    })}
                    rows={3}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500"
                    placeholder="Breve descrição do conteúdo"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Conteúdo {idiomaAtivo === 'pt' && '*'}
                  </label>
                  <textarea
                    value={idiomaAtivo === 'pt' ? form.conteudo : idiomaAtivo === 'en' ? form.conteudo_en : form.conteudo_es}
                    onChange={(e) => setForm({
                      ...form,
                      [idiomaAtivo === 'pt' ? 'conteudo' : idiomaAtivo === 'en' ? 'conteudo_en' : 'conteudo_es']: e.target.value
                    })}
                    rows={10}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500 font-mono text-sm"
                    placeholder="Conteúdo completo (suporta HTML)"
                  />
                  <p className="text-xs text-gray-500 mt-1">Suporta HTML para formatação</p>
                </div>
              </div>

              {/* Imagem */}
              <div className="mt-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Imagem de Capa
                </label>
                <div className="flex items-start gap-4">
                  {imagemPreview && (
                    <div className="w-32 h-32 rounded-lg overflow-hidden border">
                      <img src={imagemPreview} alt="Preview" className="w-full h-full object-cover" />
                    </div>
                  )}
                  <div className="flex-1">
                    <label className="flex items-center justify-center gap-2 px-4 py-8 border-2 border-dashed rounded-lg cursor-pointer hover:border-red-800 hover:bg-red-50 transition">
                      <Upload className="w-5 h-5 text-gray-400" />
                      <span className="text-sm text-gray-600">Clique para selecionar imagem</span>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleImagemChange}
                        className="hidden"
                      />
                    </label>
                    <p className="text-xs text-gray-500 mt-2">JPG, PNG ou GIF. Máx 10MB.</p>
                  </div>
                </div>
              </div>

              {/* Fonte e Tags */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Fonte
                  </label>
                  <input
                    type="text"
                    value={form.fonte}
                    onChange={(e) => setForm({...form, fonte: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500"
                    placeholder="Ex: STF, TST, Artigo próprio..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    URL da Fonte
                  </label>
                  <input
                    type="url"
                    value={form.fonte_url}
                    onChange={(e) => setForm({...form, fonte_url: e.target.value})}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500"
                    placeholder="https://..."
                  />
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tags
                </label>
                <input
                  type="text"
                  value={form.tags}
                  onChange={(e) => setForm({...form, tags: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500"
                  placeholder="trabalhista, sindical, jurisprudência (separadas por vírgula)"
                />
              </div>
            </div>

            {/* Footer do Modal */}
            <div className="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition"
              >
                Cancelar
              </button>
              <button
                onClick={salvarInsight}
                disabled={salvando}
                className="flex items-center gap-2 px-6 py-2 bg-red-800 text-white rounded-lg hover:bg-red-700 transition disabled:opacity-50"
              >
                {salvando ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Salvando...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Salvar
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
