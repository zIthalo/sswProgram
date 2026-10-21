# -*- coding: utf-8 -*-
"""
exportacoes.py
Exportacao de dados do sistema para arquivos CSV (abrem direto no Excel) e
exportacao completa ("salvaguarda") de todo o banco.

Os CSVs usam ponto e virgula como separador e codificacao UTF-8 com BOM
(utf-8-sig): e o formato que o Excel em portugues do Brasil abre
corretamente com um duplo clique, com acentos e colunas no lugar certo.
"""

import csv
import os
import shutil
from datetime import datetime

import backup
import database as db

SEPARADOR = ";"
ENCODING = "utf-8-sig"


def _escrever_csv(caminho, cabecalho, linhas):
    with open(caminho, "w", newline="", encoding=ENCODING) as f:
        escritor = csv.writer(f, delimiter=SEPARADOR)
        escritor.writerow(cabecalho)
        for linha in linhas:
            escritor.writerow(linha)


def _rotulo_morosidade(valor):
    return {"unidade": "Unidade", "cliente": "Cliente", "nenhum": "Sem morosidade"}.get(valor, valor)


def exportar_historico_csv(caminho):
    """Exporta o historico de notas resolvidas (o mesmo exibido na tela de
    Historico) para um arquivo CSV."""
    linhas = []
    for h in db.listar_historico():
        try:
            resolvido_em = datetime.fromisoformat(h["resolvido_em"]).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            resolvido_em = h["resolvido_em"]
        linhas.append([
            h["nf_numero"], h["cliente"], h["ocorrencia"], h["sigla"],
            h["dias"], h["horas"], _rotulo_morosidade(h["morosidade"]), resolvido_em,
        ])
    _escrever_csv(
        caminho,
        ["NF", "Cliente", "Ocorrência", "Sigla", "Dias", "Horas", "Morosidade", "Resolvido em"],
        linhas,
    )
    return len(linhas)


def exportar_relatorio_csv(caminho):
    """Exporta os dados do Relatorio (top 5 de cada lista, tempo medio e
    total de notas pendentes) para um arquivo CSV, em formato de secoes."""
    rel = db.gerar_relatorio()
    linhas = []

    linhas.append(["Notas pendentes", db.contar_notas_pendentes(), ""])
    linhas.append(["Tempo médio para solução", "%d dia(s) e %d hora(s)" % (
        rel["tempo_medio_dias"], rel["tempo_medio_horas"]), ""])
    linhas.append(["", "", ""])

    secoes = [
        ("Unidades/siglas com mais ocorrências", rel["siglas_mais_ocorrencias"]),
        ("Unidades mais morosas", rel["unidades_mais_morosas"]),
        ("Clientes mais morosos", rel["clientes_mais_morosos"]),
    ]
    for titulo, itens in secoes:
        linhas.append([titulo, "", ""])
        for posicao, (nome, total) in enumerate(itens, start=1):
            linhas.append(["%d" % posicao, nome, total])
        linhas.append(["", "", ""])

    _escrever_csv(caminho, ["Item", "Valor", "Quantidade"], linhas)
    return len(linhas)


def exportar_tudo(pasta_base):
    """
    Exportacao completa (salvaguarda): cria dentro de 'pasta_base' uma
    subpasta datada contendo
      - uma copia integral do banco de dados (.db) — a forma mais fiel de
        guardar tudo, que pode ser restaurada copiando o arquivo de volta;
      - notas.csv (todas as notas, ativas e resolvidas), tratativas.csv e
        historico.csv — para consulta/analise no Excel.

    Retorna o caminho da subpasta criada.
    """
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(pasta_base, "exportacao_sac_%s" % carimbo)
    os.makedirs(destino, exist_ok=True)

    # 1) Copia integral do banco (com checkpoint do WAL antes, para nao
    #    perder escritas recentes que ainda estejam fora do arquivo principal).
    backup._checkpoint_wal()
    shutil.copy2(db.get_db_path(), os.path.join(destino, db.DB_NAME))

    # 2) CSVs
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM notas ORDER BY criado_em ASC")
    notas = cur.fetchall()
    _escrever_csv(
        os.path.join(destino, "notas.csv"),
        ["ID", "NF", "Cliente", "Ocorrência", "Sigla", "Data", "Criado em",
         "Resolvida", "Agendamento", "Observação"],
        [[n["id"], n["nf_numero"], n["cliente"], n["ocorrencia"], n["sigla"],
          db_formatar_data(n["data_ocorrencia"]), n["criado_em"],
          "Sim" if n["resolvido"] else "Não",
          db_formatar_data(n["agendamento_data"]), n["observacao"] or ""] for n in notas],
    )

    cur.execute("""
        SELECT t.nota_id, n.nf_numero, n.cliente, t.timestamp, t.texto
        FROM tratativas t JOIN notas n ON n.id = t.nota_id
        ORDER BY t.nota_id ASC, t.id ASC
    """)
    _escrever_csv(
        os.path.join(destino, "tratativas.csv"),
        ["ID da nota", "NF", "Cliente", "Data/hora", "Texto"],
        [[r["nota_id"], r["nf_numero"], r["cliente"], r["timestamp"], r["texto"]]
         for r in cur.fetchall()],
    )
    conn.close()

    exportar_historico_csv(os.path.join(destino, "historico.csv"))
    return destino


def db_formatar_data(data_str):
    """ddmmyyyy -> dd/mm/aaaa (vazio se nao houver data)."""
    if not data_str:
        return ""
    import dateutils
    return dateutils.formatar_data_exibicao(data_str)
