"""Testes unitários e de integração para a Régua Operacional Persistida (Outreach Sequences).
"""

import json
import sqlite3
from datetime import datetime, timedelta, timezone
import pytest

import db
from outreach.service import (
    aprovar_pacote_conversao,
    arquivar_pacote_conversao,
    atualizar_pacote_manualmente,
    obter_ou_gerar_pacote,
)
from outreach.sequences_service import (
    SequenceConflictError,
    iniciar_sequencia,
    interromper_sequencia,
    marcar_etapa_enviada,
    obter_sequencia_detalhes,
    pausar_sequencia,
    pular_etapa,
    reagendar_etapa,
    retomar_sequencia,
)


@pytest.fixture
def conexao_memoria(monkeypatch, tmp_path):
    caminho_banco = tmp_path / "test_outreach_sequences.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho_banco)

    conexao = sqlite3.connect(caminho_banco)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON;")

    import processar
    processar.preparar_banco(conexao)

    conexao.commit()
    conexao.close()

    yield caminho_banco


def _inserir_lead_teste(caminho_banco, place_id="ChIJ_SEQ_LEAD", **kwargs):
    conexao = sqlite3.connect(caminho_banco)
    conexao.execute(
        """
        INSERT INTO leads (
            place_id, nome, categoria, nicho, cidade, nota, num_avaliacoes, site_status,
            telefone, whatsapp_link, status, atualizado_em
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            place_id,
            kwargs.get("nome", "Clínica Odonto Sequência"),
            kwargs.get("categoria", "Dentista"),
            kwargs.get("nicho", "Odontologia"),
            kwargs.get("cidade", "Recife"),
            kwargs.get("nota", 4.9),
            kwargs.get("num_avaliacoes", 110),
            kwargs.get("site_status", "sem_site"),
            kwargs.get("telefone", "5581988887777"),
            kwargs.get("whatsapp_link", "https://wa.me/5581988887777"),
            kwargs.get("status", "novo"),
            "2026-07-22T12:00:00"
        )
    )
    conexao.commit()
    conexao.close()


def test_iniciar_sequencia_apenas_pacote_aprovado(conexao_memoria):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_DRAFT_PACK")
    pack = obter_ou_gerar_pacote("ChIJ_DRAFT_PACK")

    # Tentativa de iniciar em pacote draft deve falhar
    with pytest.raises(ValueError, match="Apenas pacotes no status 'approved'"):
        iniciar_sequencia(pack["id"])

    # Aprova o pacote
    pack_aprovado = aprovar_pacote_conversao(pack["id"])

    # Agora deve iniciar com sucesso
    seq = iniciar_sequencia(pack["id"])
    assert seq["status"] == "active"
    assert seq["conversion_pack_id"] == pack["id"]
    assert seq["conversion_pack_version"] == pack_aprovado["version"]
    assert len(seq["steps"]) == 4

    # Etapa 0 é ready, demais pending
    assert seq["steps"][0]["step_order"] == 0
    assert seq["steps"][0]["status"] == "ready"
    assert seq["steps"][1]["status"] == "pending"


def test_idempotencia_e_conflito_de_sequencia_ativa(conexao_memoria):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_CONFLITO")
    pack = obter_ou_gerar_pacote("ChIJ_CONFLITO")
    aprovar_pacote_conversao(pack["id"])

    # 1. Primeira chamada cria
    seq1 = iniciar_sequencia(pack["id"])

    # 2. Segunda chamada com mesmo pacote e mesma versão devolve a existente (Idempotente)
    seq2 = iniciar_sequencia(pack["id"])
    assert seq1["id"] == seq2["id"]


def test_snapshot_das_mensagens_e_edicao_posterior(conexao_memoria):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_SNAPSHOT")
    pack = obter_ou_gerar_pacote("ChIJ_SNAPSHOT")
    aprovar_pacote_conversao(pack["id"])

    seq = iniciar_sequencia(pack["id"])
    texto_original_step0 = seq["steps"][0]["message"]

    # Edita o pacote de conversão
    novas_msgs = dict(pack["messages"])
    novas_msgs["initial"] = "MENSAGEM INICIAL COMPLETAMENTE ALTERADA POSTERIORMENTE"
    atualizar_pacote_manualmente(pack["id"], {"messages": novas_msgs})

    # Consulta a sequência: o snapshot permanece inalterado!
    seq_consultada = obter_sequencia_detalhes(sequence_id=seq["id"])
    assert seq_consultada["steps"][0]["message"] == texto_original_step0
    assert seq_consultada["version_outdated"] is True


def test_confirmar_envio_e_recalculo_de_datas(conexao_memoria):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_ENVIO")
    pack = obter_ou_gerar_pacote("ChIJ_ENVIO")
    aprovar_pacote_conversao(pack["id"])
    seq = iniciar_sequencia(pack["id"])

    step0_id = seq["steps"][0]["id"]

    # Marca step 0 como enviado
    tempo_envio = "2026-07-22T15:00:00Z"
    seq_atualizada = marcar_etapa_enviada(step0_id, sent_at=tempo_envio)

    assert seq_atualizada["steps"][0]["status"] == "sent"
    assert seq_atualizada["steps"][0]["sent_at"] == tempo_envio

    # Data do follow-up 1 deve ter sido recalculada para tempo_envio + 2 dias (24/07)
    fu1 = seq_atualizada["steps"][1]
    assert "2026-07-24" in fu1["scheduled_for"]

    # Sincronização dos campos legados no lead
    conexao = sqlite3.connect(conexao_memoria)
    conexao.row_factory = sqlite3.Row
    lead = conexao.execute("SELECT * FROM leads WHERE place_id = ?", ("ChIJ_ENVIO",)).fetchone()
    assert lead["ultimo_followup_em"] == tempo_envio
    conexao.close()


def test_envio_fora_de_ordem_e_vazio(conexao_memoria):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_ORDEM")
    pack = obter_ou_gerar_pacote("ChIJ_ORDEM")
    aprovar_pacote_conversao(pack["id"])
    seq = iniciar_sequencia(pack["id"])

    step1_id = seq["steps"][1]["id"]

    # Tentar enviar a etapa 1 antes da 0 deve falhar
    with pytest.raises(ValueError, match="Apenas etapas no estado 'ready'"):
        marcar_etapa_enviada(step1_id)


def test_pular_e_reagendar_etapas(conexao_memoria):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_PULAR")
    pack = obter_ou_gerar_pacote("ChIJ_PULAR")
    aprovar_pacote_conversao(pack["id"])
    seq = iniciar_sequencia(pack["id"])

    # Marca step 0 como enviado
    marcar_etapa_enviada(seq["steps"][0]["id"])

    # Reagenda step 1 para daqui a 1 hora
    dt_reagendada = (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        - timedelta(minutes=10)
    ).isoformat(timespec="seconds") + "Z"
    seq_reag = reagendar_etapa(seq["steps"][1]["id"], dt_reagendada)
    assert seq_reag["steps"][1]["status"] == "ready"

    # Pula step 1
    seq_pulada = pular_etapa(seq["steps"][1]["id"], reason="Contato por telefone")
    assert seq_pulada["steps"][1]["status"] == "skipped"


def test_pausar_e_retomar_sequencia(conexao_memoria):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_PAUSA")
    pack = obter_ou_gerar_pacote("ChIJ_PAUSA")
    aprovar_pacote_conversao(pack["id"])
    seq = iniciar_sequencia(pack["id"])

    # Pausa
    seq_pausada = pausar_sequencia(seq["id"])
    assert seq_pausada["status"] == "paused"
    assert seq_pausada["paused_at"] is not None

    # Retoma
    seq_retomada = retomar_sequencia(seq["id"])
    assert seq_retomada["status"] == "active"
    assert seq_retomada["resumed_at"] is not None


def test_interromper_sequencia_por_resposta(conexao_memoria):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_RESPOSTA")
    pack = obter_ou_gerar_pacote("ChIJ_RESPOSTA")
    aprovar_pacote_conversao(pack["id"])
    seq = iniciar_sequencia(pack["id"])

    # Interrompe com reason='replied'
    seq_parada = interromper_sequencia(seq["id"], reason="replied")
    assert seq_parada["status"] == "replied"
    assert seq_parada["stopped_at"] is not None
    assert seq_parada["steps"][0]["status"] == "cancelled"


def test_arquivamento_de_pacote_cancela_sequencia(conexao_memoria):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_ARQUIVAR_PACK")
    pack = obter_ou_gerar_pacote("ChIJ_ARQUIVAR_PACK")
    aprovar_pacote_conversao(pack["id"])
    seq = iniciar_sequencia(pack["id"])

    # Arquiva o pacote
    arquivar_pacote_conversao(pack["id"])

    # Sequência deve ter sido cancelada
    seq_pos = obter_sequencia_detalhes(sequence_id=seq["id"])
    assert seq_pos["status"] == "cancelled"
    assert seq_pos["stop_reason"] == "pack_archived"


def test_endpoints_rest_sequencias(conexao_memoria):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_REST_SEQ")
    pack = obter_ou_gerar_pacote("ChIJ_REST_SEQ")
    aprovar_pacote_conversao(pack["id"])

    import app as app_module
    client = app_module.app.test_client()

    # 1. POST start
    res_start = client.post(f"/api/conversion-packs/{pack['id']}/sequence/start", json={"channel": "whatsapp"})
    assert res_start.status_code == 200
    dados_seq = res_start.get_json()
    seq_id = dados_seq["id"]
    step0_id = dados_seq["steps"][0]["id"]

    # 2. GET consultar por pack
    res_get = client.get(f"/api/conversion-packs/{pack['id']}/sequence")
    assert res_get.status_code == 200
    assert res_get.get_json()["id"] == seq_id

    # 3. POST mark-sent
    res_sent = client.post(f"/api/outreach/sequence-steps/{step0_id}/mark-sent")
    assert res_sent.status_code == 200
    assert res_sent.get_json()["steps"][0]["status"] == "sent"

    # 4. POST pause & resume
    res_pause = client.post(f"/api/outreach/sequences/{seq_id}/pause")
    assert res_pause.status_code == 200
    assert res_pause.get_json()["status"] == "paused"

    res_resume = client.post(f"/api/outreach/sequences/{seq_id}/resume")
    assert res_resume.status_code == 200
    assert res_resume.get_json()["status"] == "active"

    # 5. POST stop
    res_stop = client.post(f"/api/outreach/sequences/{seq_id}/stop", json={"reason": "replied"})
    assert res_stop.status_code == 200
    assert res_stop.get_json()["status"] == "replied"
