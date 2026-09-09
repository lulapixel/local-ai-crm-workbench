"""Ferramentas de relatórios, funil e análises do ProspectOS."""

from typing import Any, Dict, Optional
from mcp.server.fastmcp import FastMCP
from mcp_server.errors import MCPError, format_error_response
from mcp_server.gateway import ProspectOSGateway
from mcp_server.schemas import build_success_response


def register_analytics_tools(mcp: FastMCP, gateway: ProspectOSGateway) -> None:
    """Registra ferramentas de analytics e relatórios no FastMCP."""

    @mcp.tool(
        name="obter_metricas",
        description=(
            "Retorna métricas gerais do CRM (total de leads, distribuição por status, conversão). "
            "Aceita canal: 'maps', 'instagram' ou 'combinado' (padrão). "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def obter_metricas(canal: str = "combinado") -> Dict[str, Any]:
        try:
            canal_clean = (canal or "combinado").lower().strip()
            if canal_clean == "maps":
                endpoint = "/api/metricas"
            elif canal_clean == "instagram":
                endpoint = "/api/instagram/metricas"
            elif canal_clean == "combinado":
                endpoint = "/api/metricas-combinadas"
            else:
                return format_error_response(
                    "PARAMETRO_INVALIDO", "Canal inválido. Use 'maps', 'instagram' ou 'combinado'."
                )

            resp = gateway.request("GET", endpoint)
            return build_success_response(resp, meta={"canal": canal_clean})
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao obter métricas: {str(exc)}")

    @mcp.tool(
        name="obter_funil",
        description=(
            "Retorna os estágios do funil de vendas do ProspectOS e a contagem de leads em cada etapa. "
            "Aceita canal: 'maps', 'instagram' ou 'combinado' (padrão). "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def obter_funil(canal: str = "combinado") -> Dict[str, Any]:
        try:
            canal_clean = (canal or "combinado").lower().strip()
            if canal_clean == "maps":
                endpoint = "/api/analytics/funil"
            elif canal_clean == "instagram":
                endpoint = "/api/instagram/analytics/funil"
            elif canal_clean == "combinado":
                endpoint = "/api/analytics/funil-combinado"
            else:
                return format_error_response(
                    "PARAMETRO_INVALIDO", "Canal inválido. Use 'maps', 'instagram' ou 'combinado'."
                )

            resp = gateway.request("GET", endpoint)
            return build_success_response(resp, meta={"canal": canal_clean})
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao obter funil: {str(exc)}")

    @mcp.tool(
        name="obter_desempenho_por_nicho",
        description=(
            "Retorna o desempenho de prospecção agrupado por nichos de mercado. "
            "Permite identificar nichos mais lucrativos e com maior taxa de conversão. "
            "Aceita canal: 'maps', 'instagram' ou 'combinado' (padrão). "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def obter_desempenho_por_nicho(
        canal: str = "combinado", limite: Optional[int] = None, ordenar_por: str = "total"
    ) -> Dict[str, Any]:
        try:
            canal_clean = (canal or "combinado").lower().strip()
            if canal_clean == "maps":
                endpoint = "/api/analytics/por-nicho"
            elif canal_clean == "instagram":
                endpoint = "/api/instagram/analytics/por-nicho"
            elif canal_clean == "combinado":
                endpoint = "/api/analytics/por-nicho-combinado"
            else:
                return format_error_response(
                    "PARAMETRO_INVALIDO", "Canal inválido. Use 'maps', 'instagram' ou 'combinado'."
                )

            resp = gateway.request("GET", endpoint)
            itens = resp if isinstance(resp, list) else []

            # Ordenação opcional no adaptador
            if ordenar_por == "fechados":
                itens.sort(key=lambda x: x.get("fechados", 0), reverse=True)
            elif ordenar_por == "taxa_conversao":
                itens.sort(key=lambda x: x.get("taxa_conversao", 0.0), reverse=True)
            else:
                itens.sort(key=lambda x: x.get("total", 0), reverse=True)

            if limite and limite > 0:
                itens = itens[:limite]

            return build_success_response(itens, meta={"canal": canal_clean, "ordenado_por": ordenar_por})
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao obter desempenho por nicho: {str(exc)}")

    @mcp.tool(
        name="obter_tarefas_hoje",
        description=(
            "Retorna as tarefas e follow-ups agendados prioritários para o dia de hoje. "
            "Reutiliza a lógica original do painel 'Tarefas de hoje' do ProspectOS. "
            "Operação somente leitura (Nível 0)."
        ),
    )
    def obter_tarefas_hoje() -> Dict[str, Any]:
        try:
            resp = gateway.request("GET", "/api/tarefas-hoje")
            return build_success_response(resp)
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao obter tarefas de hoje: {str(exc)}")
