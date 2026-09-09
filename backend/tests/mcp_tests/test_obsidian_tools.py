"""Testes do exportador Obsidian exposto pelo MCP."""

from unittest.mock import MagicMock
from pathlib import Path

from mcp_server.server import create_mcp_server


def _tool(gateway, name):
    mcp = create_mcp_server(gateway=gateway)
    return mcp._tool_manager._tools[name].fn


def test_exportar_contexto_obsidian_exige_confirmacao(monkeypatch):
    gateway = MagicMock()
    monkeypatch.delenv("PROSPECTOS_OBSIDIAN_VAULT", raising=False)

    result = _tool(gateway, "exportar_contexto_obsidian")("ChIJ123", "demo")

    assert result["ok"] is False
    assert result["erro"]["codigo"] == "CONFIRMACAO_NECESSARIA"
    gateway.request.assert_not_called()


def test_exportar_contexto_obsidian_exige_vault_configurado(monkeypatch):
    gateway = MagicMock()
    monkeypatch.setenv("PROSPECTOS_OBSIDIAN_VAULT", "")

    result = _tool(gateway, "exportar_contexto_obsidian")("ChIJ123", "demo", True)

    assert result["ok"] is False
    assert result["erro"]["codigo"] == "OBSIDIAN_NAO_CONFIGURADO"
    gateway.request.assert_not_called()


def test_exportar_contexto_obsidian_busca_contexto_e_grava_nota(monkeypatch, tmp_path):
    vault = tmp_path / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / "02-Projects").mkdir()
    monkeypatch.setenv("PROSPECTOS_OBSIDIAN_VAULT", str(vault))

    gateway = MagicMock()
    gateway.request.side_effect = [
        {
            "place_id": "ChIJ123",
            "nome": "Clínica Alpha",
            "categoria": "Clínica",
            "nicho": "saúde",
            "cidade": "Recife",
            "endereco": "Rua A, 10",
            "telefone": "5581999999999",
            "site_url": "",
            "site_status": "sem_site",
            "status": "respondeu",
            "score": 91,
            "nota": 4.8,
            "num_avaliacoes": 42,
        },
        {
            "status": "approved",
            "version": 1,
            "strategy": {"commercialAngle": "Prova social"},
            "messages": {"initial": "Posso enviar uma demonstração?"},
            "objections": [],
        },
        {
            "slug": "clinica-alpha-recife-123",
            "template_key": "geral-conversao",
            "status": "published",
            "public_url": "https://demo.example/clinica-alpha-recife-123",
            "spec": {"brand": {"name": "Clínica Alpha"}},
        },
    ]

    result = _tool(gateway, "exportar_contexto_obsidian")("ChIJ123", "demo", True)

    assert result["ok"] is True
    assert result["data"]["status"] == "created"
    note = Path(result["data"]["note_path"]).read_text(encoding="utf-8")
    assert "Clínica Alpha" in note
    assert "site-opportunity/v1" in note
    assert gateway.request.call_count == 3
