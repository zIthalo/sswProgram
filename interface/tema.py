# -*- coding: utf-8 -*-
"""
Tema visual do sistema: paleta, fonte e estilos ttk.

Somente estilo (cores, espacos, fontes): nenhum efeito, animacao ou imagem, por isso o
custo de desempenho e praticamente zero. Usa o tema "clam" do ttk (desenhado pelo proprio
Tk), que fica igual em qualquer Windows (7, 10, 11) - o tema nativo muda de um Windows
para outro.
"""

from tkinter import font as tkfont
from tkinter import ttk

PALETA = {
    "fundo": "#EEF1F6", "superficie": "#FFFFFF", "borda": "#E2E8F0", "texto": "#0F172A", "suave": "#64748B",
    "suave_forte": "#475569", "acento": "#4F46E5", "acento_hover": "#4338CA", "selecao": "#EEF2FF",
    "botao": "#F1F5F9", "botao_hover": "#E2E8F0", "borda_botao": "#CBD5E1", "rolagem": "#CBD5E1",
    "busca": "#FEF3A8", "selecao_texto": "#C7D2FE",
}
LATERAL = {"fundo": "#0F172A", "texto": "#F8FAFC", "suave": "#94A3B8", "linha": "#1E293B"}

# Cores dos "chips" de tipo de ocorrencia (fundo, texto). Tipos sem cor propria usam CHIP_PADRAO.
CHIPS = {
    "AGENDAMENTO": ("#FEF3C7", "#92400E"),
    "REENTREGA": ("#DBEAFE", "#1E40AF"),
    "LOCALIZAÇÃO": ("#EDE9FE", "#5B21B6"),
    "PRIORIZAR ENTREGA": ("#FEE2E2", "#991B1B"),
    "COMPROVANTE": ("#CCFBF1", "#115E59"),
    "DEVOLUÇÃO": ("#FFEDD5", "#9A3412"),
    "MUDOU-SE": ("#E5E7EB", "#374151"),
    "ACOMPANHAR": ("#E0F2FE", "#075985"),
}
CHIP_PADRAO = ("#E5E7EB", "#374151")
CHIP_SIGLA = ("#E2E8F0", "#334155")

PREFERENCIA_FONTES = ("Segoe UI", "Inter", "Noto Sans", "Helvetica Neue", "DejaVu Sans", "Arial")
FONTE = "TkDefaultFont"   # definida por aplicar()


def cor_urgencia(dias):
    """Faixa lateral do cartao: verde (ate 2 dias), ambar (3 a 7), vermelho (mais de 7)."""
    if dias > 7:
        return "#DC2626"
    if dias >= 3:
        return "#D97706"
    return "#16A34A"


def escolher_fonte(raiz):
    """Primeira fonte disponivel da lista: Segoe UI no Windows (ja vem instalada)."""
    disponiveis = set(tkfont.families(raiz))
    for nome in PREFERENCIA_FONTES:
        if nome in disponiveis:
            return nome
    return "TkDefaultFont"


