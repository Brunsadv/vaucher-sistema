"""
Backend - Vaucher & Álvares Sistema de Cadastro
FastAPI + PostgreSQL + Geração de Documentos + Resend para E-mail
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
    version="2.1.0"
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
ENVIO_DIR = os.path.join(BASE_DIR, "documentos_envio")

# Criar diretórios se não existirem
for dir_path in [MODELOS_DIR, UPLOADS_DIR, GERADOS_DIR, ENVIO_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Banco de dados e E-mail
DATABASE_URL = os.getenv("DATABASE_URL")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")

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

@app.on_event("startup")
def startup():
    logger.info("Iniciando aplicação...")
    logger.info(f"RESEND_API_KEY configurada: {bool(RESEND_API_KEY)}")
    logger.info(f"FROM_EMAIL: {FROM_EMAIL}")
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
        "from": FROM_EMAIL,
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

def preparar_anexo(caminho_arquivo: str) -> dict:
    """Prepara um arquivo para ser anexado ao e-mail."""
    if not os.path.exists(caminho_arquivo):
        return None
    
    with open(caminho_arquivo, "rb") as f:
        conteudo = base64.b64encode(f.read()).decode("utf-8")
    
    return {
        "filename": os.path.basename(caminho_arquivo),
        "content": conteudo
    }

# ============================================
# ROTAS DA API
# ============================================

@app.get("/")
def root():
    return {"message": "Vaucher & Álvares API", "status": "online", "version": "2.1"}

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
    user = USUARIOS.get(request.email)
    
    if user and user['senha'] == request.senha:
        token = gerar_token(request.email)
        return LoginResponse(success=True, token=token, nome=user['nome'])
    
    return LoginResponse(success=False, message="E-mail ou senha incorretos")

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
        
        # Enviar e-mail de confirmação
        try:
            corpo_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #8B1538;">Vaucher & Álvares Advogados</h2>
                    <p>Prezado(a) <strong>{dados.nome}</strong>,</p>
                    <p>Seu cadastro foi recebido com sucesso!</p>
                    <p>Nossa equipe irá analisar as informações e documentos enviados. 
                    Em breve você receberá o Contrato de Honorários e a Procuração 
                    para assinatura.</p>
                    <p><strong>Prazo estimado:</strong> até 2 dias úteis.</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        Vaucher & Álvares Sociedade de Advogados<br>
                        atendimento@vaucherealvares.com
                    </p>
                </div>
            </body>
            </html>
            """
            await enviar_email_resend(
                dados.email,
                "Cadastro Recebido - Vaucher & Álvares Advogados",
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
    
    # Montar e-mail
    corpo_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #8B1538;">Vaucher & Álvares Advogados</h2>
            <p>Prezado(a) <strong>{dados['nome']}</strong>,</p>
            <p>Seguem em anexo os documentos para sua análise e assinatura.</p>
            {f'<p>{mensagem}</p>' if mensagem else ''}
            <p>Por favor, leia atentamente os documentos. Após assiná-los, 
            você pode enviá-los de volta por e-mail ou entregá-los 
            pessoalmente em nosso escritório.</p>
            <p><strong>Dúvidas?</strong> Entre em contato conosco.</p>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="font-size: 12px; color: #666;">
                Vaucher & Álvares Sociedade de Advogados<br>
                atendimento@vaucherealvares.com
            </p>
        </div>
    </body>
    </html>
    """
    
    sucesso = await enviar_email_resend(dados["email"], assunto, corpo_html, anexos_email)
    
    if sucesso:
        cadastro["status"] = "enviado"
        salvar_cadastro(cadastro)
        return {"success": True, "message": f"E-mail enviado para {dados['email']} com {len(anexos_email)} anexo(s)"}
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
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
