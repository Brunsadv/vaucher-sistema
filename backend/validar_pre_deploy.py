# -*- coding: utf-8 -*-
"""
Validacao Pre-Deploy - Sistema Vaucher e Alvares
Execute antes de fazer push para verificar consistencia do sistema.
"""

import os
import sys
import re
import ast
from pathlib import Path

# Cores para output
class Cores:
    OK = '\033[92m'
    ERRO = '\033[91m'
    AVISO = '\033[93m'
    INFO = '\033[94m'
    RESET = '\033[0m'

def ok(msg):
    print(f"  {Cores.OK}[OK]{Cores.RESET} {msg}")

def erro(msg):
    print(f"  {Cores.ERRO}[ERRO]{Cores.RESET} {msg}")

def aviso(msg):
    print(f"  {Cores.AVISO}[AVISO]{Cores.RESET} {msg}")

def info(msg):
    print(f"  {Cores.INFO}[INFO]{Cores.RESET} {msg}")

# Contadores
erros = 0
avisos = 0

def contar_erro():
    global erros
    erros += 1

def contar_aviso():
    global avisos
    avisos += 1

# ============================================
# VERIFICACOES
# ============================================

def verificar_sintaxe():
    """Verifica sintaxe de todos os arquivos Python."""
    print("\n1. VERIFICANDO SINTAXE PYTHON")
    print("-" * 50)

    arquivos_py = list(Path(".").rglob("*.py"))
    arquivos_py = [f for f in arquivos_py if "__pycache__" not in str(f)]

    for arquivo in arquivos_py:
        try:
            with open(arquivo, "r", encoding="utf-8") as f:
                source = f.read()
            ast.parse(source)
            ok(f"{arquivo}")
        except SyntaxError as e:
            erro(f"{arquivo}: Linha {e.lineno} - {e.msg}")
            contar_erro()

def verificar_imports():
    """Verifica se todos os imports sao validos."""
    print("\n2. VERIFICANDO IMPORTS")
    print("-" * 50)

    # Funcoes criticas que devem estar importadas onde sao usadas
    funcoes_criticas = {
        "buscar_cadastro": ["main.py", "routes/admin_cadastros.py", "routes/portal_cliente.py"],
        "salvar_cadastro": ["main.py", "routes/admin_cadastros.py"],
        "verificar_admin": ["routes/admin_cadastros.py", "routes/admin_processos.py"],
        "verificar_token_cliente": ["main.py", "routes/portal_cliente.py"],
        "listar_documentos_admin": ["main.py", "routes/admin_cadastros.py"],
        "criar_documento_admin": ["routes/admin_cadastros.py"],
        "buscar_cliente_auth": ["main.py"],
    }

    for funcao, arquivos in funcoes_criticas.items():
        for arquivo in arquivos:
            if os.path.exists(arquivo):
                with open(arquivo, "r", encoding="utf-8") as f:
                    conteudo = f.read()

                # Verificar se a funcao e usada (nao em comentarios)
                linhas_uso = [l for l in conteudo.split('\n')
                              if re.search(rf'\b{funcao}\s*\(', l) and not l.strip().startswith('#')]

                if linhas_uso:
                    # Verificar se esta importada (busca mais flexivel para imports multi-linha)
                    # Busca o nome da funcao em qualquer import
                    importado = (
                        f'import {funcao}' in conteudo or
                        f', {funcao}' in conteudo or
                        f'{funcao},' in conteudo or
                        f'    {funcao},' in conteudo or
                        f'    {funcao}\n' in conteudo or
                        re.search(rf'def\s+{funcao}\s*\(', conteudo)
                    )

                    if importado:
                        ok(f"{funcao} em {arquivo}")
                    else:
                        erro(f"{funcao} usada mas NAO importada em {arquivo}")
                        contar_erro()

