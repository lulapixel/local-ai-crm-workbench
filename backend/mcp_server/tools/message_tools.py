"""Ferramentas para geração de mensagens por IA e reanálise de sites."""

from typing import Any, Dict
from mcp.server.fastmcp import FastMCP
from mcp_server.errors import MCPError, format_error_response
from mcp_server.gateway import ProspectOSGateway
from mcp_server.schemas import build_success_response


def register_message_tools(mcp: FastMCP, gateway: ProspectOSGateway) -> None:
    """Registra ferramentas de mensagens e IA no FastMCP."""

    @mcp.tool(
        name="gerar_mensagem_maps",
        description=(
            "Gera ou recupera a mensagem de abordagem/follow-up personalizada para um lead do Google Maps. "
            "Reutiliza o cache existente se disponível. "
            "Defina 'forcar_nova=True' para obrigar a IA a gerar uma nova mensagem. "
            "Não altera o status do lead no CRM automaticamente."
        ),
    )
    def gerar_mensagem_maps(place_id: str, tipo: str = "contato", forcar_nova: bool = False) -> Dict[str, Any]:
        try:
            if not place_id or not place_id.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'place_id' é obrigatório.")

            tipo_clean = (tipo or "contato").lower().strip()
            if tipo_clean not in ("contato", "followup"):
                return format_error_response("PARAMETRO_INVALIDO", "O tipo deve ser 'contato' ou 'followup'.")

            body = {
                "tipo": tipo_clean,
                "forcar_nova": bool(forcar_nova),
            }
            # Geração de IA pode demorar até 30s se forcar_nova=True
            timeout_operacao = 45.0 if forcar_nova else 15.0
            resp = gateway.request("POST", f"/api/leads/{place_id.strip()}/gerar-mensagem", json_data=body, timeout=timeout_operacao)

            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao gerar mensagem: {str(exc)}")

    @mcp.tool(
        name="gerar_mensagem_instagram",
        description=(
            "Gera ou recupera a sugestão de DM (Direct Message) personalizada por IA para um lead do Instagram. "
            "Utiliza os dados extraídos do perfil e dos comentários. "
            "Não envia a mensagem pelo Instagram automaticamente."
        ),
    )
    def gerar_mensagem_instagram(lead_id: int, forcar_nova: bool = False) -> Dict[str, Any]:
        try:
            if not lead_id:
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'lead_id' é obrigatório.")

            body = {"forcar_nova": bool(forcar_nova)}
            timeout_operacao = 45.0 if forcar_nova else 15.0
            resp = gateway.request("POST", f"/api/instagram/leads/{lead_id}/sugestao-dm", json_data=body, timeout=timeout_operacao)

            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao gerar sugestão de DM: {str(exc)}")

    @mcp.tool(
        name="reanalisar_site_maps",
        description=(
            "Dispara a reanálise do site de um lead do Google Maps. "
            "Verifica disponibilidade HTTP, SSL, responsividade e PageSpeed. "
            "Operação externa e custosa (Nível 2): Exige 'confirmar=True'."
        ),
    )
    def reanalisar_site_maps(place_id: str, confirmar: bool = False) -> Dict[str, Any]:
        try:
            if not confirmar:
                return format_error_response(
                    "CONFIRMACAO_NECESSARIA",
                    "A reanálise de site realiza requisições externas e pode alterar a classificação do lead. "
                    "Defina 'confirmar=True' para prosseguir.",
                )

            if not place_id or not place_id.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'place_id' é obrigatório.")

            resp = gateway.request("POST", f"/api/leads/{place_id.strip()}/reanalisar-site", timeout=60.0)
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao reanalisar site: {str(exc)}")
