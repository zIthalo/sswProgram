# -*- coding: utf-8 -*-
"""
Base dos testes: cada teste usa um banco TEMPORARIO (nunca o seu sac_logistica.db)
e uma janela principal de verdade (Tkinter real). Caixas de dialogo sao
substituidas por respostas programadas, para o teste nao ficar esperando um clique.
"""

import os
import sys
import shutil
import tempfile
import traceback
import unittest
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import tkinter as tk
from tkinter import messagebox, simpledialog

from nucleo import database as db


class BaseTela(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix="sac_teste_")
        self._patch_db = mock.patch.object(db, "get_db_path",
                                           lambda: os.path.join(self.pasta, "teste.db"))
        self._patch_db.start()
        from interface.app import App
        try:
            self.app = App()
        except tk.TclError as erro:
            self._patch_db.stop()
            self.skipTest("sem ambiente grafico (%s) - use testes/executar.sh" % erro)
        self.erros_tk = []
        self.app.report_callback_exception = lambda *a: self.erros_tk.append(
            "".join(traceback.format_exception(*a)))
        self.erros = []   # mensagens exibidas ao usuario via messagebox.showerror
        self.perguntas = []
        self._mocks = [
            mock.patch.object(messagebox, "showerror", lambda t, m, **k: self.erros.append(m)),
            mock.patch.object(messagebox, "showwarning", lambda t, m, **k: self.erros.append(m)),
            mock.patch.object(messagebox, "showinfo", lambda *a, **k: None),
            mock.patch.object(messagebox, "askyesno", lambda *a, **k: True),
        ]
        for m in self._mocks:
            m.start()
        self.respostas_data = []
        self._mock_data = mock.patch.object(
            simpledialog, "askstring", lambda *a, **k: self.respostas_data.pop(0))
        self._mock_data.start()

    def tearDown(self):
        for m in self._mocks + [self._mock_data]:
            m.stop()
        try:
            self.app.destroy()
        except tk.TclError:
            pass
        self._patch_db.stop()
        shutil.rmtree(self.pasta, ignore_errors=True)
        self.assertEqual(self.erros_tk, [], "Erro dentro de callback Tkinter:\n" + "\n".join(self.erros_tk))

    # ---- atalhos
    def cadastrar(self, nf, cliente, ocorrencia, sigla="SP", data_agendamento=None):
        self.app.var_nf.set(str(nf))
        self.app.var_cliente.set(cliente)
        self.app.var_ocorrencia.set(ocorrencia)
        self.app.var_sigla.set(sigla)
        if data_agendamento:
            self.respostas_data.append(data_agendamento)
        self.app._adicionar_nota()
        self.app.update()

    def nota_por_nf(self, nf, cliente=None):
        for n in db.listar_notas_ativas():
            if n["nf_numero"] == nf and (cliente is None or n["cliente"] == cliente):
                return n
        return None

    def escolher_na_busca(self, texto, descer=False):
        """Agenda a interacao com o EscolherComBusca que a acao vai abrir."""
        def agir():
            topo = [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)][-1]
            topo.var_texto.set(texto)
            topo.update()
            if descer:
                topo._mover(1)
            topo._confirmar()
        self.app.after(200, agir)
