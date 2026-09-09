"""Testes unitários e de integração para a Central de Abordagens (Outreach Review Queue).
"""

import json
import sqlite3
import pytest

import db
from outreach.service import (
    aprovar_pacotes_em_lote,
    gerar_pacotes_em_lote,
    obter_fila_abordagem,
    obter_ou_gerar_pacote,
    aprovar_pacote_conversao,
    arquivar_pacote_conversao,
)


@pytest.fixture
def conexao_memoria(monkeypatch, tmp_path):
    caminho_banco = tmp_path / "test_outreach_queue.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho_banco)

    conexao = sqlite3.connect(caminho_banco)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON;")

    import processar
    processar.preparar_banco(conexao)

    conexao.commit()
    conexao.close()

    yield caminho_banco


def _inserir_lead(caminho_banco, place_id, nome, **kwargs):
    conexao = sqlite3.connect(caminho_banco)
    conexao.execute(
        """
        INSERT INTO leads (
            place_id, nome, categoria, nicho, cidade, nota, num_avaliacoes, site_status, site_url,
            telefone, whatsapp_link, status, atualizado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            place_id,
            nome,
            kwargs.get("categoria", "Estética"),
            kwargs.get("nicho", "Estética"),
            kwargs.get("cidade", "Recife"),
            kwargs.get("nota", 4.8),
            kwargs.get("num_avaliacoes", 150),
            kwargs.get("site_status", "sem_site"),
            kwargs.get("site_url", ""),
            kwargs.get("telefone", "5581999999999"),
            kwargs.get("whatsapp_link", "https://wa.me/5581999999999"),
            kwargs.get("status", "novo"),
            "2026-07-22T10:00:00"
        )
    )
    conexao.commit()
    conexao.close()


def test_fila_vazia(conexao_memoria):
    res = obter_fila_abordagem(status="draft")
    assert res["items"] == []
    assert res["pagination"]["total"] == 0
    assert res["counts"]["not_generated"] == 0
    assert res["counts"]["draft"] == 0


def test_listagem_e_status_filtros(conexao_memoria):
    _inserir_lead(conexao_memoria, "lead-1", "Clínica Aurora")
    _inserir_lead(conexao_memoria, "lead-2", "Espaço Bella")
    _inserir_lead(conexao_memoria, "lead-3", "Odonto Sorriso")

    # lead-1: gera pacote (vira draft)
    obter_ou_gerar_pacote("lead-1")

    # lead-2: gera e aprova
    p2 = obter_ou_gerar_pacote("lead-2")
    aprovar_pacote_conversao(p2["id"])

    # lead-3: não gerado

    # Consulta not_generated
    q_ng = obter_fila_abordagem(status="not_generated")
    assert len(q_ng["items"]) == 1
    assert q_ng["items"][0]["lead"]["name"] == "Odonto Sorriso"

    # Consulta draft
    q_draft = obter_fila_abordagem(status="draft")
    assert len(q_draft["items"]) == 1
    assert q_draft["items"][0]["lead"]["name"] == "Clínica Aurora"

    # Consulta approved
    q_app = obter_fila_abordagem(status="approved")
    assert len(q_app["items"]) == 1
    assert q_app["items"][0]["lead"]["name"] == "Espaço Bella"

    # Verifica contadores globais na resposta
    counts = q_draft["counts"]
    assert counts["not_generated"] == 1
    assert counts["draft"] == 1
    assert counts["approved"] == 1
    assert counts["archived"] == 0


def test_filtros_nicho_cidade_score_canal(conexao_memoria):
    _inserir_lead(conexao_memoria, "l1", "Clínica Recife", nicho="Estética", cidade="Recife", nota=4.9, num_avaliacoes=200)
    _inserir_lead(conexao_memoria, "l2", "Clínica SP", nicho="Odontologia", cidade="São Paulo", nota=4.0, num_avaliacoes=10)

    # Filtro por cidade
    q_rec = obter_fila_abordagem(status="not_generated", city="Recife")
    assert len(q_rec["items"]) == 1
    assert q_rec["items"][0]["lead"]["name"] == "Clínica Recife"

    # Filtro por nicho
    q_odonto = obter_fila_abordagem(status="not_generated", niche="Odontologia")
    assert len(q_odonto["items"]) == 1
    assert q_odonto["items"][0]["lead"]["name"] == "Clínica SP"

    # Filtro por score minimo
    q_score = obter_fila_abordagem(status="not_generated", min_score=80)
    assert len(q_score["items"]) == 1
    assert q_score["items"][0]["lead"]["name"] == "Clínica Recife"


def test_geracao_em_lote(conexao_memoria):
    _inserir_lead(conexao_memoria, "l-batch-1", "Lead Lote 1")
    _inserir_lead(conexao_memoria, "l-batch-2", "Lead Lote 2")
    _inserir_lead(conexao_memoria, "l-batch-3", "Lead Lote 3")

    # Gera lote com ID inexistente (falha parcial esperada)
    res = gerar_pacotes_em_lote(["l-batch-1", "l-batch-2", "invalido-id"])
    assert res["requested"] == 3
    assert res["succeeded"] == 2
    assert res["failed"] == 1
    assert len(res["results"]) == 3

    # Teste limite maximo (11 leads)
    with pytest.raises(ValueError, match="Máximo de 10 leads por lote"):
        gerar_pacotes_em_lote([f"lead-{i}" for i in range(11)])


def test_aprovacao_em_lote_e_validacao(conexao_memoria):
    _inserir_lead(conexao_memoria, "l-app-1", "Lead App 1")
    _inserir_lead(conexao_memoria, "l-app-2", "Lead App 2")

    p1 = obter_ou_gerar_pacote("l-app-1")
    p2 = obter_ou_gerar_pacote("l-app-2")

    # Aprova p1 e p2 em lote
    res = aprovar_pacotes_em_lote([p1["id"], p2["id"]])
    assert res["requested"] == 2
    assert res["succeeded"] == 2
    assert res["failed"] == 0

    # Tenta re-aprovar pacotes já aprovados (deve falhar individualmente)
    res2 = aprovar_pacotes_em_lote([p1["id"]])
    assert res2["succeeded"] == 0
    assert res2["failed"] == 1
    assert "não pode ser aprovado" in res2["results"][0]["error"]


def test_alertas_operacionais(conexao_memoria):
    _inserir_lead(conexao_memoria, "l-sem-tel", "Empresa Sem Tel", telefone="", whatsapp_link="")
    obter_ou_gerar_pacote("l-sem-tel")

    q = obter_fila_abordagem(status="draft", search="Empresa Sem Tel")
    item = q["items"][0]
    assert "missing_whatsapp" in item["warnings"]
    assert "missing_contact_channel" in item["warnings"]
    assert "landing_page_not_published" in item["warnings"]


def test_endpoint_rest_review_queue(conexao_memoria):
    _inserir_lead(conexao_memoria, "rest-q-1", "Rest Lead 1")
    obter_ou_gerar_pacote("rest-q-1")

    import app as app_module
    client = app_module.app.test_client()

    res = client.get("/api/outreach/review-queue?status=draft&page=1&page_size=10")
    assert res.status_code == 200
    dados = res.get_json()
    assert "items" in dados
    assert "pagination" in dados
    assert "counts" in dados
    assert dados["items"][0]["lead"]["name"] == "Rest Lead 1"
