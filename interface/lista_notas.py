# -*- coding: utf-8 -*-
"""
Lista de notas: montagem, rolagem, recarga e mensagens.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

from nucleo import busca
from nucleo import database as db
from nucleo import dateutils
from interface.nota_block import NotaBlock


class ListaNotasMixin:

    def _ao_redimensionar_lista(self, event):
        """Mantem o conteudo da lista de notas ajustado a largura da janela,
        para que o texto dos blocos quebre a linha corretamente em vez de
        ficar cortado quando a janela e estreitada.

        O Tkinter dispara <Configure> repetidamente durante o arraste do
        mouse (varias vezes por segundo), inclusive quando so a ALTURA da
        janela mudou (ex.: arrastar so a borda inferior). Dois cuidados
        evitam trabalho desnecessario: (1) eventos que nao mudam a largura
        util sao descartados na hora, sem nenhum reflow; (2) quando a
        largura muda de verdade, o reflow de cada bloco (que recalcula
        quebra de linha e altura) so roda uma vez, apos o usuario parar de
        arrastar, em vez de a cada evento intermediario.

        Usa canvas.winfo_width() (a largura real e atual do widget) em vez
        de event.width: num redimensionamento composto de mover+redimensionar
        a janela de uma vez (Windows+seta para encaixar na metade da tela),
        o valor de event.width de um <Configure> isolado pode nao refletir
        ainda a largura final do canvas, o que deixava o conteudo da lista
        com a largura/posicao internas dessincronizadas da largura real da
        tela (texto cortado/deslocado). Tambem garante que a area rolavel
        nunca fique deslocada horizontalmente (este canvas so tem rolagem
        vertical; sem isso, um deslocamento horizontal indevido nao tinha
        como ser corrigido pelo usuario, pois nao existe barra horizontal)."""
        largura_canvas = self.canvas.winfo_width()
        self.canvas.itemconfig(self._frame_lista_janela, width=largura_canvas)
        self.canvas.xview_moveto(0.0)
        largura_nova = max(largura_canvas - 24, 200)
        if largura_nova == self._largura_lista_atual:
            return  # so a altura da janela mudou; nada para reajustar
        self._largura_lista_atual = largura_nova
        if self._redimensionar_job is not None:
            self.after_cancel(self._redimensionar_job)
        self._redimensionar_job = self.after(80, self._aplicar_redimensionamento_blocos)

    def _aplicar_redimensionamento_blocos(self):
        """Roda uma unica vez, 80ms depois do ultimo evento <Configure> (ou
        seja, uma unica vez por redimensionamento, nao a cada evento). Por
        isso pode pedir a repintura completa (forcar_repintura=True) sem
        custo perceptivel: redimensionamentos abruptos — Win+seta para
        encaixar a janela na metade da tela, ou soltar um arrasto rapido —
        pulam de largura de uma vez só, e sem essa repintura forçada aqui o
        Tkinter no Windows podia deixar a tela com conteúdo sobreposto/
        desatualizado até alguma outra ação forçar um redesenho."""
        self._redimensionar_job = None
        largura = self._largura_lista_atual
        for bloco in self.blocos.values():
            bloco.atualizar_largura(largura)
        self.atualizar_scrollregion(forcar_repintura=True)
        self.canvas.xview_moveto(0.0)

    def obter_largura_lista(self):
        return getattr(self, "_largura_lista_atual", 760)

    def _ao_rolar_lista(self, *args):
        """Chamado pela barra de rolagem (arrastar o 'thumb' ou clicar nela).
        Ver _agendar_repintura_pos_rolagem para o motivo de disparar uma
        repintura apos a rolagem."""
        self.canvas.yview(*args)
        self._agendar_repintura_pos_rolagem()

    def _registrar_rolagem(self, janela, canvas):
        """Registra o canvas rolavel de uma janela secundaria (Historico,
        detalhes do relatorio...), para a roda do mouse rolar SO ela quando
        ela estiver em foco."""
        self._canvas_rolagem[janela] = canvas
        janela.bind("<Destroy>", lambda e, j=janela: self._canvas_rolagem.pop(j, None)
                    if e.widget is j else None, add="+")

    def _janela_da_rolagem(self, event):
        """Janela (toplevel) que deve receber a rolagem: a que tem o foco do
        teclado. Se nao der para saber o foco, usa a do widget do evento."""
        try:
            foco = self.focus_get()
            if foco is not None:
                return foco.winfo_toplevel()
        except (KeyError, tk.TclError):
            pass
        try:
            return event.widget.winfo_toplevel()
        except (AttributeError, KeyError, tk.TclError):
            return None

    def _ao_rolar_roda_mouse(self, event):
        """Roda do mouse: rola APENAS a janela em foco. Antes, o binding era
        global (bind_all) e sempre rolava a lista principal, mesmo com o
        Historico, Cadastros etc. em foco — rolando as ocorrencias junto.
        Janelas sem area rolavel registrada (ex.: Cadastros, que tem a propria
        Listbox) simplesmente nao movem a lista principal.
        Ver _agendar_repintura_pos_rolagem para o motivo de disparar uma
        repintura apos a rolagem da lista principal."""
        janela = self._janela_da_rolagem(event)
        passos = int(-event.delta / 120)
        if janela is self:
            self.canvas.yview_scroll(passos, "units")
            self._agendar_repintura_pos_rolagem()
            return
        canvas = self._canvas_rolagem.get(janela)
        if canvas is not None:
            try:
                canvas.yview_scroll(passos, "units")
            except tk.TclError:
                self._canvas_rolagem.pop(janela, None)

    def _agendar_repintura_pos_rolagem(self):
        """Garante que o conteudo recem-exposto pela rolagem seja realmente
        desenhado na tela.

        Blocos criados fora da area visivel (ex.: logo apos recarregar_lista
        trocar o filtro, com a lista tendo muito mais notas do que cabe na
        tela) ficam, no Windows, com o cabecalho e o separador sem pintar
        ate alguma acao forcar um redesenho completo — o mesmo tipo de bug
        ja visto antes com blocos recem-inseridos (ver item 14 do README),
        so que agora exposto pela ROLAGEM em vez da insercao. Rolar sozinho
        (canvas.yview/yview_scroll) so reposiciona a janela de visualizacao;
        nao hA garantia de repintura completa do conteudo recem-exposto.

        Por isso, uma unica vez, apos o usuario parar de rolar (debounce de
        80ms, igual ao usado no redimensionamento), forcamos uma repintura
        completa (canvas.update()). Fazer isso a cada evento de rolagem
        seria caro com muitas notas ativas; feito uma unica vez ao final,
        o custo e desprezivel."""
        if self._rolagem_job is not None:
            self.after_cancel(self._rolagem_job)
        self._rolagem_job = self.after(80, self._repintar_apos_rolagem)

    def _repintar_apos_rolagem(self):
        self._rolagem_job = None
        self.canvas.update()

    def recarregar_lista(self, resetar_scroll=False):
        """Reconstroi a lista inteira a partir do banco (usado ao trocar de
        filtro, entre outros casos).

        Esta funcao termina chamando atualizar_scrollregion(), que no
        caminho forcar_repintura=True executa canvas.update() — e
        update() (diferente de update_idletasks()) processa TODA a fila de
        eventos pendente do Tcl, nao so geometria. Se o usuario trocar o
        filtro de novo rapido o suficiente para um segundo evento de troca
        de filtro ja estar enfileirado nesse momento, esse canvas.update()
        reentraria direto em recarregar_lista() ANTES desta chamada
        terminar, destruindo/recriando os blocos no meio do processo —
        exatamente o que produzia blocos duplicados/com cabecalho ausente
        na tela ate o usuario clicar em "Limpar filtro" (que, por coincidencia,
        e so mais uma chamada a recarregar_lista(), e funcionava por rodar
        depois que a fila de eventos jah tinha se esvaziado).

        A guarda abaixo torna essas chamadas sequenciais em vez de
        aninhadas: uma chamada que chega enquanto outra ja esta em
        andamento so marca que e preciso recarregar de novo ao final, em
        vez de destruir/recriar os blocos no meio da execucao atual. Isso
        garante que o estado final sempre reflita o ultimo filtro
        selecionado, sem nunca deixar dois conjuntos de blocos coexistindo
        na tela."""
        if getattr(self, "_recarregando_lista", False):
            self._recarregar_lista_pendente = True
            self._recarregar_lista_pendente_resetar_scroll = (
                resetar_scroll or getattr(self, "_recarregar_lista_pendente_resetar_scroll", False)
            )
            return
        self._recarregando_lista = True
        try:
            self._recarregar_lista_impl(resetar_scroll)
        finally:
            self._recarregando_lista = False
            if getattr(self, "_recarregar_lista_pendente", False):
                self._recarregar_lista_pendente = False
                resetar_pendente = self._recarregar_lista_pendente_resetar_scroll
                self._recarregar_lista_pendente_resetar_scroll = False
                self.recarregar_lista(resetar_scroll=resetar_pendente)

    def _recarregar_lista_impl(self, resetar_scroll=False):
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

        if self.filtro_busca_texto:
            notas = busca.filtrar_notas(notas, self.filtro_busca_texto, db.listar_siglas_conhecidas())

        if self.filtro_busca_ids is not None:
            notas = [n for n in notas if n["id"] in self.filtro_busca_ids]

        # Busca as tratativas de todas as notas visiveis em uma unica consulta,
        # em vez de uma consulta por nota (evita gargalo de performance quando
        # ha muitas notas ativas).
        tratativas_por_nota = db.listar_tratativas_por_notas([n["id"] for n in notas])

        for nota in notas:
            bloco = NotaBlock(self.frame_lista, self, nota, tratativas_por_nota.get(nota["id"], []))
            bloco.pack(fill="x", pady=4, padx=2)
            self.blocos[nota["id"]] = bloco

        if self.nota_selecionada_id not in self.blocos:
            self.nota_selecionada_id = None

        # Um unico update_idletasks para toda a lista (em vez de um por bloco)
        # resolve a geometria de uma vez, mantendo a insercao de notas rapida
        # mesmo com muitas notas ativas.
        self.frame_lista.update_idletasks()
        for bloco in self.blocos.values():
            bloco._ajustar_altura_cabecalho()

        # Reajustar a altura dos cabecalhos (acima) pode mudar o tamanho total
        # da lista; resincroniza a scrollregion do canvas com o tamanho final,
        # senao a area rolavel fica maior que o conteudo real e os blocos
        # parecem "se mover" quando o usuario rola o mouse.
        self.atualizar_scrollregion()

        if resetar_scroll:
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

