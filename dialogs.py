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


class PopupLembrete(tk.Toplevel):
    """
    Popup: "Você deseja ser lembrado da NF (...) em [100]?"
    O usuario pode editar o numero dentro dos colchetes.
    Retorna em self.codigo_final (int) e self.aceitou (bool), ou None se recusado/fechado.
    """

    def __init__(self, master, nf, ocorrencia, sigla, valor_inicial=100):
        super().__init__(master)
        self.title("Lembrete")
        self.resizable(False, False)
        self.aceitou = None
        self.codigo_final = None
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        texto = "Você deseja ser lembrado da NF (%s, %s, %s) em" % (nf, ocorrencia, sigla)
        ttk.Label(frame, text=texto, wraplength=380, justify="left").pack(anchor="w")

        linha = ttk.Frame(frame)
        linha.pack(pady=8, anchor="w")
        ttk.Label(linha, text="[").pack(side="left")
        self.var_valor = tk.StringVar(value=str(valor_inicial))
        entry = ttk.Entry(linha, textvariable=self.var_valor, width=6)
        entry.pack(side="left")
        ttk.Label(linha, text="] ?  (1-50 = minutos | 100-400 = horas, ex: 130 = 1h30, máx 400 = 4h)").pack(side="left")

        botoes = ttk.Frame(frame)
        botoes.pack(pady=(8, 0))
        ttk.Button(botoes, text="Sim (S)", command=self._sim).pack(side="left", padx=6)
        ttk.Button(botoes, text="Não (N/Esc)", command=self._nao).pack(side="left", padx=6)

        self.bind("<Return>", lambda e: self._sim())
        self.bind("<Escape>", lambda e: self._nao())
        entry.bind("s", lambda e: None)  # nao interceptar digitacao no campo
        self.bind("n", lambda e: self._nao_se_fora_do_campo(e))
        self.bind("N", lambda e: self._nao_se_fora_do_campo(e))

        self.protocol("WM_DELETE_WINDOW", self._nao)
        self.transient(master)
        entry.focus_set()
        entry.icursor(tk.END)
        self.update_idletasks()
        self.geometry("+%d+%d" % (master.winfo_rootx() + 60, master.winfo_rooty() + 60))
        self.wait_window(self)

    def _nao_se_fora_do_campo(self, event):
        if event.widget.winfo_class() != "TEntry":
            self._nao()

    def _sim(self):
        try:
            numero = int(self.var_valor.get())
            codigo, _delta = dateutils.normalizar_codigo_lembrete(numero)
        except (ValueError, TypeError):
            messagebox.showerror("Valor inválido", "Informe um número válido (1 a 400).", parent=self)
            return
        self.codigo_final = codigo
        self.aceitou = True
        self.destroy()

    def _nao(self):
        self.aceitou = False
        self.destroy()


class PopupAlerta(tk.Toplevel):
    """Popup simples de alerta informativo (lembretes disparados, agendamento, prioridade, etc.)."""

    def __init__(self, master, titulo, mensagem, com_verificado=False):
        super().__init__(master)
        self.title(titulo)
        self.resizable(False, False)
        self.verificado = False
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=mensagem, wraplength=380, justify="left").pack()

        botoes = ttk.Frame(frame)
        botoes.pack(pady=(12, 0))
        if com_verificado:
            ttk.Button(botoes, text="Nota já verificada", command=self._verificar).pack(side="left", padx=6)
        ttk.Button(botoes, text="OK", command=self.destroy).pack(side="left", padx=6)

        self.bind("<Return>", lambda e: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.transient(master)
        self.update_idletasks()
        self.geometry("+%d+%d" % (master.winfo_rootx() + 80, master.winfo_rooty() + 80))
        self.focus_force()
        # Bloqueia ate o usuario fechar este popup: evita que varios lembretes
        # disparados na mesma verificacao abram varias janelas modais ao mesmo
        # tempo (o que travava a aplicacao, exigindo finalizar pelo Gerenciador
        # de Tarefas).
        self.wait_window(self)

    def _verificar(self):
        self.verificado = True
        self.destroy()


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
