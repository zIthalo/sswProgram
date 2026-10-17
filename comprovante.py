# -*- coding: utf-8 -*-
"""
comprovante.py
Gera o comprovante de atendimento de uma nota (dados da nota + historico
completo de tratativas) como uma pagina HTML formatada para impressao.

O arquivo e aberto no navegador padrao do computador; de la o usuario
imprime (Ctrl+P) ou escolhe "Salvar como PDF" no destino da impressao —
recurso nativo do Windows/Chrome/Edge. Isso evita adicionar uma biblioteca
externa de PDF ao projeto (que complicaria o empacotamento com PyInstaller
e a compatibilidade com Windows 7), mantendo o sistema so com a biblioteca
padrao do Python.
"""

import html
import os
import webbrowser
from datetime import datetime

import database as db
import dateutils


def _linha(rotulo, valor):
    return "<tr><th>%s</th><td>%s</td></tr>" % (html.escape(rotulo), html.escape(str(valor)))


def montar_html(nota, tratativas):
    """Retorna o HTML completo do comprovante (string)."""
    try:
        criado = datetime.fromisoformat(nota["criado_em"])
        registrada_em = criado.strftime("%d/%m/%Y %H:%M")
        dias = (datetime.now() - criado).days
    except (ValueError, TypeError):
        registrada_em, dias = "", 0

    linhas = [
        _linha("Nota Fiscal", nota["nf_numero"]),
        _linha("Remetente", nota["cliente"]),
        _linha("Ocorrência", nota["ocorrencia"]),
        _linha("Sigla / Unidade", nota["sigla"]),
        _linha("Registrada em", registrada_em),
        _linha("Dias em tratativas", dias),
    ]
    if nota["agendamento_data"]:
        linhas.append(_linha("Agendamento", dateutils.formatar_data_exibicao(nota["agendamento_data"])))
    observacao = nota["observacao"] if "observacao" in nota.keys() else None
    if observacao:
        linhas.append(_linha("Observação", observacao))
    linhas.append(_linha("Situação", "Resolvida" if nota["resolvido"] else "Pendente"))

    if tratativas:
        itens = "".join(
            "<tr><td class='ts'>%s</td><td>%s</td></tr>" % (
                html.escape(t["timestamp"]), html.escape(t["texto"]))
            for t in tratativas)
        bloco_tratativas = "<table class='trat'>%s</table>" % itens
    else:
        bloco_tratativas = "<p class='vazio'>Nenhuma atualização registrada.</p>"

    return """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Comprovante - NF %(nf)s</title>
<style>
  body { font-family: Arial, Helvetica, sans-serif; margin: 32px; color: #111; }
  h1 { font-size: 20px; margin: 0 0 4px 0; }
  .sub { color: #555; font-size: 12px; margin-bottom: 20px; }
  h2 { font-size: 15px; border-bottom: 1px solid #999; padding-bottom: 4px; margin-top: 26px; }
  table { border-collapse: collapse; width: 100%%; }
  .dados th { text-align: left; width: 190px; padding: 5px 8px; background: #f2f2f2; border: 1px solid #ccc; }
  .dados td { padding: 5px 8px; border: 1px solid #ccc; }
  .trat td { padding: 5px 8px; border-bottom: 1px solid #ddd; vertical-align: top; }
  .trat .ts { white-space: nowrap; width: 130px; color: #333; font-weight: bold; }
  .vazio { color: #666; font-style: italic; }
  .dica { margin-top: 30px; font-size: 11px; color: #777; }
  @media print { .dica { display: none; } body { margin: 12mm; } }
</style>
</head>
<body>
<h1>Comprovante de atendimento - SAC</h1>
<div class="sub">Emitido em %(emitido)s</div>
<h2>Dados da nota</h2>
<table class="dados">%(linhas)s</table>
<h2>Histórico de tratativas</h2>
%(tratativas)s
<p class="dica">Para imprimir ou salvar em PDF: Ctrl+P e escolha a impressora ou "Salvar como PDF".</p>
</body>
</html>
""" % {
        "nf": html.escape(str(nota["nf_numero"])),
        "emitido": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "linhas": "".join(linhas),
        "tratativas": bloco_tratativas,
    }


def pasta_comprovantes():
    pasta = os.path.join(os.path.dirname(db.get_db_path()), "comprovantes")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def gerar_comprovante(nota_id, abrir_no_navegador=True):
    """Gera o arquivo HTML do comprovante da nota e (por padrao) o abre no
    navegador. Retorna o caminho do arquivo, ou None se a nota nao existir."""
    nota = db.obter_nota(nota_id)
    if nota is None:
        return None
    conteudo = montar_html(nota, db.listar_tratativas(nota_id))
    nome = "comprovante_NF%s_%s.html" % (nota["nf_numero"], datetime.now().strftime("%Y%m%d_%H%M%S"))
    caminho = os.path.join(pasta_comprovantes(), nome)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)
    if abrir_no_navegador:
        try:
            webbrowser.open("file:///" + caminho.replace("\\", "/"))
        except Exception:
            pass
    return caminho
