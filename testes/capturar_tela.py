# -*- coding: utf-8 -*-
"""Ferramenta de desenvolvimento: abre o sistema com dados FICTICIOS (banco temporario) e salva uma
imagem da tela. Linux (tela virtual):
    xvfb-run -a -s "-screen 0 1280x900x24" python3 testes/capturar_tela.py saida.png 1180 780 [gaveta]
O seu sac_logistica.db nunca e aberto."""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from testes.dados_demo import preparar_banco_demo


def esperar(app, segundos=1.2):
    fim = time.time() + segundos
    while time.time() < fim:
        app.update()


def main(destino, largura, altura, extra=None):
    preparar_banco_demo()
    from interface.app import App
    app = App()
    app.geometry("%dx%d+10+10" % (largura, altura))
    esperar(app)
    if extra == "gaveta":
        app.atalho_nova_nota()
        esperar(app, 0.6)
    subprocess.run(["import", "-window", "root", destino], check=True)
    app.destroy()


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else None)
