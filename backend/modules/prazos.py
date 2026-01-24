"""
Módulo de Prazos Processuais do Sistema Vaucher e Álvares
Criado em 23/01/2026

Este arquivo contém a lógica de cálculo automático de prazos processuais
baseado em movimentações do DataJud/CNJ.
"""

import logging
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Tuple
import json

import psycopg2
from psycopg2.extras import RealDictCursor

from modules.config import logger
from modules.database import get_db

# ============================================
# REGRAS DE PRAZOS PROCESSUAIS
# ============================================

# Movimentos que geram prazos automáticos
# Formato: { "palavra_chave": (dias, tipo_prazo, prioridade, dias_uteis) }
REGRAS_PRAZOS = {
    # Intimações e citações
    "intimação": (15, "Resposta à Intimação", "alta", True),
    "intimado": (15, "Resposta à Intimação", "alta", True),
    "citação": (15, "Contestação/Resposta", "alta", True),
    "citado": (15, "Contestação/Resposta", "alta", True),
    "cite-se": (15, "Aguardar Citação", "normal", True),

    # Recursos
    "sentença": (15, "Recurso de Apelação", "alta", True),
    "decisão interlocutória": (15, "Agravo de Instrumento", "alta", True),
    "despacho": (5, "Cumprimento de Despacho", "normal", True),

    # Manifestações
    "manifestação": (5, "Manifestação nos Autos", "normal", True),
    "manifeste-se": (5, "Manifestação nos Autos", "normal", True),
    "vista": (5, "Manifestação nos Autos", "normal", True),
    "prazo para": (15, "Cumprimento de Prazo", "normal", True),

    # Audiências
    "audiência": (0, "Audiência Designada", "alta", False),  # Será extraída a data
    "designada audiência": (0, "Audiência Designada", "alta", False),

    # Perícias
    "perito": (10, "Indicação de Assistente Técnico", "normal", True),
    "perícia": (10, "Quesitos/Assistente Técnico", "normal", True),
    "laudo": (15, "Manifestação sobre Laudo", "normal", True),

    # Pagamentos e cumprimentos
    "pagamento": (15, "Pagamento/Depósito", "alta", True),
    "pagar": (15, "Pagamento/Depósito", "alta", True),
    "cumpra-se": (15, "Cumprimento de Ordem", "normal", True),
    "cumprimento": (15, "Cumprimento de Sentença", "alta", True),

    # Embargos
    "embargos": (15, "Resposta aos Embargos", "alta", True),

    # Impugnações
    "impugnação": (15, "Manifestação sobre Impugnação", "normal", True),
    "impugnar": (15, "Apresentar Impugnação", "normal", True),

    # Outros
    "réplica": (15, "Apresentar Réplica", "normal", True),
    "contrarrazões": (15, "Apresentar Contrarrazões", "alta", True),
    "alegações finais": (15, "Apresentar Alegações Finais", "normal", True),
}

# Feriados nacionais fixos (mês, dia)
FERIADOS_FIXOS = [
    (1, 1),   # Ano Novo
    (4, 21),  # Tiradentes
    (5, 1),   # Dia do Trabalho
    (9, 7),   # Independência
    (10, 12), # Nossa Senhora Aparecida
    (11, 2),  # Finados
    (11, 15), # Proclamação da República
    (12, 25), # Natal
]

# Recesso forense (20/12 a 06/01)
RECESSO_INICIO = (12, 20)
RECESSO_FIM = (1, 6)


# ============================================
# FUNÇÕES DE CÁLCULO DE DIAS ÚTEIS
# ============================================

def eh_feriado_fixo(data: date) -> bool:
    """Verifica se a data é um feriado fixo nacional."""
    return (data.month, data.day) in FERIADOS_FIXOS


def eh_recesso_forense(data: date) -> bool:
    """Verifica se a data está no período de recesso forense."""
    mes, dia = data.month, data.day

    # Dezembro (a partir do dia 20)
    if mes == 12 and dia >= RECESSO_INICIO[1]:
        return True

    # Janeiro (até o dia 6)
    if mes == 1 and dia <= RECESSO_FIM[1]:
        return True

    return False


def eh_dia_util(data: date) -> bool:
    """Verifica se é dia útil (não é fim de semana, feriado ou recesso)."""
    # Fim de semana (0 = segunda, 6 = domingo)
    if data.weekday() >= 5:
        return False

    # Feriado fixo
    if eh_feriado_fixo(data):
        return False

    # Recesso forense
    if eh_recesso_forense(data):
        return False

    return True


def calcular_prazo_dias_uteis(data_inicio: date, dias: int) -> date:
    """
    Calcula a data final considerando apenas dias úteis.
    Exclui fins de semana, feriados e recesso forense.
    """
    if dias <= 0:
        return data_inicio

    data_atual = data_inicio
    dias_contados = 0

    while dias_contados < dias:
        data_atual += timedelta(days=1)
        if eh_dia_util(data_atual):
            dias_contados += 1

    return data_atual


