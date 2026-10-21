# -*- coding: utf-8 -*-
"""
desfazer.py
Pilha de "Desfazer ultima alteracao" (Ctrl+Z na janela principal).

Cada acao reversivel registra uma descricao e uma funcao que a desfaz (que
guarda a "foto" dos dados de antes). A pilha guarda as ultimas MAXIMO acoes
da sessao; ao fechar o programa ela e descartada.
"""

MAXIMO = 30


class PilhaDesfazer:
    def __init__(self, maximo=MAXIMO):
        self._itens = []
        self._maximo = maximo

    def registrar(self, descricao, funcao_desfazer):
        self._itens.append((descricao, funcao_desfazer))
        if len(self._itens) > self._maximo:
            del self._itens[0]

    def vazia(self):
        return not self._itens

    def proxima_descricao(self):
        return self._itens[-1][0] if self._itens else None

    def desfazer(self):
        """Executa e retira a acao mais recente. Retorna a descricao.
        Se a funcao falhar, a excecao sobe ao chamador e a acao e
        descartada (nao fica presa tentando desfazer para sempre)."""
        if not self._itens:
            return None
        descricao, funcao = self._itens.pop()
        funcao()
        return descricao
