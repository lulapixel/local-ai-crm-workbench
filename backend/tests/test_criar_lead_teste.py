import os
import sqlite3
from pathlib import Path

import pytest
import criar_lead_teste


@pytest.fixture
def banco_temp(tmp_path):
    caminho = tmp_path / "leads_test.db"
    conexao = sqlite3.connect(caminho)
    # Cria a estrutura de tabelas necessária para os testes do script
    conexao.execute(
        """
        CREATE TABLE leads (
            place_id TEXT PRIMARY KEY,
            nome TEXT,
            categoria TEXT,
            endereco TEXT,
            nota REAL,
            num_avaliacoes INTEGER,
            telefone TEXT,
            whatsapp_link TEXT,
            nicho TEXT,
            cidade TEXT,
            site_status TEXT,
            site_problemas TEXT,
            status TEXT,
            visto_em TEXT,
            atualizado_em TEXT
        )
        """
    )
    conexao.execute("CREATE TABLE historico_status (id INTEGER PRIMARY KEY, place_id TEXT)")
    conexao.execute("CREATE TABLE conversion_packs (id INTEGER PRIMARY KEY, place_id TEXT)")
    conexao.execute("CREATE TABLE conversion_pack_versions (id INTEGER PRIMARY KEY, conversion_pack_id INTEGER)")
    conexao.execute("CREATE TABLE outreach_sequences (id INTEGER PRIMARY KEY, place_id TEXT)")
    conexao.execute("CREATE TABLE outreach_sequence_steps (id INTEGER PRIMARY KEY, sequence_id INTEGER)")
    conexao.execute("CREATE TABLE outreach_conversations (id INTEGER PRIMARY KEY, place_id TEXT)")
    conexao.execute("CREATE TABLE outreach_interactions (id INTEGER PRIMARY KEY, conversation_id INTEGER)")
    conexao.commit()
    conexao.close()
    return caminho


class TestCriarLeadTesteScript:
    def test_normalizar_telefone(self):
        assert criar_lead_teste.normalizar_telefone("5565999998888") == "65999998888"
        assert criar_lead_teste.normalizar_telefone("(65) 99999-8888") == "65999998888"

    def test_criar_lead_teste(self, banco_temp):
        criar_lead_teste.criar_ou_atualizar(banco_temp, "65999998888", cidade="Cuiabá", auto_confirm=True)

        conexao = sqlite3.connect(banco_temp)
        conexao.row_factory = sqlite3.Row
        lead = conexao.execute("SELECT * FROM leads WHERE place_id = ?", (criar_lead_teste.PLACE_ID,)).fetchone()
        conexao.close()

        assert lead is not None
        assert lead["telefone"] == "65999998888"
        assert lead["cidade"] == "Cuiabá"

    def test_remover_lead_teste_com_registros_relacionados(self, banco_temp):
        # 1. Cria o lead de teste
        criar_lead_teste.criar_ou_atualizar(banco_temp, "65999998888", auto_confirm=True)

        # 2. Insere registros dependentes simulados nas tabelas de outreach
        conexao = sqlite3.connect(banco_temp)
        conexao.execute("INSERT INTO outreach_conversations (id, place_id) VALUES (1, ?)", (criar_lead_teste.PLACE_ID,))
        conexao.execute("INSERT INTO outreach_interactions (id, conversation_id) VALUES (10, 1)")
        conexao.execute("INSERT INTO outreach_sequences (id, place_id) VALUES (2, ?)", (criar_lead_teste.PLACE_ID,))
        conexao.execute("INSERT INTO outreach_sequence_steps (id, sequence_id) VALUES (20, 2)")
        conexao.commit()
        conexao.close()

        # 3. Executa a remoção
        criar_lead_teste.remover(banco_temp, auto_confirm=True)

        # 4. Assegura que todas as tabelas dependentes foram limpas transacionalmente
        conexao = sqlite3.connect(banco_temp)
        assert conexao.execute("SELECT COUNT(*) FROM leads WHERE place_id = ?", (criar_lead_teste.PLACE_ID,)).fetchone()[0] == 0
        assert conexao.execute("SELECT COUNT(*) FROM outreach_conversations WHERE place_id = ?", (criar_lead_teste.PLACE_ID,)).fetchone()[0] == 0
        assert conexao.execute("SELECT COUNT(*) FROM outreach_interactions WHERE conversation_id = 1").fetchone()[0] == 0
        assert conexao.execute("SELECT COUNT(*) FROM outreach_sequences WHERE place_id = ?", (criar_lead_teste.PLACE_ID,)).fetchone()[0] == 0
        assert conexao.execute("SELECT COUNT(*) FROM outreach_sequence_steps WHERE sequence_id = 2").fetchone()[0] == 0
        conexao.close()

    def test_dry_run_nao_modifica_banco(self, banco_temp):
        criar_lead_teste.criar_ou_atualizar(banco_temp, "65999998888", dry_run=True, auto_confirm=True)

        conexao = sqlite3.connect(banco_temp)
        count = conexao.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        conexao.close()

        assert count == 0
