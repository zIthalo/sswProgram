# -*- coding: utf-8 -*-
"""
Backup, exportacoes, atualizacao do sistema e cadastros (listas).
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from nucleo import atualizacoes
from nucleo import backup
from nucleo import database as db
from nucleo import exportacoes
from nucleo import versao
from interface.dialogs import GerenciarLista


class ManutencaoMixin:
    def _criar_backup_manual(self):
        caminho = backup.criar_backup("manual")
        if caminho:
            messagebox.showinfo(
                "Backup criado",
                "Backup salvo em:\n%s" % caminho, parent=self)
        else:
            messagebox.showerror(
                "Backup", "Não foi possível criar o backup.", parent=self)

    def _exportar_tudo(self):
        pasta = filedialog.askdirectory(
            parent=self, title="Escolha a pasta onde salvar a exportação completa")
        if not pasta:
            return
        try:
            destino = exportacoes.exportar_tudo(pasta)
        except (OSError, Exception) as erro:
            messagebox.showerror("Exportar tudo", "Falha ao exportar: %s" % erro, parent=self)
            return
        messagebox.showinfo(
            "Exportação concluída",
            "Cópia do banco de dados + notas.csv, tratativas.csv e historico.csv "
            "salvos em:\n%s" % destino, parent=self)

    def _exportar_csv(self, titulo, nome_sugerido, funcao_exportar, parent):
        caminho = filedialog.asksaveasfilename(
            parent=parent, title=titulo, defaultextension=".csv", initialfile=nome_sugerido,
            filetypes=[("Planilha CSV (Excel)", "*.csv")])
        if not caminho:
            return
        try:
            funcao_exportar(caminho)
        except OSError as erro:
            messagebox.showerror(
                "Exportar", "Falha ao salvar o arquivo (ele está aberto no Excel?):\n%s" % erro,
                parent=parent)
            return
        messagebox.showinfo("Exportar", "Arquivo salvo em:\n%s" % caminho, parent=parent)

    # ------------------------------------------------------------------
    # Verificação de atualizações (GitHub Releases)
    # ------------------------------------------------------------------
    def _verificar_atualizacoes_automatico(self):
        """Checagem silenciosa feita ao abrir o sistema: roda numa thread
        separada (para não travar a tela) e só interrompe o usuário se
        encontrar uma versão mais nova. Qualquer falha (sem internet, etc.)
        é ignorada sem aviso nenhum."""
        def tarefa():
            info = atualizacoes.verificar_nova_versao()
            if info:
                self.after(0, lambda: self._perguntar_se_atualiza(info, manual=False))
        threading.Thread(target=tarefa, daemon=True).start()

    def _verificar_atualizacoes_manual(self):
        """Checagem disparada pelo menu Arquivo > Verificar atualizações:
        mostra o resultado mesmo quando não há nada novo."""
        def tarefa():
            info = atualizacoes.verificar_nova_versao()
            self.after(0, lambda: self._mostrar_resultado_verificacao_manual(info))
        threading.Thread(target=tarefa, daemon=True).start()

    def _mostrar_resultado_verificacao_manual(self, info):
        if info:
            self._perguntar_se_atualiza(info, manual=True)
        else:
            messagebox.showinfo(
                "Verificar atualizações",
                "Você já está usando a versão mais recente (%s)." % versao.VERSAO,
                parent=self,
            )

    def _perguntar_se_atualiza(self, info, manual):
        notas = ("\n\n%s" % info["notas"]) if info["notas"] else ""
        confirmar = messagebox.askyesno(
            "Nova versão disponível",
            "Uma nova versão (%s) está disponível — você está usando a %s.%s\n\n"
            "Deseja baixar e instalar agora? O sistema será fechado e reaberto "
            "automaticamente ao final." % (info["versao"], versao.VERSAO, notas),
            parent=self,
        )
        if confirmar:
            self._baixar_e_aplicar_atualizacao(info)

    def _baixar_e_aplicar_atualizacao(self, info):
        if self._reapresentar_janela("atualizando"):
            return
        janela = tk.Toplevel(self)
        self._registrar_janela("atualizando", janela)
        janela.title("Atualizando...")
        janela.resizable(False, False)
        janela.protocol("WM_DELETE_WINDOW", lambda: None)  # não deixa fechar no meio do download
        frame = ttk.Frame(janela, padding=16)
        frame.pack(fill="both", expand=True)
        rotulo = ttk.Label(frame, text="Baixando versão %s..." % info["versao"])
        rotulo.pack(pady=(0, 8))
        barra = ttk.Progressbar(frame, mode="determinate", length=280, maximum=100)
        barra.pack()
        janela.update_idletasks()
        largura, altura = janela.winfo_reqwidth(), janela.winfo_reqheight()
        janela.geometry("+%d+%d" % (
            self.winfo_rootx() + (self.winfo_width() // 2) - (largura // 2),
            self.winfo_rooty() + (self.winfo_height() // 2) - (altura // 2),
        ))

        def progresso(lido, total):
            if total:
                self.after(0, lambda: barra.configure(value=min(100, int(lido * 100 / total))))

        def tarefa():
            caminho = atualizacoes.baixar_novo_executavel(info, progresso_callback=progresso)
            self.after(0, lambda: concluir(caminho))

        def concluir(caminho):
            janela.destroy()
            if not caminho:
                messagebox.showerror(
                    "Falha ao atualizar",
                    "Não foi possível baixar a nova versão. Verifique sua conexão com a "
                    "internet e tente novamente pelo menu Arquivo > Verificar atualizações.",
                    parent=self,
                )
                return
            backup.criar_backup("antes_atualizacao")
            if atualizacoes.aplicar_atualizacao(caminho):
                self.destroy()
            else:
                messagebox.showwarning(
                    "Atualização automática indisponível",
                    "O download foi concluído, mas a troca automática do executável só "
                    "funciona na versão instalada (.exe) com o atualizador.exe presente na "
                    "mesma pasta. Baixe e instale a nova versão manualmente em:\n%s"
                    % versao.URL_RELEASES,
                    parent=self,
                )

        threading.Thread(target=tarefa, daemon=True).start()

    def _gerenciar_empresas_parceiras(self):
        self._abrir_janela_unica("lista:empresas", lambda: GerenciarLista(
            self, "Empresas parceiras", db.listar_empresas_parceiras,
            db.adicionar_empresa_parceira, db.remover_empresa_parceira,
            ao_remover=lambda nome: self._registrar_desfazer_cadastro(
                "empresa parceira", nome, db.adicionar_empresa_parceira)))
        self._atualizar_combobox_sigla()

    def _gerenciar_tipos_ocorrencia(self):
        self._abrir_janela_unica("lista:tipos", lambda: GerenciarLista(
            self, "Tipos de ocorrência",
            db.listar_tipos_ocorrencia, db.adicionar_tipo_ocorrencia,
            db.remover_tipo_ocorrencia,
            ao_remover=lambda nome: self._registrar_desfazer_cadastro(
                "tipo de ocorrência", nome, db.adicionar_tipo_ocorrencia)))
        self._atualizar_combobox_filtro()

    def _gerenciar_clientes(self):
        self._abrir_janela_unica("lista:remetentes", lambda: GerenciarLista(
            self, "Remetentes", db.listar_clientes,
            db.adicionar_cliente, db.remover_cliente,
            ao_remover=lambda nome: self._registrar_desfazer_cadastro(
                "remetente", nome, db.adicionar_cliente)))

    def _registrar_desfazer_cadastro(self, rotulo, nome, funcao_adicionar):
        self.pilha_desfazer.registrar("remoção do %s %s" % (rotulo, nome),
                                      lambda: funcao_adicionar(nome))

