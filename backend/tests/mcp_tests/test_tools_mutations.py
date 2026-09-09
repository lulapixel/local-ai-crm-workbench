"""Testes das ferramentas de mutação do CRM e jobs com confirmação."""

from unittest.mock import MagicMock
from mcp_server.server import create_mcp_server


def test_atualizar_status_lead_maps_tool():
    gw_mock = MagicMock()
    gw_mock.request.return_value = {"ok": True, "novo_status": "contatado"}

    mcp = create_mcp_server(gateway=gw_mock)
    func = mcp._tool_manager._tools["atualizar_status_lead_maps"].fn
    res = func(place_id="ChIJ123", status="contatado")

    assert res["ok"] is True
    assert res["data"]["novo_status"] == "contatado"


def test_iniciar_busca_maps_sem_confirmacao():
    gw_mock = MagicMock()

    mcp = create_mcp_server(gateway=gw_mock)
    func = mcp._tool_manager._tools["iniciar_busca_maps"].fn
    res = func(modo="texto", queries=["Restaurantes em SP"], confirmar=False)

    assert res["ok"] is False
    assert res["erro"]["codigo"] == "CONFIRMACAO_NECESSARIA"


def test_iniciar_busca_maps_com_confirmacao():
    gw_mock = MagicMock()
    gw_mock.request.return_value = {"job_id": "job_123", "em_andamento": True}

    mcp = create_mcp_server(gateway=gw_mock)
    func = mcp._tool_manager._tools["iniciar_busca_maps"].fn
    res = func(modo="texto", queries=["Restaurantes em SP"], confirmar=True)

    assert res["ok"] is True
    assert res["data"]["job_id"] == "job_123"