def aplicar(raiz):
    """Configura o tema e os estilos ttk. Retorna o nome da fonte escolhida."""
    global FONTE
    p = PALETA
    FONTE = fonte = escolher_fonte(raiz)
    st = ttk.Style(raiz)
    st.theme_use("clam")
    raiz.configure(background=p["fundo"])
    # janelas secundarias (dialogos, relatorio...) herdam o mesmo fundo
    raiz.option_add("*Toplevel.background", p["fundo"])
    raiz.option_add("*TCombobox*Listbox.font", (fonte, 10))
    raiz.option_add("*TCombobox*Listbox.selectBackground", p["acento"])
    raiz.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    raiz.option_add("*Menu.font", (fonte, 10))

    st.configure(".", font=(fonte, 10), background=p["fundo"], foreground=p["texto"],
                 bordercolor=p["borda"], lightcolor=p["fundo"], darkcolor=p["fundo"],
                 troughcolor=p["fundo"], focuscolor=p["acento"], insertcolor=p["texto"])
    st.configure("TFrame", background=p["fundo"])
    st.configure("TLabel", background=p["fundo"], foreground=p["texto"])
    st.configure("TLabelframe", background=p["fundo"], bordercolor=p["borda"])
    st.configure("TLabelframe.Label", background=p["fundo"], foreground=p["suave_forte"])
    st.configure("Cartao.TFrame", background=p["superficie"], bordercolor=p["borda"],
                 lightcolor=p["borda"], darkcolor=p["borda"], relief="solid", borderwidth=1)
    st.configure("CartaoSel.TFrame", background=p["selecao"], bordercolor=p["acento"],
                 lightcolor=p["acento"], darkcolor=p["acento"], relief="solid", borderwidth=1)
    st.configure("Lateral.TFrame", background=LATERAL["fundo"])
    st.configure("Lateral.TLabel", background=LATERAL["fundo"], foreground=LATERAL["texto"], font=(fonte, 8, "bold"))
    st.configure("Barra.TFrame", background=p["superficie"])
    st.configure("Barra.TLabel", background=p["superficie"], foreground=p["suave"], font=(fonte, 8))

    for nome in ("TEntry", "TCombobox", "TSpinbox"):
        st.configure(nome, fieldbackground="#ffffff", foreground=p["texto"], bordercolor=p["borda"],
                     lightcolor="#ffffff", darkcolor="#ffffff", padding=(8, 6), arrowcolor=p["suave"])
        st.map(nome, bordercolor=[("focus", p["acento"])], lightcolor=[("focus", p["acento"])],
               darkcolor=[("focus", p["acento"])])
    st.map("TCombobox", fieldbackground=[("readonly", "#ffffff")])

    st.configure("TButton", padding=(12, 6), background=p["botao"], foreground=p["texto"],
                 bordercolor=p["borda_botao"], lightcolor=p["botao"], darkcolor=p["botao"],
                 relief="flat", borderwidth=1, focusthickness=1)
    st.map("TButton", background=[("active", p["botao_hover"]), ("pressed", p["botao_hover"])],
           bordercolor=[("focus", p["acento"])])
    st.configure("Acento.TButton", background=p["acento"], foreground="#ffffff", bordercolor=p["acento"],
                 lightcolor=p["acento"], darkcolor=p["acento"], font=(fonte, 10, "bold"), padding=(14, 7))
    st.map("Acento.TButton", background=[("active", p["acento_hover"]), ("pressed", p["acento_hover"])],
           foreground=[("active", "#ffffff")], bordercolor=[("active", p["acento_hover"])])

    st.configure("Vertical.TScrollbar", background=p["rolagem"], troughcolor=p["fundo"],
                 bordercolor=p["fundo"], lightcolor=p["rolagem"], darkcolor=p["rolagem"],
                 arrowsize=12, gripcount=0, relief="flat")
    st.map("Vertical.TScrollbar", background=[("active", p["suave"])])
    st.configure("TSeparator", background=p["borda"])
    st.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground=p["texto"],
                 rowheight=28, bordercolor=p["borda"], lightcolor=p["borda"], darkcolor=p["borda"])
    st.map("Treeview", background=[("selected", p["selecao_texto"])], foreground=[("selected", p["texto"])])
    st.configure("Treeview.Heading", background=p["botao"], foreground=p["suave_forte"], relief="flat",
                 font=(fonte, 9, "bold"), padding=(8, 6), bordercolor=p["borda"])
    st.map("Treeview.Heading", background=[("active", p["botao_hover"])])
    st.configure("Horizontal.TScrollbar", background=p["rolagem"], troughcolor=p["fundo"],
                 bordercolor=p["fundo"], lightcolor=p["rolagem"], darkcolor=p["rolagem"],
                 arrowsize=12, gripcount=0, relief="flat")
    return fonte
