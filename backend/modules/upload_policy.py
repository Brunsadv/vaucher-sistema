"""
Politica de Upload de Arquivos - Sistema Vaucher e Alvares
Criado em 08/02/2026

Este modulo implementa politicas de upload alinhadas com os requisitos do PJe CNJ
e boas praticas de seguranca para sistemas juridicos.

Referencias:
- Resolucao CNJ n. 185/2013 (regulamenta PJe)
- Resolucao CNJ n. 656/2025 (tamanhos minimos)
- Manual PJe - Formatos aceitos

PRINCIPIOS DE SEGURANCA:
1. Todo upload e uma porta de entrada para dados nao confiaveis
2. Validar TUDO: extensao, MIME type, magic bytes, tamanho, conteudo
3. Nunca confiar no Content-Type do header HTTP
4. Registrar todas as operacoes para auditoria
5. Limitar taxa de uploads por usuario/IP
"""

import os
import re
import hashlib
import mimetypes
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, List
from enum import Enum
from dataclasses import dataclass

from modules.config import logger

# ============================================
# CONFIGURACOES ALINHADAS COM PJE CNJ
# ============================================

class TipoArquivo(Enum):
    """Categorias de arquivos aceitos pelo sistema."""
    DOCUMENTO = "documento"
    IMAGEM = "imagem"
    AUDIO = "audio"
    VIDEO = "video"


@dataclass
class LimiteArquivo:
    """Configuracao de limite por tipo de arquivo."""
    extensoes: set
    tamanho_max_mb: float
    mime_types: set
    magic_bytes: List[Tuple[bytes, int]]  # [(bytes, offset)]
    pje_compativel: bool = True
    descricao: str = ""


# Configuracoes baseadas no PJe CNJ e boas praticas
POLITICA_ARQUIVOS: Dict[TipoArquivo, LimiteArquivo] = {
    TipoArquivo.DOCUMENTO: LimiteArquivo(
        extensoes={'.pdf'},
        tamanho_max_mb=10.0,  # PJe padrao: 10MB para PDF
        mime_types={'application/pdf'},
        magic_bytes=[(b'%PDF', 0)],
        pje_compativel=True,
        descricao="Documentos PDF para protocolo no PJe"
    ),
    TipoArquivo.IMAGEM: LimiteArquivo(
        extensoes={'.png', '.jpg', '.jpeg'},
        tamanho_max_mb=5.0,  # Conservador para imagens
        mime_types={'image/png', 'image/jpeg'},
        magic_bytes=[
            (b'\x89PNG\r\n\x1a\n', 0),  # PNG
            (b'\xff\xd8\xff', 0),        # JPEG
        ],
        pje_compativel=True,
        descricao="Imagens PNG/JPEG para anexos"
    ),
    TipoArquivo.AUDIO: LimiteArquivo(
        extensoes={'.mp3', '.ogg'},
        tamanho_max_mb=20.0,  # PJe permite ate 20MB para audio
        mime_types={'audio/mpeg', 'audio/ogg'},
        magic_bytes=[
            (b'ID3', 0),           # MP3 com tag ID3
            (b'\xff\xfb', 0),      # MP3 sem tag
            (b'\xff\xfa', 0),      # MP3 alternativo
            (b'OggS', 0),          # OGG
        ],
        pje_compativel=True,
        descricao="Arquivos de audio para audiencias"
    ),
    TipoArquivo.VIDEO: LimiteArquivo(
        extensoes={'.mp4'},
        tamanho_max_mb=30.0,  # PJe permite ate 30MB para video
        mime_types={'video/mp4'},
        magic_bytes=[
            (b'\x00\x00\x00\x18ftyp', 0),  # MP4 ftyp
            (b'\x00\x00\x00\x1cftyp', 0),  # MP4 ftyp alternativo
            (b'\x00\x00\x00\x20ftyp', 0),  # MP4 ftyp alternativo 2
        ],
        pje_compativel=True,
        descricao="Videos MP4 para provas audiovisuais"
    ),
}

