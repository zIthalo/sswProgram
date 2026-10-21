# -*- coding: utf-8 -*-
"""
tratativas_rapidas.py
Atalhos de uma letra para as atualizacoes (tratativas) mais comuns.

Na tela "Nova atualizacao", se o usuario digitar APENAS uma das letras abaixo
(maiuscula ou minuscula, sem espacos), o sistema grava a frase correspondente.
Qualquer outro texto (inclusive "ex", "e " com mais palavras, etc.) e gravado
exatamente como foi digitado.
"""

ATALHOS = {
    "e": "tratando via e-mail",
    "w": "tratando via WhatsApp",
    "s": "informacoes em sistema",
    "r": "MERCADORIA EM ROTA DE ENTREGA HOJE",
}


def expandir_atalho(texto):
    """Retorna a frase do atalho se `texto` for exatamente uma das letras
    (ignorando espacos nas pontas e maiusculas/minusculas); senao devolve o
    texto original sem alteracao."""
    if texto is None:
        return texto
    chave = texto.strip().lower()
    return ATALHOS.get(chave, texto)