def calcular_prazo_dias_corridos(data_inicio: date, dias: int) -> date:
    """Calcula a data final em dias corridos."""
    return data_inicio + timedelta(days=dias)


def calcular_data_prazo(data_inicio: date, dias: int, dias_uteis: bool = True) -> date:
    """Calcula a data final do prazo."""
    if dias_uteis:
        return calcular_prazo_dias_uteis(data_inicio, dias)
    return calcular_prazo_dias_corridos(data_inicio, dias)


# ============================================
# DETECÇÃO DE MOVIMENTOS QUE GERAM PRAZOS
# ============================================

def detectar_prazo_movimento(movimento_descricao: str) -> Optional[Tuple[int, str, str, bool]]:
    """
    Detecta se um movimento gera prazo automático.
    Retorna: (dias, tipo_prazo, prioridade, dias_uteis) ou None
    """
    descricao_lower = movimento_descricao.lower()

    for palavra_chave, (dias, tipo, prioridade, dias_uteis) in REGRAS_PRAZOS.items():
        if palavra_chave in descricao_lower:
            return (dias, tipo, prioridade, dias_uteis)

    return None


def extrair_data_audiencia(movimento_descricao: str) -> Optional[date]:
    """
    Tenta extrair a data de uma audiência do texto do movimento.
    Formatos comuns: DD/MM/AAAA, DD/MM/AA
    """
    import re

    # Padrão para DD/MM/AAAA ou DD/MM/AA
    padrao = r'(\d{2})/(\d{2})/(\d{2,4})'
    match = re.search(padrao, movimento_descricao)

    if match:
        dia, mes, ano = match.groups()
        ano = int(ano)
        if ano < 100:
            ano += 2000
        try:
            return date(ano, int(mes), int(dia))
        except ValueError:
            pass

    return None


# ============================================
# FUNÇÕES CRUD - PRAZOS
# ============================================

def criar_prazo(
    processo_id: int,
    tipo: str,
    descricao: str,
    data_inicio: date,
    data_fim: date,
    dias_uteis: bool = True,
    prioridade: str = "normal",
    origem: str = "manual",
    movimento_origem: str = None,
    observacoes: str = None
) -> Optional[int]:
    """Cria um novo prazo processual."""
    conn = get_db()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO prazos_processuais
            (processo_id, tipo, descricao, data_inicio, data_fim, dias_uteis,
             prioridade, origem, movimento_origem, observacoes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            processo_id, tipo, descricao, data_inicio, data_fim, dias_uteis,
            prioridade, origem, movimento_origem, observacoes
        ))
        prazo_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Prazo criado: ID={prazo_id}, Processo={processo_id}, Tipo={tipo}")
        return prazo_id
    except Exception as e:
        logger.error(f"Erro ao criar prazo: {e}")
        return None


