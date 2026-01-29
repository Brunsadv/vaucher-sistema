# Melhorias Pendentes - Sistema Vaucher e Álvares

**Gerado em:** 29/01/2026
**Diagnóstico por:** Claude Opus 4.5
**Status:** Aguardando implementação

---

## Como Usar Este Arquivo

Basta dizer: "Execute a melhoria X" ou "Implemente as melhorias de prioridade alta" e eu terei todas as coordenadas necessárias para executar sem retrabalho.

---

## PRIORIDADE ALTA (Impacto Imediato)

### 1. Substituir `alert()` por Toast no Frontend

**Problema:** 26+ usos de `alert()` bloqueiam a thread e são má prática de UX.

**Arquivo:** `frontend-admin/app/page.tsx`

**Linhas afetadas:**
- 2705, 2709, 2727, 2731, 2751, 2763, 2787, 2793
- 3183, 3220, 3259, 3264, 4851, 4856

**Solução:**
1. Criar componente `components/Toast.tsx`
2. Criar hook `hooks/useToast.ts`
3. Substituir todos os `alert()` por `toast.success()` ou `toast.error()`

**Código do componente Toast:**
```tsx
// frontend-admin/components/Toast.tsx
'use client'
import { useState, useEffect, createContext, useContext } from 'react'
import { CheckCircle, AlertCircle, X } from 'lucide-react'

interface ToastMessage {
  id: number
  type: 'success' | 'error' | 'info'
  message: string
}

interface ToastContextType {
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastContextType | null>(null)

export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within ToastProvider')
  return context
}

export const ToastProvider = ({ children }: { children: React.ReactNode }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const addToast = (type: ToastMessage['type'], message: string) => {
    const id = Date.now()
    setToasts(prev => [...prev, { id, type, message }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 4000)
  }

  const removeToast = (id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  return (
    <ToastContext.Provider value={{
      success: (msg) => addToast('success', msg),
      error: (msg) => addToast('error', msg),
      info: (msg) => addToast('info', msg),
    }}>
      {children}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map(toast => (
          <div
            key={toast.id}
            className={`flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg min-w-[300px] animate-slide-in ${
              toast.type === 'success' ? 'bg-green-500 text-white' :
              toast.type === 'error' ? 'bg-red-500 text-white' :
              'bg-blue-500 text-white'
            }`}
          >
            {toast.type === 'success' ? <CheckCircle className="w-5 h-5" /> :
             toast.type === 'error' ? <AlertCircle className="w-5 h-5" /> :
             <AlertCircle className="w-5 h-5" />}
            <span className="flex-1">{toast.message}</span>
            <button onClick={() => removeToast(toast.id)}>
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
```

**Adicionar ao globals.css:**
```css
@keyframes slide-in {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
.animate-slide-in {
  animation: slide-in 0.3s ease-out;
}
```

**Modificar layout.tsx:** Envolver children com `<ToastProvider>`

**Substituições no page.tsx:**
- `alert('Mensagem')` → `toast.success('Mensagem')` ou `toast.error('Mensagem')`

---

### 2. Criar Índices no Banco de Dados

**Problema:** Queries lentas em tabelas grandes sem índices.

**Arquivo:** `backend/modules/database.py` (função `inicializar_banco`)

**Adicionar após criação das tabelas (linha ~270):**
```python
# Criar índices para performance
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_cadastros_email
    ON cadastros((dados->>'email'));
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_cadastros_cpf
    ON cadastros((dados->>'cpf'));
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_processos_cadastro
    ON processos(cadastro_id);
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_processos_numero
    ON processos(numero_processo);
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_andamentos_processo
    ON processo_andamentos(processo_id);
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_contratos_cadastro
    ON contratos(cadastro_id);
""")
cur.execute("""
    CREATE INDEX IF NOT EXISTS idx_mensagens_cadastro
    ON mensagens(cadastro_id);
""")
logger.info("Índices de performance criados/verificados")
```

---

### 3. Paginação em `carregar_cadastros()`

**Problema:** Carrega TODOS os cadastros em memória, causa timeout com >10k registros.

**Arquivo:** `backend/modules/database.py`

**Função atual (linha ~778-804):**
```python
def carregar_cadastros():
    # ... código atual sem LIMIT
```

**Substituir por:**
```python
def carregar_cadastros(limit: int = 500, offset: int = 0, status: str = None):
    """Carrega cadastros com paginação."""
    conn = get_db()
    if not conn:
        return []

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        query = "SELECT * FROM cadastros"
        params = []

        if status:
            query += " WHERE status = %s"
            params.append(status)

        query += " ORDER BY data_hora DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, params)
        cadastros = cur.fetchall()

        # Converter dados JSON
        for c in cadastros:
            if isinstance(c.get('dados'), str):
                try:
                    c['dados'] = json.loads(c['dados'])
                except:
                    c['dados'] = {}

        return cadastros
    except Exception as e:
        logger.error(f"Erro ao carregar cadastros: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def contar_cadastros(status: str = None) -> int:
    """Conta total de cadastros para paginação."""
    conn = get_db()
    if not conn:
        return 0

    try:
        cur = conn.cursor()
        if status:
            cur.execute("SELECT COUNT(*) FROM cadastros WHERE status = %s", (status,))
        else:
            cur.execute("SELECT COUNT(*) FROM cadastros")
        return cur.fetchone()[0]
    except Exception as e:
        logger.error(f"Erro ao contar cadastros: {e}")
        return 0
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
```

