"""Ferramentas para consulta de leads do Google Maps."""

from typing import Any, Dict, Optional
from mcp.server.fastmcp import FastMCP
from mcp_server.errors import MCPError, format_error_response
from mcp_server.gateway import ProspectOSGateway
from mcp_server.sanitization import sanitize_maps_lead
from mcp_server.schemas import build_success_response


def register_maps_tools(mcp: FastMCP, gateway: ProspectOSGateway) -> None:
    """Registra ferramentas de consulta do Google Maps no FastMCP."""

    @mcp.tool(
        name="listar_leads_maps",
        description=(
            "Lista leads do Google Maps armazenados no CRM do ProspectOS com filtros opcionais. "
            "Não dispara uma nova busca no Google Maps e não altera os leads. "
            "Use ordenar='score' para priorizar leads com maior pontuação de oportunidade. "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def listar_leads_maps(
        status: Optional[str] = None,
        nicho: Optional[str] = None,
        nota_min: Optional[float] = None,
        busca: Optional[str] = None,
        site_status: Optional[str] = None,
        followup: Optional[str] = None,
        ordenar: Optional[str] = None,
        limite: int = 30,
        offset: int = 0,
    ) -> Dict[str, Any]:
        try:
            params: Dict[str, Any] = {
                "limit": min(max(1, limite), 100),
                "offset": max(0, offset),
            }
            if status:
                params["status"] = status
            if nicho:
                params["nicho"] = nicho
            if nota_min is not None:
                params["nota_min"] = nota_min
            if busca:
                params["busca"] = busca
            if site_status:
                params["site_status"] = site_status
            if followup:
                params["followup"] = followup
            if ordenar:
                params["ordenar"] = ordenar

            resp = gateway.request("GET", "/api/leads", params=params)
            raw_leads = resp.get("leads", []) if isinstance(resp, dict) else []
            tem_mais = resp.get("tem_mais", False) if isinstance(resp, dict) else False

            sanitized = [sanitize_maps_lead(l) for l in raw_leads]

            meta = {
                "canal": "maps",
                "limite": limite,
                "offset": offset,
                "tem_mais": tem_mais,
                "total_retornado": len(sanitized),
            }
            return build_success_response({"leads": sanitized}, meta=meta)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao listar leads do Maps: {str(exc)}")

    @mcp.tool(
        name="obter_lead_maps",
        description=(
            "Obtém o cadastro completo de um lead do Google Maps pelo seu 'place_id'. "
            "Inclui score, status do site, problemas detectados, checklist e dados de CRM. "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def obter_lead_maps(place_id: str) -> Dict[str, Any]:
        try:
            if not place_id or not place_id.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'place_id' é obrigatório.")

            resp = gateway.request("GET", f"/api/leads/{place_id.strip()}")
            sanitized = sanitize_maps_lead(resp)
            return build_success_response({"lead": sanitized})
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao obter lead: {str(exc)}")

    @mcp.tool(
        name="listar_nichos_maps",
        description=(
            "Retorna a lista de nichos de mercado disponíveis entre os leads cadastrados no Google Maps. "
            "Útil para alimentar pesquisas e filtros por nicho. Operação somente leitura (Nível 0)."
        ),
    )
    def listar_nichos_maps() -> Dict[str, Any]:
        try:
            resp = gateway.request("GET", "/api/nichos")
            nichos = resp if isinstance(resp, list) else []
            return build_success_response({"nichos": nichos})
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao listar nichos: {str(exc)}")

    @mcp.tool(
        name="obter_historico_status_maps",
        description=(
            "Retorna o histórico de alterações de status de um lead do Maps pelo 'place_id'. "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def obter_historico_status_maps(place_id: str) -> Dict[str, Any]:
        try:
            if not place_id or not place_id.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'place_id' é obrigatório.")

            resp = gateway.request("GET", f"/api/leads/{place_id.strip()}/historico")
            historico = resp if isinstance(resp, list) else []
            return build_success_response({"historico": historico})
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao obter histórico: {str(exc)}")

    @mcp.tool(
        name="listar_followups_maps",
        description=(
            "Lista os leads do Maps que possuem follow-ups pendentes ou vencidos. "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def listar_followups_maps(limite: int = 30) -> Dict[str, Any]:
        try:
            params = {"followup": "vencido", "limit": min(max(1, limite), 100)}
            resp = gateway.request("GET", "/api/leads", params=params)
            raw_leads = resp.get("leads", []) if isinstance(resp, dict) else []
            sanitized = [sanitize_maps_lead(l) for l in raw_leads]
            return build_success_response({"followups": sanitized})
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao listar followups: {str(exc)}")
