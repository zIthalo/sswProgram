# -*- coding: utf-8 -*-
"""
database.py
Camada de acesso a dados (SQLite). Usa apenas a biblioteca padrao do Python
para garantir compatibilidade com Windows 7+ e futura portabilidade para Linux.
"""

import sqlite3
import os
import sys
from datetime import datetime

DB_NAME = "sac_logistica.db"


def get_db_path():
    """Retorna o caminho do arquivo de banco de dados, ao lado do executavel/script."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, DB_NAME)


def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nf_numero INTEGER NOT NULL,
            cliente TEXT NOT NULL,
            ocorrencia TEXT NOT NULL,
            sigla TEXT NOT NULL,
            data_ocorrencia TEXT NOT NULL,      -- ddmmyyyy, data informada pelo usuario
            criado_em TEXT NOT NULL,            -- timestamp ISO completo p/ ordenacao
            resolvido INTEGER NOT NULL DEFAULT 0,
            lembrete_codigo INTEGER,            -- codigo digitado pelo usuario (1-50 ou 100..400)
            proximo_lembrete TEXT,              -- timestamp ISO do proximo disparo
            agendamento_data TEXT,              -- ddmmyyyy, data do agendamento (se aplicavel)
            verificado_parceiro INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tratativas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            texto TEXT NOT NULL,
            FOREIGN KEY (nota_id) REFERENCES notas(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS empresas_parceiras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes_cadastrados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ocorrencias_tipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            built_in INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nf_numero INTEGER NOT NULL,
            cliente TEXT NOT NULL,
            ocorrencia TEXT NOT NULL,
            sigla TEXT NOT NULL,
            dias INTEGER NOT NULL,
            horas INTEGER NOT NULL,
            morosidade TEXT NOT NULL,   -- 'unidade' | 'cliente' | 'nenhum'
            resolvido_em TEXT NOT NULL   -- timestamp ISO, usado p/ expirar em 60 dias
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS alertas_disparados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,      -- ex: 'agendamento_filial', 'parceiro_10h', 'parceiro_16h', 'prioridade_10h', 'prioridade_17h'
            data_disparo TEXT NOT NULL,  -- ddmmyyyy (dia em que ja disparou, evita repeticao)
            UNIQUE(nota_id, tipo, data_disparo)
        )
    """)

    conn.commit()

    # Migracao: se a tabela historico for de uma versao anterior do sistema (sem a
    # coluna 'morosidade'), recria com o novo formato (dias/horas/morosidade).
    cur.execute("PRAGMA table_info(historico)")
    colunas = [c["name"] for c in cur.fetchall()]
    if "morosidade" not in colunas:
        cur.execute("DROP TABLE historico")
        cur.execute("""
            CREATE TABLE historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nf_numero INTEGER NOT NULL,
                cliente TEXT NOT NULL,
                ocorrencia TEXT NOT NULL,
                sigla TEXT NOT NULL,
                dias INTEGER NOT NULL,
                horas INTEGER NOT NULL,
                morosidade TEXT NOT NULL,
                resolvido_em TEXT NOT NULL
            )
        """)
        conn.commit()

    # Popular ocorrencias padrao (built-in) se ainda nao existirem (em maiusculas)
    built_in = ["REENTREGA", "MUDOU-SE", "LOCALIZAÇÃO", "ACOMPANHAR",
                "COMPROVANTE", "PRIORIZAR ENTREGA", "AGENDAMENTO", "DEVOLUÇÃO", "OUTROS"]
    for nome in built_in:
        try:
            cur.execute("INSERT INTO ocorrencias_tipos (nome, built_in) VALUES (?, 1)", (nome,))
        except sqlite3.IntegrityError:
            pass

    # Popular empresas parceiras padrao (Agex, Risso) se ainda nao existirem
    for nome in ["Agex", "Risso"]:
        try:
            cur.execute("INSERT INTO empresas_parceiras (nome) VALUES (?)", (nome,))
        except sqlite3.IntegrityError:
            pass

    conn.commit()

    # Migracao: converte todos os tipos de ocorrencia ja cadastrados (inclusive
    # customizados criados pelo usuario) e as ocorrencias ja gravadas em notas
    # e no historico para letras maiusculas.
    _migrar_ocorrencias_maiusculas(cur)
    conn.commit()
    conn.close()


