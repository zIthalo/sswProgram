# -*- coding: utf-8 -*-
"""
dialogs.py
Janelas de dialogo (popups) reutilizaveis pela aplicacao principal.
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox

import dateutils


class PerguntaMorosidade(tk.Toplevel):
    """
    Popup unico exibido ao marcar uma nota como resolvida: pergunta quem demorou
    mais para resolver o caso.
    Atalhos: 'U' = Unidade | 'C' = Cliente | Enter = Sem morosidade | Esc = cancela
    Resultado fica em self.resultado: 'unidade' | 'cliente' | 'nenhum' | None (cancelado)
    """

    def __init__(self, master, nf, dias, horas):
        super().__init__(master)
        self.title("Resolução da NF %s" % nf)
        self.resizable(False, False)
        self.resultado = None
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        partes_tempo = []
        if dias:
            partes_tempo.append("%d dia(s)" % dias)
        partes_tempo.append("%d hora(s)" % horas)
        tempo_str = " e ".join(partes_tempo)

        ttk.Label(
            frame,
            text="A NF %s levou %s para ser resolvida.\nQuem demorou mais para resolver?"
                 % (nf, tempo_str),
            wraplength=380, justify="left"
        ).pack(pady=(0, 12))

        botoes = ttk.Frame(frame)
        botoes.pack()
        ttk.Button(botoes, text="Unidade (U)", command=self._unidade).pack(side="left", padx=6)
        ttk.Button(botoes, text="Cliente (C)", command=self._cliente).pack(side="left", padx=6)
        ttk.Button(botoes, text="Sem morosidade (Enter)", command=self._nenhum).pack(side="left", padx=6)

        self.bind("<Return>", lambda e: self._nenhum())
        self.bind("u", lambda e: self._unidade())
        self.bind("U", lambda e: self._unidade())
        self.bind("c", lambda e: self._cliente())
        self.bind("C", lambda e: self._cliente())
        self.bind("<Escape>", self._cancelar)

        self.protocol("WM_DELETE_WINDOW", lambda: self._cancelar())
        self.transient(master)
        self.update_idletasks()
        self.geometry("+%d+%d" % (master.winfo_rootx() + 60, master.winfo_rooty() + 60))
        self.focus_force()
        self.wait_window(self)

    def _unidade(self):
        self.resultado = "unidade"
        self.destroy()

    def _cliente(self):
        self.resultado = "cliente"
        self.destroy()

    def _nenhum(self):
        self.resultado = "nenhum"
        self.destroy()

    def _cancelar(self, event=None):
        self.resultado = None
        self.destroy()


def fluxo_marcar_resolvido(master, nota_row):
    """
    Executa o fluxo de 'Marcar como resolvido': calcula automaticamente os dias e
    horas que a NF ficou em tratativas (sem perguntar ao usuario) e pergunta apenas
    quem demorou mais para resolver o caso (unidade, cliente ou ninguem).

    Retorna dict com os dados para salvar no historico, ou None se o usuario cancelar.
    """
    nf = nota_row["nf_numero"]
    dias, horas = dateutils.calcular_dias_horas(nota_row["criado_em"])

    popup = PerguntaMorosidade(master, nf, dias, horas)
    if popup.resultado is None:
        return None

    return {
        "nf_numero": nf, "cliente": nota_row["cliente"], "ocorrencia": nota_row["ocorrencia"],
        "sigla": nota_row["sigla"], "dias": dias, "horas": horas, "morosidade": popup.resultado,
    }


def editar_campo_texto(master, titulo, rotulo, valor_atual):
    return simpledialog.askstring(titulo, rotulo, initialvalue=valor_atual, parent=master)


class GerenciarLista(tk.Toplevel):
    """
    Janela generica para gerenciar listas editaveis (empresas parceiras / tipos de ocorrencia).
    Recebe funcoes de listar, adicionar e remover.
    """

    def __init__(self, master, titulo, listar_fn, adicionar_fn, remover_fn, permitir_remover_todos=True):
        super().__init__(master)
        self.title(titulo)
        self.geometry("360x400")
        self.listar_fn = listar_fn
        self.adicionar_fn = adicionar_fn
        self.remover_fn = remover_fn
        self.permitir_remover_todos = permitir_remover_todos

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        self.listbox = tk.Listbox(frame)
        self.listbox.pack(fill="both", expand=True, pady=(0, 8))

        linha = ttk.Frame(frame)
        linha.pack(fill="x")
        self.var_novo = tk.StringVar()
        ttk.Entry(linha, textvariable=self.var_novo).pack(side="left", fill="x", expand=True)
        ttk.Button(linha, text="Adicionar", command=self._adicionar).pack(side="left", padx=(6, 0))
        ttk.Button(frame, text="Remover selecionado", command=self._remover).pack(fill="x", pady=(8, 0))

        self._recarregar()
        self.transient(master)

    def _recarregar(self):
        self.listbox.delete(0, tk.END)
        for item in self.listar_fn():
            self.listbox.insert(tk.END, item)

    def _adicionar(self):
        nome = self.var_novo.get().strip().upper()
        if not nome:
            return
        ok = self.adicionar_fn(nome)
        if not ok:
            messagebox.showwarning("Já existe", "'%s' já está cadastrado." % nome, parent=self)
        self.var_novo.set("")
        self._recarregar()

    def _remover(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        nome = self.listbox.get(sel[0])
        if not self.permitir_remover_todos and self.listbox.size() <= 1:
            messagebox.showwarning("Ação bloqueada", "É necessário manter ao menos um item.", parent=self)
            return
        self.remover_fn(nome)
        self._recarregar()
