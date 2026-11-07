# -*- coding: utf-8 -*-
"""
busca.py
Regras do campo de busca da janela principal (NF / cliente / sigla), sem
depender de tela, para poderem ser testadas isoladamente.

Problema que isto resolve: o campo unico procurava o texto digitado como
"contem" tanto no nome do cliente quanto na sigla. Uma sigla curta (ex.: "SP")
esta contida em varios nomes de cliente (ex.: "ASPEN", "SPEED"), entao o
resultado vinha misturado - e a sugestao de cliente ainda substituia o que o
usuario digitou pelo nome do cliente.

Como o texto e classificado (nesta ordem):
  1. so digitos                          -> numero de NF (tratado na tela)
  2. igual a uma SIGLA conhecida         -> busca por sigla: so notas dessa sigla
                                            (e, se existir, notas de um cliente
                                            cujo nome seja EXATAMENTE esse texto)
  3. qualquer outro texto                -> como sempre: contido no nome do
                                            cliente ou na sigla
"Sigla conhecida" = sigla usada em alguma nota (ativa ou do historico) ou
empresa parceira cadastrada. Comparacao sem diferenciar maiusculas/minusculas.
"""

MODO_SIGLA = "sigla"
MODO_TEXTO = "texto"


def _normalizar(texto):
    return (texto or "").strip().lower()


def classificar(texto, siglas_conhecidas):
    """Retorna MODO_SIGLA se o texto for exatamente uma sigla conhecida; senao MODO_TEXTO."""
    t = _normalizar(texto)
    if t and t in {_normalizar(s) for s in siglas_conhecidas}:
        return MODO_SIGLA
    return MODO_TEXTO


def nota_corresponde(nota, texto, siglas_conhecidas):
    """True se a nota entra no resultado da busca por `texto`."""
    t = _normalizar(texto)
    if not t:
        return True
    cliente = _normalizar(nota["cliente"])
    sigla = _normalizar(nota["sigla"])
    if classificar(t, siglas_conhecidas) == MODO_SIGLA:
        return sigla == t or cliente == t
    return t in cliente or t in sigla


def filtrar_notas(notas, texto, siglas_conhecidas):
    siglas = list(siglas_conhecidas)
    return [n for n in notas if nota_corresponde(n, texto, siglas)]
