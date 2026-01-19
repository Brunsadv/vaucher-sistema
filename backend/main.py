"""
Backend - Vaucher e Álvares Sistema de Cadastro
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
from datetime import datetime, timezone
# MIGRADO PARA modules/config.py
# try:
#     from zoneinfo import ZoneInfo
# except ImportError:
#     from backports.zoneinfo import ZoneInfo
import uuid
import hashlib
import logging
import httpx
import base64
import secrets
from io import BytesIO
from dateutil.relativedelta import relativedelta
from decimal import Decimal

# ============================================
# MIGRAÇÃO MODULAR - 18/01/2026
# Importar configurações do módulo config.py
# ============================================
from modules.config import (
    FUSO_CUIABA,
    converter_para_cuiaba,
    BASE_DIR,
    MODELOS_DIR,
    UPLOADS_DIR,
    GERADOS_DIR,
    STATIC_DIR,
    DATABASE_URL,
    RESEND_API_KEY,
    FROM_EMAIL,
    ADMIN_INICIAL_SENHA,
    TOKEN_SECRET,
    LOGO_URL,
    ALLOWED_ORIGINS,
    logger,
)

# Funções de segurança (migrado em 19/01/2026)
from modules.security import (
    hash_senha,
    verificar_senha,
    gerar_token,
    decodificar_token,
    gerar_token_cliente,
    decodificar_token_cliente,
    criar_email_html,
)

# Funções de banco de dados (migrado em 19/01/2026)
from modules.database import (
    get_db,
    init_db,
    buscar_usuario_por_email,
    listar_usuarios,
    criar_usuario,
    atualizar_usuario,
    deletar_usuario,
    salvar_cadastro,
    carregar_cadastros,
    buscar_cadastro,
    atualizar_status,
    salvar_financeiro,
    buscar_financeiro,
)

# Modelos Pydantic (migrado em 19/01/2026)
from modules.models import (
    DadosCliente,
    LoginRequest,
    LoginResponse,
    NovoUsuario,
    AtualizarUsuario,
    AlterarSenha,
    DepositoItem,
    SucumbenciaItem,
    RetencaoItem,
    DadosResidenciaMedica,
    SalvarRascunhoDemanda,
    FinanceiroData,
    ClienteLogin,
    ClienteAlterarSenha,
    ProcessoInfoModel,
    AndamentoModel,
    MensagemEnvio,
    SolicitacaoAtualizacao,
    EnvioAtualizacao,
    RejeicaoAtualizacao,
)

# Configurar logging detalhado (MIGRADO PARA modules/config.py)
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# PostgreSQL
import psycopg2
from psycopg2.extras import RealDictCursor

# MIGRADO PARA modules/config.py
# # Fuso horário de Cuiabá
# FUSO_CUIABA = ZoneInfo("America/Cuiaba")
#
# def converter_para_cuiaba(dt) -> str:
#     """Converte datetime para fuso horário de Cuiabá e retorna como ISO string."""
#     if not dt:
#         return None
#     try:
#         # Se o datetime não tem timezone, assume que é UTC
#         if dt.tzinfo is None:
#             dt = dt.replace(tzinfo=timezone.utc)
#         # Converte para Cuiabá
#         dt_cuiaba = dt.astimezone(FUSO_CUIABA)
#         return dt_cuiaba.isoformat()
#     except Exception as e:
#         logger.warning(f"Erro ao converter timezone: {e}")
#         return dt.isoformat() if dt else None

# ============================================
# CONFIGURAÇÃO
# ============================================

app = FastAPI(
    title="Vaucher e Álvares - API",
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
        "https://cadastro.vaucherealvares.com",
        "https://painel.vaucherealvares.com",
        "https://portal.vaucherealvares.com",
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

# MIGRADO PARA modules/config.py
# # Diretórios
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# MODELOS_DIR = os.path.join(BASE_DIR, "modelos")
# UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
# GERADOS_DIR = os.path.join(UPLOADS_DIR, "documentos_gerados")
# STATIC_DIR = os.path.join(BASE_DIR, "static")

# Criar diretórios se não existirem
for dir_path in [MODELOS_DIR, UPLOADS_DIR, GERADOS_DIR, STATIC_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Servir arquivos estáticos (logo)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# MIGRADO PARA modules/config.py
# # Banco de dados e E-mail
# DATABASE_URL = os.getenv("DATABASE_URL")
# RESEND_API_KEY = os.getenv("RESEND_API_KEY")
# FROM_EMAIL = os.getenv("FROM_EMAIL", "onboarding@resend.dev")
#
# # Senha inicial do admin (deve ser alterada após primeiro login)
# ADMIN_INICIAL_SENHA = os.getenv("ADMIN_INICIAL_SENHA", "VaucherAdmin2024!")
#
# # Chave secreta para tokens (em produção, usar variável de ambiente)
# TOKEN_SECRET = os.getenv("TOKEN_SECRET", "vaucher_alvares_secret_key_2024")
#
# # URL da logo
# LOGO_URL = "https://raw.githubusercontent.com/Brunsadv/vaucher-sistema/main/backend/static/Vaucher_e_Alvares-06.jpg"

# ============================================
# FUNÇÕES DE SEGURANÇA
# MIGRADO PARA modules/security.py
# ============================================

# def hash_senha(senha: str) -> str:
#     """Cria hash da senha usando SHA-256 com salt."""
#     salt = "vaucher_alvares_2024"
#     return hashlib.sha256(f"{senha}{salt}".encode()).hexdigest()
#
# def verificar_senha(senha: str, hash_armazenado: str) -> bool:
#     """Verifica se a senha corresponde ao hash."""
#     return hash_senha(senha) == hash_armazenado
#
# def gerar_token(user_id: int, email: str, is_admin: bool) -> str:
#     """Gera um token que contém informações do usuário."""
#     payload = f"{user_id}:{email}:{is_admin}"
#     signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
#     token_data = base64.b64encode(f"{payload}:{signature}".encode()).decode()
#     return token_data
#
# def decodificar_token(token: str) -> dict:
#     """Decodifica e valida um token."""
#     try:
#         decoded = base64.b64decode(token.encode()).decode()
#         parts = decoded.rsplit(":", 1)
#         if len(parts) != 2:
#             return None
#
#         payload, signature = parts
#
#         expected_signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
#         if signature != expected_signature:
#             return None
#
#         user_id, email, is_admin = payload.split(":")
#         return {
#             "id": int(user_id),
#             "email": email,
#             "is_admin": is_admin == "True"
#         }
#     except Exception:
#         return None

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
# MIGRADO PARA modules/security.py
# ============================================

# def criar_email_html(conteudo: str) -> str:
#     """Cria o HTML do e-mail com logo e rodapé padrão."""
#     return f"""
#     <html>
#     <body style="font-family: Arial, sans-serif; color: #333; background-color: #f5f5f5; margin: 0; padding: 20px;">
#         <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
#             <!-- Cabeçalho com Logo -->
#             <div style="background-color: #ffffff; padding: 30px; text-align: center; border-bottom: 3px solid #8B1538;">
#                 <img src="{LOGO_URL}" alt="Vaucher e Álvares Advogados" style="max-width: 300px; height: auto;" />
#             </div>
#
#             <!-- Conteúdo -->
#             <div style="padding: 30px;">
#                 {conteudo}
#             </div>
#
#             <!-- Rodapé -->
#             <div style="background-color: #f8f8f8; padding: 20px; text-align: center; border-top: 1px solid #eee;">
#                 <p style="font-size: 12px; color: #666; margin: 0;">
#                     <strong>Vaucher e Álvares Sociedade de Advogados</strong><br>
#                     Rua Lima, nº 106, Bairro Jardim das Américas, Cuiabá-MT<br>
#                     (65) 3025-1223 – email: atendimento@vaucherealvares.com
#                 </p>
#             </div>
#         </div>
#     </body>
#     </html>
#     """

# ============================================
# BANCO DE DADOS
# MIGRADO PARA modules/database.py em 19/01/2026
# ============================================
# As funções get_db, init_db, e demais funções CRUD
# foram migradas para modules/database.py

@app.on_event("startup")
def startup():
    logger.info("Iniciando aplicação...")
    logger.info(f"RESEND_API_KEY configurada: {bool(RESEND_API_KEY)}")
    logger.info(f"FROM_EMAIL: {FROM_EMAIL}")
    init_db()

# ============================================
# FUNÇÕES DO BANCO - USUÁRIOS, CADASTROS, FINANCEIRO
# MIGRADO PARA modules/database.py em 19/01/2026
# ============================================

# ============================================
# MODELOS DE DADOS
# MIGRADO PARA modules/models.py em 19/01/2026
# ============================================

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
        "from": f"Vaucher e Álvares <{FROM_EMAIL}>",
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
# FUNÇÕES DO BANCO - DEMANDAS ESPECÍFICAS
# ============================================

def salvar_dados_demanda(cadastro_id: str, tipo_demanda: str, dados: dict, status: str = "rascunho") -> bool:
    """Salva ou atualiza dados específicos de uma demanda."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO dados_demanda_especifica (cadastro_id, tipo_demanda, dados, status)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (cadastro_id, tipo_demanda) DO UPDATE SET
                dados = EXCLUDED.dados,
                status = EXCLUDED.status,
                atualizado_em = CURRENT_TIMESTAMP
        """, (cadastro_id, tipo_demanda, json.dumps(dados), status))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar dados da demanda: {e}")
        return False

def buscar_dados_demanda(cadastro_id: str, tipo_demanda: str) -> dict:
    """Busca dados específicos de uma demanda."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM dados_demanda_especifica 
            WHERE cadastro_id = %s AND tipo_demanda = %s
        """, (cadastro_id, tipo_demanda))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            dados = row['dados']
            if isinstance(dados, str):
                dados = json.loads(dados)
            return {
                "id": row['id'],
                "cadastro_id": row['cadastro_id'],
                "tipo_demanda": row['tipo_demanda'],
                "dados": dados,
                "status": row['status'],
                "criado_em": row['criado_em'].isoformat() if row['criado_em'] else None,
                "atualizado_em": row['atualizado_em'].isoformat() if row['atualizado_em'] else None
            }
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar dados da demanda: {e}")
        return None

def salvar_documento_demanda(cadastro_id: str, tipo_documento: str, nome_arquivo: str, 
                              nome_original: str, arquivo_path: str, descricao: str = "") -> bool:
    """Salva referência de documento específico da demanda."""
    conn = get_db()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO documentos_demanda (cadastro_id, tipo_documento, nome_arquivo, 
                nome_original, arquivo_path, descricao)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (cadastro_id, tipo_documento, nome_arquivo, nome_original, arquivo_path, descricao))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar documento da demanda: {e}")
        return False

