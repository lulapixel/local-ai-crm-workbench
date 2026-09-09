"""Testes das ferramentas de consulta do Instagram."""

from unittest.mock import MagicMock
from mcp_server.server import create_mcp_server


def test_listar_posts_instagram_tool():
    gw_mock = MagicMock()
    gw_mock.request.return_value = [
        {"id": 1, "post_url": "https://instagram.com/p/123", "num_comentarios": 15}
    ]

    mcp = create_mcp_server(gateway=gw_mock)
    func = mcp._tool_manager._tools["listar_posts_instagram"].fn
    res = func(arquivados=False)

    assert res["ok"] is True
    assert len(res["data"]["posts"]) == 1
    assert res["data"]["posts"][0]["id"] == 1


def test_obter_lead_instagram_tool():
    gw_mock = MagicMock()
    gw_mock.request.return_value = {
        "id": 42,
        "username": "joaodesign",
        "score": 90,
        "session_id": "NAO_EXPOR",
    }

    mcp = create_mcp_server(gateway=gw_mock)
    func = mcp._tool_manager._tools["obter_lead_instagram"].fn
    res = func(lead_id=42)

    assert res["ok"] is True
    assert res["data"]["lead"]["id"] == 42
    assert res["data"]["lead"]["username"] == "joaodesign"
    assert "session_id" not in res["data"]["lead"]
