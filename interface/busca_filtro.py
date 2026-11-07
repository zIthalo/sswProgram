# -*- coding: utf-8 -*-
"""
Busca por NF/texto, filtro por ocorrencia e navegacao com setas.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from nucleo import busca
from nucleo import database as db
from nucleo import occorrencias as occ


class BuscaFiltroMixin:

    def _focar_busca(self, event=None):
        self.entry_busca.focus_set()
        self.entry_busca.select_range(0, tk.END)
        return "break"

    def _sugerir_busca(self, event=None):
        texto = self.var_busca.get()
        if busca.classificar(texto, db.listar_siglas_conhecidas()) == busca.MODO_SIGLA:
            # E uma sigla: nao sugere nome de cliente (a sugestao trocaria a sigla
            # digitada pelo cliente ao apertar Enter/Tab e a busca por sigla se perdia).
            self._suggestion_busca_var.set("")
            self._sugestao_busca_atual = None
            return
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

    def _limpar_campo_busca(self):
        """Busca sem resultado: apaga o que foi digitado (e qualquer filtro de busca)
        e deixa o campo vazio, pronto para uma nova busca."""
        self.var_busca.set("")
        self._suggestion_busca_var.set("")
        self._sugestao_busca_atual = None
        self.filtro_busca_texto = ""
        self.filtro_busca_ids = None
        self.entry_busca.focus_set()

    def _executar_busca(self, event=None):
        # Se houver uma sugestão de cliente ativa, aceita-a antes de buscar
        # (nunca ocorre para siglas conhecidas: _sugerir_busca nao sugere nesse caso)
        if getattr(self, "_sugestao_busca_atual", None):
            self.var_busca.set(self._sugestao_busca_atual)
            self._suggestion_busca_var.set("")
            self._sugestao_busca_atual = None

        texto = self.var_busca.get().strip()

        if not texto:
            # Campo de busca vazio: remove qualquer filtro de busca ativo
            if self.filtro_busca_texto or self.filtro_busca_ids is not None:
                self.filtro_busca_texto = ""
                self.filtro_busca_ids = None
                self.recarregar_lista(resetar_scroll=True)
            return

        if texto.isdigit():
            # 1) Busca por NF: localiza e destaca a nota especifica (nao filtra a lista)
            nf = int(texto)

            # Mais de uma nota pendente com esse numero (remetentes
            # diferentes): filtra a lista mostrando TODAS elas, ignorando o
            # filtro de ocorrencia para nenhuma ficar escondida.
            ids_mesmo_numero = db.listar_ids_notas_ativas_por_nf(nf)
            if len(ids_mesmo_numero) > 1:
                self.var_filtro.set(self.OPCAO_TODAS)
                self.filtro_busca_texto = ""
                self.filtro_busca_ids = set(ids_mesmo_numero)
                self.recarregar_lista(resetar_scroll=True)
                return

            alvo = None
            for nota_id, bloco in self.blocos.items():
                if bloco.nota_row["nf_numero"] == nf:
                    alvo = nota_id
                    break
            if alvo is not None:
                if self.filtro_busca_texto or self.filtro_busca_ids is not None:
                    self.filtro_busca_texto = ""
                    self.filtro_busca_ids = None
                    self.recarregar_lista()
                self._destacar_nota(alvo)
                return

            # 2) Se não for uma NF ativa, localiza o número dentro das
            # atualizações de tratativa (ocorrências) já registradas.
            ids_encontrados = db.buscar_notas_ativas_por_texto_tratativa(texto)
            if ids_encontrados:
                self.filtro_busca_texto = ""
                self.filtro_busca_ids = set(ids_encontrados)
                self.recarregar_lista(resetar_scroll=True)
                return

            messagebox.showinfo(
                "Busca", "NF %d não encontrada (nem como número de NF, nem em atualizações de ocorrência)." % nf)
            self._limpar_campo_busca()
            return

        # Busca por cliente ou sigla: filtra a lista mostrando TODAS as notas
        # correspondentes, independente de NF ou ocorrência.
        self.filtro_busca_ids = None
        self.filtro_busca_texto = texto.lower()
        self.recarregar_lista(resetar_scroll=True)
        if not self.blocos:
            messagebox.showinfo(
                "Busca", "Nenhuma nota ativa encontrada para \"%s\" (cliente ou sigla)." % texto)
            self._limpar_campo_busca()
            self.recarregar_lista(resetar_scroll=True)  # sem filtro: a lista volta a mostrar todas as notas

    def _destacar_nota(self, nota_id):
        bloco = self.blocos.get(nota_id)
        if not bloco:
            return
        self._rolar_para(nota_id)
        bloco.destacar_busca()
        self.after(1500, lambda: bloco._atualizar_destaque_selecao() if bloco.winfo_exists() else None)

    def _rolar_para(self, nota_id):
        bloco = self.blocos.get(nota_id)
        if not bloco:
            return
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(bloco.winfo_y() / max(self.frame_lista.winfo_height(), 1))
        # Rolagem pontual (navegacao por teclado, Ctrl+F): forca a repintura
        # imediatamente, ja que e uma unica chamada, nao um fluxo continuo
        # de eventos como arrastar a barra ou girar a roda do mouse — ver
        # _agendar_repintura_pos_rolagem para a explicacao do porque isso e
        # necessario.
        self.canvas.update()

    def atualizar_scrollregion(self, forcar_repintura=True):
        """Resincroniza a área rolável do canvas com o conteúdo atual, sem
        reconstruir a lista inteira (usado após inserções pontuais, como uma
        nova tratativa ou uma nova nota, para manter a inserção rápida).

        forcar_repintura=True chama canvas.update() (repintura completa e
        imediata): necessário quando widgets ACABARAM DE SER CRIADOS, senão
        o bloco novo reserva o espaço certo mas fica com o conteúdo
        (tratativas) sem desenhar até o usuário redimensionar a janela.
        Widgets que já existem na tela (edição de campo, redimensionamento)
        não precisam dessa repintura forçada: passam forcar_repintura=False
        para evitar esse custo extra em uma operação que deveria ser rápida.
        """
        self.frame_lista.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        if forcar_repintura:
            self.canvas.update()

    def selecionar_nota(self, nota_id, rolar=True):
        anterior = self.blocos.get(self.nota_selecionada_id)
        self.nota_selecionada_id = nota_id
        if anterior is not None:
            anterior._atualizar_destaque_selecao()
        bloco = self.blocos.get(nota_id)
        if bloco is not None:
            bloco._atualizar_destaque_selecao()
            if rolar:
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
        self.var_busca.set("")
        self.filtro_busca_texto = ""
        self.filtro_busca_ids = None
        self.recarregar_lista(resetar_scroll=True)

    # ------------------------------------------------------------------
    # Lista principal (scrollavel)
    # ------------------------------------------------------------------

