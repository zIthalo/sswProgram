# -*- coding: utf-8 -*-
"""Layout responsivo (painel lateral / gaveta / filtros em duas linhas) e cartoes de nota."""

import unittest
from unittest import mock

from testes.base import BaseTela
from interface import layout


class TestLayoutResponsivo(BaseTela):
    def redimensionar(self, largura, altura=700):
        self.app.geometry("%dx%d" % (largura, altura))
        for _ in range(5):
            self.app.update()

    def test_amplo_mostra_painel_lateral(self):
        self.redimensionar(1200)
        self.assertFalse(self.app._modo_compacto)
        self.assertTrue(self.app._painel_visivel)
        self.assertTrue(self.app._lateral.winfo_ismapped())
        self.assertEqual(self.app._lateral.winfo_width(), layout.LARGURA_LATERAL)

    def test_textos_do_painel_sao_brancos_e_em_negrito(self):
        from tkinter import ttk
        estilo = ttk.Style(self.app)
        self.assertEqual(estilo.lookup("Lateral.TLabel", "foreground").lower(), "#f8fafc")
        self.assertIn("bold", str(estilo.lookup("Lateral.TLabel", "font")))
        for w in [x for x in self.app._form_cab + self.app._form_rod if x.winfo_class() == "Label"][1:]:
            self.assertEqual(str(w.cget("foreground")).lower(), "#f8fafc")
            self.assertIn("bold", str(w.cget("font")))

    def test_compacto_esconde_painel_e_volta(self):
        self.redimensionar(600)
        self.assertTrue(self.app._modo_compacto)
        self.assertFalse(self.app._lateral.winfo_ismapped())
        self.assertEqual(self.app.btn_painel.cget("text"), "+ Nova nota")
        self.redimensionar(1200)
        self.assertFalse(self.app._modo_compacto)
        self.assertTrue(self.app._lateral.winfo_ismapped())

    def test_preferencia_do_painel_recolhido_e_mantida(self):
        self.redimensionar(1200)
        self.app.btn_painel.invoke()                      # usuario recolhe o painel
        self.app.update()
        self.assertFalse(self.app._lateral.winfo_ismapped())
        self.redimensionar(600)
        self.redimensionar(1200)
        self.assertFalse(self.app._lateral.winfo_ismapped())   # continua recolhido

    def test_gaveta_ctrl_n_registra_e_fecha(self):
        self.redimensionar(600)
        self.app.atalho_nova_nota()
        self.app.update()
        self.assertTrue(self.app._lateral.winfo_ismapped())
        self.assertEqual(self.app.btn_painel.cget("text"), "× Fechar")
        self.cadastrar(7001, "CLIENTE GAVETA", "REENTREGA", "SP")
        self.assertFalse(self.app._lateral.winfo_ismapped())   # fechou sozinha ao registrar
        self.assertIsNotNone(self.nota_por_nf(7001))
        self.assertEqual(len(self.app.blocos), 1)

    def test_gaveta_fecha_com_esc_e_nao_perde_o_que_foi_digitado(self):
        self.redimensionar(600)
        self.app.atalho_nova_nota()
        self.app.var_nf.set("123")
        self.app._fechar_gaveta()
        self.app.update()
        self.assertFalse(self.app._lateral.winfo_ismapped())
        self.assertEqual(self.app.var_nf.get(), "123")

    def test_focar_campo_do_formulario_abre_a_gaveta(self):
        self.redimensionar(600)
        self.app._focar(self.app.entry_cliente)
        self.app.update()
        self.assertTrue(self.app._lateral.winfo_ismapped())

    def test_filtros_quebram_em_area_estreita(self):
        self.redimensionar(1200)
        self.assertFalse(self.app._estreito)
        self.assertEqual(int(self.app.btn_atualizar.grid_info()["row"]), 0)
        self.redimensionar(600)
        self.assertTrue(self.app._estreito)
        self.assertEqual(int(self.app.btn_atualizar.grid_info()["row"]), 2)
        self.redimensionar(1200)
        self.assertEqual(int(self.app.btn_atualizar.grid_info()["row"]), 0)
        self.assertEqual(self.app.btn_copiar_filtradas.cget("text"), "Copiar notas filtradas")

    def test_resumo_acompanha_a_lista(self):
        self.cadastrar(7101, "A", "REENTREGA")
        self.cadastrar(7102, "B", "AGENDAMENTO", data_agendamento="30122099")
        self.assertEqual(self.app._kpis["lista"].cget("text"), "2")
        self.assertEqual(self.app._kpis["agendadas"].cget("text"), "1")
        resultado = {"nf_numero": 7101, "cliente": "A", "ocorrencia": "REENTREGA", "sigla": "SP",
                     "dias": 1, "horas": 1, "morosidade": "cliente"}
        with mock.patch("interface.edicao_notas.fluxo_marcar_resolvido", lambda *a, **k: resultado):
            self.app.marcar_como_resolvido(self.nota_por_nf(7101)["id"])
        self.app.update()
        self.assertEqual(self.app._kpis["lista"].cget("text"), "1")


