"""
Backend - Vaucher & Álvares Sistema de Cadastro
FastAPI + PostgreSQL + Geração de Documentos + Resend para E-mail
Com gerenciamento de usuários no banco de dados
VERSÃO 3.0 - COM PORTAL DO CLIENTE
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import os
import json
import zipfile
import shutil
from datetime import datetime
import uuid
import hashlib
import logging
import httpx
import base64
import secrets
from io import BytesIO
from dateutil.relativedelta import relativedelta

# Configurar logging detalhado
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PostgreSQL
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================
# CONFIGURAÇÃO
# ============================================

app = FastAPI(
    title="Vaucher & Álvares - API",
    description="Sistema de cadastro de clientes e geração de documentos",
    version="3.0.0"
)

# CORS - permitir acesso dos frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "https://cadastro.vaucherealvares.com.br",
        "https://painel.vaucherealvares.com.br",
        "https://portal.vaucherealvares.com.br",
        "https://cadastro.vaucherealvares.com",
        "https://painel.vaucherealvares.com",
        "https://portal.vaucherealvares.com",
        "https://vaucher-cliente.vercel.app",
        "https://vaucher-admin.vercel.app",
        "https://vaucher-portal.vercel.app",
        "https://portal-cliente-five.vercel.app",
        "https://portal-cliente-git-main-brunsadvs-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELOS_DIR = os.path.join(BASE_DIR, "modelos")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
GERADOS_DIR = os.path.join(UPLOADS_DIR, "documentos_gerados")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Criar diretórios se não existirem
for dir_path in [MODELOS_DIR, UPLOADS_DIR, GERADOS_DIR, STATIC_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Servir arquivos estáticos (logo)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Banco de dados e E-mail
DATABASE_URL = os.getenv("DATABASE_URL")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")

# Senha inicial do admin (deve ser alterada após primeiro login)
ADMIN_INICIAL_SENHA = os.getenv("ADMIN_INICIAL_SENHA", "VaucherAdmin2024!")

# Chave secreta para tokens (em produção, usar variável de ambiente)
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "vaucher_alvares_secret_key_2024")

# URL da logo
LOGO_URL = "https://raw.githubusercontent.com/Brunsadv/vaucher-sistema/main/backend/static/Vaucher%20e%20Alvares-06.jpg"

# ============================================
# FUNÇÕES DE SEGURANÇA
# ============================================

def hash_senha(senha: str) -> str:
    """Cria hash da senha usando SHA-256 com salt."""
    salt = "vaucher_alvares_2024"
    return hashlib.sha256(f"{senha}{salt}".encode()).hexdigest()

def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """Verifica se a senha corresponde ao hash."""
    return hash_senha(senha) == hash_armazenado

def gerar_token(user_id: int, email: str, is_admin: bool) -> str:
    """Gera um token que contém informações do usuário."""
    payload = f"{user_id}:{email}:{is_admin}"
    signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
    token_data = base64.b64encode(f"{payload}:{signature}".encode()).decode()
    return token_data

def decodificar_token(token: str) -> dict:
    """Decodifica e valida um token."""
    try:
        decoded = base64.b64decode(token.encode()).decode()
        parts = decoded.rsplit(":", 1)
        if len(parts) != 2:
            return None
        
        payload, signature = parts
        
        expected_signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
        if signature != expected_signature:
            return None
        
        user_id, email, is_admin = payload.split(":")
        return {
            "id": int(user_id),
            "email": email,
            "is_admin": is_admin == "True"
        }
    except Exception:
        return None

def verificar_token(authorization: str = Header(None)) -> dict:
    """Verifica se o token é válido e retorna o usuário."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token não fornecido")
    
    token = authorization.replace("Bearer ", "")
    
    usuario = decodificar_token(token)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    
    usuario_db = buscar_usuario_por_email(usuario["email"])
    if not usuario_db or not usuario_db.get("ativo", True):
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")
    
    return {
        "id": usuario_db["id"],
        "email": usuario_db["email"],
        "nome": usuario_db["nome"],
        "is_admin": usuario_db["is_admin"]
    }

def verificar_admin(authorization: str = Header(None)) -> dict:
    """Verifica se o usuário é admin."""
    usuario = verificar_token(authorization)
    if not usuario.get("is_admin"):
        raise HTTPException(status_code=403, detail="Acesso negado. Apenas administradores.")
    return usuario

# ============================================
# TEMPLATE DE E-MAIL COM LOGO
# ============================================

