# -*- coding: utf-8 -*-
"""
dateutils.py
Logica de interpretacao de datas digitadas pelo usuario, conforme
especificado pelo usuario do sistema de SAC.
"""

from datetime import datetime

FORMATO = "%d%m%Y"  # ddmmyyyy, sem caracteres especiais


def parse_data_usuario(texto, referencia=None):
    """
    Interpreta a data digitada pelo usuario e retorna uma string ddmmyyyy.

    Regras:
    - "0"                       -> data atual do sistema
    - 1 ou 2 digitos (1 a 31)   -> dia informado, considerando mes/ano atuais (ou de 'referencia')
    - 8 digitos (ddmmyyyy)      -> data completa informada pelo usuario

    'referencia' permite calcular "mes/ano atuais" a partir de uma data diferente de hoje
    (usado, por exemplo, quando o usuario ja esta digitando dentro de um fluxo futuro).
    """
    texto = (texto or "").strip()
    if referencia is None:
        referencia = datetime.now()

    if texto == "0":
        return referencia.strftime(FORMATO)

    if texto.isdigit() and 1 <= len(texto) <= 2:
        dia = int(texto)
        if not (1 <= dia <= 31):
            raise ValueError("Dia invalido: %s" % texto)
        try:
            data = referencia.replace(day=dia)
        except ValueError:
            raise ValueError("Dia %d nao existe no mes/ano atual." % dia)
        return data.strftime(FORMATO)

    if texto.isdigit() and len(texto) == 8:
        try:
            data = datetime.strptime(texto, FORMATO)
        except ValueError:
            raise ValueError("Data invalida: %s" % texto)
        return data.strftime(FORMATO)

    raise ValueError("Formato de data nao reconhecido: %s" % texto)


def data_str_para_datetime(data_str):
    """Converte string ddmmyyyy em datetime (00:00)."""
    return datetime.strptime(data_str, FORMATO)


def calcular_dias_horas(criado_em_iso, referencia=None):
    """Calcula quantos dias e horas (cheios) se passaram entre criado_em_iso e agora."""
    if referencia is None:
        referencia = datetime.now()
    try:
        criado = datetime.fromisoformat(criado_em_iso)
    except (ValueError, TypeError):
        return 0, 0
    delta = referencia - criado
    dias = max(delta.days, 0)
    horas = delta.seconds // 3600
    return dias, horas


def formatar_data_exibicao(data_str):
    """Converte a data armazenada (ddmmyyyy) para exibição no formato dd/mm/aaaa."""
    try:
        return data_str_para_datetime(data_str).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return data_str or ""


def data_e_passado_ou_hoje(data_str, referencia=None):
    """Retorna True se a data informada for <= data de referencia (hoje, por padrao)."""
    if referencia is None:
        referencia = datetime.now()
    d = data_str_para_datetime(data_str)
    return d.date() <= referencia.date()
