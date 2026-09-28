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
    # Modo WAL + synchronous=NORMAL deixam os commits bem mais rapidos (menos
    # espera por gravacao em disco a cada insercao de nota/tratativa), com um
    # risco de durabilidade minimo (so afeta os ultimos commits em caso de
    # queda de energia/travamento do sistema operacional, cenario raro em uso
    # normal) — troca padrao para aplicativos desktop que precisam responder
    # rapido a cada acao do usuario.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
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
            data_ocorrencia TEXT NOT NULL,      -- ddmmyyyy, data em que a nota foi inserida
            criado_em TEXT NOT NULL,            -- timestamp ISO completo p/ ordenacao
            resolvido INTEGER NOT NULL DEFAULT 0,
            agendamento_data TEXT               -- ddmmyyyy, data do agendamento (se aplicavel)
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

    conn.commit()

    # Migracao: remove colunas relacionadas a lembretes (funcionalidade removida
    # do sistema) da tabela notas, recriando-a sem elas caso ainda existam.
    _migrar_remover_lembretes(cur)
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


def _migrar_remover_lembretes(cur):
    """Remove as colunas relacionadas a lembretes (lembrete_codigo,
    proximo_lembrete, verificado_parceiro) da tabela notas, caso existam de
    uma versao anterior do sistema, e descarta a tabela de alertas
    disparados, que nao e mais utilizada."""
    cur.execute("PRAGMA table_info(notas)")
    colunas = [c["name"] for c in cur.fetchall()]
    if "lembrete_codigo" in colunas or "verificado_parceiro" in colunas:
        cur.execute("""
            CREATE TABLE notas_novo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nf_numero INTEGER NOT NULL,
                cliente TEXT NOT NULL,
                ocorrencia TEXT NOT NULL,
                sigla TEXT NOT NULL,
                data_ocorrencia TEXT NOT NULL,
                criado_em TEXT NOT NULL,
                resolvido INTEGER NOT NULL DEFAULT 0,
                agendamento_data TEXT
            )
        """)
        cur.execute("""
            INSERT INTO notas_novo (id, nf_numero, cliente, ocorrencia, sigla,
                                     data_ocorrencia, criado_em, resolvido, agendamento_data)
            SELECT id, nf_numero, cliente, ocorrencia, sigla,
                   data_ocorrencia, criado_em, resolvido, agendamento_data
            FROM notas
        """)
        cur.execute("DROP TABLE notas")
        cur.execute("ALTER TABLE notas_novo RENAME TO notas")
    cur.execute("DROP TABLE IF EXISTS alertas_disparados")


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

def inserir_nota(nf_numero, cliente, ocorrencia, sigla, data_ocorrencia, agendamento_data=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO notas (nf_numero, cliente, ocorrencia, sigla, data_ocorrencia,
                            criado_em, resolvido, agendamento_data)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?)
    """, (nf_numero, cliente, ocorrencia, sigla, data_ocorrencia,
          datetime.now().isoformat(), agendamento_data))
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
                       "agendamento_data", "resolvido"}
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


def listar_ocorrencias_em_uso():
    """Retorna as ocorrencias (distintas) presentes entre as notas ativas,
    usadas para popular o filtro por ocorrencia mostrando apenas os tipos
    que realmente existem no momento."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT ocorrencia FROM notas WHERE resolvido=0 ORDER BY ocorrencia ASC")
    rows = cur.fetchall()
    conn.close()
    return [r["ocorrencia"] for r in rows]


def contar_notas_pendentes():
    """Quantidade total de notas ainda nao marcadas como resolvidas."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM notas WHERE resolvido=0")
    total = cur.fetchone()["total"]
    conn.close()
    return total


def contar_notas_pendentes_por_sigla(texto):
    """Quantidade de notas pendentes cuja sigla/empresa contenha o texto
    informado (busca parcial, sem diferenciar maiusculas/minusculas)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) as total FROM notas WHERE resolvido=0 AND sigla LIKE ? COLLATE NOCASE",
        ("%" + texto + "%",),
    )
    total = cur.fetchone()["total"]
    conn.close()
    return total


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
    return ts


def listar_tratativas(nota_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tratativas WHERE nota_id=? ORDER BY id ASC", (nota_id,))
    rows = cur.fetchall()
    conn.close()
    return rows


def listar_tratativas_por_notas(nota_ids):
    """Busca as tratativas de varias notas em uma unica consulta (evita repetir
    uma consulta por nota ao recarregar a lista inteira). Retorna um dict
    {nota_id: [linhas de tratativa]}."""
    nota_ids = list(nota_ids)
    if not nota_ids:
        return {}
    conn = get_connection()
    cur = conn.cursor()
    marcadores = ",".join("?" * len(nota_ids))
    cur.execute(
        "SELECT * FROM tratativas WHERE nota_id IN (%s) ORDER BY nota_id ASC, id ASC" % marcadores,
        nota_ids,
    )
    resultado = {}
    for row in cur.fetchall():
        resultado.setdefault(row["nota_id"], []).append(row)
    conn.close()
    return resultado


def buscar_notas_ativas_por_texto_tratativa(texto):
    """Retorna os ids das notas ativas cujas atualizacoes de tratativa contenham
    o texto informado (usado para localizar numeros/textos que o usuario
    tenha digitado dentro das ocorrencias/atualizacoes de uma nota)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT t.nota_id FROM tratativas t
        JOIN notas n ON n.id = t.nota_id
        WHERE n.resolvido = 0 AND t.texto LIKE ?
        """,
        ("%" + texto + "%",),
    )
    rows = cur.fetchall()
    conn.close()
    return [r["nota_id"] for r in rows]


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
