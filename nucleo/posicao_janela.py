# -*- coding: utf-8 -*-
"""
posicao_janela.py
Guarda onde (e com que tamanho) a janela principal estava ao ser fechada,
para o sistema abrir no mesmo lugar da proxima vez.

O arquivo "janela_principal.json" fica ao lado do banco de dados (nunca vai
para o repositorio). Se o arquivo nao existe, esta corrompido ou a posicao
gravada ficou fora das telas atuais (monitor desligado, resolucao menor), o
sistema abre no tamanho padrao, sem erro.
"""

import json
import os
import re

from nucleo import database as db

NOME_ARQUIVO = "janela_principal.json"
MARGEM_VISIVEL = 100  # pixels da janela que precisam estar dentro da tela para a posicao valer

_PADRAO_GEOMETRIA = re.compile(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$")


def caminho_arquivo():
    return os.path.join(os.path.dirname(db.get_db_path()), NOME_ARQUIVO)


def interpretar_geometria(texto):
    """'920x680+10+20' -> (920, 680, 10, 20); None se o texto nao tiver esse formato."""
    m = _PADRAO_GEOMETRIA.match((texto or "").strip())
    return tuple(int(g) for g in m.groups()) if m else None


def formatar_geometria(largura, altura, x, y):
    # "+-5" e o jeito do Tk de dizer posicao negativa (monitor a esquerda/acima).
    return "%dx%d+%d+%d" % (largura, altura, x, y)


def carregar():
    """Retorna {"largura","altura","x","y","maximizada"} ou None."""
    try:
        with open(caminho_arquivo(), encoding="utf-8") as arq:
            dados = json.load(arq)
        estado = {k: int(dados[k]) for k in ("largura", "altura", "x", "y")}
        estado["maximizada"] = bool(dados.get("maximizada", False))
        return estado
    except (OSError, ValueError, KeyError, TypeError):
        return None


def salvar(largura, altura, x, y, maximizada):
    """Grava o estado. Retorna True/False; nunca levanta excecao (fechar o
    sistema nao pode falhar por causa disso)."""
    try:
        with open(caminho_arquivo(), "w", encoding="utf-8") as arq:
            json.dump({"largura": int(largura), "altura": int(altura), "x": int(x), "y": int(y),
                       "maximizada": bool(maximizada)}, arq)
        return True
    except (OSError, ValueError, TypeError):
        return False


def ajustar_a_tela(estado, tela_x, tela_y, tela_larg, tela_alt, min_larg=480, min_alt=400):
    """Valida o estado salvo contra a area de tela atual (area virtual, que
    inclui todos os monitores). Retorna (largura, altura, x, y) ou None se a
    posicao nao for mais utilizavel (entao o sistema abre no padrao).
    O tamanho e limitado ao da tela; a posicao so vale se um pedaco da barra
    de titulo da janela continuar visivel (para o usuario conseguir arrastar)."""
    if not estado:
        return None
    larg = max(min_larg, min(estado["largura"], tela_larg))
    alt = max(min_alt, min(estado["altura"], tela_alt))
    x, y = estado["x"], estado["y"]
    horizontal_ok = x + larg >= tela_x + MARGEM_VISIVEL and x <= tela_x + tela_larg - MARGEM_VISIVEL
    vertical_ok = tela_y <= y <= tela_y + tela_alt - 50
    if not (horizontal_ok and vertical_ok):
        return None
    return larg, alt, x, y
