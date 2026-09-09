"""Ferramentas de alteração controlada do CRM no MCP (Nível 1)."""

from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from mcp_server.errors import MCPError, format_error_response
from mcp_server.gateway import ProspectOSGateway
from mcp_server.schemas import build_success_response


def register_crm_mutation_tools(mcp: FastMCP, gateway: ProspectOSGateway) -> None:
    """Registra ferramentas de alteração do CRM no FastMCP."""

    # --- MAPS ---

    @mcp.tool(
        name="atualizar_status_lead_maps",
        description=(
            "Atualiza o status de um lead do Google Maps no CRM. "
            "Preserva o histórico de mudanças. Operação reversível (Nível 1)."
        ),
    )
    def atualizar_status_lead_maps(place_id: str, status: str) -> Dict[str, Any]:
        try:
            if not place_id or not place_id.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'place_id' é obrigatório.")
            if not status or not status.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'status' é obrigatório.")

            resp = gateway.request(
                "POST",
                f"/api/leads/{place_id.strip()}/status",
                json_data={"status": status.strip()},
            )
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao atualizar status: {str(exc)}")

    @mcp.tool(
        name="atualizar_observacoes_maps",
        description=(
            "Atualiza as observações/anotações de um lead do Google Maps. "
            "Substitui o campo de observações existente. Operação reversível (Nível 1)."
        ),
    )
    def atualizar_observacoes_maps(place_id: str, observacoes: str) -> Dict[str, Any]:
        try:
            if not place_id or not place_id.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'place_id' é obrigatório.")

            resp = gateway.request(
                "POST",
                f"/api/leads/{place_id.strip()}/observacoes",
                json_data={"observacoes": observacoes or ""},
            )
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao atualizar observações: {str(exc)}")

    @mcp.tool(
        name="definir_tags_maps",
        description=(
            "Define a lista de tags associadas a um lead do Google Maps. "
            "Substitui o conjunto de tags atual. Operação reversível (Nível 1)."
        ),
    )
    def definir_tags_maps(place_id: str, tags: List[str]) -> Dict[str, Any]:
        try:
            if not place_id or not place_id.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'place_id' é obrigatório.")

            tags_clean = [t.strip() for t in tags if isinstance(t, str) and t.strip()] if tags else []
            resp = gateway.request(
                "POST",
                f"/api/leads/{place_id.strip()}/tags",
                json_data={"tags": tags_clean},
            )
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao definir tags: {str(exc)}")

    @mcp.tool(
        name="agendar_followup_maps",
        description=(
            "Agenda uma data de follow-up para um lead do Maps (formato ISO YYYY-MM-DD). "
            "Passe 'data_iso=None' para remover o agendamento de follow-up. Operação reversível (Nível 1)."
        ),
    )
    def agendar_followup_maps(place_id: str, data_iso: Optional[str] = None) -> Dict[str, Any]:
        try:
            if not place_id or not place_id.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'place_id' é obrigatório.")

            resp = gateway.request(
                "POST",
                f"/api/leads/{place_id.strip()}/followup",
                json_data={"proximo_followup": data_iso.strip() if data_iso else None},
            )
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao agendar follow-up: {str(exc)}")

    @mcp.tool(
        name="marcar_followup_enviado_maps",
        description=(
            "Registra que uma mensagem de follow-up foi enviada para o lead do Maps. "
            "Incrementa o contador de follow-ups enviados. Operação reversível (Nível 1)."
        ),
    )
    def marcar_followup_enviado_maps(place_id: str) -> Dict[str, Any]:
        try:
            if not place_id or not place_id.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'place_id' é obrigatório.")

            resp = gateway.request(
                "POST",
                f"/api/leads/{place_id.strip()}/marcar-followup-enviado",
                json_data={},
            )
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao marcar follow-up enviado: {str(exc)}")

    # --- INSTAGRAM ---

    @mcp.tool(
        name="atualizar_status_lead_instagram",
        description=(
            "Atualiza o status de um lead do Instagram pelo seu 'lead_id'. "
            "Preserva o histórico de mudanças. Operação reversível (Nível 1)."
        ),
    )
    def atualizar_status_lead_instagram(lead_id: int, status: str) -> Dict[str, Any]:
        try:
            if not lead_id:
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'lead_id' é obrigatório.")
            if not status or not status.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'status' é obrigatório.")

            resp = gateway.request(
                "POST",
                f"/api/instagram/leads/{lead_id}/status",
                json_data={"status": status.strip()},
            )
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao atualizar status do Instagram: {str(exc)}")

    @mcp.tool(
        name="atualizar_observacoes_instagram",
        description=(
            "Atualiza as observações de um lead do Instagram pelo seu 'lead_id'. "
            "Substitui as anotações anteriores. Operação reversível (Nível 1)."
        ),
    )
    def atualizar_observacoes_instagram(lead_id: int, observacoes: str) -> Dict[str, Any]:
        try:
            if not lead_id:
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'lead_id' é obrigatório.")

            resp = gateway.request(
                "POST",
                f"/api/instagram/leads/{lead_id}/observacoes",
                json_data={"observacoes": observacoes or ""},
            )
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao atualizar observações do Instagram: {str(exc)}")

    @mcp.tool(
        name="definir_tags_instagram",
        description=(
            "Define as tags de um lead do Instagram pelo seu 'lead_id'. "
            "Substitui a lista de tags anterior. Operação reversível (Nível 1)."
        ),
    )
    def definir_tags_instagram(lead_id: int, tags: List[str]) -> Dict[str, Any]:
        try:
            if not lead_id:
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'lead_id' é obrigatório.")

            tags_clean = [t.strip() for t in tags if isinstance(t, str) and t.strip()] if tags else []
            resp = gateway.request(
                "POST",
                f"/api/instagram/leads/{lead_id}/tags",
                json_data={"tags": tags_clean},
            )
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao definir tags do Instagram: {str(exc)}")

    @mcp.tool(
        name="agendar_followup_instagram",
        description=(
            "Agenda uma data de follow-up para um lead do Instagram (formato ISO YYYY-MM-DD). "
            "Passe 'data_iso=None' para remover o agendamento. Operação reversível (Nível 1)."
        ),
    )
    def agendar_followup_instagram(lead_id: int, data_iso: Optional[str] = None) -> Dict[str, Any]:
        try:
            if not lead_id:
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'lead_id' é obrigatório.")

            resp = gateway.request(
                "POST",
                f"/api/instagram/leads/{lead_id}/followup",
                json_data={"proximo_followup": data_iso.strip() if data_iso else None},
            )
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao agendar follow-up do Instagram: {str(exc)}")

    @mcp.tool(
        name="marcar_followup_enviado_instagram",
        description=(
            "Registra que o envio de follow-up/DM para o lead do Instagram foi realizado no CRM. "
            "Incrementa o contador de envios. Operação reversível (Nível 1)."
        ),
    )
    def marcar_followup_enviado_instagram(lead_id: int) -> Dict[str, Any]:
        try:
            if not lead_id:
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'lead_id' é obrigatório.")

            resp = gateway.request(
                "POST",
                f"/api/instagram/leads/{lead_id}/marcar-followup-enviado",
                json_data={},
            )
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao marcar follow-up enviado no Instagram: {str(exc)}")
