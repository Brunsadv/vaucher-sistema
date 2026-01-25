# -*- coding: utf-8 -*-
"""
Teste do Backend - Validacao pos-refatoracao
"""
from fastapi.testclient import TestClient
import sys

# Suprimir logs durante os testes
import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("modules.config").setLevel(logging.WARNING)

from main import app

client = TestClient(app, raise_server_exceptions=False)

resultados = {'ok': 0, 'falha': 0, 'detalhes': []}

def testar(metodo, path, esperado):
    if metodo == 'GET':
        r = client.get(path)
    elif metodo == 'POST':
        r = client.post(path, json={})
    elif metodo == 'DELETE':
        r = client.delete(path)
    else:
        r = client.put(path, json={})

    ok = r.status_code in esperado if isinstance(esperado, list) else r.status_code == esperado
    status = 'OK' if ok else 'FALHA'

    if ok:
        resultados['ok'] += 1
    else:
        resultados['falha'] += 1
        resultados['detalhes'].append(f'{metodo} {path}: esperado {esperado}, recebido {r.status_code}')

    print(f'  {metodo:6} {path:50} {r.status_code:3} [{status}]')
    return ok

print('=' * 70)
print('   TESTE COMPLETO DO BACKEND')
print('=' * 70)
print('')

# 1. ADMIN CADASTROS (routes/admin_cadastros.py)
print('1. ADMIN CADASTROS (novo modulo)')
print('-' * 70)
testar('GET', '/api/admin/clientes/test/acesso', 401)
testar('POST', '/api/admin/clientes/test/habilitar-acesso', 401)
testar('POST', '/api/admin/clientes/test/desabilitar-acesso', 401)
testar('GET', '/api/admin/clientes/test/processo', 401)
testar('GET', '/api/admin/clientes/test/documentos-enviados', 401)
testar('GET', '/api/admin/clientes/test/documentos-extras', 401)
testar('DELETE', '/api/admin/documentos/1', 401)
testar('DELETE', '/api/admin/documentos-extras/1', 401)
print('')

# 2. PORTAL CLIENTE (routes/portal_cliente.py)
print('2. PORTAL CLIENTE (novo modulo)')
print('-' * 70)
testar('GET', '/api/cliente/meus-dados', 401)
testar('GET', '/api/cliente/meus-processos', 401)
testar('GET', '/api/cliente/meus-contratos', 401)
testar('GET', '/api/cliente/mensagens', 401)
testar('GET', '/api/cliente/mensagens/nao-lidas', 401)
testar('GET', '/api/cliente/meus-documentos-extras', 401)
testar('GET', '/api/cliente/andamentos', 401)
print('')

# 3. ADMIN PROCESSOS (routes/admin_processos.py)
print('3. ADMIN PROCESSOS (modulo existente)')
print('-' * 70)
testar('GET', '/api/admin/clientes/test/processos', 401)
testar('GET', '/api/admin/processos/1', 401)
testar('GET', '/api/admin/clientes/test/contratos', 401)
testar('GET', '/api/admin/contratos/1', 401)
testar('GET', '/api/admin/comprovantes/pendentes', 401)
testar('GET', '/api/admin/clientes/test/mensagens', 401)
testar('GET', '/api/admin/mensagens/nao-lidas', 401)
print('')

# 4. BANNERS (routes/banners.py)
print('4. BANNERS')
print('-' * 70)
testar('GET', '/api/admin/banners', 401)
testar('GET', '/api/cliente/banners', 401)
print('')

# 5. PRAZOS (routes/prazos.py) - prefix /api/admin
print('5. PRAZOS')
print('-' * 70)
testar('GET', '/api/admin/prazos', 401)
testar('GET', '/api/admin/prazos/pendentes', 401)
print('')

# 6. AUTH (routes/auth.py)
print('6. AUTH')
print('-' * 70)
testar('GET', '/api/usuarios', 401)
# Login com credenciais invalidas retorna 200 com success: false
r = client.post('/api/login', json={'email': 'x@x.com', 'senha': 'x'})
status = 'OK' if r.status_code == 200 else 'FALHA'
if r.status_code == 200:
    resultados['ok'] += 1
else:
    resultados['falha'] += 1
    resultados['detalhes'].append(f'POST /api/login: esperado 200, recebido {r.status_code}')
print(f'  POST   /api/login                                         {r.status_code:3} [{status}]')
print('')

# 7. MAIN.PY (endpoints restantes)
print('7. MAIN.PY (endpoints restantes)')
print('-' * 70)
testar('GET', '/api/cadastros', [200, 401])  # Pode nao ter auth
testar('GET', '/', 200)  # Root endpoint
print('')

# RESUMO
print('=' * 70)
print('   RESUMO')
print('=' * 70)
print(f'  Testes OK:    {resultados["ok"]}')
print(f'  Testes FALHA: {resultados["falha"]}')
print('')

if resultados['falha'] == 0:
    print('  >>> TODOS OS TESTES PASSARAM! <<<')
else:
    print('  >>> ALGUNS TESTES FALHARAM <<<')
    for d in resultados['detalhes']:
        print(f'      - {d}')
    sys.exit(1)
