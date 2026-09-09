"""Ferramentas de sistema do ProspectOS MCP."""

from typing import Any, Dict
from mcp.server.fastmcp import FastMCP
from mcp_server.gateway import ProspectOSGateway
from mcp_server.schemas import build_success_response
from mcp_server.errors import format_error_response, MCPError


def register_system_tools(mcp: FastMCP, gateway: ProspectOSGateway) -> None:
    """Registra as ferramentas de sistema no servidor FastMCP."""

    @mcp.tool(
        name="prospectos_status",
        description=(
            "Verifica se o backend do ProspectOS está online e operante. "
            "Informa se há jobs de scraping ou análise em andamento no Google Maps ou Instagram. "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def prospectos_status() -> Dict[str, Any]:
        try:
            health = gateway.request("GET", "/api/health", timeout=3.0)
            maps_status = gateway.request("GET", "/api/buscar/status", timeout=3.0)
            insta_status = gateway.request("GET", "/api/instagram/status", timeout=3.0)

            data = {
                "backend_online": health.get("ok", False),
                "api_version": health.get("api_version", "1"),
                "database_ready": health.get("database_ready", False),
                "maps": {
                    "em_andamento": maps_status.get("em_andamento", False)
                    if isinstance(maps_status, dict)
                    else False
                },
                "instagram": {
                    "em_andamento": insta_status.get("em_andamento", False)
                    if isinstance(insta_status, dict)
                    else False
                },
            }
            return build_success_response(data)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao verificar status: {str(exc)}")
