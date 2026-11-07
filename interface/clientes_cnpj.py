# -*- coding: utf-8 -*-
"""
Tela "Clientes e CNPJ" (menu Relatorio): tabela totalmente editavel.

- Duplo clique (ou F2) edita a celula; Enter salva, Esc cancela.
- Clicar numa celula de coluna do tipo CNPJ copia o numero (so os digitos).
- Clicar no titulo de uma coluna ordena (e a nova ordem fica gravada); botao direito no titulo:
  renomear, mover, excluir, mudar o tipo.
- Linhas: adicionar (abaixo da selecionada), excluir, mover para cima/baixo.
- Importar planilha .xlsx; filtro por texto; criar nota para o cliente selecionado.
Tudo e gravado na hora no banco (dados do usuario; nada de cliente vem com o programa).
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from interface import tema
from interface.dialogs import pedir_texto_atualizacao
from nucleo import database as db
from nucleo import tabela_clientes as tab

ROTULO_TIPO = {tab.TIPO_CLIENTE: "Cliente", tab.TIPO_CNPJ: "copia ao clicar", tab.TIPO_TEXTO: ""}


class JanelaClientesCnpj(tk.Toplevel):
    def __init__(self, app):
        tk.Toplevel.__init__(self, app)
        self.app = app
        self.title("Clientes e CNPJ")
        self.geometry("1020x640")
        self.minsize(640, 460)
        self.colunas = []
        self.linhas = {}               # iid (str) -> {"id", "valores"}
        self._ordem_ids = []           # ids de TODAS as linhas, na ordem gravada
        self._ordenacao = None         # (coluna_id, crescente)
        self._editor = None
        self._celula = None            # (iid, coluna_id) da ultima celula clicada

        self._montar()
        self.recarregar()
        self.widget_foco = self.var_filtro_entry

    # ------------------------------------------------------------------
    # Montagem
    # ------------------------------------------------------------------
    def _montar(self):
        corpo = ttk.Frame(self, padding=(12, 10, 12, 10))
        corpo.pack(fill="both", expand=True)
        corpo.rowconfigure(2, weight=1)
        corpo.columnconfigure(0, weight=1)
        self.bind("<Configure>", self._ao_redimensionar, add="+")

        barra = ttk.Frame(corpo)
        barra.grid(row=0, column=0, columnspan=2, sticky="ew")
        for texto, comando in (("+ Linha", self.nova_linha), ("Excluir linha", self.excluir_linha),
                               ("▲", lambda: self.mover_linha(-1)), ("▼", lambda: self.mover_linha(1)),
                               ("+ Coluna", self.nova_coluna), ("Importar Excel...", self.importar),
                               ("Remover tabela", self.remover_tabela)):
            b = ttk.Button(barra, text=texto, command=comando, width=3 if texto in "▲▼" else None)
            b.pack(side="left", padx=(0, 6))
        self.var_filtro = tk.StringVar()
        filtro = ttk.Frame(corpo)
        filtro.grid(row=1, column=1, sticky="e", pady=(6, 6))
        ttk.Label(filtro, text="Filtrar:").pack(side="left", padx=(0, 6))
        self.var_filtro_entry = ttk.Entry(filtro, textvariable=self.var_filtro, width=22)
        self.var_filtro_entry.pack(side="left")
        self.var_filtro.trace_add("write", lambda *a: self._preencher())

        self.lbl_dica = ttk.Label(corpo, text="Duplo clique edita a célula • clique num CNPJ copia o número • "
                                  "clique no título ordena • botão direito no título: renomear, mover, excluir",
                                  foreground=tema.PALETA["suave"], wraplength=700, justify="left")
        self.lbl_dica.grid(row=1, column=0, sticky="w", pady=(6, 6))

        self.tree = ttk.Treeview(corpo, show="headings", selectmode="browse")
        sy = ttk.Scrollbar(corpo, orient="vertical", command=self.tree.yview)
        sx = ttk.Scrollbar(corpo, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.grid(row=2, column=0, sticky="nsew")
        sy.grid(row=2, column=1, sticky="ns")
        sx.grid(row=3, column=0, sticky="ew")
        self.tree.bind("<Button-1>", self._clique)
        self.tree.bind("<Double-Button-1>", self._duplo_clique)
        self.tree.bind("<Button-3>", self._menu_contexto)
        self.tree.bind("<<TreeviewSelect>>", self._ao_selecionar)
        self.tree.bind("<Control-z>", lambda e: self.app.desfazer_ultima_alteracao())
        self.tree.bind("<Control-Z>", lambda e: self.app.desfazer_ultima_alteracao())
        self.tree.bind("<F2>", lambda e: self._editar_celula_atual())
        self.tree.bind("<Delete>", lambda e: self.excluir_linha())
        self.tree.bind("<Control-Up>", lambda e: self.mover_linha(-1))
        self.tree.bind("<Control-Down>", lambda e: self.mover_linha(1))

        # --- nova nota para o cliente selecionado
        caixa = ttk.LabelFrame(corpo, text="Nova nota para o cliente selecionado", padding=(10, 6, 10, 8))
        caixa.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        self.var_nota_cliente = tk.StringVar()
        self.var_nota_nf = tk.StringVar()
        self.var_nota_oc = tk.StringVar()
        self.var_nota_sigla = tk.StringVar()
        campos = (("Cliente", self.var_nota_cliente, None, 30), ("NF", self.var_nota_nf, None, 12),
                  ("Ocorrência", self.var_nota_oc, "oc", 20), ("Sigla destino", self.var_nota_sigla, "sigla", 12))
        for c, (rotulo, var, lista, largura) in enumerate(campos):
            ttk.Label(caixa, text=rotulo).grid(row=0, column=c, sticky="w", padx=(0 if c == 0 else 8, 0))
            if lista:
                w = ttk.Combobox(caixa, textvariable=var, width=largura)
            else:
                w = ttk.Entry(caixa, textvariable=var, width=largura)
            w.grid(row=1, column=c, sticky="ew", padx=(0 if c == 0 else 8, 0))
            if lista == "oc":
                self.combo_oc = w
            elif lista == "sigla":
                self.combo_sigla = w
            elif rotulo == "NF":
                self.entry_nf = w
        caixa.columnconfigure(0, weight=3)
        caixa.columnconfigure(2, weight=2)
        self.btn_nota = ttk.Button(caixa, text="Adicionar nota", style="Acento.TButton", command=self.adicionar_nota)
        self.btn_nota.grid(row=1, column=4, padx=(10, 0))
        self.entry_nf.bind("<Return>", lambda e: self.adicionar_nota())
        self.combo_sigla.bind("<Return>", lambda e: self.adicionar_nota())
        self._atualizar_listas_nota()
        self.bind("<Escape>", lambda e: self._cancelar_edicao() or None)

    def _atualizar_listas_nota(self):
        self.combo_oc["values"] = db.listar_tipos_ocorrencia()
        self.combo_sigla["values"] = db.listar_empresas_parceiras()

    # ------------------------------------------------------------------
    # Dados -> tela
    # ------------------------------------------------------------------
    def recarregar(self):
        """Le colunas e linhas do banco e redesenha a tabela."""
        self._cancelar_edicao()
        self.colunas = tab.listar_colunas()
        self._todas = tab.listar_linhas()
        self._ordem_ids = [l["id"] for l in self._todas]
        self.tree["columns"] = [str(c["id"]) for c in self.colunas]
        ultima = self.colunas[-1]["id"]
        for c in self.colunas:
            self.tree.heading(str(c["id"]), text=self._titulo(c), command=lambda cid=c["id"]: self.ordenar(cid))
            self.tree.column(str(c["id"]), width=self._largura(c), minwidth=60, stretch=(c["id"] == ultima),
                             anchor="w")
        self._preencher()

    def _titulo(self, coluna):
        seta = ""
        if self._ordenacao and self._ordenacao[0] == coluna["id"]:
            seta = "  ▲" if self._ordenacao[1] else "  ▼"
        marca = "  ⧉" if coluna["tipo"] == tab.TIPO_CNPJ else ""
        return coluna["nome"] + marca + seta

    def _largura(self, coluna):
        base = len(coluna["nome"]) + 6
        for l in getattr(self, "_todas", []):
            base = max(base, min(len(l["valores"].get(coluna["id"], "")) + 2, 60))
        if coluna["tipo"] == tab.TIPO_CNPJ:
            base = max(base, 20)
        return max(90, min(base * 8, 460))

    def _valor_exibido(self, coluna, valor):
        return tab.formatar_cnpj(valor) if coluna["tipo"] == tab.TIPO_CNPJ else valor

    def _preencher(self):
        selecionada = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        self.linhas = {}
        filtro = self.var_filtro.get().strip().casefold()
        for linha in self._todas:
            if filtro and not any(filtro in v.casefold() for v in linha["valores"].values()):
                continue
            iid = str(linha["id"])
            self.linhas[iid] = linha
            self.tree.insert("", "end", iid=iid, values=[
                self._valor_exibido(c, linha["valores"].get(c["id"], "")) for c in self.colunas])
        if selecionada and selecionada[0] in self.linhas:
            self.tree.selection_set(selecionada[0])

    def _coluna_do_evento(self, event):
        """Coluna (dict) sob o ponteiro, ou None."""
        ident = self.tree.identify_column(event.x)
        try:
            return self.colunas[int(ident.lstrip("#")) - 1]
        except (ValueError, IndexError):
            return None

    # ------------------------------------------------------------------
    # Cliques
    # ------------------------------------------------------------------
    def _clique(self, event):
        self._salvar_edicao()
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        iid = self.tree.identify_row(event.y)
        coluna = self._coluna_do_evento(event)
        if not iid or coluna is None:
            return
        self._celula = (iid, coluna["id"])
        if coluna["tipo"] == tab.TIPO_CNPJ:
            valor = self.linhas[iid]["valores"].get(coluna["id"], "")
            if valor:
                self.clipboard_clear()
                self.clipboard_append(tab.texto_para_copiar(valor))
                self.update()
                self.app.mostrar_mensagem_flutuante("CNPJ copiado!")

    def _duplo_clique(self, event):
        if self.tree.identify_region(event.x, event.y) == "cell":
            self._editar_celula_atual()
            return "break"

    def _ao_selecionar(self, event=None):
        sel = self.tree.selection()
        if sel and sel[0] in self.linhas:
            col = next((c for c in self.colunas if c["tipo"] == tab.TIPO_CLIENTE), None)
            if col:
                nome = self.linhas[sel[0]]["valores"].get(col["id"], "")
                self.var_nota_cliente.set(tab.nome_para_nota(nome))

    # ------------------------------------------------------------------
    # Edicao de celula
    # ------------------------------------------------------------------
    def _editar_celula_atual(self):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        if self._celula and self._celula[0] == iid:
            coluna_id = self._celula[1]
        else:
            coluna_id = next((c["id"] for c in self.colunas if c["tipo"] == tab.TIPO_CLIENTE), self.colunas[0]["id"])
        self._iniciar_edicao(iid, coluna_id)

    def _iniciar_edicao(self, iid, coluna_id):
        self._cancelar_edicao()
        coluna = next(c for c in self.colunas if c["id"] == coluna_id)
        self.tree.see(iid)
        self.update_idletasks()
        caixa = self.tree.bbox(iid, str(coluna_id))
        if not caixa:
            return
        x, y, w, h = caixa
        var = tk.StringVar(value=self.linhas[iid]["valores"].get(coluna_id, ""))
        ed = ttk.Entry(self.tree, textvariable=var)
        ed.place(x=x, y=y, width=max(w, 120), height=h)
        ed.focus_set()
        ed.select_range(0, "end")
        ed.bind("<Return>", lambda e: self._salvar_edicao())
        ed.bind("<Escape>", lambda e: self._cancelar_edicao() or "break")
        ed.bind("<FocusOut>", lambda e: self._salvar_edicao())
        self._editor = (ed, var, iid, coluna)

    def _salvar_edicao(self):
        if not self._editor:
            return
        ed, var, iid, coluna = self._editor
        self._editor = None
        texto = var.get()
        ed.destroy()
        if iid not in self.linhas:
            return
        linha = self.linhas[iid]
        if texto.strip() == linha["valores"].get(coluna["id"], ""):
            return
        gravado = tab.salvar_celula(linha["id"], coluna["id"], texto)
        linha["valores"][coluna["id"]] = gravado
        self.tree.set(iid, str(coluna["id"]), self._valor_exibido(coluna, gravado))
        self._ao_selecionar()

    def _cancelar_edicao(self):
        if self._editor:
            ed = self._editor[0]
            self._editor = None
            try:
                ed.destroy()
            except tk.TclError:
                pass

    # ------------------------------------------------------------------
    # Linhas
    # ------------------------------------------------------------------
    def nova_linha(self):
        sel = self.tree.selection()
        linha_id = tab.adicionar_linha(depois_de=int(sel[0]) if sel else None)
        self.var_filtro.set("")
        self.recarregar()
        iid = str(linha_id)
        self.tree.selection_set(iid)
        self.tree.see(iid)
        col = next(c for c in self.colunas if c["tipo"] == tab.TIPO_CLIENTE)
        self._celula = (iid, col["id"])
        self.after(50, lambda: self._iniciar_edicao(iid, col["id"]))

    def excluir_linha(self):
        sel = self.tree.selection()
        if not sel or self._editor:
            return
        linha = self.linhas[sel[0]]
        col = next((c for c in self.colunas if c["tipo"] == tab.TIPO_CLIENTE), None)
        nome = linha["valores"].get(col["id"], "") if col else ""
        if not messagebox.askyesno("Excluir linha", "Excluir a linha \"%s\" da tabela?" % (nome or "(vazia)"),
                                   parent=self):
            return
        tab.remover_linha(linha["id"])
        self.recarregar()

    def mover_linha(self, delta):
        sel = self.tree.selection()
        if not sel:
            return
        visiveis = [int(i) for i in self.tree.get_children()]
        atual = int(sel[0])
        i = visiveis.index(atual)
        j = i + delta
        if not 0 <= j < len(visiveis):
            return
        ordem = list(self._ordem_ids)
        a, b = ordem.index(atual), ordem.index(visiveis[j])
        ordem[a], ordem[b] = ordem[b], ordem[a]
        tab.reordenar_linhas(ordem)
        self._ordenacao = None
        self.recarregar()
        self.tree.selection_set(sel[0])
        self.tree.see(sel[0])

    def ordenar(self, coluna_id):
        """Ordena por esta coluna (clicar de novo inverte) e GRAVA a nova ordem."""
        crescente = not (self._ordenacao and self._ordenacao[0] == coluna_id and self._ordenacao[1])
        ordenadas = sorted(self._todas, key=lambda l: tab.chave_ordenacao(l["valores"].get(coluna_id, "")),
                           reverse=not crescente)
        # linhas com a celula vazia ficam sempre no fim
        ordenadas = [l for l in ordenadas if l["valores"].get(coluna_id)] + \
                    [l for l in ordenadas if not l["valores"].get(coluna_id)]
        tab.reordenar_linhas([l["id"] for l in ordenadas])
        self._ordenacao = (coluna_id, crescente)
        self.recarregar()

    # ------------------------------------------------------------------
    # Colunas
    # ------------------------------------------------------------------
    def nova_coluna(self):
        nome = pedir_texto_atualizacao(self, "Nova coluna", "Nome da nova coluna:")
        if nome is None or not nome.strip():
            return
        try:
            tab.adicionar_coluna(nome)
        except tab.TabelaClientesErro as e:
            messagebox.showerror("Nova coluna", str(e), parent=self)
            return
        self.recarregar()

    def renomear_coluna(self, coluna):
        nome = pedir_texto_atualizacao(self, "Renomear coluna", "Novo nome da coluna:", coluna["nome"])
        if nome is None or not nome.strip() or nome.strip() == coluna["nome"]:
            return
        try:
            tab.renomear_coluna(coluna["id"], nome)
        except tab.TabelaClientesErro as e:
            messagebox.showerror("Renomear coluna", str(e), parent=self)
            return
        self.recarregar()

    def excluir_coluna(self, coluna):
        if not messagebox.askyesno(
                "Excluir coluna", "Excluir a coluna \"%s\"?\nTodos os dados dela serão apagados." % coluna["nome"],
                parent=self):
            return
        try:
            tab.remover_coluna(coluna["id"])
        except tab.TabelaClientesErro as e:
            messagebox.showerror("Excluir coluna", str(e), parent=self)
            return
        self.recarregar()

    def mover_coluna(self, coluna, delta):
        if tab.mover_coluna(coluna["id"], delta):
            self.recarregar()

    def alternar_cnpj(self, coluna):
        novo = tab.TIPO_TEXTO if coluna["tipo"] == tab.TIPO_CNPJ else tab.TIPO_CNPJ
        try:
            tab.definir_tipo_coluna(coluna["id"], novo)
        except tab.TabelaClientesErro as e:
            messagebox.showerror("Coluna", str(e), parent=self)
            return
        self.recarregar()

    def _menu_contexto(self, event):
        regiao = self.tree.identify_region(event.x, event.y)
        coluna = self._coluna_do_evento(event)
        menu = tk.Menu(self, tearoff=0)
        if regiao == "heading" and coluna:
            menu.add_command(label="Renomear coluna...", command=lambda: self.renomear_coluna(coluna))
            menu.add_command(label="Mover para a esquerda", command=lambda: self.mover_coluna(coluna, -1))
            menu.add_command(label="Mover para a direita", command=lambda: self.mover_coluna(coluna, 1))
            if coluna["tipo"] != tab.TIPO_CLIENTE:
                menu.add_checkbutton(label="Copiar valor ao clicar (CNPJ)", onvalue=True, offvalue=False,
                                     variable=tk.BooleanVar(value=coluna["tipo"] == tab.TIPO_CNPJ),
                                     command=lambda: self.alternar_cnpj(coluna))
                menu.add_command(label="Usar como nome do cliente",
                                 command=lambda: self._definir_cliente(coluna))
                menu.add_separator()
                menu.add_command(label="Excluir coluna...", command=lambda: self.excluir_coluna(coluna))
        elif regiao == "cell" and coluna:
            iid = self.tree.identify_row(event.y)
            self.tree.selection_set(iid)
            self._celula = (iid, coluna["id"])
            valor = self.linhas[iid]["valores"].get(coluna["id"], "")
            menu.add_command(label="Copiar", command=lambda: self._copiar_texto(valor))
            menu.add_command(label="Editar célula", command=lambda: self._iniciar_edicao(iid, coluna["id"]))
            menu.add_separator()
            menu.add_command(label="Nova linha abaixo", command=self.nova_linha)
            menu.add_command(label="Excluir linha...", command=self.excluir_linha)
        else:
            return
        menu.tk_popup(event.x_root, event.y_root)

    def _definir_cliente(self, coluna):
        try:
            tab.definir_tipo_coluna(coluna["id"], tab.TIPO_CLIENTE)
        except tab.TabelaClientesErro as e:
            messagebox.showerror("Coluna", str(e), parent=self)
            return
        self.recarregar()

    def _copiar_texto(self, texto):
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.update()
        self.app.mostrar_mensagem_flutuante("Copiado!")

    # ------------------------------------------------------------------
    # Importar planilha
    # ------------------------------------------------------------------
    def importar(self):
        """Importa uma planilha .xlsx. Com a tabela vazia, importa direto. Com dados na tabela,
        pergunta: SUBSTITUIR (a tabela fica igual a planilha) ou ACRESCENTAR ao final."""
        caminho = filedialog.askopenfilename(
            parent=self, title="Importar clientes de uma planilha",
            filetypes=[("Planilha Excel (*.xlsx)", "*.xlsx"), ("Todos os arquivos", "*.*")])
        if not caminho:
            return
        substituir = True
        if self._todas:
            resposta = messagebox.askyesnocancel(
                "Importar planilha",
                "A tabela já tem %d linha(s).\n\nSIM = substituir a tabela atual pela planilha "
                "(fica exatamente como o Excel; dá para desfazer com Ctrl+Z)\n"
                "NÃO = acrescentar as linhas da planilha ao final, sem repetir clientes que já existem"
                % len(self._todas), parent=self)
            if resposta is None:
                return
            substituir = resposta
        foto = tab.tirar_foto()
        try:
            if substituir:
                n_col, n_lin = tab.substituir_por_xlsx(caminho)
                texto = "Tabela importada como está na planilha:\n%d coluna(s) e %d linha(s)." % (n_col, n_lin)
            else:
                adicionadas, ignoradas = tab.importar_xlsx(caminho)
                texto = ("%d cliente(s) adicionado(s).\n%d já existia(m) na tabela e foi(ram) ignorado(s)."
                         % (adicionadas, ignoradas))
        except tab.TabelaClientesErro as e:
            messagebox.showerror("Importar planilha", str(e), parent=self)
            return
        self._registrar_desfazer("importação da planilha", foto)
        self._ordenacao = None
        self.var_filtro.set("")
        self.recarregar()
        messagebox.showinfo("Importar planilha", texto, parent=self)

    def remover_tabela(self):
        """Apaga todas as linhas e colunas (a tabela volta vazia, com as colunas padrao)."""
        if not self._todas and len(self.colunas) <= len(tab.COLUNAS_PADRAO):
            messagebox.showinfo("Remover tabela", "A tabela já está vazia.", parent=self)
            return
        if not messagebox.askyesno(
                "Remover tabela",
                "Remover a tabela inteira?\n\n%d linha(s) e %d coluna(s) serão apagadas.\n"
                "(Dá para desfazer com Ctrl+Z.)" % (len(self._todas), len(self.colunas)),
                parent=self):
            return
        foto = tab.tirar_foto()
        tab.limpar_tabela()
        self._registrar_desfazer("remoção da tabela de clientes", foto)
        self._ordenacao = None
        self.var_filtro.set("")
        self.recarregar()

    def _registrar_desfazer(self, rotulo, foto):
        app = self.app

        def desfazer():
            tab.restaurar_foto(foto)
            janela = app._janelas_unicas.get("clientes_cnpj")
            try:
                if janela is not None and janela.winfo_exists():
                    janela.recarregar()
            except tk.TclError:
                pass
        app.pilha_desfazer.registrar(rotulo, desfazer)

    def _ao_redimensionar(self, event):
        if event.widget is self:
            self.lbl_dica.configure(wraplength=max(240, event.width - 330))

    # ------------------------------------------------------------------
    # Nova nota
    # ------------------------------------------------------------------
    def adicionar_nota(self):
        """Cria a nota pelo MESMO caminho do formulario principal (mesmas validacoes, avisos de
        duplicada, data de agendamento etc.). O que estava digitado no formulario principal e
        devolvido depois, para nada se perder."""
        app = self.app
        guardado = [v.get() for v in (app.var_nf, app.var_cliente, app.var_ocorrencia, app.var_sigla)]
        app.var_nf.set(self.var_nota_nf.get())
        app.var_cliente.set(self.var_nota_cliente.get())
        app.var_ocorrencia.set(self.var_nota_oc.get())
        app.var_sigla.set(self.var_nota_sigla.get())
        try:
            app._adicionar_nota()
            registrada = not app.var_nf.get() and not app.var_cliente.get()
        finally:
            for var, valor in zip((app.var_nf, app.var_cliente, app.var_ocorrencia, app.var_sigla), guardado):
                var.set(valor)
        if registrada:
            self.var_nota_nf.set("")
            self._atualizar_listas_nota()
        self._trazer_de_volta()
        self.entry_nf.focus_set()

    def _trazer_de_volta(self):
        try:
            self.lift()
            self.focus_force()
        except tk.TclError:
            pass