def listar_documentos_demanda(cadastro_id: str) -> list:
    """Lista documentos específicos de uma demanda."""
    conn = get_db()
    if not conn:
        return []
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM documentos_demanda 
            WHERE cadastro_id = %s
            ORDER BY criado_em DESC
        """, (cadastro_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        return [{
            "id": row['id'],
            "tipo_documento": row['tipo_documento'],
            "nome_arquivo": row['nome_arquivo'],
            "nome_original": row['nome_original'],
            "descricao": row['descricao'],
            "arquivo_path": row.get('arquivo_path', ''),
            "criado_em": row['criado_em'].isoformat() if row['criado_em'] else None
        } for row in rows]
    except Exception as e:
        logger.error(f"Erro ao listar documentos da demanda: {e}")
        return []

def buscar_documento_demanda(doc_id: int) -> dict:
    """Busca um documento da demanda específico."""
    conn = get_db()
    if not conn:
        return None
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM documentos_demanda WHERE id = %s", (doc_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"Erro ao buscar documento da demanda: {e}")
        return None

# ============================================
# ROTAS DA API - BÁSICAS
# ============================================

@app.get("/")
def root():
    return {"message": "Vaucher e Álvares API", "status": "online", "version": "3.0"}

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
                "✅ Cadastro Recebido - Vaucher e Álvares Advogados",
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
    assunto: str = Form(default="Seus Documentos - Vaucher e Álvares Advogados"),
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


# ============================================
# FUNÇÕES DE EMAIL - ATUALIZAÇÃO CADASTRAL
# ============================================

def enviar_email_solicitacao_atualizacao(email: str, nome: str, motivo: str) -> bool:
    """Envia email ao cliente solicitando atualização cadastral."""
    import httpx
    
    try:
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1e3a5f; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Vaucher e Álvares</h1>
                <p style="color: #ccc; margin: 5px 0 0 0;">Sociedade de Advogados</p>
            </div>
            <div style="padding: 30px; background-color: #f9f9f9;">
                <h2 style="color: #1e3a5f;">Solicitação de Atualização Cadastral</h2>
                <p>Prezado(a) <strong>{nome}</strong>,</p>
                <p>O escritório <strong>Vaucher e Álvares Sociedade de Advogados</strong> 
                solicita que você atualize seus dados cadastrais em nosso sistema.</p>
                {f'<div style="background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0;"><strong>Motivo:</strong> {motivo}</div>' if motivo else ''}
                <p>Por favor, acesse o <strong>Portal do Cliente</strong> para enviar 
                os dados atualizados:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="https://portal.vaucherealvares.com" 
                       style="background-color: #1e3a5f; color: white; padding: 15px 40px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Acessar Portal do Cliente
                    </a>
                </p>
            </div>
            <div style="background-color: #eee; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                <p style="margin: 0;">Vaucher e Álvares Sociedade de Advogados</p>
                <p style="margin: 5px 0;">Rua Lima, nº 106, Jardim das Américas - Cuiabá/MT</p>
                <p style="margin: 5px 0;">Tel: (65) 3025-1223</p>
            </div>
        </div>
        """
        
        with httpx.Client() as client:
            response = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": FROM_EMAIL,
                    "to": email,
                    "subject": "Solicitação de Atualização Cadastral - Vaucher e Álvares",
                    "html": html
                }
            )
        
        if response.status_code in [200, 201]:
            logger.info(f"Email de solicitação de atualização enviado para {email}")
            return True
        else:
            logger.error(f"Erro ao enviar email: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Erro ao enviar email de solicitação: {e}")
        return False


def enviar_email_atualizacao_aprovada(email: str, nome: str) -> bool:
    """Notifica cliente que atualização foi aprovada."""
    import httpx
    
    try:
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1e3a5f; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Vaucher e Álvares</h1>
            </div>
            <div style="padding: 30px; background-color: #f9f9f9;">
                <div style="background-color: #d4edda; border-left: 4px solid #28a745; padding: 15px; margin-bottom: 20px;">
                    <h2 style="color: #155724; margin: 0;">✓ Atualização Cadastral Aprovada</h2>
                </div>
                <p>Prezado(a) <strong>{nome}</strong>,</p>
                <p>Sua atualização cadastral foi <strong style="color: #28a745;">aprovada</strong> 
                e seus dados foram atualizados em nosso sistema.</p>
                <p>Agradecemos pela colaboração!</p>
            </div>
            <div style="background-color: #eee; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                <p style="margin: 0;">Vaucher e Álvares Sociedade de Advogados</p>
            </div>
        </div>
        """
        
        with httpx.Client() as client:
            response = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": FROM_EMAIL,
                    "to": email,
                    "subject": "✓ Atualização Cadastral Aprovada - Vaucher e Álvares",
                    "html": html
                }
            )
        
        return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Erro ao enviar email de aprovação: {e}")
        return False


def enviar_email_atualizacao_rejeitada(email: str, nome: str, motivo: str) -> bool:
    """Notifica cliente que atualização foi rejeitada."""
    import httpx
    
    try:
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1e3a5f; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Vaucher e Álvares</h1>
            </div>
            <div style="padding: 30px; background-color: #f9f9f9;">
                <div style="background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin-bottom: 20px;">
                    <h2 style="color: #721c24; margin: 0;">Atualização Cadastral - Revisão Necessária</h2>
                </div>
                <p>Prezado(a) <strong>{nome}</strong>,</p>
                <p>Sua atualização cadastral precisa de ajustes antes de ser aprovada.</p>
                {f'<div style="background-color: #fff; border: 1px solid #ddd; padding: 15px; margin: 20px 0;"><strong>Observação:</strong> {motivo}</div>' if motivo else ''}
                <p>Por favor, acesse o Portal do Cliente e envie novamente os dados corrigidos.</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="https://portal.vaucherealvares.com" 
                       style="background-color: #1e3a5f; color: white; padding: 15px 40px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Acessar Portal
                    </a>
                </p>
            </div>
            <div style="background-color: #eee; padding: 20px; text-align: center; font-size: 12px; color: #666;">
                <p style="margin: 0;">Vaucher e Álvares Sociedade de Advogados</p>
            </div>
        </div>
        """
        
        with httpx.Client() as client:
            response = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": FROM_EMAIL,
                    "to": email,
                    "subject": "Atualização Cadastral - Revisão Necessária - Vaucher e Álvares",
                    "html": html
                }
            )
        
        return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Erro ao enviar email de rejeição: {e}")
        return False


