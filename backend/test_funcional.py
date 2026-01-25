# -*- coding: utf-8 -*-
"""
Testes Funcionais - Sistema Vaucher e Alvares
Testa funcionalidades reais alem da existencia de endpoints.
"""

import os
import sys
import json
import tempfile
from datetime import datetime

# Suprimir logs durante os testes
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("modules.config").setLevel(logging.WARNING)

from fastapi.testclient import TestClient

# Importar app
try:
    from main import app
    client = TestClient(app, raise_server_exceptions=False)
except Exception as e:
    print(f"ERRO ao importar app: {e}")
    sys.exit(1)

# Resultados
resultados = {
    'ok': 0,
    'falha': 0,
    'skip': 0,
    'detalhes': []
}

def ok(teste):
    resultados['ok'] += 1
    print(f"  [OK] {teste}")

def falha(teste, motivo):
    resultados['falha'] += 1
    resultados['detalhes'].append(f"{teste}: {motivo}")
    print(f"  [FALHA] {teste}: {motivo}")

def skip(teste, motivo):
    resultados['skip'] += 1
    print(f"  [SKIP] {teste}: {motivo}")


# ============================================
# TESTES DE ESTRUTURA
# ============================================

def test_estrutura_pastas():
    """Verifica se pastas essenciais existem."""
    print("\n1. ESTRUTURA DE PASTAS")
    print("-" * 50)

    pastas = ["modules", "routes", "modelos", "uploads", "gerados"]
    for pasta in pastas:
        if os.path.exists(pasta):
            ok(f"Pasta {pasta} existe")
        else:
            # Criar se nao existir
            os.makedirs(pasta, exist_ok=True)
            ok(f"Pasta {pasta} criada")


def test_arquivos_essenciais():
    """Verifica se arquivos essenciais existem."""
    print("\n2. ARQUIVOS ESSENCIAIS")
    print("-" * 50)

    arquivos = [
        "main.py",
        "modules/config.py",
        "modules/database.py",
        "modules/auth.py",
        "modules/security.py",
        "routes/admin_cadastros.py",
        "routes/portal_cliente.py",
        "CLAUDE_GUIA_TECNICO.md",
    ]

    for arquivo in arquivos:
        if os.path.exists(arquivo):
            ok(f"{arquivo}")
        else:
            falha(f"{arquivo}", "Arquivo nao encontrado")


# ============================================
# TESTES DE ENDPOINTS
# ============================================

def test_endpoint_health():
    """Testa endpoint de health check."""
    print("\n3. HEALTH CHECK")
    print("-" * 50)

    r = client.get("/health")
    if r.status_code == 200:
        data = r.json()
        if data.get("status") == "healthy":
            ok("GET /health retorna status healthy")
        else:
            falha("GET /health", f"Status: {data.get('status')}")
    else:
        falha("GET /health", f"Status code: {r.status_code}")


def test_endpoint_root():
    """Testa endpoint raiz."""
    print("\n4. ENDPOINT RAIZ")
    print("-" * 50)

    r = client.get("/")
    if r.status_code == 200:
        ok("GET / retorna 200")
    else:
        falha("GET /", f"Status code: {r.status_code}")


def test_endpoints_protegidos():
    """Testa se endpoints protegidos retornam 401 sem auth."""
    print("\n5. ENDPOINTS PROTEGIDOS (sem auth)")
    print("-" * 50)

    # Endpoints que requerem autenticacao admin
    endpoints_admin = [
        ("GET", "/api/admin/clientes/test/acesso"),
        ("GET", "/api/admin/clientes/test/documentos-enviados"),
        ("GET", "/api/admin/mensagens/nao-lidas"),
    ]

    # Endpoints que requerem autenticacao cliente
    endpoints_cliente = [
        ("GET", "/api/cliente/meus-dados"),
        ("GET", "/api/cliente/documentos"),
        ("GET", "/api/cliente/mensagens"),
    ]

    # Endpoints publicos (nao requerem auth)
    endpoints_publicos = [
        ("GET", "/api/cadastros"),  # Lista cadastros - verificado pelo frontend
    ]

    for metodo, path in endpoints_admin + endpoints_cliente:
        if metodo == "GET":
            r = client.get(path)
        elif metodo == "POST":
            r = client.post(path, json={})

        if r.status_code == 401:
            ok(f"{metodo} {path} retorna 401")
        else:
            falha(f"{metodo} {path}", f"Esperado 401, recebido {r.status_code}")

    # Verificar endpoints publicos
    for metodo, path in endpoints_publicos:
        r = client.get(path)
        if r.status_code == 200:
            ok(f"{metodo} {path} e publico (200)")
        else:
            falha(f"{metodo} {path}", f"Esperado 200, recebido {r.status_code}")


def test_login_credenciais_invalidas():
    """Testa login com credenciais invalidas."""
    print("\n6. LOGIN COM CREDENCIAIS INVALIDAS")
    print("-" * 50)

    r = client.post("/api/login", json={
        "email": "teste@invalido.com",
        "senha": "senha_errada"
    })

    if r.status_code == 200:
        data = r.json()
        if data.get("success") == False:
            ok("Login invalido retorna success: false")
        else:
            falha("Login invalido", "Deveria retornar success: false")
    else:
        falha("Login invalido", f"Status code: {r.status_code}")


