# -*- coding: utf-8 -*-
"""
NotaBlock: bloco visual de cada nota + funcoes de cabecalho.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

from nucleo import aparencia
from nucleo import database as db
from nucleo import dateutils
from nucleo import tratativas_rapidas
from nucleo import occorrencias as occ
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


def formatar_cabecalho_nota(nota):
    """Versao em texto simples do cabecalho da nota (usada ao copiar as
    informações da nota para a área de transferência)."""
    return "".join(texto for texto, _negrito in montar_segmentos_cabecalho(nota))


class NotaBlock(ttk.Frame):
    """Widget que representa o bloco visual de uma nota fiscal na tela principal."""

    def __init__(self, master, app, nota_row, tratativas=None):
        super().__init__(master, padding=8, relief="groove", borderwidth=1, style=aparencia.estilo_frame())
        self.app = app
        self.nota_id = nota_row["id"]
        self.nota_row = nota_row
        self._tratativas = tratativas if tratativas is not None else db.listar_tratativas(self.nota_id)

        self.txt_cabecalho = tk.Text(
            self, wrap="word", height=1, borderwidth=0, highlightthickness=0,
            font=("Consolas", 9), cursor="hand2", padx=0, pady=0, exportselection=False,
            **aparencia.kwargs_texto()
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

        largura_atual = self.app.obter_largura_lista()

        self._atualizar_cabecalho()

        separador = tk.Label(self, text="=" * 90, anchor="w", font=("Consolas", 7), **aparencia.kwargs_texto())
        separador.pack(fill="x")
        separador.bind("<Button-1>", self._selecionar)

        self.frame_tratativas = ttk.Frame(self, style=aparencia.estilo_frame())
        self.frame_tratativas.pack(fill="x")
        self.frame_tratativas.bind("<Button-1>", self._selecionar)
        for t in self._tratativas:
            linha = tk.Label(self.frame_tratativas, text="%s: %s" % (t["timestamp"], t["texto"]),
                              anchor="w", justify="left", font=("Consolas", 9), wraplength=largura_atual,
                              **aparencia.kwargs_texto())
            linha.pack(fill="x")
            linha.bind("<Button-1>", self._selecionar)
            linha.bind("<Double-Button-1>", self._adicionar_tratativa)
            linha.bind("<Button-3>", self._abrir_menu)
            self._labels_texto.append(linha)

        self.bind("<Button-1>", self._selecionar)
        self.bind("<Button-3>", self._abrir_menu)
        self.bind("<Double-Button-1>", self._adicionar_tratativa)

        self._atualizar_destaque_selecao()

    def _atualizar_cabecalho(self):
        """Reescreve somente o texto do cabeçalho (NF/CLIENTE/OCORRÊNCIA/
        SIGLA/AGENDAMENTO) a partir de self.nota_row. Usada tanto na
        montagem inicial do bloco (_montar) quanto na atualização pontual
        de um campo editado (atualizar) — nesse segundo caso, isolar essa
        etapa evita destruir e recriar o separador e as linhas de
        tratativa, que não mudam quando só um campo do cabeçalho é
        editado."""
        nota = self.nota_row
        self.txt_cabecalho.configure(state="normal")
        self.txt_cabecalho.delete("1.0", tk.END)
        for texto, negrito in montar_segmentos_cabecalho(nota):
            self.txt_cabecalho.insert(tk.END, texto, ("negrito",) if negrito else ())
        self.txt_cabecalho.configure(state="disabled", insertwidth=0)
        self.txt_cabecalho.bind("<Button-1>", self._copiar_nf)
        self.txt_cabecalho.bind("<Button-3>", self._abrir_menu)
        self.txt_cabecalho.bind("<Double-Button-1>", self._adicionar_tratativa)
        self._ajustar_altura_cabecalho()

    def _ajustar_altura_cabecalho(self):
        try:
            linhas = self.txt_cabecalho.count("1.0", "end", "displaylines")
            n = linhas[0] if linhas else 1
        except (tk.TclError, TypeError):
            n = 1
        n = max(n, 1)
        if int(self.txt_cabecalho.cget("height")) != n:
            self.txt_cabecalho.configure(height=n)

    def _atualizar_destaque_selecao(self):
        cfg = aparencia.obter()
        if self.app.nota_selecionada_id == self.nota_id:
            self.txt_cabecalho.configure(background=cfg["cor_selecao"])
        else:
            self.txt_cabecalho.configure(background=cfg["cor_fundo"] or self.app.cget("bg"))

    def atualizar_largura(self, largura):
        for lbl in getattr(self, "_labels_texto", []):
            lbl.configure(wraplength=max(largura, 200))
        self._ajustar_altura_cabecalho()

    def _selecionar(self, event=None):
        self.app.selecionar_nota(self.nota_id, rolar=False)

    def atualizar(self, nota_row):
        """Atualiza este bloco com os novos dados da nota após a edição de
        um campo (ocorrência, sigla, NF, cliente, etc.). Só o cabeçalho é
        reescrito — o separador e as linhas de tratativa já existentes
        mantêm seus widgets e estado intactos, já que nenhum desses dados
        muda numa edição de campo."""
        self.nota_row = nota_row
        self._atualizar_cabecalho()

    def _copiar_nf(self, event=None):
        self._selecionar()
        self.app.clipboard_clear()
        self.app.clipboard_append(str(self.nota_row["nf_numero"]))
        self.app.update()
        self.app.mostrar_mensagem_flutuante("Número copiado!", event)
        return "break"

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

    def _adicionar_linha_tratativa(self, timestamp, texto):
        """Insere a nova linha de tratativa direto neste bloco, sem reconstruir
        a lista inteira — mantém a inserção rápida mesmo com muitas notas."""
        largura_atual = self.app.obter_largura_lista()
        linha = tk.Label(self.frame_tratativas, text="%s: %s" % (timestamp, texto),
                          anchor="w", justify="left", font=("Consolas", 9), wraplength=largura_atual,
                              **aparencia.kwargs_texto())
        linha.pack(fill="x")
        linha.bind("<Button-1>", self._selecionar)
        linha.bind("<Double-Button-1>", self._adicionar_tratativa)
        linha.bind("<Button-3>", self._abrir_menu)
        self._labels_texto.append(linha)
        self._tratativas.append({"timestamp": timestamp, "texto": texto})
        self.app.atualizar_scrollregion()

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
        menu.add_command(label="Copiar informações da nota (sem atualizações)",
                          command=lambda: self.app.copiar_informacoes_nota_sem_tratativas(self.nota_id))
        menu.add_command(label="Gerar comprovante (imprimir / PDF)",
                          command=lambda: self.app.gerar_comprovante_nota(self.nota_id))
        menu.tk_popup(event.x_root, event.y_root)
        return "break"

