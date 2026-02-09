# Politica de Upload de Arquivos

## Sistema Vaucher e Alvares Advocacia
**Atualizado em:** 08/02/2026
**Baseado em:** Resolucao CNJ n. 185/2013, Resolucao CNJ n. 656/2025, Manual PJe CNJ

---

## 1. Visao Geral

Todo upload de arquivo representa uma **porta de entrada para dados nao confiaveis** no sistema. Esta politica estabelece criterios rigorosos de validacao para garantir:

- **Seguranca:** Prevenir execucao de codigo malicioso
- **Compatibilidade:** Alinhamento com requisitos do PJe CNJ
- **Performance:** Limites de tamanho adequados
- **Auditoria:** Rastreabilidade de todas as operacoes

---

## 2. Formatos Aceitos

### 2.1 Compativeis com PJe (Protocolo Judicial)

| Tipo | Extensoes | Tamanho Max | Uso |
|------|-----------|-------------|-----|
| **Documento** | `.pdf` | 10 MB | Peticoes, contratos, documentos |
| **Imagem** | `.png`, `.jpg`, `.jpeg` | 5 MB | Provas, anexos fotograficos |
| **Audio** | `.mp3`, `.ogg` | 20 MB | Audiencias, depoimentos |
| **Video** | `.mp4` | 30 MB | Provas audiovisuais |

### 2.2 Uso Interno (Nao vao para PJe)

| Tipo | Extensoes | Tamanho Max | Observacao |
|------|-----------|-------------|------------|
| **Office** | `.doc`, `.docx`, `.xls`, `.xlsx`, `.odt`, `.ods` | 15 MB | Converter para PDF antes de protocolar |

### 2.3 Formatos Bloqueados (NUNCA aceitos)

```
Executaveis:    .exe, .bat, .cmd, .com, .msi, .scr
Scripts:        .php, .asp, .aspx, .jsp, .js, .vbs, .ps1, .py, .sh
Bibliotecas:    .dll, .so, .dylib
Imagens disco:  .iso, .img, .dmg
Web (XSS):      .html, .htm, .svg
Compactados:    .zip, .rar, .7z (exceto Office que usa ZIP internamente)
```

---

## 3. Validacoes de Seguranca

### 3.1 Camadas de Validacao

1. **Extensao do arquivo** (whitelist)
   - Apenas extensoes explicitamente permitidas
   - Lista negra de extensoes perigosas

2. **Tamanho por tipo**
   - Limites especificos por categoria
   - Limite absoluto de 50 MB

3. **Magic Bytes** (assinatura do arquivo)
   - Verifica o tipo REAL do arquivo
   - Previne extensao falsa (ex: .exe renomeado para .pdf)

4. **Padroes perigosos**
   - Detecta scripts embarcados (`<script>`, `<?php>`, etc)
   - Detecta executaveis disfarfados

5. **Sanitizacao do nome**
   - Remove path traversal (`../`)
   - Remove caracteres especiais
   - Limita tamanho do nome

6. **Hash SHA-256**
   - Integridade do arquivo
   - Deduplicacao de uploads identicos

### 3.2 Exemplo de Validacao

```python
from modules.upload_policy import validar_upload_completo

valido, erro, metadados = validar_upload_completo(
    filename="contrato.pdf",
    conteudo=arquivo_bytes,
    content_type="application/pdf"
)

if not valido:
    raise HTTPException(400, erro)

# Usar metadados para armazenamento
nome_seguro = metadados["nome_sanitizado"]
hash_arquivo = metadados["hash_sha256"]
compativel_pje = metadados["pje_compativel"]
```

---

## 4. Limites de Taxa (Rate Limiting)

| Metrica | Limite |
|---------|--------|
| Uploads por minuto (por IP) | 10 |
| Uploads por hora (por usuario) | 50 |
| Tamanho maximo absoluto | 50 MB |

---

## 5. Recomendacoes para Clientes

### 5.1 Antes de Enviar

- [ ] Converter documentos Word/Excel para PDF
- [ ] Comprimir imagens grandes (recomendado < 2 MB)
- [ ] Dividir videos longos em partes de ate 30 MB
- [ ] Usar nomes descritivos (ex: `contrato_trabalho_joao_silva.pdf`)

### 5.2 Formatos Ideais

| Tipo de Documento | Formato Recomendado |
|-------------------|---------------------|
| Peticoes | PDF (texto pesquisavel) |
| Contratos | PDF assinado digitalmente |
| Fotos | JPEG (comprimido) |
| Prints de tela | PNG |
| Audiencias | MP3 (audio) ou MP4 (video) |

---

## 6. Referencias PJe CNJ

### Links Oficiais

- [Tutorial CNJ - Arquivos acima de 10MB](https://www.cnj.jus.br/tutorial-explica-como-anexar-arquivos-acima-de-10-mb-pelo-pje/)
- [Resolucao CNJ n. 185/2013](https://atos.cnj.jus.br/atos/detalhar/1933)
- [CSJT - Limites de arquivos PJe](https://www.csjt.jus.br/web/csjt/noticias3/-/asset_publisher/RPt2/content/csjt-aumenta-tamanho-de-arquivos-e-quantidade-de-documentos-suportados-no-pje)
- [TRF1 - FAQ PJe](https://portal.trf1.jus.br/portaltrf1/processual/processo-judicial-eletronico/pje/perguntas-frequentes/)

### Limites por Tribunal (podem variar)

| Tribunal | PDF | Imagem | Audio | Video |
|----------|-----|--------|-------|-------|
| **CNJ (padrao)** | 10 MB | 10 MB | 20 MB | 30 MB |
| **TRF1** | 20 MB | 10 MB | 20 MB | - |
| **TJMG** | 1,5 MB* | - | - | - |

*TJMG tem limite menor, usar fragmentacao para arquivos maiores.

---

## 7. Auditoria e Logs

Todos os uploads sao registrados com:

- Data/hora
- Usuario
- IP de origem
- Nome original e sanitizado
- Hash SHA-256
- Tamanho
- Resultado da validacao

Logs sao mantidos para fins de:
- Investigacao de incidentes de seguranca
- Compliance com LGPD
- Auditoria de processos

---

## 8. Procedimento em Caso de Rejeicao

Se um arquivo for rejeitado:

1. **Verificar a mensagem de erro** - explica o motivo
2. **Converter para formato aceito** - preferencialmente PDF
3. **Reduzir tamanho** se necessario (compressao)
4. **Renomear** se o nome contem caracteres especiais
5. **Contatar suporte** se o erro persistir

---

## 9. Contato

**Suporte Tecnico:**
Email: atendimento@vaucherealvares.com
Telefone: (65) 3025-1223

---

*Este documento faz parte da documentacao tecnica do Sistema Vaucher e Alvares e deve ser atualizado sempre que houver mudancas nas politicas do PJe CNJ.*