**Atualizar endpoint em main.py (linha ~1657):**
```python
@app.get("/api/cadastros")
async def listar_cadastros(
    limit: int = 500,
    offset: int = 0,
    status: str = None,
    admin=Depends(verificar_admin)
):
    cadastros = carregar_cadastros(limit=limit, offset=offset, status=status)
    total = contar_cadastros(status=status)
    return {
        "cadastros": cadastros,
        "total": total,
        "limit": limit,
        "offset": offset
    }
```

---

## PRIORIDADE MÉDIA (Melhorias de Qualidade)

### 4. Validar MIME Type Real de Uploads

**Problema:** Aceita qualquer arquivo baseado apenas na extensão.

**Arquivo:** `backend/main.py` (função de upload, linha ~1055-1080)

**Instalar dependência:**
```bash
pip install python-magic-bin  # Windows
# ou
pip install python-magic  # Linux/Mac
```

**Adicionar validação:**
```python
import magic

ALLOWED_MIME_TYPES = {
    'application/pdf': ['.pdf'],
    'image/jpeg': ['.jpg', '.jpeg'],
    'image/png': ['.png'],
    'application/msword': ['.doc'],
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
}

def validar_arquivo(arquivo: UploadFile) -> bool:
    """Valida se o arquivo é do tipo permitido."""
    # Ler primeiros bytes para detectar tipo real
    header = arquivo.file.read(2048)
    arquivo.file.seek(0)  # Voltar ao início

    mime = magic.from_buffer(header, mime=True)
    extensao = os.path.splitext(arquivo.filename)[1].lower()

    if mime not in ALLOWED_MIME_TYPES:
        return False

    if extensao not in ALLOWED_MIME_TYPES[mime]:
        return False

    return True
```

**Usar antes de salvar:**
```python
if not validar_arquivo(arquivo):
    raise HTTPException(status_code=400, detail="Tipo de arquivo não permitido")
```

---

### 5. Consolidar Modelos Pydantic

**Problema:** Mesmos modelos definidos em 3 arquivos diferentes.

**Arquivos afetados:**
- `backend/modules/models.py` (principal)
- `backend/routes/admin_cadastros.py` (duplicado)
- `backend/routes/portal_cliente.py` (duplicado)

**Modelos duplicados:**
- `ProcessoInfoModel`
- `AndamentoModel`
- `ClienteLogin`
- `MensagemEnvio`

**Solução:**
1. Manter apenas em `modules/models.py`
2. Importar nos outros arquivos:
```python
from modules.models import (
    ProcessoInfoModel,
    AndamentoModel,
    ClienteLogin,
    MensagemEnvio,
)
```
3. Remover definições duplicadas dos outros arquivos

---

### 6. Adicionar useMemo/useCallback no Frontend

**Problema:** Funções recriadas a cada render, causando re-renders desnecessários.

**Arquivo:** `frontend-admin/app/page.tsx`

**Funções a memoizar com useCallback:**
```tsx
// Linha ~2658
const carregarCadastros = useCallback(async () => {
  // ... código existente
}, [user.token])

// Linha ~2878
const carregarDadosCliente = useCallback(async (cadastroId: string) => {
  // ... código existente
}, [user.token])

// Linha ~3031
const enviarMensagem = useCallback(async () => {
  // ... código existente
}, [user.token, selectedCadastro?.id, novaMensagem])
```

**Listas a memoizar com useMemo:**
```tsx
// Linha ~3121
const filteredCadastros = useMemo(() =>
  cadastros.filter(c => {
    const matchesStatus = filterStatus === 'todos' || c.status === filterStatus
    const matchesSearch = c.dados.nome.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         c.dados.cpf.includes(searchTerm)
    return matchesStatus && matchesSearch
  }),
  [cadastros, filterStatus, searchTerm]
)
```

---

## PRIORIDADE BAIXA (Refatoração Futura)

### 7. Extrair Componentes Reutilizáveis

**Componentes sugeridos:**

