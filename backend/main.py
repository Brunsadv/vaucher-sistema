"""
Backend - Vaucher & Álvares Sistema de Cadastro
FastAPI + PostgreSQL + Geração de Documentos + Envio de E-mail
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import os
import json
import zipfile
import shutil
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import uuid
import hashlib
import logging

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
    version="2.0.0"
)

# CORS - permitir acesso dos frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://cadastro.vaucherealvares.com.br",
        "https://painel.vaucherealvares.com.br",
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

# Criar diretórios se não existirem
for dir_path in [MODELOS_DIR, UPLOADS_DIR, GERADOS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Banco de dados
DATABASE_URL = os.getenv("DATABASE_URL")

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
        conn.commit()
        cur.close()
        conn.close()
        logger.info("Banco de dados inicializado com sucesso!")
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")

# Inicializar banco ao iniciar
@app.on_event("startup")
def startup():
    logger.info("Iniciando aplicação...")
    init_db()

# ============================================
# FUNÇÕES DO BANCO
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
    message: Optional[str] = None

class EnviarEmailRequest(BaseModel):
    assunto: Optional[str] = "Documentos - Vaucher & Álvares Advogados"
    mensagem: Optional[str] = ""

# ============================================
# UTILITÁRIOS
# ============================================

def gerar_token(email: str) -> str:
    """Gera um token simples para autenticação."""
    timestamp = datetime.now().isoformat()
    data = f"{email}:{timestamp}:vaucher_secret_key"
    return hashlib.sha256(data.encode()).hexdigest()

# Usuários do sistema
USUARIOS = {
    "admin@vaucherealvares.com.br": {"senha": "admin123", "nome": "Administrador"},
    "bruno@vaucherealvares.com.br": {"senha": "bruno123", "nome": "Bruno Álvares"},
    "fernanda@vaucherealvares.com.br": {"senha": "fernanda123", "nome": "Fernanda Vaucher"},
}

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
        
        # Criar pasta do cliente usando ID do cadastro
        cliente_dir = os.path.join(GERADOS_DIR, cadastro_id)
        os.makedirs(cliente_dir, exist_ok=True)
        
        temp_dir = os.path.join(cliente_dir, f'temp_{uuid.uuid4().hex[:8]}')
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Extrair modelo
            with zipfile.ZipFile(modelo_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Substituir no document.xml
            doc_xml_path = os.path.join(temp_dir, 'word', 'document.xml')
            with open(doc_xml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            content = self._substituir_no_xml(content, dados)
            
            with open(doc_xml_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Criar documento
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
# ENVIO DE E-MAIL
# ============================================

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_pass = os.getenv('SMTP_PASS', '')
        self.from_email = os.getenv('FROM_EMAIL', 'atendimento@vaucherealvares.com')
        
        logger.info(f"EmailService configurado: host={self.smtp_host}, port={self.smtp_port}, user={self.smtp_user}")
    
    def enviar_confirmacao_cadastro(self, destinatario: str, nome: str) -> bool:
        """Envia e-mail de confirmação de cadastro."""
        assunto = "Cadastro Recebido - Vaucher & Álvares Advogados"
        
        corpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #8B1538;">Vaucher & Álvares Advogados</h2>
                <p>Prezado(a) <strong>{nome}</strong>,</p>
                <p>Seu cadastro foi recebido com sucesso!</p>
                <p>Nossa equipe irá analisar as informações e documentos enviados. 
                Em breve você receberá o Contrato de Honorários e a Procuração 
                para assinatura.</p>
                <p><strong>Prazo estimado:</strong> até 2 dias úteis.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">
                    Vaucher & Álvares Sociedade de Advogados<br>
                    Rua Lima, nº 106, Jardim das Américas, Cuiabá-MT<br>
                    (65) 3023-5959 | atendimento@vaucherealvares.com
                </p>
            </div>
        </body>
        </html>
        """
        
        return self._enviar(destinatario, assunto, corpo_html)
    
    def enviar_documentos(self, destinatario: str, nome: str, arquivos: List[str], assunto: str = None, mensagem_extra: str = "") -> bool:
        """Envia documentos para o cliente."""
        if not assunto:
            assunto = "Seus Documentos - Vaucher & Álvares Advogados"
        
        corpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #8B1538;">Vaucher & Álvares Advogados</h2>
                <p>Prezado(a) <strong>{nome}</strong>,</p>
                <p>Seguem em anexo os documentos para sua análise e assinatura.</p>
                {f'<p>{mensagem_extra}</p>' if mensagem_extra else ''}
                <p>Por favor, leia atentamente os documentos. Após assiná-los, 
                você pode enviá-los de volta por e-mail ou entregá-los 
                pessoalmente em nosso escritório.</p>
                <p><strong>Dúvidas?</strong> Entre em contato conosco.</p>
                <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">
                    Vaucher & Álvares Sociedade de Advogados<br>
                    Rua Lima, nº 106, Jardim das Américas, Cuiabá-MT<br>
                    (65) 3023-5959 | atendimento@vaucherealvares.com
                </p>
            </div>
        </body>
        </html>
        """
        
        return self._enviar(destinatario, assunto, corpo_html, arquivos)
    
    def _enviar(self, destinatario: str, assunto: str, corpo_html: str, anexos: List[str] = None) -> bool:
        """Envia e-mail."""
        logger.info(f"Tentando enviar e-mail para {destinatario}")
        logger.info(f"SMTP: {self.smtp_host}:{self.smtp_port}, User: {self.smtp_user}")
        
        if not self.smtp_user or not self.smtp_pass:
            logger.error("Credenciais SMTP não configuradas!")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = destinatario
            msg['Subject'] = assunto
            
            msg.attach(MIMEText(corpo_html, 'html'))
            
            # Anexos
            if anexos:
                for arquivo in anexos:
                    if os.path.exists(arquivo):
                        logger.info(f"Anexando arquivo: {arquivo}")
                        with open(arquivo, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename={os.path.basename(arquivo)}'
                            )
                            msg.attach(part)
                    else:
                        logger.warning(f"Arquivo não encontrado: {arquivo}")
            
            # Enviar
            logger.info("Conectando ao servidor SMTP...")
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.set_debuglevel(1)  # Debug SMTP
            server.starttls()
            logger.info("TLS iniciado, fazendo login...")
            server.login(self.smtp_user, self.smtp_pass)
            logger.info("Login OK, enviando mensagem...")
            server.send_message(msg)
            server.quit()
            
            logger.info(f"E-mail enviado com sucesso para {destinatario}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Erro de autenticação SMTP: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"Erro SMTP: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail: {e}")
            return False

email_service = EmailService()

# ============================================
# ROTAS DA API
# ============================================

@app.get("/")
def root():
    return {"message": "Vaucher & Álvares API", "status": "online", "version": "2.0"}

@app.get("/health")
def health():
    return {"status": "healthy", "database": "connected" if get_db() else "disconnected"}

# --- AUTENTICAÇÃO ---

@app.post("/api/login", response_model=LoginResponse)
def login(request: LoginRequest):
    """Autenticação do painel administrativo."""
    user = USUARIOS.get(request.email)
    
    if user and user['senha'] == request.senha:
        token = gerar_token(request.email)
        return LoginResponse(
            success=True,
            token=token,
            nome=user['nome']
        )
    
    return LoginResponse(
        success=False,
        message="E-mail ou senha incorretos"
    )

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
        
        # Tentar enviar e-mail de confirmação
        try:
            email_service.enviar_confirmacao_cadastro(dados.email, dados.nome)
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
        # Gerar documentos
        dados = cadastro["dados"]
        arquivos = gerador.gerar_todos(dados, cadastro_id)
        logger.info(f"Documentos gerados: {arquivos}")
        
        # Atualizar cadastro
        cadastro["status"] = "documentos_gerados"
        cadastro["arquivos_gerados"] = arquivos
        salvar_cadastro(cadastro)
        
        return {
            "success": True,
            "arquivos": arquivos,
            "message": "Documentos gerados com sucesso! Use o botão 'Enviar por E-mail' para enviar ao cliente."
        }
    except Exception as e:
        logger.error(f"Erro ao gerar documentos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cadastros/{cadastro_id}/enviar-email")
async def enviar_email_documentos(
    cadastro_id: str,
    assunto: str = Form(default="Seus Documentos - Vaucher & Álvares Advogados"),
    mensagem: str = Form(default=""),
    anexos_extras: List[UploadFile] = File(default=[])
):
    """Envia documentos por e-mail para o cliente."""
    logger.info(f"Enviando e-mail para cadastro: {cadastro_id}")
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    dados = cadastro["dados"]
    arquivos_para_enviar = []
    
    # Adicionar contrato e procuração se existirem
    if cadastro.get("arquivos_gerados"):
        if cadastro["arquivos_gerados"].get("contrato"):
            arquivos_para_enviar.append(cadastro["arquivos_gerados"]["contrato"])
        if cadastro["arquivos_gerados"].get("procuracao"):
            arquivos_para_enviar.append(cadastro["arquivos_gerados"]["procuracao"])
    
    # Salvar e adicionar anexos extras
    if anexos_extras:
        cliente_dir = os.path.join(GERADOS_DIR, cadastro_id)
        os.makedirs(cliente_dir, exist_ok=True)
        
        for anexo in anexos_extras:
            if anexo.filename:
                file_path = os.path.join(cliente_dir, anexo.filename)
                with open(file_path, "wb") as f:
                    content = await anexo.read()
                    f.write(content)
                arquivos_para_enviar.append(file_path)
                logger.info(f"Anexo extra salvo: {file_path}")
    
    # Enviar e-mail
    sucesso = email_service.enviar_documentos(
        dados["email"],
        dados["nome"],
        arquivos_para_enviar,
        assunto,
        mensagem
    )
    
    if sucesso:
        cadastro["status"] = "enviado"
        salvar_cadastro(cadastro)
        return {"success": True, "message": f"E-mail enviado para {dados['email']}"}
    else:
        raise HTTPException(status_code=500, detail="Erro ao enviar e-mail. Verifique os logs.")

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

# --- UPLOAD DE DOCUMENTOS ---

@app.post("/api/cadastros/{cadastro_id}/upload")
async def upload_documento(cadastro_id: str, arquivo: UploadFile = File(...)):
    """Recebe upload de documento do cliente."""
    logger.info(f"Upload recebido para cadastro {cadastro_id}: {arquivo.filename}")
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    # Salvar arquivo
    cliente_dir = os.path.join(UPLOADS_DIR, cadastro_id)
    os.makedirs(cliente_dir, exist_ok=True)
    
    file_path = os.path.join(cliente_dir, arquivo.filename)
    with open(file_path, "wb") as f:
        content = await arquivo.read()
        f.write(content)
    
    # Atualizar cadastro
    if arquivo.filename not in cadastro["documentos"]:
        cadastro["documentos"].append(arquivo.filename)
    salvar_cadastro(cadastro)
    
    return {"success": True, "filename": arquivo.filename}

@app.get("/api/cadastros/{cadastro_id}/uploads/{filename}")
def download_upload_cliente(cadastro_id: str, filename: str):
    """Faz download de um arquivo enviado pelo cliente."""
    file_path = os.path.join(UPLOADS_DIR, cadastro_id, filename)
    
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
    
    raise HTTPException(status_code=404, detail="Arquivo não encontrado")

# --- TESTE DE E-MAIL ---

@app.post("/api/teste-email")
def teste_email(destinatario: str = Form(...)):
    """Endpoint para testar envio de e-mail."""
    logger.info(f"Teste de e-mail para: {destinatario}")
    
    sucesso = email_service._enviar(
        destinatario,
        "Teste - Vaucher & Álvares Sistema",
        "<h1>Teste de E-mail</h1><p>Se você recebeu este e-mail, a configuração está funcionando!</p>"
    )
    
    if sucesso:
        return {"success": True, "message": f"E-mail de teste enviado para {destinatario}"}
    else:
        return {"success": False, "message": "Falha ao enviar e-mail. Verifique os logs no Railway."}

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
