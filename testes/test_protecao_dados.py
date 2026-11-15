# -*- coding: utf-8 -*-
"""Protecao dos dados: o historico nunca e apagado automaticamente; apagar manualmente exige
confirmacao digitada. Usa so bancos temporarios (nunca o sac_logistica.db real)."""

import glob
import os
import tkinter as tk
import unittest
from datetime import datetime, timedelta
from unittest import mock

from testes.base import BaseTela, RAIZ
from nucleo import database as db


def _semear_historico():
    """Insere registros de idades variadas (1, 59, 61, 200 e 800 dias) direto no banco temporario."""
    conn = db.get_connection()
    for i, dias_atras in enumerate((1, 59, 61, 200, 800)):
        quando = (datetime.now() - timedelta(days=dias_atras)).isoformat()
        conn.execute(
            "INSERT INTO historico (nf_numero, cliente, ocorrencia, sigla, dias, horas, morosidade, resolvido_em) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (1000 + i, "CLIENTE %d" % (i % 2), "AVARIA", "SP" if i % 2 == 0 else "RJ", 2, 3,
             "unidade" if i % 2 == 0 else "cliente", quando))
    conn.commit()
    conn.close()


def _total():
    return len(db.listar_historico())


class TestExclusaoAutomaticaDesativada(BaseTela):
    def setUp(self):
        super().setUp()
        _semear_historico()

    def test_funcao_de_limpeza_automatica_nao_existe_mais(self):
        self.assertFalse(hasattr(db, "limpar_historico_expirado"))

    def test_nenhum_codigo_chama_a_limpeza_automatica(self):
        for pasta in ("nucleo", "interface"):
            for arq in glob.glob(os.path.join(RAIZ, pasta, "*.py")):
                with open(arq, encoding="utf-8") as f:
                    self.assertNotIn("limpar_historico_expirado", f.read(), arq)

    def test_registros_antigos_continuam_disponiveis(self):
        self.assertEqual(_total(), 5)
        self.assertEqual(len(db.buscar_historico_por_nf(1004)), 1)       # 800 dias
        self.assertEqual(len(db.buscar_historico_por_sigla("SP")), 3)    # 1, 61 e 800 dias
        self.assertEqual(len(db.buscar_historico_por_cliente("CLIENTE 1")), 2)

    def test_abrir_relatorio_e_historico_nao_exclui(self):
        self.app._abrir_relatorio()
        self.app._abrir_historico()
        self.app.update()
        self.assertEqual(_total(), 5)

    def test_relatorio_considera_registros_antigos(self):
        rel = db.gerar_relatorio()
        self.assertEqual(dict(rel["siglas_mais_ocorrencias"]), {"SP": 3, "RJ": 2})

    def test_abrir_o_programa_e_reiniciar_nao_exclui(self):
        from interface.app import App
        self.app.destroy()                    # "fecha" o programa
        for _ in range(2):                    # reabre duas vezes
            novo = App()
            novo.update()
            novo._abrir_historico()
            novo.update()
            novo.destroy()
            self.assertEqual(_total(), 5)
        self.app = App()                      # o tearDown da base fecha esta


class TestApagarHistoricoExigeConfirmacao(BaseTela):
    def setUp(self):
        super().setUp()
        _semear_historico()
        self.janela = tk.Toplevel(self.app)

    def test_sem_confirmacao_nada_e_apagado(self):
        for resposta in (None, "", "sim", "apagar tudo", "APAGA"):
            with mock.patch("interface.dialogs.simpledialog.askstring", lambda *a, **k: resposta):
                self.app._apagar_historico(self.janela)
            self.assertEqual(_total(), 5, "resposta %r apagou" % (resposta,))

    def test_digitando_apagar_exclui(self):
        with mock.patch("interface.dialogs.simpledialog.askstring", lambda *a, **k: " apagar "):
            self.app._apagar_historico(self.janela)
        self.assertEqual(_total(), 0)

    def test_aviso_diz_que_e_irreversivel_e_mostra_quantidade(self):
        capturado = []

        def falso(titulo, mensagem, **k):
            capturado.append(mensagem)
            return None
        with mock.patch("interface.dialogs.simpledialog.askstring", falso):
            self.app._apagar_historico(self.janela)
        self.assertIn("IRREVERSÍVEL", capturado[0])
        self.assertIn("5 registro(s)", capturado[0])
        self.assertIn("APAGAR", capturado[0])


if __name__ == "__main__":
    unittest.main()
