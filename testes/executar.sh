#!/bin/sh
# Roda todos os testes automaticos. Execute na raiz do projeto: sh testes/executar.sh
# No Linux sem monitor usa xvfb-run (tela virtual); no Windows rode direto:
#     python -m unittest discover -s testes -t . -v
cd "$(dirname "$0")/.." || exit 1
if [ -z "$DISPLAY" ] && command -v xvfb-run >/dev/null 2>&1; then
    exec xvfb-run -a python3 -m unittest discover -s testes -t . -v
fi
exec python3 -m unittest discover -s testes -t . -v
