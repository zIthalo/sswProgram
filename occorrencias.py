# -*- coding: utf-8 -*-
"""
occorrencias.py
Constantes de negocio e logica de autocomplete de ocorrencias.
"""

OCORRENCIAS_PADRAO = [
    "Reentrega", "Mudou-se", "Localização", "Acompanhar",
    "Comprovante", "Priorizar entrega", "Agendamento", "Devolução", "Outros",
]

# Ocorrencias que disparam a sugestao de lembrete periodico logo apos a insercao da nota
OCORRENCIAS_COM_LEMBRETE_SUGERIDO = {
    "reentrega", "mudou-se", "localização", "localizacao", "acompanhar", "priorizar entrega",
}

# Ocorrencias tratadas como "agendamento"
OCORRENCIAS_AGENDAMENTO = {"agendamento", "agenda"}

# Ocorrencias tratadas como "prioridade" (lembrete fixo as 10h e 17h)
OCORRENCIAS_PRIORIDADE = {"priorizar entrega", "prioridade"}

# Siglas de unidades filiais da propria transportadora
UNIDADES_FILIAIS = {"BLU", "TUB", "FLN", "CRI", "CWB", "SAO", "JVL"}


def sugerir_ocorrencia(texto_digitado, tipos_disponiveis):
    """
    Dado o texto que o usuario esta digitando e a lista de tipos disponiveis
    (padrao + customizados), retorna a melhor sugestao (ou None).
    Prioriza correspondencia por prefixo; em seguida, por substring.
    """
    texto = (texto_digitado or "").strip().lower()
    if not texto:
        return None

    prefixo = [t for t in tipos_disponiveis if t.lower().startswith(texto)]
    if prefixo:
        # prioriza o mais curto (correspondencia mais provavel)
        return min(prefixo, key=len)

    substring = [t for t in tipos_disponiveis if texto in t.lower()]
    if substring:
        return min(substring, key=len)

    return None


def eh_ocorrencia_com_lembrete_sugerido(ocorrencia):
    return (ocorrencia or "").strip().lower() in OCORRENCIAS_COM_LEMBRETE_SUGERIDO


def eh_ocorrencia_agendamento(ocorrencia):
    return (ocorrencia or "").strip().lower() in OCORRENCIAS_AGENDAMENTO


def eh_ocorrencia_prioridade(ocorrencia):
    return (ocorrencia or "").strip().lower() in OCORRENCIAS_PRIORIDADE


def eh_unidade_filial(sigla):
    return (sigla or "").strip().upper() in UNIDADES_FILIAIS
