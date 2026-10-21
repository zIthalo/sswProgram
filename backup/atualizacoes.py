# -*- coding: utf-8 -*-
"""
atualizacoes.py
Verificacao e download de novas versoes do sistema, publicadas como
"Releases" no repositorio publico do GitHub (ver versao.py).

Fluxo:
1. verificar_nova_versao() consulta a API do GitHub (so leitura de um
   JSON publico, sem necessidade de login/token) e compara a versao mais
   recente la publicada com a versao local (versao.VERSAO).
2. Se houver versao mais nova, baixar_novo_executavel() baixa o .exe
   anexado aquela release para uma pasta temporaria.
3. aplicar_atualizacao() aciona o "atualizador.exe" (programa auxiliar,
   compilado separadamente - ver atualizador.py) para substituir o
   executavel atual pelo novo e reabrir o sistema. Isso e necessario
   porque um .exe em execucao no Windows nao pode se autosubstituir.

Tudo aqui e deliberadamente defensivo: qualquer falha de rede, API fora
do ar, timeout, etc. e silenciosamente ignorada (retorna None/False) -
a verificacao de atualizacao jamais deve travar ou impedir o uso normal
do sistema.
"""

import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

import versao

TIMEOUT_VERIFICACAO = 6
TIMEOUT_DOWNLOAD = 30


def _versao_para_tupla(texto):
    """Converte 'v1.4.2' (ou '1.4.2') em (1, 4, 2) para comparacao numerica
    (comparar strings diretamente falharia, por exemplo, com '1.10.0' < '1.9.0')."""
    texto = (texto or "").strip()
    if texto[:1] in ("v", "V"):
        texto = texto[1:]
    partes = []
    for pedaco in texto.split("."):
        numero = "".join(c for c in pedaco if c.isdigit())
        partes.append(int(numero) if numero else 0)
    while len(partes) < 3:
        partes.append(0)
    return tuple(partes[:3])


def verificar_nova_versao():
    """
    Consulta a release mais recente publicada no GitHub.

    Retorna um dict com os dados da nova versao
    ({"versao": "v1.1.0", "url_download": "...", "nome_arquivo": "main.exe", "notas": "..."})
    se houver uma versao mais nova do que a instalada, ou None se nao
    houver (ja esta atualizado) ou se a verificacao falhar por qualquer
    motivo (sem internet, API fora do ar, repositorio sem releases, etc.).
    """
    try:
        req = urllib.request.Request(
            versao.URL_API_ULTIMA_RELEASE,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "sswProgram-updater"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_VERIFICACAO) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, OSError):
        return None

    tag = dados.get("tag_name") or ""
    if not tag:
        return None

    if _versao_para_tupla(tag) <= _versao_para_tupla(versao.VERSAO):
        return None  # ja esta na versao mais recente

    ativos = dados.get("assets") or []
    executavel = next(
        (a for a in ativos
         if a.get("name", "").lower().endswith(".exe")
         and "atualizador" not in a.get("name", "").lower()),
        None,
    )
    if executavel is None:
        return None  # release publicada sem o executavel principal anexado

    return {
        "versao": tag,
        "url_download": executavel["browser_download_url"],
        "nome_arquivo": executavel["name"],
        "notas": (dados.get("body") or "").strip(),
    }


def baixar_novo_executavel(info_versao, progresso_callback=None):
    """
    Baixa o .exe da nova versao para uma pasta temporaria.
    'progresso_callback', se informado, e chamado como progresso_callback(lido, total)
    a cada bloco baixado (total pode ser 0 se o servidor nao informar o tamanho).

    Retorna o caminho do arquivo baixado, ou None se o download falhar ou
    o arquivo vier incompleto/corrompido.
    """
    pasta_destino = os.path.join(tempfile.gettempdir(), "sswprogram_update_%s" % info_versao["versao"])
    os.makedirs(pasta_destino, exist_ok=True)
    caminho_arquivo = os.path.join(pasta_destino, info_versao["nome_arquivo"])

    try:
        req = urllib.request.Request(
            info_versao["url_download"],
            headers={"User-Agent": "sswProgram-updater"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_DOWNLOAD) as resp:
            total = int(resp.headers.get("Content-Length", 0) or 0)
            lido = 0
            with open(caminho_arquivo, "wb") as f:
                while True:
                    bloco = resp.read(65536)
                    if not bloco:
                        break
                    f.write(bloco)
                    lido += len(bloco)
                    if progresso_callback:
                        progresso_callback(lido, total)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return None

    if not os.path.exists(caminho_arquivo) or os.path.getsize(caminho_arquivo) < 1024:
        return None  # download incompleto ou corrompido

    return caminho_arquivo


def aplicar_atualizacao(caminho_novo_exe):
    """
    Aciona o atualizador.exe (deve estar na mesma pasta do executavel
    principal) para substituir o .exe atual pelo baixado e reabrir o
    sistema. NAO encerra o processo atual - quem chamar esta funcao deve
    fechar a aplicacao (ex.: self.destroy()) logo em seguida.

    So funciona quando o sistema esta rodando como .exe (empacotado pelo
    PyInstaller); em modo desenvolvimento (python main.py) nao ha .exe
    para substituir, entao retorna False sem fazer nada.
    """
    if not getattr(sys, "frozen", False):
        return False

    exe_atual = sys.executable
    pasta_atual = os.path.dirname(exe_atual)
    atualizador = os.path.join(pasta_atual, "atualizador.exe")

    if not os.path.exists(atualizador):
        return False

    subprocess.Popen([atualizador, exe_atual, caminho_novo_exe], close_fds=True)
    return True
