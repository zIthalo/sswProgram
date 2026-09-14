# -*- coding: utf-8 -*-
"""
app.py
Aplicacao principal em Tkinter (biblioteca padrao do Python - compativel com
Windows 7 ou superior, e portavel para Linux sem alteracoes).
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

import database as db
import dateutils
import occorrencias as occ
from dialogs import GerenciarLista, editar_campo_texto, fluxo_marcar_resolvido


def dias_em_tratativas(criado_em_iso):
    try:
        criado = datetime.fromisoformat(criado_em_iso)
    except ValueError:
        return 0
    return (datetime.now() - criado).days


def hora_insercao(criado_em_iso):
    try:
        return datetime.fromisoformat(criado_em_iso).strftime("%H:%M")
    except ValueError:
        return ""


def montar_segmentos_cabecalho(nota):
    """Monta o cabecalho da nota como uma lista de (texto, negrito) — usada
    para exibir CLIENTE, OCORRÊNCIA e AGENDAMENTO em negrito no bloco da nota."""
    dias = dias_em_tratativas(nota["criado_em"])
    segmentos = [
        ("NF: %s / " % nota["nf_numero"], False),
        ("CLIENTE: %s" % nota["cliente"], True),
        (" / ", False),
        ("OCORRÊNCIA: %s" % nota["ocorrencia"], True),
        (" / SIGLA UNIDADE: %s / DATA: %s HORA: %s / DIAS EM TRATATIVAS: %s" % (
            nota["sigla"], dateutils.formatar_data_exibicao(nota["data_ocorrencia"]),
            hora_insercao(nota["criado_em"]), dias), False),
    ]
    if nota["agendamento_data"]:
        segmentos.append((" / ", False))
        segmentos.append(("AGENDAMENTO: %s" % dateutils.formatar_data_exibicao(nota["agendamento_data"]), True))
    return segmentos


def formatar_cabecalho_nota(nota):
    """Versao em texto simples do cabecalho da nota (usada ao copiar as
    informações da nota para a área de transferência)."""
    return "".join(texto for texto, _negrito in montar_segmentos_cabecalho(nota))


class NotaBlock(ttk.Frame):
    """Widget que representa o bloco visual de uma nota fiscal na tela principal."""

    def __init__(self, master, app, nota_row):
        super().__init__(master, padding=8, relief="groove", borderwidth=1)
        self.app = app
        self.nota_id = nota_row["id"]
        self.nota_row = nota_row

        self.txt_cabecalho = tk.Text(
            self, wrap="word", height=1, borderwidth=0, highlightthickness=0,
            font=("Consolas", 9), cursor="hand2", padx=0, pady=0, exportselection=False,
        )
        self.txt_cabecalho.tag_configure("negrito", font=("Consolas", 9, "bold"))
        self.txt_cabecalho.pack(fill="x")
        # Recalcula a altura sempre que a largura real do widget for definida
        # (na criacao do bloco, o layout so e conhecido depois de o widget ser
        # efetivamente posicionado — calcular a altura antes disso resultava
        # em blocos gigantes ate o usuario redimensionar a janela manualmente).
        self.txt_cabecalho.bind("<Configure>", lambda e: self._ajustar_altura_cabecalho())

        self._montar()

    def _montar(self):
        for widget in self.winfo_children():
            if widget is not self.txt_cabecalho:
                widget.destroy()
        self._labels_texto = []

        nota = self.nota_row
        largura_atual = self.app.obter_largura_lista()

        self.txt_cabecalho.configure(state="normal")
        self.txt_cabecalho.delete("1.0", tk.END)
        for texto, negrito in montar_segmentos_cabecalho(nota):
            self.txt_cabecalho.insert(tk.END, texto, ("negrito",) if negrito else ())
        self.txt_cabecalho.configure(state="disabled", insertwidth=0)
        self.txt_cabecalho.bind("<Button-1>", self._copiar_nf)
        self.txt_cabecalho.bind("<Button-3>", self._abrir_menu)
        self.txt_cabecalho.bind("<Double-Button-1>", self._adicionar_tratativa)
        self._ajustar_altura_cabecalho()

        separador = tk.Label(self, text="=" * 90, anchor="w", font=("Consolas", 7))
        separador.pack(fill="x")
        separador.bind("<Button-1>", self._selecionar)

        self.frame_tratativas = ttk.Frame(self)
        self.frame_tratativas.pack(fill="x")
        self.frame_tratativas.bind("<Button-1>", self._selecionar)
        for t in db.listar_tratativas(self.nota_id):
            linha = tk.Label(self.frame_tratativas, text="%s: %s" % (t["timestamp"], t["texto"]),
                              anchor="w", justify="left", font=("Consolas", 9), wraplength=largura_atual)
            linha.pack(fill="x")
            linha.bind("<Button-1>", self._selecionar)
            linha.bind("<Double-Button-1>", self._adicionar_tratativa)
            linha.bind("<Button-3>", self._abrir_menu)
            self._labels_texto.append(linha)

        self.bind("<Button-1>", self._selecionar)
        self.bind("<Button-3>", self._abrir_menu)
        self.bind("<Double-Button-1>", self._adicionar_tratativa)

        self._atualizar_destaque_selecao()

    def _ajustar_altura_cabecalho(self):
        self.txt_cabecalho.update_idletasks()
        try:
            linhas = self.txt_cabecalho.count("1.0", "end", "displaylines")
            n = linhas[0] if linhas else 1
        except (tk.TclError, TypeError):
            n = 1
        n = max(n, 1)
        if int(self.txt_cabecalho.cget("height")) != n:
            self.txt_cabecalho.configure(height=n)

    def _atualizar_destaque_selecao(self):
        if self.app.nota_selecionada_id == self.nota_id:
            self.txt_cabecalho.configure(background="#cfe8ff")
        else:
            self.txt_cabecalho.configure(background=self.app.cget("bg"))

    def atualizar_largura(self, largura):
        for lbl in getattr(self, "_labels_texto", []):
            lbl.configure(wraplength=max(largura, 200))
        self._ajustar_altura_cabecalho()

    def _selecionar(self, event=None):
        self.app.selecionar_nota(self.nota_id)

    def atualizar(self, nota_row):
        self.nota_row = nota_row
        self._montar()

    def _copiar_nf(self, event=None):
        self._selecionar()
        self.app.clipboard_clear()
        self.app.clipboard_append(str(self.nota_row["nf_numero"]))
        self.app.update()
        self.app.mostrar_mensagem_flutuante("Número copiado!", event)
        return "break"

    def _adicionar_tratativa(self, event=None):
        texto = simpledialog.askstring(
            "Nova atualização",
            "Descreva a atualização da tratativa para a NF %s:" % self.nota_row["nf_numero"],
            parent=self.app,
        )
        if texto:
            db.adicionar_tratativa(self.nota_id, texto.strip().upper())
            self.app.recarregar_lista()
        return "break"

    def _abrir_menu(self, event):
        menu = tk.Menu(self.app, tearoff=0)
        menu.add_command(label="Marcar como resolvido",
                          command=lambda: self.app.marcar_como_resolvido(self.nota_id))
        menu.add_separator()
        menu.add_command(label="Editar número da NF",
                          command=lambda: self.app.editar_campo(self.nota_id, "nf_numero", "Número da NF"))
        menu.add_command(label="Editar remetente",
                          command=lambda: self.app.editar_campo(self.nota_id, "cliente", "Remetente"))
        menu.add_command(label="Editar ocorrência",
                          command=lambda: self.app.editar_ocorrencia(self.nota_id))
        menu.add_command(label="Editar sigla",
                          command=lambda: self.app.editar_campo(self.nota_id, "sigla", "Sigla/Empresa"))
        menu.add_separator()
        menu.add_command(label="Copiar informações da nota",
                          command=lambda: self.app.copiar_informacoes_nota(self.nota_id))
        menu.tk_popup(event.x_root, event.y_root)
        return "break"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auxiliador de Processos Logísticos - SAC")
        self.geometry("920x680")
        self.minsize(480, 400)

        db.init_db()
        db.limpar_historico_expirado(60)

        self.blocos = {}  # nota_id -> NotaBlock
        self.nota_selecionada_id = None
        self._largura_lista_atual = 720
        self._suggestion_var = tk.StringVar(value="")

        self._montar_menu()
        self._montar_formulario()
        self._montar_busca()
        self._montar_filtro()
        self._montar_lista()

        self.recarregar_lista()

        self._configurar_navegacao_setas()
        self._configurar_atalhos_edicao()
        self.bind_all("<Control-f>", self._focar_busca)

    # ------------------------------------------------------------------
    # Menu superior
    # ------------------------------------------------------------------
    def _montar_menu(self):
        barra = tk.Menu(self)

        m_arquivo = tk.Menu(barra, tearoff=0)
        m_arquivo.add_command(label="Sair", command=self.destroy)
        barra.add_cascade(label="Arquivo", menu=m_arquivo)

        m_cadastros = tk.Menu(barra, tearoff=0)
        m_cadastros.add_command(label="Empresas parceiras (Agex, Risso, etc.)",
                                 command=self._gerenciar_empresas_parceiras)
        m_cadastros.add_command(label="Tipos de ocorrência",
                                 command=self._gerenciar_tipos_ocorrencia)
        m_cadastros.add_command(label="Remetentes",
                                 command=self._gerenciar_clientes)
        barra.add_cascade(label="Cadastros", menu=m_cadastros)

        barra.add_command(label="Relatório", command=self._abrir_relatorio)
        barra.add_command(label="Histórico", command=self._abrir_historico)

        self.config(menu=barra)

    def _gerenciar_empresas_parceiras(self):
        GerenciarLista(self, "Empresas parceiras", db.listar_empresas_parceiras,
                        db.adicionar_empresa_parceira, db.remover_empresa_parceira)
        self._atualizar_combobox_sigla()

    def _gerenciar_tipos_ocorrencia(self):
        GerenciarLista(self, "Tipos de ocorrência",
                        db.listar_tipos_ocorrencia, db.adicionar_tipo_ocorrencia,
                        db.remover_tipo_ocorrencia)
        self._atualizar_combobox_filtro()

    def _gerenciar_clientes(self):
        GerenciarLista(self, "Remetentes", db.listar_clientes,
                        db.adicionar_cliente, db.remover_cliente)

    def _abrir_relatorio(self):
        db.limpar_historico_expirado(60)
        dados = db.gerar_relatorio()

        janela = tk.Toplevel(self)
        janela.title("Relatório")
        janela.geometry("480x680")
        frame = ttk.Frame(janela, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Unidades com mais ocorrências (top 5):",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        for sigla, total in dados["siglas_mais_ocorrencias"]:
            lbl = tk.Label(frame, text="  %s — %d ocorrência(s)" % (sigla, total),
                            fg="#0645AD", cursor="hand2")
            lbl.pack(anchor="w")
            lbl.bind("<Button-1>", lambda e, s=sigla: self._mostrar_detalhes_historico(
                "Notas da unidade %s (mais ocorrências)" % s,
                db.buscar_historico_por_sigla(s)))
        if not dados["siglas_mais_ocorrencias"]:
            ttk.Label(frame, text="  (sem dados no histórico)").pack(anchor="w")

        ttk.Separator(frame).pack(fill="x", pady=10)
        ttk.Label(frame, text="Tempo médio para solução do caso:",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        ttk.Label(frame, text="  %d dia(s) e %d hora(s)"
                  % (dados["tempo_medio_dias"], dados["tempo_medio_horas"])).pack(anchor="w")

        ttk.Separator(frame).pack(fill="x", pady=10)
        ttk.Label(frame, text="Unidades mais morosas (top 5):",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        for sigla, total in dados["unidades_mais_morosas"]:
            lbl = tk.Label(frame, text="  %s — %d vez(es)" % (sigla, total),
                            fg="#0645AD", cursor="hand2")
            lbl.pack(anchor="w")
            lbl.bind("<Button-1>", lambda e, s=sigla: self._mostrar_detalhes_historico(
                "Notas da unidade %s (mais morosa)" % s,
                db.buscar_historico_por_sigla(s, somente_morosidade_unidade=True)))
        if not dados["unidades_mais_morosas"]:
            ttk.Label(frame, text="  (sem dados no histórico)").pack(anchor="w")

        ttk.Separator(frame).pack(fill="x", pady=10)
        ttk.Label(frame, text="Clientes mais morosos (top 5):",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        for cliente, total in dados["clientes_mais_morosos"]:
            ttk.Label(frame, text="  %s — %d vez(es)" % (cliente, total)).pack(anchor="w")
        if not dados["clientes_mais_morosos"]:
            ttk.Label(frame, text="  (sem dados no histórico)").pack(anchor="w")

        ttk.Separator(frame).pack(fill="x", pady=10)
        ttk.Button(frame, text="Ver histórico completo (60 dias)",
                   command=self._abrir_historico).pack(anchor="w")
        ttk.Button(frame, text="Apagar histórico (60 dias)",
                   command=lambda: self._apagar_historico(janela)).pack(anchor="w", pady=(6, 0))

    def _apagar_historico(self, janela):
        if messagebox.askyesno("Confirmar", "Deseja realmente apagar todo o histórico?", parent=janela):
            db.limpar_historico_manual()
            janela.destroy()
            self._abrir_relatorio()

    def _abrir_historico(self):
        """Aba de Histórico: mostra todas as notas tratadas nos últimos 60
        dias, do mais recente para o mais antigo, com filtros por cliente,
        sigla e número de NF."""
        db.limpar_historico_expirado(60)

        janela = tk.Toplevel(self)
        janela.title("Histórico (últimos 60 dias)")
        janela.geometry("560x620")
        janela.minsize(420, 400)
        frame = ttk.Frame(janela, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Histórico de notas tratadas (últimos 60 dias)",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")

        linha_filtros = ttk.Frame(frame)
        linha_filtros.pack(fill="x", pady=(8, 8))
        linha_filtros.columnconfigure(1, weight=1)
        linha_filtros.columnconfigure(3, weight=1)
        linha_filtros.columnconfigure(5, weight=1)

        ttk.Label(linha_filtros, text="Cliente:").grid(row=0, column=0, sticky="w")
        var_cliente = tk.StringVar()
        ttk.Entry(linha_filtros, textvariable=var_cliente).grid(row=0, column=1, padx=4, sticky="ew")

        ttk.Label(linha_filtros, text="Sigla:").grid(row=0, column=2, sticky="w")
        var_sigla = tk.StringVar()
        ttk.Entry(linha_filtros, textvariable=var_sigla, width=10).grid(row=0, column=3, padx=4, sticky="ew")

        ttk.Label(linha_filtros, text="NF:").grid(row=0, column=4, sticky="w")
        var_nf = tk.StringVar()
        ttk.Entry(linha_filtros, textvariable=var_nf, width=10).grid(row=0, column=5, padx=4, sticky="ew")

        ttk.Button(linha_filtros, text="Limpar filtros",
                   command=lambda: (var_cliente.set(""), var_sigla.set(""), var_nf.set(""))
                   ).grid(row=1, column=0, columnspan=6, sticky="w", pady=(6, 0))

        canvas = tk.Canvas(frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        interior = ttk.Frame(canvas)
        interior.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=interior, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def atualizar(*_args):
            for widget in interior.winfo_children():
                widget.destroy()

            # listar_historico() ja retorna ordenado do mais recente ao mais antigo
            registros = db.listar_historico()

            cliente_f = var_cliente.get().strip().lower()
            sigla_f = var_sigla.get().strip().lower()
            nf_f = var_nf.get().strip()

            if cliente_f:
                registros = [h for h in registros if cliente_f in h["cliente"].lower()]
            if sigla_f:
                registros = [h for h in registros if sigla_f in h["sigla"].lower()]
            if nf_f:
                if nf_f.isdigit():
                    registros = [h for h in registros if h["nf_numero"] == int(nf_f)]
                else:
                    registros = []

            if not registros:
                ttk.Label(interior, text="Nenhum registro encontrado.").pack(anchor="w")
                return
            for h in registros:
                ttk.Label(interior, text=self._formatar_linha_historico(h),
                          wraplength=480, justify="left").pack(anchor="w", pady=2)

        for var in (var_cliente, var_sigla, var_nf):
            var.trace_add("write", atualizar)

        atualizar()

    def _formatar_linha_historico(self, h):
        morosidade_txt = {"unidade": "Unidade", "cliente": "Cliente", "nenhum": "Sem morosidade"}
        return (
            "NF %s / %s / Ocorrência: %s / Sigla: %s / Tempo: %d dia(s) e %d hora(s) / "
            "Morosidade: %s / Resolvida em: %s"
        ) % (
            h["nf_numero"], h["cliente"], h["ocorrencia"], h["sigla"], h["dias"], h["horas"],
            morosidade_txt.get(h["morosidade"], "-"), h["resolvido_em"][:16].replace("T", " "),
        )

    def _mostrar_detalhes_historico(self, titulo, registros):
        """Mostra as notas do histórico que embasam um item clicado no top 5
        do relatório (unidade com mais ocorrências ou unidade mais morosa)."""
        janela = tk.Toplevel(self)
        janela.title(titulo)
        janela.geometry("480x360")
        frame = ttk.Frame(janela, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=titulo, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))

        canvas = tk.Canvas(frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        interior = ttk.Frame(canvas)
        interior.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=interior, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        if not registros:
            ttk.Label(interior, text="Nenhum registro encontrado.").pack(anchor="w")
            return
        for h in registros:
            ttk.Label(interior, text=self._formatar_linha_historico(h),
                      wraplength=420, justify="left").pack(anchor="w", pady=2)

    # ------------------------------------------------------------------
    # Formulario de insercao de nota
    # ------------------------------------------------------------------
    def _montar_formulario(self):
        frame = ttk.LabelFrame(self, text="Nova nota / ocorrência", padding=10)
        frame.pack(fill="x", padx=10, pady=(10, 4))
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(3, weight=1)

        ttk.Label(frame, text="NF:").grid(row=0, column=0, sticky="w")
        self.var_nf = tk.StringVar()
        self.entry_nf = ttk.Entry(frame, textvariable=self.var_nf, width=12)
        self.entry_nf.grid(row=0, column=1, padx=4, sticky="ew")

        ttk.Label(frame, text="Cliente/Remetente:").grid(row=0, column=2, sticky="w")
        self.var_cliente = tk.StringVar()
        self.entry_cliente = ttk.Entry(frame, textvariable=self.var_cliente, width=20)
        self.entry_cliente.grid(row=0, column=3, padx=4, sticky="ew")
        self.entry_cliente.bind("<KeyRelease>", self._sugerir_cliente)
        self._suggestion_cliente_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self._suggestion_cliente_var, foreground="#555").grid(
            row=2, column=3, sticky="w")

        ttk.Label(frame, text="Ocorrência:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.var_ocorrencia = tk.StringVar()
        self.entry_oc = ttk.Entry(frame, textvariable=self.var_ocorrencia, width=20)
        self.entry_oc.grid(row=1, column=1, padx=4, pady=(6, 0), sticky="ew")
        self.entry_oc.bind("<KeyRelease>", self._sugerir_ocorrencia)
        self.lbl_sugestao = ttk.Label(frame, textvariable=self._suggestion_var, foreground="#555")
        self.lbl_sugestao.grid(row=2, column=1, sticky="w")

        ttk.Label(frame, text="Sigla/Empresa:").grid(row=1, column=2, sticky="w", pady=(6, 0))
        self.var_sigla = tk.StringVar()
        self.combo_sigla = ttk.Combobox(frame, textvariable=self.var_sigla, width=18)
        self.combo_sigla.grid(row=1, column=3, padx=4, pady=(6, 0), sticky="ew")
        self._atualizar_combobox_sigla()

        self.btn_adicionar = ttk.Button(frame, text="Adicionar nota", command=self._adicionar_nota)
        self.btn_adicionar.grid(row=3, column=3, sticky="e", pady=(6, 0))

        # Navegacao entre campos com Enter, sem depender do TAB
        self.entry_nf.bind("<Return>", lambda e: self._focar(self.entry_cliente))
        # Enter/Tab em Cliente e Ocorrência colam a sugestão (se houver) antes de avançar
        self.entry_cliente.bind("<Return>", self._aceitar_sugestao_cliente)
        self.entry_cliente.bind("<Tab>", self._aceitar_sugestao_cliente)
        self.entry_oc.bind("<Return>", self._aceitar_sugestao_ocorrencia)
        self.entry_oc.bind("<Tab>", self._aceitar_sugestao_ocorrencia)
        # Enter na Sigla (ultimo campo) equivale a clicar no botao "Adicionar nota"
        self.combo_sigla.bind("<Return>", self._acionar_botao_adicionar)
        self.btn_adicionar.bind("<Return>", self._acionar_botao_adicionar)

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
        palavra anterior) e Ctrl+Delete (apagar palavra seguinte) aos campos de
        texto/combobox editáveis do sistema."""
        campos = [
            self.entry_nf, self.entry_cliente, self.entry_oc, self.combo_sigla,
            self.entry_busca, self.combo_filtro,
        ]
        for campo in campos:
            self._instalar_atalhos_edicao(campo)

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

        duplicada = db.buscar_duplicada(nf, cliente, ocorrencia)
        if duplicada:
            messagebox.showinfo("Duplicidade", "Esta NF e remetente já foram inseridos no sistema.")
            self.recarregar_lista()
            self._destacar_nota(duplicada["id"])
            return

        agendamento_data = None
        if occ.eh_ocorrencia_agendamento(ocorrencia):
            data_ag = simpledialog.askstring(
                "Data do agendamento",
                "Informe a data do agendamento (0=hoje, dia do mês, ou ddmmaaaa):", parent=self)
            if data_ag is None:
                return
            try:
                agendamento_data = dateutils.parse_data_usuario(data_ag)
            except ValueError as e:
                messagebox.showerror("Data inválida", str(e))
                return
            if dateutils.data_e_passado_ou_hoje(agendamento_data):
                messagebox.showerror("Erro", "A data do agendamento é igual ou inferior a data atual.")
                return

        db.inserir_nota(nf, cliente, ocorrencia, sigla, data_ocorrencia, agendamento_data)

        if cliente.lower() not in [c.lower() for c in db.listar_clientes()]:
            db.adicionar_cliente(cliente)

        self.var_nf.set("")
        self.var_cliente.set("")
        self.var_ocorrencia.set("")
        self.var_sigla.set("")
        self._suggestion_var.set("")
        self._suggestion_cliente_var.set("")
        self._sugestao_atual = None
        self._sugestao_cliente_atual = None

        self.recarregar_lista()
        self._focar(self.entry_nf)

    # ------------------------------------------------------------------
    # Busca (Ctrl+F)
    # ------------------------------------------------------------------
    def _montar_busca(self):
        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=10)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Buscar NF/Cliente/Sigla (Ctrl+F):").grid(row=0, column=0, sticky="w")
        self.var_busca = tk.StringVar()
        self.entry_busca = ttk.Entry(frame, textvariable=self.var_busca, width=20)
        self.entry_busca.grid(row=0, column=1, padx=6, sticky="ew")
        self.entry_busca.bind("<KeyRelease>", self._sugerir_busca)
        self.entry_busca.bind("<Return>", self._executar_busca)
        self.entry_busca.bind("<Tab>", self._aceitar_sugestao_busca)
        self.btn_buscar = ttk.Button(frame, text="Buscar", command=self._executar_busca)
        self.btn_buscar.grid(row=0, column=2, sticky="e")
        self._suggestion_busca_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self._suggestion_busca_var, foreground="#555").grid(
            row=1, column=1, sticky="w")

    def _focar_busca(self, event=None):
        self.entry_busca.focus_set()
        self.entry_busca.select_range(0, tk.END)
        return "break"

    def _sugerir_busca(self, event=None):
        texto = self.var_busca.get()
        clientes = db.listar_clientes()
        sugestao = occ.sugerir_ocorrencia(texto, clientes)
        if sugestao and texto.strip() and sugestao.lower() != texto.strip().lower():
            self._suggestion_busca_var.set("Sugestão: %s (Enter/Tab para usar)" % sugestao)
            self._sugestao_busca_atual = sugestao
        else:
            self._suggestion_busca_var.set("")
            self._sugestao_busca_atual = None

    def _aceitar_sugestao_busca(self, event=None):
        if getattr(self, "_sugestao_busca_atual", None):
            self.var_busca.set(self._sugestao_busca_atual)
            self.entry_busca.icursor(tk.END)
            self._suggestion_busca_var.set("")
            self._sugestao_busca_atual = None
        self._focar(self.btn_buscar)
        return "break"

    def _executar_busca(self, event=None):
        # Se houver uma sugestão de cliente ativa, aceita-a antes de buscar
        if getattr(self, "_sugestao_busca_atual", None):
            self.var_busca.set(self._sugestao_busca_atual)
            self._suggestion_busca_var.set("")
            self._sugestao_busca_atual = None

        texto = self.var_busca.get().strip()
        if not texto:
            return
        alvo = None

        if texto.isdigit():
            nf = int(texto)
            for nota_id, bloco in self.blocos.items():
                if bloco.nota_row["nf_numero"] == nf:
                    alvo = nota_id
                    break

        if alvo is None:
            texto_lower = texto.lower()
            for nota_id, bloco in self.blocos.items():
                cliente = bloco.nota_row["cliente"].lower()
                sigla = bloco.nota_row["sigla"].lower()
                if texto_lower in cliente or texto_lower in sigla:
                    alvo = nota_id
                    break

        if alvo is None:
            messagebox.showinfo(
                "Busca", "Nenhuma nota ativa encontrada para \"%s\" (NF, cliente ou sigla)." % texto)
            return
        self._destacar_nota(alvo)

    def _destacar_nota(self, nota_id):
        bloco = self.blocos.get(nota_id)
        if not bloco:
            return
        self._rolar_para(nota_id)
        bloco.txt_cabecalho.configure(background="#fff2a8")
        self.after(1500, lambda: bloco.txt_cabecalho.configure(
            background="#cfe8ff" if self.nota_selecionada_id == nota_id else self.cget("bg")))

    def _rolar_para(self, nota_id):
        bloco = self.blocos.get(nota_id)
        if not bloco:
            return
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(bloco.winfo_y() / max(self.frame_lista.winfo_height(), 1))

    def selecionar_nota(self, nota_id):
        anterior = self.blocos.get(self.nota_selecionada_id)
        if anterior is not None:
            anterior.txt_cabecalho.configure(background=self.cget("bg"))
        self.nota_selecionada_id = nota_id
        bloco = self.blocos.get(nota_id)
        if bloco is not None:
            bloco.txt_cabecalho.configure(background="#cfe8ff")
            self._rolar_para(nota_id)
        self.canvas.focus_set()

    def _mover_selecao(self, direcao):
        ids = list(self.blocos.keys())
        if not ids:
            return
        if self.nota_selecionada_id not in ids:
            novo_indice = 0 if direcao >= 0 else len(ids) - 1
        else:
            indice_atual = ids.index(self.nota_selecionada_id)
            novo_indice = min(max(indice_atual + direcao, 0), len(ids) - 1)
        self.selecionar_nota(ids[novo_indice])

    def _resolver_via_teclado(self):
        if self.nota_selecionada_id is not None:
            self.marcar_como_resolvido(self.nota_selecionada_id)

    def _adicionar_tratativa_via_teclado(self):
        bloco = self.blocos.get(self.nota_selecionada_id)
        if bloco is not None:
            bloco._adicionar_tratativa()

    # ------------------------------------------------------------------
    # Filtro por tipo de ocorrencia
    # ------------------------------------------------------------------
    OPCAO_TODAS = "Todas as ocorrências"

    def _montar_filtro(self):
        frame = ttk.Frame(self)
        frame.pack(fill="x", padx=10, pady=(4, 0))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Filtrar por ocorrência:").grid(row=0, column=0, sticky="w")
        self.var_filtro = tk.StringVar(value=self.OPCAO_TODAS)
        self.combo_filtro = ttk.Combobox(frame, textvariable=self.var_filtro, width=24, state="normal")
        self.combo_filtro.grid(row=0, column=1, padx=6, sticky="ew")
        self.combo_filtro.bind("<KeyRelease>", self._filtrar_combo_ocorrencias)
        self.combo_filtro.bind("<Return>", self._aplicar_filtro_digitado)
        self.combo_filtro.bind("<<ComboboxSelected>>", lambda e: self.recarregar_lista(resetar_scroll=True))
        self.btn_limpar_filtro = ttk.Button(frame, text="Limpar filtro", command=self._limpar_filtro)
        self.btn_limpar_filtro.grid(row=0, column=2, sticky="e")

        self._atualizar_combobox_filtro()

    def _atualizar_combobox_filtro(self):
        """O combobox mostra apenas as ocorrências que realmente existem entre
        as notas ativas no momento (ex.: se não houver nenhuma nota de
        Agendamento, essa opção não aparece)."""
        valores = [self.OPCAO_TODAS] + db.listar_ocorrencias_em_uso()
        self.combo_filtro["values"] = valores

    def _filtrar_combo_ocorrencias(self, event=None):
        """Enquanto o usuario digita, estreita as opcoes do combobox de filtro
        para agilizar a localizacao do tipo de ocorrencia desejado."""
        if event is not None and event.keysym in ("Return", "Up", "Down", "Tab"):
            return
        texto = self.var_filtro.get().strip().lower()
        tipos = [self.OPCAO_TODAS] + db.listar_ocorrencias_em_uso()
        if texto:
            tipos = [t for t in tipos if texto in t.lower()]
        self.combo_filtro["values"] = tipos

    def _aplicar_filtro_digitado(self, event=None):
        """Ao pressionar Enter no filtro, resolve o texto digitado para um tipo
        de ocorrencia valido (ou 'Todas as ocorrencias') e aplica o filtro."""
        texto = self.var_filtro.get().strip()
        tipos = db.listar_ocorrencias_em_uso()
        if not texto or texto.lower() == self.OPCAO_TODAS.lower():
            self.var_filtro.set(self.OPCAO_TODAS)
        else:
            sugestao = occ.sugerir_ocorrencia(texto, tipos)
            if sugestao:
                self.var_filtro.set(sugestao)
        self._atualizar_combobox_filtro()
        self.recarregar_lista(resetar_scroll=True)
        return "break"

    def _limpar_filtro(self):
        self.var_filtro.set(self.OPCAO_TODAS)
        self.recarregar_lista(resetar_scroll=True)

    # ------------------------------------------------------------------
    # Lista principal (scrollavel)
    # ------------------------------------------------------------------
    def _montar_lista(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        self.canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.frame_lista = ttk.Frame(self.canvas)

        self.frame_lista.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._frame_lista_janela = self.canvas.create_window((0, 0), window=self.frame_lista, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._largura_lista_atual = 760
        self.canvas.bind("<Configure>", self._ao_redimensionar_lista)

        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))

        self.canvas.bind("<Up>", lambda e: self._mover_selecao(-1))
        self.canvas.bind("<Down>", lambda e: self._mover_selecao(1))
        self.canvas.bind("<Delete>", lambda e: self._resolver_via_teclado())
        self.canvas.bind("<Return>", lambda e: self._adicionar_tratativa_via_teclado())

    def _ao_redimensionar_lista(self, event):
        """Mantem o conteudo da lista de notas ajustado a largura da janela,
        para que o texto dos blocos quebre a linha corretamente em vez de
        ficar cortado quando a janela e estreitada."""
        self.canvas.itemconfig(self._frame_lista_janela, width=event.width)
        self._largura_lista_atual = max(event.width - 24, 200)
        for bloco in self.blocos.values():
            bloco.atualizar_largura(self._largura_lista_atual)

    def obter_largura_lista(self):
        return getattr(self, "_largura_lista_atual", 760)

    def recarregar_lista(self, resetar_scroll=False):
        for widget in self.frame_lista.winfo_children():
            widget.destroy()
        self.blocos = {}

        if hasattr(self, "combo_filtro"):
            self._atualizar_combobox_filtro()

        notas = db.listar_notas_ativas()
        filtro = self.var_filtro.get() if hasattr(self, "var_filtro") else self.OPCAO_TODAS
        if filtro and filtro != self.OPCAO_TODAS:
            notas = [n for n in notas if n["ocorrencia"].strip().lower() == filtro.strip().lower()]
            if filtro.strip().upper() == "AGENDAMENTO":
                notas = sorted(notas, key=self._chave_ordenacao_agendamento)

        for nota in notas:
            bloco = NotaBlock(self.frame_lista, self, nota)
            bloco.pack(fill="x", pady=4, padx=2)
            self.blocos[nota["id"]] = bloco

        if self.nota_selecionada_id not in self.blocos:
            self.nota_selecionada_id = None

        if resetar_scroll:
            self.canvas.update_idletasks()
            self.canvas.yview_moveto(0.0)

    def _chave_ordenacao_agendamento(self, nota):
        """Ordena as notas de Agendamento pela data agendada (mais próxima
        primeiro), e não pela data em que a ocorrência foi inserida."""
        if nota["agendamento_data"]:
            try:
                return dateutils.data_str_para_datetime(nota["agendamento_data"])
            except ValueError:
                pass
        return datetime.max

    def mostrar_mensagem_flutuante(self, texto, event=None):
        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.geometry("+%d+%d" % (x + 10, y + 10))
        tk.Label(popup, text=texto, background="#333", foreground="white", padx=6, pady=3).pack()
        self.after(1000, popup.destroy)

    def copiar_informacoes_nota(self, nota_id):
        nota = db.obter_nota(nota_id)
        if nota is None:
            return
        linhas = [formatar_cabecalho_nota(nota)]
        for t in db.listar_tratativas(nota_id):
            linhas.append("%s: %s" % (t["timestamp"], t["texto"]))
        self.clipboard_clear()
        self.clipboard_append("\n".join(linhas))
        self.update()
        self.mostrar_mensagem_flutuante("Informações copiadas!")

    # ------------------------------------------------------------------
    # Acoes do menu de contexto de cada nota
    # ------------------------------------------------------------------
    def marcar_como_resolvido(self, nota_id):
        nota = db.obter_nota(nota_id)
        if nota is None:
            return
        resultado = fluxo_marcar_resolvido(self, nota)
        if resultado is None:
            return
        db.inserir_historico(
            resultado["nf_numero"], resultado["cliente"], resultado["ocorrencia"],
            resultado["sigla"], resultado["dias"], resultado["horas"], resultado["morosidade"],
        )
        db.marcar_resolvida(nota_id)
        self.recarregar_lista()

    def editar_campo(self, nota_id, campo, rotulo):
        nota = db.obter_nota(nota_id)
        if nota is None:
            return
        valor_atual = str(nota[campo])
        novo = editar_campo_texto(self, "Editar %s" % rotulo, "Novo valor para %s:" % rotulo, valor_atual)
        if novo is None or novo.strip() == "":
            return
        if campo == "nf_numero":
            try:
                novo = int(novo.strip())
            except ValueError:
                messagebox.showerror("Erro", "Número da NF inválido.")
                return
        elif campo in ("cliente", "sigla"):
            novo = novo.strip().upper()
        db.atualizar_campo_nota(nota_id, campo, novo)
        self.recarregar_lista()

    def editar_ocorrencia(self, nota_id):
        nota = db.obter_nota(nota_id)
        if nota is None:
            return
        novo = editar_campo_texto(self, "Editar ocorrência", "Nova ocorrência:", nota["ocorrencia"])
        if not novo:
            return
        novo = novo.strip().upper()
        tipos = db.listar_tipos_ocorrencia()
        sugestao = occ.sugerir_ocorrencia(novo, tipos)
        ocorrencia_final = (sugestao if sugestao else novo).upper()
        if ocorrencia_final.lower() not in [t.lower() for t in tipos]:
            if messagebox.askyesno("Nova ocorrência", "Cadastrar '%s' como novo tipo?" % ocorrencia_final):
                db.adicionar_tipo_ocorrencia(ocorrencia_final)
            else:
                return
        db.atualizar_campo_nota(nota_id, "ocorrencia", ocorrencia_final)
        self.recarregar_lista()