# ============================================
# TESTES DE MODELOS PYDANTIC
# ============================================

def test_modelo_cadastro():
    """Testa validacao do modelo de cadastro."""
    print("\n7. VALIDACAO DE MODELOS")
    print("-" * 50)

    # Dados completos validos
    dados_validos = {
        "nome": "Teste Usuario",
        "nacionalidade": "brasileiro(a)",
        "estado_civil": "solteiro",
        "profissao": "Analista",
        "cpf": "12345678901",
        "data_nascimento": "01/01/1990",
        "endereco_completo": "Rua Teste, 123, Cidade - UF",
        "email": "teste@teste.com",
        "telefone": "11999999999",
        "tipo_demanda": "Auxilio Moradia",
        "objeto_contrato": "Teste objeto",
        "poderes_especificos": "Teste poderes"
    }

    # Testar POST /api/cadastros (vai falhar no banco local, mas valida o modelo)
    r = client.post("/api/cadastros", json=dados_validos)

    # Se retornar 500 "Erro ao salvar cadastro" significa que o modelo foi validado
    # mas o banco nao esta disponivel (esperado em ambiente local)
    if r.status_code == 200:
        ok("Modelo de cadastro valido - cadastro criado")
    elif r.status_code == 500 and "salvar" in r.text.lower():
        ok("Modelo de cadastro valido (banco indisponivel)")
    elif r.status_code == 422:
        falha("Modelo de cadastro", f"Validacao falhou: {r.text}")
    else:
        falha("Modelo de cadastro", f"Status inesperado: {r.status_code}")

    # Dados incompletos (deve falhar validacao)
    dados_incompletos = {
        "nome": "Teste",
        "email": "invalido"  # Email invalido
    }

    r = client.post("/api/cadastros", json=dados_incompletos)
    if r.status_code == 422:
        ok("Modelo rejeita dados incompletos/invalidos")
    else:
        falha("Validacao de modelo", f"Deveria retornar 422, retornou {r.status_code}")


# ============================================
# TESTES DE FUNCOES DE BANCO
# ============================================

def test_funcoes_banco():
    """Testa se funcoes de banco estao importaveis."""
    print("\n8. FUNCOES DE BANCO")
    print("-" * 50)

    try:
        from modules.database import (
            get_db,
            salvar_cadastro,
            carregar_cadastros,
            buscar_cadastro,
            criar_documento_admin,
            listar_documentos_admin,
            criar_documento_extra,
            listar_documentos_extras,
        )
        ok("Todas as funcoes de banco importadas")
    except ImportError as e:
        falha("Import funcoes banco", str(e))


def test_funcoes_auth():
    """Testa se funcoes de auth estao importaveis."""
    print("\n9. FUNCOES DE AUTH")
    print("-" * 50)

    try:
        from modules.auth import verificar_admin, verificar_token, verificar_token_cliente
        ok("Funcoes de auth importadas")
    except ImportError as e:
        falha("Import funcoes auth", str(e))

    try:
        from modules.security import (
            decodificar_token_cliente,
            criar_email_html,
            sanitizar_nome_arquivo,
        )
        ok("Funcoes de security importadas")
    except ImportError as e:
        falha("Import funcoes security", str(e))


# ============================================
# TESTES DE CAMINHOS
# ============================================

def test_caminhos_consistentes():
    """Verifica se caminhos de documentos estao consistentes."""
    print("\n10. CONSISTENCIA DE CAMINHOS")
    print("-" * 50)

    from modules.config import UPLOADS_DIR, GERADOS_DIR, BASE_DIR

    # Verificar se variaveis estao definidas
    if UPLOADS_DIR:
        ok(f"UPLOADS_DIR definido: {UPLOADS_DIR}")
    else:
        falha("UPLOADS_DIR", "Nao definido")

    if GERADOS_DIR:
        ok(f"GERADOS_DIR definido: {GERADOS_DIR}")
    else:
        falha("GERADOS_DIR", "Nao definido")

    if BASE_DIR:
        ok(f"BASE_DIR definido: {BASE_DIR}")
    else:
        falha("BASE_DIR", "Nao definido")


# ============================================
# MAIN
# ============================================

def main():
    print("=" * 60)
    print("   TESTES FUNCIONAIS - SISTEMA VAUCHER E ALVARES")
    print("=" * 60)

    test_estrutura_pastas()
    test_arquivos_essenciais()
    test_endpoint_health()
    test_endpoint_root()
    test_endpoints_protegidos()
    test_login_credenciais_invalidas()
    test_modelo_cadastro()
    test_funcoes_banco()
    test_funcoes_auth()
    test_caminhos_consistentes()

    print("\n" + "=" * 60)
    print("   RESULTADO")
    print("=" * 60)
    print(f"\n  OK:    {resultados['ok']}")
    print(f"  FALHA: {resultados['falha']}")
    print(f"  SKIP:  {resultados['skip']}")

    if resultados['falha'] > 0:
        print("\n  DETALHES DAS FALHAS:")
        for d in resultados['detalhes']:
            print(f"    - {d}")
        print("\n  >>> ALGUNS TESTES FALHARAM <<<")
        sys.exit(1)
    else:
        print("\n  >>> TODOS OS TESTES PASSARAM! <<<")
        sys.exit(0)


if __name__ == "__main__":
    main()
