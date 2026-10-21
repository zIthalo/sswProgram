# -*- coding: utf-8 -*-
"""Fluxos principais do sistema, com Tkinter real: cadastrar, editar, agendar,
resolver, buscar, atalhos de tratativa, desfazer, relatorio e tela Sobre."""

import unittest
from unittest import mock

import tkinter as tk

from testes.base import BaseTela
from nucleo import database as db
from nucleo import registro_erros
from nucleo import tratativas_rapidas


class TestCadastro(BaseTela):
    def test_cadastrar_nota_e_aparece_na_lista(self):
        self.cadastrar(100, "ACME", "REENTREGA")
        nota = self.nota_por_nf(100, "ACME")
        self.assertIsNotNone(nota)
        self.assertIn(nota["id"], self.app.blocos)

    def test_duplicada_pendente_bloqueia_mas_resolvida_nao(self):
        self.cadastrar(101, "ACME", "REENTREGA")
        self.cadastrar(101, "ACME", "REENTREGA")
        self.assertTrue(self.erros and "pendente" in self.erros[-1])
        self.assertEqual(len([n for n in db.listar_notas_ativas() if n["nf_numero"] == 101]), 1)
        db.marcar_resolvida(self.nota_por_nf(101)["id"])
        self.cadastrar(101, "ACME", "REENTREGA")
        self.assertIsNotNone(self.nota_por_nf(101, "ACME"))

    def test_cadastro_com_agendamento_pede_data_e_valida(self):
        self.cadastrar(102, "ACME", "AGENDAMENTO", data_agendamento="01012020")
        self.assertIsNone(self.nota_por_nf(102))           # data passada: nao cadastra
        self.cadastrar(102, "ACME", "AGENDAMENTO", data_agendamento="25122030")
        self.assertEqual(self.nota_por_nf(102)["agendamento_data"], "25122030")


class TestEdicao(BaseTela):
    def setUp(self):
        super().setUp()
        db.adicionar_cliente("ACME")
        db.adicionar_cliente("BETA LTDA")
        self.cadastrar(200, "ACME", "REENTREGA")
        self.nota_id = self.nota_por_nf(200)["id"]

    def test_editar_remetente_com_sugestao(self):
        self.escolher_na_busca("bet")
        self.app.editar_campo(self.nota_id, "cliente", "Remetente")
        self.assertEqual(db.obter_nota(self.nota_id)["cliente"], "BETA LTDA")

    def test_editar_remetente_novo_e_cadastrado(self):
        self.escolher_na_busca("GAMMA SA")
        self.app.editar_campo(self.nota_id, "cliente", "Remetente")
        self.assertEqual(db.obter_nota(self.nota_id)["cliente"], "GAMMA SA")
        self.assertIn("GAMMA SA", db.listar_clientes())

    def test_editar_ocorrencia_para_agendamento_pede_data(self):
        antes = dict(db.obter_nota(self.nota_id))
        self.respostas_data.append("25122030")
        self.escolher_na_busca("agen")
        self.app.editar_ocorrencia(self.nota_id)
        nota = db.obter_nota(self.nota_id)
        self.assertEqual((nota["ocorrencia"], nota["agendamento_data"]), ("AGENDAMENTO", "25122030"))
        for campo in ("nf_numero", "cliente", "sigla", "data_ocorrencia", "criado_em", "observacao"):
            self.assertEqual(nota[campo], antes[campo])

    def test_data_invalida_ou_cancelada_nao_altera(self):
        for resposta in ("01012020", "xx", None):
            self.respostas_data.append(resposta)
            self.escolher_na_busca("agen")
            self.app.editar_ocorrencia(self.nota_id)
            self.assertEqual(db.obter_nota(self.nota_id)["ocorrencia"], "REENTREGA")

    def test_editar_data_do_agendamento_e_sair_dele(self):
        self.respostas_data.append("25122030")
        self.escolher_na_busca("agen")
        self.app.editar_ocorrencia(self.nota_id)
        self.respostas_data.append("26122030")
        self.app.editar_data_agendamento(self.nota_id)
        self.assertEqual(db.obter_nota(self.nota_id)["agendamento_data"], "26122030")
        self.escolher_na_busca("reentrega")
        self.app.editar_ocorrencia(self.nota_id)
        self.assertIsNone(db.obter_nota(self.nota_id)["agendamento_data"])

    def test_item_de_menu_so_aparece_quando_agendamento(self):
        self.respostas_data.append("25122030")
        self.escolher_na_busca("agen")
        self.app.editar_ocorrencia(self.nota_id)
        capturados = []
        with mock.patch.object(tk.Menu, "tk_popup", lambda self_, x, y: capturados.append(self_)):
            bloco = self.app.blocos[self.nota_id]
            bloco._abrir_menu(mock.Mock(x_root=0, y_root=0))
            menu = capturados[-1]
            rotulos = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)
                       if menu.type(i) == "command"]
        self.assertIn("Alterar data do agendamento", rotulos)

    def test_falha_de_banco_mostra_erro_e_nao_altera(self):
        import sqlite3
        with mock.patch.object(db, "atualizar_ocorrencia",
                               side_effect=sqlite3.OperationalError("disco cheio")):
            self.escolher_na_busca("prio")
            self.app.editar_ocorrencia(self.nota_id)
        self.assertTrue(any("Falha ao salvar" in e for e in self.erros))
        self.assertEqual(db.obter_nota(self.nota_id)["ocorrencia"], "REENTREGA")