def _migrar_ocorrencias_maiusculas(cur):
    cur.execute("SELECT id, nome FROM ocorrencias_tipos")
    linhas = cur.fetchall()
    vistos = set()
    for r in linhas:
        maiusc = r["nome"].upper()
        if maiusc in vistos:
            cur.execute("DELETE FROM ocorrencias_tipos WHERE id=?", (r["id"],))
        else:
            vistos.add(maiusc)
            if maiusc != r["nome"]:
                cur.execute("UPDATE ocorrencias_tipos SET nome=? WHERE id=?", (maiusc, r["id"]))
    cur.execute("UPDATE notas SET ocorrencia = UPPER(ocorrencia)")
    cur.execute("UPDATE historico SET ocorrencia = UPPER(ocorrencia)")


# ---------------------------------------------------------------------------
# CRUD de notas
# ---------------------------------------------------------------------------

def inserir_nota(nf_numero, cliente, ocorrencia, sigla, data_ocorrencia,
                  lembrete_codigo=None, proximo_lembrete=None, agendamento_data=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO notas (nf_numero, cliente, ocorrencia, sigla, data_ocorrencia,
                            criado_em, resolvido, lembrete_codigo, proximo_lembrete, agendamento_data)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
    """, (nf_numero, cliente, ocorrencia, sigla, data_ocorrencia,
          datetime.now().isoformat(), lembrete_codigo, proximo_lembrete, agendamento_data))
    conn.commit()
    novo_id = cur.lastrowid
    conn.close()
    return novo_id


def buscar_duplicada(nf_numero, cliente, ocorrencia):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM notas WHERE nf_numero=? AND cliente=? AND ocorrencia=? AND resolvido=0
    """, (nf_numero, cliente, ocorrencia))
    row = cur.fetchone()
    conn.close()
    return row


def listar_notas_ativas():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notas WHERE resolvido=0 ORDER BY criado_em ASC")
    rows = cur.fetchall()
    conn.close()
    return rows


