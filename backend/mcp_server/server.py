"""Servidor FastMCP do ProspectOS."""

import logging
from typing import Any, Dict, Optional
from mcp.server.fastmcp import FastMCP
from constantes import ESTAGIOS_FUNIL, STATUS_VALIDOS
from mcp_server.gateway import HttpProspectOSGateway, ProspectOSGateway
from mcp_server.tools.analytics_tools import register_analytics_tools
from mcp_server.tools.crm_mutation_tools import register_crm_mutation_tools
from mcp_server.tools.instagram_tools import register_instagram_tools
from mcp_server.tools.job_tools import register_job_tools
from mcp_server.tools.maps_tools import register_maps_tools
from mcp_server.tools.message_tools import register_message_tools
from mcp_server.tools.obsidian_tools import register_obsidian_tools
from mcp_server.tools.site_production_tools import register_site_production_tools
from mcp_server.tools.system_tools import register_system_tools

logger = logging.getLogger("prospectos.mcp.server")


def create_mcp_server(gateway: Optional[ProspectOSGateway] = None) -> FastMCP:
    """Instancia e configura o servidor FastMCP do ProspectOS."""
    gw = gateway or HttpProspectOSGateway()

    mcp = FastMCP(
        name="ProspectOS",
        instructions=(
            "Servidor MCP oficial do ProspectOS para prospecção B2B de clientes no Google Maps e Instagram. "
            "Fornece ferramentas de consulta de leads, análise de oportunidades por IA, controle de CRM, "
            "métricas e disparos controlados de jobs."
        ),
    )

    # Registro de todas as categorias de ferramentas
    register_system_tools(mcp, gw)
    register_maps_tools(mcp, gw)
    register_instagram_tools(mcp, gw)
    register_analytics_tools(mcp, gw)
    register_message_tools(mcp, gw)
    register_site_production_tools(mcp, gw)
    register_obsidian_tools(mcp, gw)
    register_crm_mutation_tools(mcp, gw)
    register_job_tools(mcp, gw)

    # Registro de Resources MCP
    @mcp.resource("prospectos://status")
    def resource_status() -> str:
        """Resource indicando o status operacional básico do ProspectOS."""
        try:
            health = gw.request("GET", "/api/health", timeout=3.0)
            return f"ProspectOS Status: {health.get('ok', False)} (DB: {health.get('database_ready', False)})"
        except Exception as exc:
            return f"ProspectOS Status: Offline ({str(exc)})"

    @mcp.resource("prospectos://schema/statuses")
    def resource_statuses_schema() -> str:
        """Lista de status de CRM suportados pelo ProspectOS."""
        status_finais = sorted(STATUS_VALIDOS.difference(ESTAGIOS_FUNIL))
        status_ordenados = [*ESTAGIOS_FUNIL, *status_finais]
        return "Status válidos do CRM ProspectOS:\n" + "\n".join(
            f"- {status}" for status in status_ordenados
        )

    @mcp.resource("prospectos://schema/site-statuses")
    def resource_site_statuses_schema() -> str:
        """Classificações de site válidas para leads do Google Maps."""
        return (
            "Status de site válidos:\n"
            "- sem_site (Lead sem website)\n"
            "- site_ruim (Website com falhas de SSL, mobile ou performance)\n"
            "- site_ok (Website funcional)"
        )

    return mcp