def verificar_caminhos_documentos():
    """Verifica consistencia de caminhos de documentos."""
    print("\n3. VERIFICANDO CAMINHOS DE DOCUMENTOS")
    print("-" * 50)

    # Padroes problematicos (caminhos hardcoded ou inconsistentes)
    # NOTA: Ignoramos linhas em contexto de fallback (dentro de listas de caminhos alternativos)
    padroes_problematicos = [
        (r'uploads/\{?cadastro_id\}?/assinados', "Caminho legado de assinados"),
        (r'f["\']/app/uploads/', "Caminho hardcoded /app/uploads"),
    ]

    palavras_ignorar = ["fallback", "alternativ", "legado", "antigo", "caminhos_alternativos"]

    arquivos_verificar = ["main.py", "routes/admin_cadastros.py", "routes/portal_cliente.py"]
    problemas_encontrados = 0

    for arquivo in arquivos_verificar:
        if os.path.exists(arquivo):
            with open(arquivo, "r", encoding="utf-8") as f:
                conteudo = f.read()
                linhas = conteudo.split("\n")

            em_bloco_fallback = False
            for i, linha in enumerate(linhas, 1):
                linha_lower = linha.lower()

                # Detectar inicio de bloco de fallback
                if "caminhos_alternativos" in linha_lower or "fallback" in linha_lower:
                    em_bloco_fallback = True
                    continue

                # Detectar fim de bloco (linha sem indentacao ou nova funcao)
                if em_bloco_fallback and (linha.strip() and not linha.startswith(" ") and not linha.startswith("\t")):
                    em_bloco_fallback = False

                # Ignorar se estiver em bloco de fallback
                if em_bloco_fallback:
                    continue

                # Ignorar comentarios
                if linha.strip().startswith("#"):
                    continue

                # Ignorar linhas com palavras de contexto
                if any(p in linha_lower for p in palavras_ignorar):
                    continue

                for padrao, msg in padroes_problematicos:
                    if re.search(padrao, linha):
                        aviso(f"{arquivo}:{i} - {msg}")
                        contar_aviso()
                        problemas_encontrados += 1

    if problemas_encontrados == 0:
        ok("Caminhos de documentos consistentes")

def verificar_endpoints_duplicados():
    """Verifica se ha endpoints duplicados."""
    print("\n4. VERIFICANDO ENDPOINTS DUPLICADOS")
    print("-" * 50)

    endpoints = {}
    padrao_endpoint = r'@(app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
    padrao_prefix = r'APIRouter\(prefix=["\']([^"\']+)["\']'

    arquivos = ["main.py"] + list(Path("routes").glob("*.py"))

    for arquivo in arquivos:
        if os.path.exists(arquivo):
            with open(arquivo, "r", encoding="utf-8") as f:
                conteudo = f.read()

            # Encontrar prefixo do router (se houver)
            prefix_match = re.search(padrao_prefix, conteudo)
            prefix = prefix_match.group(1) if prefix_match else ""

            matches = re.findall(padrao_endpoint, conteudo)
            for obj, metodo, path in matches:
                # Se for router, adicionar prefixo
                full_path = prefix + path if obj == "router" else path
                chave = f"{metodo.upper()} {full_path}"

                if chave in endpoints:
                    erro(f"Endpoint duplicado: {chave}")
                    erro(f"  - {endpoints[chave]}")
                    erro(f"  - {arquivo}")
                    contar_erro()
                else:
                    endpoints[chave] = str(arquivo)

    total_endpoints = len(endpoints)
    info(f"{total_endpoints} endpoints verificados")
    if erros == 0:
        ok("Nenhum endpoint duplicado")

