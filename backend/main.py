"""
Backend - Vaucher & Álvares Sistema de Cadastro
FastAPI + PostgreSQL + Geração de Documentos + Resend para E-mail
Com gerenciamento de usuários no banco de dados
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
    version="2.3.0"
)

# CORS - permitir acesso dos frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://cadastro.vaucherealvares.com.br",
        "https://painel.vaucherealvares.com.br",
        "https://cadastro.vaucherealvares.com",
        "https://painel.vaucherealvares.com",
        "https://vaucher-cliente.vercel.app",
        "https://vaucher-admin.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELOS_DIR = os.path.join(BASE_DIR, "modelos")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
GERADOS_DIR = os.path.join(BASE_DIR, "documentos_gerados")
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
    # Criar payload com dados do usuário
    payload = f"{user_id}:{email}:{is_admin}"
    # Criar assinatura
    signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
    # Codificar em base64
    token_data = base64.b64encode(f"{payload}:{signature}".encode()).decode()
    return token_data

def decodificar_token(token: str) -> dict:
    """Decodifica e valida um token."""
    try:
        # Decodificar base64
        decoded = base64.b64decode(token.encode()).decode()
        parts = decoded.rsplit(":", 1)
        if len(parts) != 2:
            return None
        
        payload, signature = parts
        
        # Verificar assinatura
        expected_signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
        if signature != expected_signature:
            return None
        
        # Extrair dados
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
    
    # Verificar se o usuário ainda existe e está ativo
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
                arquivos_gerados JSONB DEFAULT '{}'
            )
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
            INSERT INTO cadastros (id, data, data_hora, status, dados, documentos, arquivos_gerados)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                dados = EXCLUDED.dados,
                documentos = EXCLUDED.documentos,
                arquivos_gerados = EXCLUDED.arquivos_gerados
        """, (
            cadastro["id"],
            cadastro["data"],
            cadastro.get("data_hora", datetime.now().isoformat()),
            cadastro["status"],
            json.dumps(cadastro["dados"]),
            json.dumps(cadastro.get("documentos", [])),
            json.dumps(cadastro.get("arquivos_gerados", {}))
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
                "arquivos_gerados": row["arquivos_gerados"] if isinstance(row["arquivos_gerados"], dict) else json.loads(row["arquivos_gerados"] or "{}")
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
                "arquivos_gerados": row["arquivos_gerados"] if isinstance(row["arquivos_gerados"], dict) else json.loads(row["arquivos_gerados"] or "{}")
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

# ============================================
# GERADOR DE DOCUMENTOS
# ============================================

class GeradorDocumentos:
    def __init__(self):
        self.modelo_contrato = os.path.join(MODELOS_DIR, 'CONTRATO_Modelo.docx')
        self.modelo_procuracao = os.path.join(MODELOS_DIR, 'Procuracao_Modelo.docx')
    
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
        
        # Objeto do contrato
        objeto = dados.get('objeto_contrato', '')
        if objeto:
            resultado = resultado.replace(
                'advocatícios para .',
                f'advocatícios para {objeto}.'
            )
        
        # Honorários
        honorarios = dados.get('honorarios', '')
        if honorarios:
            resultado = resultado.replace(
                'fixar-se-ão em .',
                f'fixar-se-ão em {honorarios}.'
            )
        
        # Datas
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
# ROTAS DA API
# ============================================

@app.get("/")
def root():
    return {"message": "Vaucher & Álvares API", "status": "online", "version": "2.3"}

@app.get("/health")
def health():
    return {
        "status": "healthy", 
        "database": "connected" if get_db() else "disconnected",
        "email": "resend" if RESEND_API_KEY else "not_configured"
    }

# --- AUTENTICAÇÃO ---

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
    # Com tokens autocontidos, não precisa fazer nada no servidor
    return {"success": True}

# --- GERENCIAMENTO DE USUÁRIOS (APENAS ADMIN) ---

@app.get("/api/usuarios")
def listar_todos_usuarios(usuario: dict = Depends(verificar_admin)):
    """Lista todos os usuários (apenas admin)."""
    return listar_usuarios()

@app.post("/api/usuarios")
def criar_novo_usuario(dados: NovoUsuario, usuario: dict = Depends(verificar_admin)):
    """Cria um novo usuário (apenas admin)."""
    # Verificar se já existe
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
    # Não permitir desativar a si mesmo
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
        
        # Enviar e-mail de confirmação com logo
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
        
        # Tentar remover arquivos do cliente (se existirem)
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
    """Envia documentos por e-mail - VOCÊ escolhe quais arquivos anexar."""
    logger.info(f"Enviando e-mail para cadastro: {cadastro_id}")
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    dados = cadastro["dados"]
    anexos_email = []
    
    # Processar arquivos enviados pelo admin
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
    
    # URL do portal para enviar documentos assinados
    PORTAL_URL = os.getenv("PORTAL_URL", "https://cadastro.vaucherealvares.com")
    link_envio = f"{PORTAL_URL}/enviar-assinados?id={cadastro_id}"
    
    # Montar e-mail com logo
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
    
    # Criar workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Cadastros"
    
    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="8B1538", end_color="8B1538", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Cabeçalhos
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
    
    # Mapeamento de tipos de demanda
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
    
    # Mapeamento de status
    status_map = {
        'pendente': 'Pendente',
        'validado': 'Validado',
        'documentos_gerados': 'Documentos Gerados',
        'enviado': 'Enviado',
        'assinado': 'Documentos Assinados Recebidos'
    }
    
    # Dados
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
    
    # Ajustar largura das colunas
    column_widths = [12, 12, 15, 30, 15, 15, 12, 12, 12, 20, 40, 30, 15, 25, 50, 50, 30]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width
    
    # Congelar cabeçalho
    ws.freeze_panes = "A2"
    
    # Salvar em memória
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Nome do arquivo com data
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
# ÁREA DO CLIENTE - DEVOLUÇÃO DE DOCUMENTOS
# ============================================

@app.get("/api/cliente/{cadastro_id}")
def cliente_ver_cadastro(cadastro_id: str):
    """Cliente visualiza seu próprio cadastro (sem autenticação, mas limitado)."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    # Retorna apenas informações básicas (sem dados sensíveis do admin)
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
    
    # Verificar se o status permite envio de documentos
    if cadastro["status"] not in ["enviado", "assinado"]:
        raise HTTPException(status_code=400, detail="Você ainda não recebeu os documentos para assinar")
    
    # Salvar na pasta uploads (que tem volume persistente) com subpasta "assinados"
    cliente_assinados_dir = os.path.join(UPLOADS_DIR, cadastro_id, "assinados")
    os.makedirs(cliente_assinados_dir, exist_ok=True)
    
    arquivos_salvos = []
    
    for arquivo in arquivos:
        if arquivo.filename:
            # Adicionar prefixo para identificar como assinado
            nome_arquivo = f"ASSINADO_{arquivo.filename}"
            file_path = os.path.join(cliente_assinados_dir, nome_arquivo)
            
            with open(file_path, "wb") as f:
                content = await arquivo.read()
                f.write(content)
            
            arquivos_salvos.append(nome_arquivo)
            logger.info(f"Documento assinado salvo: {nome_arquivo}")
    
    if not arquivos_salvos:
        raise HTTPException(status_code=400, detail="Nenhum arquivo enviado")
    
    # Atualizar cadastro
    if "documentos_assinados" not in cadastro:
        cadastro["documentos_assinados"] = []
    
    cadastro["documentos_assinados"].extend(arquivos_salvos)
    cadastro["status"] = "assinado"
    cadastro["data_assinatura"] = datetime.now().isoformat()
    salvar_cadastro(cadastro)
    
    # Enviar e-mail para o escritório notificando
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
            FROM_EMAIL,  # Envia para o próprio escritório
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
    # Usar pasta uploads (que tem volume persistente)
    file_path = os.path.join(UPLOADS_DIR, cadastro_id, "assinados", filename)
    
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename, media_type="application/octet-stream")
    
    raise HTTPException(status_code=404, detail="Arquivo não encontrado")

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
