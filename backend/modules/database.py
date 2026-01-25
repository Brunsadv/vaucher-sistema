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
                data VARCHAR(50),
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
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='cadastros' AND column_name='atualizado_em') THEN
                    ALTER TABLE cadastros ADD COLUMN atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                END IF;
            END $$;
        """)

        # Migração: aumentar tamanho do campo data de VARCHAR(20) para VARCHAR(50)
        # O campo estava muito pequeno para ISO timestamps (ex: 2026-01-25T02:20:32.075846)
        cur.execute("""
            ALTER TABLE cadastros ALTER COLUMN data TYPE VARCHAR(50);
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
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                termos_aceitos_em TIMESTAMP
            )
        """)

        # Adicionar coluna termos_aceitos_em se não existir (migração)
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'usuarios' AND column_name = 'termos_aceitos_em'
                ) THEN
                    ALTER TABLE usuarios ADD COLUMN termos_aceitos_em TIMESTAMP;
                END IF;
            END $$;
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
                -- Novos campos para prestação de contas (21/01/2026)
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='financeiro' AND column_name='status') THEN
                    ALTER TABLE financeiro ADD COLUMN status VARCHAR(20) DEFAULT 'rascunho';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='financeiro' AND column_name='arquivo_gerado') THEN
                    ALTER TABLE financeiro ADD COLUMN arquivo_gerado VARCHAR(500);
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='financeiro' AND column_name='data_geracao') THEN
                    ALTER TABLE financeiro ADD COLUMN data_geracao TIMESTAMP;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='financeiro' AND column_name='data_assinatura') THEN
                    ALTER TABLE financeiro ADD COLUMN data_assinatura TIMESTAMP;
                END IF;
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='financeiro' AND column_name='periodo_prestacao') THEN
                    ALTER TABLE financeiro ADD COLUMN periodo_prestacao VARCHAR(100);
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

        # ========== HISTÓRICO DE IMPORTAÇÕES ==========

        # Tabela de histórico de importações
        cur.execute("""
            CREATE TABLE IF NOT EXISTS historico_importacoes (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR(50) NOT NULL,
                arquivo_nome VARCHAR(255),
                arquivo_tamanho INTEGER,
                processos_criados INTEGER DEFAULT 0,
                processos_atualizados INTEGER DEFAULT 0,
                andamentos_adicionados INTEGER DEFAULT 0,
                erros INTEGER DEFAULT 0,
                detalhes JSONB DEFAULT '{}',
                usuario_id INTEGER REFERENCES usuarios(id),
                usuario_nome VARCHAR(255),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_historico_tipo ON historico_importacoes(tipo)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_historico_data ON historico_importacoes(criado_em DESC)")

        logger.info("Tabela de histórico de importações verificada/criada!")

        # ========== BANNERS E NOTÍCIAS ==========

        # Tabela de banners/notícias para o portal do cliente
        cur.execute("""
            CREATE TABLE IF NOT EXISTS banners (
                id SERIAL PRIMARY KEY,
                tipo VARCHAR(20) NOT NULL DEFAULT 'info',
                titulo VARCHAR(255) NOT NULL,
                conteudo TEXT NOT NULL,
                link_url VARCHAR(500),
                link_texto VARCHAR(100),
                ativo BOOLEAN DEFAULT TRUE,
                data_inicio DATE,
                data_fim DATE,
                ordem INTEGER DEFAULT 0,
                criado_por VARCHAR(255),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_banners_ativo ON banners(ativo)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_banners_ordem ON banners(ordem)")

        logger.info("Tabela de banners verificada/criada!")

        # ========== PRAZOS PROCESSUAIS ==========

        # Tabela de prazos processuais
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prazos_processuais (
                id SERIAL PRIMARY KEY,
                processo_id INTEGER REFERENCES processos(id) ON DELETE CASCADE,
                tipo VARCHAR(100) NOT NULL,
                descricao TEXT NOT NULL,
                data_inicio DATE NOT NULL,
                data_fim DATE NOT NULL,
                dias_uteis BOOLEAN DEFAULT TRUE,
                status VARCHAR(20) DEFAULT 'pendente',
                prioridade VARCHAR(20) DEFAULT 'normal',
                origem VARCHAR(50) DEFAULT 'manual',
                movimento_origem TEXT,
                observacoes TEXT,
                concluido_em TIMESTAMP,
                concluido_por VARCHAR(255),
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("CREATE INDEX IF NOT EXISTS idx_prazos_processo ON prazos_processuais(processo_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_prazos_status ON prazos_processuais(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_prazos_data_fim ON prazos_processuais(data_fim)")

        logger.info("Tabela de prazos processuais verificada/criada!")

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
        cur.execute("SELECT id, email, nome, is_admin, ativo, criado_em, termos_aceitos_em FROM usuarios ORDER BY criado_em DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar usuários: {e}")
        return []


def verificar_termos_aceitos(user_id: int) -> bool:
    """Verifica se o usuário já aceitou os termos de uso."""
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT termos_aceitos_em FROM usuarios WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return bool(row and row.get("termos_aceitos_em"))
    except Exception as e:
        logger.error(f"Erro ao verificar termos aceitos: {e}")
        return False


def registrar_aceite_termos(user_id: int) -> bool:
    """Registra o aceite dos termos de uso pelo usuário."""
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE usuarios SET termos_aceitos_em = CURRENT_TIMESTAMP WHERE id = %s",
            (user_id,)
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao registrar aceite dos termos: {e}")
        return False


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
                "observacoes": row["observacoes"] or "",
                # Novos campos de prestação de contas
                "status": row.get("status") or "rascunho",
                "arquivo_gerado": row.get("arquivo_gerado") or "",
                "data_geracao": row["data_geracao"].isoformat() if row.get("data_geracao") else None,
                "data_assinatura": row["data_assinatura"].isoformat() if row.get("data_assinatura") else None,
                "periodo_prestacao": row.get("periodo_prestacao") or ""
            }
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar financeiro: {e}")
        return None


def atualizar_status_prestacao(cadastro_id: str, status: str, arquivo_gerado: str = None) -> bool:
    """Atualiza o status e arquivo da prestação de contas."""
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        if arquivo_gerado:
            cur.execute("""
                UPDATE financeiro
                SET status = %s, arquivo_gerado = %s, data_geracao = CURRENT_TIMESTAMP, atualizado_em = CURRENT_TIMESTAMP
                WHERE cadastro_id = %s
            """, (status, arquivo_gerado, cadastro_id))
        else:
            cur.execute("""
                UPDATE financeiro
                SET status = %s, atualizado_em = CURRENT_TIMESTAMP
                WHERE cadastro_id = %s
            """, (status, cadastro_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar status prestação: {e}")
        return False


def marcar_prestacao_assinada(cadastro_id: str) -> bool:
    """Marca a prestação de contas como assinada."""
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE financeiro
            SET status = 'assinado', data_assinatura = CURRENT_TIMESTAMP, atualizado_em = CURRENT_TIMESTAMP
            WHERE cadastro_id = %s
        """, (cadastro_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao marcar prestação assinada: {e}")
        return False


# ============================================
# FUNÇÕES CRUD - BANNERS/NOTÍCIAS
# ============================================

def listar_banners(apenas_ativos: bool = False) -> List[dict]:
    """Lista todos os banners."""
    conn = get_db()
    if not conn:
        return []

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        if apenas_ativos:
            cur.execute("""
                SELECT * FROM banners
                WHERE ativo = TRUE
                AND (data_inicio IS NULL OR data_inicio <= CURRENT_DATE)
                AND (data_fim IS NULL OR data_fim >= CURRENT_DATE)
                ORDER BY ordem ASC, criado_em DESC
            """)
        else:
            cur.execute("SELECT * FROM banners ORDER BY ordem ASC, criado_em DESC")
        banners = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(b) for b in banners]
    except Exception as e:
        logger.error(f"Erro ao listar banners: {e}")
        return []


def buscar_banner(banner_id: int) -> Optional[dict]:
    """Busca um banner pelo ID."""
    conn = get_db()
    if not conn:
        return None

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM banners WHERE id = %s", (banner_id,))
        banner = cur.fetchone()
        cur.close()
        conn.close()
        return dict(banner) if banner else None
    except Exception as e:
        logger.error(f"Erro ao buscar banner: {e}")
        return None


def criar_banner(dados: dict) -> Optional[int]:
    """Cria um novo banner."""
    conn = get_db()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO banners (tipo, titulo, conteudo, link_url, link_texto, ativo, data_inicio, data_fim, ordem, criado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            dados.get("tipo", "info"),
            dados.get("titulo"),
            dados.get("conteudo"),
            dados.get("link_url"),
            dados.get("link_texto"),
            dados.get("ativo", True),
            dados.get("data_inicio"),
            dados.get("data_fim"),
            dados.get("ordem", 0),
            dados.get("criado_por")
        ))
        banner_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return banner_id
    except Exception as e:
        logger.error(f"Erro ao criar banner: {e}")
        return None


def atualizar_banner(banner_id: int, dados: dict) -> bool:
    """Atualiza um banner."""
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE banners
            SET tipo = %s, titulo = %s, conteudo = %s, link_url = %s, link_texto = %s,
                ativo = %s, data_inicio = %s, data_fim = %s, ordem = %s, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (
            dados.get("tipo", "info"),
            dados.get("titulo"),
            dados.get("conteudo"),
            dados.get("link_url"),
            dados.get("link_texto"),
            dados.get("ativo", True),
            dados.get("data_inicio"),
            dados.get("data_fim"),
            dados.get("ordem", 0),
            banner_id
        ))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar banner: {e}")
        return False


