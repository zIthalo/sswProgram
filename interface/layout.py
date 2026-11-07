# -*- coding: utf-8 -*-
"""
Estrutura da janela principal: painel lateral "Nova ocorrencia" + area principal
(resumo, busca, filtros e lista de cartoes) e o comportamento RESPONSIVO.

Modos (so mudam a disposicao; nenhum dado, consulta ou regra e alterado):
  - amplo (janela >= 900 px): painel lateral fixo a esquerda; o botao "« Painel" o recolhe.
  - compacto (janela < 900 px, ex.: tela dividida ao meio / janela pequena): o painel some e o
    formulario vira uma "gaveta" no topo (botao "+ Nova nota" ou Ctrl+N), que fecha sozinha
    ao registrar a nota ou com Esc.
  - estreito (area principal < 720 px): resumo encurtado e filtros em duas linhas.
Os eventos de redimensionamento so fazem trabalho quando um limite e cruzado.
"""

import tkinter as tk
from tkinter import ttk

from interface import tema
from interface.nota_block import dias_em_tratativas

LARGURA_LATERAL = 290
LARGURA_MIN_PAINEL = 900      # janela abaixo disso: modo compacto
LARGURA_ESTREITA = 720        # area principal abaixo disso: modo estreito


class LayoutMixin:
    # ------------------------------------------------------------------
    # Estrutura + formulario (painel lateral / gaveta)
    # ------------------------------------------------------------------
    def _montar_formulario(self):
        P, LAT, f = tema.PALETA, tema.LATERAL, tema.FONTE
        self._modo_compacto = False
        self._estreito = False
        self._painel_visivel = True
        self._painel_pref = True       # preferencia do usuario no modo amplo (botao « Painel)

        self._corpo = tk.Frame(self, background=P["fundo"])
        self._corpo.pack(fill="both", expand=True)
        self._lateral = tk.Frame(self._corpo, background=LAT["fundo"], width=LARGURA_LATERAL)
        self._lateral.pack(side="left", fill="y")
        self._lateral.grid_propagate(False)
        self._lateral.columnconfigure(0, weight=1)
        self._lateral.columnconfigure(1, weight=1)
        self._principal = tk.Frame(self._corpo, background=P["fundo"])
        self._principal.pack(side="top", fill="both", expand=True)
        L = self._lateral

        self._form_cab = [
            tk.Label(L, text="SAC Logística", font=(f, 15, "bold"), foreground=LAT["texto"],
                     background=LAT["fundo"]),
            tk.Label(L, text="Auxiliador de processos logísticos", font=(f, 8, "bold"), foreground=LAT["texto"],
                     background=LAT["fundo"]),
            tk.Frame(L, height=1, background=LAT["linha"]),
            tk.Label(L, text="NOVA OCORRÊNCIA", font=(f, 8, "bold"), foreground=LAT["texto"],
                     background=LAT["fundo"]),
        ]

        self._form_blocos = []

        def campo(texto, fabrica, sugestao_var=None):
            bloco = tk.Frame(L, background=LAT["fundo"])
            ttk.Label(bloco, text=texto, style="Lateral.TLabel").pack(anchor="w", pady=(6, 2))
            w = fabrica(bloco)
            w.pack(fill="x")
            if sugestao_var is not None:
                ttk.Label(bloco, textvariable=sugestao_var, style="Lateral.TLabel", wraplength=240).pack(
                    anchor="w", pady=(2, 0))
            self._form_blocos.append(bloco)
            return w

        self.var_nf = tk.StringVar()
        self.entry_nf = campo("NF (CTRL + N):", lambda m: ttk.Entry(m, textvariable=self.var_nf))
        self.var_cliente = tk.StringVar()
        self._suggestion_cliente_var = tk.StringVar(value="")
        self.entry_cliente = campo("Cliente/Remetente:", lambda m: ttk.Entry(m, textvariable=self.var_cliente),
                                   self._suggestion_cliente_var)
        self.entry_cliente.bind("<KeyRelease>", self._sugerir_cliente)
        self.var_ocorrencia = tk.StringVar()
        self.entry_oc = campo("Ocorrência:", lambda m: ttk.Entry(m, textvariable=self.var_ocorrencia),
                              self._suggestion_var)
        self.entry_oc.bind("<KeyRelease>", self._sugerir_ocorrencia)
        self.lbl_sugestao = None
        self.var_sigla = tk.StringVar()
        self.combo_sigla = campo("Sigla/Empresa:", lambda m: ttk.Combobox(m, textvariable=self.var_sigla))
        self._atualizar_combobox_sigla()
        self.btn_adicionar = ttk.Button(L, text="Adicionar nota", style="Acento.TButton", command=self._adicionar_nota)

        self._form_rod = [
            tk.Label(L, text="ATALHOS", font=(f, 8, "bold"), foreground=LAT["texto"], background=LAT["fundo"]),
            tk.Label(L, text="Ctrl+N  nova nota\nCtrl+F  buscar\nF5  atualizar\nCtrl+Z  desfazer", font=(f, 8, "bold"),
                     justify="left", foreground=LAT["texto"], background=LAT["fundo"]),
        ]
        self._widgets_form = (self.entry_nf, self.entry_cliente, self.entry_oc, self.combo_sigla,
                              self.btn_adicionar)
        self._organizar_form(False)

        self.entry_nf.bind("<Return>", lambda e: self._focar(self.entry_cliente))
        self.entry_cliente.bind("<Return>", self._aceitar_sugestao_cliente)
        self.entry_cliente.bind("<Tab>", self._aceitar_sugestao_cliente)
        self.entry_oc.bind("<Return>", self._aceitar_sugestao_ocorrencia)
        self.entry_oc.bind("<Tab>", self._aceitar_sugestao_ocorrencia)
        self.combo_sigla.bind("<Return>", self._acionar_botao_adicionar)
        self.btn_adicionar.bind("<Return>", self._acionar_botao_adicionar)
        for w in self._widgets_form:
            w.bind("<Escape>", self._fechar_gaveta)
        self.bind("<Configure>", self._ao_mudar_tamanho, add="+")

    def _organizar_form(self, compacto):
        """Painel lateral: uma coluna com titulo e atalhos. Gaveta: 2 colunas, so os campos."""
        L = self._lateral
        titulo, sub, linha, secao = self._form_cab
        if not compacto:
            titulo.grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 0))
            sub.grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 18))
            linha.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20)
            secao.grid(row=3, column=0, columnspan=2, sticky="w", padx=20, pady=(16, 6))
            for i, bloco in enumerate(self._form_blocos):
                bloco.grid(row=4 + i, column=0, columnspan=2, sticky="new", padx=20, pady=0)
            self.btn_adicionar.grid(row=8, column=0, columnspan=2, sticky="ew", padx=20, pady=(18, 0))
            L.rowconfigure(9, weight=1)
            self._form_rod[0].grid(row=10, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 4))
            self._form_rod[1].grid(row=11, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 18))
        else:
            for w in self._form_cab + self._form_rod:
                w.grid_remove()
            L.rowconfigure(9, weight=0)
            for i, bloco in enumerate(self._form_blocos):
                bloco.grid(row=i // 2, column=i % 2, columnspan=1, sticky="new",
                           padx=(14, 6) if i % 2 == 0 else (6, 14), pady=0)
            self.btn_adicionar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(10, 14))
        L.grid_propagate(compacto)     # painel: largura fixa; gaveta: altura pelo conteudo
        if not compacto:
            L.configure(width=LARGURA_LATERAL)

    def _focar(self, widget):
        # num campo do formulario com o painel fechado (modo compacto), abre a gaveta antes
        if widget in self._widgets_form and not self._painel_visivel:
            self._mostrar_painel(True)
        widget.focus_set()

    def atalho_nova_nota(self, event=None):
        self._mostrar_painel(True)          # Ctrl+N sempre mostra o formulario
        return super().atalho_nova_nota(event)

    def _adicionar_nota(self):
        tinha_dados = bool(self.var_nf.get().strip() or self.var_cliente.get().strip())
        super()._adicionar_nota()
        # modo compacto: nota registrada (campos limpos) -> a gaveta se recolhe e devolve a tela a lista
        if (self._modo_compacto and self._painel_visivel and tinha_dados
                and not self.var_nf.get() and not self.var_cliente.get()):
            self._mostrar_painel(False)
            self.canvas.focus_set()

    def _fechar_gaveta(self, event=None):
        if self._modo_compacto and self._painel_visivel:
            self._mostrar_painel(False)
            self.canvas.focus_set()
            return "break"

    # ------------------------------------------------------------------
    # Topo da area principal: resumo + busca + filtros
    # ------------------------------------------------------------------
    def _montar_busca(self):
        P, f = tema.PALETA, tema.FONTE
        topo = ttk.Frame(self._principal, style="Barra.TFrame", padding=(20, 14, 20, 12))
        topo.pack(fill="x")
        tk.Frame(self._principal, height=1, background=P["borda"]).pack(fill="x")
        self._topo = topo

        resumo = ttk.Frame(topo, style="Barra.TFrame")
        resumo.pack(fill="x")
        self.btn_painel = ttk.Button(resumo, text="« Painel", command=self._alternar_painel)
        self.btn_painel.pack(side="right")
        self._kpis = {}
        self._kpi_titulos = {}
        for chave, longo, curto in (("lista", "NA LISTA", "LISTA"), ("agendadas", "AGENDAMENTOS", "AGEND."),
                                    ("criticas", "MAIS DE 7 DIAS", "+7 DIAS")):
            caixa = tk.Frame(resumo, background=P["superficie"], highlightthickness=1,
                             highlightbackground=P["borda"], padx=14, pady=6)
            caixa.pack(side="left", padx=(0, 10))
            num = tk.Label(caixa, text="0", font=(f, 16, "bold"), background=P["superficie"], foreground=P["texto"])
            num.pack(anchor="w")
            rotulo = tk.Label(caixa, text=longo, font=(f, 7, "bold"), background=P["superficie"],
                              foreground=P["suave"])
            rotulo.pack(anchor="w")
            self._kpis[chave] = num
            self._kpi_titulos[chave] = (caixa, rotulo, longo, curto)

        linha = ttk.Frame(topo, style="Barra.TFrame")
        linha.pack(fill="x", pady=(12, 0))
        linha.columnconfigure(0, weight=1)
        ttk.Label(linha, text="Buscar NF / Cliente / Sigla (Ctrl+F)", style="Barra.TLabel").grid(
            row=0, column=0, sticky="w")
        self.var_busca = tk.StringVar()
        self.entry_busca = ttk.Entry(linha, textvariable=self.var_busca)
        self.entry_busca.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.entry_busca.bind("<KeyRelease>", self._sugerir_busca)
        self.entry_busca.bind("<Return>", self._executar_busca)
        self.entry_busca.bind("<Tab>", self._aceitar_sugestao_busca)
        self.btn_buscar = ttk.Button(linha, text="Buscar", command=self._executar_busca)
        self.btn_buscar.grid(row=1, column=1)
        self._suggestion_busca_var = tk.StringVar(value="")
        ttk.Label(linha, textvariable=self._suggestion_busca_var, style="Barra.TLabel").grid(
            row=2, column=0, sticky="w")
        self._principal.bind("<Configure>", self._ao_mudar_principal)

    def _montar_filtro(self):
        self._linha_filtro = ttk.Frame(self._topo, style="Barra.TFrame")
        g = self._linha_filtro
        g.pack(fill="x", pady=(6, 0))
        self._lbl_filtro = ttk.Label(g, text="Ocorrência", style="Barra.TLabel")
        self.var_filtro = tk.StringVar(value=self.OPCAO_TODAS)
        self.combo_filtro = ttk.Combobox(g, textvariable=self.var_filtro, width=24, state="normal")
        self.combo_filtro.bind("<KeyRelease>", self._filtrar_combo_ocorrencias)
        self.combo_filtro.bind("<Return>", self._aplicar_filtro_digitado)
        self.combo_filtro.bind("<<ComboboxSelected>>", lambda e: self.recarregar_lista(resetar_scroll=True))
        self.btn_atualizar = ttk.Button(g, text="Atualizar (F5)", command=self.atalho_atualizar_lista)
        self.btn_limpar_filtro = ttk.Button(g, text="Limpar filtro", command=self._limpar_filtro)
        self.btn_copiar_filtradas = ttk.Button(g, text="Copiar notas filtradas", command=self.copiar_notas_filtradas)
        self._organizar_filtro(False)
        self._atualizar_combobox_filtro()

    def _organizar_filtro(self, estreito):
        """Largo: tudo em uma linha. Estreito: rotulo, combo e os 3 botoes em linhas proprias."""
        g = self._linha_filtro
        for w in (self._lbl_filtro, self.combo_filtro, self.btn_atualizar, self.btn_limpar_filtro,
                  self.btn_copiar_filtradas):
            w.grid_forget()
        if estreito:
            for c in range(3):
                g.columnconfigure(c, weight=1, uniform="filtro")
            for c in (3, 4):
                g.columnconfigure(c, weight=0, uniform="")
            self._lbl_filtro.grid(row=0, column=0, columnspan=3, sticky="w")
            self.combo_filtro.grid(row=1, column=0, columnspan=3, sticky="ew")
            self.btn_atualizar.grid(row=2, column=0, sticky="ew", pady=(6, 0))
            self.btn_limpar_filtro.grid(row=2, column=1, sticky="ew", padx=6, pady=(6, 0))
            self.btn_copiar_filtradas.grid(row=2, column=2, sticky="ew", pady=(6, 0))
            self.btn_copiar_filtradas.configure(text="Copiar filtradas")
        else:
            for c in range(5):
                g.columnconfigure(c, weight=0, uniform="")
            self._lbl_filtro.grid(row=0, column=0, padx=(0, 6))
            self.combo_filtro.grid(row=0, column=1)
            self.btn_atualizar.grid(row=0, column=2, padx=(8, 0))
            self.btn_limpar_filtro.grid(row=0, column=3, padx=(6, 0))
            self.btn_copiar_filtradas.grid(row=0, column=4, padx=(6, 0))
            self.btn_copiar_filtradas.configure(text="Copiar notas filtradas")

    def _montar_lista(self):
        P = tema.PALETA
        self._container_lista = tk.Frame(self._principal, background=P["fundo"])
        self._container_lista.pack(fill="both", expand=True, padx=(20, 12), pady=(14, 12))
        container = self._container_lista
        self.canvas = tk.Canvas(container, highlightthickness=0, background=P["fundo"])
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self._ao_rolar_lista)
        self.frame_lista = ttk.Frame(self.canvas)
        self.frame_lista.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._frame_lista_janela = self.canvas.create_window((0, 0), window=self.frame_lista, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._largura_lista_atual = 760
        self._redimensionar_job = None
        self.canvas.bind("<Configure>", self._ao_redimensionar_lista)
        self._rolagem_job = None
        self.canvas.bind_all("<MouseWheel>", self._ao_rolar_roda_mouse)
        self.canvas.bind("<Up>", lambda e: self._mover_selecao(-1))
        self.canvas.bind("<Down>", lambda e: self._mover_selecao(1))
        self.canvas.bind("<Delete>", lambda e: self._resolver_via_teclado())
        self.canvas.bind("<Return>", lambda e: self._adicionar_tratativa_via_teclado())
        # Ao abrir o sistema a lista e montada ANTES de a janela aparecer (sem largura real): assim que
        # ela fica visivel, mede tudo de novo para a lista ja abrir completa, sem precisar do F5.
        self.bind("<Map>", self._ao_exibir_janela, add="+")
        self.canvas.bind("<Control-c>", self._copiar_selecao_da_nota)
        self.canvas.bind("<Control-C>", self._copiar_selecao_da_nota)

    def _ao_exibir_janela(self, event):
        if event.widget is not self or getattr(self, "_lista_ja_ajustada", False):
            return
        self._lista_ja_ajustada = True
        for atraso in (20, 250):          # a 2a passada cobre janelas que o Windows posiciona depois
            self.after(atraso, self._reajustar_lista)

    def _reajustar_lista(self):
        try:
            self.update_idletasks()
            self._aplicar_redimensionamento_blocos()
        except tk.TclError:
            pass

    def _copiar_selecao_da_nota(self, event=None):
        """Ctrl+C na lista: copia o texto que o usuario selecionou com o mouse num cartao."""
        bloco = self.blocos.get(self.nota_selecionada_id)
        if bloco is not None:
            bloco.copiar_selecao()
        return "break"

    # ------------------------------------------------------------------
    # Resumo (calculado com o que ja esta carregado: nenhuma consulta nova ao banco)
    # ------------------------------------------------------------------
    def _atualizar_resumo(self):
        notas = [b.nota_row for b in self.blocos.values()]
        self._kpis["lista"].configure(text=str(len(notas)))
        self._kpis["agendadas"].configure(text=str(sum(1 for n in notas if n["agendamento_data"])))
        criticas = sum(1 for n in notas if dias_em_tratativas(n["criado_em"]) > 7)
        self._kpis["criticas"].configure(text=str(criticas),
                                         foreground="#DC2626" if criticas else tema.PALETA["texto"])

    def _recarregar_lista_impl(self, resetar_scroll=False):
        super()._recarregar_lista_impl(resetar_scroll)
        self._atualizar_resumo()

    def _adicionar_bloco_rapido(self, nota):
        super()._adicionar_bloco_rapido(nota)
        self._atualizar_resumo()

    def _remover_bloco_rapido(self, nota_id):
        super()._remover_bloco_rapido(nota_id)
        self._atualizar_resumo()

    # ------------------------------------------------------------------
    # Responsividade
    # ------------------------------------------------------------------
    def _texto_btn_painel(self):
        if self._modo_compacto:
            return "× Fechar" if self._painel_visivel else "+ Nova nota"
        return "« Painel" if self._painel_visivel else "» Painel"

    def _mostrar_painel(self, visivel):
        if visivel == self._painel_visivel:
            return
        self._painel_visivel = visivel
        if visivel:
            if self._modo_compacto:
                self._lateral.pack(side="top", fill="x", before=self._principal)
            else:
                self._lateral.pack(side="left", fill="y", before=self._principal)
        else:
            self._lateral.pack_forget()
        self.btn_painel.configure(text=self._texto_btn_painel())

    def _alternar_painel(self):
        novo = not self._painel_visivel
        if not self._modo_compacto:
            self._painel_pref = novo
        self._mostrar_painel(novo)
        if novo and self._modo_compacto:
            self.entry_nf.focus_set()

    def _aplicar_modo(self, compacto):
        if compacto == self._modo_compacto:
            return
        self._modo_compacto = compacto
        visivel_antes = self._painel_visivel
        if visivel_antes:
            self._lateral.pack_forget()
            self._painel_visivel = False
        self._organizar_form(compacto)
        self.btn_painel.configure(style="Acento.TButton" if compacto else "TButton")
        self._mostrar_painel(False if compacto else self._painel_pref)
        self.btn_painel.configure(text=self._texto_btn_painel())

    def _ao_mudar_tamanho(self, event):
        if event.widget is self:
            self._aplicar_modo(event.width < LARGURA_MIN_PAINEL)

    def _ao_mudar_principal(self, event):
        estreito = event.width < LARGURA_ESTREITA
        if estreito == self._estreito:
            return
        self._estreito = estreito
        self._organizar_filtro(estreito)
        for caixa, rotulo, longo, curto in self._kpi_titulos.values():
            rotulo.configure(text=curto if estreito else longo)
            caixa.configure(padx=8 if estreito else 14)
            caixa.pack_configure(padx=(0, 6 if estreito else 10))
        self._topo.configure(padding=(10, 10, 10, 8) if estreito else (20, 14, 20, 12))
        self._container_lista.pack_configure(padx=(10, 4) if estreito else (20, 12))
