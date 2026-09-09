"""Testes unitários e de integração para o domínio de Outreach (Pacote de Conversão).
"""

import json
import sqlite3
from copy import deepcopy
import pytest

import db
from outreach.schema import migrar_outreach, migrar_template_legacy_conversion_packs
from outreach.strategy import extrair_evidencias_e_estrategia
from outreach.service import (
    aprovar_pacote_conversao,
    arquivar_pacote_conversao,
    atualizar_pacote_manualmente,
    obter_ou_gerar_pacote,
    obter_pacote_por_place_id,
    regenerar_secoes_pacote,
)
from outreach.repository import (
    obter_por_id,
    obter_versoes_pacote,
)


@pytest.fixture
def conexao_memoria(monkeypatch, tmp_path):
    """Fixture que cria um banco SQLite em arquivo temporário com o schema completo."""
    caminho_banco = tmp_path / "test_outreach.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho_banco)

    conexao = sqlite3.connect(caminho_banco)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON;")

    import processar
    processar.preparar_banco(conexao)

    conexao.commit()
    conexao.close()

    yield caminho_banco


def _inserir_lead_teste(caminho_banco, place_id="ChIJ_123", **kwargs):
    conexao = sqlite3.connect(caminho_banco)
    conexao.execute(
        """
        INSERT INTO leads (
            place_id, nome, categoria, cidade, nota, num_avaliacoes, site_status, site_url, site_problemas, instagram_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            place_id,
            kwargs.get("nome", "Clínica Odonto Teste"),
            kwargs.get("categoria", "Dentista"),
            kwargs.get("cidade", "São Paulo"),
            kwargs.get("nota", 4.9),
            kwargs.get("num_avaliacoes", 120),
            kwargs.get("site_status", "sem_site"),
            kwargs.get("site_url", ""),
            kwargs.get("site_problemas", ""),
            kwargs.get("instagram_url", "https://instagram.com/odontoteste")
        )
    )
    conexao.commit()
    conexao.close()


def test_migracao_idempotente(conexao_memoria):
    """Garante que a migração de outreach é segura para rodar múltiplas vezes."""
    conexao = sqlite3.connect(conexao_memoria)
    migrar_outreach(conexao)
    migrar_outreach(conexao)

    colunas = [row[1] for row in conexao.execute("PRAGMA table_info(conversion_packs)").fetchall()]
    assert "place_id" in colunas
    assert "strategy_json" in colunas
    assert "status" in colunas
    assert "version" in colunas
    conexao.close()


def test_diagnostico_deterministico_sem_site(conexao_memoria):
    """Testa a regra determinística para empresa sem site próprio e boa reputação."""
    lead = {
        "nome": "Sorriso Real",
        "categoria": "Dentista",
        "cidade": "Curitiba",
        "nota": 4.9,
        "num_avaliacoes": 85,
        "site_status": "sem_site",
        "site_url": "",
        "instagram_url": "https://instagram.com/sorrisoreal"
    }
    diag = extrair_evidencias_e_estrategia(lead)
    assert diag["primaryRule"] == "sem_site"
    assert "Curitiba" in diag["evidence"][0] or "Google Maps" in diag["evidence"][0]
    assert diag["confidence"] == "high"


def test_geracao_inicial_pacote_e_lp_draft(conexao_memoria):
    """Testa a geração inicial do pacote, criando automaticamente a LP em draft e vinculando os IDs."""
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_SEM_SITE", site_status="sem_site", site_url="")

    pacote = obter_ou_gerar_pacote("ChIJ_SEM_SITE")

    assert pacote["placeId"] == "ChIJ_SEM_SITE"
    assert pacote["status"] == "draft"
    assert pacote["version"] == 1
    assert pacote["landingPageId"] is not None
    assert pacote["prototype"]["templateKey"] == "geral-conversao"

    conexao = sqlite3.connect(conexao_memoria)
    spec_json = conexao.execute(
        "SELECT current_spec_json FROM landing_pages WHERE id = ?",
        (pacote["landingPageId"],),
    ).fetchone()[0]
    conexao.close()
    spec = json.loads(spec_json)
    assert spec["palette"]["background"]
    assert "whatsappNumber" in spec["contact"]
    assert spec["hero"]["title"] == pacote["prototype"]["heroAngle"]
    assert spec["hero"]["primaryCta"] == pacote["prototype"]["primaryCta"]

    # Verifica se as mensagens possuem a estrutura esperada
    messages = pacote["messages"]
    assert "initial" in messages
    assert "afterInterest" in messages
    assert "prototypeDelivery" in messages
    assert len(messages["followups"]) == 3

    # Verifica historico de versoes
    conexao = sqlite3.connect(conexao_memoria)
    versoes = obter_versoes_pacote(conexao, pacote["id"])
    assert len(versoes) == 1
    assert versoes[0]["changeType"] == "initial_generation"
    conexao.close()


def test_reutilizacao_lp_existente(conexao_memoria):
    """Garante que se o lead já tiver uma LP, o pacote associa essa mesma LP."""
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_COM_LP")

    # Cria LP manualmente primeiro
    conexao = sqlite3.connect(conexao_memoria)
    conexao.row_factory = sqlite3.Row
    from lp.service import obter_ou_criar_landing_page
    lp_existente = obter_ou_criar_landing_page(conexao, "ChIJ_COM_LP", "clean_pro")
    conexao.close()

    pacote = obter_ou_gerar_pacote("ChIJ_COM_LP")
    assert pacote["landingPageId"] == lp_existente["id"]
    assert lp_existente["template_key"] == "geral-conversao"


def test_regeneracao_normaliza_legado_e_preserva_template_valido(conexao_memoria, monkeypatch):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_TEMPLATE_CANONICO")
    pacote_inicial = obter_ou_gerar_pacote("ChIJ_TEMPLATE_CANONICO")

    import outreach.service as service_module

    payload_legado = {
        "strategy": deepcopy(pacote_inicial["strategy"]),
        "messages": deepcopy(pacote_inicial["messages"]),
        "objections": deepcopy(pacote_inicial["objections"]),
        "prototype": deepcopy(pacote_inicial["prototype"]),
        "provider": "teste",
    }
    payload_legado["prototype"]["templateKey"] = "clean_pro"
    monkeypatch.setattr(service_module, "gerar_pacote_com_ia", lambda *args, **kwargs: payload_legado)

    pacote_canonico = obter_ou_gerar_pacote("ChIJ_TEMPLATE_CANONICO", force_regenerate=True)
    assert pacote_canonico["prototype"]["templateKey"] == "geral-conversao"

    payload_valido = deepcopy(payload_legado)
    payload_valido["prototype"]["templateKey"] = "estetica-premium"
    monkeypatch.setattr(service_module, "gerar_pacote_com_ia", lambda *args, **kwargs: payload_valido)

    pacote_valido = obter_ou_gerar_pacote("ChIJ_TEMPLATE_CANONICO", force_regenerate=True)
    assert pacote_valido["prototype"]["templateKey"] == "estetica-premium"

    conexao = sqlite3.connect(conexao_memoria)
    template_lp = conexao.execute(
        "SELECT template_key FROM landing_pages WHERE id = ?",
        (pacote_valido["landingPageId"],),
    ).fetchone()[0]
    conexao.close()
    assert template_lp == "estetica-premium"


def test_migracao_pack_clean_pro_preserva_estado_e_e_idempotente(conexao_memoria):
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_PACK_LEGADO")
    pacote = obter_ou_gerar_pacote("ChIJ_PACK_LEGADO")

    conexao = sqlite3.connect(conexao_memoria)
    prototype = deepcopy(pacote["prototype"])
    prototype["templateKey"] = "clean_pro"
    conexao.execute(
        "UPDATE conversion_packs SET prototype_json = ? WHERE id = ?",
        (json.dumps(prototype, ensure_ascii=False), pacote["id"]),
    )
    antes = conexao.execute(
        "SELECT id, place_id, landing_page_id, status, version, created_at, updated_at, approved_at "
        "FROM conversion_packs WHERE id = ?",
        (pacote["id"],),
    ).fetchone()
    versoes_antes = conexao.execute(
        "SELECT COUNT(*) FROM conversion_pack_versions WHERE conversion_pack_id = ?",
        (pacote["id"],),
    ).fetchone()[0]

    migrar_outreach(conexao)
    assert migrar_template_legacy_conversion_packs(conexao) == 0

    depois = conexao.execute(
        "SELECT id, place_id, landing_page_id, status, version, created_at, updated_at, approved_at "
        "FROM conversion_packs WHERE id = ?",
        (pacote["id"],),
    ).fetchone()
    prototype_depois = json.loads(
        conexao.execute(
            "SELECT prototype_json FROM conversion_packs WHERE id = ?", (pacote["id"],)
        ).fetchone()[0]
    )
    versoes_depois = conexao.execute(
        "SELECT COUNT(*) FROM conversion_pack_versions WHERE conversion_pack_id = ?",
        (pacote["id"],),
    ).fetchone()[0]
    conexao.close()

    assert prototype_depois["templateKey"] == "geral-conversao"
    assert depois == antes
    assert versoes_depois == versoes_antes


def test_edicao_manual_e_historico_versoes(conexao_memoria):
    """Testa a edição manual de mensagens e confirmação de incremento de versão."""
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_EDITAR")
    pacote_orig = obter_ou_gerar_pacote("ChIJ_EDITAR")

    novas_messages = dict(pacote_orig["messages"])
    novas_messages["initial"] = "Mensagem inicial customizada pelo usuário."

    pacote_editado = atualizar_pacote_manualmente(pacote_orig["id"], {"messages": novas_messages})

    assert pacote_editado["version"] == 2
    assert pacote_editado["messages"]["initial"] == "Mensagem inicial customizada pelo usuário."

    conexao = sqlite3.connect(conexao_memoria)
    versoes = obter_versoes_pacote(conexao, pacote_orig["id"])
    assert len(versoes) == 2
    assert versoes[0]["version"] == 2
    assert versoes[0]["changeType"] == "manual_edit"
    conexao.close()


def test_aprovacao_e_arquivamento(conexao_memoria):
    """Testa alterar o status do pacote para approved e archived."""
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_STATUS")
    pacote = obter_ou_gerar_pacote("ChIJ_STATUS")

    pacote_aprovado = aprovar_pacote_conversao(pacote["id"])
    assert pacote_aprovado["status"] == "approved"
    assert pacote_aprovado["approvedAt"] is not None

    pacote_arquivado = arquivar_pacote_conversao(pacote["id"])
    assert pacote_arquivado["status"] == "archived"


def test_exclusao_em_cascata(conexao_memoria):
    """Testa se a remoção do lead remove o conversion_pack correspondente em cascata."""
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_DELETAR")
    pacote = obter_ou_gerar_pacote("ChIJ_DELETAR")

    conexao = db.conectar()
    try:
        conexao.execute("DELETE FROM leads WHERE place_id = ?", ("ChIJ_DELETAR",))
        conexao.commit()

        pacote_pos = obter_por_id(conexao, pacote["id"])
        assert pacote_pos is None
    finally:
        conexao.close()


def test_rotas_rest_outreach(conexao_memoria):
    """Testa os endpoints REST do blueprint outreach."""
    _inserir_lead_teste(conexao_memoria, place_id="ChIJ_REST")

    import app as app_module
    client = app_module.app.test_client()

    # 1. POST gerar
    res = client.post("/api/leads/ChIJ_REST/conversion-pack", json={"force_regenerate": True})
    assert res.status_code == 200
    dados = res.get_json()
    pack_id = dados["id"]
    assert dados["placeId"] == "ChIJ_REST"

    # 2. GET consultar
    res_get = client.get("/api/leads/ChIJ_REST/conversion-pack")
    assert res_get.status_code == 200
    assert res_get.get_json()["id"] == pack_id

    # 3. PATCH atualizar
    res_patch = client.patch(f"/api/conversion-packs/{pack_id}", json={
        "messages": {"initial": "Texto testado via REST."}
    })
    assert res_patch.status_code == 200
    assert res_patch.get_json()["messages"]["initial"] == "Texto testado via REST."

    # 4. POST approve
    res_app = client.post(f"/api/conversion-packs/{pack_id}/approve")
    assert res_app.status_code == 200
    assert res_app.get_json()["status"] == "approved"