class TestTratativaAtalhos(BaseTela):
    def test_funcao_expandir(self):
        for entrada, saida in (("e", "tratando via e-mail"), ("E", "tratando via e-mail"),
                               ("w", "tratando via WhatsApp"), ("W", "tratando via WhatsApp"),
                               ("s", "informacoes em sistema"), (" S ", "informacoes em sistema"),
                               ("ex", "ex"), ("e mail", "e mail"), ("", ""), ("x", "x")):
            self.assertEqual(tratativas_rapidas.expandir_atalho(entrada), saida)

    def test_nova_atualizacao_grava_frase(self):
        self.cadastrar(300, "ACME", "REENTREGA")
        nota_id = self.nota_por_nf(300)["id"]
        for letra, esperado in (("e", "TRATANDO VIA E-MAIL"), ("W", "TRATANDO VIA WHATSAPP"),
                                ("s", "INFORMACOES EM SISTEMA"), ("contato feito", "CONTATO FEITO")):
            with mock.patch("interface.nota_block.pedir_texto_atualizacao", lambda *a, **k: letra):
                self.app.blocos[nota_id]._adicionar_tratativa()
            textos = [t["texto"] for t in db.listar_tratativas(nota_id)]
            self.assertEqual(textos[-1], esperado)


class TestResolverBuscaDesfazer(BaseTela):
    def setUp(self):
        super().setUp()
        self.cadastrar(400, "ACME", "REENTREGA")
        self.cadastrar(401, "BETA", "REENTREGA")
        self.id400 = self.nota_por_nf(400)["id"]

    def _resolver(self, id_nota, morosidade="cliente"):
        nota = db.obter_nota(id_nota)
        resultado = {"nf_numero": nota["nf_numero"], "cliente": nota["cliente"],
                     "ocorrencia": nota["ocorrencia"], "sigla": nota["sigla"],
                     "dias": 3, "horas": 5, "morosidade": morosidade}
        with mock.patch("interface.edicao_notas.fluxo_marcar_resolvido", lambda *a, **k: resultado):
            self.app.marcar_como_resolvido(id_nota)

    def test_resolver_vai_para_historico(self):
        self._resolver(self.id400)
        self.assertIsNone(self.nota_por_nf(400))
        self.assertEqual(len(db.buscar_historico_por_nf(400)), 1)

    def test_buscar_por_nf(self):
        self.app.var_busca.set("401")
        self.app._executar_busca()
        bloco = self.app.blocos[self.nota_por_nf(401)["id"]]
        self.assertEqual(str(bloco.txt_cabecalho.cget("background")), "#fff2a8")  # nota destacada
        self.assertNotEqual(str(self.app.blocos[self.id400].txt_cabecalho.cget("background")), "#fff2a8")

    def test_buscar_nf_repetida_mostra_todas(self):
        self.cadastrar(400, "OUTRO", "REENTREGA")
        self.app.var_busca.set("400")
        self.app._executar_busca()
        self.app.update()
        self.assertEqual(len(self.app.blocos), 2)

    def test_desfazer_edicao_e_resolucao(self):
        self.escolher_na_busca("prio")
        self.app.editar_ocorrencia(self.id400)
        self.assertEqual(db.obter_nota(self.id400)["ocorrencia"], "PRIORIZAR ENTREGA")
        self.app.desfazer_ultima_alteracao()
        self.assertEqual(db.obter_nota(self.id400)["ocorrencia"], "REENTREGA")

        self._resolver(self.id400)
        self.app.desfazer_ultima_alteracao()
        self.assertIsNotNone(self.nota_por_nf(400))
        self.assertEqual(db.buscar_historico_por_nf(400), [])
        self.assertIn(self.id400, self.app.blocos)

    def test_desfazer_sem_nada_nao_quebra(self):
        self.app.desfazer_ultima_alteracao()

    def test_desfazer_limpeza_do_historico_e_remocao_de_cadastro(self):
        self._resolver(self.id400)
        self.app._registrar_desfazer_cadastro("remetente", "ZZZ", db.adicionar_cliente)
        self.app.desfazer_ultima_alteracao()
        self.assertIn("ZZZ", db.listar_clientes())
        registros = list(db.listar_historico())
        db.limpar_historico_manual()
        from nucleo import database
        self.app.pilha_desfazer.registrar("limpeza", lambda: database.restaurar_historico(registros))
        self.app.desfazer_ultima_alteracao()
        self.assertEqual(len(db.listar_historico()), 1)

    def test_ctrl_z_na_janela_principal(self):
        self.escolher_na_busca("prio")
        self.app.editar_ocorrencia(self.id400)
        self.app.focus_force()
        self.app.event_generate("<Control-z>")
        self.app.update()
        self.assertEqual(db.obter_nota(self.id400)["ocorrencia"], "REENTREGA")


