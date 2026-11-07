# -*- coding: utf-8 -*-
"""Tela "Clientes e CNPJ": dados (sem janela) e janela. Usa dados ficticios."""

import os
import tempfile
import unittest
import zipfile
from unittest import mock

from nucleo import database as db
from nucleo import tabela_clientes as tab
from testes.base import BaseTela


def criar_xlsx(caminho, linhas):
    """Planilha .xlsx minima (textos inline) so para testar a importacao."""
    def celula(ref, valor):
        if isinstance(valor, int):
            return '<c r="%s"><v>%d</v></c>' % (ref, valor)
        return '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, valor)
    corpo = ""
    for i, linha in enumerate(linhas, start=2):
        if not linha:
            continue
        corpo += '<row r="%d">%s</row>' % (i, "".join(
            celula("%s%d" % ("BCDEFGH"[j], i), v) for j, v in enumerate(linha) if v != ""))
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   '<sheets><sheet name="P" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                   '<sheetData>%s</sheetData></worksheet>' % corpo)


class TestDadosTabela(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix="sac_tab_")
        self._p = mock.patch.object(db, "get_db_path", lambda: os.path.join(self.pasta, "t.db"))
        self._p.start()
        db.init_db()

    def tearDown(self):
        self._p.stop()

    def ids(self):
        return {c["nome"]: c["id"] for c in tab.listar_colunas()}

    def test_colunas_padrao_e_funcoes_de_texto(self):
        self.assertEqual([c["nome"] for c in tab.listar_colunas()], ["Cliente", "CNPJ", "Vendedor", "Contatos"])
        self.assertEqual(tab.normalizar_cnpj("460986000506"), "00460986000506")      # zeros recuperados
        self.assertEqual(tab.normalizar_cnpj("12.345.678/0001-95"), "12345678000195")
        self.assertEqual(tab.normalizar_cnpj("sem cnpj"), "sem cnpj")
        self.assertEqual(tab.formatar_cnpj("12345678000195"), "12.345.678/0001-95")
        self.assertEqual(tab.texto_para_copiar("12.345.678/0001-95"), "12345678000195")
        self.assertEqual(tab.nome_para_nota("Empresa Exemplo/ não possui isenção"), "Empresa Exemplo")
        self.assertEqual(tab.nome_para_nota("COMERCIAL BETA S/A"), "COMERCIAL BETA S/A")

    def test_linhas_celulas_ordem_e_remocao(self):
        c = self.ids()
        a = tab.adicionar_linha({c["Cliente"]: "Zeta", c["CNPJ"]: "1"})
        b = tab.adicionar_linha({c["Cliente"]: "Alfa"})
        m = tab.adicionar_linha({c["Cliente"]: "Meio"}, depois_de=a)
        self.assertEqual([l["id"] for l in tab.listar_linhas()], [a, m, b])
        tab.reordenar_linhas([b, a, m])
        self.assertEqual([l["id"] for l in tab.listar_linhas()], [b, a, m])
        self.assertEqual(tab.salvar_celula(a, c["CNPJ"], "12.345.678/0001-95"), "12345678000195")
        tab.salvar_celula(a, c["Vendedor"], "  Ana ")
        linha = [l for l in tab.listar_linhas() if l["id"] == a][0]
        self.assertEqual(linha["valores"][c["Vendedor"]], "Ana")
        tab.remover_linha(a)
        self.assertEqual(len(tab.listar_linhas()), 2)

    def test_colunas_novas_renomear_mover_excluir(self):
        nova = tab.adicionar_coluna("Região")
        with self.assertRaises(tab.TabelaClientesErro):
            tab.adicionar_coluna("região")                      # nome repetido
        tab.renomear_coluna(nova, "Regional")
        self.assertTrue(tab.mover_coluna(nova, -1))
        self.assertEqual([c["nome"] for c in tab.listar_colunas()][3], "Regional")
        linha = tab.adicionar_linha({nova: "Sul"})
        tab.remover_coluna(nova)
        self.assertNotIn(nova, tab.listar_linhas()[0]["valores"])  # dados da coluna saem junto
        with self.assertRaises(tab.TabelaClientesErro):
            tab.remover_coluna(self.ids()["Cliente"])           # a do cliente nao pode sair

    def test_importar_xlsx(self):
        arq = os.path.join(self.pasta, "clientes.xlsx")
        criar_xlsx(arq, [["Cliente ", "CNPJ", "Vendedor", "contatos ", "Região"],
                         ["Alfa Ltda/ nota", 460986000506, "Ana", "a@a.com", "Sul"],
                         ["Beta S/A", "12.345.678/0001-95", "Bia", "", ""]])
        self.assertEqual(tab.importar_xlsx(arq), (2, 0))
        self.assertEqual(tab.importar_xlsx(arq), (0, 2))        # de novo: nao duplica
        c = self.ids()
        self.assertIn("Região", c)
        valores = [l["valores"] for l in tab.listar_linhas()]
        self.assertEqual(valores[0][c["CNPJ"]], "00460986000506")
        self.assertEqual(valores[0][c["Região"]], "Sul")
        self.assertEqual(valores[1][c["CNPJ"]], "12345678000195")

    def planilha_variada(self):
        arq = os.path.join(self.pasta, "variada.xlsx")
        criar_xlsx(arq, [["TITULO SOLTO"],
                         ["Cliente", "CNPJ", "", "Vendedor", "", "Filial"],
                         ["Alfa Ltda", 460986000506, "", "Ana", "", "SP"],
                         [],
                         ["Alfa Ltda", 460986000506, "", "Ana", "", "SP"],       # repetida: tem que ficar
                         ["Beta", "", "", "", "", ""],
                         ["Gama", "98765432000110", "", "Bia", "obs sem titulo", ""]])
        return arq

    def test_substituir_importa_exatamente_como_a_planilha(self):
        c = self.ids()
        tab.adicionar_linha({c["Cliente"]: "VELHO"})            # dado antigo some na substituicao
        tab.adicionar_coluna("Antiga")
        self.assertEqual(tab.substituir_por_xlsx(self.planilha_variada()), (5, 4))
        cols = tab.listar_colunas()
        self.assertEqual([x["nome"] for x in cols], ["Cliente", "CNPJ", "Vendedor", "Coluna 6", "Filial"])
        self.assertEqual([x["tipo"] for x in cols], ["cliente", "cnpj", "texto", "texto", "texto"])
        linhas = tab.listar_linhas()
        self.assertEqual(len(linhas), 4)                         # vazias fora; repetidas dentro
        nomes = [l["valores"].get(cols[0]["id"]) for l in linhas]
        self.assertEqual(nomes, ["Alfa Ltda", "Alfa Ltda", "Beta", "Gama"])
        self.assertEqual(linhas[0]["valores"][cols[1]["id"]], "00460986000506")
        self.assertEqual(linhas[3]["valores"][cols[3]["id"]], "obs sem titulo")   # coluna sem titulo mantida
        self.assertNotIn("VELHO", nomes)

    def test_substituir_falha_sem_tocar_na_tabela(self):
        c = self.ids()
        tab.adicionar_linha({c["Cliente"]: "FICA"})
        arq = os.path.join(self.pasta, "ruim.xlsx")
        open(arq, "wb").write(b"isto nao e um xlsx")
        with self.assertRaises(tab.TabelaClientesErro):
            tab.substituir_por_xlsx(arq)
        self.assertEqual(len(tab.listar_linhas()), 1)

    def test_limpar_e_restaurar_foto(self):
        c = self.ids()
        tab.adicionar_linha({c["Cliente"]: "A", c["CNPJ"]: "12345678000195"})
        tab.adicionar_coluna("Extra")
        foto = tab.tirar_foto()
        tab.limpar_tabela()
        self.assertEqual(tab.total_linhas(), 0)
        self.assertEqual([x["nome"] for x in tab.listar_colunas()], ["Cliente", "CNPJ", "Vendedor", "Contatos"])
        tab.restaurar_foto(foto)
        self.assertEqual(tab.tirar_foto(), foto)

    def test_ordenacao_natural(self):
        k = tab.chave_ordenacao
        self.assertLess(k("Cliente 2"), k("Cliente 10"))
        self.assertLess(k("álamo"), k("Beta"))


