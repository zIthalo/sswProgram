# -*- coding: utf-8 -*-
"""Icone da janela (barra de titulo e barra de tarefas)."""

import os
import sys
import tkinter as tk


def caminho_icone():
    """Caminho do icone.ico: dentro do .exe (PyInstaller) ou na pasta recursos/ do projeto."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "recursos", "icone.ico")


def aplicar_icone(janela):
    """Aplica o icone na janela (e nas janelas filhas). Falha em silencio: o icone e so estetica."""
    caminho = caminho_icone()
    if not os.path.isfile(caminho):
        return False
    try:
        janela.iconbitmap(default=caminho)  # default= => vale tambem para os Toplevel
        return True
    except tk.TclError:  # ex.: Linux nao aceita .ico
        return False