def listar_prazos_processo(processo_id: int) -> List[dict]:
    """Lista todos os prazos de um processo."""
    conn = get_db()
    if not conn:
        return []

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT * FROM prazos_processuais
            WHERE processo_id = %s
            ORDER BY data_fim ASC
        """, (processo_id,))
        prazos = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(p) for p in prazos]
    except Exception as e:
        logger.error(f"Erro ao listar prazos: {e}")
        return []


def listar_prazos_pendentes(cadastro_id: str = None, dias_limite: int = 30) -> List[dict]:
    """
    Lista prazos pendentes com data de vencimento nos próximos X dias.
    Se cadastro_id for fornecido, filtra por cliente.
    """
    conn = get_db()
    if not conn:
        return []

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        data_limite = date.today() + timedelta(days=dias_limite)

        if cadastro_id:
            cur.execute("""
                SELECT pp.*, p.numero_processo, p.cadastro_id,
                       c.dados->>'nome' as cliente_nome
                FROM prazos_processuais pp
                JOIN processos p ON pp.processo_id = p.id
                JOIN cadastros c ON p.cadastro_id = c.id
                WHERE p.cadastro_id = %s
                  AND pp.status = 'pendente'
                  AND pp.data_fim <= %s
                ORDER BY pp.data_fim ASC
            """, (cadastro_id, data_limite))
        else:
            cur.execute("""
                SELECT pp.*, p.numero_processo, p.cadastro_id,
                       c.dados->>'nome' as cliente_nome
                FROM prazos_processuais pp
                JOIN processos p ON pp.processo_id = p.id
                JOIN cadastros c ON p.cadastro_id = c.id
                WHERE pp.status = 'pendente'
                  AND pp.data_fim <= %s
                ORDER BY pp.data_fim ASC
            """, (data_limite,))

        prazos = cur.fetchall()
        cur.close()
        conn.close()

        # Adicionar informações extras
        resultado = []
        hoje = date.today()
        for p in prazos:
            prazo = dict(p)
            data_fim = prazo["data_fim"]
            if isinstance(data_fim, str):
                data_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()

            dias_restantes = (data_fim - hoje).days
            prazo["dias_restantes"] = dias_restantes
            prazo["vencido"] = dias_restantes < 0
            prazo["vence_hoje"] = dias_restantes == 0
            prazo["urgente"] = dias_restantes <= 3 and dias_restantes >= 0
            resultado.append(prazo)

        return resultado
    except Exception as e:
        logger.error(f"Erro ao listar prazos pendentes: {e}")
        return []


def listar_todos_prazos(status: str = None) -> List[dict]:
    """Lista todos os prazos, opcionalmente filtrados por status."""
    conn = get_db()
    if not conn:
        return []

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        if status:
            cur.execute("""
                SELECT pp.*, p.numero_processo, p.cadastro_id,
                       c.dados->>'nome' as cliente_nome
                FROM prazos_processuais pp
                JOIN processos p ON pp.processo_id = p.id
                JOIN cadastros c ON p.cadastro_id = c.id
                WHERE pp.status = %s
                ORDER BY pp.data_fim ASC
            """, (status,))
        else:
            cur.execute("""
                SELECT pp.*, p.numero_processo, p.cadastro_id,
                       c.dados->>'nome' as cliente_nome
                FROM prazos_processuais pp
                JOIN processos p ON pp.processo_id = p.id
                JOIN cadastros c ON p.cadastro_id = c.id
                ORDER BY pp.data_fim ASC
            """)

        prazos = cur.fetchall()
        cur.close()
        conn.close()

        resultado = []
        hoje = date.today()
        for p in prazos:
            prazo = dict(p)
            data_fim = prazo["data_fim"]
            if isinstance(data_fim, str):
                data_fim = datetime.strptime(data_fim, "%Y-%m-%d").date()

            dias_restantes = (data_fim - hoje).days
            prazo["dias_restantes"] = dias_restantes
            prazo["vencido"] = dias_restantes < 0 and prazo["status"] == "pendente"
            prazo["vence_hoje"] = dias_restantes == 0
            prazo["urgente"] = dias_restantes <= 3 and dias_restantes >= 0
            resultado.append(prazo)

        return resultado
    except Exception as e:
        logger.error(f"Erro ao listar todos prazos: {e}")
        return []


def atualizar_prazo(prazo_id: int, dados: dict) -> bool:
    """Atualiza um prazo existente."""
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()

        updates = []
        values = []

        campos_permitidos = ["tipo", "descricao", "data_inicio", "data_fim",
                            "dias_uteis", "prioridade", "observacoes"]

        for campo in campos_permitidos:
            if campo in dados:
                updates.append(f"{campo} = %s")
                values.append(dados[campo])

        if updates:
            updates.append("atualizado_em = CURRENT_TIMESTAMP")
            values.append(prazo_id)
            cur.execute(f"""
                UPDATE prazos_processuais
                SET {', '.join(updates)}
                WHERE id = %s
            """, values)
            conn.commit()

        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar prazo: {e}")
        return False


def concluir_prazo(prazo_id: int, usuario: str = None) -> bool:
    """Marca um prazo como concluído."""
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE prazos_processuais
            SET status = 'concluido',
                concluido_em = CURRENT_TIMESTAMP,
                concluido_por = %s,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (usuario, prazo_id))
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Prazo {prazo_id} concluído por {usuario}")
        return True
    except Exception as e:
        logger.error(f"Erro ao concluir prazo: {e}")
        return False


def cancelar_prazo(prazo_id: int, motivo: str = None) -> bool:
    """Cancela um prazo."""
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE prazos_processuais
            SET status = 'cancelado',
                observacoes = COALESCE(observacoes || ' | ', '') || %s,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (f"Cancelado: {motivo}" if motivo else "Cancelado", prazo_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao cancelar prazo: {e}")
        return False


def deletar_prazo(prazo_id: int) -> bool:
    """Deleta um prazo (use com cuidado)."""
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM prazos_processuais WHERE id = %s", (prazo_id,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Erro ao deletar prazo: {e}")
        return False


# ============================================
# GERAÇÃO AUTOMÁTICA DE PRAZOS
# ============================================

def prazo_ja_existe(processo_id: int, tipo: str, data_inicio: date) -> bool:
    """Verifica se já existe um prazo similar para evitar duplicatas."""
    conn = get_db()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM prazos_processuais
            WHERE processo_id = %s AND tipo = %s AND data_inicio = %s
        """, (processo_id, tipo, data_inicio))
        existe = cur.fetchone() is not None
        cur.close()
        conn.close()
        return existe
    except Exception as e:
        logger.error(f"Erro ao verificar prazo existente: {e}")
        return False


