"""
Funções de Banco de Dados do Sistema Vaucher e Álvares
Migrado do main.py em 19/01/2026

Este arquivo contém conexão, inicialização e funções CRUD base.
"""

import json
import logging
from typing import List, Optional
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from modules.config import DATABASE_URL, ADMIN_INICIAL_SENHA, logger
from modules.security import hash_senha

# ============================================
# CONEXÃO COM BANCO DE DADOS
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


# ============================================
# INICIALIZAÇÃO DO BANCO DE DADOS
# ============================================

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
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cadastros' AND column_name='assinaturas_digitais') THEN
                    ALTER TABLE cadastros ADD COLUMN assinaturas_digitais JSONB DEFAULT '{}';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cadastros' AND column_name='documentos_finais') THEN
                    ALTER TABLE cadastros ADD COLUMN documentos_finais JSONB DEFAULT '{}';
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

        # ========== PORTAL DO CLIENTE - TABELAS ==========

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

        # ========== ATUALIZAÇÃO CADASTRAL ==========

        # Tabela de solicitações de atualização cadastral
        cur.execute("""
            CREATE TABLE IF NOT EXISTS atualizacoes_cadastrais (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                tipo VARCHAR(20) NOT NULL,
                status VARCHAR(20) DEFAULT 'pendente',
                motivo_solicitacao TEXT,
                solicitado_em TIMESTAMP,
                solicitado_por VARCHAR(255),
                dados_novos JSONB,
                documentos_novos JSONB,
                enviado_em TIMESTAMP,
                analisado_em TIMESTAMP,
                analisado_por VARCHAR(255),
                motivo_rejeicao TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Índices para melhor performance
        cur.execute("CREATE INDEX IF NOT EXISTS idx_atualizacoes_cadastro ON atualizacoes_cadastrais(cadastro_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_atualizacoes_status ON atualizacoes_cadastrais(status)")

        logger.info("Tabelas do Portal do Cliente verificadas/criadas!")
        logger.info("Tabela de atualizações cadastrais verificada/criada!")

        # ========== TERMOS DE USO E PRIVACIDADE ==========

        # Tabela de versões dos termos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS termos_versoes (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR(50) NOT NULL,
                versao VARCHAR(20) NOT NULL,
                conteudo TEXT NOT NULL,
                data_vigencia TIMESTAMP NOT NULL,
                ativo BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de aceites dos termos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS aceites_termos (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) NOT NULL,
                termos_versao_id INTEGER NOT NULL,
                ip_address VARCHAR(45) NOT NULL,
                user_agent TEXT,
                aceito_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadados JSONB DEFAULT '{}'
            )
        """)

        # Adicionar colunas de termos na tabela cadastros se não existirem
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cadastros' AND column_name='termos_aceitos') THEN
                    ALTER TABLE cadastros ADD COLUMN termos_aceitos BOOLEAN DEFAULT FALSE;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cadastros' AND column_name='termos_aceitos_em') THEN
                    ALTER TABLE cadastros ADD COLUMN termos_aceitos_em TIMESTAMP;
                END IF;
            END $$;
        """)

        # Índices para termos
        cur.execute("CREATE INDEX IF NOT EXISTS idx_termos_tipo_ativo ON termos_versoes(tipo, ativo)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_aceites_cadastro ON aceites_termos(cadastro_id)")

        # ========== DEMANDAS ESPECÍFICAS (FORMULÁRIOS DINÂMICOS) ==========

        # Tabela para dados específicos de cada tipo de demanda
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dados_demanda_especifica (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                tipo_demanda VARCHAR(100) NOT NULL,
                dados JSONB NOT NULL DEFAULT '{}',
                status VARCHAR(20) DEFAULT 'rascunho',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(cadastro_id, tipo_demanda)
            )
        """)

        # Tabela para documentos específicos da demanda
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documentos_demanda (
                id SERIAL PRIMARY KEY,
                cadastro_id VARCHAR(20) REFERENCES cadastros(id) ON DELETE CASCADE,
                tipo_documento VARCHAR(100) NOT NULL,
                nome_arquivo VARCHAR(255) NOT NULL,
                nome_original VARCHAR(255) NOT NULL,
                arquivo_path VARCHAR(500) NOT NULL,
                descricao VARCHAR(255),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        logger.info("Tabelas de Demandas Específicas verificadas/criadas!")
        logger.info("Tabelas de Termos de Uso e Privacidade verificadas/criadas!")

        conn.commit()

        # Criar usuário admin inicial se não existir
        cur.execute("SELECT COUNT(*) FROM usuarios WHERE email = %s", ("admin@vaucherealvares.com.br",))
        if cur.fetchone()[0] == 0:
            senha_hash_admin = hash_senha(ADMIN_INICIAL_SENHA)
            cur.execute("""
                INSERT INTO usuarios (email, senha_hash, nome, is_admin)
                VALUES (%s, %s, %s, %s)
            """, ("admin@vaucherealvares.com.br", senha_hash_admin, "Administrador", True))
            conn.commit()
            logger.info("Usuário admin inicial criado!")

        cur.close()
        conn.close()
        logger.info("Banco de dados inicializado com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")


# ============================================
# FUNÇÕES CRUD - USUÁRIOS
# ============================================

def buscar_usuario_por_email(email: str) -> Optional[dict]:
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
        senha_hash_user = hash_senha(senha)
        cur.execute("""
            INSERT INTO usuarios (email, senha_hash, nome, is_admin)
            VALUES (%s, %s, %s, %s)
        """, (email, senha_hash_user, nome, is_admin))
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
# FUNÇÕES CRUD - CADASTROS
# ============================================

def salvar_cadastro(cadastro: dict) -> bool:
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
                "data_assinatura": row.get("data_assinatura").isoformat() if row.get("data_assinatura") else None,
                "assinaturas_digitais": row.get("assinaturas_digitais") if isinstance(row.get("assinaturas_digitais"), dict) else json.loads(row.get("assinaturas_digitais") or "{}"),
                "documentos_finais": row.get("documentos_finais") if isinstance(row.get("documentos_finais"), dict) else json.loads(row.get("documentos_finais") or "{}")
            })
        return cadastros
    except Exception as e:
        logger.error(f"Erro ao carregar cadastros: {e}")
        return []


def buscar_cadastro(cadastro_id: str) -> Optional[dict]:
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
                "data_assinatura": row.get("data_assinatura").isoformat() if row.get("data_assinatura") else None,
                "assinaturas_digitais": row.get("assinaturas_digitais") if isinstance(row.get("assinaturas_digitais"), dict) else json.loads(row.get("assinaturas_digitais") or "{}"),
                "documentos_finais": row.get("documentos_finais") if isinstance(row.get("documentos_finais"), dict) else json.loads(row.get("documentos_finais") or "{}")
            }
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar cadastro: {e}")
        return None


def atualizar_status(cadastro_id: str, status: str) -> bool:
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
# FUNÇÕES CRUD - FINANCEIRO
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


def buscar_financeiro(cadastro_id: str) -> Optional[dict]:
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
