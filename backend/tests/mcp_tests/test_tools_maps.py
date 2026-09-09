"""Testes das ferramentas de consulta do Maps."""

from unittest.mock import MagicMock
from mcp_server.server import create_mcp_server


def test_listar_leads_maps_tool():
    gw_mock = MagicMock()
    gw_mock.request.return_value = {
        "leads": [
            {
                "place_id": "ChIJ123",
                "nome": "Padaria Alpha",
                "score": 85,
                "secret_key": "VAZAR_NAO",
            }
        ],
        "tem_mais": False,
    }

    mcp = create_mcp_server(gateway=gw_mock)
    func = mcp._tool_manager._tools["listar_leads_maps"].fn
    res = func(limite=10)

    assert res["ok"] is True
    assert len(res["data"]["leads"]) == 1
    lead = res["data"]["leads"][0]
    assert lead["place_id"] == "ChIJ123"
    assert lead["nome"] == "Padaria Alpha"
    assert "secret_key" not in lead


def test_obter_lead_maps_tool():
    gw_mock = MagicMock()
    gw_mock.request.return_value = {
        "place_id": "ChIJ999",
        "nome": "Clínica Odonto",
        "status": "novo",
    }

    mcp = create_mcp_server(gateway=gw_mock)
    func = mcp._tool_manager._tools["obter_lead_maps"].fn
    res = func(place_id="ChIJ999")

    assert res["ok"] is True
    assert res["data"]["lead"]["place_id"] == "ChIJ999"
    assert res["data"]["lead"]["nome"] == "Clínica Odonto"
