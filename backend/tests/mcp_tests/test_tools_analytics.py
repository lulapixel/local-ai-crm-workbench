"""Testes das ferramentas de analytics do MCP."""

from unittest.mock import MagicMock
from mcp_server.server import create_mcp_server


def test_obter_metricas_tool():
    gw_mock = MagicMock()
    gw_mock.request.return_value = {
        "total_leads": 120,
        "por_status": {"novo": 50, "fechado": 10},
    }

    mcp = create_mcp_server(gateway=gw_mock)
    func = mcp._tool_manager._tools["obter_metricas"].fn
    res = func(canal="combinado")

    assert res["ok"] is True
    assert res["data"]["total_leads"] == 120
    assert res["meta"]["canal"] == "combinado"


def test_obter_tarefas_hoje_tool():
    gw_mock = MagicMock()
    gw_mock.request.return_value = {
        "followups_hoje": [{"place_id": "123", "nome": "Empresa A"}]
    }

    mcp = create_mcp_server(gateway=gw_mock)
    func = mcp._tool_manager._tools["obter_tarefas_hoje"].fn
    res = func()

    assert res["ok"] is True
    assert len(res["data"]["followups_hoje"]) == 1
