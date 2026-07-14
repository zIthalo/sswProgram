# -*- coding: utf-8 -*-
"""
dialogs.py
Janelas de dialogo (popups) reutilizaveis pela aplicacao principal.
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from datetime import datetime

import dateutils


class PerguntaSimNao(tk.Toplevel):
    """
    Popup generico de pergunta Sim/Nao.
    Atalhos: Enter ou 'S' = Sim | 'N' ou Esc = Nao
    Resultado fica em self.resultado (True / False / None se fechado sem responder)
    """

    def __init__(self, master, titulo, pergunta):
        super().__init__(master)
        self.title(titulo)
        self.resizable(False, False)
        self.resultado = None
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=pergunta, wraplength=380, justify="left").pack(pady=(0, 12))

        botoes = ttk.Frame(frame)
        botoes.pack()
        ttk.Button(botoes, text="Sim (S)", command=self._sim).pack(side="left", padx=6)
        ttk.Button(botoes, text="Não (N)", command=self._nao).pack(side="left", padx=6)

        self.bind("<Return>", lambda e: self._sim())
        self.bind("s", lambda e: self._sim())
        self.bind("S", lambda e: self._sim())
        self.bind("n", lambda e: self._nao())
        self.bind("N", lambda e: self._nao())
        self.bind("<Escape>", lambda e: self._nao())

        self.protocol("WM_DELETE_WINDOW", self._nao)
        self.transient(master)
        self.update_idletasks()
        self._centralizar(master)
        self.focus_force()
        self.wait_window(self)

    def _centralizar(self, master):
        self.geometry("+%d+%d" % (
            master.winfo_rootx() + 60, master.winfo_rooty() + 60))

    def _sim(self):
        self.resultado = True
        self.destroy()

    def _nao(self):
        self.resultado = False
        self.destroy()


def perguntar_dias_no_sistema(master, titulo, texto_padrao):
    """Pede ao usuario para confirmar/informar a quantidade de dias em tratativas."""
    return simpledialog.askinteger(titulo, texto_padrao, parent=master, minvalue=0)


def fluxo_marcar_resolvido(master, nota_row, dias_em_tratativas):
    """
    Executa o fluxo completo de 'Marcar como resolvido' descrito no requisito:
    1) Unidade entregadora foi agil?
    2) Se nao, perguntar/confirmar quantidade de dias.
    3) Remetente foi agil?
    4) Se nao, perguntar/confirmar quantidade de dias e registrar no relatorio o nome
       do cliente e os dias que levou para auxiliar na solucao.

    Retorna dict com os dados para salvar no historico, ou None se o usuario cancelar.
    """
    nf = nota_row["nf_numero"]
    cliente = nota_row["cliente"]
    ocorrencia = nota_row["ocorrencia"]
    sigla = nota_row["sigla"]

    p1 = PerguntaSimNao(
        master, "Resolução da NF %s" % nf,
        "A unidade entregadora (%s) foi ágil na resolução do problema da NF %s?" % (sigla, nf)
    )
    if p1.resultado is None:
        return None
    unidade_agil = p1.resultado
    if unidade_agil:
        dias_unidade = dias_em_tratativas
    else:
        dias_unidade = perguntar_dias_no_sistema(
            master, "Dias em tratativas",
            "Confirme quantos dias a NF %s ficou em tratativas com a unidade %s:" % (nf, sigla)
        )
        if dias_unidade is None:
            dias_unidade = dias_em_tratativas

    p2 = PerguntaSimNao(
        master, "Resolução da NF %s" % nf,
        "O remetente (%s) foi ágil na solução do caso?" % cliente
    )
    if p2.resultado is None:
        return None
    remetente_agil = p2.resultado
    if remetente_agil:
        dias_remetente = dias_em_tratativas
    else:
        dias_remetente = perguntar_dias_no_sistema(
            master, "Dias em tratativas",
            "Confirme quantos dias o cliente %s levou para auxiliar na solução do problema:" % cliente
        )
        if dias_remetente is None:
            dias_remetente = dias_em_tratativas
        messagebox.showinfo(
            "Relatório atualizado",
            "O cliente %s levou %d dia(s) para auxiliar na solução do problema."
            % (cliente, dias_remetente)
        )

    return {
        "nf_numero": nf, "cliente": cliente, "ocorrencia": ocorrencia, "sigla": sigla,
        "dias_unidade": dias_unidade, "unidade_agil": unidade_agil,
        "dias_remetente": dias_remetente, "remetente_agil": remetente_agil,
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
        self.transient(master)
        self.update_idletasks()
        self.geometry("+%d+%d" % (master.winfo_rootx() + 80, master.winfo_rooty() + 80))

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
