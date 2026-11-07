# -*- coding: utf-8 -*-
"""
NotaBlock: cartao visual de cada nota + funcoes de cabecalho.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

from nucleo import aparencia
from nucleo import database as db
from nucleo import dateutils
from nucleo import tratativas_rapidas
from nucleo import occorrencias as occ
from interface import tema
from interface.dialogs import pedir_texto_atualizacao


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
    """Monta o cabecalho da nota como uma lista de (texto, negrito). Quais
    campos aparecem em negrito vem das preferencias de aparencia do usuario
    (padrao de fabrica: CLIENTE, OCORRENCIA e AGENDAMENTO). O TEXTO e sempre
    o mesmo, independentemente da aparencia."""
    neg = aparencia.eh_negrito
    dias = dias_em_tratativas(nota["criado_em"])
    segmentos = [
        ("NF: %s" % nota["nf_numero"], neg("nf")),
        (" / ", False),
        ("CLIENTE: %s" % nota["cliente"], neg("cliente")),
        (" / ", False),
        ("OCORRÊNCIA: %s" % nota["ocorrencia"], neg("ocorrencia")),
        (" / ", False),
        ("SIGLA UNIDADE: %s" % nota["sigla"], neg("sigla")),
        (" / ", False),
        ("DATA: %s HORA: %s" % (dateutils.formatar_data_exibicao(nota["data_ocorrencia"]),
                                hora_insercao(nota["criado_em"])), neg("data_hora")),
        (" / ", False),
        ("DIAS EM TRATATIVAS: %s" % dias, neg("dias")),
    ]
    if nota["agendamento_data"]:
        segmentos.append((" / ", False))
        segmentos.append(("AGENDAMENTO: %s" % dateutils.formatar_data_exibicao(nota["agendamento_data"]),
                          neg("agendamento")))
    observacao = nota["observacao"] if "observacao" in nota.keys() else None
    if observacao:
        segmentos.append((" / ", False))
        segmentos.append(("OBS: %s" % observacao, neg("observacao")))
    return segmentos


SEPARADOR_COPIA = "-" * 30


def formatar_nota_para_copia(nota):
    """Texto de uma nota para colar (ex.: WhatsApp): um campo por linha, com asteriscos para
    deixar NF, remetente e unidade em negrito."""
    return "\n".join([
        "*NF: %s;*" % nota["nf_numero"],
        "Cliente: *%s*;" % nota["cliente"],
        "Ocorrência: %s;" % nota["ocorrencia"],
        "Unidade: *%s*;" % nota["sigla"],
        "Dias em tratativas: %s;" % dias_em_tratativas(nota["criado_em"]),
    ])


def formatar_notas_para_copia(notas):
    """Uma nota: so o bloco. Mais de uma: cada bloco seguido de uma linha separadora."""
    blocos = [formatar_nota_para_copia(n) for n in notas]
    if len(blocos) == 1:
        return blocos[0]
    return "".join("%s\n\n%s\n\n" % (bloco, SEPARADOR_COPIA) for bloco in blocos)


class NotaBlock(ttk.Frame):
    """Cartao de uma nota fiscal na tela principal.

    Faixa lateral colorida pela urgencia (dias em tratativas), "chips" de ocorrencia/sigla/
    agendamento, remetente e observacao, e a linha do tempo das tratativas. Tudo o que e texto
    fica num UNICO widget Text (menos widgets por nota = lista rapida mesmo com muitas notas).
    Respeita as preferencias de "Aparencia" (cor da fonte, do fundo, da selecao e negrito)."""

    LINHAS_CABECALHO = 3      # linhas do Text que formam o cabecalho (clicar nelas copia a NF)
    PAD_TEXTO = 10            # pady interno do Text (usado no calculo da altura em pixels)

    def __init__(self, master, app, nota_row, tratativas=None):
        ttk.Frame.__init__(self, master, style="Cartao.TFrame", padding=0)
        self.app = app
        self.nota_id = nota_row["id"]
        self.nota_row = nota_row
        self._tratativas = tratativas if tratativas is not None else db.listar_tratativas(self.nota_id)
        self._largura_medida = None
        p, f = tema.PALETA, tema.FONTE
        cfg = aparencia.obter()
        self._cor_fundo = cfg["cor_fundo"] or p["superficie"]
        self._cor_texto = cfg["cor_fonte"] or p["texto"]
        self._cor_selecao = (p["selecao"] if cfg["cor_selecao"] == aparencia.COR_SELECAO_PADRAO
                             else cfg["cor_selecao"])

        self.columnconfigure(1, weight=1)
        self.faixa = tk.Frame(self, width=5, background=p["acento"])
        self.faixa.grid(row=0, column=0, sticky="ns")
        # A altura do cartao e medida em PIXELS (Text.count "ypixels"): o texto mistura fontes de
        # tamanhos diferentes e a medida em "linhas" cortaria o final.
        self.caixa = tk.Frame(self, background=self._cor_fundo, height=1)
        self.caixa.grid(row=0, column=1, sticky="ew")
        self.caixa.pack_propagate(False)
        self.txt_cabecalho = tk.Text(
            self.caixa, wrap="word", height=1, borderwidth=0, highlightthickness=0, cursor="hand2",
            padx=14, pady=self.PAD_TEXTO, exportselection=False, background=self._cor_fundo,
            foreground=self._cor_texto, font=(f, 10), spacing1=1, spacing3=1, insertwidth=0,
            selectbackground=p["selecao_texto"], selectforeground=self._cor_texto,
            inactiveselectbackground=p["selecao_texto"])
        self.txt_cabecalho.pack(fill="both", expand=True)
        self.lateral = tk.Frame(self, background=self._cor_fundo)
        self.lateral.grid(row=0, column=2, sticky="nsew")
        self.lbl_dias = tk.Label(self.lateral, font=(f, 20, "bold"), background=self._cor_fundo)
        self.lbl_dias.pack(padx=18, pady=(10, 0))
        self.lbl_dias_txt = tk.Label(self.lateral, font=(f, 8), foreground=p["suave"], background=self._cor_fundo)
        self.lbl_dias_txt.pack()

        self._configurar_tags()
        # A largura real so e conhecida depois que o widget e posicionado; recalcula a altura nesse
        # momento. Durante um redimensionamento da janela quem reajusta e a lista (uma unica vez,
        # ao parar de arrastar: ver _aplicar_redimensionamento_blocos), nao cada cartao a cada evento.
        self.txt_cabecalho.bind("<Configure>", self._ao_configurar_texto)
        self.txt_cabecalho.bind("<Button-1>", self._pressionar_texto)
        self.txt_cabecalho.bind("<ButtonRelease-1>", self._soltar_texto)
        for w in (self.txt_cabecalho, self.faixa, self.lateral, self.lbl_dias, self.lbl_dias_txt, self):
            w.bind("<Button-3>", self._abrir_menu)
            w.bind("<Double-Button-1>", self._duplo_clique)
        for w in (self.faixa, self.lateral, self.lbl_dias, self.lbl_dias_txt, self):
            w.bind("<Button-1>", self._selecionar)
        self._renderizar()
        self._atualizar_destaque_selecao()

    # ------------------------------------------------------------------
    # Desenho
    # ------------------------------------------------------------------
    def _configurar_tags(self):
        f, p, t = tema.FONTE, tema.PALETA, self.txt_cabecalho
        neg = aparencia.eh_negrito
        t.tag_configure("nf", font=(f, 13, "bold"), foreground=self._cor_texto)
        t.tag_configure("cliente", font=(f, 10, "bold") if neg("cliente") else (f, 10), foreground=self._cor_texto)
        t.tag_configure("obs", font=(f, 9, "bold") if neg("observacao") else (f, 9), foreground=p["suave_forte"])
        t.tag_configure("meta", font=(f, 8, "bold") if neg("data_hora") else (f, 8), foreground=p["suave"])
        t.tag_configure("ts", font=(f, 9), foreground=p["suave"])
        t.tag_configure("trat", font=(f, 9), foreground=self._cor_texto)
        t.tag_configure("topo", spacing1=10)       # respiro entre o cabecalho e a linha do tempo
        fundo, texto = tema.CHIP_SIGLA
        t.tag_configure("chip_sigla", font=(f, 8, "bold"), background=fundo, foreground=texto)
        for nome, (fundo, texto) in list(tema.CHIPS.items()) + [("_padrao", tema.CHIP_PADRAO)]:
            t.tag_configure("chip_" + nome, font=(f, 8, "bold"), background=fundo, foreground=texto)

    def _renderizar(self):
        nota, t = self.nota_row, self.txt_cabecalho
        t.configure(state="normal")
        t.delete("1.0", tk.END)
        oc = nota["ocorrencia"]
        t.insert(tk.END, "NF %s" % nota["nf_numero"], "nf")
        t.insert(tk.END, "   ")
        t.insert(tk.END, " %s " % oc, "chip_" + (oc if oc in tema.CHIPS else "_padrao"))
        t.insert(tk.END, "  ")
        t.insert(tk.END, " %s " % nota["sigla"], "chip_sigla")
        if nota["agendamento_data"]:
            t.insert(tk.END, "  ")
            t.insert(tk.END, " AGENDADO PARA %s " % dateutils.formatar_data_exibicao(nota["agendamento_data"]),
                     "chip_AGENDAMENTO")
        t.insert(tk.END, "\n")
        t.insert(tk.END, nota["cliente"], "cliente")
        obs = nota["observacao"] if "observacao" in nota.keys() else None
        if obs:
            t.insert(tk.END, "     OBS: %s" % obs, "obs")
        t.insert(tk.END, "\n")
        t.insert(tk.END, "Registrada em %s às %s" % (dateutils.formatar_data_exibicao(nota["data_ocorrencia"]),
                                                      hora_insercao(nota["criado_em"])), "meta")
        for i, tr in enumerate(self._tratativas):
            self._inserir_tratativa(tr["timestamp"], tr["texto"], primeira=(i == 0))
        t.configure(state="disabled")
        dias = dias_em_tratativas(nota["criado_em"])
        cor = tema.cor_urgencia(dias)
        self.faixa.configure(background=cor)
        self.lbl_dias.configure(text=str(dias), foreground=cor)
        self.lbl_dias_txt.configure(text="dia" if dias == 1 else "dias")
        self._ajustar_altura_cabecalho()

    def _inserir_tratativa(self, timestamp, texto, primeira):
        t = self.txt_cabecalho
        marca = ("topo",) if primeira else ()
        t.insert(tk.END, "\n", marca)
        t.insert(tk.END, timestamp, ("ts",) + marca)
        t.insert(tk.END, "   %s" % texto, ("trat",) + marca)

    def _atualizar_cabecalho(self):
        self._renderizar()

    def _ao_configurar_texto(self, event):
        if event.width == self._largura_medida:
            return        # so a altura mudou (efeito do proprio ajuste): nada a recalcular
        self._largura_medida = event.width
        if getattr(self.app, "_redimensionar_job", None) is None:
            self._ajustar_altura_cabecalho()

    LARGURA_MIN_MEDIR = 120       # abaixo disso o Text ainda nao foi posicionado na tela
    ALTURA_MAXIMA = 6000

    def _ajustar_altura_cabecalho(self):
        """Ajusta a altura do cartao ao texto. So mede com o Text ja posicionado: antes disso
        (janela ainda sendo aberta) a largura e minima, cada letra quebra a linha e a altura
        medida seria enorme - o cartao ficava gigante e escondia as demais notas ate o F5."""
        try:
            if self.txt_cabecalho.winfo_width() < self.LARGURA_MIN_MEDIR:
                return
            pixels = self.txt_cabecalho.count("1.0", "end", "ypixels")
            altura = (pixels[0] if pixels else 16) + 2 * self.PAD_TEXTO + 2    # + pady do Text + folga
        except (tk.TclError, TypeError):
            return
        altura = min(altura, self.ALTURA_MAXIMA)
        if int(self.caixa.cget("height")) != altura:
            self.caixa.configure(height=altura)

    def atualizar_largura(self, largura):
        self._ajustar_altura_cabecalho()

    # ------------------------------------------------------------------
    # Selecao / destaque
    # ------------------------------------------------------------------
    def _pintar(self, cor):
        for w in (self.txt_cabecalho, self.lateral, self.lbl_dias, self.lbl_dias_txt):
            w.configure(background=cor)

    def _atualizar_destaque_selecao(self):
        sel = self.app.nota_selecionada_id == self.nota_id
        self.configure(style="CartaoSel.TFrame" if sel else "Cartao.TFrame")
        if not sel:
            self.txt_cabecalho.tag_remove("sel", "1.0", "end")
        self._pintar(self._cor_selecao if sel else self._cor_fundo)

    def destacar_busca(self):
        """Realce amarelo temporario da nota encontrada pela busca por NF."""
        self._pintar(tema.PALETA["busca"])

    # ------------------------------------------------------------------
    # Interacao
    # ------------------------------------------------------------------
    def _linha_do_evento(self, event):
        return int(self.txt_cabecalho.index("@%d,%d" % (event.x, event.y)).split(".")[0])

    def _pressionar_texto(self, event):
        """Selecionar o cartao. Nao interrompe o evento: arrastar o mouse sobre o texto seleciona
        (Ctrl+C copia o trecho selecionado - ver copiar_selecao)."""
        self._pressionado = (event.x, event.y, self._linha_do_evento(event))
        self._selecionar()

    def _soltar_texto(self, event):
        """Clique simples (sem arrastar e sem texto selecionado) no cabecalho copia a NF, como sempre."""
        pressionado = getattr(self, "_pressionado", None)
        self._pressionado = None
        if pressionado is None:
            return
        x, y, linha = pressionado
        if abs(event.x - x) > 3 or abs(event.y - y) > 3:
            return      # arrastou: e uma selecao de texto
        if linha <= self.LINHAS_CABECALHO and not self.txt_cabecalho.tag_ranges("sel"):
            self._copiar_nf(event)

    def _y_inicio_tratativas(self):
        """Altura (em tela) onde comecam as atualizacoes; sem atualizacoes, o cartao inteiro conta."""
        if not self._tratativas:
            return None
        caixa = self.txt_cabecalho.bbox("%d.0" % (self.LINHAS_CABECALHO + 1))
        if not caixa:
            return None
        return self.txt_cabecalho.winfo_rooty() + caixa[1]

    def _duplo_clique(self, event):
        """Duplo clique adiciona uma atualizacao so na regiao do cartao ANTES das atualizacoes
        (cabecalho, faixa, dias). Sobre as linhas das atualizacoes nao faz nada, e o duplo clique
        seleciona a palavra, como em qualquer texto."""
        limite = self._y_inicio_tratativas()
        if limite is not None and event.y_root >= limite:
            return None
        return self._adicionar_tratativa(event)

    def copiar_selecao(self):
        """Ctrl+C: copia o trecho de texto selecionado com o mouse neste cartao. True se copiou."""
        try:
            trecho = self.txt_cabecalho.get("sel.first", "sel.last")
        except tk.TclError:
            return False
        if not trecho:
            return False
        self.app.clipboard_clear()
        self.app.clipboard_append(trecho)
        self.app.update()
        self.app.mostrar_mensagem_flutuante("Texto copiado!")
        return True

    def atualizar(self, nota_row):
        """Atualiza este cartao apos a edicao de um campo (ocorrencia, sigla, NF, cliente...)."""
        self.nota_row = nota_row
        self._renderizar()

    def _copiar_nf(self, event=None):
        self._selecionar()
        self.app.clipboard_clear()
        self.app.clipboard_append(str(self.nota_row["nf_numero"]))
        self.app.update()
        self.app.mostrar_mensagem_flutuante("Número copiado!", event)
        return "break"

    def _adicionar_linha_tratativa(self, timestamp, texto):
        """Acrescenta a nova linha direto neste cartao, sem reconstruir a lista inteira."""
        self._tratativas.append({"timestamp": timestamp, "texto": texto})
        self.txt_cabecalho.configure(state="normal")
        self._inserir_tratativa(timestamp, texto, primeira=(len(self._tratativas) == 1))
        self.txt_cabecalho.configure(state="disabled")
        self.txt_cabecalho.update_idletasks()      # a medida precisa do texto ja assentado
        self._ajustar_altura_cabecalho()
        self.app.atualizar_scrollregion()
        self.after_idle(self._ajustar_altura_cabecalho)    # confirma a altura apos o desenho

    def _selecionar(self, event=None):
        self.app.selecionar_nota(self.nota_id, rolar=False)

    def _adicionar_tratativa(self, event=None):
        texto = pedir_texto_atualizacao(
            self.app,
            "Nova atualização",
            "Descreva a atualização da tratativa para a NF %s:\n(atalhos: E = e-mail, W = WhatsApp, S = informações em sistema, R = mercadoria em rota de entrega hoje)"
            % self.nota_row["nf_numero"],
        )
        if texto:
            # "e", "w" ou "s" sozinhos viram frases prontas (ver nucleo/tratativas_rapidas.py).
            texto = tratativas_rapidas.expandir_atalho(texto.strip()).upper()
            timestamp = db.adicionar_tratativa(self.nota_id, texto)
            self._adicionar_linha_tratativa(timestamp, texto)
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
        if occ.eh_ocorrencia_agendamento(self.nota_row["ocorrencia"]):
            menu.add_command(label="Alterar data do agendamento",
                              command=lambda: self.app.editar_data_agendamento(self.nota_id))
        menu.add_command(label="Editar sigla",
                          command=lambda: self.app.editar_campo(self.nota_id, "sigla", "Sigla/Empresa"))
        menu.add_command(label="Editar observação/tag",
                          command=lambda: self.app.editar_observacao(self.nota_id))
        menu.add_separator()
        menu.add_command(label="Nova nota para o mesmo remetente/sigla",
                          command=lambda: self.app.duplicar_nota(self.nota_id))
        menu.add_separator()
        menu.add_command(label="Copiar informações da nota",
                          command=lambda: self.app.copiar_informacoes_nota(self.nota_id))
        menu.add_command(label="Gerar comprovante (imprimir / PDF)",
                          command=lambda: self.app.gerar_comprovante_nota(self.nota_id))
        menu.tk_popup(event.x_root, event.y_root)
        return "break"
