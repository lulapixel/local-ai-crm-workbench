"""Testes de integração básica do servidor FastMCP."""

from unittest.mock import MagicMock
from constantes import STATUS_VALIDOS
from mcp_server.server import create_mcp_server


def test_mcp_server_tools_registration():
    gw_mock = MagicMock()
    mcp = create_mcp_server(gateway=gw_mock)

    tools_names = set(mcp._tool_manager._tools.keys())

    assert "prospectos_status" in tools_names
    assert "listar_leads_maps" in tools_names
    assert "obter_lead_maps" in tools_names
    assert "listar_posts_instagram" in tools_names
    assert "obter_lead_instagram" in tools_names
    assert "obter_metricas" in tools_names
    assert "gerar_mensagem_maps" in tools_names
    assert "atualizar_status_lead_maps" in tools_names
    assert "iniciar_busca_maps" in tools_names
    assert "obter_contexto_producao_site" in tools_names
    assert "registrar_resultado_site" in tools_names
    assert "exportar_contexto_obsidian" in tools_names


def test_mcp_server_resources_registration():
    gw_mock = MagicMock()
    gw_mock.request.return_value = {"ok": True, "database_ready": True}

    mcp = create_mcp_server(gateway=gw_mock)
    resources = set(mcp._resource_manager._resources.keys())

    assert "prospectos://status" in resources
    assert "prospectos://schema/statuses" in resources
    assert "prospectos://schema/site-statuses" in resources


def test_mcp_status_resource_matches_domain_statuses():
    mcp = create_mcp_server(gateway=MagicMock())
    resource = mcp._resource_manager._resources["prospectos://schema/statuses"]
    schema = resource.fn()
    announced = {
        line.removeprefix("- ")
        for line in schema.splitlines()
        if line.startswith("- ")
    }

    assert announced == STATUS_VALIDOS
