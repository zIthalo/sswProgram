# -*- coding: utf-8 -*-
"""
atualizador.py
Programa auxiliar, EMPACOTADO SEPARADAMENTE (gera "atualizador.exe"), que
substitui o executavel principal (main.exe) por uma versao mais nova ja
baixada do GitHub, e o reabre em seguida.

Precisa ser um .exe separado do principal porque o Windows nao permite
que um executavel em uso sobrescreva a si mesmo.

Uso (chamado automaticamente pelo sistema principal, nao pelo usuario):
    atualizador.exe <caminho_do_main.exe_atual> <caminho_do_novo_exe_baixado>

Fica parado tentando substituir o arquivo por alguns segundos, porque o
programa principal esta se fechando no mesmo instante em que aciona este
atualizador - o arquivo so fica livre para ser sobrescrito depois que ele
realmente encerrar.
"""

import os
import shutil
import subprocess
import sys
import time

TENTATIVAS = 40
INTERVALO_SEGUNDOS = 0.5


def main():
    if len(sys.argv) < 3:
        return

    exe_atual = sys.argv[1]
    novo_exe = sys.argv[2]

    substituido = False
    for _ in range(TENTATIVAS):
        try:
            shutil.copy2(novo_exe, exe_atual)
            substituido = True
            break
        except (PermissionError, OSError):
            time.sleep(INTERVALO_SEGUNDOS)

    if not substituido:
        return  # desiste silenciosamente; o usuario pode tentar atualizar de novo depois

    try:
        shutil.rmtree(os.path.dirname(novo_exe), ignore_errors=True)
    except OSError:
        pass

    try:
        subprocess.Popen([exe_atual], close_fds=True)
    except OSError:
        pass


if __name__ == "__main__":
    main()
