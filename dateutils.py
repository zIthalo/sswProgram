# -*- coding: utf-8 -*-
"""
dateutils.py
Logica de interpretacao de datas digitadas pelo usuario e de codigos de lembrete,
conforme especificado pelo usuario do sistema de SAC.
"""

from datetime import datetime, timedelta

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


# ---------------------------------------------------------------------------
# Codigos de lembrete
# ---------------------------------------------------------------------------
# Regras (conforme especificado):
#   1 a 50   -> minutos literais (1 a 50 minutos)
#   > 50     -> arredondado para o codigo valido mais proximo dentre:
#               100 (1h), 130 (1h30), 200 (2h), 230 (2h30),
#               300 (3h), 330 (3h30), 400 (4h)  <- maximo permitido
CODIGOS_HORA_VALIDOS = [100, 130, 200, 230, 300, 330, 400]


def normalizar_codigo_lembrete(numero):
    """
    Recebe o numero digitado pelo usuario (inteiro) e devolve o codigo final
    (ja normalizado) a ser salvo e exibido, junto com o timedelta correspondente.
    Retorna (codigo_final:int, delta:timedelta)
    """
    if numero is None:
        raise ValueError("Numero de lembrete nao informado.")
    numero = int(numero)

    if numero < 1:
        raise ValueError("O valor de lembrete deve ser maior que zero.")

    if numero <= 50:
        return numero, timedelta(minutes=numero)

    # numero > 50: arredonda para o codigo de hora valido mais proximo, limitado a 400
    mais_proximo = min(CODIGOS_HORA_VALIDOS, key=lambda c: abs(c - numero))
    horas = mais_proximo // 100
    minutos = mais_proximo % 100
    return mais_proximo, timedelta(hours=horas, minutes=minutos)


def formatar_codigo_lembrete(codigo):
    """Retorna uma string amigavel para exibicao, ex: '30 min' ou '1h30'."""
    if codigo is None:
        return ""
    if codigo <= 50:
        return "%d min" % codigo
    horas = codigo // 100
    minutos = codigo % 100
    if minutos == 0:
        return "%dh" % horas
    return "%dh%02d" % (horas, minutos)
