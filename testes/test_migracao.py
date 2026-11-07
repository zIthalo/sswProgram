# -*- coding: utf-8 -*-
"""
Atualizar o sistema NUNCA pode perder dados de quem ja usa uma versao antiga.
Estes testes criam um banco no formato antigo (com colunas de lembrete, sem
'observacao', indice unico global, tipos em minusculas), abrem com o codigo
atual e conferem que tudo foi preservado. Nao precisam de tela.
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from nucleo import database as db

BANCO_ANTIGO = """
CREATE TABLE notas (id INTEGER PRIMARY KEY AUTOINCREMENT, nf_numero INTEGER NOT NULL, cliente TEXT NOT NULL,
  ocorrencia TEXT NOT NULL, sigla TEXT NOT NULL, data_ocorrencia TEXT NOT NULL, criado_em TEXT NOT NULL,
  resolvido INTEGER NOT NULL DEFAULT 0, agendamento_data TEXT, lembrete_codigo TEXT, proximo_lembrete TEXT,
  verificado_parceiro INTEGER DEFAULT 0);
CREATE UNIQUE INDEX idx_nf_cliente ON notas(nf_numero, cliente);
CREATE TABLE tratativas (id INTEGER PRIMARY KEY AUTOINCREMENT, nota_id INTEGER NOT NULL,
  timestamp TEXT NOT NULL, texto TEXT NOT NULL,
  FOREIGN KEY (nota_id) REFERENCES notas(id) ON DELETE CASCADE);
CREATE TABLE historico (id INTEGER PRIMARY KEY AUTOINCREMENT, nf_numero INTEGER NOT NULL, cliente TEXT NOT NULL,
  ocorrencia TEXT NOT NULL, sigla TEXT NOT NULL, dias INTEGER NOT NULL, horas INTEGER NOT NULL,
  morosidade TEXT NOT NULL, resolvido_em TEXT NOT NULL);
CREATE TABLE ocorrencias_tipos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, built_in INTEGER DEFAULT 0);
INSERT INTO ocorrencias_tipos(nome, built_in) VALUES ('reentrega',1),('meu tipo',0);
INSERT INTO notas(nf_numero,cliente,ocorrencia,sigla,data_ocorrencia,criado_em,resolvido,agendamento_data,lembrete_codigo)
  VALUES (1,'ACME','reentrega','SP','10102026','2026-10-10T10:00:00',0,NULL,'x'),
         (2,'ACME','agendamento','RJ','11102026','2026-10-11T10:00:00',0,'25122030',NULL),
         (3,'BETA','meu tipo','SP','09102026','2026-10-09T10:00:00',1,NULL,NULL);
INSERT INTO tratativas(nota_id,timestamp,texto) VALUES
  (1,'2026-10-10T11:00:00','CONTATO FEITO'),(1,'2026-10-10T12:00:00','AGUARDANDO'),(2,'2026-10-11T11:00:00','OUTRA');
INSERT INTO historico(nf_numero,cliente,ocorrencia,sigla,dias,horas,morosidade,resolvido_em)
  VALUES (3,'BETA','meu tipo','SP',2,3,'cliente','2026-10-12T10:00:00');
"""


class TestMigracaoDeBancoAntigo(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.mkdtemp(prefix="sac_mig_")
        self.caminho = os.path.join(self.pasta, "antigo.db")
        con = sqlite3.connect(self.caminho)
        con.executescript(BANCO_ANTIGO)
        con.commit()
        con.close()
        self._patch = mock.patch.object(db, "get_db_path", lambda: self.caminho)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        shutil.rmtree(self.pasta, ignore_errors=True)

    def test_dados_preservados(self):
        db.init_db()
        db.init_db()  # abrir de novo (todo inicio do programa) nao pode alterar nada
        notas = db.listar_notas_ativas()
        self.assertEqual([(n["nf_numero"], n["ocorrencia"], n["agendamento_data"]) for n in notas],
                         [(1, "REENTREGA", None), (2, "AGENDAMENTO", "25122030")])
        self.assertEqual([t["texto"] for t in db.listar_tratativas(notas[0]["id"])],
                         ["CONTATO FEITO", "AGUARDANDO"])      # tratativas NAO podem sumir
        self.assertEqual([t["texto"] for t in db.listar_tratativas(notas[1]["id"])], ["OUTRA"])
        historico = db.listar_historico()
        self.assertEqual([(h["nf_numero"], h["morosidade"]) for h in historico], [(3, "cliente")])
        self.assertIn("MEU TIPO", db.listar_tipos_ocorrencia())  # tipo personalizado mantido

    def test_novas_regras_valem_no_banco_migrado(self):
        db.init_db()
        db.inserir_nota(3, "BETA", "REENTREGA", "SP", "20102026")   # NF resolvida pode voltar
        with self.assertRaises(db.NotaDuplicadaError):                # pendente continua bloqueada
            db.inserir_nota(1, "ACME", "REENTREGA", "SP", "20102026")
        con = sqlite3.connect(self.caminho)
        colunas = [c[1] for c in con.execute("PRAGMA table_info(notas)")]
        con.close()
        self.assertIn("observacao", colunas)
        self.assertNotIn("lembrete_codigo", colunas)

    def test_chaves_estrangeiras_continuam_ligadas(self):
        db.init_db()
        con = db.get_connection()
        try:
            self.assertEqual(con.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()
