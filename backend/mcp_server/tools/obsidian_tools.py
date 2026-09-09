"""Ferramentas MCP para exportação explícita de contexto ao Obsidian."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP
from obsidian_sync import export_lead

from mcp_server.errors import MCPError, format_error_response
from mcp_server.gateway import ProspectOSGateway
from mcp_server.schemas import build_success_response
from mcp_server.tools.site_production_tools import (
    _build_site_context,
    _validate_level,
    _validate_place_id,
)


def register_obsidian_tools(mcp: FastMCP, gateway: ProspectOSGateway) -> None:
    """Registra o exportador unidirecional ProspectOS -> Obsidian."""

    @mcp.tool(
        name="exportar_contexto_obsidian",
        description=(
            "Exporta um contexto site-opportunity/v1 sanitizado para uma nota do vault Obsidian configurado. "
            "É uma mutação local reversível, exige confirmar=True, não altera o CRM e não publica site."
        ),
    )
    def exportar_contexto_obsidian(
        place_id: str, nivel: str = "demo", confirmar: bool = False
    ) -> Dict[str, Any]:
        if not confirmar:
            return format_error_response(
                "CONFIRMACAO_NECESSARIA",
                "Defina 'confirmar=True' para gravar a nota sanitizada no Obsidian.",
                {
                    "operation": "prospectos_to_obsidian",
                    "reversible": True,
                    "crm_mutation": False,
                },
            )

        vault_value = os.environ.get("PROSPECTOS_OBSIDIAN_VAULT", "").strip()
        if not vault_value:
            return format_error_response(
                "OBSIDIAN_NAO_CONFIGURADO",
                "Defina PROSPECTOS_OBSIDIAN_VAULT com o caminho absoluto do vault Obsidian.",
            )

        try:
            pid = _validate_place_id(place_id)
            level = _validate_level(nivel)
            context = _build_site_context(gateway, pid, level)

            result = export_lead(
                Path(vault_value),
                {"data": context},
                write=True,
            )
            if result["status"] == "conflict":
                return format_error_response(
                    "CONFLITO_OBSIDIAN",
                    "A nota de lead existente não é gerenciada pelo ProspectOS e não foi sobrescrita.",
                    {"path": result["path"], "reason": result.get("reason", "")},
                )
            return build_success_response(
                {
                    "contract_version": context["contract_version"],
                    "lead_id": result["lead_id"],
                    "note_path": result["path"],
                    "status": result["status"],
                },
                meta={
                    "idempotent": result["status"] == "unchanged",
                    "read_only": False,
                    "crm_mutation": False,
                    "vault": result["vault"],
                },
            )
        except ValueError as err:
            return format_error_response("PARAMETRO_INVALIDO", str(err))
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response(
                "OBSIDIAN_EXPORT_FAILED",
                f"Falha ao exportar contexto para o Obsidian: {str(exc)}",
            )