class TestJanelaClientes(BaseTela):
    def abrir(self):
        self.app._abrir_clientes_cnpj()
        self.app.update()
        return self.app._janelas_unicas["clientes_cnpj"]

    def popular(self):
        c = {x["nome"]: x["id"] for x in tab.listar_colunas()}
        for nome, cnpj in (("Zeta Ltda", "12345678000195"), ("Alfa SA", "98765432000110"), ("Beta", "")):
            tab.adicionar_linha({c["Cliente"]: nome, c["CNPJ"]: cnpj, c["Vendedor"]: "Ana"})
        return c

    def test_abre_uma_unica_vez_e_mostra_as_linhas(self):
        self.popular()
        j = self.abrir()
        self.app._abrir_clientes_cnpj()
        self.assertEqual(len([w for w in self.app.winfo_children() if w is j]), 1)
        self.assertEqual(len(j.tree.get_children()), 3)
        primeira = j.tree.item(j.tree.get_children()[0], "values")
        self.assertEqual(primeira[1], "12.345.678/0001-95")     # CNPJ formatado na tela

    def test_clicar_no_cnpj_copia_so_os_numeros(self):
        c = self.popular()
        j = self.abrir()
        iid = j.tree.get_children()[0]
        x, y, w, h = j.tree.bbox(iid, str(c["CNPJ"]))
        j.tree.event_generate("<Button-1>", x=x + 5, y=y + 5)
        self.app.update()
        self.assertEqual(self.app.clipboard_get(), "12345678000195")
        self.app.clipboard_clear()
        self.app.clipboard_append("intacto")
        x, y, w, h = j.tree.bbox(iid, str(c["Vendedor"]))       # outra coluna: nao copia
        j.tree.event_generate("<Button-1>", x=x + 5, y=y + 5)
        self.app.update()
        self.assertEqual(self.app.clipboard_get(), "intacto")

    def test_editar_celula_grava_no_banco(self):
        c = self.popular()
        j = self.abrir()
        iid = j.tree.get_children()[0]
        j._celula = (iid, c["Vendedor"])
        j.tree.selection_set(iid)
        j._editar_celula_atual()
        j._editor[1].set("Carlos")
        j._salvar_edicao()
        linha = [l for l in tab.listar_linhas() if str(l["id"]) == iid][0]
        self.assertEqual(linha["valores"][c["Vendedor"]], "Carlos")

    def test_ordenar_por_coluna_fica_gravado(self):
        c = self.popular()
        j = self.abrir()
        j.ordenar(c["Cliente"])
        nomes = [l["valores"].get(c["Cliente"]) for l in tab.listar_linhas()]
        self.assertEqual(nomes, ["Alfa SA", "Beta", "Zeta Ltda"])
        j.ordenar(c["Cliente"])                                 # de novo: inverte
        nomes = [l["valores"].get(c["Cliente"]) for l in tab.listar_linhas()]
        self.assertEqual(nomes, ["Zeta Ltda", "Beta", "Alfa SA"])

    def test_nova_linha_e_nova_coluna(self):
        self.popular()
        j = self.abrir()
        j.tree.selection_set(j.tree.get_children()[0])
        j.nova_linha()
        self.app.update()
        self.assertEqual(len(tab.listar_linhas()), 4)
        j._cancelar_edicao()
        with mock.patch("interface.clientes_cnpj.pedir_texto_atualizacao", lambda *a, **k: "Região"):
            j.nova_coluna()
        self.assertIn("Região", [c["nome"] for c in tab.listar_colunas()])
        self.assertIn("Região", [j.tree.heading(col, "text") for col in j.tree["columns"]])

    def test_remover_tabela_e_desfazer(self):
        self.popular()
        j = self.abrir()
        j.remover_tabela()
        self.assertEqual(len(j.tree.get_children()), 0)
        self.assertEqual(tab.total_linhas(), 0)
        self.app.desfazer_ultima_alteracao()
        self.app.update()
        self.assertEqual(tab.total_linhas(), 3)
        self.assertEqual(len(j.tree.get_children()), 3)          # a janela aberta acompanha

    def test_importar_substituindo_e_acrescentando(self):
        self.popular()
        j = self.abrir()
        arq = os.path.join(self.pasta, "p.xlsx")
        criar_xlsx(arq, [["Cliente", "CNPJ", "Praça"], ["Nova A", 11222333000181, "RJ"], ["Nova B", "", "SP"]])
        with mock.patch("interface.clientes_cnpj.filedialog.askopenfilename", lambda **k: arq), \
                mock.patch("interface.clientes_cnpj.messagebox.askyesnocancel", lambda *a, **k: False):
            j.importar()                                         # NAO = acrescentar
        self.assertEqual(tab.total_linhas(), 5)
        with mock.patch("interface.clientes_cnpj.filedialog.askopenfilename", lambda **k: arq), \
                mock.patch("interface.clientes_cnpj.messagebox.askyesnocancel", lambda *a, **k: True):
            j.importar()                                         # SIM = substituir
        self.assertEqual(tab.total_linhas(), 2)
        self.assertEqual([c["nome"] for c in tab.listar_colunas()], ["Cliente", "CNPJ", "Praça"])
        self.assertEqual(len(j.tree.get_children()), 2)
        self.app.desfazer_ultima_alteracao()                     # volta ao que havia antes da substituicao
        self.assertEqual(tab.total_linhas(), 5)

    def test_filtro(self):
        self.popular()
        j = self.abrir()
        j.var_filtro.set("alfa")
        self.assertEqual(len(j.tree.get_children()), 1)

    def test_adicionar_nota_pela_tela_preserva_o_formulario_principal(self):
        self.popular()
        self.app.var_nf.set("555")                              # usuario estava digitando na tela principal
        self.app.var_cliente.set("Rascunho")
        j = self.abrir()
        j.tree.selection_set(j.tree.get_children()[0])
        j._ao_selecionar()
        self.assertEqual(j.var_nota_cliente.get(), "Zeta Ltda")
        j.var_nota_nf.set("8001")
        j.var_nota_oc.set("REENTREGA")
        j.var_nota_sigla.set("SP")
        j.adicionar_nota()
        self.app.update()
        nota = self.nota_por_nf(8001, "ZETA LTDA")        # o sistema grava em maiúsculas
        self.assertIsNotNone(nota)
        self.assertEqual((nota["ocorrencia"], nota["sigla"]), ("REENTREGA", "SP"))
        self.assertEqual(j.var_nota_nf.get(), "")               # pronto para a proxima NF
        self.assertEqual((self.app.var_nf.get(), self.app.var_cliente.get()), ("555", "Rascunho"))

    def test_nome_com_anotacao_vira_nome_limpo_na_nota(self):
        c = {x["nome"]: x["id"] for x in tab.listar_colunas()}
        tab.adicionar_linha({c["Cliente"]: "Empresa Exemplo/ não possui isenção"})
        j = self.abrir()
        j.tree.selection_set(j.tree.get_children()[0])
        j._ao_selecionar()
        self.assertEqual(j.var_nota_cliente.get(), "Empresa Exemplo")


if __name__ == "__main__":
    unittest.main()
