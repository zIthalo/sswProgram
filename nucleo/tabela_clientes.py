# -*- coding: utf-8 -*-
"""
Tabela de clientes (Cliente / CNPJ / Vendedor / Contatos ...), totalmente editavel.

As colunas e as linhas sao do usuario: ele cria, renomeia, move e exclui colunas e linhas, e
digita o que quiser em cada celula. Cada coluna tem um "tipo":
  - "cliente": coluna com o nome do cliente (uma so; usada ao criar notas; nao pode ser excluida)
  - "cnpj":    ao clicar numa celula o numero e copiado para a area de transferencia
  - "texto":   coluna comum
Nenhum dado de cliente vem com o programa: a tabela comeca vazia (so com as 4 colunas padrao) e
e preenchida pelo usuario, digitando ou importando uma planilha .xlsx (importar_xlsx).
Leitura de .xlsx feita so com a biblioteca padrao (zipfile + xml), sem instalar nada.
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from decimal import Decimal

from nucleo import database as db

TIPO_CLIENTE = "cliente"
TIPO_CNPJ = "cnpj"
TIPO_TEXTO = "texto"
COLUNAS_PADRAO = (("Cliente", TIPO_CLIENTE), ("CNPJ", TIPO_CNPJ), ("Vendedor", TIPO_TEXTO),
                  ("Contatos", TIPO_TEXTO))


class TabelaClientesErro(Exception):
    pass


def _conexao():
    """Conexao com as tabelas garantidas (CREATE IF NOT EXISTS e barato; roda a cada uso)."""
    conn = db.get_connection()
    conn.execute("""CREATE TABLE IF NOT EXISTS clientes_colunas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, tipo TEXT NOT NULL DEFAULT 'texto',
        ordem INTEGER NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS clientes_linhas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ordem INTEGER NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS clientes_celulas (
        linha_id INTEGER NOT NULL REFERENCES clientes_linhas(id) ON DELETE CASCADE,
        coluna_id INTEGER NOT NULL REFERENCES clientes_colunas(id) ON DELETE CASCADE,
        valor TEXT NOT NULL DEFAULT '', PRIMARY KEY (linha_id, coluna_id))""")
    if conn.execute("SELECT COUNT(*) FROM clientes_colunas").fetchone()[0] == 0:
        for ordem, (nome, tipo) in enumerate(COLUNAS_PADRAO):
            conn.execute("INSERT INTO clientes_colunas (nome, tipo, ordem) VALUES (?, ?, ?)", (nome, tipo, ordem))
    conn.commit()
    return conn


# ----------------------------------------------------------------------
# Texto: CNPJ e nome do cliente
# ----------------------------------------------------------------------
def normalizar_cnpj(texto):
    """Digitos com 14 casas quando for um CNPJ (recupera os zeros a esquerda que o Excel
    apaga: 12 ou 13 digitos viram 14). Qualquer outro texto fica como o usuario digitou."""
    texto = (texto or "").strip()
    digitos = re.sub(r"\D", "", texto)
    if digitos and re.fullmatch(r"[\d.\-/\s]+", texto) and 12 <= len(digitos) <= 14:
        return digitos.zfill(14)
    return texto


def formatar_cnpj(valor):
    """00.000.000/0000-00 para valores de 14 digitos; o resto aparece como esta."""
    if re.fullmatch(r"\d{14}", valor or ""):
        d = valor
        return "%s.%s.%s/%s-%s" % (d[:2], d[2:5], d[5:8], d[8:12], d[12:])
    return valor or ""


def texto_para_copiar(valor):
    """O que vai para a area de transferencia ao clicar num CNPJ: so os numeros."""
    valor = (valor or "").strip()
    digitos = re.sub(r"\D", "", valor)
    return digitos if digitos and re.fullmatch(r"[\d.\-/\s]+", valor) else valor


def nome_para_nota(cliente):
    """Nome do cliente para criar uma nota: corta anotacoes depois de '/' seguida de espaco
    ('Empresa Exemplo/ nao possui isencao' -> 'Empresa Exemplo'); 'S/A' e preservado."""
    return re.split(r"\s*/\s+", (cliente or "").strip(), maxsplit=1)[0].strip()


# ----------------------------------------------------------------------
# Colunas
# ----------------------------------------------------------------------
def listar_colunas():
    conn = _conexao()
    try:
        return [dict(r) for r in conn.execute("SELECT id, nome, tipo, ordem FROM clientes_colunas ORDER BY ordem, id")]
    finally:
        conn.close()


def _validar_nome_coluna(conn, nome, ignorar_id=None):
    nome = (nome or "").strip()
    if not nome:
        raise TabelaClientesErro("Digite um nome para a coluna.")
    for r in conn.execute("SELECT id, nome FROM clientes_colunas"):
        if r["id"] != ignorar_id and r["nome"].casefold() == nome.casefold():
            raise TabelaClientesErro("Já existe uma coluna chamada \"%s\"." % r["nome"])
    return nome


def adicionar_coluna(nome, tipo=TIPO_TEXTO):
    conn = _conexao()
    try:
        nome = _validar_nome_coluna(conn, nome)
        ordem = conn.execute("SELECT COALESCE(MAX(ordem), -1) + 1 FROM clientes_colunas").fetchone()[0]
        cur = conn.execute("INSERT INTO clientes_colunas (nome, tipo, ordem) VALUES (?, ?, ?)", (nome, tipo, ordem))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def renomear_coluna(coluna_id, nome):
    conn = _conexao()
    try:
        nome = _validar_nome_coluna(conn, nome, ignorar_id=coluna_id)
        conn.execute("UPDATE clientes_colunas SET nome = ? WHERE id = ?", (nome, coluna_id))
        conn.commit()
    finally:
        conn.close()


def remover_coluna(coluna_id):
    conn = _conexao()
    try:
        tipo = conn.execute("SELECT tipo FROM clientes_colunas WHERE id = ?", (coluna_id,)).fetchone()
        if tipo is None:
            return
        if tipo["tipo"] == TIPO_CLIENTE:
            raise TabelaClientesErro("A coluna do nome do cliente não pode ser excluída "
                                     "(ela é usada para criar as notas). Você pode renomeá-la.")
        conn.execute("DELETE FROM clientes_colunas WHERE id = ?", (coluna_id,))   # celulas saem em cascata
        conn.commit()
    finally:
        conn.close()


def mover_coluna(coluna_id, delta):
    """delta = -1 (para a esquerda) ou +1 (para a direita). Devolve True se moveu."""
    conn = _conexao()
    try:
        ids = [r["id"] for r in conn.execute("SELECT id FROM clientes_colunas ORDER BY ordem, id")]
        if coluna_id not in ids:
            return False
        i = ids.index(coluna_id)
        j = i + delta
        if not 0 <= j < len(ids):
            return False
        ids[i], ids[j] = ids[j], ids[i]
        conn.executemany("UPDATE clientes_colunas SET ordem = ? WHERE id = ?", [(n, c) for n, c in enumerate(ids)])
        conn.commit()
        return True
    finally:
        conn.close()


def definir_tipo_coluna(coluna_id, tipo):
    """Troca o tipo. Marcar 'cliente' desmarca a coluna 'cliente' anterior (so existe uma)."""
    if tipo not in (TIPO_CLIENTE, TIPO_CNPJ, TIPO_TEXTO):
        raise TabelaClientesErro("Tipo de coluna inválido.")
    conn = _conexao()
    try:
        atual = conn.execute("SELECT tipo FROM clientes_colunas WHERE id = ?", (coluna_id,)).fetchone()
        if atual is None:
            return
        if atual["tipo"] == TIPO_CLIENTE and tipo != TIPO_CLIENTE:
            raise TabelaClientesErro("Escolha outra coluna como \"Cliente\" antes de mudar esta.")
        if tipo == TIPO_CLIENTE:
            conn.execute("UPDATE clientes_colunas SET tipo = ? WHERE tipo = ?", (TIPO_TEXTO, TIPO_CLIENTE))
        conn.execute("UPDATE clientes_colunas SET tipo = ? WHERE id = ?", (tipo, coluna_id))
        conn.commit()
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Linhas e celulas
# ----------------------------------------------------------------------
def listar_linhas():
    """[{'id': 3, 'valores': {coluna_id: 'texto'}}, ...] na ordem escolhida pelo usuario."""
    conn = _conexao()
    try:
        linhas = {r["id"]: {"id": r["id"], "valores": {}}
                  for r in conn.execute("SELECT id FROM clientes_linhas ORDER BY ordem, id")}
        ordem = list(linhas)
        for c in conn.execute("SELECT linha_id, coluna_id, valor FROM clientes_celulas"):
            if c["linha_id"] in linhas:
                linhas[c["linha_id"]]["valores"][c["coluna_id"]] = c["valor"]
        return [linhas[i] for i in ordem]
    finally:
        conn.close()


def adicionar_linha(valores=None, depois_de=None):
    """Cria uma linha (opcionalmente ja com valores {coluna_id: texto}) no fim da tabela ou logo
    depois da linha `depois_de`. Devolve o id."""
    conn = _conexao()
    try:
        ordem = conn.execute("SELECT COALESCE(MAX(ordem), -1) + 1 FROM clientes_linhas").fetchone()[0]
        linha_id = conn.execute("INSERT INTO clientes_linhas (ordem) VALUES (?)", (ordem,)).lastrowid
        for coluna_id, valor in (valores or {}).items():
            if (valor or "").strip():
                conn.execute("INSERT INTO clientes_celulas (linha_id, coluna_id, valor) VALUES (?, ?, ?)",
                             (linha_id, coluna_id, valor))
        if depois_de is not None:
            ids = [r["id"] for r in conn.execute("SELECT id FROM clientes_linhas ORDER BY ordem, id")]
            if depois_de in ids:
                ids.remove(linha_id)
                ids.insert(ids.index(depois_de) + 1, linha_id)
                conn.executemany("UPDATE clientes_linhas SET ordem = ? WHERE id = ?",
                                 [(n, i) for n, i in enumerate(ids)])
        conn.commit()
        return linha_id
    finally:
        conn.close()


def remover_linha(linha_id):
    conn = _conexao()
    try:
        conn.execute("DELETE FROM clientes_linhas WHERE id = ?", (linha_id,))
        conn.commit()
    finally:
        conn.close()



def salvar_celula(linha_id, coluna_id, valor):
    """Grava o texto da celula (normaliza o numero quando a coluna e do tipo CNPJ). Devolve o
    valor realmente gravado."""
    conn = _conexao()
    try:
        tipo = conn.execute("SELECT tipo FROM clientes_colunas WHERE id = ?", (coluna_id,)).fetchone()
        if tipo is None:
            raise TabelaClientesErro("Coluna inexistente.")
        valor = normalizar_cnpj(valor) if tipo["tipo"] == TIPO_CNPJ else (valor or "").strip()
        conn.execute("""INSERT INTO clientes_celulas (linha_id, coluna_id, valor) VALUES (?, ?, ?)
                        ON CONFLICT(linha_id, coluna_id) DO UPDATE SET valor = excluded.valor""",
                     (linha_id, coluna_id, valor))
        conn.commit()
        return valor
    finally:
        conn.close()


def reordenar_linhas(ids_ordenados):
    """Grava a nova ordem (lista COMPLETA de ids de linhas, na ordem desejada)."""
    conn = _conexao()
    try:
        conn.executemany("UPDATE clientes_linhas SET ordem = ? WHERE id = ?",
                         [(n, i) for n, i in enumerate(ids_ordenados)])
        conn.commit()
    finally:
        conn.close()


def chave_ordenacao(texto):
    """Ordem natural, sem diferenciar maiusculas/acentos e com numeros em ordem numerica."""
    import unicodedata
    base = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().casefold()
    return [(0, int(p), "") if p.isdigit() else (1, 0, p) for p in re.split(r"(\d+)", base) if p != ""]


# ----------------------------------------------------------------------
# Importacao de planilha .xlsx (so biblioteca padrao)
# ----------------------------------------------------------------------
_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
       "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
       "rel": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _indice_coluna(ref):
    letras = re.match(r"[A-Z]+", ref).group(0)
    n = 0
    for ch in letras:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def ler_xlsx(caminho):
    """Primeira planilha do arquivo como lista de linhas (lista de textos)."""
    try:
        z = zipfile.ZipFile(caminho)
    except (zipfile.BadZipFile, OSError) as e:
        raise TabelaClientesErro("Não foi possível abrir o arquivo (precisa ser .xlsx): %s" % e)
    with z:
        textos = []
        if "xl/sharedStrings.xml" in z.namelist():
            raiz = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in raiz.findall("m:si", _NS):
                textos.append("".join(t.text or "" for t in si.iter("{%s}t" % _NS["m"])))
        alvo = None
        try:
            wb = ET.fromstring(z.read("xl/workbook.xml"))
            rid = wb.find("m:sheets/m:sheet", _NS).get("{%s}id" % _NS["r"])
            rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
            for rel in rels.findall("rel:Relationship", _NS):
                if rel.get("Id") == rid:
                    alvo = rel.get("Target").lstrip("/")
                    alvo = alvo if alvo.startswith("xl/") else "xl/" + alvo
        except (KeyError, AttributeError, ET.ParseError):
            alvo = None
        if alvo is None or alvo not in z.namelist():
            planilhas = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))
            if not planilhas:
                raise TabelaClientesErro("O arquivo não tem nenhuma planilha.")
            alvo = planilhas[0]
        raiz = ET.fromstring(z.read(alvo))
    linhas = []
    for row in raiz.iter("{%s}row" % _NS["m"]):
        celulas = {}
        for c in row.findall("m:c", _NS):
            tipo = c.get("t")
            v = c.find("m:v", _NS)
            if tipo == "inlineStr":
                valor = "".join(t.text or "" for t in c.iter("{%s}t" % _NS["m"]))
            elif v is None or v.text is None:
                continue
            elif tipo == "s":
                valor = textos[int(v.text)]
            elif tipo in ("str", "e"):
                valor = v.text
            elif tipo == "b":
                valor = "Sim" if v.text == "1" else "Não"
            else:                       # numero: 1.1222333E+13 -> 11222333000000 (sem notacao cientifica)
                try:
                    d = Decimal(v.text)
                    valor = format(d.quantize(Decimal(1)), "f") if d == d.to_integral_value() else v.text
                except Exception:
                    valor = v.text
            celulas[_indice_coluna(c.get("r"))] = valor.strip()
        if celulas:
            linhas.append([celulas.get(i, "") for i in range(max(celulas) + 1)])
    return linhas


def importar_xlsx(caminho):
    """Acrescenta as linhas da planilha a tabela. A primeira linha com 2+ celulas preenchidas e o
    cabecalho; colunas com o mesmo nome (sem diferenciar maiusculas) recebem os dados, as demais
    sao criadas. Linhas cujo CNPJ (ou, sem CNPJ, nome de cliente) ja existe sao ignoradas, entao
    importar de novo nao duplica. Devolve (adicionadas, ignoradas)."""
    linhas = ler_xlsx(caminho)
    cab_i = next((i for i, l in enumerate(linhas) if sum(1 for x in l if x) >= 2), None)
    if cab_i is None:
        raise TabelaClientesErro("Não encontrei uma linha de cabeçalho na planilha.")
    cabecalho = linhas[cab_i]
    usadas = [i for i, nome in enumerate(cabecalho) if nome.strip()]
    colunas = {c["nome"].casefold(): c for c in listar_colunas()}
    mapa = {}                                           # indice na planilha -> coluna
    for i in usadas:
        nome = re.sub(r"\s+", " ", cabecalho[i]).strip()
        col = colunas.get(nome.casefold())
        if col is None:
            tipo = TIPO_CNPJ if "cnpj" in nome.casefold() else TIPO_TEXTO
            cid = adicionar_coluna(nome, tipo)
            col = {"id": cid, "nome": nome, "tipo": tipo}
            colunas[nome.casefold()] = col
        mapa[i] = col
    cols_cnpj = [c["id"] for c in colunas.values() if c["tipo"] == TIPO_CNPJ]
    col_cliente = next((c["id"] for c in colunas.values() if c["tipo"] == TIPO_CLIENTE), None)
    existentes_cnpj, existentes_nome = set(), set()
    for linha in listar_linhas():
        for cid in cols_cnpj:
            v = re.sub(r"\D", "", linha["valores"].get(cid, ""))
            if v:
                existentes_cnpj.add(v)
        if col_cliente:
            existentes_nome.add(linha["valores"].get(col_cliente, "").casefold())
    adicionadas = ignoradas = 0
    for dados in linhas[cab_i + 1:]:
        valores = {}
        for i, col in mapa.items():
            texto = dados[i] if i < len(dados) else ""
            texto = normalizar_cnpj(texto) if col["tipo"] == TIPO_CNPJ else texto.strip()
            if texto:
                valores[col["id"]] = texto
        if not valores:
            continue
        cnpjs = {re.sub(r"\D", "", valores[c]) for c in cols_cnpj if c in valores} - {""}
        nome = valores.get(col_cliente, "").casefold() if col_cliente else ""
        if (cnpjs and cnpjs & existentes_cnpj) or (not cnpjs and nome and nome in existentes_nome):
            ignoradas += 1
            continue
        adicionar_linha(valores)
        existentes_cnpj |= cnpjs
        if nome:
            existentes_nome.add(nome)
        adicionadas += 1
    return adicionadas, ignoradas


# ----------------------------------------------------------------------
# Substituir / remover a tabela inteira (+ "foto" para o Desfazer)
# ----------------------------------------------------------------------
def tirar_foto():
    """Copia completa da tabela (colunas e linhas, com os mesmos ids) para restaurar depois."""
    return {"colunas": listar_colunas(), "linhas": listar_linhas()}


def restaurar_foto(foto):
    conn = _conexao()
    try:
        _apagar_tudo(conn)
        for c in foto["colunas"]:
            conn.execute("INSERT INTO clientes_colunas (id, nome, tipo, ordem) VALUES (?, ?, ?, ?)",
                         (c["id"], c["nome"], c["tipo"], c["ordem"]))
        for ordem, linha in enumerate(foto["linhas"]):
            conn.execute("INSERT INTO clientes_linhas (id, ordem) VALUES (?, ?)", (linha["id"], ordem))
            for coluna_id, valor in linha["valores"].items():
                conn.execute("INSERT INTO clientes_celulas (linha_id, coluna_id, valor) VALUES (?, ?, ?)",
                             (linha["id"], coluna_id, valor))
        conn.commit()
    finally:
        conn.close()


def _apagar_tudo(conn):
    conn.execute("DELETE FROM clientes_celulas")
    conn.execute("DELETE FROM clientes_linhas")
    conn.execute("DELETE FROM clientes_colunas")


def limpar_tabela():
    """Remove todas as linhas e colunas. A tabela volta vazia, com as 4 colunas padrao."""
    conn = _conexao()
    try:
        _apagar_tudo(conn)
        conn.commit()
    finally:
        conn.close()
    _conexao().close()                  # recria as colunas padrao


def total_linhas():
    conn = _conexao()
    try:
        return conn.execute("SELECT COUNT(*) FROM clientes_linhas").fetchone()[0]
    finally:
        conn.close()


def _extrair_planilha(caminho):
    """A planilha como ela e: [(indice, nome)] das colunas que tem informacao e as linhas
    (dict indice -> texto) abaixo do cabecalho, na mesma ordem. So ficam de fora as linhas e
    colunas totalmente vazias e o que vem antes do cabecalho (titulos soltos)."""
    linhas = ler_xlsx(caminho)
    cab_i = next((i for i, l in enumerate(linhas) if sum(1 for x in l if x) >= 2), None)
    if cab_i is None:
        raise TabelaClientesErro("Não encontrei uma linha de cabeçalho na planilha.")
    cabecalho = linhas[cab_i]
    corpo = [l for l in linhas[cab_i + 1:] if any(x for x in l)]
    usadas = [i for i in range(max([len(cabecalho)] + [len(l) for l in corpo]))
              if (i < len(cabecalho) and cabecalho[i].strip()) or any(i < len(l) and l[i] for l in corpo)]
    colunas, vistos = [], set()
    for i in usadas:
        nome = re.sub(r"\s+", " ", cabecalho[i] if i < len(cabecalho) else "").strip() or "Coluna %d" % (i + 1)
        base, n = nome, 2
        while nome.casefold() in vistos:
            nome, n = "%s (%d)" % (base, n), n + 1
        vistos.add(nome.casefold())
        colunas.append((i, nome))
    return colunas, [{i: (l[i] if i < len(l) else "") for i, _ in colunas} for l in corpo]


def substituir_por_xlsx(caminho):
    """Troca a tabela inteira pela planilha, EXATAMENTE como ela esta: mesmas colunas (nos
    mesmos nomes e ordem) e mesmas linhas (na mesma ordem, inclusive repetidas). Tudo ou nada: se
    a leitura falhar, a tabela atual nao e tocada. Devolve (n_colunas, n_linhas)."""
    colunas, corpo = _extrair_planilha(caminho)
    nomes = [n for _, n in colunas]
    i_cliente = next((k for k, n in enumerate(nomes) if "cliente" in n.casefold()), None)
    if i_cliente is None:
        i_cliente = next((k for k, n in enumerate(nomes) if "cnpj" not in n.casefold()), 0)
    conn = _conexao()
    try:
        _apagar_tudo(conn)
        ids = {}
        for ordem, (i, nome) in enumerate(colunas):
            tipo = TIPO_CLIENTE if ordem == i_cliente else (TIPO_CNPJ if "cnpj" in nome.casefold() else TIPO_TEXTO)
            ids[i] = (conn.execute("INSERT INTO clientes_colunas (nome, tipo, ordem) VALUES (?, ?, ?)",
                                   (nome, tipo, ordem)).lastrowid, tipo)
        for ordem, dados in enumerate(corpo):
            linha_id = conn.execute("INSERT INTO clientes_linhas (ordem) VALUES (?)", (ordem,)).lastrowid
            for i, (coluna_id, tipo) in ids.items():
                texto = dados.get(i, "")
                texto = normalizar_cnpj(texto) if tipo == TIPO_CNPJ else texto.strip()
                if texto:
                    conn.execute("INSERT INTO clientes_celulas (linha_id, coluna_id, valor) VALUES (?, ?, ?)",
                                 (linha_id, coluna_id, texto))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return len(colunas), len(corpo)