class TestAtalhosGlobais(BaseTela):
    def _tecla(self, sequencia):
        self.app.update()
        self.app.focus_force()
        self.app.update()
        self.app.event_generate(sequencia)
        self.app.update()

    def test_ctrl_n_limpa_formulario_e_foca_nf(self):
        self.app.var_nf.set("123")
        self.app.var_cliente.set("ACME")
        self.app.entry_busca.focus_force()
        self.app.update()
        self.app.entry_busca.event_generate("<Control-n>")
        self.app.update()
        self.assertEqual((self.app.var_nf.get(), self.app.var_cliente.get()), ("", ""))
        self.assertIs(self.app.focus_get(), self.app.entry_nf)

    def test_ctrl_f_foca_busca(self):
        self.app.entry_nf.focus_force()
        self.app.update()
        self.app.entry_nf.event_generate("<Control-f>")
        self.app.update()
        self.assertIs(self.app.focus_get(), self.app.entry_busca)

    def test_f5_recarrega_lista_com_dados_novos(self):
        self.assertEqual(len(self.app.blocos), 0)
        db.inserir_nota(900, "ACME", "REENTREGA", "SP", "16102026", None)  # entrou por fora da tela
        self._tecla("<F5>")
        self.assertEqual(len(self.app.blocos), 1)

    def test_atalhos_listados_no_menu_editar(self):
        barra = self.app.nametowidget(self.app.cget("menu"))
        indice = [i for i in range(barra.index("end") + 1)
                  if barra.type(i) == "cascade" and barra.entrycget(i, "label") == "Editar"][0]
        menu = self.app.nametowidget(barra.entrycget(indice, "menu"))
        acel = [menu.entrycget(i, "accelerator") for i in range(menu.index("end") + 1)
                if menu.type(i) == "command"]
        self.assertEqual(acel, ["Ctrl+Z", "Ctrl+N", "Ctrl+F", "F5"])


