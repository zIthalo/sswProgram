# -*- coding: utf-8 -*-
"""
Regras de janelas secundarias da aplicacao:
  * abrem SEMPRE na frente da janela que as abriu (e da janela principal);
  * cada tipo de janela so pode estar aberto uma vez - pedir de novo apenas
    traz a janela existente para a frente;
  * a janela principal lembra posicao/tamanho ao fechar (ver nucleo/posicao_janela.py).
"""

import tkinter as tk

from nucleo import posicao_janela


class JanelasMixin:
    # ------------------------------------------------------------------
    # Janelas secundarias: sempre na frente, sem duplicar
    # ------------------------------------------------------------------
    def _janela_ativa(self):
        """Janela (toplevel) em uso agora; usada como 'pai' das novas janelas para
        que apareçam na frente de quem as abriu (ex.: detalhes aberto a partir do Relatório)."""
        try:
            foco = self.focus_get()
            topo = foco.winfo_toplevel() if foco is not None else self
            return topo if topo.winfo_exists() else self
        except (KeyError, tk.TclError):
            return self

    def _trazer_para_frente(self, janela):
        """Coloca a janela na frente e COM FOCO. O foco so pega depois que a janela
        esta visivel na tela; por isso tenta de novo a cada 20 ms (ate ~1 s) e
        mais uma vez ao final, caso o gerenciador de janelas tenha roubado o foco."""
        try:
            if janela.state() in ("iconic", "withdrawn"):
                janela.deiconify()
            janela.lift()
        except tk.TclError:
            return
        self._focar_quando_visivel(janela, 50)

    def _focar_quando_visivel(self, janela, tentativas):
        try:
            if not janela.winfo_exists():
                return
            if janela.winfo_viewable():
                janela.lift()
                janela.focus_force()
                alvo = getattr(janela, "widget_foco", None)  # campo que deve receber o cursor
                if alvo is not None:
                    alvo.focus_set()
                if tentativas > 10:  # reforco unico apos a janela estabilizar
                    janela.after(150, lambda: self._focar_quando_visivel(janela, 0))
                return
            if tentativas > 0:
                janela.after(20, lambda: self._focar_quando_visivel(janela, tentativas - 1))
        except tk.TclError:
            pass

    def _posicionar_sobre(self, janela, pai):
        """Centraliza a janela sobre a janela `pai` (a principal, ou a secundaria de onde
        foi aberta), mantendo-a inteira dentro da tela."""
        try:
            janela.update_idletasks()
            if pai.state() == "iconic":
                pai = self
            largura, altura = janela.winfo_width(), janela.winfo_height()
            if largura <= 1 or altura <= 1:
                largura, altura = janela.winfo_reqwidth(), janela.winfo_reqheight()
            x = pai.winfo_rootx() + (pai.winfo_width() - largura) // 2
            y = pai.winfo_rooty() + (pai.winfo_height() - altura) // 2
            vx, vy = self.winfo_vrootx(), self.winfo_vrooty()
            vw, vh = self.winfo_vrootwidth(), self.winfo_vrootheight()
            x = max(vx, min(x, vx + vw - largura))
            y = max(vy, min(y, vy + vh - altura - 40))  # 40 px: folga para a barra de tarefas
            janela.geometry("+%d+%d" % (x, y))
        except tk.TclError:
            pass

    def _reapresentar_janela(self, chave):
        """Se ja existe uma janela aberta com esta chave, a traz para a frente e
        retorna True (quem chamou NAO deve criar outra). Senao retorna False."""
        atual = self._janelas_unicas.get(chave)
        try:
            existe = atual is not None and atual.winfo_exists()
        except tk.TclError:
            existe = False
        if existe:
            self._trazer_para_frente(atual)
            return True
        self._janelas_unicas.pop(chave, None)
        return False

    def _registrar_janela(self, chave, janela, pai=None):
        """Registra a janela recem-criada (para impedir duplicatas), amarra-a ao pai
        (fica sempre na frente dele) e a coloca em primeiro plano."""
        self._janelas_unicas[chave] = janela
        try:
            janela.transient(pai or self)
        except tk.TclError:
            pass

        def ao_destruir(event, chave=chave, janela=janela):
            if event.widget is janela and self._janelas_unicas.get(chave) is janela:
                del self._janelas_unicas[chave]
        janela.bind("<Destroy>", ao_destruir, add="+")
        alvo = pai or self

        def mostrar():
            self._posicionar_sobre(janela, alvo)
            self._trazer_para_frente(janela)
        janela.after_idle(mostrar)
        return janela

    def _abrir_janela_unica(self, chave, criar):
        """Atalho: reapresenta a janela da chave ou cria uma com criar() (que devolve o Toplevel)."""
        if self._reapresentar_janela(chave):
            return self._janelas_unicas[chave]
        return self._registrar_janela(chave, criar())

    # ------------------------------------------------------------------
    # Posicao da janela principal
    # ------------------------------------------------------------------
    def _restaurar_posicao_janela(self, geometria_padrao):
        """Aplica a posicao/tamanho salvos (se ainda couberem nas telas atuais);
        senao usa a geometria padrao."""
        self._geometria_normal = None
        estado = posicao_janela.carregar()
        ajustado = None
        if estado:
            try:
                ajustado = posicao_janela.ajustar_a_tela(
                    estado, self.winfo_vrootx(), self.winfo_vrooty(),
                    self.winfo_vrootwidth(), self.winfo_vrootheight())
            except tk.TclError:
                ajustado = None
        if ajustado:
            self.geometry(posicao_janela.formatar_geometria(*ajustado))
            self._geometria_normal = ajustado
            if estado["maximizada"]:
                try:
                    self.state("zoomed")
                except tk.TclError:
                    try:
                        self.attributes("-zoomed", True)
                    except tk.TclError:
                        pass
        else:
            self.geometry(geometria_padrao)
        self.bind("<Configure>", self._ao_mudar_geometria, add="+")

    def _ao_mudar_geometria(self, event):
        # Guarda a ultima geometria "normal" (nao maximizada/minimizada): e ela que
        # sera restaurada quando o usuario sair do modo maximizado.
        if event.widget is not self:
            return
        try:
            if self.state() != "normal":
                return
        except tk.TclError:
            return
        atual = posicao_janela.interpretar_geometria(self.geometry())
        if atual:
            self._geometria_normal = atual

    def _salvar_posicao_janela(self):
        try:
            maximizada = self.state() == "zoomed" or bool(self.attributes("-zoomed"))
        except tk.TclError:
            maximizada = False
        if maximizada and self._geometria_normal:
            largura, altura, x, y = self._geometria_normal
        else:
            atual = posicao_janela.interpretar_geometria(self.geometry()) or self._geometria_normal
            if not atual:
                return
            largura, altura, x, y = atual
        posicao_janela.salvar(largura, altura, x, y, maximizada)