def criar_email_html(conteudo: str) -> str:
    """Cria o HTML do e-mail com logo e rodapé padrão."""
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; background-color: #f5f5f5; margin: 0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <!-- Cabeçalho com Logo -->
            <div style="background-color: #ffffff; padding: 30px; text-align: center; border-bottom: 3px solid #8B1538;">
                <img src="{LOGO_URL}" alt="Vaucher & Álvares Advogados" style="max-width: 300px; height: auto;" />
            </div>
            
            <!-- Conteúdo -->
            <div style="padding: 30px;">
                {conteudo}
            </div>
            
            <!-- Rodapé -->
            <div style="background-color: #f8f8f8; padding: 20px; text-align: center; border-top: 1px solid #eee;">
                <p style="font-size: 12px; color: #666; margin: 0;">
                    <strong>Vaucher & Álvares Sociedade de Advogados</strong><br>
                    Rua Lima, nº 106, Jardim das Américas, Cuiabá-MT<br>
                    (65) 3023-5959 | atendimento@vaucherealvares.com
                </p>
            </div>
        </div>
    </body>
    </html>
    """

# ============================================
# BANCO DE DADOS
# ============================================

def get_db():
    """Conecta ao PostgreSQL."""
    if not DATABASE_URL:
        logger.error("DATABASE_URL não configurada!")
        return None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        logger.error(f"Erro ao conectar ao banco: {e}")
        return None

def init_db():
    """Cria as tabelas se não existirem."""
    conn = get_db()
    if not conn:
        logger.error("Não foi possível inicializar o banco de dados")
        return
    
    try:
        cur = conn.cursor()
        
        # Tabela de cadastros
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cadastros (
                id VARCHAR(20) PRIMARY KEY,
                data VARCHAR(20),
                data_hora TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pendente',
                dados JSONB,
                documentos JSONB DEFAULT '[]',
                arquivos_gerados JSONB DEFAULT '{}',
                documentos_assinados JSONB DEFAULT '[]',
                data_assinatura TIMESTAMP
            )
        """)
        
        # Adicionar colunas se não existirem (para bancos existentes)
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cadastros' AND column_name='documentos_assinados') THEN
                    ALTER TABLE cadastros ADD COLUMN documentos_assinados JSONB DEFAULT '[]';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cadastros' AND column_name='data_assinatura') THEN
                    ALTER TABLE cadastros ADD COLUMN data_assinatura TIMESTAMP;
                END IF;
            END $$;
        """)
        
        # Tabela de usuários
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                senha_hash VARCHAR(255) NOT NULL,
                nome VARCHAR(255) NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                ativo BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela financeiro - estrutura completa
        cur.execute("""
            CREATE TABLE IF NOT EXISTS financeiro (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                numero_processo VARCHAR(100),
                vara_tribunal VARCHAR(255),
                percentual_honorarios DECIMAL(5,2) DEFAULT 20,
                valor_credito_cliente DECIMAL(15,2) DEFAULT 0,
                depositos JSONB DEFAULT '[]',
                sucumbencias JSONB DEFAULT '[]',
                retencoes JSONB DEFAULT '[]',
                observacoes TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cadastro_id)
            )
        """)
        
        # Migrar tabela existente se necessário
        cur.execute("""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='financeiro' AND column_name='valor_credito_cliente') THEN
                    ALTER TABLE financeiro ADD COLUMN valor_credito_cliente DECIMAL(15,2) DEFAULT 0;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='financeiro' AND column_name='depositos') THEN
                    ALTER TABLE financeiro ADD COLUMN depositos JSONB DEFAULT '[]';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='financeiro' AND column_name='sucumbencias') THEN
                    ALTER TABLE financeiro ADD COLUMN sucumbencias JSONB DEFAULT '[]';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='financeiro' AND column_name='retencoes') THEN
                    ALTER TABLE financeiro ADD COLUMN retencoes JSONB DEFAULT '[]';
                END IF;
            END $$;
        """)
        
        # ========== PORTAL DO CLIENTE - NOVAS TABELAS ==========
        
        # Tabela de autenticação de clientes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS clientes_auth (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                senha_hash VARCHAR(255) NOT NULL,
                ativo BOOLEAN DEFAULT TRUE,
                primeiro_acesso BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_acesso TIMESTAMP,
                UNIQUE(cadastro_id)
            )
        """)
        
        # Tabela de informações do processo
        cur.execute("""
            CREATE TABLE IF NOT EXISTS processo_info (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                numero_processo VARCHAR(50),
                vara_tribunal VARCHAR(255),
                fase VARCHAR(50) DEFAULT 'Inicial',
                data_distribuicao DATE,
                valor_causa DECIMAL(15,2),
                reu TEXT,
                observacoes TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cadastro_id)
            )
        """)
        
        # Tabela de andamentos processuais
        cur.execute("""
            CREATE TABLE IF NOT EXISTS andamentos (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                data DATE NOT NULL,
                descricao TEXT NOT NULL,
                visivel_cliente BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
# Tabela de mensagens
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mensagens (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                remetente VARCHAR(20) NOT NULL,
                texto TEXT NOT NULL,
                lida BOOLEAN DEFAULT FALSE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ========== MÚLTIPLOS PROCESSOS E HONORÁRIOS ==========
        
        # Tabela de processos (múltiplos por cliente)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS processos (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                numero_processo VARCHAR(50),
                tipo_acao VARCHAR(100),
                vara_tribunal VARCHAR(255),
                fase VARCHAR(100) DEFAULT 'Inicial',
                reu TEXT,
                valor_causa DECIMAL(15,2),
                data_distribuicao DATE,
                status VARCHAR(20) DEFAULT 'ativo',
                observacoes TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de andamentos (vinculado a processo específico)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS processo_andamentos (
                id SERIAL PRIMARY KEY,
                processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
                data DATE NOT NULL,
                descricao TEXT NOT NULL,
                visivel_cliente BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de contratos de honorários
        cur.execute("""
            CREATE TABLE IF NOT EXISTS contratos_honorarios (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                processo_id INTEGER REFERENCES processos(id) ON DELETE SET NULL,
                tipo VARCHAR(20) NOT NULL,
                descricao VARCHAR(255),
                valor_total DECIMAL(15,2),
                num_parcelas INTEGER DEFAULT 1,
                valor_mensal DECIMAL(15,2),
                dia_vencimento INTEGER DEFAULT 10,
                percentual_exito DECIMAL(5,2),
                data_inicio DATE,
                status VARCHAR(20) DEFAULT 'ativo',
                observacoes TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de parcelas
        cur.execute("""
            CREATE TABLE IF NOT EXISTS parcelas (
                id SERIAL PRIMARY KEY,
                contrato_id INTEGER REFERENCES contratos_honorarios(id) ON DELETE CASCADE,
                numero INTEGER NOT NULL,
                valor DECIMAL(15,2) NOT NULL,
                vencimento DATE NOT NULL,
                status VARCHAR(20) DEFAULT 'pendente',
                data_pagamento DATE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de comprovantes
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comprovantes (
                id SERIAL PRIMARY KEY,
                parcela_id INTEGER REFERENCES parcelas(id) ON DELETE CASCADE,
                arquivo_nome VARCHAR(255),
                arquivo_path VARCHAR(500),
                enviado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pendente',
                verificado_em TIMESTAMP,
                verificado_por VARCHAR(255),
                observacoes TEXT
            )
        """)
        
        # ========== DOCUMENTOS ADMIN E EXTRAS ==========
        
        # Tabela de documentos enviados pelo admin para o cliente
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documentos_admin (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                nome_arquivo VARCHAR(255) NOT NULL,
                nome_original VARCHAR(255) NOT NULL,
                arquivo_path VARCHAR(500) NOT NULL,
                descricao VARCHAR(255),
                enviado_por VARCHAR(255),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de documentos extras enviados pelo cliente
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documentos_extras (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                nome_arquivo VARCHAR(255) NOT NULL,
                nome_original VARCHAR(255) NOT NULL,
                arquivo_path VARCHAR(500) NOT NULL,
                descricao VARCHAR(255),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        logger.info("Tabelas do Portal do Cliente verificadas/criadas!")
        
        conn.commit()
        
        # Criar usuário admin inicial se não existir
        cur.execute("SELECT COUNT(*) FROM usuarios WHERE email = %s", ("admin@vaucherealvares.com.br",))
        if cur.fetchone()[0] == 0:
            senha_hash = hash_senha(ADMIN_INICIAL_SENHA)
            cur.execute("""
                INSERT INTO usuarios (email, senha_hash, nome, is_admin)
                VALUES (%s, %s, %s, %s)
            """, ("admin@vaucherealvares.com.br", senha_hash, "Administrador", True))
            conn.commit()
            logger.info("Usuário admin inicial criado!")
        
        cur.close()
        conn.close()
        logger.info("Banco de dados inicializado com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")

@app.on_event("startup")
def startup():
    logger.info("Iniciando aplicação...")
    logger.info(f"RESEND_API_KEY configurada: {bool(RESEND_API_KEY)}")
    logger.info(f"FROM_EMAIL: {FROM_EMAIL}")
    init_db()

# ============================================
# FUNÇÕES DO BANCO - USUÁRIOS
# ============================================

def buscar_usuario_por_email(email: str) -> dict:
    """Busca um usuário pelo e-mail."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM usuarios WHERE email = %s AND ativo = TRUE", (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar usuário: {e}")
        return None

def listar_usuarios() -> List[dict]:
    """Lista todos os usuários."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, email, nome, is_admin, ativo, criado_em FROM usuarios ORDER BY criado_em DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return []

def criar_usuario(email: str, senha: str, nome: str, is_admin: bool = False) -> bool:
    """Cria um novo usuário."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        senha_hash = hash_senha(senha)
        cur.execute("""
            INSERT INTO usuarios (email, senha_hash, nome, is_admin)
            VALUES (%s, %s, %s, %s)
        """, (email, senha_hash, nome, is_admin))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao criar usuário: {e}")
        return False

def atualizar_usuario(user_id: int, nome: str = None, senha: str = None, is_admin: bool = None, ativo: bool = None) -> bool:
    """Atualiza um usuário."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        updates = []
        values = []
        
        if nome is not None:
            updates.append("nome = %s")
            values.append(nome)
        if senha is not None:
            updates.append("senha_hash = %s")
            values.append(hash_senha(senha))
        if is_admin is not None:
            updates.append("is_admin = %s")
            values.append(is_admin)
        if ativo is not None:
            updates.append("ativo = %s")
            values.append(ativo)
        
        if updates:
            values.append(user_id)
            cur.execute(f"UPDATE usuarios SET {', '.join(updates)} WHERE id = %s", values)
            conn.commit()
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar usuário: {e}")
        return False

def deletar_usuario(user_id: int) -> bool:
    """Desativa um usuário (soft delete)."""
    return atualizar_usuario(user_id, ativo=False)

# ============================================
# FUNÇÕES DO BANCO - CADASTROS
# ============================================

def salvar_cadastro(cadastro: dict):
    """Salva ou atualiza um cadastro no banco."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO cadastros (id, data, data_hora, status, dados, documentos, arquivos_gerados, documentos_assinados, data_assinatura)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                dados = EXCLUDED.dados,
                documentos = EXCLUDED.documentos,
                arquivos_gerados = EXCLUDED.arquivos_gerados,
                documentos_assinados = EXCLUDED.documentos_assinados,
                data_assinatura = EXCLUDED.data_assinatura
        """, (
            cadastro["id"],
            cadastro["data"],
            cadastro.get("data_hora", datetime.now().isoformat()),
            cadastro["status"],
            json.dumps(cadastro["dados"]),
            json.dumps(cadastro.get("documentos", [])),
            json.dumps(cadastro.get("arquivos_gerados", {})),
            json.dumps(cadastro.get("documentos_assinados", [])),
            cadastro.get("data_assinatura")
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar cadastro: {e}")
        return False

def carregar_cadastros() -> List[dict]:
    """Carrega todos os cadastros do banco."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM cadastros ORDER BY data_hora DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        cadastros = []
        for row in rows:
            cadastros.append({
                "id": row["id"],
                "data": row["data"],
                "data_hora": row["data_hora"].isoformat() if row["data_hora"] else "",
                "status": row["status"],
                "dados": row["dados"] if isinstance(row["dados"], dict) else json.loads(row["dados"]),
                "documentos": row["documentos"] if isinstance(row["documentos"], list) else json.loads(row["documentos"] or "[]"),
                "arquivos_gerados": row["arquivos_gerados"] if isinstance(row["arquivos_gerados"], dict) else json.loads(row["arquivos_gerados"] or "{}"),
                "documentos_assinados": row.get("documentos_assinados") if isinstance(row.get("documentos_assinados"), list) else json.loads(row.get("documentos_assinados") or "[]"),
                "data_assinatura": row.get("data_assinatura").isoformat() if row.get("data_assinatura") else None
            })
        return cadastros
    except Exception as e:
        logger.error(f"Erro ao carregar cadastros: {e}")
        return []

def buscar_cadastro(cadastro_id: str) -> dict:
    """Busca um cadastro específico."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM cadastros WHERE id = %s", (cadastro_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            return {
                "id": row["id"],
                "data": row["data"],
                "data_hora": row["data_hora"].isoformat() if row["data_hora"] else "",
                "status": row["status"],
                "dados": row["dados"] if isinstance(row["dados"], dict) else json.loads(row["dados"]),
                "documentos": row["documentos"] if isinstance(row["documentos"], list) else json.loads(row["documentos"] or "[]"),
                "arquivos_gerados": row["arquivos_gerados"] if isinstance(row["arquivos_gerados"], dict) else json.loads(row["arquivos_gerados"] or "{}"),
                "documentos_assinados": row.get("documentos_assinados") if isinstance(row.get("documentos_assinados"), list) else json.loads(row.get("documentos_assinados") or "[]"),
                "data_assinatura": row.get("data_assinatura").isoformat() if row.get("data_assinatura") else None
            }
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar cadastro: {e}")
        return None

def atualizar_status(cadastro_id: str, status: str):
    """Atualiza o status de um cadastro."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("UPDATE cadastros SET status = %s WHERE id = %s", (status, cadastro_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar status: {e}")
        return False

# ============================================
# FUNÇÕES DO BANCO - FINANCEIRO
# ============================================

def salvar_financeiro(cadastro_id: str, dados: dict) -> bool:
    """Salva ou atualiza dados financeiros de um cadastro."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO financeiro (cadastro_id, numero_processo, vara_tribunal, 
                percentual_honorarios, valor_credito_cliente, depositos, sucumbencias, retencoes, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cadastro_id) DO UPDATE SET
                numero_processo = EXCLUDED.numero_processo,
                vara_tribunal = EXCLUDED.vara_tribunal,
                percentual_honorarios = EXCLUDED.percentual_honorarios,
                valor_credito_cliente = EXCLUDED.valor_credito_cliente,
                depositos = EXCLUDED.depositos,
                sucumbencias = EXCLUDED.sucumbencias,
                retencoes = EXCLUDED.retencoes,
                observacoes = EXCLUDED.observacoes,
                atualizado_em = CURRENT_TIMESTAMP
        """, (
            cadastro_id,
            dados.get("numero_processo", ""),
            dados.get("vara_tribunal", ""),
            dados.get("percentual_honorarios", 20),
            dados.get("valor_credito_cliente", 0),
            json.dumps(dados.get("depositos", [])),
            json.dumps(dados.get("sucumbencias", [])),
            json.dumps(dados.get("retencoes", [])),
            dados.get("observacoes", "")
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar financeiro: {e}")
        return False

def buscar_financeiro(cadastro_id: str) -> dict:
    """Busca dados financeiros de um cadastro."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM financeiro WHERE cadastro_id = %s", (cadastro_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            depositos = row.get("depositos")
            if isinstance(depositos, str):
                depositos = json.loads(depositos)
            elif depositos is None:
                depositos = []
            
            sucumbencias = row.get("sucumbencias")
            if isinstance(sucumbencias, str):
                sucumbencias = json.loads(sucumbencias)
            elif sucumbencias is None:
                sucumbencias = []
            
            retencoes = row.get("retencoes")
            if isinstance(retencoes, str):
                retencoes = json.loads(retencoes)
            elif retencoes is None:
                retencoes = []
            
            return {
                "id": row["id"],
                "cadastro_id": row["cadastro_id"],
                "numero_processo": row["numero_processo"] or "",
                "vara_tribunal": row["vara_tribunal"] or "",
                "percentual_honorarios": float(row["percentual_honorarios"]) if row["percentual_honorarios"] else 20,
                "valor_credito_cliente": float(row["valor_credito_cliente"]) if row.get("valor_credito_cliente") else 0,
                "depositos": depositos,
                "sucumbencias": sucumbencias,
                "retencoes": retencoes,
                "observacoes": row["observacoes"] or ""
            }
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar financeiro: {e}")
        return None

# ============================================
# MODELOS DE DADOS
# ============================================

class DadosCliente(BaseModel):
    nome: str
    nacionalidade: str = "brasileiro(a)"
    estado_civil: str
    profissao: str
    rg: str
    cpf: str
    data_nascimento: str
    endereco_completo: str
    email: EmailStr
    telefone: str
    tipo_demanda: str
    objeto_contrato: str
    poderes_especificos: str
    honorarios: Optional[str] = ""
    observacoes: Optional[str] = ""

class LoginRequest(BaseModel):
    email: str
    senha: str

class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    nome: Optional[str] = None
    is_admin: Optional[bool] = None
    message: Optional[str] = None

class NovoUsuario(BaseModel):
    email: EmailStr
    senha: str
    nome: str
    is_admin: bool = False

class AtualizarUsuario(BaseModel):
    nome: Optional[str] = None
    senha: Optional[str] = None
    is_admin: Optional[bool] = None
    ativo: Optional[bool] = None

class AlterarSenha(BaseModel):
    senha_atual: str
    nova_senha: str

class DepositoItem(BaseModel):
    data: str = ""
    origem: str = ""
    valor: float = 0

class SucumbenciaItem(BaseModel):
    descricao: str = ""
    valor: float = 0

class RetencaoItem(BaseModel):
    descricao: str = ""
    valor: float = 0

class FinanceiroData(BaseModel):
    numero_processo: Optional[str] = ""
    vara_tribunal: Optional[str] = ""
    percentual_honorarios: Optional[float] = 20
    valor_credito_cliente: Optional[float] = 0
    depositos: Optional[List[dict]] = []
    sucumbencias: Optional[List[dict]] = []
    retencoes: Optional[List[dict]] = []
    observacoes: Optional[str] = ""

# ========== MODELS PORTAL DO CLIENTE ==========

class ClienteLogin(BaseModel):
    email: str
    senha: str

class ClienteAlterarSenha(BaseModel):
    senha_atual: str
    nova_senha: str

class ProcessoInfoModel(BaseModel):
    numero_processo: Optional[str] = ""
    vara_tribunal: Optional[str] = ""
    fase: Optional[str] = "Inicial"
    data_distribuicao: Optional[str] = None
    valor_causa: Optional[float] = 0
    reu: Optional[str] = ""
    observacoes: Optional[str] = ""

class AndamentoModel(BaseModel):
    data: str
    descricao: str
    visivel_cliente: Optional[bool] = True

class MensagemEnvio(BaseModel):
    texto: str

# ============================================
# GERADOR DE DOCUMENTOS
# ============================================

class GeradorDocumentos:
    def __init__(self):
        self.modelo_contrato = os.path.join(MODELOS_DIR, 'CONTRATO_Modelo.docx')
        self.modelo_procuracao = os.path.join(MODELOS_DIR, 'Procuracao_Modelo.docx')
        self.modelo_prestacao = os.path.join(MODELOS_DIR, 'Prestacao_Contas_Modelo.docx')
    
    def _formatar_data(self, data_str: str) -> str:
        if not data_str:
            return ''
        try:
            if '-' in data_str:
                partes = data_str.split('-')
                return f"{partes[2]}/{partes[1]}/{partes[0]}"
            return data_str
        except:
            return data_str
    
    def _data_por_extenso(self) -> str:
        meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
        hoje = datetime.now()
        return f"{hoje.day} de {meses[hoje.month - 1]} de {hoje.year}"
    
    def _substituir_no_xml(self, xml_content: str, dados: dict) -> str:
        substituicoes = {
            '{{nome}}': dados.get('nome', ''),
            '{{nacionalidade}}': dados.get('nacionalidade', ''),
            '{{estado_civil}}': dados.get('estado_civil', ''),
            '{{profissão}}': dados.get('profissao', ''),
            '{{rg}}': dados.get('rg', ''),
            '{{cpf}}': dados.get('cpf', ''),
            '{{data_nascimento}}': self._formatar_data(dados.get('data_nascimento', '')),
            '{{endereco_completo}}': dados.get('endereco_completo', ''),
            '{{email}}': dados.get('email', ''),
            '{{telefone}}': dados.get('telefone', ''),
            '{{poderes_especificos}}': dados.get('poderes_especificos', ''),
        }
        
        resultado = xml_content
        for placeholder, valor in substituicoes.items():
            resultado = resultado.replace(placeholder, valor)
        
        objeto = dados.get('objeto_contrato', '')
        if objeto:
            resultado = resultado.replace(
                'advocatícios para .',
                f'advocatícios para {objeto}.'
            )
        
        honorarios = dados.get('honorarios', '')
        if honorarios:
            resultado = resultado.replace(
                'fixar-se-ão em .',
                f'fixar-se-ão em {honorarios}.'
            )
        
        resultado = resultado.replace('sample text question answer', self._data_por_extenso())
        resultado = resultado.replace(
            'Cuiabá, ____ de ____________de________.',
            f'Cuiabá, {self._data_por_extenso()}.'
        )
        
        return resultado
    
    def _gerar_documento(self, modelo_path: str, dados: dict, nome_saida: str, cadastro_id: str) -> str:
        if not os.path.exists(modelo_path):
            raise FileNotFoundError(f"Modelo não encontrado: {modelo_path}")
        
        cliente_dir = os.path.join(GERADOS_DIR, cadastro_id)
        os.makedirs(cliente_dir, exist_ok=True)
        
        temp_dir = os.path.join(cliente_dir, f'temp_{uuid.uuid4().hex[:8]}')
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            with zipfile.ZipFile(modelo_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            doc_xml_path = os.path.join(temp_dir, 'word', 'document.xml')
            with open(doc_xml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content = self._substituir_no_xml(content, dados)
            
            with open(doc_xml_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            saida_path = os.path.join(cliente_dir, nome_saida)
            
            with zipfile.ZipFile(saida_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            return saida_path
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    def gerar_contrato(self, dados: dict, cadastro_id: str) -> str:
        nome = dados.get('nome', 'Cliente').replace(' ', '_')
        nome_arquivo = f"Contrato_Honorarios_{nome}.docx"
        return self._gerar_documento(self.modelo_contrato, dados, nome_arquivo, cadastro_id)
    
    def gerar_procuracao(self, dados: dict, cadastro_id: str) -> str:
        nome = dados.get('nome', 'Cliente').replace(' ', '_')
        nome_arquivo = f"Procuracao_{nome}.docx"
        return self._gerar_documento(self.modelo_procuracao, dados, nome_arquivo, cadastro_id)
    
    def _format_money(self, value: float) -> str:
        """Formata valor para moeda brasileira."""
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def _format_data(self, data_str: str) -> str:
        """Formata data de YYYY-MM-DD para DD/MM/YYYY."""
        if not data_str:
            return ""
        try:
            partes = data_str.split("-")
            return f"{partes[2]}/{partes[1]}/{partes[0]}"
        except:
            return data_str
    
    def gerar_prestacao_contas(self, dados_cliente: dict, financeiro: dict, cadastro_id: str) -> str:
        """Gera documento de prestação de contas completo usando python-docx."""
        from docx import Document
        from docx.shared import Pt, Cm, Inches, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        
        depositos = financeiro.get("depositos", [])
        sucumbencias = financeiro.get("sucumbencias", [])
        retencoes = financeiro.get("retencoes", [])
        percentual = float(financeiro.get("percentual_honorarios", 20))
        valor_credito = float(financeiro.get("valor_credito_cliente", 0))
        
        total_depositos = sum(float(d.get("valor", 0)) for d in depositos)
        total_sucumbencias = sum(float(s.get("valor", 0)) for s in sucumbencias)
        total_retencoes = sum(float(r.get("valor", 0)) for r in retencoes)
        honorarios_contratuais = valor_credito * (percentual / 100)
        valor_liquido = valor_credito - honorarios_contratuais - total_retencoes
        
        doc = Document()
        
        for section in doc.sections:
            section.top_margin = Cm(2)
            section.bottom_margin = Cm(2)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.5)
        
        def set_cell_shading(cell, color):
            shading = OxmlElement('w:shd')
            shading.set(qn('w:fill'), color)
            cell._tc.get_or_add_tcPr().append(shading)
        
        # TÍTULO
        titulo = doc.add_paragraph()
        titulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = titulo.add_run("PRESTAÇÃO DE CONTAS")
        run.bold = True
        run.font.size = Pt(14)
        run.font.name = "Arial"
        
        subtitulo = doc.add_paragraph()
        subtitulo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run1 = subtitulo.add_run("VAUCHER E ÁLVARES SOCIEDADE DE ADVOGADOS ")
        run1.bold = True
        run1.font.size = Pt(11)
        run2 = subtitulo.add_run("→ ")
        run2.font.size = Pt(11)
        run3 = subtitulo.add_run("Cliente")
        run3.bold = True
        run3.font.size = Pt(11)
        run3.font.color.rgb = RGBColor(238, 0, 0)
        
        # 1. IDENTIFICAÇÃO
        doc.add_paragraph()
        h1 = doc.add_paragraph()
        run = h1.add_run("1. Identificação das Partes")
        run.bold = True
        run.font.size = Pt(11)
        
        p = doc.add_paragraph()
        p.add_run("Cliente: ").bold = True
        p.add_run(dados_cliente.get('nome', '').upper())
        
        p = doc.add_paragraph()
        p.add_run("Escritório de Advocacia: ").bold = True
        p.add_run("VAUCHER E ÁLVARES SOCIEDADE DE ADVOGADOS").bold = True
        p.add_run(", devidamente registrada na Ordem dos Advogados do Brasil Seccional de Mato Grosso sob o nº 669, inscrita no CNPJ sob o nº 21.336.697/0001-46, com sede na Rua Lima, n. 106, Bairro Jardim das Américas, em Cuiabá-MT.")
        
        p = doc.add_paragraph()
        p.add_run("Processo(s): ").bold = True
        run = p.add_run(f"{financeiro.get('numero_processo', '')} / {financeiro.get('vara_tribunal', '')}")
        run.font.color.rgb = RGBColor(238, 0, 0)
        
        # 2. OBJETO
        doc.add_paragraph()
        h2 = doc.add_paragraph()
        run = h2.add_run("2. Objeto da Prestação de Contas")
        run.bold = True
        run.font.size = Pt(11)
        
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(1.25)
        p.add_run("A presente prestação de contas tem por finalidade demonstrar, de forma ")
        p.add_run("transparente, discriminada e fundamentada").bold = True
        p.add_run(", os valores ")
        p.add_run("totais recebidos").bold = True
        p.add_run(" no âmbito do(s) processo(s) acima identificado(s), indicando:")
        
        items = [
            ("valores pertencentes ao ", "cliente", ";"),
            ("valores correspondentes aos ", "honorários advocatícios contratuais", ";"),
            ("valores referentes aos ", "honorários advocatícios sucumbenciais", ", de titularidade do advogado;"),
            ("valores retidos a título de ", "tributos/contribuição previdenciária (PSS)", "."),
        ]
        for prefix, bold_text, suffix in items:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(prefix)
            p.add_run(bold_text).bold = True
            p.add_run(suffix)
        
        # 3. VALORES TOTAIS RECEBIDOS
        doc.add_paragraph()
        h3 = doc.add_paragraph()
        run = h3.add_run("3. Valores Totais Recebidos")
        run.bold = True
        run.font.size = Pt(11)
        
        num_depositos = len(depositos) if depositos else 1
        table = doc.add_table(rows=num_depositos + 2, cols=3)
        table.style = 'Table Grid'
        
        hdr = table.rows[0].cells
        hdr[0].text = "Data do Recebimento"
        hdr[1].text = "Origem do Valor"
        hdr[2].text = "Valor Bruto (R$)"
        for cell in hdr:
            cell.paragraphs[0].runs[0].bold = True
            set_cell_shading(cell, "D9D9D9")
        
        if depositos:
            for i, dep in enumerate(depositos):
                row = table.rows[i + 1].cells
                row[0].text = self._format_data(dep.get("data", ""))
                row[1].text = dep.get("origem", "")
                row[2].text = self._format_money(float(dep.get("valor", 0)))
        else:
            row = table.rows[1].cells
            row[0].text = "-"
            row[1].text = "-"
            row[2].text = self._format_money(0)
        
        total_row = table.rows[-1].cells
        total_row[0].text = ""
        total_row[1].text = "TOTAL"
        total_row[1].paragraphs[0].runs[0].bold = True
        total_row[2].text = self._format_money(total_depositos)
        total_row[2].paragraphs[0].runs[0].bold = True
        
        # 4. DISCRIMINAÇÃO DOS VALORES
        doc.add_paragraph()
        h4 = doc.add_paragraph()
        run = h4.add_run("4. Discriminação dos Valores")
        run.bold = True
        run.font.size = Pt(11)
        
        # 4.1 Receita do Cliente
        h41 = doc.add_paragraph()
        run = h41.add_run("4.1. Receita Pertencente ao Cliente")
        run.bold = True
        
        p = doc.add_paragraph()
        p.add_run("Corresponde à parcela do valor recebido que integra o patrimônio do cliente, após a dedução dos honorários advocatícios devidos e das retenções legais.")
        
        table41 = doc.add_table(rows=5 + len(retencoes), cols=2)
        table41.style = 'Table Grid'
        
        rows_data = [
            ("Valor bruto total recebido (Principal + Sucumbência)", self._format_money(total_depositos), False),
            (f"(-) Honorários contratuais ({percentual}% sobre crédito do cliente)", self._format_money(honorarios_contratuais), False),
            (f"(-) Honorários sucumbenciais", self._format_money(total_sucumbencias), False),
        ]
        
        for ret in retencoes:
            rows_data.append((f"(-) {ret.get('descricao', 'Retenção')}", self._format_money(float(ret.get('valor', 0))), False))
        
        if not retencoes:
            rows_data.append(("(-) Retenções Legais (PSS/IRRF)", self._format_money(0), False))
        
        rows_data.append(("Valor líquido devido ao cliente", self._format_money(valor_liquido), True))
        
        for i, (desc, val, is_total) in enumerate(rows_data):
            row = table41.rows[i].cells
            row[0].text = desc
            row[1].text = val
            if is_total:
                row[0].paragraphs[0].runs[0].bold = True
                row[1].paragraphs[0].runs[0].bold = True
                set_cell_shading(row[0], "E2EFDA")
                set_cell_shading(row[1], "E2EFDA")
        
        # 4.2 Honorários Contratuais
        doc.add_paragraph()
        h42 = doc.add_paragraph()
        run = h42.add_run("4.2. Honorários Advocatícios Contratuais")
        run.bold = True
        
        p = doc.add_paragraph()
        p.add_run("Nos termos do art. 22 da Lei nº 8.906/1994, os honorários advocatícios ajustados em contrato constituem direito do advogado, possuindo natureza remuneratória pelos serviços prestados.")
        
        p = doc.add_paragraph()
        p.add_run("Percentual contratado: ").bold = True
        p.add_run(f"{percentual}%")
        
        p = doc.add_paragraph()
        p.add_run("Base de cálculo: ").bold = True
        p.add_run(f"Valor do crédito do cliente ({self._format_money(valor_credito)})")
        
        table42 = doc.add_table(rows=1, cols=2)
        table42.style = 'Table Grid'
        row = table42.rows[0].cells
        row[0].text = f"Percentual contratual ({percentual}%) sobre {self._format_money(valor_credito)}"
        row[1].text = self._format_money(honorarios_contratuais)
        row[1].paragraphs[0].runs[0].bold = True
        
        # 4.3 Honorários Sucumbenciais
        doc.add_paragraph()
        h43 = doc.add_paragraph()
        run = h43.add_run("4.3. Honorários Advocatícios Sucumbenciais")
        run.bold = True
        
        p = doc.add_paragraph()
        p.add_run("Os honorários sucumbenciais são fixados judicialmente e pertencem exclusivamente ao advogado, conforme dispõe expressamente o art. 85, §14, do CPC.")
        
        num_sucumb = len(sucumbencias) if sucumbencias else 1
        table43 = doc.add_table(rows=num_sucumb + 1, cols=2)
        table43.style = 'Table Grid'
        
        if sucumbencias:
            for i, suc in enumerate(sucumbencias):
                row = table43.rows[i].cells
                row[0].text = suc.get("descricao", "")
                row[1].text = self._format_money(float(suc.get("valor", 0)))
        else:
            row = table43.rows[0].cells
            row[0].text = "Honorários sucumbenciais"
            row[1].text = self._format_money(0)
        
        total_suc_row = table43.rows[-1].cells
        total_suc_row[0].text = "Total Honorários Sucumbenciais"
        total_suc_row[0].paragraphs[0].runs[0].bold = True
        total_suc_row[1].text = self._format_money(total_sucumbencias)
        total_suc_row[1].paragraphs[0].runs[0].bold = True
        
        p = doc.add_paragraph()
        run = p.add_run("Obs.: Os honorários sucumbenciais não se confundem com o crédito do cliente, não integram sua base patrimonial e não substituem os honorários contratuais.")
        run.italic = True
        run.font.size = Pt(9)
        
        # 5. RESUMO GERAL
        doc.add_paragraph()
        h5 = doc.add_paragraph()
        run = h5.add_run("5. Resumo Geral da Prestação de Contas")
        run.bold = True
        run.font.size = Pt(11)
        
        table5 = doc.add_table(rows=5, cols=3)
        table5.style = 'Table Grid'
        
        hdr5 = table5.rows[0].cells
        hdr5[0].text = "Natureza do Valor"
        hdr5[1].text = "Valor (R$)"
        hdr5[2].text = "Titularidade"
        for cell in hdr5:
            cell.paragraphs[0].runs[0].bold = True
            set_cell_shading(cell, "D9D9D9")
        
        resumo_data = [
            ("Receita líquida do cliente", self._format_money(valor_liquido), "Cliente"),
            ("Honorários contratuais", self._format_money(honorarios_contratuais), "Escritório"),
            ("Honorários sucumbenciais", self._format_money(total_sucumbencias), "Escritório"),
            ("TOTAL GERAL", self._format_money(total_depositos), ""),
        ]
        
        for i, (nat, val, tit) in enumerate(resumo_data):
            row = table5.rows[i + 1].cells
            row[0].text = nat
            row[1].text = val
            row[2].text = tit
            if i == 3:
                row[0].paragraphs[0].runs[0].bold = True
                row[1].paragraphs[0].runs[0].bold = True
                set_cell_shading(row[0], "F2F2F2")
                set_cell_shading(row[1], "F2F2F2")
                set_cell_shading(row[2], "F2F2F2")
        
        # 6. CONCLUSÃO
        doc.add_paragraph()
        h6 = doc.add_paragraph()
        run = h6.add_run("6. Conclusão")
        run.bold = True
        run.font.size = Pt(11)
        
        doc.add_paragraph("O escritório declara que:")
        
        conclusoes = [
            "os valores foram corretamente recebidos e contabilizados;",
            "a retenção dos honorários observa expressa previsão legal e contratual;",
            "o valor líquido indicado encontra-se à disposição do cliente, após a assinatura da presente prestação de contas que também reconhece a quitação geral e irrestrita quanto as obrigações do escritório na demanda em referência."
        ]
        for c in conclusoes:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(c)
        
        doc.add_paragraph()
        doc.add_paragraph()
        p = doc.add_paragraph(f"Cuiabá-MT, {self._data_por_extenso()}.")
        
        doc.add_paragraph()
        doc.add_paragraph()
        
        ass1 = doc.add_paragraph("VAUCHER E ÁLVARES SOCIEDADE DE ADVOGADOS")
        ass1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ass1.runs[0].bold = True
        
        cnpj = doc.add_paragraph("CNPJ 21.336.697/0001-46")
        cnpj.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        oab = doc.add_paragraph("OAB/MT 669")
        oab.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph()
        doc.add_paragraph()
        
        ass2 = doc.add_paragraph(dados_cliente.get('nome', '').upper())
        ass2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ass2.runs[0].bold = True
        
        cliente_dir = os.path.join(GERADOS_DIR, cadastro_id)
        os.makedirs(cliente_dir, exist_ok=True)
        
        nome = dados_cliente.get('nome', 'Cliente').replace(' ', '_')
        nome_arquivo = f"Prestacao_Contas_{nome}.docx"
        caminho_arquivo = os.path.join(cliente_dir, nome_arquivo)
        
        doc.save(caminho_arquivo)
        return caminho_arquivo
    
    def gerar_todos(self, dados: dict, cadastro_id: str) -> dict:
        return {
            'contrato': self.gerar_contrato(dados, cadastro_id),
            'procuracao': self.gerar_procuracao(dados, cadastro_id)
        }

gerador = GeradorDocumentos()

# ============================================
# ENVIO DE E-MAIL COM RESEND
# ============================================

async def enviar_email_resend(destinatario: str, assunto: str, corpo_html: str, anexos: List[dict] = None) -> bool:
    """Envia e-mail usando a API do Resend."""
    if not RESEND_API_KEY:
        logger.error("RESEND_API_KEY não configurada!")
        return False
    
    logger.info(f"Enviando e-mail via Resend para {destinatario}")
    
    payload = {
        "from": f"Vaucher & Álvares <{FROM_EMAIL}>",
        "to": [destinatario],
        "subject": assunto,
        "html": corpo_html
    }
    
    if anexos:
        payload["attachments"] = anexos
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30.0
            )
            
            logger.info(f"Resend response status: {response.status_code}")
            logger.info(f"Resend response body: {response.text}")
            
            if response.status_code == 200:
                logger.info(f"E-mail enviado com sucesso para {destinatario}")
                return True
            else:
                logger.error(f"Erro do Resend: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail: {e}")
        return False

# ============================================
# ROTAS DA API - BÁSICAS
# ============================================

@app.get("/")
def root():
    return {"message": "Vaucher & Álvares API", "status": "online", "version": "3.0"}

@app.get("/health")
def health():
    return {
        "status": "healthy", 
        "database": "connected" if get_db() else "disconnected",
        "email": "resend" if RESEND_API_KEY else "not_configured"
    }

# --- AUTENTICAÇÃO ADMIN ---

@app.post("/api/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """Autenticação do painel administrativo."""
    usuario = buscar_usuario_por_email(request.email)
    
    if usuario and verificar_senha(request.senha, usuario['senha_hash']):
        token = gerar_token(usuario["id"], usuario["email"], usuario["is_admin"])
        return LoginResponse(
            success=True, 
            token=token, 
            nome=usuario['nome'],
            is_admin=usuario['is_admin']
        )
    
    return LoginResponse(success=False, message="E-mail ou senha incorretos")

@app.post("/api/logout")
def logout():
    """Encerra a sessão do usuário."""
    return {"success": True}

# --- GERENCIAMENTO DE USUÁRIOS (APENAS ADMIN) ---

@app.get("/api/usuarios")
def listar_todos_usuarios(usuario: dict = Depends(verificar_admin)):
    """Lista todos os usuários (apenas admin)."""
    return listar_usuarios()

@app.post("/api/usuarios")
def criar_novo_usuario(dados: NovoUsuario, usuario: dict = Depends(verificar_admin)):
    """Cria um novo usuário (apenas admin)."""
    if buscar_usuario_por_email(dados.email):
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    
    if criar_usuario(dados.email, dados.senha, dados.nome, dados.is_admin):
        return {"success": True, "message": f"Usuário {dados.nome} criado com sucesso"}
    
    raise HTTPException(status_code=500, detail="Erro ao criar usuário")

@app.put("/api/usuarios/{user_id}")
def atualizar_usuario_existente(user_id: int, dados: AtualizarUsuario, usuario: dict = Depends(verificar_admin)):
    """Atualiza um usuário (apenas admin)."""
    if atualizar_usuario(user_id, dados.nome, dados.senha, dados.is_admin, dados.ativo):
        return {"success": True, "message": "Usuário atualizado com sucesso"}
    
    raise HTTPException(status_code=500, detail="Erro ao atualizar usuário")

@app.delete("/api/usuarios/{user_id}")
def desativar_usuario(user_id: int, usuario: dict = Depends(verificar_admin)):
    """Desativa um usuário (apenas admin)."""
    if usuario["id"] == user_id:
        raise HTTPException(status_code=400, detail="Você não pode desativar sua própria conta")
    
    if deletar_usuario(user_id):
        return {"success": True, "message": "Usuário desativado com sucesso"}
    
    raise HTTPException(status_code=500, detail="Erro ao desativar usuário")

@app.post("/api/alterar-senha")
def alterar_minha_senha(dados: AlterarSenha, usuario: dict = Depends(verificar_token)):
    """Permite ao usuário alterar sua própria senha."""
    usuario_db = buscar_usuario_por_email(usuario["email"])
    
    if not usuario_db or not verificar_senha(dados.senha_atual, usuario_db["senha_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    
    if atualizar_usuario(usuario["id"], senha=dados.nova_senha):
        return {"success": True, "message": "Senha alterada com sucesso"}
    
    raise HTTPException(status_code=500, detail="Erro ao alterar senha")

# --- CADASTROS ---

@app.post("/api/cadastros")
async def criar_cadastro(dados: DadosCliente):
    """Recebe novo cadastro do cliente."""
    logger.info(f"Novo cadastro recebido: {dados.nome}")
    
    novo_cadastro = {
        "id": uuid.uuid4().hex[:12],
        "data": datetime.now().strftime("%d/%m/%Y"),
        "data_hora": datetime.now().isoformat(),
        "status": "pendente",
        "dados": dados.dict(),
        "documentos": [],
        "arquivos_gerados": {}
    }
    
    if salvar_cadastro(novo_cadastro):
        logger.info(f"Cadastro salvo com ID: {novo_cadastro['id']}")
        
        try:
            conteudo = f"""
                <p style="font-size: 16px;">Prezado(a) <strong>{dados.nome}</strong>,</p>
                <p>Seu cadastro foi recebido com sucesso!</p>
                <p>Nossa equipe irá analisar as informações e documentos enviados. 
                Em breve você receberá o Contrato de Honorários e a Procuração 
                para assinatura.</p>
                
                <div style="background-color: #f0f0f0; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0 0 10px 0;"><strong>📋 Seu código de protocolo:</strong></p>
                    <p style="font-size: 20px; font-family: monospace; background: #fff; padding: 10px; border-radius: 5px; text-align: center; margin: 0; color: #8B1538; font-weight: bold;">{novo_cadastro['id']}</p>
                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #666;">Guarde este código para acompanhar seu cadastro</p>
                </div>
                
                <div style="background-color: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>⏱ Prazo estimado:</strong> até 2 dias úteis</p>
                </div>
                
                <p>Agradecemos a confiança em nosso escritório!</p>
            """
            corpo_html = criar_email_html(conteudo)
            
            await enviar_email_resend(
                dados.email,
                "✅ Cadastro Recebido - Vaucher & Álvares Advogados",
                corpo_html
            )
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de confirmação: {e}")
        
        return {"success": True, "id": novo_cadastro["id"]}
    else:
        raise HTTPException(status_code=500, detail="Erro ao salvar cadastro")

@app.get("/api/cadastros")
def listar_cadastros():
    """Lista todos os cadastros (painel admin)."""
    return carregar_cadastros()

@app.get("/api/cadastros/{cadastro_id}")
def obter_cadastro(cadastro_id: str):
    """Obtém detalhes de um cadastro específico."""
    cadastro = buscar_cadastro(cadastro_id)
    if cadastro:
        return cadastro
    raise HTTPException(status_code=404, detail="Cadastro não encontrado")

@app.delete("/api/cadastros/{cadastro_id}")
def deletar_cadastro(cadastro_id: str, usuario: dict = Depends(verificar_admin)):
    """Deleta um cadastro permanentemente (apenas admin)."""
    logger.info(f"Deletando cadastro: {cadastro_id} por {usuario['email']}")
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM cadastros WHERE id = %s", (cadastro_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        cliente_uploads = os.path.join(UPLOADS_DIR, cadastro_id)
        cliente_gerados = os.path.join(GERADOS_DIR, cadastro_id)
        
        if os.path.exists(cliente_uploads):
            shutil.rmtree(cliente_uploads)
        if os.path.exists(cliente_gerados):
            shutil.rmtree(cliente_gerados)
        
        logger.info(f"Cadastro {cadastro_id} deletado com sucesso")
        return {"success": True, "message": "Cadastro deletado com sucesso"}
    except Exception as e:
        logger.error(f"Erro ao deletar cadastro: {e}")
        raise HTTPException(status_code=500, detail="Erro ao deletar cadastro")

@app.put("/api/cadastros/{cadastro_id}/validar")
def validar_cadastro(cadastro_id: str):
    """Marca cadastro como validado."""
    if atualizar_status(cadastro_id, "validado"):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Cadastro não encontrado")

@app.post("/api/cadastros/{cadastro_id}/gerar-documentos")
def gerar_documentos(cadastro_id: str):
    """Gera documentos SEM enviar por e-mail."""
    logger.info(f"Gerando documentos para cadastro: {cadastro_id}")
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    try:
        dados = cadastro["dados"]
        arquivos = gerador.gerar_todos(dados, cadastro_id)
        logger.info(f"Documentos gerados: {arquivos}")
        
        cadastro["status"] = "documentos_gerados"
        cadastro["arquivos_gerados"] = arquivos
        salvar_cadastro(cadastro)
        
        return {
            "success": True,
            "arquivos": arquivos,
            "message": "Documentos gerados com sucesso!"
        }
    except Exception as e:
        logger.error(f"Erro ao gerar documentos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cadastros/{cadastro_id}/enviar-email")
async def enviar_email_documentos(
    cadastro_id: str,
    assunto: str = Form(default="Seus Documentos - Vaucher & Álvares Advogados"),
    mensagem: str = Form(default=""),
    arquivos: List[UploadFile] = File(default=[])
):
    """Envia documentos por e-mail."""
    logger.info(f"Enviando e-mail para cadastro: {cadastro_id}")
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    dados = cadastro["dados"]
    anexos_email = []
    
    if arquivos:
        for arquivo in arquivos:
            if arquivo.filename:
                logger.info(f"Processando anexo: {arquivo.filename}")
                conteudo = await arquivo.read()
                anexos_email.append({
                    "filename": arquivo.filename,
                    "content": base64.b64encode(conteudo).decode("utf-8")
                })
    
    if not anexos_email:
        raise HTTPException(status_code=400, detail="Nenhum arquivo selecionado para envio")
    
    PORTAL_URL = os.getenv("PORTAL_URL", "https://cadastro.vaucherealvares.com")
    link_envio = f"{PORTAL_URL}/enviar-assinados?id={cadastro_id}"
    
    mensagem_html = f"<p>{mensagem}</p>" if mensagem else ""
    
    conteudo = f"""
        <p style="font-size: 16px;">Prezado(a) <strong>{dados['nome']}</strong>,</p>
        <p>Seguem em anexo os documentos para sua análise e assinatura.</p>
        {mensagem_html}
        <p>Por favor, leia atentamente os documentos. Após assiná-los, devolva-os por uma das opções abaixo:</p>
        
        <div style="background-color: #f0f0f0; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0 0 10px 0;"><strong>📋 Seu código de protocolo:</strong></p>
            <p style="font-size: 20px; font-family: monospace; background: #fff; padding: 10px; border-radius: 5px; text-align: center; margin: 0; color: #8B1538; font-weight: bold;">{cadastro_id}</p>
        </div>
        
        <div style="background-color: #e8f5e9; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0 0 15px 0;"><strong>📤 Como devolver os documentos assinados:</strong></p>
            
            <p style="margin: 0 0 10px 0;"><strong>Opção 1 - Pelo nosso portal:</strong></p>
            <p style="margin: 0 0 15px 0;">
                <a href="{link_envio}" style="background-color: #8B1538; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Clique aqui para enviar os documentos assinados
                </a>
            </p>
            
            <p style="margin: 0 0 10px 0;"><strong>Opção 2 - Por e-mail:</strong></p>
            <p style="margin: 0;">Responda este e-mail com os documentos anexados ou envie para:<br>
            <a href="mailto:atendimento@vaucherealvares.com" style="color: #8B1538; font-weight: bold;">atendimento@vaucherealvares.com</a></p>
        </div>
        
        <div style="background-color: #fff3e0; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="margin: 0;"><strong>📎 Anexos neste e-mail:</strong> {len(anexos_email)} documento(s)</p>
        </div>
        
        <p><strong>Dúvidas?</strong> Entre em contato conosco pelos canais abaixo.</p>
    """
    corpo_html = criar_email_html(conteudo)
    
    sucesso = await enviar_email_resend(dados["email"], assunto, corpo_html, anexos_email)
    
    if sucesso:
        cadastro["status"] = "enviado"
        salvar_cadastro(cadastro)
        return {"success": True, "message": f"E-mail enviado para {dados['email']} com {len(anexos_email)} anexo(s)"}
    else:
        raise HTTPException(status_code=500, detail="Erro ao enviar e-mail. Verifique os logs.")

@app.get("/api/cadastros/exportar/excel")
def exportar_cadastros_excel():
    """Exporta todos os cadastros para uma planilha Excel."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        raise HTTPException(status_code=500, detail="Biblioteca openpyxl não instalada")
    
    cadastros = carregar_cadastros()
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Cadastros"
    
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="8B1538", end_color="8B1538", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    headers = [
        "ID", "Data Cadastro", "Status", "Nome", "CPF", "RG", 
        "Data Nascimento", "Estado Civil", "Nacionalidade", "Profissão",
        "Endereço", "E-mail", "Telefone", "Tipo de Demanda",
        "Objeto do Contrato", "Poderes Específicos", "Observações"
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    tipos_demanda = {
        'adicional_insalubridade': 'Adicional de Insalubridade',
        'adicional_periculosidade': 'Adicional de Periculosidade',
        'desvio_funcao': 'Desvio de Função',
        'progressao_funcional': 'Progressão Funcional',
        'revisao_aposentadoria': 'Revisão de Aposentadoria',
        'licenca_premio': 'Licença Prêmio',
        'ferias_nao_gozadas': 'Férias Não Gozadas',
        'horas_extras': 'Horas Extras',
        'reintegracao': 'Reintegração',
        'outro': 'Outro'
    }
    
    status_map = {
        'pendente': 'Pendente',
        'validado': 'Validado',
        'documentos_gerados': 'Documentos Gerados',
        'enviado': 'Enviado',
        'assinado': 'Documentos Assinados Recebidos'
    }
    
    for row, cadastro in enumerate(cadastros, 2):
        dados = cadastro.get("dados", {})
        
        values = [
            cadastro.get("id", ""),
            cadastro.get("data", ""),
            status_map.get(cadastro.get("status", ""), cadastro.get("status", "")),
            dados.get("nome", ""),
            dados.get("cpf", ""),
            dados.get("rg", ""),
            dados.get("data_nascimento", ""),
            dados.get("estado_civil", ""),
            dados.get("nacionalidade", ""),
            dados.get("profissao", ""),
            dados.get("endereco_completo", ""),
            dados.get("email", ""),
            dados.get("telefone", ""),
            tipos_demanda.get(dados.get("tipo_demanda", ""), dados.get("tipo_demanda", "")),
            dados.get("objeto_contrato", ""),
            dados.get("poderes_especificos", ""),
            dados.get("observacoes", "")
        ]
        
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    
    column_widths = [12, 12, 15, 30, 15, 15, 12, 12, 12, 20, 40, 30, 15, 25, 50, 50, 30]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width
    
    ws.freeze_panes = "A2"
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"cadastros_vaucher_alvares_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/cadastros/{cadastro_id}/download/{tipo}")
def download_documento(cadastro_id: str, tipo: str):
    """Faz download de um documento gerado."""
    cadastro = buscar_cadastro(cadastro_id)
    
    if cadastro and cadastro.get("arquivos_gerados"):
        arquivo = cadastro["arquivos_gerados"].get(tipo)
        if arquivo and os.path.exists(arquivo):
            return FileResponse(
                arquivo,
                filename=os.path.basename(arquivo),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
    
    raise HTTPException(status_code=404, detail="Documento não encontrado")

@app.post("/api/cadastros/{cadastro_id}/enviar-assinados")
async def receber_documentos_assinados(cadastro_id: str, arquivos: List[UploadFile] = File(...)):
    """Recebe documentos assinados enviados pelo cliente."""
    logger.info(f"ENVIAR-ASSINADOS: cadastro_id={cadastro_id}, arquivos={len(arquivos)}")
    
    # Buscar cadastro
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    # Criar pasta para documentos assinados
    pasta_assinados = f"/app/uploads/documentos_assinados/{cadastro_id}"
    os.makedirs(pasta_assinados, exist_ok=True)
    
    # Salvar arquivos
    arquivos_salvos = []
    for arquivo in arquivos:
        nome_arquivo = arquivo.filename
        caminho = f"{pasta_assinados}/{nome_arquivo}"
        
        with open(caminho, "wb") as f:
            conteudo = await arquivo.read()
            f.write(conteudo)
        
        arquivos_salvos.append(nome_arquivo)
        logger.info(f"Arquivo salvo: {caminho}")
    
    # Atualizar cadastro no banco
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor()
        
        # Pegar documentos assinados existentes
        docs_existentes = cadastro.get("documentos_assinados", []) or []
        docs_atualizados = docs_existentes + arquivos_salvos
        
        cur.execute("""
            UPDATE cadastros 
            SET documentos_assinados = %s,
                data_assinatura = NOW(),
                status = 'assinado'
            WHERE id = %s
        """, (json.dumps(docs_atualizados), cadastro_id))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Cadastro {cadastro_id} atualizado com {len(arquivos_salvos)} documentos assinados")
        
        return {
            "success": True,
            "message": f"{len(arquivos_salvos)} documento(s) recebido(s) com sucesso",
            "arquivos": arquivos_salvos
        }
    
    except Exception as e:
        logger.error(f"Erro ao salvar documentos assinados: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar documentos")

# --- UPLOAD DE DOCUMENTOS DO CLIENTE ---

@app.post("/api/cadastros/{cadastro_id}/upload")
async def upload_documento(cadastro_id: str, arquivo: UploadFile = File(...)):
    """Recebe upload de documento do cliente."""
    logger.info(f"Upload recebido para cadastro {cadastro_id}: {arquivo.filename}")
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    cliente_dir = os.path.join(UPLOADS_DIR, cadastro_id)
    os.makedirs(cliente_dir, exist_ok=True)
    
    file_path = os.path.join(cliente_dir, arquivo.filename)
    with open(file_path, "wb") as f:
        content = await arquivo.read()
        f.write(content)
    
    if arquivo.filename not in cadastro["documentos"]:
        cadastro["documentos"].append(arquivo.filename)
    salvar_cadastro(cadastro)
    
    return {"success": True, "filename": arquivo.filename}

@app.get("/api/cadastros/{cadastro_id}/uploads/{filename}")
def download_upload_cliente(cadastro_id: str, filename: str):
    """Faz download de um arquivo enviado pelo cliente."""
    file_path = os.path.join(UPLOADS_DIR, cadastro_id, filename)
    
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename, media_type="application/octet-stream")
    
    raise HTTPException(status_code=404, detail="Arquivo não encontrado")

# ============================================
# MÓDULO FINANCEIRO
# ============================================

@app.get("/api/cadastros/{cadastro_id}/financeiro")
def obter_financeiro(cadastro_id: str):
    """Obtém dados financeiros de um cadastro."""
    financeiro = buscar_financeiro(cadastro_id)
    if financeiro:
        return financeiro
    return {
        "cadastro_id": cadastro_id,
        "numero_processo": "",
        "vara_tribunal": "",
        "percentual_honorarios": 20,
        "valor_credito_cliente": 0,
        "depositos": [],
        "sucumbencias": [],
        "retencoes": [],
        "observacoes": ""
    }

@app.post("/api/cadastros/{cadastro_id}/financeiro")
def salvar_dados_financeiro(cadastro_id: str, dados: FinanceiroData):
    """Salva ou atualiza dados financeiros de um cadastro."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    if salvar_financeiro(cadastro_id, dados.dict()):
        return {"success": True, "message": "Dados financeiros salvos com sucesso"}
    raise HTTPException(status_code=500, detail="Erro ao salvar dados financeiros")

@app.get("/api/cadastros/{cadastro_id}/prestacao-contas")
def gerar_documento_prestacao_contas(cadastro_id: str):
    """Gera documento de prestação de contas."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    financeiro = buscar_financeiro(cadastro_id)
    if not financeiro:
        raise HTTPException(status_code=400, detail="Dados financeiros não encontrados.")
    
    depositos = financeiro.get("depositos", [])
    if not depositos or len(depositos) == 0:
        raise HTTPException(status_code=400, detail="Adicione pelo menos um depósito.")
    
    try:
        caminho_arquivo = gerador.gerar_prestacao_contas(
            dados_cliente=cadastro["dados"],
            financeiro=financeiro,
            cadastro_id=cadastro_id
        )
        
        nome_arquivo = os.path.basename(caminho_arquivo)
        
        return FileResponse(
            caminho_arquivo,
            filename=nome_arquivo,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except Exception as e:
        logger.error(f"Erro ao gerar prestação de contas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ÁREA DO CLIENTE - DEVOLUÇÃO DE DOCUMENTOS (EXISTENTE)
# ============================================

@app.get("/api/cliente/cadastro/{cadastro_id}")
def cliente_ver_cadastro_publico(cadastro_id: str):
    """Cliente visualiza seu próprio cadastro (sem autenticação, mas limitado)."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    return {
        "id": cadastro["id"],
        "nome": cadastro["dados"].get("nome", ""),
        "email": cadastro["dados"].get("email", ""),
        "status": cadastro["status"],
        "data": cadastro["data"],
        "tipo_demanda": cadastro["dados"].get("tipo_demanda", ""),
        "documentos_assinados": cadastro.get("documentos_assinados", [])
    }

@app.post("/api/cliente/{cadastro_id}/enviar-assinados")
async def cliente_enviar_documentos_assinados(
    cadastro_id: str,
    arquivos: List[UploadFile] = File(...)
):
    """Cliente envia documentos assinados."""
    logger.info(f"Cliente enviando documentos assinados para cadastro: {cadastro_id}")
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    if cadastro["status"] not in ["enviado", "assinado"]:
        raise HTTPException(status_code=400, detail="Você ainda não recebeu os documentos para assinar")
    
    cliente_assinados_dir = os.path.join(UPLOADS_DIR, cadastro_id, "assinados")
    os.makedirs(cliente_assinados_dir, exist_ok=True)
    
    arquivos_salvos = []
    
    for arquivo in arquivos:
        if arquivo.filename:
            nome_arquivo = f"ASSINADO_{arquivo.filename}"
            file_path = os.path.join(cliente_assinados_dir, nome_arquivo)
            
            with open(file_path, "wb") as f:
                content = await arquivo.read()
                f.write(content)
            
            arquivos_salvos.append(nome_arquivo)
            logger.info(f"Documento assinado salvo: {nome_arquivo}")
    
    if not arquivos_salvos:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")
    
    if "documentos_assinados" not in cadastro:
        cadastro["documentos_assinados"] = []
    
    cadastro["documentos_assinados"].extend(arquivos_salvos)
    cadastro["status"] = "assinado"
    cadastro["data_assinatura"] = datetime.now().isoformat()
    salvar_cadastro(cadastro)
    
    try:
        dados = cadastro["dados"]
        conteudo = f"""
            <p style="font-size: 16px;"><strong>📝 Novos documentos assinados recebidos!</strong></p>
            <p>O cliente <strong>{dados['nome']}</strong> enviou os documentos assinados.</p>
            <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Cadastro:</strong> {cadastro_id}</p>
                <p style="margin: 0;"><strong>E-mail:</strong> {dados['email']}</p>
                <p style="margin: 0;"><strong>Telefone:</strong> {dados['telefone']}</p>
                <p style="margin: 0;"><strong>Arquivos:</strong> {len(arquivos_salvos)} documento(s)</p>
            </div>
            <p>Acesse o painel administrativo para visualizar os documentos.</p>
        """
        corpo_html = criar_email_html(conteudo)
        
        await enviar_email_resend(
            FROM_EMAIL,
            f"📝 Documentos Assinados - {dados['nome']}",
            corpo_html
        )
    except Exception as e:
        logger.error(f"Erro ao notificar escritório: {e}")
    
    return {
        "success": True,
        "message": f"{len(arquivos_salvos)} documento(s) enviado(s) com sucesso!",
        "arquivos": arquivos_salvos
    }

@app.get("/api/cadastros/{cadastro_id}/assinados/{filename}")
def download_documento_assinado(cadastro_id: str, filename: str):
    """Faz download de um documento assinado pelo cliente."""
    file_path = os.path.join(UPLOADS_DIR, cadastro_id, "assinados", filename)
    
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename, media_type="application/octet-stream")
    
    raise HTTPException(status_code=404, detail="Arquivo não encontrado")


# ============================================
# PORTAL DO CLIENTE - FUNÇÕES DO BANCO
# ============================================

def criar_cliente_auth(cadastro_id: str, senha: str) -> bool:
    """Cria autenticação para um cliente."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        senha_hash = hash_senha(senha)
        cur.execute("""
            INSERT INTO clientes_auth (cadastro_id, senha_hash)
            VALUES (%s, %s)
            ON CONFLICT (cadastro_id) DO UPDATE SET
                senha_hash = EXCLUDED.senha_hash,
                primeiro_acesso = TRUE,
                ativo = TRUE
        """, (cadastro_id, senha_hash))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao criar auth cliente: {e}")
        return False

def buscar_cliente_auth(cadastro_id: str) -> dict:
    """Busca autenticação de um cliente."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT ca.*, c.dados->>'email' as email, c.dados->>'nome' as nome
            FROM clientes_auth ca
            JOIN cadastros c ON c.id = ca.cadastro_id
            WHERE ca.cadastro_id = %s AND ca.ativo = TRUE
        """, (cadastro_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar auth cliente: {e}")
        return None

def buscar_cliente_por_email(email: str) -> dict:
    """Busca cliente pelo email."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT ca.*, c.dados->>'email' as email, c.dados->>'nome' as nome, c.id as cadastro_id
            FROM cadastros c
            LEFT JOIN clientes_auth ca ON c.id = ca.cadastro_id
            WHERE c.dados->>'email' = %s
        """, (email,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar cliente por email: {e}")
        return None

def atualizar_senha_cliente(cadastro_id: str, nova_senha: str) -> bool:
    """Atualiza a senha de um cliente."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        senha_hash = hash_senha(nova_senha)
        cur.execute("""
            UPDATE clientes_auth 
            SET senha_hash = %s, primeiro_acesso = FALSE
            WHERE cadastro_id = %s
        """, (senha_hash, cadastro_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar senha cliente: {e}")
        return False

def registrar_acesso_cliente(cadastro_id: str):
    """Registra o último acesso do cliente."""
    conn = get_db()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE clientes_auth 
            SET ultimo_acesso = CURRENT_TIMESTAMP
            WHERE cadastro_id = %s
        """, (cadastro_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao registrar acesso: {e}")


# ============================================
# PORTAL DO CLIENTE - FUNÇÕES PROCESSO
# ============================================
# ============================================
# FUNÇÕES CRUD - PROCESSOS (MÚLTIPLOS)
# ============================================

def criar_processo(cadastro_id: str, dados: dict) -> int:
    """Cria um novo processo para o cliente."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO processos (cadastro_id, numero_processo, tipo_acao, vara_tribunal, 
                                   fase, reu, valor_causa, data_distribuicao, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            cadastro_id,
            dados.get("numero_processo"),
            dados.get("tipo_acao"),
            dados.get("vara_tribunal"),
            dados.get("fase", "Inicial"),
            dados.get("reu"),
            dados.get("valor_causa"),
            dados.get("data_distribuicao") if dados.get("data_distribuicao") else None,
            dados.get("observacoes")
        ))
        processo_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return processo_id
    except Exception as e:
        logger.error(f"Erro ao criar processo: {e}")
        return None

def listar_processos(cadastro_id: str) -> list:
    """Lista todos os processos de um cliente."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM processos 
            WHERE cadastro_id = %s 
            ORDER BY criado_em DESC
        """, (cadastro_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        processos = []
        for row in rows:
            processos.append({
                "id": row["id"],
                "cadastro_id": row["cadastro_id"],
                "numero_processo": row["numero_processo"] or "",
                "tipo_acao": row["tipo_acao"] or "",
                "vara_tribunal": row["vara_tribunal"] or "",
                "fase": row["fase"] or "Inicial",
                "reu": row["reu"] or "",
                "valor_causa": float(row["valor_causa"]) if row["valor_causa"] else 0,
                "data_distribuicao": row["data_distribuicao"].isoformat() if row["data_distribuicao"] else None,
                "status": row["status"] or "ativo",
                "observacoes": row["observacoes"] or ""
            })
        return processos
    except Exception as e:
        logger.error(f"Erro ao listar processos: {e}")
        return []

def buscar_processo(processo_id: int) -> dict:
    """Busca um processo específico."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM processos WHERE id = %s", (processo_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            return {
                "id": row["id"],
                "cadastro_id": row["cadastro_id"],
                "numero_processo": row["numero_processo"] or "",
                "tipo_acao": row["tipo_acao"] or "",
                "vara_tribunal": row["vara_tribunal"] or "",
                "fase": row["fase"] or "Inicial",
                "reu": row["reu"] or "",
                "valor_causa": float(row["valor_causa"]) if row["valor_causa"] else 0,
                "data_distribuicao": row["data_distribuicao"].isoformat() if row["data_distribuicao"] else None,
                "status": row["status"] or "ativo",
                "observacoes": row["observacoes"] or ""
            }
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar processo: {e}")
        return None

def atualizar_processo(processo_id: int, dados: dict) -> bool:
    """Atualiza um processo existente."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE processos SET
                numero_processo = %s,
                tipo_acao = %s,
                vara_tribunal = %s,
                fase = %s,
                reu = %s,
                valor_causa = %s,
                data_distribuicao = %s,
                status = %s,
                observacoes = %s,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (
            dados.get("numero_processo"),
            dados.get("tipo_acao"),
            dados.get("vara_tribunal"),
            dados.get("fase"),
            dados.get("reu"),
            dados.get("valor_causa"),
            dados.get("data_distribuicao") if dados.get("data_distribuicao") else None,
            dados.get("status", "ativo"),
            dados.get("observacoes"),
            processo_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar processo: {e}")
        return False

def deletar_processo(processo_id: int) -> bool:
    """Deleta um processo."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM processos WHERE id = %s", (processo_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar processo: {e}")
        return False

# ============================================
# FUNÇÕES CRUD - ANDAMENTOS DE PROCESSO
# ============================================

def criar_andamento_processo(processo_id: int, data: str, descricao: str, visivel: bool = True) -> int:
    """Cria um andamento para um processo."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO processo_andamentos (processo_id, data, descricao, visivel_cliente)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (processo_id, data, descricao, visivel))
        andamento_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return andamento_id
    except Exception as e:
        logger.error(f"Erro ao criar andamento processo: {e}")
        return None

def listar_andamentos_processo(processo_id: int, apenas_visiveis: bool = False) -> list:
    """Lista andamentos de um processo."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if apenas_visiveis:
            cur.execute("""
                SELECT * FROM processo_andamentos 
                WHERE processo_id = %s AND visivel_cliente = TRUE
                ORDER BY data DESC, criado_em DESC
            """, (processo_id,))
        else:
            cur.execute("""
                SELECT * FROM processo_andamentos 
                WHERE processo_id = %s 
                ORDER BY data DESC, criado_em DESC
            """, (processo_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return [{
            "id": row["id"],
            "processo_id": row["processo_id"],
            "data": row["data"].isoformat() if row["data"] else None,
            "descricao": row["descricao"],
            "visivel_cliente": row["visivel_cliente"]
        } for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar andamentos processo: {e}")
        return []

def deletar_andamento_processo(andamento_id: int) -> bool:
    """Deleta um andamento de processo."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM processo_andamentos WHERE id = %s", (andamento_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar andamento processo: {e}")
        return False

# ============================================
# FUNÇÕES CRUD - CONTRATOS DE HONORÁRIOS
# ============================================

def criar_contrato_honorarios(cadastro_id: str, dados: dict) -> int:
    """Cria um contrato de honorários."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO contratos_honorarios (
                cadastro_id, processo_id, tipo, descricao, valor_total, 
                num_parcelas, valor_mensal, dia_vencimento, percentual_exito,
                data_inicio, observacoes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            cadastro_id,
            dados.get("processo_id"),
            dados.get("tipo"),
            dados.get("descricao"),
            dados.get("valor_total"),
            dados.get("num_parcelas", 1),
            dados.get("valor_mensal"),
            dados.get("dia_vencimento", 10),
            dados.get("percentual_exito"),
            dados.get("data_inicio") if dados.get("data_inicio") else None,
            dados.get("observacoes")
        ))
        contrato_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        # Gerar parcelas automaticamente se for fixo ou parcelado
        if dados.get("tipo") in ["fixo", "parcelado"]:
            gerar_parcelas_contrato(contrato_id, dados)
        
        return contrato_id
    except Exception as e:
        logger.error(f"Erro ao criar contrato: {e}")
        return None

def gerar_parcelas_contrato(contrato_id: int, dados: dict):
    """Gera parcelas para um contrato."""
    from datetime import date
    from dateutil.relativedelta import relativedelta
    
    conn = get_db()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        
        valor_total = float(dados.get("valor_total", 0))
        num_parcelas = int(dados.get("num_parcelas", 1))
        valor_parcela = valor_total / num_parcelas
        dia_vencimento = int(dados.get("dia_vencimento", 10))
        
        data_inicio = dados.get("data_inicio")
        if data_inicio:
            if isinstance(data_inicio, str):
                data_base = date.fromisoformat(data_inicio)
            else:
                data_base = data_inicio
        else:
            data_base = date.today()
        
        for i in range(num_parcelas):
            vencimento = data_base + relativedelta(months=i)
            try:
                vencimento = vencimento.replace(day=dia_vencimento)
            except ValueError:
                # Se o dia não existe no mês, usa o último dia
                next_month = vencimento + relativedelta(months=1, day=1)
                vencimento = next_month - relativedelta(days=1)
            
            cur.execute("""
                INSERT INTO parcelas (contrato_id, numero, valor, vencimento)
                VALUES (%s, %s, %s, %s)
            """, (contrato_id, i + 1, valor_parcela, vencimento))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao gerar parcelas: {e}")

def listar_contratos(cadastro_id: str) -> list:
    """Lista contratos de um cliente."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT c.*, p.numero_processo as processo_numero
            FROM contratos_honorarios c
            LEFT JOIN processos p ON c.processo_id = p.id
            WHERE c.cadastro_id = %s
            ORDER BY c.criado_em DESC
        """, (cadastro_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        contratos = []
        for row in rows:
            contrato = {
                "id": row["id"],
                "cadastro_id": row["cadastro_id"],
                "processo_id": row["processo_id"],
                "processo_numero": row["processo_numero"] or "",
                "tipo": row["tipo"],
                "descricao": row["descricao"] or "",
                "valor_total": float(row["valor_total"]) if row["valor_total"] else 0,
                "num_parcelas": row["num_parcelas"] or 1,
                "valor_mensal": float(row["valor_mensal"]) if row["valor_mensal"] else 0,
                "dia_vencimento": row["dia_vencimento"] or 10,
                "percentual_exito": float(row["percentual_exito"]) if row["percentual_exito"] else 0,
                "data_inicio": row["data_inicio"].isoformat() if row["data_inicio"] else None,
                "status": row["status"] or "ativo",
                "observacoes": row["observacoes"] or ""
            }
            # Buscar parcelas
            contrato["parcelas"] = listar_parcelas(row["id"])
            contratos.append(contrato)
        
        return contratos
    except Exception as e:
        logger.error(f"Erro ao listar contratos: {e}")
        return []

def buscar_contrato(contrato_id: int) -> dict:
    """Busca um contrato específico."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT c.*, p.numero_processo as processo_numero
            FROM contratos_honorarios c
            LEFT JOIN processos p ON c.processo_id = p.id
            WHERE c.id = %s
        """, (contrato_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            contrato = {
                "id": row["id"],
                "cadastro_id": row["cadastro_id"],
                "processo_id": row["processo_id"],
                "processo_numero": row["processo_numero"] or "",
                "tipo": row["tipo"],
                "descricao": row["descricao"] or "",
                "valor_total": float(row["valor_total"]) if row["valor_total"] else 0,
                "num_parcelas": row["num_parcelas"] or 1,
                "valor_mensal": float(row["valor_mensal"]) if row["valor_mensal"] else 0,
                "dia_vencimento": row["dia_vencimento"] or 10,
                "percentual_exito": float(row["percentual_exito"]) if row["percentual_exito"] else 0,
                "data_inicio": row["data_inicio"].isoformat() if row["data_inicio"] else None,
                "status": row["status"] or "ativo",
                "observacoes": row["observacoes"] or ""
            }
            contrato["parcelas"] = listar_parcelas(row["id"])
            return contrato
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar contrato: {e}")
        return None

def atualizar_contrato(contrato_id: int, dados: dict) -> bool:
    """Atualiza um contrato."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE contratos_honorarios SET
                processo_id = %s,
                tipo = %s,
                descricao = %s,
                valor_total = %s,
                num_parcelas = %s,
                valor_mensal = %s,
                dia_vencimento = %s,
                percentual_exito = %s,
                data_inicio = %s,
                status = %s,
                observacoes = %s,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (
            dados.get("processo_id"),
            dados.get("tipo"),
            dados.get("descricao"),
            dados.get("valor_total"),
            dados.get("num_parcelas", 1),
            dados.get("valor_mensal"),
            dados.get("dia_vencimento", 10),
            dados.get("percentual_exito"),
            dados.get("data_inicio") if dados.get("data_inicio") else None,
            dados.get("status", "ativo"),
            dados.get("observacoes"),
            contrato_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar contrato: {e}")
        return False

def deletar_contrato(contrato_id: int) -> bool:
    """Deleta um contrato e suas parcelas."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM contratos_honorarios WHERE id = %s", (contrato_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar contrato: {e}")
        return False

# ============================================
# FUNÇÕES CRUD - PARCELAS
# ============================================

def listar_parcelas(contrato_id: int) -> list:
    """Lista parcelas de um contrato."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT p.*, 
                   (SELECT COUNT(*) FROM comprovantes WHERE parcela_id = p.id) as tem_comprovante
            FROM parcelas p
            WHERE p.contrato_id = %s
            ORDER BY p.numero
        """, (contrato_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return [{
            "id": row["id"],
            "contrato_id": row["contrato_id"],
            "numero": row["numero"],
            "valor": float(row["valor"]) if row["valor"] else 0,
            "vencimento": row["vencimento"].isoformat() if row["vencimento"] else None,
            "status": row["status"] or "pendente",
            "data_pagamento": row["data_pagamento"].isoformat() if row["data_pagamento"] else None,
            "tem_comprovante": row["tem_comprovante"] > 0
        } for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar parcelas: {e}")
        return []

def atualizar_parcela(parcela_id: int, dados: dict) -> bool:
    """Atualiza uma parcela."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE parcelas SET
                valor = %s,
                vencimento = %s,
                status = %s,
                data_pagamento = %s
            WHERE id = %s
        """, (
            dados.get("valor"),
            dados.get("vencimento"),
            dados.get("status"),
            dados.get("data_pagamento") if dados.get("data_pagamento") else None,
            parcela_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar parcela: {e}")
        return False

def marcar_parcela_paga(parcela_id: int) -> bool:
    """Marca uma parcela como paga."""
    from datetime import date
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE parcelas SET status = 'pago', data_pagamento = %s WHERE id = %s
        """, (date.today(), parcela_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao marcar parcela paga: {e}")
        return False

# ============================================
# FUNÇÕES CRUD - COMPROVANTES
# ============================================

def criar_comprovante(parcela_id: int, arquivo_nome: str, arquivo_path: str) -> int:
    """Cria um registro de comprovante."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO comprovantes (parcela_id, arquivo_nome, arquivo_path)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (parcela_id, arquivo_nome, arquivo_path))
        comprovante_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return comprovante_id
    except Exception as e:
        logger.error(f"Erro ao criar comprovante: {e}")
        return None

def listar_comprovantes_pendentes() -> list:
    """Lista todos os comprovantes pendentes de verificação."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT cp.*, p.numero, p.valor, p.vencimento,
                   c.descricao as contrato_descricao, c.cadastro_id,
                   ca.dados->>'nome' as cliente_nome
            FROM comprovantes cp
            JOIN parcelas p ON cp.parcela_id = p.id
            JOIN contratos_honorarios c ON p.contrato_id = c.id
            JOIN cadastros ca ON c.cadastro_id = ca.id
            WHERE cp.status = 'pendente'
            ORDER BY cp.enviado_em DESC
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return [{
            "id": row["id"],
            "parcela_id": row["parcela_id"],
            "arquivo_nome": row["arquivo_nome"],
            "arquivo_path": row["arquivo_path"],
            "enviado_em": row["enviado_em"].isoformat() if row["enviado_em"] else None,
            "parcela_numero": row["numero"],
            "parcela_valor": float(row["valor"]) if row["valor"] else 0,
            "parcela_vencimento": row["vencimento"].isoformat() if row["vencimento"] else None,
            "contrato_descricao": row["contrato_descricao"],
            "cadastro_id": row["cadastro_id"],
            "cliente_nome": row["cliente_nome"]
        } for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar comprovantes: {e}")
        return []

def aprovar_comprovante(comprovante_id: int, admin_email: str) -> bool:
    """Aprova um comprovante e marca a parcela como paga."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Buscar parcela_id
        cur.execute("SELECT parcela_id FROM comprovantes WHERE id = %s", (comprovante_id,))
        row = cur.fetchone()
        if not row:
            return False
        
        parcela_id = row[0]
        
        # Atualizar comprovante
        cur.execute("""
            UPDATE comprovantes SET 
                status = 'aprovado', 
                verificado_em = CURRENT_TIMESTAMP,
                verificado_por = %s
            WHERE id = %s
        """, (admin_email, comprovante_id))
        
        # Marcar parcela como paga
        cur.execute("""
            UPDATE parcelas SET status = 'pago', data_pagamento = CURRENT_DATE WHERE id = %s
        """, (parcela_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao aprovar comprovante: {e}")
        return False

def rejeitar_comprovante(comprovante_id: int, admin_email: str, motivo: str = None) -> bool:
    """Rejeita um comprovante."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE comprovantes SET 
                status = 'rejeitado', 
                verificado_em = CURRENT_TIMESTAMP,
                verificado_por = %s,
                observacoes = %s
            WHERE id = %s
        """, (admin_email, motivo, comprovante_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao rejeitar comprovante: {e}")
        return False


# ============================================
# FUNÇÕES DO BANCO - DOCUMENTOS ADMIN
# ============================================

def criar_documento_admin(cadastro_id: str, nome_arquivo: str, nome_original: str, arquivo_path: str, descricao: str, admin_email: str) -> int:
    """Cria um registro de documento enviado pelo admin."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO documentos_admin (cadastro_id, nome_arquivo, nome_original, arquivo_path, descricao, enviado_por)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (cadastro_id, nome_arquivo, nome_original, arquivo_path, descricao, admin_email))
        doc_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return doc_id
    except Exception as e:
        logger.error(f"Erro ao criar documento admin: {e}")
        return None

def listar_documentos_admin(cadastro_id: str) -> list:
    """Lista documentos enviados pelo admin para um cliente."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, nome_arquivo, nome_original, descricao, enviado_por, criado_em
            FROM documentos_admin
            WHERE cadastro_id = %s
            ORDER BY criado_em DESC
        """, (cadastro_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar documentos admin: {e}")
        return []

def buscar_documento_admin(doc_id: int) -> dict:
    """Busca um documento admin específico."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM documentos_admin WHERE id = %s", (doc_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar documento admin: {e}")
        return None

def deletar_documento_admin(doc_id: int) -> bool:
    """Deleta um documento admin."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Buscar caminho do arquivo
        cur.execute("SELECT arquivo_path FROM documentos_admin WHERE id = %s", (doc_id,))
        row = cur.fetchone()
        
        if row and row["arquivo_path"]:
            # Deletar arquivo físico
            if os.path.exists(row["arquivo_path"]):
                os.remove(row["arquivo_path"])
        
        # Deletar registro
        cur.execute("DELETE FROM documentos_admin WHERE id = %s", (doc_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar documento admin: {e}")
        return False


# ============================================
# FUNÇÕES DO BANCO - DOCUMENTOS EXTRAS (CLIENTE)
# ============================================

def criar_documento_extra(cadastro_id: str, nome_arquivo: str, nome_original: str, arquivo_path: str, descricao: str) -> int:
    """Cria um registro de documento extra enviado pelo cliente."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO documentos_extras (cadastro_id, nome_arquivo, nome_original, arquivo_path, descricao)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (cadastro_id, nome_arquivo, nome_original, arquivo_path, descricao))
        doc_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return doc_id
    except Exception as e:
        logger.error(f"Erro ao criar documento extra: {e}")
        return None

def listar_documentos_extras(cadastro_id: str) -> list:
    """Lista documentos extras enviados pelo cliente."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, nome_arquivo, nome_original, descricao, criado_em
            FROM documentos_extras
            WHERE cadastro_id = %s
            ORDER BY criado_em DESC
        """, (cadastro_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar documentos extras: {e}")
        return []

def buscar_documento_extra(doc_id: int) -> dict:
    """Busca um documento extra específico."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM documentos_extras WHERE id = %s", (doc_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar documento extra: {e}")
        return None

def deletar_documento_extra(doc_id: int) -> bool:
    """Deleta um documento extra."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Buscar caminho do arquivo
        cur.execute("SELECT arquivo_path FROM documentos_extras WHERE id = %s", (doc_id,))
        row = cur.fetchone()
        
        if row and row["arquivo_path"]:
            # Deletar arquivo físico
            if os.path.exists(row["arquivo_path"]):
                os.remove(row["arquivo_path"])
        
        # Deletar registro
        cur.execute("DELETE FROM documentos_extras WHERE id = %s", (doc_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar documento extra: {e}")
        return False


def buscar_processo_info(cadastro_id: str) -> dict:
    """Busca informações do processo de um cliente."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM processo_info WHERE cadastro_id = %s", (cadastro_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            return {
                "cadastro_id": row["cadastro_id"],
                "numero_processo": row["numero_processo"] or "",
                "vara_tribunal": row["vara_tribunal"] or "",
                "fase": row["fase"] or "Inicial",
                "data_distribuicao": row["data_distribuicao"].isoformat() if row["data_distribuicao"] else None,
                "valor_causa": float(row["valor_causa"]) if row["valor_causa"] else 0,
                "reu": row["reu"] or "",
                "observacoes": row["observacoes"] or ""
            }
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar processo info: {e}")
        return None

def salvar_processo_info(cadastro_id: str, dados: dict) -> bool:
    """Salva ou atualiza informações do processo."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO processo_info (cadastro_id, numero_processo, vara_tribunal, fase, 
                                       data_distribuicao, valor_causa, reu, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cadastro_id) DO UPDATE SET
                numero_processo = EXCLUDED.numero_processo,
                vara_tribunal = EXCLUDED.vara_tribunal,
                fase = EXCLUDED.fase,
                data_distribuicao = EXCLUDED.data_distribuicao,
                valor_causa = EXCLUDED.valor_causa,
                reu = EXCLUDED.reu,
                observacoes = EXCLUDED.observacoes,
                atualizado_em = CURRENT_TIMESTAMP
        """, (
            cadastro_id,
            dados.get("numero_processo"),
            dados.get("vara_tribunal"),
            dados.get("fase", "Inicial"),
            dados.get("data_distribuicao") if dados.get("data_distribuicao") else None,
            dados.get("valor_causa", 0),
            dados.get("reu"),
            dados.get("observacoes")
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar processo info: {e}")
        return False


# ============================================
# PORTAL DO CLIENTE - FUNÇÕES ANDAMENTOS
# ============================================

def listar_andamentos(cadastro_id: str, apenas_visiveis: bool = False) -> list:
    """Lista andamentos de um processo."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if apenas_visiveis:
            cur.execute("""
                SELECT * FROM andamentos 
                WHERE cadastro_id = %s AND visivel_cliente = TRUE
                ORDER BY data DESC, criado_em DESC
            """, (cadastro_id,))
        else:
            cur.execute("""
                SELECT * FROM andamentos 
                WHERE cadastro_id = %s
                ORDER BY data DESC, criado_em DESC
            """, (cadastro_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return [{
            "id": row["id"],
            "cadastro_id": row["cadastro_id"],
            "data": row["data"].isoformat() if row["data"] else None,
            "descricao": row["descricao"],
            "visivel_cliente": row["visivel_cliente"],
            "criado_em": row["criado_em"].isoformat() if row["criado_em"] else None
        } for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar andamentos: {e}")
        return []

def criar_andamento(cadastro_id: str, data: str, descricao: str, visivel_cliente: bool = True) -> bool:
    """Cria um novo andamento."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO andamentos (cadastro_id, data, descricao, visivel_cliente)
            VALUES (%s, %s, %s, %s)
        """, (cadastro_id, data, descricao, visivel_cliente))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao criar andamento: {e}")
        return False

def deletar_andamento(andamento_id: int) -> bool:
    """Deleta um andamento."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM andamentos WHERE id = %s", (andamento_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar andamento: {e}")
        return False


# ============================================
# PORTAL DO CLIENTE - FUNÇÕES MENSAGENS
# ============================================

def listar_mensagens(cadastro_id: str) -> list:
    """Lista mensagens de um cliente."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM mensagens 
            WHERE cadastro_id = %s
            ORDER BY criado_em ASC
        """, (cadastro_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return [{
            "id": row["id"],
            "cadastro_id": row["cadastro_id"],
            "remetente": row["remetente"],
            "texto": row["texto"],
            "lida": row["lida"],
            "criado_em": row["criado_em"].isoformat() if row["criado_em"] else None
        } for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar mensagens: {e}")
        return []

def criar_mensagem(cadastro_id: str, remetente: str, texto: str) -> int:
    """Cria uma nova mensagem."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO mensagens (cadastro_id, remetente, texto)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (cadastro_id, remetente, texto))
        msg_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return msg_id
    except Exception as e:
        logger.error(f"Erro ao criar mensagem: {e}")
        return None

def marcar_mensagens_lidas(cadastro_id: str, remetente: str):
    """Marca mensagens como lidas."""
    conn = get_db()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        outro_remetente = "escritorio" if remetente == "cliente" else "cliente"
        cur.execute("""
            UPDATE mensagens 
            SET lida = TRUE
            WHERE cadastro_id = %s AND remetente = %s AND lida = FALSE
        """, (cadastro_id, outro_remetente))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao marcar mensagens lidas: {e}")

def contar_mensagens_nao_lidas(cadastro_id: str = None, remetente: str = None) -> int:
    """Conta mensagens não lidas."""
    conn = get_db()
    if not conn:
        return 0
    
    try:
        cur = conn.cursor()
        if cadastro_id and remetente:
            cur.execute("""
                SELECT COUNT(*) FROM mensagens 
                WHERE cadastro_id = %s AND remetente = %s AND lida = FALSE
            """, (cadastro_id, remetente))
        elif remetente:
            cur.execute("""
                SELECT COUNT(*) FROM mensagens 
                WHERE remetente = %s AND lida = FALSE
            """, (remetente,))
        else:
            return 0
        
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception as e:
        logger.error(f"Erro ao contar mensagens: {e}")
        return 0


# ============================================
# PORTAL DO CLIENTE - TOKENS
# ============================================

def gerar_token_cliente(cadastro_id: str, email: str) -> str:
    """Gera um token específico para clientes."""
    payload = f"cliente:{cadastro_id}:{email}"
    signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
    token_data = base64.b64encode(f"{payload}:{signature}".encode()).decode()
    return token_data

def decodificar_token_cliente(token: str) -> dict:
    """Decodifica e valida um token de cliente."""
    try:
        decoded = base64.b64decode(token.encode()).decode()
        parts = decoded.rsplit(":", 1)
        if len(parts) != 2:
            return None
        
        payload, signature = parts
        
        expected_signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
        if signature != expected_signature:
            return None
        
        tipo, cadastro_id, email = payload.split(":")
        if tipo != "cliente":
            return None
            
        return {
            "cadastro_id": cadastro_id,
            "email": email,
            "tipo": "cliente"
        }
    except Exception:
        return None

def verificar_token_cliente(authorization: str = Header(None)) -> dict:
    """Verifica se o token de cliente é válido."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token não fornecido")
    
    token = authorization.replace("Bearer ", "")
    
    cliente = decodificar_token_cliente(token)
    if not cliente:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    
    auth = buscar_cliente_auth(cliente["cadastro_id"])
    if not auth or not auth.get("ativo", True):
        raise HTTPException(status_code=401, detail="Cliente não encontrado ou inativo")
    
    return {
        "cadastro_id": cliente["cadastro_id"],
        "email": auth["email"],
        "nome": auth["nome"],
        "primeiro_acesso": auth.get("primeiro_acesso", False)
    }


# ============================================
# ENDPOINTS - AUTENTICAÇÃO DO CLIENTE
# ============================================

@app.post("/api/cliente/login")
async def portal_cliente_login(dados: ClienteLogin):
    """Login do cliente no portal."""
    logger.info(f"Tentativa de login cliente: {dados.email}")
    
    cliente = buscar_cliente_por_email(dados.email)
    logger.info(f"Cliente encontrado: {cliente}")
    
    if not cliente:
        raise HTTPException(status_code=401, detail="Email não encontrado")
    
    if not cliente.get("senha_hash"):
        logger.info(f"Senha hash não encontrada para cliente: {cliente.get('cadastro_id')}")
        raise HTTPException(status_code=401, detail="Acesso não habilitado. Entre em contato com o escritório.")
    
    if not verificar_senha(dados.senha, cliente["senha_hash"]):
        raise HTTPException(status_code=401, detail="Senha incorreta")
    
    if not cliente.get("ativo", True):
        raise HTTPException(status_code=401, detail="Acesso desativado")
    
    registrar_acesso_cliente(cliente["cadastro_id"])
    token = gerar_token_cliente(cliente["cadastro_id"], cliente["email"])
    
    return {
        "success": True,
        "token": token,
        "cadastro_id": cliente["cadastro_id"],
        "nome": cliente["nome"],
        "email": cliente["email"],
        "primeiro_acesso": cliente.get("primeiro_acesso", False)
    }

@app.post("/api/cliente/alterar-senha")
async def portal_cliente_alterar_senha(
    dados: ClienteAlterarSenha,
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente altera sua própria senha."""
    auth = buscar_cliente_auth(cliente["cadastro_id"])
    if not verificar_senha(dados.senha_atual, auth["senha_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    
    if len(dados.nova_senha) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter no mínimo 6 caracteres")
    
    if atualizar_senha_cliente(cliente["cadastro_id"], dados.nova_senha):
        return {"success": True, "message": "Senha alterada com sucesso"}
    
    raise HTTPException(status_code=500, detail="Erro ao alterar senha")


# ============================================
# ENDPOINTS - PORTAL DO CLIENTE
# ============================================

@app.get("/api/cliente/meus-dados")
async def portal_cliente_meus_dados(cliente: dict = Depends(verificar_token_cliente)):
    """Retorna dados pessoais do cliente logado."""
    logger.info(f"MEUS-DADOS: cadastro_id={cliente['cadastro_id']}")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM cadastros WHERE id = %s", (cliente["cadastro_id"],))
        row = cur.fetchone()
        logger.info(f"MEUS-DADOS: row encontrado={row is not None}")
        cur.close()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail=f"Cadastro {cliente['cadastro_id']} não encontrado")
        
        dados = row["dados"] if isinstance(row["dados"], dict) else json.loads(row["dados"])
        
        return {
            "cadastro_id": cliente["cadastro_id"],
            "nome": dados.get("nome", ""),
            "email": dados.get("email", ""),
            "telefone": dados.get("telefone", ""),
            "cpf": dados.get("cpf", ""),
            "endereco": dados.get("endereco_completo", ""),
            "primeiro_acesso": cliente.get("primeiro_acesso", False)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro em meus-dados: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cliente/meus-processos")
async def portal_cliente_meus_processos(cliente: dict = Depends(verificar_token_cliente)):
    """Retorna todos os processos do cliente logado."""
    logger.info(f"MEUS-PROCESSOS: cadastro_id={cliente['cadastro_id']}")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, cadastro_id, numero_processo, tipo_acao, vara_tribunal,
                   fase, reu, valor_causa, data_distribuicao, status, observacoes
            FROM processos
            WHERE cadastro_id = %s
            ORDER BY criado_em DESC
        """, (cliente["cadastro_id"],))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        processos = []
        for row in rows:
            processos.append({
                "id": row["id"],
                "cadastro_id": row["cadastro_id"],
                "numero_processo": row["numero_processo"],
                "tipo_acao": row["tipo_acao"],
                "vara_tribunal": row["vara_tribunal"],
                "fase": row["fase"],
                "reu": row["reu"],
                "valor_causa": float(row["valor_causa"]) if row["valor_causa"] else 0,
                "data_distribuicao": row["data_distribuicao"].isoformat() if row["data_distribuicao"] else None,
                "status": row["status"],
                "observacoes": row["observacoes"]
            })
        
        logger.info(f"MEUS-PROCESSOS: encontrados {len(processos)} processos")
        return {"processos": processos}
    
    except Exception as e:
        logger.error(f"Erro ao buscar processos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar processos")


@app.get("/api/cliente/processo/{processo_id}/andamentos")
async def portal_cliente_andamentos_processo(processo_id: int, cliente: dict = Depends(verificar_token_cliente)):
    """Retorna andamentos de um processo (apenas visíveis ao cliente)."""
    logger.info(f"ANDAMENTOS: processo_id={processo_id}, cadastro_id={cliente['cadastro_id']}")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar se o processo pertence ao cliente
        cur.execute("""
            SELECT id FROM processos 
            WHERE id = %s AND cadastro_id = %s
        """, (processo_id, cliente["cadastro_id"]))
        
        if not cur.fetchone():
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Processo não encontrado")
        
        # Buscar andamentos visíveis ao cliente
        cur.execute("""
            SELECT id, processo_id, data, descricao
            FROM processo_andamentos
            WHERE processo_id = %s AND visivel_cliente = true
            ORDER BY data DESC, criado_em DESC
        """, (processo_id,))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        andamentos = []
        for row in rows:
            andamentos.append({
                "id": row["id"],
                "processo_id": row["processo_id"],
                "data": row["data"].isoformat() if row["data"] else None,
                "descricao": row["descricao"]
            })
        
        logger.info(f"ANDAMENTOS: encontrados {len(andamentos)} andamentos")
        return {"andamentos": andamentos}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar andamentos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar andamentos")


@app.get("/api/cliente/meus-contratos")
async def portal_cliente_meus_contratos(cliente: dict = Depends(verificar_token_cliente)):
    """Retorna todos os contratos de honorários do cliente."""
    logger.info(f"MEUS-CONTRATOS: cadastro_id={cliente['cadastro_id']}")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Buscar contratos
        cur.execute("""
            SELECT c.id, c.cadastro_id, c.processo_id, c.tipo, c.descricao,
                   c.valor_total, c.num_parcelas, c.valor_mensal, c.dia_vencimento,
                   c.percentual_exito, c.data_inicio, c.status, c.observacoes,
                   p.numero_processo
            FROM contratos_honorarios c
            LEFT JOIN processos p ON c.processo_id = p.id
            WHERE c.cadastro_id = %s
            ORDER BY c.criado_em DESC
        """, (cliente["cadastro_id"],))
        
        rows = cur.fetchall()
        
        contratos = []
        for row in rows:
            contrato_id = row["id"]
            
            # Buscar parcelas do contrato
            cur.execute("""
                SELECT id, contrato_id, numero, valor, vencimento, status, data_pagamento
                FROM parcelas
                WHERE contrato_id = %s
                ORDER BY numero
            """, (contrato_id,))
            
            parcelas_rows = cur.fetchall()
            parcelas = []
            for p in parcelas_rows:
                parcelas.append({
                    "id": p["id"],
                    "contrato_id": p["contrato_id"],
                    "numero": p["numero"],
                    "valor": float(p["valor"]) if p["valor"] else 0,
                    "vencimento": p["vencimento"].isoformat() if p["vencimento"] else None,
                    "status": p["status"],
                    "data_pagamento": p["data_pagamento"].isoformat() if p["data_pagamento"] else None
                })
            
            contratos.append({
                "id": contrato_id,
                "cadastro_id": row["cadastro_id"],
                "processo_id": row["processo_id"],
                "tipo": row["tipo"],
                "descricao": row["descricao"],
                "valor_total": float(row["valor_total"]) if row["valor_total"] else 0,
                "num_parcelas": row["num_parcelas"] or 1,
                "valor_mensal": float(row["valor_mensal"]) if row["valor_mensal"] else 0,
                "dia_vencimento": row["dia_vencimento"],
                "percentual_exito": float(row["percentual_exito"]) if row["percentual_exito"] else 0,
                "data_inicio": row["data_inicio"].isoformat() if row["data_inicio"] else None,
                "status": row["status"],
                "observacoes": row["observacoes"],
                "processo_numero": row["numero_processo"],
                "parcelas": parcelas
            })
        
        cur.close()
        conn.close()
        
        logger.info(f"MEUS-CONTRATOS: encontrados {len(contratos)} contratos")
        return {"contratos": contratos}
    
    except Exception as e:
        logger.error(f"Erro ao buscar contratos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar contratos")        

@app.get("/api/cliente/andamentos")
async def portal_cliente_andamentos(cliente: dict = Depends(verificar_token_cliente)):
    """Lista andamentos visíveis para o cliente."""
    andamentos = listar_andamentos(cliente["cadastro_id"], apenas_visiveis=True)
    return {"andamentos": andamentos}

@app.get("/api/cliente/documentos")
async def portal_cliente_documentos(cliente: dict = Depends(verificar_token_cliente)):
    """Lista documentos disponíveis para o cliente."""
    cadastro = buscar_cadastro(cliente["cadastro_id"])
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    documentos = []
    
    # 1. Documentos Gerados pelo Sistema (Contrato e Procuração)
    arquivos_gerados = cadastro.get("arquivos_gerados", {})
    if arquivos_gerados:
        # Contrato de Honorários
        if arquivos_gerados.get("contrato"):
            documentos.append({
                "tipo": "contrato",
                "nome": "Contrato de Honorários",
                "categoria": "Documento Gerado",
                "disponivel": True
            })
        
        # Procuração
        if arquivos_gerados.get("procuracao"):
            documentos.append({
                "tipo": "procuracao",
                "nome": "Procuração",
                "categoria": "Documento Gerado",
                "disponivel": True
            })
    
    # 2. Documentos Enviados pelo Escritório (admin)
    docs_admin = listar_documentos_admin(cliente["cadastro_id"])
    for doc in docs_admin:
        documentos.append({
            "tipo": f"admin_{doc['id']}",
            "nome": doc["nome_original"],
            "descricao": doc.get("descricao", ""),
            "categoria": "Enviado pelo Escritório",
            "disponivel": True,
            "data": doc["criado_em"].isoformat() if doc.get("criado_em") else None
        })
    
    # 3. Documentos Enviados pelo Cliente (uploads do cadastro)
    documentos_cliente = cadastro.get("documentos", [])
    if documentos_cliente:
        for i, doc_path in enumerate(documentos_cliente):
            # Extrair nome do arquivo do caminho
            nome_arquivo = doc_path.split("/")[-1] if "/" in doc_path else doc_path
            documentos.append({
                "tipo": f"cliente_{i}",
                "nome": nome_arquivo,
                "categoria": "Enviado pelo Cliente",
                "disponivel": True
            })
    
    # 4. Documentos Assinados (devolvidos pelo cliente)
    documentos_assinados = cadastro.get("documentos_assinados", [])
    if documentos_assinados:
        for i, doc_path in enumerate(documentos_assinados):
            nome_arquivo = doc_path.split("/")[-1] if "/" in doc_path else doc_path
            documentos.append({
                "tipo": f"assinado_{i}",
                "nome": nome_arquivo,
                "categoria": "Documento Assinado",
                "disponivel": True
            })
    
    return {"documentos": documentos}


# ============================================
# ENDPOINTS - PORTAL CLIENTE (DOCUMENTOS EXTRAS)
# ============================================

@app.post("/api/cliente/documentos-extras")
async def portal_cliente_enviar_documento_extra(
    arquivo: UploadFile = File(...),
    descricao: str = Form(""),
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente envia documento extra para o escritório."""
    # Criar diretório para documentos extras
    docs_dir = os.path.join(UPLOADS_DIR, "documentos_extras", cliente["cadastro_id"])
    os.makedirs(docs_dir, exist_ok=True)
    
    # Salvar arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"{timestamp}_{arquivo.filename}"
    caminho_arquivo = os.path.join(docs_dir, nome_arquivo)
    
    with open(caminho_arquivo, "wb") as f:
        conteudo = await arquivo.read()
        f.write(conteudo)
    
    # Criar registro no banco
    doc_id = criar_documento_extra(
        cadastro_id=cliente["cadastro_id"],
        nome_arquivo=nome_arquivo,
        nome_original=arquivo.filename,
        arquivo_path=caminho_arquivo,
        descricao=descricao
    )
    
    if doc_id:
        # Enviar e-mail notificando o escritório
        cadastro = buscar_cadastro(cliente["cadastro_id"])
        nome_cliente = cliente.get("nome", "Cliente")
        
        conteudo_email = f"""
            <h2 style="color: #8B1538;">Novo Documento Recebido</h2>
            
            <p>O cliente <strong>{nome_cliente}</strong> enviou um novo documento pelo Portal do Cliente.</p>
            
            <div style="background-color: #f8f8f8; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Documento:</strong> {arquivo.filename}</p>
                {f'<p><strong>Descrição:</strong> {descricao}</p>' if descricao else ''}
                <p><strong>Cliente:</strong> {nome_cliente}</p>
                <p><strong>Código:</strong> {cliente["cadastro_id"]}</p>
            </div>
            
            <p>Acesse o <strong>Painel Administrativo</strong> para visualizar e baixar o documento:</p>
            
            <p style="text-align: center; margin: 30px 0;">
                <a href="https://painel.vaucherealvares.com.br" 
                   style="background-color: #8B1538; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Acessar Painel Administrativo
                </a>
            </p>
        """
        
        email_html = criar_email_html(conteudo_email)
        
        try:
            # Enviar para o e-mail do escritório
            await enviar_email_resend(
                "atendimento@vaucherealvares.com.br",
                f"Novo documento recebido de {nome_cliente}",
                email_html
            )
            logger.info(f"E-mail de notificação enviado para o escritório - documento de {nome_cliente}")
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de notificação: {e}")
        
        return {
            "success": True,
            "message": "Documento enviado com sucesso",
            "documento_id": doc_id
        }
    
    raise HTTPException(status_code=500, detail="Erro ao salvar documento")

@app.get("/api/cliente/meus-documentos-extras")
async def portal_cliente_listar_documentos_extras(
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente lista seus documentos extras enviados."""
    documentos = listar_documentos_extras(cliente["cadastro_id"])
    return {"documentos": documentos}

@app.delete("/api/cliente/documentos-extras/{doc_id}")
async def portal_cliente_deletar_documento_extra(
    doc_id: int,
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente deleta um documento extra enviado."""
    # Verificar se o documento pertence ao cliente
    doc = buscar_documento_extra(doc_id)
    if not doc or doc["cadastro_id"] != cliente["cadastro_id"]:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    if deletar_documento_extra(doc_id):
        return {"success": True, "message": "Documento deletado"}
    
    raise HTTPException(status_code=500, detail="Erro ao deletar documento")

@app.get("/api/cliente/documentos/{tipo}/download")
async def portal_cliente_download_documento(
    tipo: str,
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente baixa um documento."""
    cadastro = buscar_cadastro(cliente["cadastro_id"])
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    # Documento do admin
    if tipo.startswith("admin_"):
        doc_id = int(tipo.replace("admin_", ""))
        doc = buscar_documento_admin(doc_id)
        if not doc or doc["cadastro_id"] != cliente["cadastro_id"]:
            raise HTTPException(status_code=404, detail="Documento não encontrado")
        
        if not os.path.exists(doc["arquivo_path"]):
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        
        return FileResponse(
            doc["arquivo_path"],
            filename=doc["nome_original"],
            media_type="application/octet-stream"
        )
    
    # Documento gerado (contrato/procuração)
    arquivos_gerados = cadastro.get("arquivos_gerados", {})
    if tipo in ["contrato", "procuracao"]:
        arquivo_path = arquivos_gerados.get(tipo)
        if not arquivo_path or not os.path.exists(arquivo_path):
            raise HTTPException(status_code=404, detail="Documento não encontrado")
        
        nome = "Contrato de Honorários.docx" if tipo == "contrato" else "Procuração.docx"
        return FileResponse(
            arquivo_path,
            filename=nome,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    
    raise HTTPException(status_code=404, detail="Tipo de documento não reconhecido")

@app.get("/api/cliente/mensagens")
async def portal_cliente_mensagens(cliente: dict = Depends(verificar_token_cliente)):
    """Lista mensagens do cliente."""
    marcar_mensagens_lidas(cliente["cadastro_id"], "cliente")
    mensagens = listar_mensagens(cliente["cadastro_id"])
    return {"mensagens": mensagens}

@app.post("/api/cliente/mensagens")
async def portal_cliente_enviar_mensagem(
    dados: MensagemEnvio,
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente envia mensagem para o escritório."""
    if not dados.texto.strip():
        raise HTTPException(status_code=400, detail="Mensagem não pode ser vazia")
    
    msg_id = criar_mensagem(cliente["cadastro_id"], "cliente", dados.texto.strip())
    if msg_id:
        return {"success": True, "message_id": msg_id}
    
    raise HTTPException(status_code=500, detail="Erro ao enviar mensagem")

@app.get("/api/cliente/mensagens/nao-lidas")
async def portal_cliente_mensagens_nao_lidas(cliente: dict = Depends(verificar_token_cliente)):
    """Conta mensagens não lidas do escritório."""
    count = contar_mensagens_nao_lidas(cliente["cadastro_id"], "escritorio")
    return {"nao_lidas": count}


# ============================================
# ENDPOINTS - ADMIN GERENCIAR ACESSO CLIENTE
# ============================================

@app.post("/api/admin/clientes/{cadastro_id}/habilitar-acesso")
async def admin_habilitar_acesso_cliente(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin habilita acesso ao portal para um cliente."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    senha_temporaria = secrets.token_urlsafe(8)
    
    if not criar_cliente_auth(cadastro_id, senha_temporaria):
        raise HTTPException(status_code=500, detail="Erro ao criar acesso")
    
    dados = cadastro["dados"]
    email_cliente = dados.get("email")
    
    if email_cliente and RESEND_API_KEY:
        try:
            conteudo = f"""
                <p style="font-size: 16px;">Olá, <strong>{dados['nome']}</strong>!</p>
                
                <p>Seu acesso ao Portal do Cliente foi habilitado.</p>
                
                <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Email:</strong> {email_cliente}</p>
                    <p style="margin: 10px 0;"><strong>Senha temporária:</strong> <code style="background: #e0e0e0; padding: 3px 8px; border-radius: 4px; font-size: 18px;">{senha_temporaria}</code></p>
                </div>
                
                <p>Acesse o portal em: <a href="https://portal.vaucherealvares.com.br" style="color: #8B1538;">portal.vaucherealvares.com.br</a></p>
                
                <p style="color: #666; font-size: 14px;">
                    <strong>Importante:</strong> Recomendamos que você altere sua senha no primeiro acesso.
                </p>
            """
            corpo_html = criar_email_html(conteudo)
            
            await enviar_email_resend(
                email_cliente,
                "🔐 Seu acesso ao Portal do Cliente - Vaucher & Álvares",
                corpo_html
            )
            
            return {
                "success": True, 
                "message": f"Acesso habilitado! Senha enviada para {email_cliente}",
                "senha_temporaria": senha_temporaria
            }
        except Exception as e:
            logger.error(f"Erro ao enviar email: {e}")
            return {
                "success": True,
                "message": "Acesso habilitado, mas houve erro ao enviar email.",
                "senha_temporaria": senha_temporaria
            }
    
    return {
        "success": True,
        "message": "Acesso habilitado!",
        "senha_temporaria": senha_temporaria
    }

@app.post("/api/admin/clientes/{cadastro_id}/desabilitar-acesso")
async def admin_desabilitar_acesso_cliente(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin desabilita acesso ao portal de um cliente."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor()
        cur.execute("UPDATE clientes_auth SET ativo = FALSE WHERE cadastro_id = %s", (cadastro_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"success": True, "message": "Acesso desabilitado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/clientes/{cadastro_id}/acesso")
async def admin_verificar_acesso_cliente(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Verifica se o cliente tem acesso ao portal."""
    auth = buscar_cliente_auth(cadastro_id)
    return {
        "tem_acesso": bool(auth and auth.get("ativo")),
        "primeiro_acesso": auth.get("primeiro_acesso") if auth else None,
        "ultimo_acesso": auth.get("ultimo_acesso") if auth else None
    }


# ============================================
# ENDPOINTS - ADMIN PROCESSO
# ============================================

@app.get("/api/admin/clientes/{cadastro_id}/processo")
async def admin_obter_processo(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin obtém informações do processo."""
    processo = buscar_processo_info(cadastro_id)
    return processo or {
        "cadastro_id": cadastro_id,
        "numero_processo": "",
        "vara_tribunal": "",
        "fase": "Inicial",
        "data_distribuicao": None,
        "valor_causa": 0,
        "reu": "",
        "observacoes": ""
    }

@app.post("/api/admin/clientes/{cadastro_id}/processo")
async def admin_salvar_processo(
    cadastro_id: str,
    dados: ProcessoInfoModel,
    usuario: dict = Depends(verificar_admin)
):
    """Admin salva informações do processo."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    if salvar_processo_info(cadastro_id, dados.dict()):
        return {"success": True, "message": "Informações do processo salvas"}
    
    raise HTTPException(status_code=500, detail="Erro ao salvar")


# ============================================
# ENDPOINTS - ADMIN ANDAMENTOS
# ============================================

@app.get("/api/admin/clientes/{cadastro_id}/andamentos")
async def admin_listar_andamentos(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista todos os andamentos."""
    andamentos = listar_andamentos(cadastro_id, apenas_visiveis=False)
    return {"andamentos": andamentos}

@app.post("/api/admin/clientes/{cadastro_id}/andamentos")
async def admin_criar_andamento(
    cadastro_id: str,
    dados: AndamentoModel,
    usuario: dict = Depends(verificar_admin)
):
    """Admin cria novo andamento."""
    if criar_andamento(cadastro_id, dados.data, dados.descricao, dados.visivel_cliente):
        return {"success": True, "message": "Andamento criado"}
    
    raise HTTPException(status_code=500, detail="Erro ao criar andamento")

@app.delete("/api/admin/andamentos/{andamento_id}")
async def admin_deletar_andamento(
    andamento_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um andamento."""
    if deletar_andamento(andamento_id):
        return {"success": True, "message": "Andamento deletado"}
    
    raise HTTPException(status_code=500, detail="Erro ao deletar andamento")


# ============================================
# ENDPOINTS - ADMIN MENSAGENS
# ============================================

@app.get("/api/admin/clientes/{cadastro_id}/mensagens")
async def admin_listar_mensagens(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista mensagens de um cliente."""
    marcar_mensagens_lidas(cadastro_id, "escritorio")
    mensagens = listar_mensagens(cadastro_id)
    return {"mensagens": mensagens}

@app.post("/api/admin/clientes/{cadastro_id}/mensagens")
async def admin_enviar_mensagem(
    cadastro_id: str,
    dados: MensagemEnvio,
    usuario: dict = Depends(verificar_admin)
):
    """Admin envia mensagem para o cliente."""
    if not dados.texto.strip():
        raise HTTPException(status_code=400, detail="Mensagem não pode ser vazia")
    
    msg_id = criar_mensagem(cadastro_id, "escritorio", dados.texto.strip())
    if msg_id:
        return {"success": True, "message_id": msg_id}
    
    raise HTTPException(status_code=500, detail="Erro ao enviar mensagem")

@app.get("/api/admin/mensagens/nao-lidas")
async def admin_mensagens_nao_lidas(usuario: dict = Depends(verificar_admin)):
    """Conta total de mensagens não lidas de clientes."""
    count = contar_mensagens_nao_lidas(remetente="cliente")
    return {"nao_lidas": count}

@app.get("/api/admin/clientes/{cadastro_id}/mensagens/nao-lidas")
async def admin_mensagens_nao_lidas_cliente(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Conta mensagens não lidas de um cliente específico."""
    count = contar_mensagens_nao_lidas(cadastro_id, "cliente")
    return {"nao_lidas": count}

# ============================================
# ENDPOINTS - ADMIN PROCESSOS (MÚLTIPLOS)
# ============================================

@app.get("/api/admin/clientes/{cadastro_id}/processos")
async def admin_listar_processos(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista todos os processos de um cliente."""
    processos = listar_processos(cadastro_id)
    return {"processos": processos}

@app.post("/api/admin/clientes/{cadastro_id}/processos")
async def admin_criar_processo(
    cadastro_id: str,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin cria novo processo para o cliente."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    processo_id = criar_processo(cadastro_id, dados)
    if processo_id:
        return {"success": True, "processo_id": processo_id}
    
    raise HTTPException(status_code=500, detail="Erro ao criar processo")

@app.get("/api/admin/processos/{processo_id}")
async def admin_obter_processo_por_id(
    processo_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin obtém um processo específico."""
    processo = buscar_processo(processo_id)
    if not processo:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return processo

@app.put("/api/admin/processos/{processo_id}")
async def admin_atualizar_processo(
    processo_id: int,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin atualiza um processo."""
    if atualizar_processo(processo_id, dados):
        return {"success": True, "message": "Processo atualizado"}
    
    raise HTTPException(status_code=500, detail="Erro ao atualizar processo")

@app.delete("/api/admin/processos/{processo_id}")
async def admin_deletar_processo(
    processo_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um processo."""
    if deletar_processo(processo_id):
        return {"success": True, "message": "Processo deletado"}
    
    raise HTTPException(status_code=500, detail="Erro ao deletar processo")


# ============================================
# ENDPOINTS - ADMIN ANDAMENTOS DE PROCESSO
# ============================================

@app.get("/api/admin/processos/{processo_id}/andamentos")
async def admin_listar_andamentos_processo(
    processo_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista andamentos de um processo."""
    andamentos = listar_andamentos_processo(processo_id, apenas_visiveis=False)
    return {"andamentos": andamentos}

@app.post("/api/admin/processos/{processo_id}/andamentos")
async def admin_criar_andamento_processo(
    processo_id: int,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin cria andamento para um processo."""
    andamento_id = criar_andamento_processo(
        processo_id,
        dados.get("data"),
        dados.get("descricao"),
        dados.get("visivel_cliente", True)
    )
    if andamento_id:
        return {"success": True, "andamento_id": andamento_id}
    
    raise HTTPException(status_code=500, detail="Erro ao criar andamento")

@app.delete("/api/admin/processo-andamentos/{andamento_id}")
async def admin_deletar_andamento_processo(
    andamento_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um andamento de processo."""
    if deletar_andamento_processo(andamento_id):
        return {"success": True, "message": "Andamento deletado"}
    
    raise HTTPException(status_code=500, detail="Erro ao deletar andamento")


# ============================================
# ENDPOINTS - ADMIN CONTRATOS DE HONORÁRIOS
# ============================================

@app.get("/api/admin/clientes/{cadastro_id}/contratos")
async def admin_listar_contratos(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista contratos de um cliente."""
    contratos = listar_contratos(cadastro_id)
    return {"contratos": contratos}

@app.post("/api/admin/clientes/{cadastro_id}/contratos")
async def admin_criar_contrato(
    cadastro_id: str,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin cria novo contrato de honorários."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    contrato_id = criar_contrato_honorarios(cadastro_id, dados)
    if contrato_id:
        return {"success": True, "contrato_id": contrato_id}
    
    raise HTTPException(status_code=500, detail="Erro ao criar contrato")

@app.get("/api/admin/contratos/{contrato_id}")
async def admin_obter_contrato(
    contrato_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin obtém um contrato específico."""
    contrato = buscar_contrato(contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    return contrato

@app.put("/api/admin/contratos/{contrato_id}")
async def admin_atualizar_contrato(
    contrato_id: int,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin atualiza um contrato."""
    if atualizar_contrato(contrato_id, dados):
        return {"success": True, "message": "Contrato atualizado"}
    
    raise HTTPException(status_code=500, detail="Erro ao atualizar contrato")

@app.delete("/api/admin/contratos/{contrato_id}")
async def admin_deletar_contrato(
    contrato_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um contrato."""
    if deletar_contrato(contrato_id):
        return {"success": True, "message": "Contrato deletado"}
    
    raise HTTPException(status_code=500, detail="Erro ao deletar contrato")


# ============================================
# ENDPOINTS - ADMIN PARCELAS
# ============================================

@app.put("/api/admin/parcelas/{parcela_id}")
async def admin_atualizar_parcela(
    parcela_id: int,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin atualiza uma parcela."""
    if atualizar_parcela(parcela_id, dados):
        return {"success": True, "message": "Parcela atualizada"}
    
    raise HTTPException(status_code=500, detail="Erro ao atualizar parcela")

@app.post("/api/admin/parcelas/{parcela_id}/marcar-pago")
async def admin_marcar_parcela_paga(
    parcela_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin marca uma parcela como paga."""
    if marcar_parcela_paga(parcela_id):
        return {"success": True, "message": "Parcela marcada como paga"}
    
    raise HTTPException(status_code=500, detail="Erro ao marcar parcela")


# ============================================
# ENDPOINTS - ADMIN COMPROVANTES
# ============================================

@app.get("/api/admin/comprovantes/pendentes")
async def admin_listar_comprovantes_pendentes(
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista comprovantes pendentes de verificação."""
    comprovantes = listar_comprovantes_pendentes()
    return {"comprovantes": comprovantes}

@app.post("/api/admin/comprovantes/{comprovante_id}/aprovar")
async def admin_aprovar_comprovante(
    comprovante_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin aprova um comprovante e marca parcela como paga."""
    if aprovar_comprovante(comprovante_id, usuario["email"]):
        return {"success": True, "message": "Comprovante aprovado e parcela marcada como paga"}
    
    raise HTTPException(status_code=500, detail="Erro ao aprovar comprovante")

@app.post("/api/admin/comprovantes/{comprovante_id}/rejeitar")
async def admin_rejeitar_comprovante(
    comprovante_id: int,
    dados: dict,
    usuario: dict = Depends(verificar_admin)
):
    """Admin rejeita um comprovante."""
    if rejeitar_comprovante(comprovante_id, usuario["email"], dados.get("motivo")):
        return {"success": True, "message": "Comprovante rejeitado"}
    
    raise HTTPException(status_code=500, detail="Erro ao rejeitar comprovante")

@app.get("/api/admin/comprovantes/{comprovante_id}/download")
async def admin_download_comprovante(
    comprovante_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin baixa um comprovante."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT arquivo_nome, arquivo_path FROM comprovantes WHERE id = %s", (comprovante_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Comprovante não encontrado")
        
        if not os.path.exists(row["arquivo_path"]):
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        
        return FileResponse(
            row["arquivo_path"],
            filename=row["arquivo_nome"],
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINTS - ADMIN DOCUMENTOS (PARA CLIENTE)
# ============================================

@app.post("/api/admin/clientes/{cadastro_id}/enviar-documentos")
async def admin_enviar_documentos(
    cadastro_id: str,
    arquivos: List[UploadFile] = File(...),
    usuario: dict = Depends(verificar_admin)
):
    """Admin envia documentos para o cliente."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    # Criar diretório para documentos do admin
    docs_dir = os.path.join(UPLOADS_DIR, "documentos_admin", cadastro_id)
    os.makedirs(docs_dir, exist_ok=True)
    
    arquivos_salvos = []
    
    for arquivo in arquivos:
        # Salvar arquivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"{timestamp}_{arquivo.filename}"
        caminho_arquivo = os.path.join(docs_dir, nome_arquivo)
        
        with open(caminho_arquivo, "wb") as f:
            conteudo = await arquivo.read()
            f.write(conteudo)
        
        # Criar registro no banco
        doc_id = criar_documento_admin(
            cadastro_id=cadastro_id,
            nome_arquivo=nome_arquivo,
            nome_original=arquivo.filename,
            arquivo_path=caminho_arquivo,
            descricao="",
            admin_email=usuario["email"]
        )
        
        if doc_id:
            arquivos_salvos.append({
                "id": doc_id,
                "nome": arquivo.filename
            })
    
    if arquivos_salvos:
        # Enviar e-mail notificando o cliente
        dados_cliente = cadastro.get("dados", {})
        email_cliente = dados_cliente.get("email")
        nome_cliente = dados_cliente.get("nome", "Cliente")
        
        if email_cliente:
            lista_arquivos = "".join([f"<li>{arq['nome']}</li>" for arq in arquivos_salvos])
            
            conteudo_email = f"""
                <h2 style="color: #8B1538;">Novos Documentos Disponíveis</h2>
                
                <p>Olá, <strong>{nome_cliente}</strong>!</p>
                
                <p>O escritório <strong>Vaucher & Álvares Sociedade de Advogados</strong> enviou novos documentos para você:</p>
                
                <ul style="background-color: #f8f8f8; padding: 15px 30px; border-radius: 8px;">
                    {lista_arquivos}
                </ul>
                
                <p>Para visualizar e baixar os documentos, acesse o <strong>Portal do Cliente</strong>:</p>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="https://portal.vaucherealvares.com.br" 
                       style="background-color: #8B1538; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Acessar Portal do Cliente
                    </a>
                </p>
                
                <p style="color: #666; font-size: 14px;">
                    Caso tenha dúvidas, entre em contato conosco pelo portal ou pelos nossos canais de atendimento.
                </p>
            """
            
            email_html = criar_email_html(conteudo_email)
            
            try:
                await enviar_email_resend(
                    email_cliente,
                    "Novos documentos disponíveis - Vaucher & Álvares",
                    email_html
                )
                logger.info(f"E-mail de notificação enviado para {email_cliente}")
            except Exception as e:
                logger.error(f"Erro ao enviar e-mail de notificação: {e}")
        
        return {
            "success": True,
            "message": f"{len(arquivos_salvos)} documento(s) enviado(s)",
            "arquivos": arquivos_salvos,
            "email_enviado": bool(email_cliente)
        }
    
    raise HTTPException(status_code=500, detail="Erro ao salvar documentos")

@app.post("/api/admin/clientes/{cadastro_id}/documentos")
async def admin_upload_documento(
    cadastro_id: str,
    arquivo: UploadFile = File(...),
    descricao: str = Form(""),
    usuario: dict = Depends(verificar_admin)
):
    """Admin envia documento para o cliente (endpoint alternativo)."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    # Criar diretório para documentos do admin
    docs_dir = os.path.join(UPLOADS_DIR, "documentos_admin", cadastro_id)
    os.makedirs(docs_dir, exist_ok=True)
    
    # Salvar arquivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"{timestamp}_{arquivo.filename}"
    caminho_arquivo = os.path.join(docs_dir, nome_arquivo)
    
    with open(caminho_arquivo, "wb") as f:
        conteudo = await arquivo.read()
        f.write(conteudo)
    
    # Criar registro no banco
    doc_id = criar_documento_admin(
        cadastro_id=cadastro_id,
        nome_arquivo=nome_arquivo,
        nome_original=arquivo.filename,
        arquivo_path=caminho_arquivo,
        descricao=descricao,
        admin_email=usuario["email"]
    )
    
    if doc_id:
        return {
            "success": True,
            "message": "Documento enviado com sucesso",
            "documento_id": doc_id
        }
    
    raise HTTPException(status_code=500, detail="Erro ao salvar documento")

@app.get("/api/admin/clientes/{cadastro_id}/documentos-enviados")
async def admin_listar_documentos_enviados(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista documentos enviados para o cliente."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    documentos = listar_documentos_admin(cadastro_id)
    return {"documentos": documentos}

@app.delete("/api/admin/documentos/{doc_id}")
async def admin_deletar_documento(
    doc_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um documento enviado."""
    if deletar_documento_admin(doc_id):
        return {"success": True, "message": "Documento deletado"}
    
    raise HTTPException(status_code=500, detail="Erro ao deletar documento")

@app.get("/api/admin/documentos/{doc_id}/download")
async def admin_download_documento(
    doc_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin baixa um documento enviado."""
    doc = buscar_documento_admin(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    if not os.path.exists(doc["arquivo_path"]):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    return FileResponse(
        doc["arquivo_path"],
        filename=doc["nome_original"],
        media_type="application/octet-stream"
    )


# ============================================
# ENDPOINTS - ADMIN DOCUMENTOS EXTRAS (DO CLIENTE)
# ============================================

@app.get("/api/admin/clientes/{cadastro_id}/documentos-extras")
async def admin_listar_documentos_extras(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Admin lista documentos extras enviados pelo cliente."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    documentos = listar_documentos_extras(cadastro_id)
    return {"documentos": documentos}

@app.get("/api/admin/documentos-extras/{doc_id}/download")
async def admin_download_documento_extra(
    doc_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin baixa um documento extra enviado pelo cliente."""
    doc = buscar_documento_extra(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")
    
    if not os.path.exists(doc["arquivo_path"]):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    return FileResponse(
        doc["arquivo_path"],
        filename=doc["nome_original"],
        media_type="application/octet-stream"
    )

@app.delete("/api/admin/documentos-extras/{doc_id}")
async def admin_deletar_documento_extra(
    doc_id: int,
    usuario: dict = Depends(verificar_admin)
):
    """Admin deleta um documento extra."""
    if deletar_documento_extra(doc_id):
        return {"success": True, "message": "Documento deletado"}
    
    raise HTTPException(status_code=500, detail="Erro ao deletar documento")


# ============================================
# ENDPOINTS - PORTAL CLIENTE (PROCESSOS E HONORÁRIOS)
# ============================================

@app.get("/api/cliente/meus-processos")
async def portal_cliente_meus_processos(cliente: dict = Depends(verificar_token_cliente)):
    """Cliente lista seus processos."""
    processos = listar_processos(cliente["cadastro_id"])
    
    # Para cada processo, buscar andamentos visíveis
    for processo in processos:
        processo["andamentos"] = listar_andamentos_processo(processo["id"], apenas_visiveis=True)
    
    return {"processos": processos}

@app.get("/api/cliente/processo/{processo_id}/andamentos")
async def portal_cliente_andamentos_processo(
    processo_id: int,
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente visualiza andamentos de um processo."""
    processo = buscar_processo(processo_id)
    if not processo or processo["cadastro_id"] != cliente["cadastro_id"]:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    
    andamentos = listar_andamentos_processo(processo_id, apenas_visiveis=True)
    return {"andamentos": andamentos}

@app.get("/api/cliente/meus-contratos")
async def portal_cliente_meus_contratos(cliente: dict = Depends(verificar_token_cliente)):
    """Cliente lista seus contratos e parcelas."""
    contratos = listar_contratos(cliente["cadastro_id"])
    return {"contratos": contratos}

@app.post("/api/cliente/parcelas/{parcela_id}/comprovante")
async def portal_cliente_enviar_comprovante(
    parcela_id: int,
    arquivo: UploadFile = File(...),
    cliente: dict = Depends(verificar_token_cliente)
):
    """Cliente envia comprovante de pagamento."""
    # Verificar se a parcela pertence ao cliente
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT p.*, c.cadastro_id 
            FROM parcelas p
            JOIN contratos_honorarios c ON p.contrato_id = c.id
            WHERE p.id = %s
        """, (parcela_id,))
        parcela = cur.fetchone()
        cur.close()
        conn.close()
        
        if not parcela or parcela["cadastro_id"] != cliente["cadastro_id"]:
            raise HTTPException(status_code=404, detail="Parcela não encontrada")
        
        if parcela["status"] == "pago":
            raise HTTPException(status_code=400, detail="Parcela já está paga")
        
        # Salvar arquivo
        comprovantes_dir = os.path.join(UPLOADS_DIR, "comprovantes", cliente["cadastro_id"])
        os.makedirs(comprovantes_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"parcela_{parcela_id}_{timestamp}_{arquivo.filename}"
        caminho_arquivo = os.path.join(comprovantes_dir, nome_arquivo)
        
        with open(caminho_arquivo, "wb") as f:
            conteudo = await arquivo.read()
            f.write(conteudo)
        
        # Criar registro do comprovante
        comprovante_id = criar_comprovante(parcela_id, arquivo.filename, caminho_arquivo)
        
        if comprovante_id:
            return {
                "success": True,
                "message": "Comprovante enviado! Aguarde verificação do escritório.",
                "comprovante_id": comprovante_id
            }
        
        raise HTTPException(status_code=500, detail="Erro ao salvar comprovante")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar comprovante: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