#### 7.1 ConfirmationModal
```tsx
// frontend-admin/components/ConfirmationModal.tsx
interface Props {
  isOpen: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  onConfirm: () => void
  onCancel: () => void
  variant?: 'danger' | 'warning' | 'info'
}

export default function ConfirmationModal({ ... }: Props) {
  if (!isOpen) return null
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button onClick={onCancel} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">
            {cancelText || 'Cancelar'}
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 rounded-lg text-white ${
              variant === 'danger' ? 'bg-red-600 hover:bg-red-700' :
              variant === 'warning' ? 'bg-amber-600 hover:bg-amber-700' :
              'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {confirmText || 'Confirmar'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

#### 7.2 LoadingSpinner
```tsx
// frontend-admin/components/LoadingSpinner.tsx
export default function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' }
  return (
    <div className={`${sizes[size]} border-2 border-gray-200 border-t-red-800 rounded-full animate-spin`} />
  )
}
```

#### 7.3 EmptyState
```tsx
// frontend-admin/components/EmptyState.tsx
import { LucideIcon } from 'lucide-react'

interface Props {
  icon: LucideIcon
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export default function EmptyState({ icon: Icon, title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Icon className="w-12 h-12 text-gray-300 mb-4" />
      <h3 className="text-lg font-medium text-gray-900">{title}</h3>
      {description && <p className="text-gray-500 mt-1">{description}</p>}
      {action && (
        <button onClick={action.onClick} className="mt-4 text-red-800 hover:underline">
          {action.label}
        </button>
      )}
    </div>
  )
}
```

---

### 8. Headers de Segurança

**Arquivo:** `backend/main.py`

**Adicionar middleware após criar app (linha ~115):**
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Middleware de segurança
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    # HSTS apenas em produção
    if "railway.app" in str(request.url):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

---

### 9. Debounce na Busca do Frontend

**Arquivo:** `frontend-admin/app/page.tsx`

**Criar hook useDebounce:**
```tsx
// Adicionar no início do arquivo ou criar hooks/useDebounce.ts
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}
```

**Usar no componente (linha ~2556):**
```tsx
const [searchTerm, setSearchTerm] = useState('')
const debouncedSearch = useDebounce(searchTerm, 300)

// Usar debouncedSearch no filtro ao invés de searchTerm
const filteredCadastros = useMemo(() =>
  cadastros.filter(c => {
    const matchesSearch = c.dados.nome.toLowerCase().includes(debouncedSearch.toLowerCase()) ||
                         c.dados.cpf.includes(debouncedSearch)
    // ...
  }),
  [cadastros, filterStatus, debouncedSearch]
)
```

---

### 10. Lazy Loading de Imagens

**Arquivo:** `frontend-admin/components/InsightsManager.tsx`

**Linha ~454-463, adicionar `loading="lazy"`:**
```tsx
<img
  src={imageUrl}
  alt={insight.titulo}
  loading="lazy"
  className="w-full h-48 object-cover"
/>
```

---

### 11. Invalidação de Token no Logout

**Problema:** Token continua válido após logout.

**Solução simples (blacklist em memória):**

**Arquivo:** `backend/modules/auth.py`

```python
# Adicionar no início do arquivo
from datetime import datetime, timedelta

# Blacklist simples em memória (para produção usar Redis)
_token_blacklist = set()
_blacklist_cleanup_time = datetime.now()

def adicionar_token_blacklist(token: str):
    """Adiciona token à blacklist."""
    global _blacklist_cleanup_time
    _token_blacklist.add(token)

    # Limpar blacklist a cada hora (tokens expirados)
    if datetime.now() - _blacklist_cleanup_time > timedelta(hours=1):
        _token_blacklist.clear()
        _blacklist_cleanup_time = datetime.now()

def token_na_blacklist(token: str) -> bool:
    """Verifica se token está na blacklist."""
    return token in _token_blacklist
```

**Modificar verificar_token (linha ~51):**
```python
def verificar_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")

    token = authorization.replace("Bearer ", "")

    # Verificar blacklist
    if token_na_blacklist(token):
        raise HTTPException(status_code=401, detail="Token invalidado")

    # ... resto do código
```

**Modificar logout em routes/auth.py (linha ~77):**
```python
from modules.auth import adicionar_token_blacklist

@router.post("/logout")
def logout(authorization: str = Header(None)):
    """Encerra a sessão do usuário."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        adicionar_token_blacklist(token)
    return {"success": True}
```

---

## Checklist de Implementação

- [ ] 1. Toast notifications (substituir alert)
- [ ] 2. Índices no banco de dados
- [ ] 3. Paginação em carregar_cadastros
- [ ] 4. Validação MIME type de uploads
- [ ] 5. Consolidar modelos Pydantic
- [ ] 6. useMemo/useCallback no frontend
- [ ] 7. Componentes reutilizáveis (Toast, Modal, etc)
- [ ] 8. Headers de segurança
- [ ] 9. Debounce na busca
- [ ] 10. Lazy loading de imagens
- [ ] 11. Invalidação de token no logout

---

## Notas Importantes

1. **Sempre testar localmente** antes de fazer push
2. **Fazer backup do banco** antes de criar índices em produção
3. **Manter compatibilidade** - não quebrar APIs existentes
4. **Commits pequenos** - uma melhoria por commit

---

*Documento gerado automaticamente. Atualizar conforme implementação.*
