# -*- coding: utf-8 -*-
"""
dialogs.py
Janelas de dialogo (popups) reutilizaveis pela aplicacao principal.
"""

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, colorchooser

import aparencia
import dateutils
import occorrencias as occ


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


class CampoTextoComAtalhos(tk.Toplevel):
    """
    Dialogo de entrada de texto de uma linha com suporte a desfazer/refazer
    (Ctrl+Z / Ctrl+Y) e apagar a palavra inteira antes/depois do cursor
    (Ctrl+Backspace / Ctrl+Delete) — atalhos que o Entry padrao usado por
    simpledialog.askstring nao oferece (Entry nao tem pilha de desfazer).

    Usa um tk.Text de uma unica linha (height=1, wrap="none") em vez de
    Entry, pois soh o Text do Tkinter tem pilha de desfazer/refazer
    embutida (habilitada aqui via undo=True). Visualmente e no fluxo de
    uso (Enter confirma, Esc cancela) se comporta como o campo de uma
    linha anterior.

    Resultado fica em self.resultado: a string digitada, ou None se o
    usuario cancelar (Esc, botao Cancelar ou fechar a janela).
    """

    def __init__(self, master, titulo, rotulo, valor_inicial=""):
        super().__init__(master)
        self.title(titulo)
        self.resizable(False, False)
        self.resultado = None
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=rotulo, wraplength=380, justify="left").pack(anchor="w", pady=(0, 8))

        self.texto = tk.Text(frame, height=1, width=48, wrap="none", undo=True,
                              font=("Consolas", 10))
        self.texto.pack(fill="x")
        if valor_inicial:
            self.texto.insert("1.0", valor_inicial)
        self.texto.edit_reset()  # o preenchimento inicial nao deve entrar na pilha de desfazer
        self.texto.mark_set("insert", "end")
        self.texto.focus_set()

        botoes = ttk.Frame(frame)
        botoes.pack(fill="x", pady=(12, 0))
        ttk.Button(botoes, text="OK", command=self._confirmar).pack(side="right")
        ttk.Button(botoes, text="Cancelar", command=self._cancelar).pack(side="right", padx=(0, 6))

        self.texto.bind("<Return>", self._confirmar)
        self.texto.bind("<KP_Enter>", self._confirmar)
        self.texto.bind("<Escape>", self._cancelar)
        self.texto.bind("<Control-z>", self._desfazer)
        self.texto.bind("<Control-Z>", self._desfazer)
        self.texto.bind("<Control-y>", self._refazer)
        self.texto.bind("<Control-Y>", self._refazer)
        self.texto.bind("<Control-BackSpace>", self._apagar_palavra_tras)
        self.texto.bind("<Control-Delete>", self._apagar_palavra_frente)

        self.protocol("WM_DELETE_WINDOW", self._cancelar)
        self.transient(master)
        self.update_idletasks()
        largura = self.winfo_reqwidth()
        altura = self.winfo_reqheight()
        pos_x = master.winfo_rootx() + (master.winfo_width() // 2) - (largura // 2)
        pos_y = master.winfo_rooty() + (master.winfo_height() // 2) - (altura // 2)
        self.geometry("+%d+%d" % (max(pos_x, 0), max(pos_y, 0)))
        self.wait_window(self)

    def _confirmar(self, event=None):
        self.resultado = self.texto.get("1.0", "end-1c")
        self.destroy()
        return "break"

    def _cancelar(self, event=None):
        self.resultado = None
        self.destroy()
        return "break"

    def _desfazer(self, event=None):
        try:
            self.texto.edit_undo()
        except tk.TclError:
            pass  # pilha de desfazer vazia; nada a fazer
        return "break"

    def _refazer(self, event=None):
        try:
            self.texto.edit_redo()
        except tk.TclError:
            pass  # pilha de refazer vazia; nada a fazer
        return "break"

    def _apagar_palavra_tras(self, event=None):
        inicio = self.texto.index("insert -1c wordstart")
        self.texto.delete(inicio, "insert")
        return "break"

    def _apagar_palavra_frente(self, event=None):
        fim = self.texto.index("insert wordend")
        self.texto.delete("insert", fim)
        return "break"


def pedir_texto_atualizacao(master, titulo, rotulo, valor_inicial=""):
    """Usada no lugar de simpledialog.askstring onde o usuario precisa de
    desfazer/refazer (Ctrl+Z/Ctrl+Y) e apagar palavra inteira
    (Ctrl+Backspace/Ctrl+Delete) — recursos que o Entry padrao nao oferece."""
    return CampoTextoComAtalhos(master, titulo, rotulo, valor_inicial).resultado


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


class JanelaAparencia(tk.Toplevel):
    """
    Tela de personalização: cor da fonte, cor de fundo e cor de seleção dos
    blocos de nota, e quais campos do cabeçalho ficam em negrito.

    Resultado: self.acao = 'salvar' (com self.config_resultado preenchido),
    'restaurar' (voltar ao padrão de fábrica) ou None (cancelado).
    """

    def __init__(self, master, config_atual):
        super().__init__(master)
        self.title("Aparência")
        self.resizable(False, False)
        self.acao = None
        self.config_resultado = None
        self._cores = {
            "cor_fonte": config_atual["cor_fonte"],
            "cor_fundo": config_atual["cor_fundo"],
            "cor_selecao": config_atual["cor_selecao"],
        }
        self.grab_set()

        frame = ttk.Frame(self, padding=14)
        frame.pack(fill="both", expand=True)

        self._amostras = {}
        linhas = [("cor_fonte", "Cor da fonte:", ""),
                  ("cor_fundo", "Cor de fundo:", ""),
                  ("cor_selecao", "Cor da nota selecionada:", aparencia.COR_SELECAO_PADRAO)]
        for i, (chave, rotulo, padrao) in enumerate(linhas):
            ttk.Label(frame, text=rotulo).grid(row=i, column=0, sticky="w", pady=3)
            amostra = tk.Label(frame, width=18, relief="sunken", borderwidth=1)
            amostra.grid(row=i, column=1, padx=8, pady=3)
            self._amostras[chave] = amostra
            ttk.Button(frame, text="Escolher...",
                       command=lambda c=chave: self._escolher(c)).grid(row=i, column=2, padx=(0, 4))
            ttk.Button(frame, text="Padrão",
                       command=lambda c=chave, p=padrao: self._definir(c, p)).grid(row=i, column=3)

        caixa = ttk.LabelFrame(frame, text="Campos em negrito no cabeçalho da nota", padding=8)
        caixa.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(12, 8))
        self._vars_negrito = {}
        for i, (campo, rotulo) in enumerate(aparencia.CAMPOS_NEGRITO):
            var = tk.BooleanVar(value=config_atual["negrito"].get(campo, False))
            var.trace_add("write", lambda *_: self._atualizar_previa())
            self._vars_negrito[campo] = var
            ttk.Checkbutton(caixa, text=rotulo, variable=var).grid(
                row=i // 2, column=i % 2, sticky="w", padx=8, pady=1)

        ttk.Label(frame, text="Pré-visualização:").grid(row=4, column=0, sticky="w")
        self._previa = tk.Text(frame, height=2, width=58, wrap="word", borderwidth=1, relief="solid",
                               font=("Consolas", 9))
        self._previa.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(2, 10))

        botoes = ttk.Frame(frame)
        botoes.grid(row=6, column=0, columnspan=4, sticky="ew")
        ttk.Button(botoes, text="Restaurar padrão de fábrica", command=self._restaurar).pack(side="left")
        ttk.Button(botoes, text="Salvar", command=self._salvar).pack(side="right")
        ttk.Button(botoes, text="Cancelar", command=self._cancelar).pack(side="right", padx=(0, 6))

        self.bind("<Escape>", lambda e: self._cancelar())
        self.protocol("WM_DELETE_WINDOW", self._cancelar)
        for chave in self._cores:
            self._atualizar_amostra(chave)
        self._atualizar_previa()

        self.transient(master)
        self.update_idletasks()
        pos_x = master.winfo_rootx() + (master.winfo_width() // 2) - (self.winfo_reqwidth() // 2)
        pos_y = master.winfo_rooty() + (master.winfo_height() // 2) - (self.winfo_reqheight() // 2)
        self.geometry("+%d+%d" % (max(pos_x, 0), max(pos_y, 0)))
        self.wait_window(self)

    def _escolher(self, chave):
        inicial = self._cores[chave] or None
        _rgb, hexa = colorchooser.askcolor(color=inicial, parent=self, title="Escolher cor")
        if hexa:
            self._definir(chave, hexa)

    def _definir(self, chave, valor):
        self._cores[chave] = valor
        self._atualizar_amostra(chave)
        self._atualizar_previa()

    def _atualizar_amostra(self, chave):
        valor = self._cores[chave]
        amostra = self._amostras[chave]
        if valor:
            amostra.configure(text=valor, background=valor,
                              foreground="#000000" if _claro(valor) else "#ffffff")
        else:
            amostra.configure(text="(padrão do sistema)", background=self.cget("bg"), foreground="#000000")

    def _atualizar_previa(self):
        previa = self._previa
        fundo = self._cores["cor_fundo"] or self.cget("bg")
        fonte = self._cores["cor_fonte"] or "#000000"
        previa.configure(state="normal", background=fundo, foreground=fonte)
        previa.delete("1.0", tk.END)
        previa.tag_configure("negrito", font=("Consolas", 9, "bold"))
        trechos = [("NF: 123456", "nf"), (" / ", None), ("CLIENTE: EXEMPLO LTDA", "cliente"), (" / ", None),
                   ("OCORRÊNCIA: REENTREGA", "ocorrencia"), (" / ", None), ("SIGLA UNIDADE: BLU", "sigla"),
                   (" / ", None), ("DATA: 14/10/2026 HORA: 10:00", "data_hora"), (" / ", None),
                   ("DIAS EM TRATATIVAS: 2", "dias"), (" / ", None),
                   ("AGENDAMENTO: 20/10/2026", "agendamento"), (" / ", None), ("OBS: EXEMPLO", "observacao")]
        for texto, campo in trechos:
            negrito = campo is not None and self._vars_negrito[campo].get()
            previa.insert(tk.END, texto, ("negrito",) if negrito else ())
        previa.configure(state="disabled")

    def _salvar(self):
        self.config_resultado = {
            "cor_fonte": self._cores["cor_fonte"],
            "cor_fundo": self._cores["cor_fundo"],
            "cor_selecao": self._cores["cor_selecao"] or aparencia.COR_SELECAO_PADRAO,
            "negrito": {campo: var.get() for campo, var in self._vars_negrito.items()},
        }
        self.acao = "salvar"
        self.destroy()

    def _restaurar(self):
        if messagebox.askyesno("Restaurar padrão",
                               "Voltar todas as cores e o negrito ao padrão de fábrica?", parent=self):
            self.acao = "restaurar"
            self.destroy()

    def _cancelar(self):
        self.acao = None
        self.destroy()


def _claro(cor_hex):
    """True se a cor for clara (para escolher texto preto/branco legível)."""
    try:
        r, g, b = int(cor_hex[1:3], 16), int(cor_hex[3:5], 16), int(cor_hex[5:7], 16)
    except (ValueError, IndexError):
        return True
    return (0.299 * r + 0.587 * g + 0.114 * b) > 150


class EscolherComBusca(tk.Toplevel):
    """
    Dialogo para escolher um valor ja cadastrado (remetente, tipo de
    ocorrencia...) com busca dinamica: a lista de sugestoes e filtrada a cada
    tecla digitada, por nome/descricao (comeca com o texto primeiro, depois
    contem o texto). Setas cima/baixo (ou clique) escolhem uma sugestao; Enter
    confirma; Esc cancela. O primeiro resultado ja vem destacado assim que o
    usuario digita, entao digitar "prio" + Enter escolhe "PRIORIZAR ENTREGA".

    Se nada cadastrado corresponder ao texto e permitir_novo=True, o texto
    digitado e devolvido como valor novo (eh_novo=True) — quem chamou decide
    se o cadastra, como ja acontece no cadastro de notas.

    Resultado em self.resultado: (valor, eh_novo) ou None se cancelado.
    """

    def __init__(self, master, titulo, rotulo, opcoes, permitir_novo=True):
        super().__init__(master)
        self.title(titulo)
        self.resizable(False, False)
        self.resultado = None
        self._opcoes = list(opcoes)
        self._permitir_novo = permitir_novo
        self._filtradas = []
        self._indice = None
        self.grab_set()

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=rotulo, wraplength=420, justify="left").pack(anchor="w", pady=(0, 8))

        self.var_texto = tk.StringVar()
        self.entry = ttk.Entry(frame, textvariable=self.var_texto, width=52)
        self.entry.pack(fill="x")

        caixa = ttk.Frame(frame)
        caixa.pack(fill="both", expand=True, pady=(6, 0))
        self.lista = tk.Listbox(caixa, height=8, exportselection=False, activestyle="none")
        barra = ttk.Scrollbar(caixa, orient="vertical", command=self.lista.yview)
        self.lista.configure(yscrollcommand=barra.set)
        self.lista.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

        self.var_status = tk.StringVar()
        ttk.Label(frame, textvariable=self.var_status, foreground="#555", wraplength=420,
                  justify="left").pack(anchor="w", pady=(6, 0))

        botoes = ttk.Frame(frame)
        botoes.pack(fill="x", pady=(12, 0))
        ttk.Button(botoes, text="OK", command=self._confirmar).pack(side="right")
        ttk.Button(botoes, text="Cancelar", command=self._cancelar).pack(side="right", padx=(0, 6))

        self.var_texto.trace_add("write", lambda *_: self._atualizar(destacar_primeiro=True))
        self.entry.bind("<Down>", lambda e: self._mover(1))
        self.entry.bind("<Up>", lambda e: self._mover(-1))
        self.entry.bind("<Return>", self._confirmar)
        self.entry.bind("<KP_Enter>", self._confirmar)
        self.entry.bind("<Escape>", self._cancelar)
        self.lista.bind("<<ListboxSelect>>", self._ao_selecionar)
        self.lista.bind("<Double-Button-1>", self._confirmar)
        self.lista.bind("<Return>", self._confirmar)
        self.lista.bind("<Escape>", self._cancelar)
        self.protocol("WM_DELETE_WINDOW", self._cancelar)

        self._atualizar(destacar_primeiro=False)
        self.entry.focus_set()

        self.transient(master)
        self.update_idletasks()
        pos_x = master.winfo_rootx() + (master.winfo_width() // 2) - (self.winfo_reqwidth() // 2)
        pos_y = master.winfo_rooty() + (master.winfo_height() // 2) - (self.winfo_reqheight() // 2)
        self.geometry("+%d+%d" % (max(pos_x, 0), max(pos_y, 0)))
        self.wait_window(self)

    def _atualizar(self, destacar_primeiro):
        texto = self.var_texto.get()
        self._filtradas = occ.filtrar_opcoes(texto, self._opcoes)
        self.lista.delete(0, tk.END)
        for opcao in self._filtradas:
            self.lista.insert(tk.END, opcao)
        self._indice = None
        if self._filtradas and destacar_primeiro and texto.strip():
            self._destacar(0)
        if self._filtradas:
            self.var_status.set("%d sugestão(ões). Use ↑/↓ ou clique para escolher e Enter para confirmar."
                                % len(self._filtradas))
        elif texto.strip() and self._permitir_novo:
            self.var_status.set("Nenhum cadastro encontrado: \"%s\" será usado como novo valor."
                                % texto.strip().upper())
        elif texto.strip():
            self.var_status.set("Nenhum registro encontrado.")
        else:
            self.var_status.set("Nenhum cadastro disponível. Digite um valor.")

    def _destacar(self, indice):
        self._indice = indice
        self.lista.selection_clear(0, tk.END)
        self.lista.selection_set(indice)
        self.lista.activate(indice)
        self.lista.see(indice)

    def _mover(self, passo):
        if not self._filtradas:
            return "break"
        atual = -1 if self._indice is None else self._indice
        self._destacar(max(0, min(len(self._filtradas) - 1, atual + passo)))
        return "break"

    def _ao_selecionar(self, _event=None):
        sel = self.lista.curselection()
        if sel:
            self._indice = sel[0]

    def _confirmar(self, event=None):
        valor, eh_novo = occ.resolver_escolha(
            self.var_texto.get(), self._opcoes, self._indice, self._permitir_novo)
        if valor is None:
            self.var_status.set("Digite para buscar e escolha uma das sugestões.")
            self.bell()
            return "break"
        self.resultado = (valor, eh_novo)
        self.destroy()
        return "break"

    def _cancelar(self, event=None):
        self.resultado = None
        self.destroy()
        return "break"


def pedir_opcao(master, titulo, rotulo, opcoes, permitir_novo=True):
    """Abre o EscolherComBusca. Retorna (valor, eh_novo) ou None se cancelado."""
    return EscolherComBusca(master, titulo, rotulo, opcoes, permitir_novo).resultado