def gerar_prazos_movimento(
    processo_id: int,
    data_movimento: date,
    descricao_movimento: str
) -> List[int]:
    """
    Analisa um movimento e gera prazos automáticos se aplicável.
    Retorna lista de IDs dos prazos criados.
    """
    prazos_criados = []

    resultado = detectar_prazo_movimento(descricao_movimento)
    if not resultado:
        return prazos_criados

    dias, tipo_prazo, prioridade, dias_uteis = resultado

    # Tratamento especial para audiências
    if "audiência" in tipo_prazo.lower():
        data_audiencia = extrair_data_audiencia(descricao_movimento)
        if data_audiencia:
            # Criar prazo para a data da audiência
            if not prazo_ja_existe(processo_id, tipo_prazo, data_movimento):
                prazo_id = criar_prazo(
                    processo_id=processo_id,
                    tipo=tipo_prazo,
                    descricao=f"Audiência: {descricao_movimento[:200]}",
                    data_inicio=data_movimento,
                    data_fim=data_audiencia,
                    dias_uteis=False,
                    prioridade="alta",
                    origem="datajud",
                    movimento_origem=descricao_movimento[:500]
                )
                if prazo_id:
                    prazos_criados.append(prazo_id)
    else:
        # Calcular data fim
        data_fim = calcular_data_prazo(data_movimento, dias, dias_uteis)

        # Verificar se já existe
        if not prazo_ja_existe(processo_id, tipo_prazo, data_movimento):
            prazo_id = criar_prazo(
                processo_id=processo_id,
                tipo=tipo_prazo,
                descricao=f"{tipo_prazo}: {descricao_movimento[:200]}",
                data_inicio=data_movimento,
                data_fim=data_fim,
                dias_uteis=dias_uteis,
                prioridade=prioridade,
                origem="datajud",
                movimento_origem=descricao_movimento[:500]
            )
            if prazo_id:
                prazos_criados.append(prazo_id)

    return prazos_criados


def processar_andamentos_para_prazos(processo_id: int) -> Dict:
    """
    Processa todos os andamentos de um processo e gera prazos automáticos.
    Retorna estatísticas.
    """
    conn = get_db()
    if not conn:
        return {"erro": "Erro de conexão"}

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT data, descricao FROM processo_andamentos
            WHERE processo_id = %s
            ORDER BY data DESC
        """, (processo_id,))
        andamentos = cur.fetchall()
        cur.close()
        conn.close()

        total_analisados = len(andamentos)
        prazos_criados = 0

        for andamento in andamentos:
            data_mov = andamento["data"]
            if isinstance(data_mov, str):
                data_mov = datetime.strptime(data_mov, "%Y-%m-%d").date()

            ids = gerar_prazos_movimento(processo_id, data_mov, andamento["descricao"])
            prazos_criados += len(ids)

        return {
            "sucesso": True,
            "andamentos_analisados": total_analisados,
            "prazos_criados": prazos_criados
        }
    except Exception as e:
        logger.error(f"Erro ao processar andamentos: {e}")
        return {"erro": str(e)}


def obter_resumo_prazos() -> Dict:
    """Retorna um resumo estatístico dos prazos."""
    conn = get_db()
    if not conn:
        return {}

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        hoje = date.today()

        # Total por status
        cur.execute("""
            SELECT status, COUNT(*) as total
            FROM prazos_processuais
            GROUP BY status
        """)
        por_status = {row["status"]: row["total"] for row in cur.fetchall()}

        # Vencidos
        cur.execute("""
            SELECT COUNT(*) as total
            FROM prazos_processuais
            WHERE status = 'pendente' AND data_fim < %s
        """, (hoje,))
        vencidos = cur.fetchone()["total"]

        # Vencem hoje
        cur.execute("""
            SELECT COUNT(*) as total
            FROM prazos_processuais
            WHERE status = 'pendente' AND data_fim = %s
        """, (hoje,))
        vence_hoje = cur.fetchone()["total"]

        # Próximos 7 dias
        cur.execute("""
            SELECT COUNT(*) as total
            FROM prazos_processuais
            WHERE status = 'pendente' AND data_fim BETWEEN %s AND %s
        """, (hoje, hoje + timedelta(days=7)))
        proximos_7_dias = cur.fetchone()["total"]

        cur.close()
        conn.close()

        return {
            "por_status": por_status,
            "pendentes": por_status.get("pendente", 0),
            "concluidos": por_status.get("concluido", 0),
            "cancelados": por_status.get("cancelado", 0),
            "vencidos": vencidos,
            "vence_hoje": vence_hoje,
            "proximos_7_dias": proximos_7_dias
        }
    except Exception as e:
        logger.error(f"Erro ao obter resumo: {e}")
        return {}
