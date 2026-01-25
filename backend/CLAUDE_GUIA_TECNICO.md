# GUIA TECNICO - SISTEMA VAUCHER E ALVARES

**LEIA ESTE ARQUIVO ANTES DE QUALQUER ALTERACAO NO CODIGO**

Este documento contem informacoes criticas sobre a arquitetura do sistema.
Alteracoes sem considerar estas informacoes podem quebrar funcionalidades em producao.

---

## 1. ESTRUTURA DE PASTAS DE DOCUMENTOS

### CRITICO: Caminhos de Arquivos

Os documentos sao salvos em diferentes pastas dependendo do tipo.
**NUNCA altere estes caminhos sem atualizar TODOS os endpoints que os utilizam.**

```
/app/uploads/                          # UPLOADS_DIR no Railway
├── documentos_assinados/              # Documentos assinados (ZapSign webhook)
│   └── {cadastro_id}/
│       ├── contrato_assinado.pdf
│       └── procuracao_assinado.pdf
│
├── documentos_admin/                  # Documentos enviados pelo admin para cliente
│   └── {cadastro_id}/
│       └── {timestamp}_{nome_arquivo}
│
├── documentos_extras/                 # Documentos enviados pelo cliente (extras)
│   └── {cadastro_id}/
│       └── {timestamp}_{nome_arquivo}
│
├── documentos_demanda/                # Documentos da demanda especifica
│   └── {cadastro_id}/
│       └── {tipo}/{nome_arquivo}
│
├── comprovantes/                      # Comprovantes de pagamento
│   └── {cadastro_id}/
│       └── {parcela_id}_{timestamp}.{ext}
│
└── {cadastro_id}/                     # Documentos do cadastro inicial (LEGADO)
    ├── rg_frente.pdf
    ├── cpf.pdf
    └── assinados/                     # CAMINHO LEGADO - manter fallback
        └── *.pdf
```

### Fallbacks Implementados

Para documentos assinados, ha fallback para caminhos legados:
1. `uploads/documentos_assinados/{id}/` (atual)
2. `uploads/{id}/assinados/` (legado)
3. `/app/uploads/...` (caminhos absolutos antigos)

---

## 2. ESTRUTURA DO BANCO DE DADOS

### Tabelas Principais

```sql
-- Cadastros de clientes
cadastros (
    id VARCHAR(20) PRIMARY KEY,      -- UUID de 12 caracteres
    data VARCHAR(50),                -- ISO timestamp
    data_hora TIMESTAMP,
    status VARCHAR(20),              -- pendente, validado, enviado, assinado, concluido
    dados JSONB,                     -- Dados pessoais do cliente
    documentos JSONB,                -- Lista de documentos do cadastro
    arquivos_gerados JSONB,          -- Contrato e procuracao gerados
    documentos_assinados JSONB,
    data_assinatura TIMESTAMP,
    assinaturas_digitais JSONB,      -- Info do ZapSign
    documentos_finais JSONB
)

-- Autenticacao do portal do cliente
clientes_auth (
    id SERIAL PRIMARY KEY,
    cadastro_id VARCHAR(20) REFERENCES cadastros(id),
    senha_hash VARCHAR(255),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP,
    ultimo_acesso TIMESTAMP
)

-- Documentos enviados pelo admin para cliente
documentos_admin (
    id SERIAL PRIMARY KEY,
    cadastro_id VARCHAR(20) REFERENCES cadastros(id),
    nome_arquivo VARCHAR(255),
    nome_original VARCHAR(255),
    arquivo_path VARCHAR(500),       -- Caminho completo do arquivo
    descricao VARCHAR(255),
    enviado_por VARCHAR(255),
    criado_em TIMESTAMP
)

-- Documentos extras enviados pelo cliente
documentos_extras (
    id SERIAL PRIMARY KEY,
    cadastro_id VARCHAR(20) REFERENCES cadastros(id),
    nome_arquivo VARCHAR(255),
    nome_original VARCHAR(255),
    arquivo_path VARCHAR(500),
    descricao VARCHAR(255),
    criado_em TIMESTAMP
)

-- Documentos da demanda
documentos_demanda (
    id SERIAL PRIMARY KEY,
    cadastro_id VARCHAR(20) REFERENCES cadastros(id),
    tipo_documento VARCHAR(50),
    nome_arquivo VARCHAR(255),
    nome_original VARCHAR(255),
    arquivo_path VARCHAR(500),
    descricao TEXT,
    criado_em TIMESTAMP
)
```

### Migracoes

Migracoes sao executadas automaticamente em `init_db()` em `modules/database.py`.
Ao adicionar novas colunas, usar o padrao:

```sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='tabela' AND column_name='nova_coluna') THEN
        ALTER TABLE tabela ADD COLUMN nova_coluna TIPO DEFAULT valor;
    END IF;
END $$;
```

---

## 3. ESTRUTURA DE MODULOS

### Arquivos Principais

```
backend/
├── main.py                    # App principal, endpoints que NAO foram modularizados
├── modules/
│   ├── config.py              # Configuracoes, variaveis de ambiente, init_db
│   ├── database.py            # Funcoes CRUD do banco de dados
│   ├── auth.py                # Autenticacao admin (verificar_admin)
│   ├── security.py            # Funcoes de seguranca (tokens, sanitizacao)
│   ├── email.py               # Envio de emails via Resend
│   ├── documents.py           # Geracao de PDFs (contrato, procuracao)
│   ├── assinatura.py          # Integracao ZapSign
│   └── models.py              # Modelos Pydantic
├── routes/
│   ├── auth.py                # Rotas de login/logout
│   ├── admin_cadastros.py     # Rotas admin: clientes, documentos, acesso
│   ├── admin_processos.py     # Rotas admin: processos, contratos, mensagens
│   ├── portal_cliente.py      # Rotas do portal do cliente
│   ├── banners.py             # Rotas de banners
│   └── prazos.py              # Rotas de prazos processuais
└── test_backend.py            # Testes automatizados
```

