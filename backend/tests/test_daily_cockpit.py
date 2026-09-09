"""Testes unitários e de integração para o Cockpit Diário de Prospecção (Daily Outreach Cockpit).
"""

import sqlite3
from datetime import datetime, timedelta, timezone
import pytest

import db
from outreach.daily_service import obter_cockpit_diario
from outreach.service import aprovar_pacote_conversao, obter_ou_gerar_pacote
from outreach.sequences_service import (
    iniciar_sequencia,
    marcar_etapa_enviada,
    pausar_sequencia,
    reagendar_etapa,
)


@pytest.fixture
def conexao_memoria(monkeypatch, tmp_path):
    caminho_banco = tmp_path / "test_daily_cockpit.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho_banco)

    conexao = sqlite3.connect(caminho_banco)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON;")

    import processar
    processar.preparar_banco(conexao)

    conexao.commit()
    conexao.close()

    yield caminho_banco


def _inserir_lead(caminho_banco, place_id, nome, score_nota=4.9, num_avaliacoes=100, site_status="sem_site"):
    conexao = sqlite3.connect(caminho_banco)
    conexao.execute(
        """
        INSERT INTO leads (
            place_id, nome, categoria, nicho, cidade, nota, num_avaliacoes, site_status,
            telefone, whatsapp_link, status, atualizado_em
        ) VALUES (?, ?, 'Dentista', 'Odontologia', 'Recife', ?, ?, ?, '5581999998888', 'https://wa.me/5581999998888', 'novo', '2026-07-22T12:00:00')
        """,
        (place_id, nome, score_nota, num_avaliacoes, site_status),
    )
    conexao.commit()
    conexao.close()


def test_cockpit_vazio(conexao_memoria):
    res = obter_cockpit_diario(date_str="2026-07-22")
    assert res["date"] == "2026-07-22"
    assert res["timezone"] == "America/Recife"
    assert res["counts"]["overdue"] == 0
    assert res["counts"]["ready_today"] == 0
    assert res["counts"]["new_contacts"] == 0
    assert len(res["items"]) == 0


def test_novos_contatos_aprovados_sem_sequencia(conexao_memoria):
    _inserir_lead(conexao_memoria, "ChIJ_NEW_LEAD", "Clínica Novo Contato")
    pack = obter_ou_gerar_pacote("ChIJ_NEW_LEAD")
    aprovar_pacote_conversao(pack["id"])

    res = obter_cockpit_diario(date_str="2026-07-22")
    assert res["counts"]["new_contacts"] == 1
    assert len(res["items"]) == 1
    item = res["items"][0]
    assert item["action_type"] == "new_contact"
    assert item["priority"] == "new_contacts"
    assert item["lead"]["place_id"] == "ChIJ_NEW_LEAD"


def test_etapas_atrasadas_e_prontas_hoje(conexao_memoria):
    _inserir_lead(conexao_memoria, "ChIJ_CADENCIA", "Clínica Cadência")
    pack = obter_ou_gerar_pacote("ChIJ_CADENCIA")
    aprovar_pacote_conversao(pack["id"])
    seq = iniciar_sequencia(pack["id"])
    data_referencia = datetime.fromisoformat(
        seq["steps"][0]["scheduled_for"].replace("Z", "+00:00")
    ).replace(tzinfo=None)
    data_hoje = data_referencia.date().isoformat()

    # Etapa 0 está ready hoje
    res_inicial = obter_cockpit_diario(date_str=data_hoje)
    assert res_inicial["counts"]["ready_today"] == 1

    # Reagenda etapa 0 para 2 dias atrás (faz ser atrasada)
    dt_passada = (data_referencia - timedelta(days=2)).isoformat(timespec="seconds") + "Z"
    reagendar_etapa(seq["steps"][0]["id"], dt_passada)

    res_atrasado = obter_cockpit_diario(date_str=data_hoje)
    assert res_atrasado["counts"]["overdue"] == 1
    assert res_atrasado["items"][0]["priority"] == "overdue"


def test_ordenacao_de_prioridade(conexao_memoria):
    # Lead 1: Novo contato aprovado (Prioridade 4)
    _inserir_lead(conexao_memoria, "ChIJ_NOVO", "Lead Novo", score_nota=4.5)
    p1 = obter_ou_gerar_pacote("ChIJ_NOVO")
    aprovar_pacote_conversao(p1["id"])

    # Lead 2: Follow-up atrasado (Prioridade 1)
    _inserir_lead(conexao_memoria, "ChIJ_ATRASADO", "Lead Atrasado", score_nota=4.9)
    p2 = obter_ou_gerar_pacote("ChIJ_ATRASADO")
    aprovar_pacote_conversao(p2["id"])
    seq2 = iniciar_sequencia(p2["id"])
    dt_passada = (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        - timedelta(days=2)
    ).isoformat(timespec="seconds") + "Z"
    reagendar_etapa(seq2["steps"][0]["id"], dt_passada)

    # Lead 3: Pausado (Prioridade 5)
    _inserir_lead(conexao_memoria, "ChIJ_PAUSADO", "Lead Pausado", score_nota=4.8)
    p3 = obter_ou_gerar_pacote("ChIJ_PAUSADO")
    aprovar_pacote_conversao(p3["id"])
    seq3 = iniciar_sequencia(p3["id"])
    pausar_sequencia(seq3["id"])

    res = obter_cockpit_diario(date_str="2026-07-22")
    assert len(res["items"]) == 3
    # Ordem esperada: Atrasado (1) -> Novo Contato (4) -> Pausado (5)
    assert res["items"][0]["lead"]["place_id"] == "ChIJ_ATRASADO"
    assert res["items"][1]["lead"]["place_id"] == "ChIJ_NOVO"
    assert res["items"][2]["lead"]["place_id"] == "ChIJ_PAUSADO"


def test_filtros_de_categoria_e_busca(conexao_memoria):
    _inserir_lead(conexao_memoria, "ChIJ_BUSCA1", "Estética Sorriso", score_nota=4.9)
    p1 = obter_ou_gerar_pacote("ChIJ_BUSCA1")
    aprovar_pacote_conversao(p1["id"])

    _inserir_lead(conexao_memoria, "ChIJ_BUSCA2", "Barbearia Alpha", score_nota=4.0)
    p2 = obter_ou_gerar_pacote("ChIJ_BUSCA2")
    aprovar_pacote_conversao(p2["id"])

    # Filtro por busca
    res_busca = obter_cockpit_diario(date_str="2026-07-22", search="Sorriso")
    assert len(res_busca["items"]) == 1
    assert res_busca["items"][0]["lead"]["name"] == "Estética Sorriso"

    # Filtro por min_score
    res_score = obter_cockpit_diario(date_str="2026-07-22", min_score=80)
    assert len(res_score["items"]) == 1
    assert res_score["items"][0]["lead"]["name"] == "Estética Sorriso"


def test_endpoint_rest_daily_cockpit(conexao_memoria):
    _inserir_lead(conexao_memoria, "ChIJ_REST_COCKPIT", "Lead REST Cockpit")
    p = obter_ou_gerar_pacote("ChIJ_REST_COCKPIT")
    aprovar_pacote_conversao(p["id"])

    import app as app_module
    client = app_module.app.test_client()

    res = client.get("/api/outreach/daily-cockpit?date=2026-07-22&category=all")
    assert res.status_code == 200
    dados = res.get_json()
    assert "counts" in dados
    assert "items" in dados
    assert dados["counts"]["new_contacts"] == 1
