# -*- coding: utf-8 -*-
"""
app.py
Aplicacao principal em Tkinter (biblioteca padrao do Python - compativel com
Windows 7 ou superior, e portavel para Linux sem alteracoes).
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta

import database as db
import dateutils
import occorrencias as occ
from dialogs import (
    PopupLembrete, PopupAlerta, GerenciarLista, editar_campo_texto, fluxo_marcar_resolvido,
)

INTERVALO_VERIFICACAO_MS = 30 * 1000  # checa lembretes a cada 30 segundos


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


class NotaBlock(ttk.Frame):
    """Widget que representa o bloco visual de uma nota fiscal na tela principal."""

    def __init__(self, master, app, nota_row):
        super().__init__(master, padding=8, relief="groove", borderwidth=1)
        self.app = app
        self.nota_id = nota_row["id"]
        self.nota_row = nota_row
        self._montar()

    def _montar(self):
        for widget in self.winfo_children():
            widget.destroy()

        nota = self.nota_row
        dias = dias_em_tratativas(nota["criado_em"])
        lembrete_txt = dateutils.formatar_codigo_lembrete(nota["lembrete_codigo"])

        agendamento_txt = ""
        if nota["agendamento_data"]:
            agendamento_txt = " / AGENDAMENTO: %s" % dateutils.formatar_data_exibicao(nota["agendamento_data"])

        cabecalho = (
            "NF: {nf} / CLIENTE: {cliente} / OCORRÊNCIA: {oc} / SIGLA UNIDADE: {sigla} / "
            "DATA: {data} HORA: {hora} / DIAS EM TRATATIVAS: {dias}{lembrete}{agendamento}"
        ).format(
            nf=nota["nf_numero"], cliente=nota["cliente"], oc=nota["ocorrencia"],
            sigla=nota["sigla"], data=dateutils.formatar_data_exibicao(nota["data_ocorrencia"]),
            hora=hora_insercao(nota["criado_em"]), dias=dias,
            lembrete=(" / LEMBRAR A CADA: %s" % lembrete_txt) if lembrete_txt else "",
            agendamento=agendamento_txt,
        )

        self.lbl_cabecalho = tk.Label(self, text=cabecalho, anchor="w", justify="left",
                                       font=("Consolas", 9, "bold"), cursor="hand2", wraplength=760)
        self.lbl_cabecalho.pack(fill="x")
        self.lbl_cabecalho.bind("<Button-1>", self._copiar_nf)
        self.lbl_cabecalho.bind("<Button-3>", self._abrir_menu)
        self.lbl_cabecalho.bind("<Double-Button-1>", self._adicionar_tratativa)

        separador = tk.Label(self, text="=" * 90, anchor="w", font=("Consolas", 7))
        separador.pack(fill="x")
        separador.bind("<Button-1>", self._selecionar)

        self.frame_tratativas = ttk.Frame(self)
        self.frame_tratativas.pack(fill="x")
        self.frame_tratativas.bind("<Button-1>", self._selecionar)
        for t in db.listar_tratativas(self.nota_id):
            linha = tk.Label(self.frame_tratativas, text="%s: %s" % (t["timestamp"], t["texto"]),
                              anchor="w", justify="left", font=("Consolas", 9), wraplength=760)
            linha.pack(fill="x")
            linha.bind("<Button-1>", self._selecionar)
            linha.bind("<Double-Button-1>", self._adicionar_tratativa)
            linha.bind("<Button-3>", self._abrir_menu)

        self.bind("<Button-1>", self._selecionar)
        self.bind("<Button-3>", self._abrir_menu)
        self.bind("<Double-Button-1>", self._adicionar_tratativa)

        if self.app.nota_selecionada_id == self.nota_id:
            self.lbl_cabecalho.configure(background="#cfe8ff")

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

    def _adicionar_tratativa(self, event=None):
        texto = simpledialog.askstring(
            "Nova atualização",
            "Descreva a atualização da tratativa para a NF %s:" % self.nota_row["nf_numero"],
            parent=self.app,
        )
        if texto:
            db.adicionar_tratativa(self.nota_id, texto)
            self.app.recarregar_lista()

    def _abrir_menu(self, event):
        menu = tk.Menu(self.app, tearoff=0)
        menu.add_command(label="Marcar como resolvido",
                          command=lambda: self.app.marcar_como_resolvido(self.nota_id))
        if self.nota_row["lembrete_codigo"]:
            menu.add_command(label="Remover lembrete",
                              command=lambda: self.app.remover_lembrete(self.nota_id))
        else:
            menu.add_command(label="Adicionar lembrete",
                              command=lambda: self.app.adicionar_lembrete(self.nota_id))
        menu.add_separator()
        menu.add_command(label="Editar número da NF",
                          command=lambda: self.app.editar_campo(self.nota_id, "nf_numero", "Número da NF"))
        menu.add_command(label="Editar remetente",
                          command=lambda: self.app.editar_campo(self.nota_id, "cliente", "Remetente"))
        menu.add_command(label="Editar ocorrência",
                          command=lambda: self.app.editar_ocorrencia(self.nota_id))
        menu.add_command(label="Editar sigla",
                          command=lambda: self.app.editar_campo(self.nota_id, "sigla", "Sigla/Empresa"))
        menu.tk_popup(event.x_root, event.y_root)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Auxiliador de Processos Logísticos - SAC")
        self.geometry("920x680")

        db.init_db()
        db.limpar_historico_expirado(60)

        self.blocos = {}  # nota_id -> NotaBlock
        self.nota_selecionada_id = None
        self._suggestion_var = tk.StringVar(value="")

        self._montar_menu()
        self._montar_formulario()
        self._montar_busca()
        self._montar_filtro()
        self._montar_lista()

        self.recarregar_lista()
        self.after(1000, self._checar_lembretes)

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
            ttk.Label(frame, text="  %s — %d ocorrência(s)" % (sigla, total)).pack(anchor="w")
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
            ttk.Label(frame, text="  %s — %d vez(es)" % (sigla, total)).pack(anchor="w")
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
        ttk.Label(frame, text="Buscar NF no histórico:",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        linha_busca = ttk.Frame(frame)
        linha_busca.pack(fill="x", pady=(4, 4))
        var_nf_hist = tk.StringVar()
        entry_nf_hist = ttk.Entry(linha_busca, textvariable=var_nf_hist, width=14)
        entry_nf_hist.pack(side="left")
        resultado_frame = ttk.Frame(frame)
        resultado_frame.pack(fill="both", expand=True, pady=(4, 0))

        def buscar_no_historico(event=None):
            for widget in resultado_frame.winfo_children():
                widget.destroy()
            texto = var_nf_hist.get().strip()
            if not texto.isdigit():
                ttk.Label(resultado_frame, text="Digite um número de NF válido.").pack(anchor="w")
                return
            encontrados = db.buscar_historico_por_nf(int(texto))
            if not encontrados:
                ttk.Label(resultado_frame, text="Nenhum registro encontrado no histórico.").pack(anchor="w")
                return
            morosidade_txt = {"unidade": "Unidade", "cliente": "Cliente", "nenhum": "Sem morosidade"}
            for h in encontrados:
                texto_linha = (
                    "NF %s / %s / Ocorrência: %s / Sigla: %s / Tempo: %d dia(s) e %d hora(s) / "
                    "Morosidade: %s / Resolvida em: %s"
                ) % (
                    h["nf_numero"], h["cliente"], h["ocorrencia"], h["sigla"], h["dias"], h["horas"],
                    morosidade_txt.get(h["morosidade"], "-"), h["resolvido_em"][:16].replace("T", " "),
                )
                ttk.Label(resultado_frame, text=texto_linha, wraplength=440, justify="left").pack(
                    anchor="w", pady=2)

        entry_nf_hist.bind("<Return>", buscar_no_historico)
        ttk.Button(linha_busca, text="Buscar", command=buscar_no_historico).pack(side="left", padx=(6, 0))

        ttk.Separator(frame).pack(fill="x", pady=10)
        ttk.Button(frame, text="Apagar histórico (60 dias)",
                   command=lambda: self._apagar_historico(janela)).pack(anchor="w")

    def _apagar_historico(self, janela):
        if messagebox.askyesno("Confirmar", "Deseja realmente apagar todo o histórico?", parent=janela):
            db.limpar_historico_manual()
            janela.destroy()
            self._abrir_relatorio()

    # ------------------------------------------------------------------
    # Formulario de insercao de nota
    # ------------------------------------------------------------------
    def _montar_formulario(self):
        frame = ttk.LabelFrame(self, text="Nova nota / ocorrência", padding=10)
        frame.pack(fill="x", padx=10, pady=(10, 4))

        ttk.Label(frame, text="NF:").grid(row=0, column=0, sticky="w")
        self.var_nf = tk.StringVar()
        self.entry_nf = ttk.Entry(frame, textvariable=self.var_nf, width=12)
        self.entry_nf.grid(row=0, column=1, padx=4)

        ttk.Label(frame, text="Cliente/Remetente:").grid(row=0, column=2, sticky="w")
        self.var_cliente = tk.StringVar()
        self.entry_cliente = ttk.Entry(frame, textvariable=self.var_cliente, width=20)
        self.entry_cliente.grid(row=0, column=3, padx=4)
        self.entry_cliente.bind("<KeyRelease>", self._sugerir_cliente)
        self._suggestion_cliente_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self._suggestion_cliente_var, foreground="#555").grid(
            row=2, column=3, sticky="w")

        ttk.Label(frame, text="Ocorrência:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.var_ocorrencia = tk.StringVar()
        self.entry_oc = ttk.Entry(frame, textvariable=self.var_ocorrencia, width=20)
        self.entry_oc.grid(row=1, column=1, padx=4, pady=(6, 0))
        self.entry_oc.bind("<KeyRelease>", self._sugerir_ocorrencia)
        self.lbl_sugestao = ttk.Label(frame, textvariable=self._suggestion_var, foreground="#555")
        self.lbl_sugestao.grid(row=2, column=1, sticky="w")

        ttk.Label(frame, text="Sigla/Empresa:").grid(row=1, column=2, sticky="w", pady=(6, 0))
        self.var_sigla = tk.StringVar()
        self.combo_sigla = ttk.Combobox(frame, textvariable=self.var_sigla, width=18)
        self.combo_sigla.grid(row=1, column=3, padx=4, pady=(6, 0))
        self._atualizar_combobox_sigla()

        ttk.Label(frame, text="Data (0=hoje, dia ou ddmmaaaa):").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.var_data = tk.StringVar(value="0")
        self.entry_data = ttk.Entry(frame, textvariable=self.var_data, width=12)
        self.entry_data.grid(row=3, column=1, padx=4, pady=(6, 0))

        self.btn_adicionar = ttk.Button(frame, text="Adicionar nota", command=self._adicionar_nota)
        self.btn_adicionar.grid(row=3, column=3, sticky="e", pady=(6, 0))

        # Navegacao entre campos com Enter, sem depender do TAB
        self.entry_nf.bind("<Return>", lambda e: self._focar(self.entry_cliente))
        # Enter/Tab em Cliente e Ocorrência colam a sugestão (se houver) antes de avançar
        self.entry_cliente.bind("<Return>", self._aceitar_sugestao_cliente)
        self.entry_cliente.bind("<Tab>", self._aceitar_sugestao_cliente)
        self.entry_oc.bind("<Return>", self._aceitar_sugestao_ocorrencia)
        self.entry_oc.bind("<Tab>", self._aceitar_sugestao_ocorrencia)
        self.combo_sigla.bind("<Return>", lambda e: self._focar(self.entry_data))
        # Enter no ultimo campo (Data) equivale a clicar no botao "Adicionar nota"
        self.entry_data.bind("<Return>", self._acionar_botao_adicionar)
        self.btn_adicionar.bind("<Return>", self._acionar_botao_adicionar)

    def _acionar_botao_adicionar(self, event=None):
        self.btn_adicionar.invoke()
        return "break"

    def _configurar_navegacao_setas(self):
        """Permite mover entre os campos/botões do topo (NF, Cliente, Ocorrência,
        Sigla, Data, Adicionar nota, Buscar NF, Buscar, Filtrar por ocorrência,
        Limpar filtro e Somente notas com lembrete) usando as setas ↑/↓."""
        ordem = [
            self.entry_nf, self.entry_cliente, self.entry_oc, self.combo_sigla, self.entry_data,
            self.btn_adicionar, self.entry_busca, self.btn_buscar, self.combo_filtro,
            self.btn_limpar_filtro, self.chk_somente_lembrete,
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
            self.entry_data, self.entry_busca, self.combo_filtro,
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

        try:
            data_ocorrencia = dateutils.parse_data_usuario(self.var_data.get().strip())
        except ValueError as e:
            messagebox.showerror("Data inválida", str(e))
            return

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

        lembrete_codigo = None
        proximo_lembrete = None
        if occ.eh_ocorrencia_com_lembrete_sugerido(ocorrencia):
            popup = PopupLembrete(self, nf, ocorrencia, sigla, valor_inicial=100)
            if popup.aceitou:
                lembrete_codigo = popup.codigo_final
                _codigo, delta = dateutils.normalizar_codigo_lembrete(lembrete_codigo)
                proximo_lembrete = (datetime.now() + delta).isoformat()

        db.inserir_nota(nf, cliente, ocorrencia, sigla, data_ocorrencia,
                         lembrete_codigo, proximo_lembrete, agendamento_data)

        if cliente.lower() not in [c.lower() for c in db.listar_clientes()]:
            if messagebox.askyesno(
                "Cadastrar remetente",
                "Deseja cadastrar o remetente '%s' para facilitar a sugestão em próximas notas?" % cliente
            ):
                db.adicionar_cliente(cliente)

        self.var_nf.set("")
        self.var_cliente.set("")
        self.var_ocorrencia.set("")
        self.var_sigla.set("")
        self.var_data.set("0")
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
        ttk.Label(frame, text="Buscar NF (Ctrl+F):").pack(side="left")
        self.var_busca = tk.StringVar()
        self.entry_busca = ttk.Entry(frame, textvariable=self.var_busca, width=20)
        self.entry_busca.pack(side="left", padx=6)
        self.entry_busca.bind("<Return>", self._executar_busca)
        self.btn_buscar = ttk.Button(frame, text="Buscar", command=self._executar_busca)
        self.btn_buscar.pack(side="left")

    def _focar_busca(self, event=None):
        self.entry_busca.focus_set()
        self.entry_busca.select_range(0, tk.END)
        return "break"

    def _executar_busca(self, event=None):
        texto = self.var_busca.get().strip()
        if not texto.isdigit():
            messagebox.showinfo("Busca", "Digite um número de NF válido.")
            return
        nf = int(texto)
        alvo = None
        for nota_id, bloco in self.blocos.items():
            if bloco.nota_row["nf_numero"] == nf:
                alvo = nota_id
                break
        if alvo is None:
            messagebox.showinfo("Busca", "NF %d não encontrada entre as notas ativas." % nf)
            return
        self._destacar_nota(alvo)

    def _destacar_nota(self, nota_id):
        bloco = self.blocos.get(nota_id)
        if not bloco:
            return
        self._rolar_para(nota_id)
        bloco.lbl_cabecalho.configure(background="#fff2a8")
        self.after(1500, lambda: bloco.lbl_cabecalho.configure(
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
            anterior.lbl_cabecalho.configure(background=self.cget("bg"))
        self.nota_selecionada_id = nota_id
        bloco = self.blocos.get(nota_id)
        if bloco is not None:
            bloco.lbl_cabecalho.configure(background="#cfe8ff")
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
        ttk.Label(frame, text="Filtrar por ocorrência:").pack(side="left")
        self.var_filtro = tk.StringVar(value=self.OPCAO_TODAS)
        self.combo_filtro = ttk.Combobox(frame, textvariable=self.var_filtro, width=24, state="normal")
        self.combo_filtro.pack(side="left", padx=6)
        self.combo_filtro.bind("<KeyRelease>", self._filtrar_combo_ocorrencias)
        self.combo_filtro.bind("<Return>", self._aplicar_filtro_digitado)
        self.combo_filtro.bind("<<ComboboxSelected>>", lambda e: self.recarregar_lista())
        self.btn_limpar_filtro = ttk.Button(frame, text="Limpar filtro", command=self._limpar_filtro)
        self.btn_limpar_filtro.pack(side="left")

        self.var_somente_lembrete = tk.BooleanVar(value=False)
        self.chk_somente_lembrete = ttk.Checkbutton(
            frame, text="Somente notas com lembrete", variable=self.var_somente_lembrete,
            command=self.recarregar_lista)
        self.chk_somente_lembrete.pack(side="left", padx=(16, 0))

        self._atualizar_combobox_filtro()

    def _atualizar_combobox_filtro(self):
        valores = [self.OPCAO_TODAS] + db.listar_tipos_ocorrencia()
        self.combo_filtro["values"] = valores

    def _filtrar_combo_ocorrencias(self, event=None):
        """Enquanto o usuario digita, estreita as opcoes do combobox de filtro
        para agilizar a localizacao do tipo de ocorrencia desejado."""
        if event is not None and event.keysym in ("Return", "Up", "Down", "Tab"):
            return
        texto = self.var_filtro.get().strip().lower()
        tipos = [self.OPCAO_TODAS] + db.listar_tipos_ocorrencia()
        if texto:
            tipos = [t for t in tipos if texto in t.lower()]
        self.combo_filtro["values"] = tipos

    def _aplicar_filtro_digitado(self, event=None):
        """Ao pressionar Enter no filtro, resolve o texto digitado para um tipo
        de ocorrencia valido (ou 'Todas as ocorrencias') e aplica o filtro."""
        texto = self.var_filtro.get().strip()
        tipos = db.listar_tipos_ocorrencia()
        if not texto or texto.lower() == self.OPCAO_TODAS.lower():
            self.var_filtro.set(self.OPCAO_TODAS)
        else:
            sugestao = occ.sugerir_ocorrencia(texto, tipos)
            if sugestao:
                self.var_filtro.set(sugestao)
        self._atualizar_combobox_filtro()
        self.recarregar_lista()
        return "break"

    def _limpar_filtro(self):
        self.var_filtro.set(self.OPCAO_TODAS)
        self.var_somente_lembrete.set(False)
        self.recarregar_lista()

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
        self.canvas.create_window((0, 0), window=self.frame_lista, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))

        self.canvas.bind("<Up>", lambda e: self._mover_selecao(-1))
        self.canvas.bind("<Down>", lambda e: self._mover_selecao(1))
        self.canvas.bind("<Delete>", lambda e: self._resolver_via_teclado())
        self.canvas.bind("<Return>", lambda e: self._adicionar_tratativa_via_teclado())

    def recarregar_lista(self):
        for widget in self.frame_lista.winfo_children():
            widget.destroy()
        self.blocos = {}

        if hasattr(self, "combo_filtro"):
            self._atualizar_combobox_filtro()

        notas = db.listar_notas_ativas()
        filtro = self.var_filtro.get() if hasattr(self, "var_filtro") else self.OPCAO_TODAS
        if filtro and filtro != self.OPCAO_TODAS:
            notas = [n for n in notas if n["ocorrencia"].strip().lower() == filtro.strip().lower()]

        if hasattr(self, "var_somente_lembrete") and self.var_somente_lembrete.get():
            notas = [n for n in notas if n["lembrete_codigo"] is not None]

        for nota in notas:
            bloco = NotaBlock(self.frame_lista, self, nota)
            bloco.pack(fill="x", pady=4, padx=2)
            self.blocos[nota["id"]] = bloco

        if self.nota_selecionada_id not in self.blocos:
            self.nota_selecionada_id = None

    def mostrar_mensagem_flutuante(self, texto, event=None):
        x = self.winfo_pointerx()
        y = self.winfo_pointery()
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.geometry("+%d+%d" % (x + 10, y + 10))
        tk.Label(popup, text=texto, background="#333", foreground="white", padx=6, pady=3).pack()
        self.after(1000, popup.destroy)

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

    def remover_lembrete(self, nota_id):
        db.atualizar_campo_nota(nota_id, "lembrete_codigo", None)
        db.atualizar_campo_nota(nota_id, "proximo_lembrete", None)
        self.recarregar_lista()

    def adicionar_lembrete(self, nota_id):
        nota = db.obter_nota(nota_id)
        if nota is None:
            return
        popup = PopupLembrete(self, nota["nf_numero"], nota["ocorrencia"], nota["sigla"], valor_inicial=100)
        if popup.aceitou:
            codigo, delta = dateutils.normalizar_codigo_lembrete(popup.codigo_final)
            db.atualizar_campo_nota(nota_id, "lembrete_codigo", codigo)
            db.atualizar_campo_nota(nota_id, "proximo_lembrete", (datetime.now() + delta).isoformat())
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

    # ------------------------------------------------------------------
    # Verificacao periodica de lembretes / agendamentos / prioridades
    # ------------------------------------------------------------------
    def _checar_lembretes(self):
        agora = datetime.now()
        hoje_str = agora.strftime(dateutils.FORMATO)

        for nota in db.listar_notas_ativas():
            self._checar_lembrete_periodico(nota, agora)
            self._checar_agendamento(nota, agora, hoje_str)
            self._checar_prioridade(nota, agora, hoje_str)

        self.after(INTERVALO_VERIFICACAO_MS, self._checar_lembretes)

    def _checar_lembrete_periodico(self, nota, agora):
        if not nota["proximo_lembrete"]:
            return
        try:
            proximo = datetime.fromisoformat(nota["proximo_lembrete"])
        except ValueError:
            return
        if agora >= proximo:
            PopupAlerta(
                self, "Lembrete de NF",
                "Lembrete: NF %s / %s / %s ainda está pendente de tratativa."
                % (nota["nf_numero"], nota["ocorrencia"], nota["sigla"])
            )
            codigo, delta = dateutils.normalizar_codigo_lembrete(nota["lembrete_codigo"])
            db.atualizar_campo_nota(nota["id"], "proximo_lembrete", (agora + delta).isoformat())
            self.recarregar_lista()

    def _checar_agendamento(self, nota, agora, hoje_str):
        if not nota["agendamento_data"]:
            return
        try:
            data_agendamento = dateutils.data_str_para_datetime(nota["agendamento_data"])
        except ValueError:
            return

        um_dia_antes = (data_agendamento - timedelta(days=1)).date()
        eh_filial = occ.eh_unidade_filial(nota["sigla"])

        if agora.date() == um_dia_antes and agora.hour >= 14 and (agora.hour > 14 or agora.minute >= 30):
            tipo = "agendamento_filial" if eh_filial else "agendamento_parceiro"
            if not db.alerta_ja_disparado(nota["id"], tipo, hoje_str):
                PopupAlerta(
                    self, "Lembrete de agendamento",
                    "Agendamento amanhã!\nNF: %s / Remetente: %s / Sigla: %s"
                    % (nota["nf_numero"], nota["cliente"], nota["sigla"])
                )
                db.registrar_alerta_disparado(nota["id"], tipo, hoje_str)
            return

        if not eh_filial and not nota["verificado_parceiro"]:
            for hora, tipo in ((10, "parceiro_10h"), (16, "parceiro_16h")):
                if agora.hour == hora and not db.alerta_ja_disparado(nota["id"], tipo, hoje_str):
                    popup = PopupAlerta(
                        self, "Acompanhamento de parceiro",
                        "Verifique o status de entrega da NF %s (%s) junto à unidade parceira %s."
                        % (nota["nf_numero"], nota["cliente"], nota["sigla"]),
                        com_verificado=True,
                    )
                    db.registrar_alerta_disparado(nota["id"], tipo, hoje_str)
                    if popup.verificado:
                        db.atualizar_campo_nota(nota["id"], "verificado_parceiro", 1)
                        self.recarregar_lista()

    def _checar_prioridade(self, nota, agora, hoje_str):
        if not occ.eh_ocorrencia_prioridade(nota["ocorrencia"]):
            return
        for hora, tipo in ((10, "prioridade_10h"), (17, "prioridade_17h")):
            if agora.hour == hora and not db.alerta_ja_disparado(nota["id"], tipo, hoje_str):
                PopupAlerta(
                    self, "Prioridade de entrega",
                    "NF prioritária: %s / Cliente: %s / Sigla: %s"
                    % (nota["nf_numero"], nota["cliente"], nota["sigla"])
                )
                db.registrar_alerta_disparado(nota["id"], tipo, hoje_str)