class TestCartao(BaseTela):
    def test_clique_no_cabecalho_copia_nf_e_nas_tratativas_so_seleciona(self):
        self.cadastrar(7201, "CLIENTE CARTAO", "REENTREGA")
        nota = self.nota_por_nf(7201)
        from nucleo import database as db
        db.adicionar_tratativa(nota["id"], "TESTE")
        self.app.recarregar_lista()
        self.app.update()
        bloco = self.app.blocos[nota["id"]]
        txt = bloco.txt_cabecalho
        # cabecalho (linha 1): copia
        def clicar(x, y, ate_x=None):
            txt.event_generate("<ButtonPress-1>", x=x, y=y)
            if ate_x is not None:
                txt.event_generate("<B1-Motion>", x=ate_x, y=y)
            txt.event_generate("<ButtonRelease-1>", x=ate_x if ate_x is not None else x, y=y)
            self.app.update()
        clicar(20, 15)
        self.assertEqual(self.app.clipboard_get(), "7201")
        self.app.clipboard_clear()
        self.app.clipboard_append("outra coisa")
        clicar(60, 15, ate_x=160)               # arrastou: seleciona texto, nao copia a NF
        self.assertEqual(self.app.clipboard_get(), "outra coisa")
        self.assertTrue(txt.tag_ranges("sel"))
        self.app.clipboard_clear()
        self.app.clipboard_append("outra coisa")
        # linha da tratativa (ultima linha): nao copia
        y_ultima = txt.bbox("end-1c linestart")[1] + 4
        clicar(20, y_ultima)
        self.assertEqual(self.app.clipboard_get(), "outra coisa")
        self.assertEqual(self.app.nota_selecionada_id, nota["id"])

    def test_formato_de_copia_uma_nota(self):
        from interface.nota_block import formatar_notas_para_copia
        self.cadastrar(7401, "CLIENTE COPIA", "REENTREGA", "SP")
        nota = self.nota_por_nf(7401)
        self.assertEqual(formatar_notas_para_copia([nota]), "\n".join([
            "*NF: 7401;*", "Cliente: *CLIENTE COPIA*;", "Ocorrência: REENTREGA;",
            "Unidade: *SP*;", "Dias em tratativas: 0;"]))
        self.app.copiar_informacoes_nota(nota["id"])
        self.assertEqual(self.app.clipboard_get(), formatar_notas_para_copia([nota]))

    def test_copiar_notas_filtradas_com_separador(self):
        self.cadastrar(7501, "A", "REENTREGA", "SP")
        self.cadastrar(7502, "B", "LOCALIZAÇÃO", "RJ")
        self.app.copiar_notas_filtradas()
        copiado = self.app.clipboard_get()
        sep = "-" * 30
        self.assertEqual(copiado.count(sep), 2)                 # um apos cada nota (inclusive a ultima)
        self.assertIn("*NF: 7501;*\nCliente: *A*;\nOcorrência: REENTREGA;\nUnidade: *SP*;\n"
                      "Dias em tratativas: 0;\n\n%s\n\n*NF: 7502;*" % sep, copiado)
        self.assertTrue(copiado.endswith(sep + "\n\n"))
        self.app.var_busca.set("A")                             # uma nota so: sem separador
        self.app._executar_busca()
        self.app.update()
        self.app.copiar_notas_filtradas()
        self.assertNotIn(sep, self.app.clipboard_get())

    def test_menu_so_tem_uma_opcao_de_copiar(self):
        self.cadastrar(7601, "A", "REENTREGA")
        bloco = self.app.blocos[self.nota_por_nf(7601)["id"]]
        rotulos = []
        import tkinter as tk
        original = tk.Menu.tk_popup
        tk.Menu.tk_popup = lambda m, *a: rotulos.extend(
            m.entrycget(i, "label") for i in range(m.index("end") + 1) if m.type(i) == "command")
        try:
            bloco._abrir_menu(type("E", (), {"x_root": 0, "y_root": 0})())
        finally:
            tk.Menu.tk_popup = original
        copias = [r for r in rotulos if r.startswith("Copiar")]
        self.assertEqual(copias, ["Copiar informações da nota"])

    def test_duplo_clique_so_antes_das_atualizacoes(self):
        from nucleo import database as db
        from unittest import mock
        self.cadastrar(7701, "A", "REENTREGA")
        nota = self.nota_por_nf(7701)
        db.adicionar_tratativa(nota["id"], "PRIMEIRA")
        self.app.recarregar_lista()
        self.app.update()
        bloco = self.app.blocos[nota["id"]]
        txt = bloco.txt_cabecalho
        topo = txt.bbox("1.0")[1] + txt.winfo_rooty() + 4
        trat = txt.bbox("4.0")[1] + txt.winfo_rooty() + 4
        with mock.patch.object(type(bloco), "_adicionar_tratativa", lambda self, e=None: "break") as m:
            ev = lambda y: type("E", (), {"y_root": y})()
            self.assertEqual(bloco._duplo_clique(ev(topo)), "break")      # cabecalho: adiciona
            self.assertIsNone(bloco._duplo_clique(ev(trat)))               # atualizacoes: nao

    def test_selecao_com_mouse_e_ctrl_c(self):
        self.cadastrar(7801, "CLIENTE SELECAO", "REENTREGA")
        nota = self.nota_por_nf(7801)
        bloco = self.app.blocos[nota["id"]]
        self.app.selecionar_nota(nota["id"])
        txt = bloco.txt_cabecalho
        txt.tag_add("sel", "2.0", "2.7")          # o que o arrasto do mouse faz
        self.app._copiar_selecao_da_nota()
        self.assertEqual(self.app.clipboard_get(), "CLIENTE")

    def test_altura_do_cartao_mostra_todas_as_linhas(self):
        self.cadastrar(7301, "CLIENTE ALTURA", "REENTREGA")
        nota = self.nota_por_nf(7301)
        bloco = self.app.blocos[nota["id"]]
        for i in range(4):
            bloco._adicionar_linha_tratativa("01/01/2026 10:0%d" % i, "LINHA %d" % i)
        self.app.update()
        pixels = bloco.txt_cabecalho.count("1.0", "end", "ypixels")[0]
        self.assertGreaterEqual(int(bloco.caixa.cget("height")), pixels + 2 * bloco.PAD_TEXTO)

    def altura_correta(self, bloco):
        pixels = bloco.txt_cabecalho.count("1.0", "end", "ypixels")[0]
        esperado = pixels + 2 * bloco.PAD_TEXTO + 2
        return int(bloco.caixa.cget("height")) == esperado

    def test_nao_mede_a_altura_com_o_texto_ainda_sem_largura(self):
        """Janela ainda abrindo (Text sem largura real): medir daria uma altura gigante."""
        from unittest import mock
        self.cadastrar(7901, "CLIENTE A", "REENTREGA")
        self.app.update()
        bloco = self.app.blocos[self.nota_por_nf(7901)["id"]]
        certa = int(bloco.caixa.cget("height"))
        with mock.patch.object(bloco.txt_cabecalho, "winfo_width", lambda: 1):
            bloco._ajustar_altura_cabecalho()
        self.assertEqual(int(bloco.caixa.cget("height")), certa)               # nao mexeu
        bloco.caixa.configure(height=1)
        self.app._reajustar_lista()                                            # com largura real: mede
        self.app.update()
        self.assertTrue(self.altura_correta(bloco))

    def test_lista_e_reajustada_sozinha_ao_exibir_a_janela(self):
        self.assertTrue(getattr(self.app, "_lista_ja_ajustada", False))        # <Map> tratado

    def test_nova_atualizacao_aparece_na_hora_e_o_cartao_cresce(self):
        import time
        from unittest import mock
        self.cadastrar(7951, "CLIENTE ATUALIZA", "REENTREGA")
        self.cadastrar(7952, "OUTRO", "REENTREGA")
        nota = self.nota_por_nf(7951)
        bloco = self.app.blocos[nota["id"]]
        antes = int(bloco.caixa.cget("height"))
        with mock.patch("interface.nota_block.pedir_texto_atualizacao", lambda *a, **k: "texto novo da tratativa"):
            t0 = time.perf_counter()
            bloco._adicionar_tratativa()
            self.app.update_idletasks()
            gasto = time.perf_counter() - t0
        self.assertIn("TEXTO NOVO DA TRATATIVA", bloco.txt_cabecalho.get("1.0", "end"))
        self.assertGreater(int(bloco.caixa.cget("height")), antes)
        self.app.update()
        self.assertTrue(self.altura_correta(bloco))
        self.assertLess(gasto, 0.25, "inserir atualizacao demorou %.3fs" % gasto)   # sem recarregar a lista

    def test_cores_de_urgencia(self):
        from interface import tema
        self.assertEqual(tema.cor_urgencia(0), tema.cor_urgencia(2))
        self.assertNotEqual(tema.cor_urgencia(2), tema.cor_urgencia(3))
        self.assertEqual(tema.cor_urgencia(3), tema.cor_urgencia(7))
        self.assertNotEqual(tema.cor_urgencia(7), tema.cor_urgencia(8))


if __name__ == "__main__":
    unittest.main()
