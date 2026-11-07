# -*- coding: utf-8 -*-
"""
Formulario de nova nota e atalhos de teclado do formulario.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from nucleo import busca
from nucleo import database as db
from nucleo import dateutils
from nucleo import occorrencias as occ
from interface.nota_block import NotaBlock


class FormularioMixin:

    def _acionar_botao_adicionar(self, event=None):
        self.btn_adicionar.invoke()
        return "break"

    def _configurar_navegacao_setas(self):
        """Permite mover entre os campos/botões do topo (NF, Cliente, Ocorrência,
        Sigla, Adicionar nota, Buscar, Buscar, Filtrar por ocorrência e
        Limpar filtro) usando as setas ↑/↓."""
        ordem = [
            self.entry_nf, self.entry_cliente, self.entry_oc, self.combo_sigla,
            self.btn_adicionar, self.entry_busca, self.btn_buscar, self.combo_filtro,
            self.btn_limpar_filtro,
        ]

        def mover(indice, direcao):
            novo = indice + direcao
            if 0 <= novo < len(ordem):
                self._focar(ordem[novo])
            return "break"

        for indice, widget in enumerate(ordem):
            widget.bind("<Down>", lambda e, i=indice: mover(i, 1))
            widget.bind("<Up>", lambda e, i=indice: mover(i, -1))

    def _configurar_atalhos_edicao(self):
        """Adiciona Ctrl+Z (desfazer), Ctrl+Y (refazer), Ctrl+Backspace (apagar
        palavra anterior), Ctrl+Delete (apagar palavra seguinte) e Ctrl+F
        (focar a busca) aos campos de texto/combobox editáveis do sistema."""
        campos = [
            self.entry_nf, self.entry_cliente, self.entry_oc, self.combo_sigla,
            self.entry_busca, self.combo_filtro,
        ]
        for campo in campos:
            self._instalar_atalhos_edicao(campo)
            # Entry/Combobox do Tkinter tem um atalho padrao de Ctrl+F (mover o
            # cursor) que intercepta o evento antes de chegar ao bind_all da
            # janela — por isso precisa ser sobrescrito individualmente aqui.
            campo.bind("<Control-f>", self._focar_busca)

    def _instalar_atalhos_edicao(self, widget):
        widget._undo_stack = []
        widget._redo_stack = []
        widget._ultimo_valor_undo = widget.get()

        def registrar_mudanca(event=None):
            atual = widget.get()
            if atual != widget._ultimo_valor_undo:
                widget._undo_stack.append(widget._ultimo_valor_undo)
                if len(widget._undo_stack) > 100:
                    widget._undo_stack.pop(0)
                widget._redo_stack.clear()
                widget._ultimo_valor_undo = atual

        def desfazer(event=None):
            if widget._undo_stack:
                atual = widget.get()
                widget._redo_stack.append(atual)
                anterior = widget._undo_stack.pop()
                widget.delete(0, tk.END)
                widget.insert(0, anterior)
                widget._ultimo_valor_undo = anterior
            return "break"

        def refazer(event=None):
            if widget._redo_stack:
                atual = widget.get()
                widget._undo_stack.append(atual)
                proximo = widget._redo_stack.pop()
                widget.delete(0, tk.END)
                widget.insert(0, proximo)
                widget._ultimo_valor_undo = proximo
            return "break"

        widget.bind("<KeyRelease>", registrar_mudanca, add="+")
        widget.bind("<Control-z>", desfazer)
        widget.bind("<Control-Z>", desfazer)
        widget.bind("<Control-y>", refazer)
        widget.bind("<Control-Y>", refazer)
        widget.bind("<Control-BackSpace>", self._excluir_palavra_anterior)
        widget.bind("<Control-Delete>", self._excluir_palavra_seguinte)

    def _excluir_palavra_anterior(self, event):
        widget = event.widget
        texto = widget.get()
        pos = widget.index(tk.INSERT)
        i = pos
        while i > 0 and texto[i - 1] == " ":
            i -= 1
        while i > 0 and texto[i - 1] != " ":
            i -= 1
        widget.delete(i, pos)
        return "break"

    def _excluir_palavra_seguinte(self, event):
        widget = event.widget
        texto = widget.get()
        pos = widget.index(tk.INSERT)
        n = len(texto)
        i = pos
        while i < n and texto[i] == " ":
            i += 1
        while i < n and texto[i] != " ":
            i += 1
        widget.delete(pos, i)
        return "break"

    def _limpar_formulario(self, focar=True):
        """Esvazia todos os campos do formulario de nova nota (e as sugestoes)."""
        self.var_nf.set("")
        self.var_cliente.set("")
        self.var_ocorrencia.set("")
        self.var_sigla.set("")
        self._suggestion_var.set("")
        self._suggestion_cliente_var.set("")
        self._sugestao_atual = None
        self._sugestao_cliente_atual = None
        if focar:
            self.entry_nf.focus_set()

    def atalho_nova_nota(self, event=None):
        """Ctrl+N: limpa o formulario e leva o cursor ao campo da NF."""
        self._limpar_formulario()
        return "break"

    def atalho_atualizar_lista(self, event=None):
        """F5: recarrega a lista de notas a partir do banco."""
        self.recarregar_lista()
        self.mostrar_mensagem_flutuante("Lista atualizada")
        return "break"

    def _atualizar_combobox_sigla(self):
        empresas = db.listar_empresas_parceiras()
        self.combo_sigla["values"] = empresas

    def _focar(self, widget):
        widget.focus_set()
        if isinstance(widget, ttk.Entry):
            widget.select_range(0, tk.END)
        return "break"

    def _sugerir_cliente(self, event=None):
        texto = self.var_cliente.get()
        clientes = db.listar_clientes()
        sugestao = occ.sugerir_ocorrencia(texto, clientes)
        if sugestao and sugestao.lower() != texto.strip().lower():
            self._suggestion_cliente_var.set("Sugestão: %s (Enter/Tab para usar)" % sugestao)
            self._sugestao_cliente_atual = sugestao
        else:
            self._suggestion_cliente_var.set("")
            self._sugestao_cliente_atual = None

    def _aceitar_sugestao_cliente(self, event=None):
        if getattr(self, "_sugestao_cliente_atual", None):
            self.var_cliente.set(self._sugestao_cliente_atual)
            self.entry_cliente.icursor(tk.END)
            self._suggestion_cliente_var.set("")
            self._sugestao_cliente_atual = None
        self._focar(self.entry_oc)
        return "break"

    def _sugerir_ocorrencia(self, event=None):
        texto = self.var_ocorrencia.get()
        tipos = db.listar_tipos_ocorrencia()
        sugestao = occ.sugerir_ocorrencia(texto, tipos)
        if sugestao and sugestao.lower() != texto.strip().lower():
            self._suggestion_var.set("Sugestão: %s (Enter/Tab para usar)" % sugestao)
            self._sugestao_atual = sugestao
        else:
            self._suggestion_var.set("")
            self._sugestao_atual = None

    def _aceitar_sugestao_ocorrencia(self, event=None):
        if getattr(self, "_sugestao_atual", None):
            self.var_ocorrencia.set(self._sugestao_atual)
            self.entry_oc.icursor(tk.END)
            self._suggestion_var.set("")
            self._sugestao_atual = None
        self._focar(self.combo_sigla)
        return "break"

    def _adicionar_nota(self):
        try:
            nf = int(self.var_nf.get().strip())
        except ValueError:
            messagebox.showerror("Erro", "Número da NF inválido.")
            return

        cliente = self.var_cliente.get().strip().upper()
        if not cliente:
            messagebox.showerror("Erro", "Informe o cliente/remetente.")
            return

        # Regra de unicidade: nao pode haver duas NFs PENDENTES de tratativa
        # com o mesmo numero para o mesmo remetente. Uma nota ja resolvida
        # nao bloqueia: o usuario pode cadastrar a NF de novo. Checada aqui
        # ANTES de pedir ocorrencia/agendamento, para nao fazer o usuario
        # preencher o resto do formulario so para descobrir depois.
        existente = db.existe_nf_cliente(nf, cliente)
        if existente:
            messagebox.showerror("Nota Fiscal duplicada", db.MENSAGEM_NF_DUPLICADA)
            self.var_filtro.set(self.OPCAO_TODAS)
            self.recarregar_lista()
            self._destacar_nota(existente["id"])
            self._limpar_formulario()  # pronto para o usuario digitar a proxima ocorrencia
            return

        ocorrencia_digitada = self.var_ocorrencia.get().strip().upper()
        if not ocorrencia_digitada:
            messagebox.showerror("Erro", "Informe a ocorrência.")
            return

        tipos = db.listar_tipos_ocorrencia()
        sugestao = occ.sugerir_ocorrencia(ocorrencia_digitada, tipos)
        ocorrencia = (sugestao if sugestao else ocorrencia_digitada).upper()
        if ocorrencia.lower() not in [t.lower() for t in tipos]:
            if messagebox.askyesno(
                "Nova ocorrência",
                "'%s' não está cadastrada. Deseja cadastrar este novo tipo de ocorrência?" % ocorrencia
            ):
                db.adicionar_tipo_ocorrencia(ocorrencia)
            else:
                return

        sigla = self.var_sigla.get().strip().upper()
        if not sigla:
            messagebox.showerror("Erro", "Informe a sigla da unidade ou a empresa parceira.")
            return

        data_ocorrencia = dateutils.parse_data_usuario("0")

        agendamento_data = None
        if occ.eh_ocorrencia_agendamento(ocorrencia):
            agendamento_data = self._pedir_data_agendamento()
            if agendamento_data is None:
                return

        try:
            novo_id = db.inserir_nota(nf, cliente, ocorrencia, sigla, data_ocorrencia, agendamento_data)
        except db.NotaDuplicadaError:
            # Defesa contra concorrencia: a checagem existe_nf_cliente() acima
            # ja cobre o caso comum, mas se outra insercao da MESMA NF+remetente
            # tiver commitado entre essa checagem e este INSERT, o indice
            # UNIQUE do banco pega o caso e cai aqui.
            messagebox.showerror("Nota Fiscal duplicada", db.MENSAGEM_NF_DUPLICADA)
            self.recarregar_lista()
            self._limpar_formulario()
            return

        if cliente.lower() not in [c.lower() for c in db.listar_clientes()]:
            db.adicionar_cliente(cliente)

        self._garantir_visibilidade(cliente, sigla, ocorrencia)

        self._limpar_formulario(focar=False)

        filtro_atual = self.var_filtro.get() if hasattr(self, "var_filtro") else self.OPCAO_TODAS
        if filtro_atual.strip().upper() == "AGENDAMENTO":
            # Precisa reordenar pela data do agendamento: usa o caminho completo.
            self.recarregar_lista()
        else:
            # Caminho rápido: acrescenta só o bloco novo, sem reconstruir a
            # lista inteira (mantém a inserção rápida mesmo com muitas notas).
            self._adicionar_bloco_rapido(db.obter_nota(novo_id))
        self._focar(self.entry_nf)
        self.mostrar_mensagem_flutuante("Ocorrência registrada com sucesso.")

    def _adicionar_bloco_rapido(self, nota):
        """Acrescenta uma nota recém-inserida diretamente na tela, sem
        reconstruir todos os blocos existentes — a lista já fica ordenada por
        data de inserção, então a nota nova sempre entra no final."""
        bloco = NotaBlock(self.frame_lista, self, nota, [])
        bloco.pack(fill="x", pady=4, padx=2)
        self.blocos[nota["id"]] = bloco
        self.frame_lista.update_idletasks()
        bloco._ajustar_altura_cabecalho()
        self.atualizar_scrollregion()
        if hasattr(self, "combo_filtro"):
            self._atualizar_combobox_filtro()

    def _garantir_visibilidade(self, cliente, sigla, ocorrencia):
        """Limpa filtros ativos (por ocorrência ou por busca) que fariam uma
        nota recem-inserida ou editada ficar escondida da lista — sem isso, o
        usuário tinha a impressão de que a nota "sumiu" até fechar e reabrir
        o sistema."""
        if hasattr(self, "var_filtro"):
            filtro_atual = self.var_filtro.get()
            if filtro_atual != self.OPCAO_TODAS and filtro_atual.strip().lower() != ocorrencia.strip().lower():
                self.var_filtro.set(self.OPCAO_TODAS)

        if getattr(self, "filtro_busca_texto", ""):
            if not busca.nota_corresponde({"cliente": cliente, "sigla": sigla}, self.filtro_busca_texto,
                                          db.listar_siglas_conhecidas()):
                self.var_busca.set("")
                self.filtro_busca_texto = ""

        if getattr(self, "filtro_busca_ids", None) is not None:
            self.var_busca.set("")
            self.filtro_busca_ids = None

    # ------------------------------------------------------------------
    # Busca (Ctrl+F)
    # ------------------------------------------------------------------

