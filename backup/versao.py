# -*- coding: utf-8 -*-
"""
versao.py
Versao atual do sistema e dados do repositorio usado para checar
atualizacoes.

IMPORTANTE: a cada nova versao publicada como Release no GitHub, alterar
o valor de VERSAO abaixo ANTES de gerar o novo main.exe com o PyInstaller,
e usar o mesmo numero (com "v" na frente) como tag do Release no GitHub.
Exemplo: VERSAO = "1.1.0" aqui  ->  tag "v1.1.0" no Release.

Se os dois nao baterem, o sistema instalado nunca vai perceber que existe
uma versao nova (ou vai ficar perguntando por uma atualizacao que, na
pratica, e a mesma versao que ja esta rodando).
"""

VERSAO = "1.0.0"

REPOSITORIO_GITHUB = "zIthalo/sswProgram"
URL_API_ULTIMA_RELEASE = "https://api.github.com/repos/%s/releases/latest" % REPOSITORIO_GITHUB
URL_RELEASES = "https://github.com/%s/releases" % REPOSITORIO_GITHUB