### Dependencias entre Modulos

```
main.py
  └── importa de: modules/*, routes/*

routes/admin_cadastros.py
  └── importa de: modules/database.py, modules/auth.py, modules/security.py

routes/portal_cliente.py
  └── importa de: modules/database.py, modules/security.py

modules/database.py
  └── importa de: modules/config.py (get_db, logger)
```

**REGRA:** Ao mover funcoes entre modulos, verificar TODOS os arquivos que importam essa funcao.

---

## 4. ENDPOINTS CRITICOS

### Endpoints de Documentos

| Endpoint | Arquivo | Funcao DB | Pasta de Arquivos |
|----------|---------|-----------|-------------------|
| POST /api/admin/clientes/{id}/enviar-documentos | admin_cadastros.py | criar_documento_admin | documentos_admin/{id}/ |
| GET /api/admin/clientes/{id}/documentos-enviados | admin_cadastros.py | listar_documentos_admin | - |
| GET /api/admin/documentos/{id}/download | admin_cadastros.py | buscar_documento_admin | documentos_admin/{id}/ |
| POST /api/cliente/documentos-extras | portal_cliente.py | criar_documento_extra | documentos_extras/{id}/ |
| GET /api/cliente/documentos | main.py | listar_documentos_* | Multiplas pastas |
| GET /api/cadastros/{id}/assinados/{file} | main.py | - | documentos_assinados/{id}/ |
| POST /api/webhooks/zapsign | main.py | - | documentos_assinados/{id}/ |

### Endpoints de Autenticacao

| Endpoint | Arquivo | Descricao |
|----------|---------|-----------|
| POST /api/login | routes/auth.py | Login admin e cliente |
| POST /api/cliente/login | main.py | Login especifico cliente |
| GET /api/cliente/* | main.py, portal_cliente.py | Requer verificar_token_cliente |
| GET /api/admin/* | admin_cadastros.py, admin_processos.py | Requer verificar_admin |

---

## 5. REGRAS PARA REFATORACAO

### ANTES de qualquer alteracao:

1. **Ler este guia completamente**
2. **Executar testes:** `python test_backend.py`
3. **Verificar imports:** Usar grep para encontrar todos os usos de funcoes/classes
4. **Mapear caminhos:** Se mexer em arquivos, verificar todos os endpoints que usam esse caminho

### DURANTE a alteracao:

1. **Nunca remover imports** sem verificar se sao usados em outros arquivos
2. **Nunca alterar caminhos de arquivos** sem atualizar todos os endpoints
3. **Nunca alterar schema do banco** sem adicionar migracao
4. **Manter fallbacks** para caminhos legados de arquivos

### APOS a alteracao:

1. **Executar testes:** `python test_backend.py`
2. **Executar validacao:** `python validar_pre_deploy.py`
3. **Testar localmente** os endpoints afetados
4. **Fazer commit pequeno** com mensagem descritiva
5. **Aguardar deploy no Railway** e verificar logs
6. **Testar em producao** os endpoints afetados

### Checklist de Verificacao

- [ ] Testes passam localmente
- [ ] Validacao pre-deploy passa
- [ ] Nenhum import foi removido incorretamente
- [ ] Caminhos de arquivos estao consistentes
- [ ] Migracoes de banco estao implementadas
- [ ] Commit tem mensagem clara
- [ ] Deploy no Railway sem erros
- [ ] Endpoints funcionam em producao

---

## 6. VARIAVEIS DE AMBIENTE (Railway)

```
DATABASE_URL          # PostgreSQL connection string
RESEND_API_KEY        # API key do Resend para emails
FROM_EMAIL            # Email de origem (atendimento@vaucherealvares.com)
ZAPSIGN_API_TOKEN     # Token da API ZapSign
JWT_SECRET            # Chave secreta para tokens JWT
```

---

## 7. URLS EM PRODUCAO

- **Backend:** https://vaucher-sistema-production.up.railway.app
- **Portal Admin:** https://admin.vaucherealvares.com
- **Portal Cliente:** https://appcliente.vaucherealvares.com
- **Formulario Cadastro:** https://cadastro.vaucherealvares.com

---

## 8. ERROS COMUNS E SOLUCOES

### "value too long for type character varying(N)"
- **Causa:** Campo do banco com tamanho insuficiente
- **Solucao:** Adicionar migracao ALTER TABLE para aumentar tamanho

### "Arquivo nao encontrado" em documentos
- **Causa:** Caminho salvo no banco diferente do caminho real
- **Solucao:** Verificar consistencia de caminhos, adicionar fallbacks

### "NameError: name 'X' is not defined"
- **Causa:** Import removido ou funcao movida
- **Solucao:** Verificar todos os imports, usar grep para encontrar usos

### CORS errors no frontend
- **Causa:** Servidor crashou ou dominio nao esta em ALLOWED_ORIGINS
- **Solucao:** Verificar logs do Railway, adicionar dominio em config.py

---

## 9. COMANDOS UTEIS

```bash
# Executar testes
python test_backend.py

# Validar pre-deploy
python validar_pre_deploy.py

# Verificar sintaxe
python -m py_compile main.py

# Buscar usos de uma funcao
grep -r "nome_funcao" --include="*.py"

# Ver commits recentes
git log --oneline -10

# Reverter ultimo commit (se necessario)
git revert HEAD
```

---

**IMPORTANTE:** Este arquivo deve ser atualizado sempre que houver mudancas estruturais no sistema.

Ultima atualizacao: 25/01/2026
