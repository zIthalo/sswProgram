# -*- coding: utf-8 -*-
"""
registro_erros.py
Registro de erros inesperados em "erros.log" (ao lado do banco de dados).

Antes, quando algo falhava dentro de um menu/botao, o Tkinter apenas imprimia
o erro no console - que no .exe nem existe -, e o usuario via "nada
acontecer". Agora:
  * o erro completo (data, versao, traceback) e gravado em erros.log;
  * o usuario recebe uma mensagem amigavel dizendo onde esta o arquivo, para
    poder enviar ao desenvolvedor.
O arquivo e recriado quando passa de 1 MB (o anterior vira erros.log.antigo).
"""

import os
import sys
import time
import traceback
from datetime import datetime

from nucleo import database as db
from nucleo import versao

NOME_ARQUIVO = "erros.log"
TAMANHO_MAXIMO = 1024 * 1024
INTERVALO_MENSAGEM_S = 10  # evita uma enxurrada de janelas se o mesmo erro se repetir

_ultima_mensagem = [0.0]


def caminho_log():
    return os.path.join(os.path.dirname(db.get_db_path()), NOME_ARQUIVO)


def registrar(exc_type, exc, tb, contexto=""):
    """Grava o erro no log. Nunca levanta excecao (o log nao pode causar outro erro).
    Retorna o caminho do log, ou None se nao foi possivel gravar."""
    caminho = caminho_log()
    try:
        if os.path.exists(caminho) and os.path.getsize(caminho) > TAMANHO_MAXIMO:
            antigo = caminho + ".antigo"
            if os.path.exists(antigo):
                os.remove(antigo)
            os.replace(caminho, antigo)
        with open(caminho, "a", encoding="utf-8") as arq:
            arq.write("=" * 70 + "\n")
            arq.write("%s | versao %s%s\n" % (
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"), versao.VERSAO,
                (" | " + contexto) if contexto else ""))
            arq.write("".join(traceback.format_exception(exc_type, exc, tb)))
            arq.write("\n")
        return caminho
    except Exception:
        return None


def _avisar_usuario(janela, exc, caminho):
    agora = time.time()
    if agora - _ultima_mensagem[0] < INTERVALO_MENSAGEM_S:
        return
    _ultima_mensagem[0] = agora
    try:
        from tkinter import messagebox
        texto = "Ocorreu um erro inesperado e a ação não foi concluída.\n\n%s: %s\n\n" % (
            type(exc).__name__, exc)
        if caminho:
            texto += "Os detalhes foram salvos em:\n%s\n\nEnvie este arquivo ao desenvolvedor." % caminho
        else:
            texto += "Não foi possível gravar o arquivo de registro de erros."
        messagebox.showerror("Erro inesperado", texto, parent=janela)
    except Exception:
        pass


def instalar():
    """Liga o registro: erros em callbacks do Tkinter (menus, botoes, teclas)
    e excecoes nao tratadas passam a ir para o erros.log."""
    import tkinter as tk

    def _callback_tk(self, exc_type, exc, tb):
        caminho = registrar(exc_type, exc, tb, "callback Tkinter")
        _avisar_usuario(self, exc, caminho)

    tk.Tk.report_callback_exception = _callback_tk

    original = sys.excepthook

    def _hook(exc_type, exc, tb):
        registrar(exc_type, exc, tb, "excecao nao tratada")
        original(exc_type, exc, tb)

    sys.excepthook = _hook
