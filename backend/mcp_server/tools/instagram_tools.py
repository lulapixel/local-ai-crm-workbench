"""Ferramentas para consulta de posts e leads do Instagram."""

from typing import Any, Dict, Optional
from mcp.server.fastmcp import FastMCP
from mcp_server.errors import MCPError, format_error_response
from mcp_server.gateway import ProspectOSGateway
from mcp_server.sanitization import sanitize_instagram_lead
from mcp_server.schemas import build_success_response


def register_instagram_tools(mcp: FastMCP, gateway: ProspectOSGateway) -> None:
    """Registra ferramentas de consulta do Instagram no FastMCP."""

    @mcp.tool(
        name="listar_posts_instagram",
        description=(
            "Lista os posts do Instagram submetidos para análise de comentários no ProspectOS. "
            "Pode listar posts ativos ou arquivados. Operação somente leitura (Nível 0)."
        ),
    )
    def listar_posts_instagram(arquivados: bool = False) -> Dict[str, Any]:
        try:
            params = {"arquivados": "true" if arquivados else "false"}
            resp = gateway.request("GET", "/api/instagram/posts", params=params)
            posts = resp if isinstance(resp, list) else []
            return build_success_response({"posts": posts})
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao listar posts: {str(exc)}")

    @mcp.tool(
        name="listar_leads_instagram",
        description=(
            "Lista os leads capturados a partir dos comentários de um post do Instagram. "
            "Permite filtragem por status, nicho e busca por texto. Operação somente leitura (Nível 0)."
        ),
    )
    def listar_leads_instagram(
        post_id: int,
        status: Optional[str] = None,
        nicho: Optional[str] = None,
        busca: Optional[str] = None,
        limite: int = 30,
        offset: int = 0,
    ) -> Dict[str, Any]:
        try:
            if not post_id:
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'post_id' é obrigatório.")

            params: Dict[str, Any] = {
                "limit": min(max(1, limite), 100),
                "offset": max(0, offset),
            }
            if status:
                params["status"] = status
            if nicho:
                params["nicho"] = nicho
            if busca:
                params["busca"] = busca

            resp = gateway.request("GET", f"/api/instagram/posts/{post_id}/leads", params=params)
            raw_leads = resp.get("leads", []) if isinstance(resp, dict) else (resp if isinstance(resp, list) else [])
            tem_mais = resp.get("tem_mais", False) if isinstance(resp, dict) else False

            sanitized = [sanitize_instagram_lead(l) for l in raw_leads]
            meta = {
                "canal": "instagram",
                "post_id": post_id,
                "limite": limite,
                "offset": offset,
                "tem_mais": tem_mais,
            }
            return build_success_response({"leads": sanitized}, meta=meta)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao listar leads do Instagram: {str(exc)}")

    @mcp.tool(
        name="obter_lead_instagram",
        description=(
            "Obtém o cadastro completo de um lead do Instagram pelo seu identificador único 'lead_id'. "
            "Inclui biografia, métricas do perfil, nicho detectado e score. Operação somente leitura (Nível 0)."
        ),
    )
    def obter_lead_instagram(lead_id: int) -> Dict[str, Any]:
        try:
            if not lead_id:
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'lead_id' é obrigatório.")

            resp = gateway.request("GET", f"/api/instagram/leads/{lead_id}")
            sanitized = sanitize_instagram_lead(resp)
            return build_success_response({"lead": sanitized})
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao obter lead do Instagram: {str(exc)}")

    @mcp.tool(
        name="obter_historico_status_instagram",
        description=(
            "Retorna o histórico de alterações de status de um lead do Instagram pelo seu 'lead_id'. "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def obter_historico_status_instagram(lead_id: int) -> Dict[str, Any]:
        try:
            if not lead_id:
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'lead_id' é obrigatório.")

            resp = gateway.request("GET", f"/api/instagram/leads/{lead_id}/historico")
            historico = resp if isinstance(resp, list) else []
            return build_success_response({"historico": historico})
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao obter histórico do Instagram: {str(exc)}")