def enviar_email_nova_atualizacao_admin(cadastro_id: str, nome_cliente: str) -> bool:
    """Notifica escritório sobre nova atualização cadastral."""
    import httpx
    
    try:
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1e3a5f; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">Nova Atualização Cadastral</h1>
            </div>
            <div style="padding: 30px; background-color: #f9f9f9;">
                <p>O cliente <strong>{nome_cliente}</strong> enviou uma atualização cadastral para análise.</p>
                <p><strong>ID do Cadastro:</strong> {cadastro_id}</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="https://painel.vaucherealvares.com" 
                       style="background-color: #1e3a5f; color: white; padding: 15px 40px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Acessar Painel Administrativo
                    </a>
                </p>
            </div>
        </div>
        """
        
        with httpx.Client() as client:
            response = client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": FROM_EMAIL,
                    "to": "atendimento@vaucherealvares.com",
                    "subject": f"Nova Atualização Cadastral - {nome_cliente}",
                    "html": html
                }
            )
        
        return response.status_code in [200, 201]
    except Exception as e:
        logger.error(f"Erro ao enviar email para admin: {e}")
        return False


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
async def upload_documento(
    cadastro_id: str, 
    arquivo: UploadFile = File(...),
    tipo_documento: str = Form(default=""),
    categoria: str = Form(default="")
):
    """Recebe upload de documento do cliente.
    
    Se tipo_documento ou categoria for especificado, salva na tabela documentos_demanda.
    Caso contrário, salva na lista de documentos genérica do cadastro.
    """
    logger.info(f"Upload recebido para cadastro {cadastro_id}: {arquivo.filename}, tipo: {tipo_documento}, categoria: {categoria}")
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    # Determinar o tipo do documento
    tipo = tipo_documento or categoria
    
    if tipo:
        # Salvar como documento específico da demanda
        cliente_dir = os.path.join(UPLOADS_DIR, "documentos_demanda", cadastro_id)
        os.makedirs(cliente_dir, exist_ok=True)
        
        ext = os.path.splitext(arquivo.filename)[1]
        nome_arquivo = f"{tipo}_{uuid.uuid4().hex[:8]}{ext}"
        arquivo_path = os.path.join(cliente_dir, nome_arquivo)
        
        content = await arquivo.read()
        with open(arquivo_path, "wb") as f:
            f.write(content)
        
        # Salvar na tabela documentos_demanda
        sucesso = salvar_documento_demanda(
            cadastro_id, tipo, nome_arquivo, 
            arquivo.filename, arquivo_path, tipo
        )
        
        if not sucesso:
            logger.error(f"Erro ao salvar documento da demanda no banco: {arquivo.filename}")
        
        return {"success": True, "filename": arquivo.filename, "tipo": tipo, "modo": "demanda"}
    else:
        # Comportamento padrão - salva na pasta do cliente e lista genérica
        cliente_dir = os.path.join(UPLOADS_DIR, cadastro_id)
        os.makedirs(cliente_dir, exist_ok=True)
        
        file_path = os.path.join(cliente_dir, arquivo.filename)
        content = await arquivo.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        if arquivo.filename not in cadastro["documentos"]:
            cadastro["documentos"].append(arquivo.filename)
        salvar_cadastro(cadastro)
        
        return {"success": True, "filename": arquivo.filename, "modo": "generico"}

@app.get("/api/cadastros/{cadastro_id}/uploads/{filename}")
def download_upload_cliente(cadastro_id: str, filename: str):
    """Faz download de um arquivo enviado pelo cliente."""
    file_path = os.path.join(UPLOADS_DIR, cadastro_id, filename)
    
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename, media_type="application/octet-stream")
    
    raise HTTPException(status_code=404, detail="Arquivo não encontrado")


@app.post("/api/cadastros/{cadastro_id}/uploads-categorizados")
async def upload_documentos_categorizados(
    cadastro_id: str,
    arquivos: List[UploadFile] = File(...),
    categorias: str = Form(default="")
):
    """Recebe múltiplos uploads com suas categorias.
    
    categorias deve ser uma string JSON com lista de categorias na mesma ordem dos arquivos.
    Exemplo: ["documentos_pessoais", "certificado_residencia", "contracheques"]
    
    Todos os documentos são salvos na tabela documentos_demanda.
    """
    logger.info(f"Uploads categorizados para cadastro {cadastro_id}: {len(arquivos)} arquivo(s)")
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    # Parse das categorias
    try:
        lista_categorias = json.loads(categorias) if categorias else []
    except:
        lista_categorias = []
    
    # Criar diretório
    cliente_dir = os.path.join(UPLOADS_DIR, "documentos_demanda", cadastro_id)
    os.makedirs(cliente_dir, exist_ok=True)
    
    salvos = []
    erros = []
    
    for i, arquivo in enumerate(arquivos):
        # Determinar categoria
        categoria = lista_categorias[i] if i < len(lista_categorias) else "documento_geral"
        
        try:
            ext = os.path.splitext(arquivo.filename)[1]
            nome_arquivo = f"{categoria}_{uuid.uuid4().hex[:8]}{ext}"
            arquivo_path = os.path.join(cliente_dir, nome_arquivo)
            
            content = await arquivo.read()
            with open(arquivo_path, "wb") as f:
                f.write(content)
            
            # Salvar na tabela documentos_demanda
            sucesso = salvar_documento_demanda(
                cadastro_id, categoria, nome_arquivo, 
                arquivo.filename, arquivo_path, categoria
            )
            
            if sucesso:
                salvos.append({"nome": arquivo.filename, "categoria": categoria})
            else:
                erros.append({"nome": arquivo.filename, "erro": "Erro ao salvar no banco"})
        except Exception as e:
            logger.error(f"Erro ao processar arquivo {arquivo.filename}: {e}")
            erros.append({"nome": arquivo.filename, "erro": str(e)})
    
    return {
        "success": len(salvos) > 0,
        "salvos": salvos,
        "erros": erros,
        "total_salvos": len(salvos),
        "total_erros": len(erros)
    }


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
# PORTAL DO CLIENTE - TOKENS
# MIGRADO PARA modules/security.py (exceto verificar_token_cliente)
# ============================================

# def gerar_token_cliente(cadastro_id: str, email: str) -> str:
#     """Gera um token específico para clientes."""
#     payload = f"cliente:{cadastro_id}:{email}"
#     signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
#     token_data = base64.b64encode(f"{payload}:{signature}".encode()).decode()
#     return token_data
#
# def decodificar_token_cliente(token: str) -> dict:
#     """Decodifica e valida um token de cliente."""
#     try:
#         decoded = base64.b64decode(token.encode()).decode()
#         parts = decoded.rsplit(":", 1)
#         if len(parts) != 2:
#             return None
#
#         payload, signature = parts
#
#         expected_signature = hashlib.sha256(f"{payload}:{TOKEN_SECRET}".encode()).hexdigest()[:16]
#         if signature != expected_signature:
#             return None
#
#         tipo, cadastro_id, email = payload.split(":")
#         if tipo != "cliente":
#             return None
#
#         return {
#             "cadastro_id": cadastro_id,
#             "email": email,
#             "tipo": "cliente"
#         }
#     except Exception:
#         return None

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
    """Lista documentos disponíveis para o cliente (recebidos, enviados e da demanda)."""
    cadastro = buscar_cadastro(cliente["cadastro_id"])
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    documentos = []
    
    # 1. Documentos RECEBIDOS do Escritório (admin -> cliente)
    docs_admin = listar_documentos_admin(cliente["cadastro_id"])
    for doc in docs_admin:
        documentos.append({
            "id": doc['id'],
            "tipo": f"admin_{doc['id']}",
            "nome": doc["nome_original"],
            "descricao": doc.get("descricao", ""),
            "categoria": "Recebido do Escritório",
            "origem": "recebido",
            "disponivel": True,
            "data": doc["criado_em"].isoformat() if doc.get("criado_em") else None
        })
    
    # 2. Documentos ENVIADOS pelo Cliente (documentos extras)
    docs_extras = listar_documentos_extras(cliente["cadastro_id"])
    for doc in docs_extras:
        documentos.append({
            "id": doc['id'],
            "tipo": f"extra_{doc['id']}",
            "nome": doc["nome_original"],
            "descricao": doc.get("descricao", ""),
            "categoria": "Enviado por Você",
            "origem": "enviado",
            "disponivel": True,
            "data": doc["criado_em"].isoformat() if doc.get("criado_em") else None
        })
    
    # 3. Documentos da DEMANDA (enviados pelo cliente no cadastro da demanda)
    docs_demanda = listar_documentos_demanda(cliente["cadastro_id"])
    for doc in docs_demanda:
        # Traduzir tipo de documento para nome amigável
        tipos_nomes = {
            "processo_anterior": "Processo Anterior",
            "historico_financeiro": "Histórico Financeiro",
            "certificado_residencia": "Certificado de Residência",
            "doc_pessoais": "Documento Pessoal",
            "comprovante_residencia": "Comprovante de Residência",
            "contracheque": "Contracheque",
            "outros": "Outros"
        }
        tipo_nome = tipos_nomes.get(doc["tipo_documento"], doc["tipo_documento"])
        
        documentos.append({
            "id": doc['id'],
            "tipo": f"demanda_{doc['id']}",
            "nome": doc["nome_original"],
            "descricao": doc.get("descricao") or tipo_nome,
            "categoria": "Documento da Demanda",
            "origem": "enviado",
            "tipo_documento": doc["tipo_documento"],
            "disponivel": True,
            "data": doc.get("criado_em")
        })
    
    # Ordenar por data (mais recente primeiro)
    documentos.sort(key=lambda x: x.get("data") or "", reverse=True)
    
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
                <a href="https://painel.vaucherealvares.com" 
                   style="background-color: #8B1538; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Acessar Painel Administrativo
                </a>
            </p>
        """
        
        email_html = criar_email_html(conteudo_email)
        
        try:
            # Enviar para o e-mail do escritório
            await enviar_email_resend(
                "atendimento@vaucherealvares.com",
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
    
    # Documento do admin (recebido do escritório)
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
    
    # Documento extra (enviado pelo cliente)
    if tipo.startswith("extra_"):
        doc_id = int(tipo.replace("extra_", ""))
        doc = buscar_documento_extra(doc_id)
        if not doc or doc["cadastro_id"] != cliente["cadastro_id"]:
            raise HTTPException(status_code=404, detail="Documento não encontrado")
        
        if not os.path.exists(doc["arquivo_path"]):
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        
        return FileResponse(
            doc["arquivo_path"],
            filename=doc["nome_original"],
            media_type="application/octet-stream"
        )
    
    # Documento da demanda (enviado pelo cliente no cadastro)
    if tipo.startswith("demanda_"):
        doc_id = int(tipo.replace("demanda_", ""))
        doc = buscar_documento_demanda(doc_id)
        if not doc or doc["cadastro_id"] != cliente["cadastro_id"]:
            raise HTTPException(status_code=404, detail="Documento não encontrado")
        
        if not doc.get("arquivo_path") or not os.path.exists(doc["arquivo_path"]):
            raise HTTPException(status_code=404, detail="Arquivo não encontrado")
        
        return FileResponse(
            doc["arquivo_path"],
            filename=doc["nome_original"],
            media_type="application/octet-stream"
        )
    
    # Documento gerado (contrato/procuração) - mantido para compatibilidade
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
        # Enviar e-mail notificando o escritório
        nome_cliente = cliente.get("nome", "Cliente")
        
        conteudo_email = f"""
            <h2 style="color: #8B1538;">Nova Mensagem Recebida</h2>
            
            <p>O cliente <strong>{nome_cliente}</strong> enviou uma nova mensagem pelo Portal do Cliente.</p>
            
            <div style="background-color: #f8f8f8; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #8B1538;">
                <p style="margin: 0; white-space: pre-wrap;">{dados.texto.strip()}</p>
            </div>
            
            <p><strong>Cliente:</strong> {nome_cliente}<br>
            <strong>Código:</strong> {cliente["cadastro_id"]}</p>
            
            <p>Acesse o <strong>Painel Administrativo</strong> para responder:</p>
            
            <p style="text-align: center; margin: 30px 0;">
                <a href="https://painel.vaucherealvares.com" 
                   style="background-color: #8B1538; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Acessar Painel Administrativo
                </a>
            </p>
        """
        
        email_html = criar_email_html(conteudo_email)
        
        try:
            await enviar_email_resend(
                "atendimento@vaucherealvares.com",
                f"Nova mensagem de {nome_cliente}",
                email_html
            )
            logger.info(f"E-mail de notificação de mensagem enviado - cliente {nome_cliente}")
        except Exception as e:
            logger.error(f"Erro ao enviar e-mail de notificação de mensagem: {e}")
        
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
                
                <p>Acesse o portal em: <a href="https://portal.vaucherealvares.com" style="color: #8B1538;">portal.vaucherealvares.com </a></p>
                
                <p style="color: #666; font-size: 14px;">
                    <strong>Importante:</strong> Recomendamos que você altere sua senha no primeiro acesso.
                </p>
            """
            corpo_html = criar_email_html(conteudo)
            
            await enviar_email_resend(
                email_cliente,
                "🔐 Seu acesso ao Portal do Cliente - Vaucher e Álvares",
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
                
                <p>O escritório <strong>Vaucher e Álvares Sociedade de Advogados</strong> enviou novos documentos para você:</p>
                
                <ul style="background-color: #f8f8f8; padding: 15px 30px; border-radius: 8px;">
                    {lista_arquivos}
                </ul>
                
                <p>Para visualizar e baixar os documentos, acesse o <strong>Portal do Cliente</strong>:</p>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="https://portal.vaucherealvares.com" 
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
                    "Novos documentos disponíveis - Vaucher e Álvares",
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
# ENDPOINTS - ATUALIZAÇÃO CADASTRAL (ADMIN)
# ============================================

@app.post("/api/admin/clientes/{cadastro_id}/solicitar-atualizacao")
async def solicitar_atualizacao_cadastral(
    cadastro_id: str,
    dados: SolicitacaoAtualizacao,
    admin = Depends(verificar_admin)
):
    """Admin solicita que cliente atualize seus dados cadastrais."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Verificar se cadastro existe
        cur.execute("SELECT id FROM cadastros WHERE id = %s", (cadastro_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Cadastro não encontrado")
        
        # Verificar se já existe solicitação pendente ou enviada
        cur.execute("""
            SELECT id FROM atualizacoes_cadastrais 
            WHERE cadastro_id = %s AND status IN ('pendente', 'enviada')
        """, (cadastro_id,))
        
        if cur.fetchone():
            raise HTTPException(
                status_code=400, 
                detail="Já existe uma solicitação de atualização pendente para este cliente"
            )
        
        # Criar solicitação
        cur.execute("""
            INSERT INTO atualizacoes_cadastrais 
            (cadastro_id, tipo, status, motivo_solicitacao, solicitado_em, solicitado_por)
            VALUES (%s, 'solicitada', 'pendente', %s, CURRENT_TIMESTAMP, %s)
            RETURNING id
        """, (cadastro_id, dados.motivo, admin["email"]))
        
        atualizacao_id = cur.fetchone()["id"]
        conn.commit()
        
        # Buscar dados do cliente para enviar email
        cur.execute("""
            SELECT dados->>'nome' as nome, dados->>'email' as email 
            FROM cadastros WHERE id = %s
        """, (cadastro_id,))
        cliente = cur.fetchone()
        
        email_enviado = False
        if cliente and cliente["email"]:
            email_enviado = enviar_email_solicitacao_atualizacao(
                cliente["email"], 
                cliente["nome"] or "Cliente", 
                dados.motivo
            )
        
        cur.close()
        conn.close()
        
        return {
            "success": True, 
            "id": atualizacao_id, 
            "message": "Solicitação de atualização criada com sucesso",
            "email_enviado": email_enviado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao solicitar atualização: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/atualizacoes-pendentes")
async def listar_atualizacoes_pendentes(admin = Depends(verificar_admin)):
    """Lista todas as atualizações cadastrais pendentes de análise do admin."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                a.id, a.cadastro_id, a.tipo, a.status,
                a.motivo_solicitacao, a.solicitado_em,
                a.dados_novos, a.documentos_novos, a.enviado_em,
                c.dados->>'nome' as nome_cliente,
                c.dados->>'email' as email_cliente,
                c.dados->>'cpf' as cpf_cliente
            FROM atualizacoes_cadastrais a
            JOIN cadastros c ON c.id = a.cadastro_id
            WHERE a.status = 'enviada'
            ORDER BY a.enviado_em DESC
        """)
        
        atualizacoes = []
        for row in cur.fetchall():
            atualizacao = dict(row)
            for campo in ['solicitado_em', 'enviado_em']:
                if atualizacao.get(campo):
                    atualizacao[campo] = atualizacao[campo].isoformat()
            atualizacoes.append(atualizacao)
        
        cur.close()
        conn.close()
        
        return {"atualizacoes": atualizacoes, "total": len(atualizacoes)}
        
    except Exception as e:
        logger.error(f"Erro ao listar atualizações: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/clientes/{cadastro_id}/atualizacoes")
async def listar_atualizacoes_cliente(cadastro_id: str, admin = Depends(verificar_admin)):
    """Lista histórico de atualizações cadastrais de um cliente específico."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, tipo, status, motivo_solicitacao, solicitado_em, 
                   solicitado_por, dados_novos, enviado_em, analisado_em, 
                   analisado_por, motivo_rejeicao, criado_em
            FROM atualizacoes_cadastrais 
            WHERE cadastro_id = %s 
            ORDER BY criado_em DESC
        """, (cadastro_id,))
        
        atualizacoes = []
        for row in cur.fetchall():
            atualizacao = dict(row)
            for campo in ['solicitado_em', 'enviado_em', 'analisado_em', 'criado_em']:
                if atualizacao.get(campo):
                    atualizacao[campo] = atualizacao[campo].isoformat()
            atualizacoes.append(atualizacao)
        
        cur.close()
        conn.close()
        
        return {"atualizacoes": atualizacoes}
        
    except Exception as e:
        logger.error(f"Erro ao listar atualizações do cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/atualizacoes/{atualizacao_id}")
async def buscar_atualizacao(atualizacao_id: int, admin = Depends(verificar_admin)):
    """Busca detalhes de uma atualização específica."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT 
                a.*,
                c.dados as dados_atuais,
                c.dados->>'nome' as nome_cliente
            FROM atualizacoes_cadastrais a
            JOIN cadastros c ON c.id = a.cadastro_id
            WHERE a.id = %s
        """, (atualizacao_id,))
        
        result = cur.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Atualização não encontrada")
        
        atualizacao = dict(result)
        for campo in ['solicitado_em', 'enviado_em', 'analisado_em', 'criado_em', 'atualizado_em']:
            if atualizacao.get(campo):
                atualizacao[campo] = atualizacao[campo].isoformat()
        
        cur.close()
        conn.close()
        
        return atualizacao
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar atualização: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/atualizacoes/{atualizacao_id}/aprovar")
async def aprovar_atualizacao(atualizacao_id: int, admin = Depends(verificar_admin)):
    """Aprova a atualização e aplica os novos dados ao cadastro do cliente."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT cadastro_id, dados_novos FROM atualizacoes_cadastrais 
            WHERE id = %s AND status = 'enviada'
        """, (atualizacao_id,))
        
        atualizacao = cur.fetchone()
        if not atualizacao:
            raise HTTPException(
                status_code=404, 
                detail="Atualização não encontrada ou já foi processada"
            )
        
        cadastro_id = atualizacao["cadastro_id"]
        dados_novos = atualizacao["dados_novos"]
        
        # Atualizar cadastro com novos dados (merge)
        if dados_novos:
            cur.execute("""
                UPDATE cadastros 
                SET dados = dados || %s::jsonb
                WHERE id = %s
            """, (json.dumps(dados_novos), cadastro_id))
        
        # Marcar atualização como aprovada
        cur.execute("""
            UPDATE atualizacoes_cadastrais 
            SET status = 'aprovada', 
                analisado_em = CURRENT_TIMESTAMP,
                analisado_por = %s,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (admin["email"], atualizacao_id))
        
        conn.commit()
        
        # Notificar cliente
        cur.execute("""
            SELECT dados->>'nome' as nome, dados->>'email' as email 
            FROM cadastros WHERE id = %s
        """, (cadastro_id,))
        cliente = cur.fetchone()
        
        email_enviado = False
        if cliente and cliente["email"]:
            email_enviado = enviar_email_atualizacao_aprovada(cliente["email"], cliente["nome"] or "Cliente")
        
        cur.close()
        conn.close()
        
        return {
            "success": True, 
            "message": "Atualização aprovada e dados atualizados com sucesso",
            "email_enviado": email_enviado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao aprovar atualização: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/atualizacoes/{atualizacao_id}/rejeitar")
async def rejeitar_atualizacao(
    atualizacao_id: int, 
    dados: RejeicaoAtualizacao,
    admin = Depends(verificar_admin)
):
    """Rejeita a atualização com um motivo."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT cadastro_id FROM atualizacoes_cadastrais 
            WHERE id = %s AND status = 'enviada'
        """, (atualizacao_id,))
        
        result = cur.fetchone()
        if not result:
            raise HTTPException(
                status_code=404, 
                detail="Atualização não encontrada ou já foi processada"
            )
        
        cadastro_id = result["cadastro_id"]
        
        cur.execute("""
            UPDATE atualizacoes_cadastrais 
            SET status = 'rejeitada', 
                analisado_em = CURRENT_TIMESTAMP,
                analisado_por = %s,
                motivo_rejeicao = %s,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (admin["email"], dados.motivo, atualizacao_id))
        
        conn.commit()
        
        # Notificar cliente
        cur.execute("""
            SELECT dados->>'nome' as nome, dados->>'email' as email 
            FROM cadastros WHERE id = %s
        """, (cadastro_id,))
        cliente = cur.fetchone()
        
        email_enviado = False
        if cliente and cliente["email"]:
            email_enviado = enviar_email_atualizacao_rejeitada(
                cliente["email"], 
                cliente["nome"] or "Cliente", 
                dados.motivo
            )
        
        cur.close()
        conn.close()
        
        return {
            "success": True, 
            "message": "Atualização rejeitada",
            "email_enviado": email_enviado
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao rejeitar atualização: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINTS - ATUALIZAÇÃO CADASTRAL (CLIENTE)
# ============================================

@app.get("/api/cliente/atualizacao-pendente")
async def verificar_atualizacao_pendente(cliente = Depends(verificar_token_cliente)):
    """Verifica se há solicitação de atualização pendente para o cliente."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, tipo, motivo_solicitacao, solicitado_em, status
            FROM atualizacoes_cadastrais 
            WHERE cadastro_id = %s AND status = 'pendente'
            ORDER BY criado_em DESC LIMIT 1
        """, (cliente["cadastro_id"],))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return {
                "tem_solicitacao": True,
                "solicitacao": {
                    "id": result["id"],
                    "tipo": result["tipo"],
                    "motivo": result["motivo_solicitacao"],
                    "data": result["solicitado_em"].isoformat() if result["solicitado_em"] else None,
                    "status": result["status"]
                }
            }
        
        return {"tem_solicitacao": False, "solicitacao": None}
        
    except Exception as e:
        logger.error(f"Erro ao verificar solicitação pendente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cliente/iniciar-atualizacao")