# Documentos internos (nao vao para PJe, uso administrativo)
POLITICA_DOCUMENTOS_INTERNOS: Dict[str, LimiteArquivo] = {
    "office": LimiteArquivo(
        extensoes={'.doc', '.docx', '.xls', '.xlsx', '.odt', '.ods'},
        tamanho_max_mb=15.0,
        mime_types={
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.oasis.opendocument.text',
            'application/vnd.oasis.opendocument.spreadsheet',
        },
        magic_bytes=[
            (b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1', 0),  # OLE (doc, xls)
            (b'PK\x03\x04', 0),                         # ZIP (docx, xlsx, odt, ods)
        ],
        pje_compativel=False,
        descricao="Documentos Office para uso interno"
    ),
}

# Limite global de seguranca
TAMANHO_MAXIMO_ABSOLUTO_MB = 50.0  # Nenhum arquivo pode exceder 50MB
UPLOADS_POR_MINUTO_POR_IP = 10     # Rate limiting
UPLOADS_POR_HORA_POR_USUARIO = 50  # Rate limiting por usuario

# Padroes perigosos para bloquear
PADROES_PERIGOSOS = [
    b'<script',           # JavaScript embarcado
    b'<?php',             # PHP embarcado
    b'<%',                # ASP embarcado
    b'#!/',               # Shebang (scripts)
    b'MZ',                # Executavel Windows (PE)
    b'\x7fELF',           # Executavel Linux (ELF)
    b'PK\x03\x04',        # ZIP (verificar se e Office legitimo)
]

# Extensoes NUNCA permitidas (lista negra absoluta)
EXTENSOES_BLOQUEADAS = {
    '.exe', '.bat', '.cmd', '.com', '.msi', '.scr',  # Executaveis Windows
    '.sh', '.bash', '.zsh',                           # Scripts Unix
    '.php', '.asp', '.aspx', '.jsp', '.cgi',         # Scripts web
    '.js', '.vbs', '.ps1', '.psm1',                   # Scripts
    '.dll', '.so', '.dylib',                          # Bibliotecas
    '.jar', '.war', '.ear',                           # Java
    '.py', '.pyc', '.pyo', '.rb',                     # Python/Ruby
    '.html', '.htm', '.svg',                          # Podem conter XSS
    '.iso', '.img', '.dmg',                           # Imagens de disco
}


# ============================================
# FUNCOES DE VALIDACAO
# ============================================

def identificar_tipo_arquivo(extensao: str) -> Optional[TipoArquivo]:
    """Identifica o tipo de arquivo pela extensao."""
    ext = extensao.lower()
    for tipo, config in POLITICA_ARQUIVOS.items():
        if ext in config.extensoes:
            return tipo
    return None


def validar_extensao(filename: str) -> Tuple[bool, str, Optional[TipoArquivo]]:
    """
    Valida a extensao do arquivo.
    Retorna (valido, mensagem, tipo_arquivo).
    """
    if not filename:
        return False, "Nome do arquivo nao fornecido", None

    # Sanitiza e extrai extensao
    filename = os.path.basename(filename)
    ext = os.path.splitext(filename)[1].lower()

    if not ext:
        return False, "Arquivo sem extensao", None

    # Verifica lista negra primeiro
    if ext in EXTENSOES_BLOQUEADAS:
        logger.warning(f"Tentativa de upload de arquivo bloqueado: {filename}")
        return False, f"Tipo de arquivo nao permitido: {ext}", None

    # Identifica tipo
    tipo = identificar_tipo_arquivo(ext)

    if tipo:
        return True, "", tipo

    # Verifica documentos internos
    for categoria, config in POLITICA_DOCUMENTOS_INTERNOS.items():
        if ext in config.extensoes:
            return True, "", None  # Aceito mas sem tipo PJe

    # Extensao desconhecida
    extensoes_permitidas = set()
    for config in POLITICA_ARQUIVOS.values():
        extensoes_permitidas.update(config.extensoes)
    for config in POLITICA_DOCUMENTOS_INTERNOS.values():
        extensoes_permitidas.update(config.extensoes)

    return False, f"Extensao nao permitida. Aceitos: {', '.join(sorted(extensoes_permitidas))}", None


def validar_tamanho(
    tamanho_bytes: int,
    tipo: Optional[TipoArquivo] = None,
    extensao: str = ""
) -> Tuple[bool, str]:
    """
    Valida o tamanho do arquivo.
    Retorna (valido, mensagem).
    """
    if tamanho_bytes <= 0:
        return False, "Arquivo vazio ou tamanho invalido"

    tamanho_mb = tamanho_bytes / (1024 * 1024)

    # Limite absoluto
    if tamanho_mb > TAMANHO_MAXIMO_ABSOLUTO_MB:
        return False, f"Arquivo excede limite absoluto de {TAMANHO_MAXIMO_ABSOLUTO_MB}MB"

    # Limite por tipo PJe
    if tipo and tipo in POLITICA_ARQUIVOS:
        limite = POLITICA_ARQUIVOS[tipo].tamanho_max_mb
        if tamanho_mb > limite:
            return False, f"Arquivo {tipo.value} excede limite de {limite}MB (PJe)"

    # Limite para documentos internos
    ext = extensao.lower()
    for categoria, config in POLITICA_DOCUMENTOS_INTERNOS.items():
        if ext in config.extensoes:
            if tamanho_mb > config.tamanho_max_mb:
                return False, f"Arquivo excede limite de {config.tamanho_max_mb}MB"
            break

    return True, ""


def validar_magic_bytes(conteudo: bytes, extensao: str) -> Tuple[bool, str]:
    """
    Valida o tipo real do arquivo verificando magic bytes.
    Isso impede arquivos maliciosos com extensao falsa.
    Retorna (valido, mensagem).
    """
    if not conteudo or len(conteudo) < 8:
        return False, "Arquivo muito pequeno ou vazio"

    ext = extensao.lower()
    header = conteudo[:1024]  # Primeiros 1024 bytes

    # Verifica padroes perigosos em TODOS os arquivos
    for padrao in PADROES_PERIGOSOS:
        if padrao in header:
            # Excecao: ZIP e valido para Office (docx, xlsx, etc)
            if padrao == b'PK\x03\x04' and ext in {'.docx', '.xlsx', '.odt', '.ods'}:
                continue
            logger.warning(f"Padrao perigoso detectado em arquivo {ext}: {padrao[:10]}")
            return False, "Arquivo contem conteudo potencialmente perigoso"

    # Busca configuracao para a extensao
    config = None
    tipo = identificar_tipo_arquivo(ext)
    if tipo:
        config = POLITICA_ARQUIVOS[tipo]
    else:
        for cat_config in POLITICA_DOCUMENTOS_INTERNOS.values():
            if ext in cat_config.extensoes:
                config = cat_config
                break

    if not config:
        return True, ""  # Sem config especifica, aceita

    # Valida magic bytes
    magic_valido = False
    for magic, offset in config.magic_bytes:
        if conteudo[offset:offset + len(magic)] == magic:
            magic_valido = True
            break

    # Tratamento especial para PDF (pode estar em qualquer posicao nos primeiros 1024 bytes)
    if ext == '.pdf' and not magic_valido:
        if b'%PDF' in header:
            magic_valido = True

    # Tratamento especial para MP3 (varios formatos)
    if ext == '.mp3' and not magic_valido:
        if header[:3] == b'ID3' or header[:2] in [b'\xff\xfb', b'\xff\xfa', b'\xff\xf3']:
            magic_valido = True

    if not magic_valido:
        logger.warning(f"Magic bytes invalidos para {ext}")
        return False, f"Arquivo {ext.upper()[1:]} invalido ou corrompido"

    return True, ""


def validar_nome_arquivo(filename: str) -> Tuple[bool, str]:
    """
    Valida o nome do arquivo para prevenir path traversal e caracteres perigosos.
    Retorna (valido, mensagem).
    """
    if not filename:
        return False, "Nome do arquivo nao fornecido"

    # Caracteres/padroes perigosos
    padroes_perigosos = [
        '..',           # Path traversal
        '/',            # Separador Unix
        '\\',           # Separador Windows
        '\x00',         # Null byte
        '\n', '\r',     # Newlines
        '%00',          # Null byte encoded
        '%2e%2e',       # .. encoded
        '..%c0%af',     # Unicode path traversal
    ]

    filename_lower = filename.lower()
    for padrao in padroes_perigosos:
        if padrao in filename_lower:
            logger.warning(f"Padrao perigoso no nome: {filename}")
            return False, "Nome do arquivo contem caracteres invalidos"

    # Tamanho maximo do nome
    if len(filename) > 255:
        return False, "Nome do arquivo muito longo (max 255 caracteres)"

    # Verifica se comeca com ponto (arquivo oculto)
    basename = os.path.basename(filename)
    if basename.startswith('.') and basename != '.pdf':
        return False, "Nome do arquivo nao pode comecar com ponto"

    return True, ""


def sanitizar_nome_arquivo(filename: str) -> str:
    """
    Sanitiza o nome do arquivo para armazenamento seguro.
    Remove caracteres especiais e normaliza.
    """
    # Remove path
    filename = os.path.basename(filename)

    # Separa nome e extensao
    nome, ext = os.path.splitext(filename)

    # Remove caracteres especiais do nome (mantem apenas alfanumericos, hifen, underscore)
    nome = re.sub(r'[^\w\-]', '_', nome, flags=re.UNICODE)

    # Remove underscores multiplos
    nome = re.sub(r'_+', '_', nome)

    # Remove underscores no inicio/fim
    nome = nome.strip('_')

    # Se nome ficou vazio, usa timestamp
    if not nome:
        nome = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Limita tamanho
    if len(nome) > 200:
        nome = nome[:200]

    return f"{nome}{ext.lower()}"


def calcular_hash_arquivo(conteudo: bytes) -> str:
    """Calcula hash SHA-256 do arquivo para deduplicacao e integridade."""
    return hashlib.sha256(conteudo).hexdigest()


# ============================================
# FUNCAO PRINCIPAL DE VALIDACAO
# ============================================

def validar_upload_completo(
    filename: str,
    conteudo: bytes,
    content_type: str = "",
    verificar_pje: bool = True
) -> Tuple[bool, str, Dict]:
    """
    Validacao completa de upload de arquivo.

    Args:
        filename: Nome original do arquivo
        conteudo: Conteudo em bytes do arquivo
        content_type: MIME type informado no header (nao confiavel)
        verificar_pje: Se True, valida compatibilidade com PJe

    Returns:
        Tuple[bool, str, Dict]: (valido, mensagem_erro, metadados)

    Metadados retornados:
        - nome_sanitizado: Nome seguro para armazenamento
        - tipo: TipoArquivo ou None
        - extensao: Extensao do arquivo
        - tamanho_bytes: Tamanho em bytes
        - tamanho_mb: Tamanho em MB
        - hash_sha256: Hash do conteudo
        - pje_compativel: Se pode ser enviado ao PJe
    """
    metadados = {
        "nome_original": filename,
        "nome_sanitizado": None,
        "tipo": None,
        "extensao": None,
        "tamanho_bytes": len(conteudo) if conteudo else 0,
        "tamanho_mb": round(len(conteudo) / (1024 * 1024), 2) if conteudo else 0,
        "hash_sha256": None,
        "pje_compativel": False,
        "content_type_informado": content_type,
    }

    # 1. Validar nome do arquivo
    valido, msg = validar_nome_arquivo(filename)
    if not valido:
        return False, msg, metadados

    # 2. Validar extensao
    valido, msg, tipo = validar_extensao(filename)
    if not valido:
        return False, msg, metadados

    ext = os.path.splitext(filename)[1].lower()
    metadados["extensao"] = ext
    metadados["tipo"] = tipo.value if tipo else None

    # 3. Validar tamanho
    valido, msg = validar_tamanho(len(conteudo), tipo, ext)
    if not valido:
        return False, msg, metadados

    # 4. Validar magic bytes (tipo real do arquivo)
    valido, msg = validar_magic_bytes(conteudo, ext)
    if not valido:
        return False, msg, metadados

    # 5. Gerar nome sanitizado e hash
    metadados["nome_sanitizado"] = sanitizar_nome_arquivo(filename)
    metadados["hash_sha256"] = calcular_hash_arquivo(conteudo)

    # 6. Verificar compatibilidade com PJe
    if tipo and tipo in POLITICA_ARQUIVOS:
        metadados["pje_compativel"] = POLITICA_ARQUIVOS[tipo].pje_compativel

    # 7. Log de auditoria
    logger.info(
        f"Upload validado: {metadados['nome_sanitizado']} | "
        f"Tipo: {metadados['tipo']} | "
        f"Tamanho: {metadados['tamanho_mb']}MB | "
        f"PJe: {metadados['pje_compativel']}"
    )

    return True, "", metadados


# ============================================
# FUNCOES AUXILIARES
# ============================================

def obter_extensoes_permitidas_pje() -> set:
    """Retorna conjunto de extensoes compativeis com PJe."""
    extensoes = set()
    for config in POLITICA_ARQUIVOS.values():
        if config.pje_compativel:
            extensoes.update(config.extensoes)
    return extensoes


def obter_limites_tamanho() -> Dict[str, float]:
    """Retorna dicionario com limites de tamanho por tipo."""
    limites = {}
    for tipo, config in POLITICA_ARQUIVOS.items():
        limites[tipo.value] = config.tamanho_max_mb
    return limites


def arquivo_precisa_conversao_pje(extensao: str) -> bool:
    """Verifica se o arquivo precisa ser convertido para PDF antes de enviar ao PJe."""
    ext = extensao.lower()
    # Documentos Office precisam ser convertidos
    for config in POLITICA_DOCUMENTOS_INTERNOS.values():
        if ext in config.extensoes:
            return True
    return False


def gerar_nome_unico(filename: str, prefixo: str = "") -> str:
    """Gera nome unico para evitar colisoes no storage."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    nome_sanitizado = sanitizar_nome_arquivo(filename)
    nome, ext = os.path.splitext(nome_sanitizado)

    if prefixo:
        return f"{prefixo}_{timestamp}_{nome}{ext}"
    return f"{timestamp}_{nome}{ext}"


# ============================================
# DOCUMENTACAO DA POLITICA
# ============================================

POLITICA_DOCUMENTACAO = """
================================================================================
POLITICA DE UPLOAD DE ARQUIVOS - VAUCHER E ALVARES ADVOCACIA
================================================================================

1. FORMATOS ACEITOS PARA PJE (PROTOCOLO JUDICIAL)
-------------------------------------------------
| Tipo      | Extensoes      | Tamanho Max | Observacao                    |
|-----------|----------------|-------------|-------------------------------|
| Documento | .pdf           | 10 MB       | Formato padrao do PJe         |
| Imagem    | .png, .jpg     | 5 MB        | Para anexos e provas          |
| Audio     | .mp3, .ogg     | 20 MB       | Audiencias e depoimentos      |
| Video     | .mp4           | 30 MB       | Provas audiovisuais           |

2. FORMATOS ACEITOS PARA USO INTERNO (NAO VAO PARA PJE)
-------------------------------------------------------
| Tipo      | Extensoes                    | Tamanho Max |
|-----------|------------------------------|-------------|
| Office    | .doc, .docx, .xls, .xlsx     | 15 MB       |
|           | .odt, .ods                   |             |

3. FORMATOS BLOQUEADOS (NUNCA ACEITOS)
--------------------------------------
- Executaveis: .exe, .bat, .cmd, .com, .msi, .scr
- Scripts: .php, .asp, .js, .vbs, .ps1, .py, .sh
- Bibliotecas: .dll, .so, .dylib
- Imagens de disco: .iso, .img, .dmg
- Arquivos web: .html, .htm, .svg (risco XSS)

4. VALIDACOES DE SEGURANCA
--------------------------
a) Extensao do arquivo (whitelist)
b) Tamanho por tipo de arquivo
c) Magic bytes (verifica tipo real, nao apenas extensao)
d) Padroes perigosos no conteudo (scripts embarcados)
e) Sanitizacao do nome do arquivo
f) Hash SHA-256 para integridade/deduplicacao

5. RECOMENDACOES PARA CLIENTES
------------------------------
- Converta documentos Word/Excel para PDF antes de enviar
- Comprima imagens grandes antes do upload
- Videos longos devem ser divididos em partes de ate 30MB
- Nomeie arquivos de forma descritiva (ex: "contrato_trabalho_joao.pdf")

6. LIMITES DE TAXA (RATE LIMITING)
----------------------------------
- Maximo 10 uploads por minuto por IP
- Maximo 50 uploads por hora por usuario
- Tamanho maximo absoluto: 50 MB por arquivo

================================================================================
Atualizado em: 08/02/2026
Baseado em: Resolucao CNJ n. 185/2013, Manual PJe CNJ
================================================================================
"""


def obter_documentacao_politica() -> str:
    """Retorna a documentacao da politica de uploads."""
    return POLITICA_DOCUMENTACAO