def obter_nota(nota_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM notas WHERE id=?", (nota_id,))
    row = cur.fetchone()
    conn.close()
    return row


def atualizar_campo_nota(nota_id, campo, valor):
    campos_validos = {"nf_numero", "cliente", "ocorrencia", "sigla", "data_ocorrencia",
                       "lembrete_codigo", "proximo_lembrete", "agendamento_data",
                       "verificado_parceiro", "resolvido"}
    if campo not in campos_validos:
        raise ValueError("Campo invalido: %s" % campo)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE notas SET %s=? WHERE id=?" % campo, (valor, nota_id))
    conn.commit()
    conn.close()


def remover_nota(nota_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM notas WHERE id=?", (nota_id,))
    conn.commit()
    conn.close()


def marcar_resolvida(nota_id):
    atualizar_campo_nota(nota_id, "resolvido", 1)


# ---------------------------------------------------------------------------
# Tratativas (atualizacoes de ocorrencia)
# ---------------------------------------------------------------------------

def adicionar_tratativa(nota_id, texto):
    conn = get_connection()
    cur = conn.cursor()
    ts = datetime.now().strftime("%d/%m/%Y %H:%M")
    cur.execute("INSERT INTO tratativas (nota_id, timestamp, texto) VALUES (?, ?, ?)",
                (nota_id, ts, texto))
    conn.commit()
    conn.close()


def listar_tratativas(nota_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tratativas WHERE nota_id=? ORDER BY id ASC", (nota_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Empresas parceiras (Agex, Risso, etc.)
# ---------------------------------------------------------------------------

def listar_empresas_parceiras():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM empresas_parceiras ORDER BY nome ASC")
    rows = cur.fetchall()
    conn.close()
    return [r["nome"] for r in rows]


def adicionar_empresa_parceira(nome):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO empresas_parceiras (nome) VALUES (?)", (nome,))
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    conn.close()
    return ok


def remover_empresa_parceira(nome):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM empresas_parceiras WHERE nome=?", (nome,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Remetentes/clientes cadastrados (para sugestao automatica ao digitar)
# ---------------------------------------------------------------------------

def listar_clientes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nome FROM clientes_cadastrados ORDER BY nome ASC")
    rows = cur.fetchall()
    conn.close()
    return [r["nome"] for r in rows]


def adicionar_cliente(nome):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO clientes_cadastrados (nome) VALUES (?)", (nome,))
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    conn.close()
    return ok


def remover_cliente(nome):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM clientes_cadastrados WHERE nome=?", (nome,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Tipos de ocorrencia (built-in + customizados)
# ---------------------------------------------------------------------------

def listar_tipos_ocorrencia():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nome FROM ocorrencias_tipos ORDER BY built_in DESC, nome ASC")
    rows = cur.fetchall()
    conn.close()
    return [r["nome"] for r in rows]


def adicionar_tipo_ocorrencia(nome):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO ocorrencias_tipos (nome, built_in) VALUES (?, 0)", (nome,))
        conn.commit()
        ok = True
    except sqlite3.IntegrityError:
        ok = False
    conn.close()
    return ok


def remover_tipo_ocorrencia(nome):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM ocorrencias_tipos WHERE nome=? AND built_in=0", (nome,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Historico / Relatorio
# ---------------------------------------------------------------------------

def inserir_historico(nf_numero, cliente, ocorrencia, sigla, dias, horas, morosidade):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO historico (nf_numero, cliente, ocorrencia, sigla, dias, horas, morosidade, resolvido_em)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (nf_numero, cliente, ocorrencia, sigla, dias, horas, morosidade, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def buscar_historico_por_nf(nf_numero):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM historico WHERE nf_numero=? ORDER BY resolvido_em DESC", (nf_numero,))
    rows = cur.fetchall()
    conn.close()
    return rows


def buscar_historico_por_sigla(sigla, somente_morosidade_unidade=False):
    """Retorna os registros do historico de uma sigla/unidade, usados como
    embasamento dos itens clicaveis do top 5 no relatorio. Quando
    somente_morosidade_unidade=True, traz apenas os casos em que essa unidade
    foi apontada como a mais morosa."""
    conn = get_connection()
    cur = conn.cursor()
    if somente_morosidade_unidade:
        cur.execute(
            "SELECT * FROM historico WHERE sigla=? AND morosidade='unidade' ORDER BY resolvido_em DESC",
            (sigla,))
    else:
        cur.execute("SELECT * FROM historico WHERE sigla=? ORDER BY resolvido_em DESC", (sigla,))
    rows = cur.fetchall()
    conn.close()
    return rows


def limpar_historico_expirado(dias=60):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, resolvido_em FROM historico")
    rows = cur.fetchall()
    agora = datetime.now()
    for r in rows:
        try:
            dt = datetime.fromisoformat(r["resolvido_em"])
        except ValueError:
            continue
        if (agora - dt).days >= dias:
            cur.execute("DELETE FROM historico WHERE id=?", (r["id"],))
    conn.commit()
    conn.close()


def limpar_historico_manual():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM historico")
    conn.commit()
    conn.close()


def listar_historico():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM historico ORDER BY resolvido_em DESC")
    rows = cur.fetchall()
    conn.close()
    return rows


def gerar_relatorio():
    """Retorna dict com os dados exibidos na tela de Relatorio (top 5 em cada lista)."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT sigla, COUNT(*) as total FROM historico
        GROUP BY sigla ORDER BY total DESC LIMIT 5
    """)
    siglas_mais_ocorrencias = [(r["sigla"], r["total"]) for r in cur.fetchall()]

    cur.execute("""
        SELECT sigla, COUNT(*) as total FROM historico
        WHERE morosidade='unidade' GROUP BY sigla ORDER BY total DESC LIMIT 5
    """)
    unidades_mais_morosas = [(r["sigla"], r["total"]) for r in cur.fetchall()]

    cur.execute("""
        SELECT cliente, COUNT(*) as total FROM historico
        WHERE morosidade='cliente' GROUP BY cliente ORDER BY total DESC LIMIT 5
    """)
    clientes_mais_morosos = [(r["cliente"], r["total"]) for r in cur.fetchall()]

    cur.execute("SELECT dias, horas FROM historico")
    rows = cur.fetchall()
    conn.close()

    horas_totais = [(r["dias"] or 0) * 24 + (r["horas"] or 0) for r in rows]
    media_horas = sum(horas_totais) / len(horas_totais) if horas_totais else 0.0

    return {
        "siglas_mais_ocorrencias": siglas_mais_ocorrencias,
        "unidades_mais_morosas": unidades_mais_morosas,
        "clientes_mais_morosos": clientes_mais_morosos,
        "tempo_medio_dias": int(media_horas // 24),
        "tempo_medio_horas": int(round(media_horas % 24)),
    }


# ---------------------------------------------------------------------------
# Alertas ja disparados (evita repetir popup no mesmo dia)
# ---------------------------------------------------------------------------

def alerta_ja_disparado(nota_id, tipo, data_disparo):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM alertas_disparados WHERE nota_id=? AND tipo=? AND data_disparo=?",
                (nota_id, tipo, data_disparo))
    row = cur.fetchone()
    conn.close()
    return row is not None


def registrar_alerta_disparado(nota_id, tipo, data_disparo):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO alertas_disparados (nota_id, tipo, data_disparo) VALUES (?, ?, ?)",
                    (nota_id, tipo, data_disparo))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
