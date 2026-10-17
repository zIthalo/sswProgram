# -*- coding: utf-8 -*-
"""
aparencia.py
Preferencias de aparencia do usuario: cor da fonte, cor de fundo e cor de
selecao dos blocos de nota, e quais campos do cabecalho aparecem em negrito.

As preferencias ficam num arquivo proprio (config_aparencia.json, ao lado do
banco), separado do banco de dados: mexer na aparencia nunca toca nos dados
das notas, e apagar esse arquivo (ou usar "Restaurar padrao de fabrica")
devolve o sistema exatamente a aparencia original.

Desempenho: o arquivo e lido uma unica vez (ao iniciar) e mantido em memoria;
consultar uma preferencia durante a montagem de um bloco e apenas uma busca
em dicionario.

Cor vazia ("") significa "usar a cor padrao do sistema" — e o padrao de
fabrica: com isso o programa continua exatamente com a paleta original.
"""

import json
import os
import re

import database as db

NOME_ARQUIVO = "config_aparencia.json"

# Campos do cabecalho da nota que podem ser colocados em negrito.
CAMPOS_NEGRITO = [
    ("nf", "Número da NF"),
    ("cliente", "Remetente / cliente"),
    ("ocorrencia", "Ocorrência"),
    ("sigla", "Sigla da unidade"),
    ("data_hora", "Data e hora"),
    ("dias", "Dias em tratativas"),
    ("agendamento", "Data de agendamento"),
    ("observacao", "Observação / tag"),
]

COR_SELECAO_PADRAO = "#cfe8ff"

# Padrao de fabrica: identico ao visual original do sistema.
PADRAO = {
    "cor_fonte": "",      # "" = cor padrao do sistema
    "cor_fundo": "",      # "" = cor padrao do sistema
    "cor_selecao": COR_SELECAO_PADRAO,
    "negrito": {
        "nf": False, "cliente": True, "ocorrencia": True, "sigla": False,
        "data_hora": False, "dias": False, "agendamento": True, "observacao": False,
    },
}

_REGEX_COR = re.compile(r"^#[0-9a-fA-F]{6}$")

_config = None  # cache em memoria


def caminho_arquivo():
    return os.path.join(os.path.dirname(db.get_db_path()), NOME_ARQUIVO)


def _copiar_padrao():
    return {
        "cor_fonte": PADRAO["cor_fonte"],
        "cor_fundo": PADRAO["cor_fundo"],
        "cor_selecao": PADRAO["cor_selecao"],
        "negrito": dict(PADRAO["negrito"]),
    }


def _validar(bruto):
    """Mescla o que veio do arquivo sobre o padrao, descartando qualquer
    valor invalido (arquivo editado a mao, corrompido, de outra versao...)."""
    cfg = _copiar_padrao()
    if not isinstance(bruto, dict):
        return cfg
    for chave in ("cor_fonte", "cor_fundo", "cor_selecao"):
        valor = bruto.get(chave)
        if isinstance(valor, str) and (_REGEX_COR.match(valor) or (valor == "" and chave != "cor_selecao")):
            cfg[chave] = valor
    negrito = bruto.get("negrito")
    if isinstance(negrito, dict):
        for campo in cfg["negrito"]:
            if isinstance(negrito.get(campo), bool):
                cfg["negrito"][campo] = negrito[campo]
    return cfg


def carregar():
    """Le o arquivo de preferencias (se existir) e guarda em memoria."""
    global _config
    try:
        with open(caminho_arquivo(), "r", encoding="utf-8") as f:
            _config = _validar(json.load(f))
    except (OSError, ValueError):
        _config = _copiar_padrao()
    return _config


def obter():
    if _config is None:
        carregar()
    return _config


def salvar(nova_config):
    """Valida, guarda em memoria e grava no arquivo. Retorna True se gravou."""
    global _config
    _config = _validar(nova_config)
    try:
        with open(caminho_arquivo(), "w", encoding="utf-8") as f:
            json.dump(_config, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def restaurar_padrao():
    """Volta ao padrao de fabrica: apaga o arquivo de preferencias."""
    global _config
    _config = _copiar_padrao()
    try:
        os.remove(caminho_arquivo())
    except FileNotFoundError:
        pass
    except OSError:
        return False
    return True


def eh_negrito(campo):
    return bool(obter()["negrito"].get(campo, False))


def kwargs_texto():
    """Opcoes de cor (fonte/fundo) para widgets tk.Label/tk.Text; vazio
    quando o usuario nao personalizou (mantem o visual padrao do sistema)."""
    cfg = obter()
    opcoes = {}
    if cfg["cor_fonte"]:
        opcoes["foreground"] = cfg["cor_fonte"]
    if cfg["cor_fundo"]:
        opcoes["background"] = cfg["cor_fundo"]
    return opcoes


def estilo_frame():
    """Nome do estilo ttk para os frames dos blocos de nota."""
    return "Nota.TFrame" if obter()["cor_fundo"] else "TFrame"
