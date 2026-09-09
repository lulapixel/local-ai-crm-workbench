"""Testes das ferramentas de sistema do MCP."""

from unittest.mock import MagicMock
from mcp_server.server import create_mcp_server


def test_prospectos_status_tool_success():
    gw_mock = MagicMock()
    gw_mock.request.side_effect = [
        {"ok": True, "api_version": "1", "database_ready": True},
        {"em_andamento": False},
        {"em_andamento": True},
    ]

    mcp = create_mcp_server(gateway=gw_mock)
    func = mcp._tool_manager._tools["prospectos_status"].fn
    res = func()

    assert res["ok"] is True
    assert res["data"]["backend_online"] is True
    assert res["data"]["maps"]["em_andamento"] is False
    assert res["data"]["instagram"]["em_andamento"] is True
