"""Ferramentas para acionamento e acompanhamento de jobs de scraping e análise (Nível 2)."""

from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from mcp_server.errors import MCPError, format_error_response
from mcp_server.gateway import ProspectOSGateway
from mcp_server.schemas import build_success_response


def register_job_tools(mcp: FastMCP, gateway: ProspectOSGateway) -> None:
    """Registra ferramentas de acionamento e consulta de jobs de background no FastMCP."""

    # --- MAPS JOBS ---

    @mcp.tool(
        name="iniciar_busca_maps",
        description=(
            "Inicia um novo job de scraping de empresas no Google Maps em segundo plano. "
            "A ação é executada de maneira assíncrona. "
            "Operação com acesso ao mundo externo (Nível 2): Exige 'confirmar=True'."
        ),
    )
    def iniciar_busca_maps(
        modo: str = "texto",
        queries: Optional[List[str]] = None,
        nichos: Optional[List[str]] = None,
        areas: Optional[List[str]] = None,
        confirmar: bool = False,
    ) -> Dict[str, Any]:
        try:
            if not confirmar:
                return format_error_response(
                    "CONFIRMACAO_NECESSARIA",
                    "Iniciar uma busca no Google Maps consome recursos locais e faz requisições externas. "
                    "Defina 'confirmar=True' para autorizar a operação.",
                )

            modo_clean = (modo or "texto").lower().strip()
            body: Dict[str, Any] = {"modo": modo_clean}

            if modo_clean == "texto":
                if not queries:
                    return format_error_response("PARAMETRO_INVALIDO", "Para modo 'texto', forneça a lista de 'queries'.")
                body["queries"] = queries
            elif modo_clean == "mapa":
                if not nichos or not areas:
                    return format_error_response(
                        "PARAMETRO_INVALIDO", "Para modo 'mapa', forneça as listas de 'nichos' e 'areas'."
                    )
                body["nichos"] = nichos
                body["areas"] = areas
            else:
                return format_error_response("PARAMETRO_INVALIDO", "Modo de busca inválido (use 'texto' ou 'mapa').")

            resp = gateway.request("POST", "/api/buscar", json_data=body)
            meta = {
                "orientacao": "Use 'consultar_status_busca_maps' para acompanhar o progresso da busca."
            }
            return build_success_response(resp, meta=meta)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao iniciar busca no Maps: {str(exc)}")

    @mcp.tool(
        name="consultar_status_busca_maps",
        description=(
            "Consulta o status do job de busca do Google Maps ativo em segundo plano. "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def consultar_status_busca_maps() -> Dict[str, Any]:
        try:
            resp = gateway.request("GET", "/api/buscar/status")
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao consultar status da busca: {str(exc)}")

    @mcp.tool(
        name="listar_historico_buscas_maps",
        description=(
            "Retorna o histórico das buscas no Google Maps realizadas anteriormente. "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def listar_historico_buscas_maps() -> Dict[str, Any]:
        try:
            resp = gateway.request("GET", "/api/buscar/historico")
            historico = resp if isinstance(resp, list) else []
            return build_success_response({"historico": historico})
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao obter histórico de buscas: {str(exc)}")

    # --- INSTAGRAM JOBS ---

    @mcp.tool(
        name="iniciar_analise_post_instagram",
        description=(
            "Inicia a análise dos comentários de um post do Instagram para extração e qualificação de leads. "
            "Utiliza a conta do Instagram configurada no ProspectOS. "
            "Operação com acesso ao mundo externo (Nível 2): Exige 'confirmar=True'."
        ),
    )
    def iniciar_analise_post_instagram(
        post_url: str, nicho_alvo: Optional[str] = None, confirmar: bool = False
    ) -> Dict[str, Any]:
        try:
            if not confirmar:
                return format_error_response(
                    "CONFIRMACAO_NECESSARIA",
                    "A análise de post acessa a rede e utiliza a sessão configurada do Instagram. "
                    "Defina 'confirmar=True' para autorizar a operação.",
                )

            if not post_url or not post_url.strip():
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'post_url' é obrigatório.")

            body: Dict[str, Any] = {"post_url": post_url.strip()}
            if nicho_alvo:
                body["nicho_alvo"] = nicho_alvo.strip()

            resp = gateway.request("POST", "/api/instagram/analisar", json_data=body)
            meta = {
                "orientacao": "Use 'consultar_status_analise_instagram' para acompanhar o progresso."
            }
            return build_success_response(resp, meta=meta)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao iniciar análise do Instagram: {str(exc)}")

    @mcp.tool(
        name="consultar_status_analise_instagram",
        description=(
            "Consulta o status do job de análise de post do Instagram em andamento. "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def consultar_status_analise_instagram() -> Dict[str, Any]:
        try:
            resp = gateway.request("GET", "/api/instagram/status")
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao consultar status do Instagram: {str(exc)}")

    @mcp.tool(
        name="retomar_analise_instagram",
        description=(
            "Retoma a análise de um post do Instagram que foi pausada ou interrompida. "
            "Operação de execução externa (Nível 2): Exige 'confirmar=True'."
        ),
    )
    def retomar_analise_instagram(post_id: int, confirmar: bool = False) -> Dict[str, Any]:
        try:
            if not confirmar:
                return format_error_response(
                    "CONFIRMACAO_NECESSARIA",
                    "Retomar uma análise no Instagram aciona novas requisições. "
                    "Defina 'confirmar=True' para autorizar a operação.",
                )

            if not post_id:
                return format_error_response("PARAMETRO_INVALIDO", "O parâmetro 'post_id' é obrigatório.")

            resp = gateway.request("POST", f"/api/instagram/posts/{post_id}/retomar", json_data={})
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao retomar análise do Instagram: {str(exc)}")