def verificar_schema_banco():
    """Verifica se as migracoes estao implementadas."""
    print("\n5. VERIFICANDO MIGRACOES DO BANCO")
    print("-" * 50)

    arquivo_db = "modules/database.py"
    if not os.path.exists(arquivo_db):
        erro("modules/database.py nao encontrado")
        contar_erro()
        return

    with open(arquivo_db, "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Verificar se ha CREATE TABLE para tabelas principais
    tabelas_requeridas = [
        "cadastros",
        "usuarios",
        "clientes_auth",
        "documentos_admin",
        "documentos_extras",
        "documentos_demanda",
    ]

    for tabela in tabelas_requeridas:
        if f"CREATE TABLE IF NOT EXISTS {tabela}" in conteudo:
            ok(f"Tabela {tabela} definida")
        else:
            erro(f"Tabela {tabela} NAO definida")
            contar_erro()

def verificar_variaveis_ambiente():
    """Verifica se variaveis de ambiente estao sendo usadas."""
    print("\n6. VERIFICANDO VARIAVEIS DE AMBIENTE")
    print("-" * 50)

    # Variaveis e onde devem estar configuradas
    variaveis_requeridas = [
        ("DATABASE_URL", [os.path.join("modules", "config.py")]),
        ("RESEND_API_KEY", [os.path.join("modules", "config.py")]),
        ("ZAPSIGN_API_TOKEN", [os.path.join("modules", "assinatura.py")]),
    ]

    for var, arquivos in variaveis_requeridas:
        encontrada = False
        for arquivo in arquivos:
            if os.path.exists(arquivo):
                with open(arquivo, "r", encoding="utf-8") as f:
                    conteudo = f.read()
                # Buscar os.getenv("VAR") ou os.getenv("VAR", default)
                if f'os.getenv("{var}"' in conteudo or f"os.getenv('{var}'" in conteudo:
                    encontrada = True
                    break

        if encontrada:
            ok(f"{var} configurada")
        else:
            aviso(f"{var} pode nao estar configurada corretamente")
            contar_aviso()

def verificar_testes():
    """Executa os testes basicos."""
    print("\n7. EXECUTANDO TESTES")
    print("-" * 50)

    if not os.path.exists("test_backend.py"):
        aviso("test_backend.py nao encontrado")
        contar_aviso()
        return

    import subprocess
    resultado = subprocess.run(
        [sys.executable, "test_backend.py"],
        capture_output=True,
        text=True
    )

    if resultado.returncode == 0:
        ok("Todos os testes passaram")
    else:
        erro("Alguns testes falharam")
        print(resultado.stdout)
        contar_erro()

def verificar_guia_tecnico():
    """Verifica se o guia tecnico existe."""
    print("\n8. VERIFICANDO DOCUMENTACAO")
    print("-" * 50)

    if os.path.exists("CLAUDE_GUIA_TECNICO.md"):
        ok("CLAUDE_GUIA_TECNICO.md existe")
    else:
        aviso("CLAUDE_GUIA_TECNICO.md nao encontrado - criar documentacao!")
        contar_aviso()

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print("   VALIDACAO PRE-DEPLOY - SISTEMA VAUCHER E ALVARES")
    print("=" * 60)

    verificar_sintaxe()
    verificar_imports()
    verificar_caminhos_documentos()
    verificar_endpoints_duplicados()
    verificar_schema_banco()
    verificar_variaveis_ambiente()
    verificar_testes()
    verificar_guia_tecnico()

    print("\n" + "=" * 60)
    print("   RESULTADO")
    print("=" * 60)

    if erros > 0:
        print(f"\n  {Cores.ERRO}FALHOU{Cores.RESET}: {erros} erro(s), {avisos} aviso(s)")
        print(f"\n  {Cores.ERRO}NAO FACA DEPLOY ate corrigir os erros!{Cores.RESET}")
        sys.exit(1)
    elif avisos > 0:
        print(f"\n  {Cores.AVISO}PASSOU COM AVISOS{Cores.RESET}: {avisos} aviso(s)")
        print(f"\n  Verifique os avisos antes de fazer deploy.")
        sys.exit(0)
    else:
        print(f"\n  {Cores.OK}PASSOU{Cores.RESET}: Sistema pronto para deploy!")
        sys.exit(0)

if __name__ == "__main__":
    main()