def deletar_banner(banner_id: int) -> bool:
    """Deleta um banner."""
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM banners WHERE id = %s", (banner_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar banner: {e}")
        return False


# ============================================
# FUNÇÕES CRUD - PROCESSOS
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
            dados.get("num_parcelas") or dados.get("numero_parcelas") or 1,
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
        num_parcelas = int(dados.get("num_parcelas") or dados.get("numero_parcelas") or 1)
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


def criar_contrato_honorarios(cadastro_id: str, dados: dict) -> int:
    """Cria um contrato de honorarios."""
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
            dados.get("num_parcelas") or dados.get("numero_parcelas") or 1,
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

        # Gerar parcelas automaticamente
        num_parcelas = dados.get("num_parcelas") or dados.get("numero_parcelas") or 1
        if int(num_parcelas) >= 1:
            gerar_parcelas_contrato(contrato_id, dados)

        return contrato_id
    except Exception as e:
        logger.error(f"Erro ao criar contrato: {e}")
        return None


# ============================================
# FUNÇÕES CRUD - PARCELAS
# ============================================

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

        cur.execute("SELECT parcela_id FROM comprovantes WHERE id = %s", (comprovante_id,))
        row = cur.fetchone()
        if not row:
            return False

        parcela_id = row[0]

        cur.execute("""
            UPDATE comprovantes SET
                status = 'aprovado',
                verificado_em = CURRENT_TIMESTAMP,
                verificado_por = %s
            WHERE id = %s
        """, (admin_email, comprovante_id))

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
# FUNÇÕES CRUD - ANDAMENTOS (LEGACY)
# ============================================

