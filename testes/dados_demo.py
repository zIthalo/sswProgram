# -*- coding: utf-8 -*-
"""
Dados FICTICIOS para as previas de layout. Cria um banco temporario: o seu
sac_logistica.db nunca e lido nem alterado pelas previas.
"""

import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from nucleo import database as db


def preparar_banco_demo():
    pasta = tempfile.mkdtemp(prefix="sac_previa_")
    caminho = os.path.join(pasta, "demo.db")
    mock.patch.object(db, "get_db_path", lambda: caminho).start()
    db.init_db()
    hoje = datetime.now()

    notas = [
        # nf, cliente, ocorrencia, sigla, dias_atras, agendamento(dias a frente), obs, tratativas
        (48213, "DISTRIBUIDORA ALFA LTDA", "REENTREGA", "SP", 6, None, "PROTOCOLO 88231",
         ["TRATANDO VIA E-MAIL", "AGUARDANDO RETORNO DO CLIENTE", "MERCADORIA EM ROTA DE ENTREGA HOJE"]),
        (51877, "COMERCIAL BETA S/A", "AGENDAMENTO", "RJ", 2, 3, None,
         ["TRATANDO VIA WHATSAPP", "CLIENTE CONFIRMOU RECEBIMENTO NO DIA AGENDADO"]),
        (50342, "INDUSTRIA GAMA", "LOCALIZAÇÃO", "BH", 11, None, "URGENTE",
         ["INFORMACOES EM SISTEMA", "UNIDADE VERIFICANDO CARGA NO PATIO"]),
        (52019, "MERCADO DELTA", "PRIORIZAR ENTREGA", "SP", 0, None, None, []),
        (49760, "FARMA ÔMEGA", "COMPROVANTE", "AGEX", 4, None, None,
         ["SOLICITADO CANHOTO A PARCEIRA"]),
        (52144, "ASPEN COMERCIO", "MUDOU-SE", "RJ", 1, None, None, ["TRATANDO VIA E-MAIL"]),
        (47105, "SPEED LOG", "DEVOLUÇÃO", "RISSO", 15, None, "REVERSA APROVADA",
         ["TRATANDO VIA E-MAIL", "DEVOLUCAO AUTORIZADA", "AGUARDANDO COLETA"]),
    ]
    for nf, cliente, oc, sigla, dias, agenda, obs, trats in notas:
        criado = hoje - timedelta(days=dias, hours=2)
        ag = (hoje + timedelta(days=agenda)).strftime("%d%m%Y") if agenda else None
        nid = db.inserir_nota(nf, cliente, oc, sigla, criado.strftime("%d%m%Y"), ag, obs)
        con = sqlite3.connect(caminho)
        con.execute("UPDATE notas SET criado_em=? WHERE id=?", (criado.isoformat(), nid))
        con.commit()
        con.close()
        for i, texto in enumerate(trats):
            db.adicionar_tratativa(nid, texto)
        con = sqlite3.connect(caminho)
        for i, (tid,) in enumerate(con.execute("SELECT id FROM tratativas WHERE nota_id=? ORDER BY id", (nid,)).fetchall()):
            ts = (criado + timedelta(hours=3 + i * 20)).strftime("%d/%m/%Y %H:%M")
            con.execute("UPDATE tratativas SET timestamp=? WHERE id=?", (ts, tid))
        con.commit()
        con.close()
        db.adicionar_cliente(cliente)
    return caminho
