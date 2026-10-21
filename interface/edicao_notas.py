# -*- coding: utf-8 -*-
"""
Acoes sobre uma nota: copiar, resolver, editar campos/ocorrencia/agendamento.
"""

import sqlite3
from tkinter import messagebox, simpledialog

from nucleo import comprovante
from nucleo import database as db
from nucleo import dateutils
from nucleo import occorrencias as occ
from interface.dialogs import editar_campo_texto, fluxo_marcar_resolvido, pedir_opcao, pedir_texto_atualizacao
from interface.nota_block import formatar_cabecalho_nota


class EdicaoNotasMixin:
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

    def copiar_informacoes_nota_sem_tratativas(self, nota_id):
        """Copia só o cabeçalho da nota (NF/CLIENTE/OCORRÊNCIA/SIGLA/DATA/...),
        sem o histórico de tratativas abaixo — útil para cobrança rápida,
        sem o texto ficar poluído com todas as atualizações já registradas."""
        nota = db.obter_nota(nota_id)
        if nota is None:
            return
        self.clipboard_clear()
        self.clipboard_append(formatar_cabecalho_nota(nota))
        self.update()
        self.mostrar_mensagem_flutuante("Informações copiadas (sem atualizações)!")

    def copiar_notas_filtradas(self):
        """Copia o cabeçalho (sem tratativas) de TODAS as notas atualmente
        visíveis na tela — ou seja, já considerando o filtro de ocorrência e
        a busca por cliente/sigla/NF em uso no momento. Pensado para a
        cobrança diária de uma unidade/sigla/empresa inteira de uma vez,
        em vez de copiar nota por nota."""
        notas_visiveis = [bloco.nota_row for bloco in self.blocos.values()]
        if not notas_visiveis:
            messagebox.showinfo(
                "Copiar notas filtradas",
                "Não há notas para copiar com o filtro/busca atual.",
                parent=self,
            )
            return
        texto = "\n\n".join(formatar_cabecalho_nota(nota) for nota in notas_visiveis)
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.update()
        self.mostrar_mensagem_flutuante("%d nota(s) copiada(s)!" % len(notas_visiveis))

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
        historico_id = db.inserir_historico(
            resultado["nf_numero"], resultado["cliente"], resultado["ocorrencia"],
            resultado["sigla"], resultado["dias"], resultado["horas"], resultado["morosidade"],
        )
        db.marcar_resolvida(nota_id)
        self.pilha_desfazer.registrar(
            "resolução da NF %s" % nota["nf_numero"],
            lambda: db.reabrir_nota(nota_id, historico_id))
        self._remover_bloco_rapido(nota_id)
        self.mostrar_mensagem_flutuante("Ocorrência resolvida pressione CTRL + Z para desfazer")

    # ------------------------------------------------------------------
    # Desfazer (Ctrl+Z na janela principal / menu Editar)
    # ------------------------------------------------------------------
    def _registrar_desfazer_campos(self, nota_antes, descricao, campos):
        """Guarda a 'foto' dos campos da nota ANTES da edicao para o Desfazer."""
        antes = {c: nota_antes[c] for c in campos}
        nota_id = nota_antes["id"]
        self.pilha_desfazer.registrar(
            "%s da NF %s" % (descricao, nota_antes["nf_numero"]),
            lambda: db.restaurar_campos_nota(nota_id, antes))

    def desfazer_ultima_alteracao(self, event=None):
        if self.pilha_desfazer.vazia():
            self.mostrar_mensagem_flutuante("Nada para desfazer")
            return "break"
        try:
            descricao = self.pilha_desfazer.desfazer()
        except db.NotaDuplicadaError:
            messagebox.showerror("Não foi possível desfazer", db.MENSAGEM_NF_DUPLICADA, parent=self)
            return "break"
        except sqlite3.Error as erro:
            messagebox.showerror("Não foi possível desfazer", "Falha ao desfazer: %s" % erro, parent=self)
            return "break"
        self.recarregar_lista()
        self._atualizar_combobox_sigla()
        self.mostrar_mensagem_flutuante("Desfeito: %s" % descricao)
        return "break"

    def _remover_bloco_rapido(self, nota_id):
        """Remove o bloco de uma nota resolvida diretamente da tela, sem
        reconstruir a lista inteira (mantém a ação rápida mesmo com muitas
        notas ativas)."""
        bloco = self.blocos.pop(nota_id, None)
        if bloco is not None:
            if self.nota_selecionada_id == nota_id:
                self.nota_selecionada_id = None
            bloco.destroy()
            self.atualizar_scrollregion(forcar_repintura=False)
        if hasattr(self, "combo_filtro"):
            self._atualizar_combobox_filtro()

    def _atualizar_bloco_rapido(self, nota_id):
        """Atualiza na tela somente o bloco da nota editada, sem reconstruir
        a lista inteira — é essa reconstrução total (recarregar_lista) que
        fazia uma edição pontual (ocorrência, sigla, etc.) demorar quando
        havia muitas notas ativas, pois destruía e recriava todos os blocos
        e reconsultava o banco inteiro por causa de uma única nota."""
        filtro_atual = self.var_filtro.get() if hasattr(self, "var_filtro") else self.OPCAO_TODAS
        if filtro_atual.strip().upper() == "AGENDAMENTO":
            # Esse filtro reordena pela data do agendamento; precisa do
            # caminho completo para recalcular a posição na lista.
            self.recarregar_lista()
            return
        nota = db.obter_nota(nota_id)
        bloco = self.blocos.get(nota_id)
        if nota is None:
            if bloco is not None:
                self._remover_bloco_rapido(nota_id)
            return
        if bloco is not None:
            bloco.atualizar(nota)
            self.atualizar_scrollregion(forcar_repintura=False)
        else:
            self._adicionar_bloco_rapido(nota)
        if hasattr(self, "combo_filtro"):
            self._atualizar_combobox_filtro()

    def _pedir_data_agendamento(self, data_atual=None):
        """Pergunta e valida a data de agendamento (mesmas regras da criacao
        da nota). Retorna a data (ddmmaaaa) ou None se cancelado/invalido.
        data_atual: data ja gravada, mostrada e usada como valor inicial."""
        msg = "Informe a data do agendamento (0=hoje, dia do mês, ou ddmmaaaa):"
        if data_atual:
            msg = "Data atual do agendamento: %s\n\n%s" % (
                dateutils.formatar_data_exibicao(data_atual), msg)
        data_ag = simpledialog.askstring("Data do agendamento", msg, parent=self,
                                         initialvalue=data_atual or "")
        if data_ag is None:
            return None
        try:
            agendamento_data = dateutils.parse_data_usuario(data_ag)
        except ValueError as e:
            messagebox.showerror("Data inválida", str(e), parent=self)
            return None
        if dateutils.data_e_passado_ou_hoje(agendamento_data):
            messagebox.showerror("Erro", "A data do agendamento é igual ou inferior a data atual.",
                                 parent=self)
            return None
        return agendamento_data

    def editar_campo(self, nota_id, campo, rotulo):
        nota = db.obter_nota(nota_id)
        if nota is None:
            return
        valor_atual = str(nota[campo])
        if campo == "cliente":
            escolha = pedir_opcao(self, "Editar %s" % rotulo,
                                  "Busque o %s cadastrado (ou digite um novo):" % rotulo.lower(),
                                  db.listar_clientes())
            if escolha is None:
                return
            novo, cliente_novo = escolha
        else:
            cliente_novo = False
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
        try:
            db.atualizar_campo_nota(nota_id, campo, novo)
        except db.NotaDuplicadaError:
            messagebox.showerror("Nota Fiscal duplicada", db.MENSAGEM_NF_DUPLICADA, parent=self)
            return
        except sqlite3.Error as erro:
            messagebox.showerror("Erro", "Falha ao salvar a alteração: %s" % erro, parent=self)
            return
        self._registrar_desfazer_campos(nota, "edição de %s" % rotulo.lower(), [campo])
        if cliente_novo:
            # Mesmo comportamento do cadastro de notas: remetente novo entra no cadastro.
            try:
                db.adicionar_cliente(novo)
            except sqlite3.Error:
                pass
        cliente_atual = novo if campo == "cliente" else nota["cliente"]
        sigla_atual = novo if campo == "sigla" else nota["sigla"]
        self._garantir_visibilidade(cliente_atual, sigla_atual, nota["ocorrencia"])
        self._atualizar_bloco_rapido(nota_id)

    def editar_data_agendamento(self, nota_id):
        """Altera somente a data de uma nota cuja ocorrência já é Agendamento."""
        nota = db.obter_nota(nota_id)
        if nota is None or not occ.eh_ocorrencia_agendamento(nota["ocorrencia"]):
            return
        nova = self._pedir_data_agendamento(nota["agendamento_data"])
        if nova is None:
            return
        try:
            db.atualizar_campo_nota(nota_id, "agendamento_data", nova)
        except sqlite3.Error as erro:
            messagebox.showerror("Erro", "Falha ao salvar a data: %s" % erro, parent=self)
            return
        self._registrar_desfazer_campos(nota, "alteração da data do agendamento", ["agendamento_data"])
        self._atualizar_bloco_rapido(nota_id)

    def gerar_comprovante_nota(self, nota_id):
        """Abre no navegador o comprovante da nota (dados + todas as
        tratativas), pronto para imprimir ou salvar como PDF (Ctrl+P)."""
        try:
            caminho = comprovante.gerar_comprovante(nota_id)
        except OSError as erro:
            messagebox.showerror("Comprovante", "Não foi possível gerar o comprovante: %s" % erro, parent=self)
            return
        if caminho:
            self.mostrar_mensagem_flutuante("Comprovante aberto no navegador")

    def editar_observacao(self, nota_id):
        """Observação/tag livre da nota (ex.: motivo, protocolo, contato).
        Texto vazio apaga a observação; cancelar não altera nada."""
        nota = db.obter_nota(nota_id)
        if nota is None:
            return
        novo = pedir_texto_atualizacao(
            self, "Observação / tag",
            "Observação/tag para a NF %s (deixe vazio para remover):" % nota["nf_numero"],
            nota["observacao"] or "")
        if novo is None:
            return
        novo = novo.strip().upper()
        db.atualizar_campo_nota(nota_id, "observacao", novo or None)
        self._registrar_desfazer_campos(nota, "edição da observação", ["observacao"])
        self._atualizar_bloco_rapido(nota_id)

    def duplicar_nota(self, nota_id):
        """Atalho para cadastrar outra nota do mesmo remetente/sigla: preenche
        o formulário de nova nota com Remetente e Sigla da nota escolhida e
        deixa NF e ocorrência para o usuário digitar. O número da NF NÃO é
        copiado de propósito: a regra de unicidade (NF + Remetente) impede
        duas notas com o mesmo número para o mesmo remetente."""
        nota = db.obter_nota(nota_id)
        if nota is None:
            return
        self.var_nf.set("")
        self.var_cliente.set(nota["cliente"])
        self.var_ocorrencia.set("")
        self.var_sigla.set(nota["sigla"])
        self._suggestion_var.set("")
        self.entry_nf.focus_set()

    def editar_ocorrencia(self, nota_id):
        nota = db.obter_nota(nota_id)
        if nota is None:
            return
        tipos = db.listar_tipos_ocorrencia()
        escolha = pedir_opcao(self, "Editar ocorrência",
                              "Busque o tipo de ocorrência (ou digite um novo):", tipos)
        if escolha is None:
            return
        ocorrencia_final, eh_novo = escolha
        ocorrencia_final = ocorrencia_final.strip().upper()
        if not ocorrencia_final:
            return
        if eh_novo:
            sugestao = occ.sugerir_ocorrencia(ocorrencia_final, tipos)
            if sugestao:
                ocorrencia_final, eh_novo = sugestao.upper(), False
        if eh_novo and not messagebox.askyesno(
                "Nova ocorrência", "Cadastrar '%s' como novo tipo?" % ocorrencia_final, parent=self):
            return
        agendamento_data = None
        if occ.eh_ocorrencia_agendamento(ocorrencia_final):
            agendamento_data = self._pedir_data_agendamento(
                nota["agendamento_data"] if occ.eh_ocorrencia_agendamento(nota["ocorrencia"]) else None)
            if agendamento_data is None:
                return  # cancelado/invalido: nada e alterado
        try:
            db.atualizar_ocorrencia(nota_id, ocorrencia_final, agendamento_data)
            if eh_novo:
                db.adicionar_tipo_ocorrencia(ocorrencia_final)
        except sqlite3.Error as erro:
            messagebox.showerror("Erro", "Falha ao salvar a alteração: %s" % erro, parent=self)
            return
        self._registrar_desfazer_campos(nota, "alteração da ocorrência", ["ocorrencia", "agendamento_data"])
        self._garantir_visibilidade(nota["cliente"], nota["sigla"], ocorrencia_final)
        self._atualizar_bloco_rapido(nota_id)