async def iniciar_atualizacao_espontanea(cliente = Depends(verificar_token_cliente)):
    """Cliente inicia uma atualização espontânea de seus dados."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT id, status FROM atualizacoes_cadastrais 
            WHERE cadastro_id = %s AND status IN ('pendente', 'enviada')
            ORDER BY criado_em DESC LIMIT 1
        """, (cliente["cadastro_id"],))
        
        existente = cur.fetchone()
        if existente:
            cur.close()
            conn.close()
            return {
                "success": True, 
                "id": existente["id"], 
                "status": existente["status"],
                "message": "Já existe uma atualização em andamento"
            }
        
        cur.execute("""
            INSERT INTO atualizacoes_cadastrais 
            (cadastro_id, tipo, status)
            VALUES (%s, 'espontanea', 'pendente')
            RETURNING id
        """, (cliente["cadastro_id"],))
        
        atualizacao_id = cur.fetchone()["id"]
        conn.commit()
        
        cur.close()
        conn.close()
        
        return {"success": True, "id": atualizacao_id, "message": "Atualização iniciada"}
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao iniciar atualização: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cliente/enviar-atualizacao")
async def enviar_atualizacao_cadastral(
    dados: EnvioAtualizacao,
    cliente = Depends(verificar_token_cliente)
):
    """Cliente envia dados atualizados para análise do escritório."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        atualizacao_id = dados.atualizacao_id
        
        if atualizacao_id:
            cur.execute("""
                UPDATE atualizacoes_cadastrais 
                SET dados_novos = %s,
                    documentos_novos = %s,
                    status = 'enviada',
                    enviado_em = CURRENT_TIMESTAMP,
                    atualizado_em = CURRENT_TIMESTAMP
                WHERE id = %s AND cadastro_id = %s AND status = 'pendente'
                RETURNING id
            """, (
                json.dumps(dados.dados),
                json.dumps(dados.documentos),
                atualizacao_id,
                cliente["cadastro_id"]
            ))
            
            result = cur.fetchone()
            if not result:
                raise HTTPException(
                    status_code=400, 
                    detail="Solicitação não encontrada ou já foi enviada"
                )
        else:
            cur.execute("""
                INSERT INTO atualizacoes_cadastrais 
                (cadastro_id, tipo, status, dados_novos, documentos_novos, enviado_em)
                VALUES (%s, 'espontanea', 'enviada', %s, %s, CURRENT_TIMESTAMP)
                RETURNING id
            """, (
                cliente["cadastro_id"],
                json.dumps(dados.dados),
                json.dumps(dados.documentos)
            ))
            
            atualizacao_id = cur.fetchone()["id"]
        
        conn.commit()
        
        # Buscar nome do cliente para email
        cur.execute("""
            SELECT dados->>'nome' as nome FROM cadastros WHERE id = %s
        """, (cliente["cadastro_id"],))
        result = cur.fetchone()
        nome_cliente = result["nome"] if result else cliente["cadastro_id"]
        
        cur.close()
        conn.close()
        
        enviar_email_nova_atualizacao_admin(cliente["cadastro_id"], nome_cliente)
        
        return {
            "success": True, 
            "message": "Atualização enviada para análise do escritório",
            "id": atualizacao_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Erro ao enviar atualização: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cliente/minhas-atualizacoes")
async def listar_minhas_atualizacoes(cliente = Depends(verificar_token_cliente)):
    """Lista histórico de atualizações cadastrais do cliente logado."""
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, tipo, status, motivo_solicitacao, 
                   solicitado_em, enviado_em, analisado_em, motivo_rejeicao
            FROM atualizacoes_cadastrais 
            WHERE cadastro_id = %s 
            ORDER BY criado_em DESC
        """, (cliente["cadastro_id"],))
        
        atualizacoes = []
        for row in cur.fetchall():
            atualizacao = dict(row)
            for campo in ['solicitado_em', 'enviado_em', 'analisado_em']:
                if atualizacao.get(campo):
                    atualizacao[campo] = atualizacao[campo].isoformat()
            atualizacoes.append(atualizacao)
        
        cur.close()
        conn.close()
        
        return {"atualizacoes": atualizacoes}
        
    except Exception as e:
        logger.error(f"Erro ao listar atualizações: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ENDPOINTS - BACKUP E GERENCIAMENTO DE DOCUMENTOS
# ============================================

@app.get("/api/admin/backup/listar-documentos")
async def admin_listar_todos_documentos(
    usuario: dict = Depends(verificar_admin)
):
    """
    Lista TODOS os documentos do sistema organizados por cliente.
    Retorna estrutura para seleção individual de arquivos.
    """
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Buscar todos os cadastros
        cur.execute("""
            SELECT id, dados, documentos, arquivos_gerados, documentos_assinados
            FROM cadastros ORDER BY data_hora DESC
        """)
        cadastros = cur.fetchall()
        
        resultado = []
        
        for cadastro in cadastros:
            cadastro_id = cadastro["id"]
            dados = cadastro["dados"] if isinstance(cadastro["dados"], dict) else json.loads(cadastro["dados"] or "{}")
            nome_cliente = dados.get("nome", "Sem nome")
            
            documentos_cliente = {
                "cadastro_id": cadastro_id,
                "nome_cliente": nome_cliente,
                "documentos": []
            }
            
            # 1. Documentos enviados pelo cliente no cadastro inicial
            docs_cadastro = cadastro["documentos"] if isinstance(cadastro["documentos"], list) else json.loads(cadastro["documentos"] or "[]")
            for doc in docs_cadastro:
                if isinstance(doc, dict) and doc.get("arquivo"):
                    caminho = os.path.join(UPLOADS_DIR, doc["arquivo"])
                    documentos_cliente["documentos"].append({
                        "id": f"cadastro_{cadastro_id}_{doc.get('arquivo', '')}",
                        "tipo": "cadastro_inicial",
                        "nome": doc.get("nome", doc.get("arquivo", "Documento")),
                        "arquivo": doc.get("arquivo"),
                        "caminho": caminho,
                        "existe": os.path.exists(caminho),
                        "tamanho": os.path.getsize(caminho) if os.path.exists(caminho) else 0
                    })
            
            # 2. Documentos gerados (contrato e procuração)
            arq_gerados = cadastro["arquivos_gerados"] if isinstance(cadastro["arquivos_gerados"], dict) else json.loads(cadastro["arquivos_gerados"] or "{}")
            for tipo, caminho in arq_gerados.items():
                if caminho:
                    caminho_completo = caminho if os.path.isabs(caminho) else os.path.join(BASE_DIR, caminho)
                    documentos_cliente["documentos"].append({
                        "id": f"gerado_{cadastro_id}_{tipo}",
                        "tipo": "documento_gerado",
                        "nome": f"{tipo.replace('_', ' ').title()}",
                        "arquivo": os.path.basename(caminho),
                        "caminho": caminho_completo,
                        "existe": os.path.exists(caminho_completo),
                        "tamanho": os.path.getsize(caminho_completo) if os.path.exists(caminho_completo) else 0
                    })
            
            # 3. Documentos assinados
            docs_assinados = cadastro["documentos_assinados"] if isinstance(cadastro["documentos_assinados"], list) else json.loads(cadastro["documentos_assinados"] or "[]")
            for doc in docs_assinados:
                if isinstance(doc, dict) and doc.get("arquivo"):
                    caminho = os.path.join(UPLOADS_DIR, doc["arquivo"])
                    documentos_cliente["documentos"].append({
                        "id": f"assinado_{cadastro_id}_{doc.get('arquivo', '')}",
                        "tipo": "documento_assinado",
                        "nome": doc.get("nome", "Documento Assinado"),
                        "arquivo": doc.get("arquivo"),
                        "caminho": caminho,
                        "existe": os.path.exists(caminho),
                        "tamanho": os.path.getsize(caminho) if os.path.exists(caminho) else 0
                    })
            
            # 4. Documentos extras enviados pelo cliente (tabela documentos_extras)
            cur.execute("""
                SELECT id, nome_original, arquivo_path, descricao, criado_em
                FROM documentos_extras WHERE cadastro_id = %s
            """, (cadastro_id,))
            docs_extras = cur.fetchall()
            for doc in docs_extras:
                documentos_cliente["documentos"].append({
                    "id": f"extra_{doc['id']}",
                    "db_id": doc["id"],
                    "tipo": "documento_extra",
                    "nome": doc["nome_original"],
                    "descricao": doc.get("descricao", ""),
                    "caminho": doc["arquivo_path"],
                    "existe": os.path.exists(doc["arquivo_path"]),
                    "tamanho": os.path.getsize(doc["arquivo_path"]) if os.path.exists(doc["arquivo_path"]) else 0,
                    "data": doc["criado_em"].isoformat() if doc["criado_em"] else None
                })
            
            # 5. Documentos enviados pelo admin para o cliente (tabela documentos_admin)
            cur.execute("""
                SELECT id, nome_original, arquivo_path, descricao, criado_em
                FROM documentos_admin WHERE cadastro_id = %s
            """, (cadastro_id,))
            docs_admin = cur.fetchall()
            for doc in docs_admin:
                documentos_cliente["documentos"].append({
                    "id": f"admin_{doc['id']}",
                    "db_id": doc["id"],
                    "tipo": "documento_admin",
                    "nome": doc["nome_original"],
                    "descricao": doc.get("descricao", ""),
                    "caminho": doc["arquivo_path"],
                    "existe": os.path.exists(doc["arquivo_path"]),
                    "tamanho": os.path.getsize(doc["arquivo_path"]) if os.path.exists(doc["arquivo_path"]) else 0,
                    "data": doc["criado_em"].isoformat() if doc["criado_em"] else None
                })
            
            # 6. Comprovantes de pagamento
            cur.execute("""
                SELECT c.id, c.arquivo_nome, c.arquivo_path, c.enviado_em, c.status,
                       p.numero as parcela_numero, ch.descricao as contrato_descricao
                FROM comprovantes c
                JOIN parcelas p ON c.parcela_id = p.id
                JOIN contratos_honorarios ch ON p.contrato_id = ch.id
                WHERE ch.cadastro_id = %s
            """, (cadastro_id,))
            comprovantes = cur.fetchall()
            for comp in comprovantes:
                documentos_cliente["documentos"].append({
                    "id": f"comprovante_{comp['id']}",
                    "db_id": comp["id"],
                    "tipo": "comprovante",
                    "nome": f"Comprovante - Parcela {comp['parcela_numero']} - {comp.get('contrato_descricao', '')}",
                    "arquivo": comp["arquivo_nome"],
                    "caminho": comp["arquivo_path"],
                    "existe": os.path.exists(comp["arquivo_path"]) if comp["arquivo_path"] else False,
                    "tamanho": os.path.getsize(comp["arquivo_path"]) if comp["arquivo_path"] and os.path.exists(comp["arquivo_path"]) else 0,
                    "status": comp["status"],
                    "data": comp["enviado_em"].isoformat() if comp["enviado_em"] else None
                })
            
            # Calcular totais
            docs_existentes = [d for d in documentos_cliente["documentos"] if d.get("existe")]
            documentos_cliente["total_documentos"] = len(documentos_cliente["documentos"])
            documentos_cliente["documentos_existentes"] = len(docs_existentes)
            documentos_cliente["tamanho_total"] = sum(d.get("tamanho", 0) for d in docs_existentes)
            
            resultado.append(documentos_cliente)
        
        cur.close()
        conn.close()
        
        # Calcular totais gerais
        total_geral = sum(c["total_documentos"] for c in resultado)
        existentes_geral = sum(c["documentos_existentes"] for c in resultado)
        tamanho_geral = sum(c["tamanho_total"] for c in resultado)
        
        return {
            "clientes": resultado,
            "resumo": {
                "total_clientes": len(resultado),
                "total_documentos": total_geral,
                "documentos_existentes": existentes_geral,
                "tamanho_total": tamanho_geral,
                "tamanho_formatado": formatar_tamanho(tamanho_geral)
            }
        }
    except Exception as e:
        logger.error(f"Erro ao listar documentos para backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def formatar_tamanho(bytes_size: int) -> str:
    """Formata tamanho em bytes para formato legível."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


class BackupRequest(BaseModel):
    documentos_ids: List[str]  # Lista de IDs dos documentos selecionados
    incluir_dados_json: bool = True  # Se inclui JSON com dados dos clientes


@app.post("/api/admin/backup/download")
async def admin_download_backup(
    request: BackupRequest,
    usuario: dict = Depends(verificar_admin)
):
    """
    Gera um ZIP com os documentos selecionados.
    Organiza por cliente em pastas separadas.
    """
    if not request.documentos_ids:
        raise HTTPException(status_code=400, detail="Nenhum documento selecionado")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Criar arquivo ZIP em memória
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # Buscar todos os cadastros para organização
            cur.execute("SELECT id, dados FROM cadastros")
            cadastros = {row["id"]: row for row in cur.fetchall()}
            
            arquivos_adicionados = set()
            dados_clientes = {}
            
            for doc_id in request.documentos_ids:
                partes = doc_id.split("_", 2)
                if len(partes) < 2:
                    continue
                
                tipo = partes[0]
                
                # Identificar cadastro_id e buscar arquivo
                caminho_arquivo = None
                nome_arquivo = None
                cadastro_id = None
                
                if tipo == "cadastro":
                    # Formato: cadastro_{cadastro_id}_{arquivo}
                    cadastro_id = partes[1]
                    arquivo = "_".join(partes[2:]) if len(partes) > 2 else ""
                    caminho_arquivo = os.path.join(UPLOADS_DIR, arquivo)
                    nome_arquivo = arquivo
                    
                elif tipo == "gerado":
                    # Formato: gerado_{cadastro_id}_{tipo_doc}
                    cadastro_id = partes[1]
                    tipo_doc = "_".join(partes[2:]) if len(partes) > 2 else ""
                    cadastro = buscar_cadastro(cadastro_id)
                    if cadastro and cadastro.get("arquivos_gerados"):
                        caminho = cadastro["arquivos_gerados"].get(tipo_doc)
                        if caminho:
                            caminho_arquivo = caminho if os.path.isabs(caminho) else os.path.join(BASE_DIR, caminho)
                            nome_arquivo = os.path.basename(caminho)
                
                elif tipo == "assinado":
                    # Formato: assinado_{cadastro_id}_{arquivo}
                    cadastro_id = partes[1]
                    arquivo = "_".join(partes[2:]) if len(partes) > 2 else ""
                    caminho_arquivo = os.path.join(UPLOADS_DIR, arquivo)
                    nome_arquivo = arquivo
                
                elif tipo == "extra":
                    # Formato: extra_{db_id}
                    db_id = int(partes[1])
                    cur.execute("SELECT * FROM documentos_extras WHERE id = %s", (db_id,))
                    doc = cur.fetchone()
                    if doc:
                        cadastro_id = doc["cadastro_id"]
                        caminho_arquivo = doc["arquivo_path"]
                        nome_arquivo = doc["nome_original"]
                
                elif tipo == "admin":
                    # Formato: admin_{db_id}
                    db_id = int(partes[1])
                    cur.execute("SELECT * FROM documentos_admin WHERE id = %s", (db_id,))
                    doc = cur.fetchone()
                    if doc:
                        cadastro_id = doc["cadastro_id"]
                        caminho_arquivo = doc["arquivo_path"]
                        nome_arquivo = doc["nome_original"]
                
                elif tipo == "comprovante":
                    # Formato: comprovante_{db_id}
                    db_id = int(partes[1])
                    cur.execute("""
                        SELECT c.*, ch.cadastro_id 
                        FROM comprovantes c
                        JOIN parcelas p ON c.parcela_id = p.id
                        JOIN contratos_honorarios ch ON p.contrato_id = ch.id
                        WHERE c.id = %s
                    """, (db_id,))
                    doc = cur.fetchone()
                    if doc:
                        cadastro_id = doc["cadastro_id"]
                        caminho_arquivo = doc["arquivo_path"]
                        nome_arquivo = doc["arquivo_nome"]
                
                # Adicionar arquivo ao ZIP
                if caminho_arquivo and os.path.exists(caminho_arquivo) and caminho_arquivo not in arquivos_adicionados:
                    # Buscar nome do cliente
                    nome_cliente = "Sem_Nome"
                    if cadastro_id and cadastro_id in cadastros:
                        dados = cadastros[cadastro_id]["dados"]
                        if isinstance(dados, str):
                            dados = json.loads(dados)
                        nome_cliente = dados.get("nome", "Sem_Nome").replace(" ", "_").replace("/", "-")[:50]
                    
                    # Criar pasta do cliente
                    pasta_cliente = f"{cadastro_id}_{nome_cliente}"
                    
                    # Adicionar ao ZIP
                    zip_file.write(caminho_arquivo, f"{pasta_cliente}/{nome_arquivo}")
                    arquivos_adicionados.add(caminho_arquivo)
                    
                    # Guardar dados do cliente para JSON
                    if cadastro_id not in dados_clientes:
                        dados_clientes[cadastro_id] = {
                            "cadastro_id": cadastro_id,
                            "nome": nome_cliente,
                            "arquivos": []
                        }
                    dados_clientes[cadastro_id]["arquivos"].append(nome_arquivo)
            
            # Incluir JSON com dados dos clientes
            if request.incluir_dados_json:
                # Buscar dados completos dos clientes incluídos
                for cadastro_id in dados_clientes.keys():
                    cadastro = buscar_cadastro(cadastro_id)
                    if cadastro:
                        dados_clientes[cadastro_id]["dados_cadastro"] = cadastro["dados"]
                        dados_clientes[cadastro_id]["status"] = cadastro["status"]
                        dados_clientes[cadastro_id]["data_cadastro"] = cadastro["data"]
                        
                        # Buscar processos
                        processos = listar_processos(cadastro_id)
                        dados_clientes[cadastro_id]["processos"] = processos
                        
                        # Buscar contratos
                        contratos = listar_contratos(cadastro_id)
                        dados_clientes[cadastro_id]["contratos"] = contratos
                
                # Adicionar JSON ao ZIP
                json_content = json.dumps(list(dados_clientes.values()), indent=2, ensure_ascii=False, default=str)
                zip_file.writestr("dados_clientes.json", json_content)
        
        cur.close()
        conn.close()
        
        # Retornar o ZIP
        zip_buffer.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_vaucher_alvares_{timestamp}.zip"
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Erro ao gerar backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class DeleteDocumentosRequest(BaseModel):
    documentos_ids: List[str]  # Lista de IDs dos documentos a deletar
    confirmar: bool = False  # Confirmação obrigatória


@app.post("/api/admin/backup/deletar-documentos")
async def admin_deletar_documentos_selecionados(
    request: DeleteDocumentosRequest,
    usuario: dict = Depends(verificar_admin)
):
    """
    Deleta múltiplos documentos selecionados.
    Requer confirmação explícita.
    """
    if not request.confirmar:
        raise HTTPException(
            status_code=400, 
            detail="Confirmação obrigatória. Defina 'confirmar: true' para prosseguir."
        )
    
    if not request.documentos_ids:
        raise HTTPException(status_code=400, detail="Nenhum documento selecionado")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        deletados = []
        erros = []
        
        for doc_id in request.documentos_ids:
            try:
                partes = doc_id.split("_", 2)
                if len(partes) < 2:
                    erros.append({"id": doc_id, "erro": "ID inválido"})
                    continue
                
                tipo = partes[0]
                sucesso = False
                
                if tipo == "cadastro":
                    # Documentos do cadastro inicial - remover do JSON
                    cadastro_id = partes[1]
                    arquivo = "_".join(partes[2:]) if len(partes) > 2 else ""
                    caminho = os.path.join(UPLOADS_DIR, arquivo)
                    
                    # Remover arquivo físico
                    if os.path.exists(caminho):
                        os.remove(caminho)
                    
                    # Atualizar JSON no banco
                    cadastro = buscar_cadastro(cadastro_id)
                    if cadastro:
                        docs = cadastro.get("documentos", [])
                        docs_atualizados = [d for d in docs if d.get("arquivo") != arquivo]
                        cur.execute(
                            "UPDATE cadastros SET documentos = %s WHERE id = %s",
                            (json.dumps(docs_atualizados), cadastro_id)
                        )
                        conn.commit()
                    sucesso = True
                    
                elif tipo == "gerado":
                    # Documentos gerados - remover arquivo e atualizar JSON
                    cadastro_id = partes[1]
                    tipo_doc = "_".join(partes[2:]) if len(partes) > 2 else ""
                    
                    cadastro = buscar_cadastro(cadastro_id)
                    if cadastro and cadastro.get("arquivos_gerados"):
                        caminho = cadastro["arquivos_gerados"].get(tipo_doc)
                        if caminho:
                            caminho_completo = caminho if os.path.isabs(caminho) else os.path.join(BASE_DIR, caminho)
                            if os.path.exists(caminho_completo):
                                os.remove(caminho_completo)
                        
                        # Atualizar JSON
                        arq_gerados = cadastro["arquivos_gerados"]
                        arq_gerados[tipo_doc] = None
                        cur.execute(
                            "UPDATE cadastros SET arquivos_gerados = %s WHERE id = %s",
                            (json.dumps(arq_gerados), cadastro_id)
                        )
                        conn.commit()
                    sucesso = True
                    
                elif tipo == "assinado":
                    # Documentos assinados
                    cadastro_id = partes[1]
                    arquivo = "_".join(partes[2:]) if len(partes) > 2 else ""
                    caminho = os.path.join(UPLOADS_DIR, arquivo)
                    
                    if os.path.exists(caminho):
                        os.remove(caminho)
                    
                    cadastro = buscar_cadastro(cadastro_id)
                    if cadastro:
                        docs = cadastro.get("documentos_assinados", [])
                        docs_atualizados = [d for d in docs if d.get("arquivo") != arquivo]
                        cur.execute(
                            "UPDATE cadastros SET documentos_assinados = %s WHERE id = %s",
                            (json.dumps(docs_atualizados), cadastro_id)
                        )
                        conn.commit()
                    sucesso = True
                    
                elif tipo == "extra":
                    # Documentos extras - deletar do banco e arquivo
                    db_id = int(partes[1])
                    cur.execute("SELECT arquivo_path FROM documentos_extras WHERE id = %s", (db_id,))
                    doc = cur.fetchone()
                    if doc and doc["arquivo_path"] and os.path.exists(doc["arquivo_path"]):
                        os.remove(doc["arquivo_path"])
                    cur.execute("DELETE FROM documentos_extras WHERE id = %s", (db_id,))
                    conn.commit()
                    sucesso = True
                    
                elif tipo == "admin":
                    # Documentos admin
                    db_id = int(partes[1])
                    cur.execute("SELECT arquivo_path FROM documentos_admin WHERE id = %s", (db_id,))
                    doc = cur.fetchone()
                    if doc and doc["arquivo_path"] and os.path.exists(doc["arquivo_path"]):
                        os.remove(doc["arquivo_path"])
                    cur.execute("DELETE FROM documentos_admin WHERE id = %s", (db_id,))
                    conn.commit()
                    sucesso = True
                    
                elif tipo == "comprovante":
                    # Comprovantes
                    db_id = int(partes[1])
                    cur.execute("SELECT arquivo_path FROM comprovantes WHERE id = %s", (db_id,))
                    doc = cur.fetchone()
                    if doc and doc["arquivo_path"] and os.path.exists(doc["arquivo_path"]):
                        os.remove(doc["arquivo_path"])
                    cur.execute("DELETE FROM comprovantes WHERE id = %s", (db_id,))
                    conn.commit()
                    sucesso = True
                
                if sucesso:
                    deletados.append(doc_id)
                else:
                    erros.append({"id": doc_id, "erro": "Tipo não reconhecido"})
                    
            except Exception as e:
                erros.append({"id": doc_id, "erro": str(e)})
        
        cur.close()
        conn.close()
        
        return {
            "success": True,
            "deletados": len(deletados),
            "erros": len(erros),
            "detalhes": {
                "ids_deletados": deletados,
                "erros": erros
            }
        }
    except Exception as e:
        logger.error(f"Erro ao deletar documentos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/backup/download-completo")
async def admin_download_backup_completo(
    usuario: dict = Depends(verificar_admin)
):
    """
    Gera um backup COMPLETO de todos os clientes e documentos.
    Inclui JSON com todos os dados.
    """
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Criar arquivo ZIP em memória
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # Buscar todos os cadastros
            cur.execute("SELECT * FROM cadastros ORDER BY data_hora DESC")
            cadastros = cur.fetchall()
            
            todos_dados = []
            
            for cadastro in cadastros:
                cadastro_id = cadastro["id"]
                dados = cadastro["dados"] if isinstance(cadastro["dados"], dict) else json.loads(cadastro["dados"] or "{}")
                nome_cliente = dados.get("nome", "Sem_Nome").replace(" ", "_").replace("/", "-")[:50]
                pasta_cliente = f"{cadastro_id}_{nome_cliente}"
                
                cliente_dados = {
                    "cadastro_id": cadastro_id,
                    "nome": dados.get("nome"),
                    "dados_cadastro": dados,
                    "status": cadastro["status"],
                    "data_cadastro": str(cadastro["data"]),
                    "arquivos_incluidos": []
                }
                
                # 1. Documentos do cadastro
                docs = cadastro["documentos"] if isinstance(cadastro["documentos"], list) else json.loads(cadastro["documentos"] or "[]")
                for doc in docs:
                    if isinstance(doc, dict) and doc.get("arquivo"):
                        caminho = os.path.join(UPLOADS_DIR, doc["arquivo"])
                        if os.path.exists(caminho):
                            zip_file.write(caminho, f"{pasta_cliente}/cadastro/{doc['arquivo']}")
                            cliente_dados["arquivos_incluidos"].append(f"cadastro/{doc['arquivo']}")
                
                # 2. Documentos gerados
                arq = cadastro["arquivos_gerados"] if isinstance(cadastro["arquivos_gerados"], dict) else json.loads(cadastro["arquivos_gerados"] or "{}")
                for tipo, caminho in arq.items():
                    if caminho:
                        caminho_completo = caminho if os.path.isabs(caminho) else os.path.join(BASE_DIR, caminho)
                        if os.path.exists(caminho_completo):
                            nome = os.path.basename(caminho)
                            zip_file.write(caminho_completo, f"{pasta_cliente}/gerados/{nome}")
                            cliente_dados["arquivos_incluidos"].append(f"gerados/{nome}")
                
                # 3. Documentos assinados
                docs_ass = cadastro["documentos_assinados"] if isinstance(cadastro["documentos_assinados"], list) else json.loads(cadastro["documentos_assinados"] or "[]")
                for doc in docs_ass:
                    if isinstance(doc, dict) and doc.get("arquivo"):
                        caminho = os.path.join(UPLOADS_DIR, doc["arquivo"])
                        if os.path.exists(caminho):
                            zip_file.write(caminho, f"{pasta_cliente}/assinados/{doc['arquivo']}")
                            cliente_dados["arquivos_incluidos"].append(f"assinados/{doc['arquivo']}")
                
                # 4. Documentos extras
                cur.execute("SELECT * FROM documentos_extras WHERE cadastro_id = %s", (cadastro_id,))
                for doc in cur.fetchall():
                    if doc["arquivo_path"] and os.path.exists(doc["arquivo_path"]):
                        zip_file.write(doc["arquivo_path"], f"{pasta_cliente}/extras/{doc['nome_original']}")
                        cliente_dados["arquivos_incluidos"].append(f"extras/{doc['nome_original']}")
                
                # 5. Documentos admin
                cur.execute("SELECT * FROM documentos_admin WHERE cadastro_id = %s", (cadastro_id,))
                for doc in cur.fetchall():
                    if doc["arquivo_path"] and os.path.exists(doc["arquivo_path"]):
                        zip_file.write(doc["arquivo_path"], f"{pasta_cliente}/documentos_escritorio/{doc['nome_original']}")
                        cliente_dados["arquivos_incluidos"].append(f"documentos_escritorio/{doc['nome_original']}")
                
                # 6. Comprovantes
                cur.execute("""
                    SELECT c.* FROM comprovantes c
                    JOIN parcelas p ON c.parcela_id = p.id
                    JOIN contratos_honorarios ch ON p.contrato_id = ch.id
                    WHERE ch.cadastro_id = %s
                """, (cadastro_id,))
                for comp in cur.fetchall():
                    if comp["arquivo_path"] and os.path.exists(comp["arquivo_path"]):
                        zip_file.write(comp["arquivo_path"], f"{pasta_cliente}/comprovantes/{comp['arquivo_nome']}")
                        cliente_dados["arquivos_incluidos"].append(f"comprovantes/{comp['arquivo_nome']}")
                
                # Buscar processos e contratos
                cliente_dados["processos"] = listar_processos(cadastro_id)
                cliente_dados["contratos"] = listar_contratos(cadastro_id)
                
                # Buscar financeiro
                financeiro = buscar_financeiro(cadastro_id)
                if financeiro:
                    cliente_dados["financeiro"] = financeiro
                
                todos_dados.append(cliente_dados)
            
            # Adicionar JSON completo
            json_content = json.dumps(todos_dados, indent=2, ensure_ascii=False, default=str)
            zip_file.writestr("backup_completo.json", json_content)
        
        cur.close()
        conn.close()
        
        zip_buffer.seek(0)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"backup_completo_vaucher_alvares_{timestamp}.zip"
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"Erro ao gerar backup completo: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
# ============================================
# TERMOS DE USO E POLÍTICA DE PRIVACIDADE
# ============================================

@app.get("/api/termos/{tipo}")
async def get_termos_vigentes(tipo: str):
    """
    Retorna a versão vigente dos termos.
    Tipos: 'termos_uso' ou 'politica_privacidade'
    """
    if tipo not in ['termos_uso', 'politica_privacidade']:
        raise HTTPException(status_code=400, detail="Tipo inválido. Use 'termos_uso' ou 'politica_privacidade'")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco de dados")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, versao, conteudo, data_vigencia
            FROM termos_versoes
            WHERE tipo = %s AND ativo = TRUE
            ORDER BY data_vigencia DESC
            LIMIT 1
        """, (tipo,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Termos não encontrados. Configure os termos no banco de dados.")
        
        return {
            "id": row["id"],
            "versao": row["versao"],
            "conteudo": row["conteudo"],
            "data_vigencia": row["data_vigencia"].isoformat() if row["data_vigencia"] else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar termos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar termos")


@app.post("/api/aceitar-termos")
async def aceitar_termos(request):
    """
    Registra o aceite dos termos pelo cliente no momento do cadastro.
    Armazena IP, User-Agent e metadados para validade legal.
    """
    from starlette.requests import Request
    
    # Obter dados do body
    try:
        data = await request.json()
    except:
        raise HTTPException(status_code=400, detail="JSON inválido")
    
    cadastro_id = data.get('cadastro_id')
    termos_uso_versao_id = data.get('termos_uso_versao_id')
    privacidade_versao_id = data.get('privacidade_versao_id')
    
    if not cadastro_id:
        raise HTTPException(status_code=400, detail="cadastro_id é obrigatório")
    
    if not termos_uso_versao_id and not privacidade_versao_id:
        raise HTTPException(status_code=400, detail="Pelo menos um ID de versão de termos é obrigatório")
    
    # Capturar IP do cliente
    ip_address = request.client.host if request.client else "0.0.0.0"
    
    # Tentar pegar IP real se estiver atrás de proxy/load balancer
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        ip_address = forwarded_for.split(',')[0].strip()
    
    # Capturar User-Agent
    user_agent = request.headers.get('User-Agent', 'Não informado')
    
    # Metadados adicionais para prova legal
    metadados = {
        "accept_language": request.headers.get('Accept-Language'),
        "origin": request.headers.get('Origin'),
        "referer": request.headers.get('Referer'),
        "timestamp_servidor": datetime.now().isoformat(),
        "x_real_ip": request.headers.get('X-Real-IP'),
    }
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco de dados")
    
    try:
        cur = conn.cursor()
        
        # Registrar aceite dos Termos de Uso
        if termos_uso_versao_id:
            cur.execute("""
                INSERT INTO aceites_termos (cadastro_id, termos_versao_id, ip_address, user_agent, metadados)
                VALUES (%s, %s, %s, %s, %s)
            """, (cadastro_id, termos_uso_versao_id, ip_address, user_agent, json.dumps(metadados)))
        
        # Registrar aceite da Política de Privacidade
        if privacidade_versao_id:
            cur.execute("""
                INSERT INTO aceites_termos (cadastro_id, termos_versao_id, ip_address, user_agent, metadados)
                VALUES (%s, %s, %s, %s, %s)
            """, (cadastro_id, privacidade_versao_id, ip_address, user_agent, json.dumps(metadados)))
        
        # Atualizar cadastro marcando que aceitou os termos
        cur.execute("""
            UPDATE cadastros 
            SET termos_aceitos = TRUE, termos_aceitos_em = NOW()
            WHERE id = %s
        """, (cadastro_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info(f"Termos aceitos - Cadastro: {cadastro_id}, IP: {ip_address}")
        
        return {
            "success": True, 
            "message": "Termos aceitos e registrados com sucesso",
            "cadastro_id": cadastro_id,
            "ip_registrado": ip_address,
            "data_aceite": datetime.now().isoformat()
        }
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Erro ao registrar aceite de termos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao registrar aceite dos termos")


@app.get("/api/admin/clientes/{cadastro_id}/aceites")
async def get_aceites_cliente(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """
    Lista todos os aceites de termos de um cliente.
    Usado para auditoria e comprovação legal.
    """
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco de dados")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Buscar todos os aceites com informações da versão dos termos
        cur.execute("""
            SELECT 
                a.id,
                a.cadastro_id,
                t.tipo,
                t.versao,
                t.conteudo,
                a.ip_address,
                a.user_agent,
                a.aceito_em,
                a.metadados
            FROM aceites_termos a
            JOIN termos_versoes t ON a.termos_versao_id = t.id
            WHERE a.cadastro_id = %s
            ORDER BY a.aceito_em DESC
        """, (cadastro_id,))
        
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        aceites = []
        for row in rows:
            aceites.append({
                "id": row["id"],
                "cadastro_id": row["cadastro_id"],
                "tipo": row["tipo"],
                "versao": row["versao"],
                "conteudo_resumo": row["conteudo"][:200] + "..." if row["conteudo"] and len(row["conteudo"]) > 200 else row["conteudo"],
                "ip_address": row["ip_address"],
                "user_agent": row["user_agent"],
                "aceito_em": row["aceito_em"].isoformat() if row["aceito_em"] else None,
                "metadados": row["metadados"]
            })
        
        return {
            "cadastro_id": cadastro_id,
            "total_aceites": len(aceites),
            "aceites": aceites
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar aceites do cliente {cadastro_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro ao buscar aceites")


@app.get("/api/admin/aceites/exportar/{cadastro_id}")
async def exportar_aceites_cliente(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """
    Exporta todos os aceites de um cliente em formato JSON completo.
    Útil para comprovação judicial.
    """
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco de dados")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Buscar dados do cadastro
        cur.execute("SELECT * FROM cadastros WHERE id = %s", (cadastro_id,))
        cadastro = cur.fetchone()
        
        if not cadastro:
            raise HTTPException(status_code=404, detail="Cadastro não encontrado")
        
        # Buscar todos os aceites com o conteúdo completo dos termos
        cur.execute("""
            SELECT 
                a.id,
                a.cadastro_id,
                t.tipo,
                t.versao,
                t.conteudo,
                t.data_vigencia,
                a.ip_address,
                a.user_agent,
                a.aceito_em,
                a.metadados
            FROM aceites_termos a
            JOIN termos_versoes t ON a.termos_versao_id = t.id
            WHERE a.cadastro_id = %s
            ORDER BY a.aceito_em DESC
        """, (cadastro_id,))
        
        aceites = cur.fetchall()
        cur.close()
        conn.close()
        
        # Montar documento de comprovação
        dados_cadastro = cadastro["dados"] if isinstance(cadastro["dados"], dict) else json.loads(cadastro["dados"] or "{}")
        
        documento_comprovacao = {
            "titulo": "COMPROVAÇÃO DE ACEITE DE TERMOS",
            "gerado_em": datetime.now().isoformat(),
            "gerado_por": usuario["email"],
            "cliente": {
                "cadastro_id": cadastro_id,
                "nome": dados_cadastro.get("nome"),
                "cpf": dados_cadastro.get("cpf"),
                "email": dados_cadastro.get("email"),
                "data_cadastro": str(cadastro["data"]),
                "termos_aceitos": cadastro.get("termos_aceitos", False),
                "termos_aceitos_em": cadastro.get("termos_aceitos_em").isoformat() if cadastro.get("termos_aceitos_em") else None
            },
            "aceites": [
                {
                    "id_aceite": a["id"],
                    "tipo_documento": a["tipo"],
                    "versao_documento": a["versao"],
                    "data_vigencia_documento": a["data_vigencia"].isoformat() if a["data_vigencia"] else None,
                    "conteudo_integral": a["conteudo"],
                    "ip_address": a["ip_address"],
                    "user_agent": a["user_agent"],
                    "data_hora_aceite": a["aceito_em"].isoformat() if a["aceito_em"] else None,
                    "metadados_tecnicos": a["metadados"]
                }
                for a in aceites
            ],
            "declaracao": "Este documento comprova que o titular acima identificado aceitou os termos nas datas e condições especificadas, através do sistema digital do escritório Vaucher e Álvares Sociedade de Advogados."
        }
        
        return documento_comprovacao
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao exportar aceites: {e}")
        raise HTTPException(status_code=500, detail="Erro ao exportar aceites")

# ============================================
# ENDPOINTS - DEMANDA ESPECÍFICA E DOCUMENTOS
# ============================================

@app.post("/api/admin/clientes/{cadastro_id}/importar-documentos-demanda")
async def importar_documentos_para_demanda(
    cadastro_id: str,
    usuario: dict = Depends(verificar_admin)
):
    """Importa documentos existentes da pasta do cliente para a tabela documentos_demanda.
    
    Útil para migrar documentos de clientes que foram cadastrados antes da 
    funcionalidade de documentos específicos da demanda.
    """
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    # Verificar pastas de documentos
    pasta_cliente = os.path.join(UPLOADS_DIR, cadastro_id)
    pasta_demanda = os.path.join(UPLOADS_DIR, "documentos_demanda", cadastro_id)
    
    importados = []
    ja_existentes = []
    
    # Verificar documentos na pasta genérica do cliente
    if os.path.exists(pasta_cliente):
        for arquivo in os.listdir(pasta_cliente):
            arquivo_path = os.path.join(pasta_cliente, arquivo)
            if os.path.isfile(arquivo_path):
                # Determinar tipo baseado no nome do arquivo
                nome_lower = arquivo.lower()
                if 'contracheque' in nome_lower or 'holerite' in nome_lower or 'pagamento' in nome_lower:
                    tipo = 'contracheque'
                elif 'certificado' in nome_lower or 'residencia' in nome_lower or 'coreme' in nome_lower:
                    tipo = 'certificado_residencia'
                elif 'comprovante' in nome_lower or 'endereco' in nome_lower:
                    tipo = 'comprovante_residencia'
                elif 'rg' in nome_lower or 'cpf' in nome_lower or 'identidade' in nome_lower or 'cnh' in nome_lower:
                    tipo = 'documentos_pessoais'
                elif 'processo' in nome_lower or 'peticao' in nome_lower:
                    tipo = 'processo_anterior'
                else:
                    tipo = 'documento_geral'
                
                # Copiar para pasta de demanda
                os.makedirs(pasta_demanda, exist_ok=True)
                ext = os.path.splitext(arquivo)[1]
                novo_nome = f"{tipo}_{uuid.uuid4().hex[:8]}{ext}"
                novo_path = os.path.join(pasta_demanda, novo_nome)
                
                try:
                    shutil.copy2(arquivo_path, novo_path)
                    
                    # Salvar na tabela
                    sucesso = salvar_documento_demanda(
                        cadastro_id, tipo, novo_nome, 
                        arquivo, novo_path, f"Importado de {arquivo}"
                    )
                    
                    if sucesso:
                        importados.append({"nome": arquivo, "tipo": tipo})
                    else:
                        ja_existentes.append(arquivo)
                except Exception as e:
                    logger.error(f"Erro ao importar {arquivo}: {e}")
    
    # Também verificar lista de documentos do cadastro que podem não estar na pasta
    for doc_nome in cadastro.get("documentos", []):
        doc_path = os.path.join(pasta_cliente, doc_nome)
        if os.path.exists(doc_path) and doc_nome not in [d["nome"] for d in importados]:
            # Já foi processado no loop acima
            continue
    
    return {
        "success": True,
        "importados": importados,
        "total_importados": len(importados),
        "ja_existentes": ja_existentes,
        "message": f"{len(importados)} documento(s) importado(s) para a demanda"
    }


@app.post("/api/cadastros/{cadastro_id}/demanda-especifica")
async def salvar_rascunho_demanda(cadastro_id: str, dados: SalvarRascunhoDemanda):
    """Salva ou atualiza dados específicos de uma demanda (rascunho)."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    sucesso = salvar_dados_demanda(cadastro_id, dados.tipo_demanda, dados.dados, "rascunho")
    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao salvar rascunho")
    
    return {"success": True, "message": "Rascunho salvo com sucesso"}

@app.get("/api/cadastros/{cadastro_id}/demanda-especifica/{tipo_demanda}")
async def buscar_rascunho_demanda(cadastro_id: str, tipo_demanda: str):
    """Busca dados específicos de uma demanda."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    dados = buscar_dados_demanda(cadastro_id, tipo_demanda)
    return {"success": True, "dados": dados}

@app.post("/api/cadastros/{cadastro_id}/documento-demanda/{tipo_documento}")
async def upload_documento_demanda(
    cadastro_id: str, 
    tipo_documento: str,
    arquivo: UploadFile = File(...),
    descricao: str = Form("")
):
    """Faz upload de um documento específico da demanda."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    # Criar diretório para documentos da demanda
    cliente_dir = os.path.join(UPLOADS_DIR, "documentos_demanda", cadastro_id)
    os.makedirs(cliente_dir, exist_ok=True)
    
    # Gerar nome único para o arquivo
    ext = os.path.splitext(arquivo.filename)[1]
    nome_arquivo = f"{tipo_documento}_{uuid.uuid4().hex[:8]}{ext}"
    arquivo_path = os.path.join(cliente_dir, nome_arquivo)
    
    # Salvar arquivo
    with open(arquivo_path, "wb") as f:
        content = await arquivo.read()
        f.write(content)
    
    # Salvar referência no banco
    sucesso = salvar_documento_demanda(
        cadastro_id, tipo_documento, nome_arquivo, 
        arquivo.filename, arquivo_path, descricao
    )
    
    if not sucesso:
        raise HTTPException(status_code=500, detail="Erro ao registrar documento")
    
    return {"success": True, "message": "Documento enviado com sucesso", "nome_arquivo": nome_arquivo}

@app.get("/api/cadastros/{cadastro_id}/documentos-demanda")
async def listar_docs_demanda(cadastro_id: str):
    """Lista documentos específicos da demanda."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    documentos = listar_documentos_demanda(cadastro_id)
    return {"success": True, "documentos": documentos}

@app.get("/api/cadastros/{cadastro_id}/documentos-demanda/{doc_id}/download")
async def download_documento_demanda(cadastro_id: str, doc_id: int):
    """Download de um documento específico da demanda."""
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    conn = get_db()
    if not conn:
        raise HTTPException(status_code=500, detail="Erro de conexão com banco")
    
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM documentos_demanda 
            WHERE id = %s AND cadastro_id = %s
        """, (doc_id, cadastro_id))
        doc = cur.fetchone()
        cur.close()
        conn.close()
        
        if not doc:
            raise HTTPException(status_code=404, detail="Documento não encontrado")
        
        arquivo_path = doc['arquivo_path']
        if not os.path.exists(arquivo_path):
            raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")
        
        return FileResponse(
            arquivo_path,
            filename=doc['nome_original'],
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao baixar documento da demanda: {e}")
        raise HTTPException(status_code=500, detail="Erro ao baixar documento")


# ============================================
# FUNÇÃO PARA GERAR PETIÇÃO INICIAL - AUXÍLIO MORADIA
# ============================================

def gerar_peticao_auxilio_moradia(dados_cliente: dict, dados_residencia: dict, cadastro_id: str) -> str:
    """
    Gera a petição inicial de auxílio moradia para residência médica.
    Usa o modelo peticao_auxilio_moradia_modelo.docx com substituição de placeholders.
    """

    # Caminho do modelo
    modelo_path = os.path.join(MODELOS_DIR, 'peticao_auxilio_moradia_modelo.docx')

    if not os.path.exists(modelo_path):
        raise FileNotFoundError(f"Modelo não encontrado: {modelo_path}")

    # Funções auxiliares
    def formatar_data(data_str):
        """Formata data de YYYY-MM-DD para DD/MM/YYYY."""
        if not data_str:
            return ''
        try:
            partes = data_str.split('-')
            return f"{partes[2]}/{partes[1]}/{partes[0]}"
        except:
            return data_str

    def formatar_moeda(valor):
        """Formata valor para moeda brasileira."""
        try:
            valor_float = float(valor)
            return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "R$ 0,00"

    def valor_por_extenso(valor):
        """Converte valor para extenso (simplificado)."""
        try:
            valor_float = float(valor)
            inteiro = int(valor_float)
            centavos = int((valor_float - inteiro) * 100)
            # Simplificado - retorna o valor numérico formatado
            if centavos > 0:
                return f"{inteiro} reais e {centavos} centavos"
            return f"{inteiro} reais"
        except:
            return "zero reais"

    # Extrair dados do cliente
    nome = dados_cliente.get('nome', '').upper()
    cpf = dados_cliente.get('cpf', '')
    endereco = dados_cliente.get('endereco_completo', '')
    estado_civil = dados_cliente.get('estado_civil', '')

    # Extrair dados da residência médica
    hospital_nome = dados_residencia.get('unidade_hospitalar', '')
    hospital_nome_completo = dados_residencia.get('unidade_hospitalar', '')
    cnpj_hospital = dados_residencia.get('cnpj_hospital', '')
    endereco_hospital = dados_residencia.get('endereco_hospital', '')

    universidade_nome = dados_residencia.get('instituicao_ensino', '')
    cnpj_universidade = dados_residencia.get('cnpj_universidade', '')
    endereco_universidade = dados_residencia.get('endereco_universidade', '')

    especialidade = dados_residencia.get('especialidade_medica', '')
    data_inicio = dados_residencia.get('data_inicio_residencia', '')
    data_termino = dados_residencia.get('data_termino_residencia', '')
    valor_bolsa = dados_residencia.get('valor_bolsa_mensal', 0)

    # Dados do processo anterior (se houver)
    numero_processo_anterior_1 = dados_residencia.get('numero_processo_anterior', '')
    numero_processo_anterior_2 = dados_residencia.get('numero_processo_anterior_2', '')
    vara_anterior_1 = dados_residencia.get('vara_juizado_anterior', '')
    vara_anterior_2 = dados_residencia.get('vara_juizado_anterior_2', '')
    data_ajuizamento_anterior = dados_residencia.get('data_protocolo_anterior', '')

    # Calcular valores
    try:
        valor_bolsa_float = float(valor_bolsa) if valor_bolsa else 0
        valor_auxilio_moradia = valor_bolsa_float * 0.30

        # Calcular período e total
        if data_inicio and data_termino:
            from datetime import datetime as dt
            dt_inicio = dt.strptime(data_inicio, '%Y-%m-%d')
            dt_termino = dt.strptime(data_termino, '%Y-%m-%d')
            meses = (dt_termino.year - dt_inicio.year) * 12 + (dt_termino.month - dt_inicio.month)
            if meses < 0:
                meses = 0
        else:
            meses = 0

        valor_total_bolsas = valor_auxilio_moradia * meses
        periodo_auxilio = f"{meses} meses"
    except:
        valor_auxilio_moradia = 0
        valor_total_bolsas = 0
        periodo_auxilio = ""

    # Determinar gênero (baseado no estado civil ou nome)
    # Por padrão, usar feminino se estado_civil terminar em 'a' (casada, solteira, etc.)
    genero_feminino = estado_civil.lower().endswith('a') if estado_civil else False
    a_o = "a" if genero_feminino else "o"
    a_vazio = "a" if genero_feminino else ""

    # Mapeamento de placeholders para valores
    substituicoes = {
        '{{NOME_AUTOR}}': nome,
        '{{ESTADO_CIVIL}}': estado_civil,
        '{{CPF}}': cpf,
        '{{ENDERECO_COMPLETO}}': endereco,
        '{{A_O}}': a_o,
        '{{A_VAZIO}}': a_vazio,
        '{{HOSPITAL_NOME_COMPLETO}}': hospital_nome_completo,
        '{{HOSPITAL_NOME}}': hospital_nome,
        '{{CNPJ_HOSPITAL}}': cnpj_hospital,
        '{{ENDERECO_HOSPITAL}}': endereco_hospital,
        '{{UNIVERSIDADE_NOME}}': universidade_nome,
        '{{CNPJ_UNIVERSIDADE}}': cnpj_universidade,
        '{{ENDERECO_UNIVERSIDADE}}': endereco_universidade,
        '{{ESPECIALIDADE}}': especialidade,
        '{{DATA_INICIO_RESIDENCIA}}': formatar_data(data_inicio),
        '{{DATA_FIM_RESIDENCIA}}': formatar_data(data_termino),
        '{{PERIODO_AUXILIO}}': periodo_auxilio,
        '{{VALOR_BOLSA_MENSAL}}': formatar_moeda(valor_bolsa),
        '{{VALOR_AUXILIO_MORADIA}}': formatar_moeda(valor_auxilio_moradia),
        '{{VALOR_AUXILIO_MORADIA_EXTENSO}}': valor_por_extenso(valor_auxilio_moradia),
        '{{VALOR_TOTAL_BOLSAS}}': formatar_moeda(valor_total_bolsas),
        '{{NUMERO_PROCESSO_ANTERIOR_1}}': numero_processo_anterior_1,
        '{{NUMERO_PROCESSO_ANTERIOR_2}}': numero_processo_anterior_2,
        '{{VARA_ANTERIOR_1}}': vara_anterior_1,
        '{{VARA_ANTERIOR_2}}': vara_anterior_2,
        '{{DATA_AJUIZAMENTO_ANTERIOR}}': formatar_data(data_ajuizamento_anterior),
    }

    # Criar diretório de saída
    cliente_dir = os.path.join(GERADOS_DIR, cadastro_id)
    os.makedirs(cliente_dir, exist_ok=True)

    # Criar diretório temporário para extração
    temp_dir = os.path.join(cliente_dir, f'temp_{uuid.uuid4().hex[:8]}')
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Extrair o modelo (DOCX é um ZIP)
        with zipfile.ZipFile(modelo_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Ler o document.xml
        doc_xml_path = os.path.join(temp_dir, 'word', 'document.xml')
        with open(doc_xml_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Substituir todos os placeholders
        for placeholder, valor in substituicoes.items():
            content = content.replace(placeholder, str(valor) if valor else '')

        # Salvar o XML modificado
        with open(doc_xml_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Criar o documento final
        nome_arquivo = f"Peticao_Auxilio_Moradia_{nome.replace(' ', '_')}.docx"
        caminho_arquivo = os.path.join(cliente_dir, nome_arquivo)

        # Recriar o DOCX
        with zipfile.ZipFile(caminho_arquivo, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        return caminho_arquivo

    finally:
        # Limpar diretório temporário
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# ============================================
# ENDPOINTS PARA GERAR PETIÇÃO INICIAL
# ============================================

@app.post("/api/admin/clientes/{cadastro_id}/gerar-peticao/{tipo_demanda}")
async def gerar_peticao_inicial(cadastro_id: str, tipo_demanda: str, usuario: dict = Depends(verificar_admin)):
    """Gera a petição inicial para uma demanda específica."""
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    dados_demanda = buscar_dados_demanda(cadastro_id, tipo_demanda)
    if not dados_demanda:
        raise HTTPException(status_code=404, detail="Dados da demanda não encontrados")
    
    try:
        if tipo_demanda == "auxilio_moradia_residencia":
            caminho = gerar_peticao_auxilio_moradia(
                cadastro.get('dados', {}),
                dados_demanda.get('dados', {}),
                cadastro_id
            )
            
            # Atualizar arquivos_gerados no cadastro
            arquivos = cadastro.get('arquivos_gerados', {})
            arquivos['peticao_auxilio_moradia'] = caminho
            
            conn = get_db()
            if conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE cadastros SET arquivos_gerados = %s WHERE id = %s
                """, (json.dumps(arquivos), cadastro_id))
                conn.commit()
                cur.close()
                conn.close()
            
            return {
                "success": True,
                "message": "Petição gerada com sucesso",
                "arquivo": os.path.basename(caminho)
            }
        else:
            raise HTTPException(status_code=400, detail="Tipo de demanda não suportado para geração de petição")
    
    except Exception as e:
        logger.error(f"Erro ao gerar petição: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao gerar petição: {str(e)}")

@app.get("/api/admin/clientes/{cadastro_id}/peticao/{tipo_demanda}")
async def download_peticao(cadastro_id: str, tipo_demanda: str, usuario: dict = Depends(verificar_admin)):
    """Download da petição gerada."""
    
    cadastro = buscar_cadastro(cadastro_id)
    if not cadastro:
        raise HTTPException(status_code=404, detail="Cadastro não encontrado")
    
    arquivos = cadastro.get('arquivos_gerados', {})
    
    if tipo_demanda == "auxilio_moradia_residencia":
        caminho = arquivos.get('peticao_auxilio_moradia')
    else:
        raise HTTPException(status_code=400, detail="Tipo de demanda não suportado")
    
    if not caminho or not os.path.exists(caminho):
        raise HTTPException(status_code=404, detail="Petição não encontrada. Gere a petição primeiro.")
    
    return FileResponse(
        caminho,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=os.path.basename(caminho)
    )

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
