# Plano de Refatoração do Backend - Vaucher e Álvares

**Data:** 23/01/2026
**Autor:** Claude (assistente de desenvolvimento)
**Status:** Em andamento

---

## Situação Atual

### Métricas do main.py
| Métrica | Valor |
|---------|-------|
| Linhas totais | 9.318 |
| Endpoints (@app) | 165 |
| Funções | 233 |
| Módulos já extraídos | 8 |

### Módulos Existentes (✓ Funcionando)
```
backend/
├── modules/
│   ├── config.py        ✓ Configurações centralizadas
│   ├── security.py      ✓ Bcrypt, JWT, validação (ATUALIZADO)
│   ├── database.py      ✓ Conexão e CRUD básico
│   ├── models.py        ✓ Modelos Pydantic
│   ├── documents.py     ✓ Geração de documentos
│   ├── email.py         ✓ Envio de emails
│   ├── assinatura.py    ✓ Assinatura digital
│   └── prazos.py        ✓ Prazos processuais (NOVO)
└── routes/
    ├── __init__.py      ✓ Inicializador
    ├── auth.py          ✓ Autenticação (CRIADO, não integrado)
    ├── datajud.py       ✓ CNJ DataJud (CRIADO, não integrado)
    ├── prazos.py        ✓ Prazos (CRIADO, não integrado)
    └── banners.py       ✓ Banners (CRIADO, não integrado)
```

---

## Fase 1: Segurança (✓ CONCLUÍDA)

| Item | Status |
|------|--------|
| Bcrypt para senhas | ✓ Implementado |
| JWT com expiração | ✓ 24h admin, 72h cliente |
| Rate limiting | ✓ 5/min nos logins |
| Validação de uploads | ✓ Extensões e tamanho |
| Sanitização de arquivos | ✓ Path traversal blocked |
| CORS restritivo | ✓ Métodos específicos |
| Migração automática senhas | ✓ No login |

---

## Fase 2: Integração de Rotas (PRÓXIMA)

### Prioridade 1 - Rotas já criadas
Integrar os 4 módulos já criados em `/routes`:

| Módulo | Endpoints | Linhas | Risco |
|--------|-----------|--------|-------|
| auth.py | 8 | ~200 | Baixo |
| prazos.py | 11 | ~200 | Baixo |
| datajud.py | 3 | ~280 | Baixo |
| banners.py | 6 | ~130 | Baixo |

**Ação:** Adicionar `app.include_router()` no main.py e remover endpoints duplicados.

### Prioridade 2 - Novos módulos a criar

| Módulo | Seção no main.py | Linhas aprox. |
|--------|------------------|---------------|
| routes/cadastros.py | 372-711 | ~340 |
| routes/financeiro.py | 1333-1487 | ~155 |
| routes/processos.py | 4017-4179, 4180-4244 | ~230 |
| routes/honorarios.py | 4288-4379 | ~90 |
| routes/documentos.py | 4450-4681, 4682-4729 | ~280 |
| routes/portal_cliente.py | 2876-3286, 4730-4823 | ~500 |
| routes/backup.py | 5370-6655 | ~1285 |
| routes/peticoes.py | 6851-8413 | ~1560 |
| routes/mensagens.py | 4093-4179 | ~85 |

---

## Fase 3: Organização de Funções do Banco

Mover funções de banco que estão no main.py para modules/database.py:

| Seção | Linhas | Funções |
|-------|--------|---------|
| Demandas específicas | 241-370 | 6 funções |
| Email atualização | 713-1262 | Várias |
| Portal funções | 1591-1872 | ~15 funções |
| Andamentos | 1873-1950 | 4 funções |
| Honorários | 1951-2193 | 8 funções |
| Parcelas | 2194-2280 | 4 funções |
| Comprovantes | 2281-2410 | 5 funções |
| Documentos | 2411-2665 | 8 funções |
| Mensagens | 2744-2848 | 4 funções |

---

## Cronograma Sugerido

### Semana 1: Integração Básica
- [ ] Dia 1-2: Integrar routes/auth.py
- [ ] Dia 3: Integrar routes/prazos.py
- [ ] Dia 4: Integrar routes/datajud.py
- [ ] Dia 5: Integrar routes/banners.py
- [ ] Testes completos

### Semana 2: Módulos Críticos
- [ ] Dia 1-2: Criar e integrar routes/cadastros.py
- [ ] Dia 3-4: Criar e integrar routes/processos.py
- [ ] Dia 5: Criar e integrar routes/honorarios.py

### Semana 3: Portal e Documentos
- [ ] Dia 1-2: Criar routes/portal_cliente.py
- [ ] Dia 3-4: Criar routes/documentos.py
- [ ] Dia 5: Criar routes/financeiro.py

### Semana 4: Módulos Grandes
- [ ] Dia 1-3: Criar routes/backup.py (maior módulo)
- [ ] Dia 4-5: Criar routes/peticoes.py

### Semana 5: Limpeza Final
- [ ] Mover funções de banco para database.py
- [ ] Remover código duplicado do main.py
- [ ] Testes de integração completos
- [ ] Documentação da API

---

## Estrutura Final Esperada

```
backend/
├── main.py              (~500 linhas - apenas setup e imports)
├── modules/
│   ├── config.py
│   ├── security.py
│   ├── database.py      (expandido com mais funções)
│   ├── models.py
│   ├── documents.py
│   ├── email.py
│   ├── assinatura.py
│   └── prazos.py
└── routes/
    ├── __init__.py
    ├── auth.py
    ├── cadastros.py
    ├── processos.py
    ├── honorarios.py
    ├── financeiro.py
    ├── documentos.py
    ├── portal_cliente.py
    ├── mensagens.py
    ├── backup.py
    ├── peticoes.py
    ├── datajud.py
    ├── prazos.py
    └── banners.py
```

---

## Benefícios Esperados

1. **Manutenibilidade**: Arquivos menores e focados
2. **Testabilidade**: Módulos isolados para testes unitários
3. **Colaboração**: Múltiplos desenvolvedores podem trabalhar simultaneamente
4. **Performance**: Imports mais rápidos
5. **Escalabilidade**: Fácil adicionar novos módulos

---

## Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| Quebrar endpoints existentes | Testar cada migração antes de remover do main |
| Imports circulares | Usar lazy imports quando necessário |
| Dependências não mapeadas | Mapear todas as dependências antes de mover |
| Downtime em produção | Deploy incremental, rollback preparado |

---

## Próximos Passos Imediatos

1. **Testar API em produção** para confirmar que correções de segurança funcionam
2. **Integrar routes/auth.py** como primeiro teste de integração
3. **Validar que o Railway redeploy funciona** com as novas dependências
4. **Monitorar logs** para detectar qualquer problema

---

## Notas Técnicas

### Como integrar um módulo de rotas

```python
# No main.py, adicionar após criar o app:
from routes import auth_router, prazos_router, datajud_router, banners_router

app.include_router(auth_router)
app.include_router(prazos_router)
app.include_router(datajud_router)
app.include_router(banners_router)
```

### Depois de integrar, remover os endpoints duplicados do main.py

Buscar pelos decoradores `@app.post`, `@app.get`, etc. e comentar/remover as funções correspondentes que foram movidas para os routers.

---

*Documento gerado automaticamente. Atualizar conforme progresso.*
