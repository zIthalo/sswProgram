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


def filtrar_opcoes(texto_digitado, opcoes):
    """
    Busca dinamica usada nas telas de escolha com sugestoes: devolve as
    opcoes que contem o texto digitado (sem diferenciar maiusculas/minusculas),
    com as que COMECAM pelo texto primeiro e, depois, as que apenas o contem.
    Dentro de cada grupo mantem a ordem original das opcoes. Texto vazio
    devolve todas as opcoes.
    """
    opcoes = list(opcoes)
    texto = (texto_digitado or "").strip().lower()
    if not texto:
        return opcoes
    prefixo = [o for o in opcoes if o.lower().startswith(texto)]
    contem = [o for o in opcoes if texto in o.lower() and not o.lower().startswith(texto)]
    return prefixo + contem


def resolver_escolha(texto_digitado, opcoes, indice_destacado, permitir_novo=True):
    """
    Decide o valor final de uma tela de escolha com sugestoes. Retorna uma
    tupla (valor, eh_novo):
      - se ha uma sugestao destacada na lista -> essa sugestao, exatamente
        como esta cadastrada (eh_novo=False);
      - senao, se o texto digitado coincide com um cadastro (ignorando
        maiusculas/minusculas) -> o cadastro, com a grafia oficial;
      - senao, se permitir_novo e ha texto -> o proprio texto, em maiusculas
        (eh_novo=True; quem chamou decide se cadastra);
      - senao -> (None, False): nada valido para usar.
    Garante que o que o usuario SELECIONA sempre corresponde a um cadastro.
    """
    filtradas = filtrar_opcoes(texto_digitado, opcoes)
    if indice_destacado is not None and 0 <= indice_destacado < len(filtradas):
        return filtradas[indice_destacado], False
    texto = (texto_digitado or "").strip()
    for o in opcoes:
        if o.lower() == texto.lower() and texto:
            return o, False
    if permitir_novo and texto:
        return texto.upper(), True
    return None, False
