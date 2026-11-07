# -*- coding: utf-8 -*-
"""Icone do programa."""

import os
import unittest

from testes.base import BaseTela
from interface import icone


class TestIcone(BaseTela):
    def test_arquivo_existe_e_e_ico_valido(self):
        caminho = icone.caminho_icone()
        self.assertTrue(os.path.isfile(caminho))
        with open(caminho, "rb") as f:
            self.assertEqual(f.read(4), b"\x00\x00\x01\x00")  # cabecalho ICO

    def test_aplicar_nao_quebra(self):
        self.assertIn(icone.aplicar_icone(self.app), (True, False))


if __name__ == "__main__":
    unittest.main()
