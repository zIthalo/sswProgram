# -*- coding: utf-8 -*-
"""
backup.py
Backup automatico (e manual) do banco de dados SQLite.

O banco (sac_logistica.db) e um arquivo unico local: se o computador tiver
um problema (disco corrompido, exclusao acidental, etc.), ele pode ser
perdido por completo. Este modulo mantem copias datadas dele numa subpasta
"backups", ao lado do banco original.

Cuidados tomados:
- A copia e feita com o banco em modo WAL + synchronous=NORMAL (ver
  database.get_connection); copiar o arquivo .db sozinho, sem copiar os
  arquivos -wal/-shm que podem existir ao lado dele, poderia perder as
  ultimas escritas ainda nao mescladas de volta ao arquivo principal. Por
  isso, antes de copiar, e feito um PRAGMA wal_checkpoint(TRUNCATE), que
  forca tudo o que estiver no WAL a ser gravado no arquivo .db principal
  (o mesmo tipo de cuidado que um backup de banco de dados "a quente" exige).
- So mantém os ultimos N backups (por padrao 30), apagando os mais antigos,
  para não deixar a pasta crescendo sem limite.
- Qualquer falha aqui (disco cheio, permissao negada, etc.) e tratada sem
  derrubar o sistema - um backup que falha nunca deve impedir o uso normal
  do programa.
"""

import os
import shutil
import sqlite3
from datetime import datetime

import database as db

NOME_PASTA_BACKUPS = "backups"
MAXIMO_BACKUPS_AUTOMATICOS = 30


def pasta_backups():
    pasta = os.path.join(os.path.dirname(db.get_db_path()), NOME_PASTA_BACKUPS)
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _checkpoint_wal():
    """Garante que as escritas recentes (ainda no arquivo -wal) sejam
    gravadas no arquivo principal do banco antes de copia-lo."""
    try:
        conn = sqlite3.connect(db.get_db_path())
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
    except sqlite3.Error:
        pass  # segue mesmo assim; o checkpoint e so uma garantia extra


def criar_backup(motivo="automatico"):
    """
    Cria uma cópia datada do banco de dados na pasta de backups.
    'motivo' vira parte do nome do arquivo (ex.: 'automatico', 'manual',
    'antes_atualizacao') só para facilitar identificar depois por que
    aquele backup foi feito.

    Retorna o caminho do backup criado, ou None se a cópia falhar (qualquer
    erro é silenciosamente ignorado — um backup que falha não deve travar
    o sistema).
    """
    origem = db.get_db_path()
    if not os.path.exists(origem):
        return None

    _checkpoint_wal()

    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_destino = "%s_%s_%s" % (db.DB_NAME.replace(".db", ""), carimbo, motivo)
    destino = os.path.join(pasta_backups(), nome_destino + ".db")

    try:
        shutil.copy2(origem, destino)
    except OSError:
        return None

    if motivo == "automatico":
        _podar_backups_antigos()

    return destino


def _podar_backups_antigos(maximo=MAXIMO_BACKUPS_AUTOMATICOS):
    """Mantém só os N backups automáticos mais recentes, apagando os
    excedentes mais antigos. Backups manuais e 'antes_atualizacao' não são
    contados aqui nem apagados automaticamente — só o usuário apaga esses."""
    pasta = pasta_backups()
    try:
        arquivos = [
            f for f in os.listdir(pasta)
            if f.endswith("_automatico.db")
        ]
    except OSError:
        return
    arquivos.sort()  # o carimbo de data/hora no nome ordena cronologicamente
    excedente = len(arquivos) - maximo
    for nome in arquivos[:max(excedente, 0)]:
        try:
            os.remove(os.path.join(pasta, nome))
        except OSError:
            pass


def listar_backups():
    """Retorna a lista de backups existentes (nome do arquivo, mais recente
    primeiro) para exibição numa tela de gerenciamento, se necessário."""
    pasta = pasta_backups()
    try:
        arquivos = [f for f in os.listdir(pasta) if f.endswith(".db")]
    except OSError:
        return []
    arquivos.sort(reverse=True)
    return arquivos