class TestJanelasUnicasEFrente(BaseTela):
    def _toplevels(self):
        return [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)]

    def test_nao_abre_duas_janelas_iguais(self):
        db.adicionar_empresa_parceira("PARCEIRA X")
        aberturas = {
            "relatorio": self.app._abrir_relatorio,
            "historico": self.app._abrir_historico,
            "sobre": self.app._abrir_sobre,
            "empresas": self.app._gerenciar_empresas_parceiras,
            "tipos": self.app._gerenciar_tipos_ocorrencia,
            "remetentes": self.app._gerenciar_clientes,
        }
        for nome, abrir in aberturas.items():
            antes = len(self._toplevels())
            abrir()
            self.app.update()
            self.assertEqual(len(self._toplevels()), antes + 1, nome + ": nao abriu")
            abrir()
            abrir()
            self.app.update()
            self.assertEqual(len(self._toplevels()), antes + 1, nome + ": abriu duplicada")

    def test_reabre_depois_de_fechar(self):
        self.app._abrir_sobre()
        self.app.update()
        self._toplevels()[-1].destroy()
        self.app.update()
        self.app._abrir_sobre()
        self.app.update()
        self.assertEqual(len(self._toplevels()), 1)

    def test_pedir_de_novo_traz_a_existente_para_frente(self):
        self.app._abrir_sobre()
        self.app.update()
        sobre = self._toplevels()[-1]
        sobre.withdraw()
        self.app.update()
        self.app._abrir_sobre()
        self.app.update()
        self.assertEqual(sobre.state(), "normal")

    def test_janelas_ficam_na_frente_da_principal(self):
        for abrir in (self.app._abrir_relatorio, self.app._abrir_historico, self.app._abrir_sobre,
                      self.app._gerenciar_clientes):
            abrir()
        self.app.update()
        ordem = [str(w) for w in self.app.tk.call("wm", "stackorder", self.app).split()] \
            if False else list(self.app.tk.splitlist(self.app.tk.call("wm", "stackorder", ".")))
        for janela in self._toplevels():
            self.assertEqual(str(janela.wm_transient()), str(self.app))
            self.assertGreater(ordem.index(str(janela)), ordem.index("."), "janela atras da principal")

    def test_detalhes_abre_na_frente_do_relatorio_e_nao_duplica(self):
        db.inserir_historico(1, "CLIENTE LENTO", "REENTREGA", "SP", 5, 2, "cliente")
        self.app._abrir_relatorio()
        self.app.update()
        rel = self._toplevels()[-1]
        rel.focus_force()
        self.app.update()
        regs = db.buscar_historico_por_cliente("CLIENTE LENTO", True)
        self.app._mostrar_detalhes_historico("Notas do cliente X", regs)
        self.app._mostrar_detalhes_historico("Notas do cliente X", regs)
        self.app.update()
        detalhes = [w for w in self._toplevels() if w is not rel]
        self.assertEqual(len(detalhes), 1)
        self.assertEqual(str(detalhes[0].wm_transient()), str(rel))


class TestPosicaoJanelaPrincipal(BaseTela):
    def _reabrir(self):
        from interface.app import App
        try:
            self.app.destroy()
        except tk.TclError:
            pass  # ja foi destruida por _ao_fechar
        self.app = App()
        self.app.report_callback_exception = lambda *a: self.erros_tk.append("erro")
        self.app.update()

    def test_abre_onde_foi_fechada(self):
        self.app.geometry("700x500+120+90")
        self.app.update()
        self.app._ao_fechar()
        self._reabrir()
        self.assertEqual(self.app.geometry(), "700x500+120+90")

    def test_sem_arquivo_usa_tamanho_padrao(self):
        self.assertTrue(self.app.geometry().startswith("920x680"))

    def test_arquivo_corrompido_nao_quebra(self):
        from nucleo import posicao_janela
        with open(posicao_janela.caminho_arquivo(), "w") as arq:
            arq.write("{isto nao e json")
        self._reabrir()
        self.assertTrue(self.app.geometry().startswith("920x680"))

    def test_posicao_fora_da_tela_volta_ao_padrao(self):
        from nucleo import posicao_janela
        posicao_janela.salvar(700, 500, 9000, 9000, False)
        self._reabrir()
        self.assertTrue(self.app.geometry().startswith("920x680"))

    def test_ajustar_a_tela(self):
        from nucleo import posicao_janela as pj
        ok = {"largura": 800, "altura": 600, "x": 10, "y": 10, "maximizada": False}
        self.assertEqual(pj.ajustar_a_tela(ok, 0, 0, 1920, 1080), (800, 600, 10, 10))
        grande = dict(ok, largura=5000, altura=5000)
        self.assertEqual(pj.ajustar_a_tela(grande, 0, 0, 1920, 1080)[:2], (1920, 1080))
        # monitor secundario a esquerda do principal (coordenadas negativas) e valido
        esq = dict(ok, x=-1500)
        self.assertEqual(pj.ajustar_a_tela(esq, -1920, 0, 3840, 1080)[2], -1500)
        # ... mas se esse monitor nao existe mais, volta ao padrao
        self.assertIsNone(pj.ajustar_a_tela(esq, 0, 0, 1920, 1080))
        self.assertIsNone(pj.ajustar_a_tela(None, 0, 0, 1920, 1080))
        self.assertEqual(pj.interpretar_geometria("920x680+-5+10"), (920, 680, -5, 10))
        self.assertIsNone(pj.interpretar_geometria("lixo"))

    def test_maximizada_e_lembrada(self):
        from nucleo import posicao_janela
        posicao_janela.salvar(700, 500, 120, 90, True)
        self.assertTrue(posicao_janela.carregar()["maximizada"])


