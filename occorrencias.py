# -*- coding: utf-8 -*-
"""
occorrencias.py
Constantes de negocio e logica de autocomplete de ocorrencias.
"""

OCORRENCIAS_PADRAO = [
    "REENTREGA", "MUDOU-SE", "LOCALIZAÇÃO", "ACOMPANHAR",
    "COMPROVANTE", "PRIORIZAR ENTREGA", "AGENDAMENTO", "DEVOLUÇÃO", "OUTROS",
]

# Ocorrencias tratadas como "agendamento"
OCORRENCIAS_AGENDAMENTO = {"agendamento", "agenda"}


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


def eh_ocorrencia_agendamento(ocorrencia):
    return (ocorrencia or "").strip().lower() in OCORRENCIAS_AGENDAMENTO
