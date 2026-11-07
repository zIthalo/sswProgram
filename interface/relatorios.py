# -*- coding: utf-8 -*-
"""
Relatorio de morosidade e historico.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from nucleo import database as db
from nucleo import exportacoes


class RelatoriosMixin:
    def _abrir_clientes_cnpj(self):
        from interface.clientes_cnpj import JanelaClientesCnpj
        self._abrir_janela_unica("clientes_cnpj", lambda: JanelaClientesCnpj(self))

    def _abrir_relatorio(self):
        db.limpar_historico_expirado(60)
        try:
            dados = db.gerar_relatorio()
        except Exception:
            dados = {
                "siglas_mais_ocorrencias": [], "unidades_mais_morosas": [],
                "clientes_mais_morosos": [], "tempo_medio_dias": 0, "tempo_medio_horas": 0,
            }

        if self._reapresentar_janela("relatorio"):
            return
        janela = tk.Toplevel(self)
        self._registrar_janela("relatorio", janela)
        janela.title("Relatório")
        janela.geometry("480x760")
        frame = ttk.Frame(janela, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Notas pendentes de tratativa:",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        try:
            total_pendentes = db.contar_notas_pendentes()
            texto_total = "  Total: %d nota(s) pendente(s)" % total_pendentes
        except Exception:
            texto_total = "  Não foi possível calcular (verifique se o programa foi atualizado corretamente)."
        ttk.Label(frame, text=texto_total).pack(anchor="w")

        linha_sigla = ttk.Frame(frame)
        linha_sigla.pack(fill="x", pady=(4, 0))
        ttk.Label(linha_sigla, text="  Por sigla/empresa:").pack(side="left")
        var_sigla_pendente = tk.StringVar()
        ttk.Entry(linha_sigla, textvariable=var_sigla_pendente, width=16).pack(side="left", padx=(6, 6))
        lbl_resultado_sigla = ttk.Label(linha_sigla, text="")
        lbl_resultado_sigla.pack(side="left")

        def atualizar_contagem_sigla(*_args):
            texto = var_sigla_pendente.get().strip()
            if not texto:
                lbl_resultado_sigla.configure(text="")
                return
            try:
                total = db.contar_notas_pendentes_por_sigla(texto)
                lbl_resultado_sigla.configure(text="%d nota(s) pendente(s)" % total)
            except Exception:
                lbl_resultado_sigla.configure(text="Não foi possível calcular.")

        var_sigla_pendente.trace_add("write", atualizar_contagem_sigla)

        ttk.Separator(frame).pack(fill="x", pady=10)
        ttk.Label(frame, text="Unidades com mais ocorrências (top 5):",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        for sigla, total in dados["siglas_mais_ocorrencias"]:
            lbl = tk.Label(frame, text="  %s — %d ocorrência(s)" % (sigla, total),
                            fg="#0645AD", cursor="hand2")
            lbl.pack(anchor="w")
            lbl.bind("<Button-1>", lambda e, s=sigla: self._mostrar_detalhes_historico(
                "Notas da unidade %s (mais ocorrências)" % s,
                db.buscar_historico_por_sigla(s)))
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
            lbl = tk.Label(frame, text="  %s — %d vez(es)" % (sigla, total),
                            fg="#0645AD", cursor="hand2")
            lbl.pack(anchor="w")
            lbl.bind("<Button-1>", lambda e, s=sigla: self._mostrar_detalhes_historico(
                "Notas da unidade %s (mais morosa)" % s,
                db.buscar_historico_por_sigla(s, somente_morosidade_unidade=True)))
        if not dados["unidades_mais_morosas"]:
            ttk.Label(frame, text="  (sem dados no histórico)").pack(anchor="w")

        ttk.Separator(frame).pack(fill="x", pady=10)
        ttk.Label(frame, text="Clientes mais morosos (top 5):",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")
        for cliente, total in dados["clientes_mais_morosos"]:
            lbl = tk.Label(frame, text="  %s — %d vez(es)" % (cliente, total),
                            fg="#0645AD", cursor="hand2")
            lbl.pack(anchor="w")
            lbl.bind("<Button-1>", lambda e, c=cliente: self._mostrar_detalhes_historico(
                "Notas do cliente %s (mais moroso)" % c,
                db.buscar_historico_por_cliente(c, somente_morosidade_cliente=True)))
        if not dados["clientes_mais_morosos"]:
            ttk.Label(frame, text="  (sem dados no histórico)").pack(anchor="w")

        ttk.Separator(frame).pack(fill="x", pady=10)
        ttk.Button(frame, text="Exportar relatório (CSV/Excel)",
                   command=lambda: self._exportar_csv(
                       "Exportar relatório", "relatorio_sac.csv",
                       exportacoes.exportar_relatorio_csv, janela)).pack(anchor="w", pady=(0, 6))
        ttk.Button(frame, text="Ver histórico completo (60 dias)",
                   command=self._abrir_historico).pack(anchor="w")
        ttk.Button(frame, text="Apagar histórico (60 dias)",
                   command=lambda: self._apagar_historico(janela)).pack(anchor="w", pady=(6, 0))

    def _apagar_historico(self, janela):
        if messagebox.askyesno("Confirmar", "Deseja realmente apagar todo o histórico?", parent=janela):
            registros = list(db.listar_historico())
            db.limpar_historico_manual()
            if registros:
                self.pilha_desfazer.registrar(
                    "limpeza do histórico (%d registro(s))" % len(registros),
                    lambda: db.restaurar_historico(registros))
            janela.destroy()
            self._abrir_relatorio()

    def _abrir_historico(self):
        """Aba de Histórico: mostra todas as notas tratadas nos últimos 60
        dias, do mais recente para o mais antigo, com filtros por cliente,
        sigla e número de NF."""
        db.limpar_historico_expirado(60)

        if self._reapresentar_janela("historico"):
            return
        janela = tk.Toplevel(self)
        self._registrar_janela("historico", janela)
        janela.title("Histórico (últimos 60 dias)")
        janela.geometry("560x620")
        janela.minsize(420, 400)
        frame = ttk.Frame(janela, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Histórico de notas tratadas (últimos 60 dias)",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")

        linha_filtros = ttk.Frame(frame)
        linha_filtros.pack(fill="x", pady=(8, 8))
        linha_filtros.columnconfigure(1, weight=1)
        linha_filtros.columnconfigure(3, weight=1)
        linha_filtros.columnconfigure(5, weight=1)

        ttk.Label(linha_filtros, text="Cliente:").grid(row=0, column=0, sticky="w")
        var_cliente = tk.StringVar()
        ttk.Entry(linha_filtros, textvariable=var_cliente).grid(row=0, column=1, padx=4, sticky="ew")

        ttk.Label(linha_filtros, text="Sigla:").grid(row=0, column=2, sticky="w")
        var_sigla = tk.StringVar()
        ttk.Entry(linha_filtros, textvariable=var_sigla, width=10).grid(row=0, column=3, padx=4, sticky="ew")

        ttk.Label(linha_filtros, text="NF:").grid(row=0, column=4, sticky="w")
        var_nf = tk.StringVar()
        ttk.Entry(linha_filtros, textvariable=var_nf, width=10).grid(row=0, column=5, padx=4, sticky="ew")

        ttk.Button(linha_filtros, text="Limpar filtros",
                   command=lambda: (var_cliente.set(""), var_sigla.set(""), var_nf.set(""))
                   ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Button(linha_filtros, text="Exportar histórico (CSV/Excel)",
                   command=lambda: self._exportar_csv(
                       "Exportar histórico", "historico_sac.csv",
                       exportacoes.exportar_historico_csv, janela)
                   ).grid(row=1, column=3, columnspan=3, sticky="e", pady=(6, 0))

        canvas = tk.Canvas(frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        interior = ttk.Frame(canvas)
        interior.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=interior, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._registrar_rolagem(janela, canvas)

        def atualizar(*_args):
            for widget in interior.winfo_children():
                widget.destroy()

            # listar_historico() ja retorna ordenado do mais recente ao mais antigo
            registros = db.listar_historico()

            cliente_f = var_cliente.get().strip().lower()
            sigla_f = var_sigla.get().strip().lower()
            nf_f = var_nf.get().strip()

            if cliente_f:
                registros = [h for h in registros if cliente_f in h["cliente"].lower()]
            if sigla_f:
                registros = [h for h in registros if sigla_f in h["sigla"].lower()]
            if nf_f:
                if nf_f.isdigit():
                    registros = [h for h in registros if h["nf_numero"] == int(nf_f)]
                else:
                    registros = []

            if not registros:
                ttk.Label(interior, text="Nenhum registro encontrado.").pack(anchor="w")
                return
            for h in registros:
                self._criar_label_historico(interior, h, wraplength=480).pack(anchor="w", pady=2)

        for var in (var_cliente, var_sigla, var_nf):
            var.trace_add("write", atualizar)

        atualizar()

    def _formatar_linha_historico(self, h):
        morosidade_txt = {"unidade": "Unidade", "cliente": "Cliente", "nenhum": "Sem morosidade"}
        return (
            "NF %s / %s / Ocorrência: %s / Sigla: %s / Tempo: %d dia(s) e %d hora(s) / "
            "Morosidade: %s / Resolvida em: %s"
        ) % (
            h["nf_numero"], h["cliente"], h["ocorrencia"], h["sigla"], h["dias"], h["horas"],
            morosidade_txt.get(h["morosidade"], "-"), h["resolvido_em"][:16].replace("T", " "),
        )

    def _criar_label_historico(self, master, h, wraplength):
        """Cria o label de uma linha de histórico/relatório; clicar nele copia
        o número da NF para a área de transferência (assim como já acontece
        nos blocos de notas ativas)."""
        lbl = tk.Label(master, text=self._formatar_linha_historico(h), wraplength=wraplength,
                        justify="left", cursor="hand2")
        lbl.bind("<Button-1>", lambda e, nf=h["nf_numero"]: self._copiar_nf_historico(nf))
        return lbl

    def _copiar_nf_historico(self, nf_numero):
        self.clipboard_clear()
        self.clipboard_append(str(nf_numero))
        self.update()
        self.mostrar_mensagem_flutuante("Número copiado!")

    def _mostrar_detalhes_historico(self, titulo, registros):
        """Mostra as notas do histórico que embasam um item clicado no top 5
        do relatório (unidade com mais ocorrências, unidade mais morosa ou cliente mais moroso)."""
        chave = "detalhes:" + titulo
        if self._reapresentar_janela(chave):
            return
        pai = self._janela_ativa()  # abre na frente da janela de onde foi clicado (ex.: Relatório)
        janela = tk.Toplevel(self)
        self._registrar_janela(chave, janela, pai)
        janela.title(titulo)
        janela.geometry("480x360")
        frame = ttk.Frame(janela, padding=12)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=titulo, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))

        canvas = tk.Canvas(frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        interior = ttk.Frame(canvas)
        interior.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=interior, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._registrar_rolagem(janela, canvas)

        if not registros:
            ttk.Label(interior, text="Nenhum registro encontrado.").pack(anchor="w")
            return
        for h in registros:
            self._criar_label_historico(interior, h, wraplength=420).pack(anchor="w", pady=2)

    # ------------------------------------------------------------------
    # Formulario de insercao de nota
    # ------------------------------------------------------------------