class TestFeedbackPlaceholderBotao(BaseTela):
    def setUp(self):
        super().setUp()
        self.mensagens = []
        self.app.mostrar_mensagem_flutuante = lambda texto, event=None: self.mensagens.append(texto)

    def test_rotulo_do_campo_nf_mostra_o_atalho(self):
        rotulos = [w.cget("text") for w in self.app.entry_nf.master.winfo_children()
                   if w.winfo_class() == "TLabel"]
        self.assertIn("NF (CTRL + N):", rotulos)
        self.assertFalse(hasattr(self.app.entry_nf, "dica_placeholder"))   # sem placeholder dentro do campo

    def test_botao_atualizar_antes_de_limpar_filtro(self):
        self.assertEqual(self.app.btn_atualizar.cget("text"), "Atualizar (F5)")
        col_atualizar = int(self.app.btn_atualizar.grid_info()["column"])
        col_limpar = int(self.app.btn_limpar_filtro.grid_info()["column"])
        self.assertEqual(col_atualizar + 1, col_limpar)
        db.inserir_nota(910, "ACME", "REENTREGA", "SP", "16102026", None)
        self.app.btn_atualizar.invoke()
        self.assertEqual(len(self.app.blocos), 1)

    def test_feedback_ao_registrar_nota(self):
        self.cadastrar(500, "ACME", "REENTREGA")
        self.assertIn("Ocorrência registrada com sucesso.", self.mensagens)

    def test_sem_feedback_quando_cadastro_falha(self):
        self.cadastrar(501, "ACME", "REENTREGA")
        self.mensagens.clear()
        self.cadastrar(501, "ACME", "REENTREGA")   # duplicada
        self.assertNotIn("Ocorrência registrada com sucesso.", self.mensagens)

    def test_feedback_ao_resolver(self):
        self.cadastrar(502, "ACME", "REENTREGA")
        nota = self.nota_por_nf(502)
        resultado = {"nf_numero": 502, "cliente": "ACME", "ocorrencia": "REENTREGA", "sigla": "SP",
                     "dias": 0, "horas": 1, "morosidade": "nenhum"}
        with mock.patch("interface.edicao_notas.fluxo_marcar_resolvido", lambda *a, **k: resultado):
            self.app.marcar_como_resolvido(nota["id"])
        self.assertIn("Ocorrência resolvida pressione CTRL + Z para desfazer", self.mensagens)

    def test_feedback_real_aparece_e_some_em_1_segundo(self):
        import time
        del self.app.mostrar_mensagem_flutuante          # usa a implementacao real
        self.app.mostrar_mensagem_flutuante("teste")
        self.app.update()
        popups = [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertEqual(len(popups), 1)
        fim = time.time() + 0.7
        while time.time() < fim:
            self.app.update()
        self.assertTrue(popups[0].winfo_exists())          # ainda visivel antes de 1 s
        fim = time.time() + 0.6
        while time.time() < fim:
            self.app.update()
        self.assertFalse(popups[0].winfo_exists())         # sumiu apos ~1 s

    def test_atalho_r_mercadoria_em_rota(self):
        for entrada in ("r", "R", " r ", "R "):
            self.assertEqual(tratativas_rapidas.expandir_atalho(entrada), "MERCADORIA EM ROTA DE ENTREGA HOJE")
        self.assertEqual(tratativas_rapidas.expandir_atalho("rota"), "rota")
        self.cadastrar(503, "ACME", "REENTREGA")
        nota_id = self.nota_por_nf(503)["id"]
        with mock.patch("interface.nota_block.pedir_texto_atualizacao", lambda *a, **k: "r"):
            self.app.blocos[nota_id]._adicionar_tratativa()
        self.assertEqual(db.listar_tratativas(nota_id)[-1]["texto"], "MERCADORIA EM ROTA DE ENTREGA HOJE")

    def test_busca_sem_resultado_limpa_o_campo(self):
        self.cadastrar(504, "ACME", "REENTREGA")
        for digitado in ("99999", "naoexiste"):
            self.app.var_busca.set(digitado)
            self.app._executar_busca()
            self.app.update()
            self.assertEqual(self.app.var_busca.get(), "", digitado)
            self.assertEqual(len(self.app.blocos), 1, "a lista deve voltar a mostrar as notas")
            self.assertIs(self.app.focus_get(), self.app.entry_busca)

    def test_busca_com_resultado_mantem_o_campo(self):
        self.cadastrar(505, "ACME", "REENTREGA")
        self.app.var_busca.set("505")
        self.app._executar_busca()
        self.assertEqual(self.app.var_busca.get(), "505")

    def test_duplicada_limpa_todos_os_campos(self):
        self.cadastrar(506, "ACME", "REENTREGA", "SP")
        self.app.var_nf.set("506")
        self.app.var_cliente.set("ACME")
        self.app.var_ocorrencia.set("REENTREGA")
        self.app.var_sigla.set("SP")
        self.app._adicionar_nota()
        self.assertTrue(self.erros and "pendente" in self.erros[-1])
        for var in (self.app.var_nf, self.app.var_cliente, self.app.var_ocorrencia, self.app.var_sigla):
            self.assertEqual(var.get(), "")
        self.assertIs(self.app.focus_get(), self.app.entry_nf)


class TestJanelasEmFoco(BaseTela):
    def _esperar(self, segundos=0.4):
        import time
        fim = time.time() + segundos
        while time.time() < fim:
            self.app.update()

    def test_janelas_abrem_em_foco_e_sobre_a_principal(self):
        self.app.geometry("900x700+100+60")
        self.app.update()
        for abrir in (self.app._abrir_relatorio, self.app._abrir_historico,
                      self.app._abrir_sobre, self.app._gerenciar_clientes):
            antes = set(w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel))
            abrir()
            self._esperar()
            nova = [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel) and w not in antes][0]
            self.assertTrue(nova.winfo_viewable())
            foco = self.app.focus_get()
            self.assertIsNotNone(foco)
            self.assertIs(foco.winfo_toplevel(), nova, "janela %s sem foco" % nova.title())
            cx = nova.winfo_rootx() + nova.winfo_width() // 2
            cy = nova.winfo_rooty() + nova.winfo_height() // 2
            self.assertTrue(self.app.winfo_rootx() <= cx <= self.app.winfo_rootx() + self.app.winfo_width())
            self.assertTrue(self.app.winfo_rooty() <= cy <= self.app.winfo_rooty() + self.app.winfo_height())
            nova.destroy()
            self._esperar(0.1)


