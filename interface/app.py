# -*- coding: utf-8 -*-
"""
Janela principal. A logica esta dividida em mixins (ver pasta interface/).
"""

import tkinter as tk
from tkinter import ttk, messagebox

from nucleo import aparencia
from nucleo import backup
from nucleo import database as db
from nucleo.desfazer import PilhaDesfazer
from nucleo import versao
from interface import tema
from interface.icone import aplicar_icone
from interface.dialogs import JanelaAparencia
from interface.layout import LayoutMixin
from interface.janelas import JanelasMixin
from interface.manutencao import ManutencaoMixin
from interface.relatorios import RelatoriosMixin
from interface.formulario import FormularioMixin
from interface.busca_filtro import BuscaFiltroMixin
from interface.lista_notas import ListaNotasMixin
from interface.edicao_notas import EdicaoNotasMixin


class App(LayoutMixin, JanelasMixin, ManutencaoMixin, RelatoriosMixin, FormularioMixin, BuscaFiltroMixin,
          ListaNotasMixin, EdicaoNotasMixin, tk.Tk):
    """Janela principal. Cada mixin agrupa um assunto (ver docstring de cada modulo)."""


    def __init__(self):
        super().__init__()
        self.title("Auxiliador de Processos Logísticos - SAC")
        self.minsize(480, 400)
        aplicar_icone(self)
        self._janelas_unicas = {}  # chave da janela -> Toplevel aberto (ver interface/janelas.py)
        self._restaurar_posicao_janela("1100x720")  # abre onde o usuario fechou da ultima vez

        self.pilha_desfazer = PilhaDesfazer()
        db.init_db()
        db.limpar_historico_expirado(60)
        aparencia.carregar()
        self._aplicar_estilos_aparencia()

        self._canvas_rolagem = {}  # janela secundaria -> canvas rolavel dela (ver _registrar_rolagem)
        self.blocos = {}  # nota_id -> NotaBlock
        self.nota_selecionada_id = None
        self.filtro_busca_texto = ""  # filtro ativo de busca por cliente/sigla (minusculo, ou vazio)
        self.filtro_busca_ids = None  # ids de notas encontradas por numero/texto nas tratativas (ou None)
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

        # Verificacao de atualizacao em segundo plano: nao deve atrasar a
        # abertura do sistema nem travar a interface, por isso roda numa
        # thread separada e so volta a mexer na tela (via self.after) se
        # encontrar uma versao nova.
        self.after(1500, self._verificar_atualizacoes_automatico)

        # Fechar a janela (X ou menu Sair) gera um backup datado do banco.
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    # ------------------------------------------------------------------
    # Menu superior
    # ------------------------------------------------------------------
    def _abrir_sobre(self):
        """Aba "Sobre": informacoes do desenvolvedor."""
        if self._reapresentar_janela("sobre"):
            return
        janela = tk.Toplevel(self)
        self._registrar_janela("sobre", janela)
        janela.title("Sobre")
        janela.resizable(False, False)
        quadro = ttk.Frame(janela, padding=24)
        quadro.pack(fill="both", expand=True)
        ttk.Label(quadro, text="Auxiliador de Processos Logísticos - SAC",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")
        ttk.Label(quadro, text="Versão %s" % versao.VERSAO).pack(anchor="w", pady=(0, 14))
        ttk.Label(quadro, text="Desenvolvido por Ithalo Willian").pack(anchor="w")
        ttk.Label(quadro, text="Contato: ithalowillian@hotmail.com").pack(anchor="w", pady=(2, 14))

        def copiar_contato():
            self.clipboard_clear()
            self.clipboard_append("ithalowillian@hotmail.com")
            self.mostrar_mensagem_flutuante("E-mail copiado!")

        botoes = ttk.Frame(quadro)
        botoes.pack(fill="x")
        ttk.Button(botoes, text="Copiar e-mail", command=copiar_contato).pack(side="left")
        ttk.Button(botoes, text="Fechar", command=janela.destroy).pack(side="right")
        janela.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - janela.winfo_reqwidth()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - janela.winfo_reqheight()) // 2
        janela.geometry("+%d+%d" % (max(x, 0), max(y, 0)))

    def _montar_menu(self):
        barra = tk.Menu(self)

        m_arquivo = tk.Menu(barra, tearoff=0)
        m_arquivo.add_command(label="Criar backup agora", command=self._criar_backup_manual)
        m_arquivo.add_command(label="Exportar tudo (salvaguarda)...", command=self._exportar_tudo)
        m_arquivo.add_separator()
        m_arquivo.add_command(label="Verificar atualizações...", command=self._verificar_atualizacoes_manual)
        m_arquivo.add_separator()
        m_arquivo.add_command(label="Sair", command=self._ao_fechar)
        barra.add_cascade(label="Arquivo", menu=m_arquivo)

        m_editar = tk.Menu(barra, tearoff=0)
        m_editar.add_command(label="Desfazer última alteração", accelerator="Ctrl+Z",
                              command=self.desfazer_ultima_alteracao)
        m_editar.add_separator()
        m_editar.add_command(label="Nova nota", accelerator="Ctrl+N", command=self.atalho_nova_nota)
        m_editar.add_command(label="Ir para a busca", accelerator="Ctrl+F", command=self._focar_busca)
        m_editar.add_command(label="Atualizar lista", accelerator="F5", command=self.atalho_atualizar_lista)
        barra.add_cascade(label="Editar", menu=m_editar)
        # Ctrl+Z so na janela principal: campos de texto com desfazer proprio (formulario,
        # dialogos) tratam o atalho antes e nao disparam o Desfazer das notas.
        self.bind("<Control-z>", self.desfazer_ultima_alteracao)
        self.bind("<Control-Z>", self.desfazer_ultima_alteracao)
        # Atalhos globais da janela principal (Ctrl+F, que ja existia, esta em _montar_busca).
        self.bind("<Control-n>", self.atalho_nova_nota)
        self.bind("<Control-N>", self.atalho_nova_nota)
        self.bind("<F5>", self.atalho_atualizar_lista)

        m_cadastros = tk.Menu(barra, tearoff=0)
        m_cadastros.add_command(label="Empresas parceiras (Agex, Risso, etc.)",
                                 command=self._gerenciar_empresas_parceiras)
        m_cadastros.add_command(label="Tipos de ocorrência",
                                 command=self._gerenciar_tipos_ocorrencia)
        m_cadastros.add_command(label="Remetentes",
                                 command=self._gerenciar_clientes)
        barra.add_cascade(label="Cadastros", menu=m_cadastros)

        barra.add_command(label="Aparência", command=self._abrir_aparencia)
        m_relatorio = tk.Menu(barra, tearoff=0)
        m_relatorio.add_command(label="Relatório de morosidade", command=self._abrir_relatorio)
        m_relatorio.add_command(label="Clientes e CNPJ", command=self._abrir_clientes_cnpj)
        barra.add_cascade(label="Relatório", menu=m_relatorio)
        barra.add_command(label="Histórico", command=self._abrir_historico)
        barra.add_command(label="Sobre", command=self._abrir_sobre)

        self.config(menu=barra)

    # ------------------------------------------------------------------
    # Aparência (cores e negrito)
    # ------------------------------------------------------------------
    def _aplicar_estilos_aparencia(self):
        """Tema visual (cores, fonte e estilos ttk). As cores/negrito escolhidos em "Aparência"
        sao aplicados pelos proprios cartoes de nota (ver NotaBlock)."""
        tema.aplicar(self)

    def _abrir_aparencia(self):
        if getattr(self, "_aparencia_aberta", False):  # janela modal: so uma por vez
            return
        self._aparencia_aberta = True
        try:
            janela = JanelaAparencia(self, aparencia.obter())
        finally:
            self._aparencia_aberta = False
        if janela.acao == "salvar":
            if not aparencia.salvar(janela.config_resultado):
                messagebox.showwarning(
                    "Aparência", "Não foi possível gravar o arquivo de preferências; "
                    "as mudanças valem só até fechar o sistema.", parent=self)
        elif janela.acao == "restaurar":
            aparencia.restaurar_padrao()
        else:
            return
        self._aplicar_estilos_aparencia()
        self.recarregar_lista()

    # ------------------------------------------------------------------
    # Backup e exportação
    # ------------------------------------------------------------------
    def _ao_fechar(self):
        """Cria um backup automático datado do banco antes de fechar. Falha
        no backup nunca impede o fechamento (criar_backup trata os erros)."""
        try:
            self._salvar_posicao_janela()
            backup.criar_backup("automatico")
        finally:
            self.destroy()

