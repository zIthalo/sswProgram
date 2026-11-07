# -*- coding: utf-8 -*-
"""Campo de busca unico (NF / cliente / sigla): a sigla nao pode ser engolida por nomes de cliente."""

import unittest

from nucleo import busca
from nucleo import database as db
from testes.base import BaseTela

SIGLAS = ["SP", "RJ", "AGEX", "BH"]


class TestRegrasDeBusca(unittest.TestCase):
    NOTAS = [
        {"cliente": "ASPEN LTDA", "sigla": "RJ"},     # nome contem "sp"
        {"cliente": "SPEED LOG", "sigla": "BH"},      # nome comeca com "sp"
        {"cliente": "ACME", "sigla": "SP"},
        {"cliente": "BETA", "sigla": "sp"},
        {"cliente": "SP", "sigla": "AGEX"},           # cliente chamado exatamente como a sigla
    ]

    def _clientes(self, texto):
        return [n["cliente"] for n in busca.filtrar_notas(self.NOTAS, texto, SIGLAS)]

    def test_sigla_exata_ignora_clientes_que_apenas_contem_as_letras(self):
        self.assertEqual(self._clientes("SP"), ["ACME", "BETA", "SP"])
        self.assertEqual(self._clientes("sp"), ["ACME", "BETA", "SP"])   # sem diferenciar maiusculas
        self.assertEqual(self._clientes(" Sp "), ["ACME", "BETA", "SP"])  # espacos nas pontas

    def test_classificacao(self):
        self.assertEqual(busca.classificar("rj", SIGLAS), busca.MODO_SIGLA)
        self.assertEqual(busca.classificar("spe", SIGLAS), busca.MODO_TEXTO)
        self.assertEqual(busca.classificar("", SIGLAS), busca.MODO_TEXTO)

    def test_texto_que_nao_e_sigla_continua_buscando_cliente_e_sigla_parcial(self):
        self.assertEqual(self._clientes("spe"), ["ASPEN LTDA", "SPEED LOG"])   # "contem", como sempre
        self.assertEqual(self._clientes("asp"), ["ASPEN LTDA"])
        self.assertEqual(self._clientes("ag"), ["SP"])                  # sigla AGEX contem "ag"
        self.assertEqual(self._clientes("acme"), ["ACME"])

    def test_texto_vazio_nao_filtra(self):
        self.assertEqual(len(self._clientes("")), len(self.NOTAS))


class TestBuscaNaTela(BaseTela):
    def setUp(self):
        super().setUp()
        for cliente in ("ASPEN LTDA", "SPEED LOG", "ACME"):
            db.adicionar_cliente(cliente)
        self.cadastrar(1, "ASPEN LTDA", "REENTREGA", "RJ")
        self.cadastrar(2, "SPEED LOG", "REENTREGA", "BH")
        self.cadastrar(3, "ACME", "REENTREGA", "SP")
        self.cadastrar(4, "ACME", "REENTREGA", "SP")
        self.cadastrar(5, "ACME", "REENTREGA", "RJ")

    def _buscar(self, texto):
        """Simula o usuario: digita, o campo sugere (KeyRelease) e aperta Enter."""
        self.app.var_busca.set(texto)
        self.app._sugerir_busca()
        self.app._executar_busca()
        self.app.update()
        return sorted(b.nota_row["nf_numero"] for b in self.app.blocos.values())

    def test_busca_por_sigla_retorna_so_a_sigla(self):
        self.assertEqual(self._buscar("SP"), [3, 4])
        self.assertEqual(self.app.var_busca.get(), "SP")        # a sigla NAO foi trocada por cliente
        self.assertEqual(self.app._suggestion_busca_var.get(), "")

    def test_outras_siglas_e_caixa(self):
        self.assertEqual(self._buscar("rj"), [1, 5])
        self.assertEqual(self._buscar("bh"), [2])

    def test_busca_por_cliente_continua_igual(self):
        self.assertEqual(self._buscar("acme"), [3, 4, 5])
        self.assertEqual(self._buscar("spee"), [2])             # sugestao de cliente ainda funciona
        self.assertEqual(self.app.var_busca.get().upper(), "SPEED LOG")

    def test_busca_por_numero_continua_igual(self):
        self._buscar("")
        self.app.var_busca.set("3")
        self.app._executar_busca()
        self.app.update()
        self.assertEqual(len(self.app.blocos), 5)               # NF unica: so destaca, nao filtra

    def test_sigla_conhecida_sem_notas_ativas_limpa_o_campo(self):
        db.adicionar_empresa_parceira("RISSO")
        notas = self._buscar("RISSO")
        self.assertEqual(self.app.var_busca.get(), "")           # regra: busca sem resultado limpa o campo
        self.assertEqual(notas, [1, 2, 3, 4, 5])                 # e a lista volta completa

    def test_garantir_visibilidade_respeita_busca_por_sigla(self):
        self._buscar("SP")
        self.cadastrar(6, "BETA", "REENTREGA", "RJ")             # nota fora do filtro "SP"
        self.assertEqual(self.app.filtro_busca_texto, "")        # filtro limpo para a nota nao sumir
        self.assertIn(self.nota_por_nf(6)["id"], self.app.blocos)


if __name__ == "__main__":
    unittest.main()