def listar_andamentos(cadastro_id: str, apenas_visiveis: bool = False) -> list:
    """Lista andamentos de um cadastro (tabela andamentos legacy)."""
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
    """Cria um novo andamento (tabela andamentos legacy)."""
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
    """Deleta um andamento (tabela andamentos legacy)."""
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
# FUNÇÕES CRUD - MENSAGENS
# ============================================

def listar_mensagens(cadastro_id: str) -> list:
    """Lista mensagens de um cliente."""
    from modules.config import converter_para_cuiaba
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
            "criado_em": converter_para_cuiaba(row["criado_em"])
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
# COMPROVANTES
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


# ============================================
# DOCUMENTOS ADMIN (ENVIADOS PELO ESCRITÓRIO)
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
    import os
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT arquivo_path FROM documentos_admin WHERE id = %s", (doc_id,))
        row = cur.fetchone()

        if row and row["arquivo_path"]:
            if os.path.exists(row["arquivo_path"]):
                os.remove(row["arquivo_path"])

        cur.execute("DELETE FROM documentos_admin WHERE id = %s", (doc_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar documento admin: {e}")
        return False


# ============================================
# DOCUMENTOS EXTRAS (ENVIADOS PELO CLIENTE)
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
    import os
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT arquivo_path FROM documentos_extras WHERE id = %s", (doc_id,))
        row = cur.fetchone()

        if row and row["arquivo_path"]:
            if os.path.exists(row["arquivo_path"]):
                os.remove(row["arquivo_path"])

        cur.execute("DELETE FROM documentos_extras WHERE id = %s", (doc_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar documento extra: {e}")
        return False


# ============================================
# PROCESSO INFO (LEGACY - POR CADASTRO)
# ============================================

def buscar_processo_info(cadastro_id: str) -> dict:
    """Busca informações do processo de um cliente (modelo legacy)."""
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
    """Salva ou atualiza informações do processo (modelo legacy)."""
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
# AUTENTICAÇÃO DO CLIENTE (PORTAL)
# ============================================

def criar_cliente_auth(cadastro_id: str, senha: str) -> bool:
    """Cria autenticação para um cliente (recebe senha em texto plano)."""
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
    """Atualiza a senha de um cliente (recebe senha em texto plano)."""
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
