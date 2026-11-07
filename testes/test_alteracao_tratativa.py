# -*- coding: utf-8 -*-
"""Alteracoes de campos da nota ficam registradas nas tratativas; data de agendamento abre com foco."""

import unittest
from unittest import mock

from testes.base import BaseTela
from nucleo import database as db


class TestAlteracaoNasTratativas(BaseTela):
    def setUp(self):
        super().setUp()
        db.adicionar_cliente("ACME")
        db.adicionar_cliente("BETA LTDA")
        self.cadastrar(200, "ACME", "REENTREGA")
        self.nota_id = self.nota_por_nf(200)["id"]

    def textos(self):
        return [t["texto"] for t in db.listar_tratativas(self.nota_id)]

    def test_remetente(self):
        self.escolher_na_busca("bet")
        self.app.editar_campo(self.nota_id, "cliente", "Remetente")
        self.assertEqual(self.textos(), ["REMETENTE ALTERADO DE ACME PARA BETA LTDA"])

    def test_numero_da_nf_e_sigla(self):
        with mock.patch("interface.edicao_notas.editar_campo_texto", lambda *a, **k: "201"):
            self.app.editar_campo(self.nota_id, "nf_numero", "Número da NF")
        with mock.patch("interface.edicao_notas.editar_campo_texto", lambda *a, **k: "rj"):
            self.app.editar_campo(self.nota_id, "sigla", "Sigla/Empresa")
        self.assertEqual(self.textos(), ["NÚMERO DA NF ALTERADO DE 200 PARA 201",
                                         "SIGLA ALTERADA DE SP PARA RJ"])

    def test_ocorrencia_e_aparece_no_cartao(self):
        self.escolher_na_busca("prio")
        self.app.editar_ocorrencia(self.nota_id)
        self.assertEqual(self.textos(), ["OCORRÊNCIA ALTERADA DE REENTREGA PARA PRIORIZAR ENTREGA"])
        bloco = self.app.blocos[self.nota_id]
        self.assertEqual(len(bloco._tratativas), 1)
        self.assertIn("OCORRÊNCIA ALTERADA", bloco.txt_cabecalho.get("1.0", "end"))

    def test_observacao(self):
        with mock.patch("interface.edicao_notas.pedir_texto_atualizacao", lambda *a, **k: "protocolo 9"):
            self.app.editar_observacao(self.nota_id)
        self.assertEqual(self.textos(), ["OBSERVAÇÃO/TAG ALTERADA DE (VAZIO) PARA PROTOCOLO 9"])

    def test_desfazer_remove_a_tratativa(self):
        self.escolher_na_busca("prio")
        self.app.editar_ocorrencia(self.nota_id)
        self.app.desfazer_ultima_alteracao()
        self.assertEqual(self.textos(), [])
        self.assertEqual(db.obter_nota(self.nota_id)["ocorrencia"], "REENTREGA")

    def test_sem_mudanca_nao_registra(self):
        with mock.patch("interface.edicao_notas.editar_campo_texto", lambda *a, **k: "SP"):
            self.app.editar_campo(self.nota_id, "sigla", "Sigla/Empresa")
        self.assertEqual(self.textos(), [])


class TestDataAgendamentoComFoco(BaseTela):
    def test_dialogo_da_data_usa_campo_com_foco(self):
        from interface import edicao_notas
        chamadas = []
        with mock.patch.object(edicao_notas, "pedir_texto_atualizacao",
                               lambda *a, **k: chamadas.append(a) or "25122030"):
            self.assertEqual(self.app._pedir_data_agendamento(), "25122030")
        self.assertEqual(chamadas[0][1], "Data do agendamento")

    def test_campo_recebe_foco_ao_abrir(self):
        from interface.dialogs import CampoTextoComAtalhos
        self._mock_data2.stop()   # aqui queremos o dialogo real
        self.addCleanup(self._mock_data2.start)
        foco = []
        original = CampoTextoComAtalhos._focar_campo
        def espiao(self_):
            original(self_)
            foco.append(self_.focus_get() is self_.texto)
            self_.after(0, self_._cancelar)
        with mock.patch.object(CampoTextoComAtalhos, "_focar_campo", espiao):
            self.app._pedir_data_agendamento()
        self.assertEqual(foco, [True])


if __name__ == "__main__":
    unittest.main()
