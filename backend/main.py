"""
Backend - Vaucher & Álvares Sistema de Cadastro
FastAPI + Geração de Documentos + Envio de E-mail
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

# ============================================
# CONFIGURAÇÃO
# ============================================

app = FastAPI(
    title="Vaucher & Álvares - API",
    description="Sistema de cadastro de clientes e geração de documentos",
    version="1.0.0"
)

# CORS - permitir acesso dos frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://cadastro.vaucherealvares.com.br",
        "https://painel.vaucherealvares.com.br",
        # Adicione seus domínios Vercel aqui após deploy
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
DATA_DIR = os.path.join(BASE_DIR, "data")

# Criar diretórios se não existirem
for dir_path in [MODELOS_DIR, UPLOADS_DIR, GERADOS_DIR, DATA_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Arquivo de dados (em produção, usar banco de dados)
CADASTROS_FILE = os.path.join(DATA_DIR, "cadastros.json")

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

class CadastroCompleto(BaseModel):
    id: str
    data: str
    status: str  # pendente, validado, enviado
    dados: DadosCliente
    documentos: List[str] = []

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

def carregar_cadastros() -> List[dict]:
    """Carrega cadastros do arquivo JSON."""
    if os.path.exists(CADASTROS_FILE):
        with open(CADASTROS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def salvar_cadastros(cadastros: List[dict]):
    """Salva cadastros no arquivo JSON."""
    with open(CADASTROS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cadastros, f, ensure_ascii=False, indent=2)

def gerar_token(email: str) -> str:
    """Gera um token simples para autenticação."""
    timestamp = datetime.now().isoformat()
    data = f"{email}:{timestamp}:vaucher_secret_key"
    return hashlib.sha256(data.encode()).hexdigest()

# Usuários do sistema (em produção, usar banco de dados)
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
    
    def _gerar_documento(self, modelo_path: str, dados: dict, nome_saida: str) -> str:
        if not os.path.exists(modelo_path):
            raise FileNotFoundError(f"Modelo não encontrado: {modelo_path}")
        
        # Criar pasta do cliente
        cliente_dir = os.path.join(GERADOS_DIR, dados.get('cpf', 'temp').replace('.', '').replace('-', ''))
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
    
    def gerar_contrato(self, dados: dict) -> str:
        nome = dados.get('nome', 'Cliente').replace(' ', '_')
        nome_arquivo = f"Contrato_Honorarios_{nome}.docx"
        return self._gerar_documento(self.modelo_contrato, dados, nome_arquivo)
    
    def gerar_procuracao(self, dados: dict) -> str:
        nome = dados.get('nome', 'Cliente').replace(' ', '_')
        nome_arquivo = f"Procuracao_{nome}.docx"
        return self._gerar_documento(self.modelo_procuracao, dados, nome_arquivo)
    
    def gerar_todos(self, dados: dict) -> dict:
        return {
            'contrato': self.gerar_contrato(dados),
            'procuracao': self.gerar_procuracao(dados)
        }

gerador = GeradorDocumentos()

# ============================================
# ENVIO DE E-MAIL
# ============================================

class EmailService:
    def __init__(self):
        # Configurar via variáveis de ambiente
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_pass = os.getenv('SMTP_PASS', '')
        self.from_email = os.getenv('FROM_EMAIL', 'atendimento@vaucherealvares.com')
    
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
    
    def enviar_documentos(self, destinatario: str, nome: str, arquivos: List[str]) -> bool:
        """Envia documentos para o cliente."""
        assunto = "Seus Documentos - Vaucher & Álvares Advogados"
        
        corpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #8B1538;">Vaucher & Álvares Advogados</h2>
                <p>Prezado(a) <strong>{nome}</strong>,</p>
                <p>Seguem em anexo os documentos para sua análise e assinatura:</p>
                <ul>
                    <li>Contrato de Honorários Advocatícios</li>
                    <li>Procuração Ad Judicia</li>
                </ul>
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
        if not self.smtp_user or not self.smtp_pass:
            print("⚠️ Credenciais SMTP não configuradas. E-mail não enviado.")
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
                        with open(arquivo, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename={os.path.basename(arquivo)}'
                            )
                            msg.attach(part)
            
            # Enviar
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Erro ao enviar e-mail: {e}")
            return False

email_service = EmailService()

# ============================================
# ROTAS DA API
# ============================================

@app.get("/")
def root():
    return {"message": "Vaucher & Álvares API", "status": "online"}

@app.get("/health")
def health():
    return {"status": "healthy"}

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
    cadastros = carregar_cadastros()
    
    novo_cadastro = {
        "id": uuid.uuid4().hex[:12],
        "data": datetime.now().strftime("%d/%m/%Y"),
        "data_hora": datetime.now().isoformat(),
        "status": "pendente",
        "dados": dados.dict(),
        "documentos": []
    }
    
    cadastros.insert(0, novo_cadastro)
    salvar_cadastros(cadastros)
    
    # Enviar e-mail de confirmação
    email_service.enviar_confirmacao_cadastro(dados.email, dados.nome)
    
    return {"success": True, "id": novo_cadastro["id"]}

@app.get("/api/cadastros")
def listar_cadastros():
    """Lista todos os cadastros (painel admin)."""
    return carregar_cadastros()

@app.get("/api/cadastros/{cadastro_id}")
def obter_cadastro(cadastro_id: str):
    """Obtém detalhes de um cadastro específico."""
    cadastros = carregar_cadastros()
    for c in cadastros:
        if c["id"] == cadastro_id:
            return c
    raise HTTPException(status_code=404, detail="Cadastro não encontrado")

@app.put("/api/cadastros/{cadastro_id}/validar")
def validar_cadastro(cadastro_id: str):
    """Marca cadastro como validado."""
    cadastros = carregar_cadastros()
    for c in cadastros:
        if c["id"] == cadastro_id:
            c["status"] = "validado"
            salvar_cadastros(cadastros)
            return {"success": True}
    raise HTTPException(status_code=404, detail="Cadastro não encontrado")

@app.post("/api/cadastros/{cadastro_id}/gerar-documentos")
def gerar_e_enviar_documentos(cadastro_id: str):
    """Gera documentos e envia para o cliente."""
    cadastros = carregar_cadastros()
    cadastro = None
    
    for c in cadastros:
        if c["id"] == cadastro_id:
            cadastro = c
            break
    
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    try:
        # Gerar documentos
        dados = cadastro["dados"]
        arquivos = gerador.gerar_todos(dados)
        
        # Enviar por e-mail
        email_service.enviar_documentos(
            dados["email"],
            dados["nome"],
            [arquivos["contrato"], arquivos["procuracao"]]
        )
        
        # Atualizar status
        cadastro["status"] = "enviado"
        cadastro["arquivos_gerados"] = arquivos
        salvar_cadastros(cadastros)
        
        return {
            "success": True,
            "arquivos": arquivos
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cadastros/{cadastro_id}/download/{tipo}")
def download_documento(cadastro_id: str, tipo: str):
    """Faz download de um documento gerado."""
    cadastros = carregar_cadastros()
    
    for c in cadastros:
        if c["id"] == cadastro_id and "arquivos_gerados" in c:
            arquivo = c["arquivos_gerados"].get(tipo)
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
    cadastros = carregar_cadastros()
    
    for c in cadastros:
        if c["id"] == cadastro_id:
            # Salvar arquivo
            cliente_dir = os.path.join(UPLOADS_DIR, cadastro_id)
            os.makedirs(cliente_dir, exist_ok=True)
            
            file_path = os.path.join(cliente_dir, arquivo.filename)
            with open(file_path, "wb") as f:
                content = await arquivo.read()
                f.write(content)
            
            # Atualizar cadastro
            if arquivo.filename not in c["documentos"]:
                c["documentos"].append(arquivo.filename)
            salvar_cadastros(cadastros)
            
            return {"success": True, "filename": arquivo.filename}
    
    raise HTTPException(status_code=404, detail="Cadastro não encontrado")

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