class TestCursorNoCampo(BaseTela):
    """O cursor de digitacao ja deve estar no campo ao abrir o dialogo (sem precisar clicar)."""

    def _foco_no_dialogo(self, abrir, fechar_com="_cancelar"):
        achado = {}

        def checar():
            topo = [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)][-1]
            achado["foco"] = self.app.focus_get()
            achado["topo"] = topo
            getattr(topo, fechar_com)()
        self.app.after(500, checar)
        abrir()
        return achado

    def test_nova_atualizacao_por_duplo_clique_ou_enter(self):
        self.cadastrar(600, "ACME", "REENTREGA")
        bloco = self.app.blocos[self.nota_por_nf(600)["id"]]
        for acionar in (bloco._adicionar_tratativa,                       # duplo clique
                        self.app._adicionar_tratativa_via_teclado):        # Enter com a nota selecionada
            self.app.nota_selecionada_id = bloco.nota_id
            achado = self._foco_no_dialogo(acionar)
            self.assertIsInstance(achado["foco"], tk.Text)
            self.assertIs(achado["foco"], achado["topo"].texto)

    def test_nova_atualizacao_aceita_digitacao_imediata(self):
        self.cadastrar(601, "ACME", "REENTREGA")
        bloco = self.app.blocos[self.nota_por_nf(601)["id"]]
        resultado = {}

        def digitar():
            topo = [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)][-1]
            topo.texto.insert("1.0", "r")   # o que a digitacao no foco faria
            resultado["texto"] = topo.texto.get("1.0", "end").strip()
            topo._confirmar()
        self.app.after(500, digitar)
        bloco._adicionar_tratativa()
        self.assertEqual(db.listar_tratativas(bloco.nota_id)[-1]["texto"], "MERCADORIA EM ROTA DE ENTREGA HOJE")

    def test_busca_de_remetente_e_cadastros(self):
        db.adicionar_cliente("ACME")
        achado = self._foco_no_dialogo(
            lambda: __import__("interface.dialogs", fromlist=["x"]).pedir_opcao(
                self.app, "t", "r", ["ACME"]))
        self.assertIs(achado["foco"], achado["topo"].entry)
        self.app._gerenciar_clientes()
        for _ in range(30):
            self.app.update()
            import time; time.sleep(0.02)
        topo = [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        self.assertIs(self.app.focus_get(), topo.entry_novo)


class TestRelatorioSobreErros(BaseTela):
    def test_cliente_moroso_clicavel(self):
        db.inserir_historico(1, "CLIENTE LENTO", "REENTREGA", "SP", 5, 2, "cliente")
        db.inserir_historico(2, "CLIENTE LENTO", "REENTREGA", "RJ", 9, 0, "cliente")
        db.inserir_historico(3, "CLIENTE LENTO", "REENTREGA", "RJ", 1, 0, "unidade")
        regs = db.buscar_historico_por_cliente("CLIENTE LENTO", somente_morosidade_cliente=True)
        self.assertEqual(sorted(r["nf_numero"] for r in regs), [1, 2])
        self.app._abrir_relatorio()
        self.app.update()
        rel = [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)][-1]

        def achar(widget):
            for f in widget.winfo_children():
                if isinstance(f, tk.Label) and "CLIENTE LENTO" in str(f.cget("text")):
                    return f
                r = achar(f)
                if r:
                    return r
        rotulo = achar(rel)
        self.assertIsNotNone(rotulo)
        self.assertEqual(str(rotulo.cget("cursor")), "hand2")
        antes = len([w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)])
        rotulo.event_generate("<Button-1>")
        self.app.update()
        depois = [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertEqual(len(depois), antes + 1)
        self.assertIn("CLIENTE LENTO", depois[-1].title())

    def test_aba_sobre(self):
        self.app._abrir_sobre()
        self.app.update()
        janela = [w for w in self.app.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        textos = []

        def coletar(w):
            for f in w.winfo_children():
                try:
                    textos.append(str(f.cget("text")))
                except tk.TclError:
                    pass
                coletar(f)
        coletar(janela)
        self.assertIn("Desenvolvido por Ithalo Willian", textos)
        self.assertIn("Contato: ithalowillian@hotmail.com", textos)

    def test_menu_tem_sobre_e_editar(self):
        barra = self.app.nametowidget(self.app.cget("menu"))
        rotulos = [barra.entrycget(i, "label") for i in range(barra.index("end") + 1)
                   if barra.type(i) in ("cascade", "command")]
        self.assertIn("Sobre", rotulos)
        self.assertIn("Editar", rotulos)

    def test_erro_em_callback_vai_para_log(self):
        registro_erros.instalar()
        caminho = registro_erros.caminho_log()
        self.assertTrue(caminho.startswith(self.pasta))
        with mock.patch.object(registro_erros, "_avisar_usuario") as aviso:
            def falha():
                raise RuntimeError("falha de teste")
            self.erros_tk_original = self.app.report_callback_exception
            del self.app.report_callback_exception   # volta ao tratador instalado (registro_erros)
            self.app.after(10, falha)
            self.app.after(60, self.app.quit)
            self.app.mainloop()
            self.app.report_callback_exception = self.erros_tk_original
            aviso.assert_called_once()
        with open(caminho, encoding="utf-8") as arq:
            conteudo = arq.read()
        self.assertIn("RuntimeError: falha de teste", conteudo)
        self.assertIn("versao", conteudo)


if __name__ == "__main__":
    unittest.main()
