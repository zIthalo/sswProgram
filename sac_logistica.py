# -*- coding: utf-8 -*-
"""
main.py
Ponto de entrada do Auxiliador de Processos Logisticos (SAC).
Execute com: python main.py

Organizacao do projeto:
    main.py        -> este arquivo (unico ponto de entrada)
    nucleo/        -> regras de negocio e dados (banco, datas, backup, exportacoes...)
    interface/     -> telas e dialogos (Tkinter)
    atualizador/   -> programa auxiliar que troca o .exe durante a atualizacao
    testes/        -> testes automaticos
"""

from interface.app import App
from nucleo import registro_erros


def main():
    registro_erros.instalar()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
