"""Cliente HTTP interno para comunicação com a API local do ProspectOS."""

import logging
import threading
import time
from typing import Any, Dict, Optional
import requests
from mcp_server.backend_locator import BackendLocator
from mcp_server.errors import MCPError

logger = logging.getLogger("prospectos.mcp.api_client")
_HEALTH_CACHE_TTL_SECONDS = 1.0


class ProspectOSApiClient:
    """Cliente HTTP desacoplado que traduz chamadas das tools MCP em requisições para a API Flask."""

    def __init__(self, locator: Optional[BackendLocator] = None):
        self.locator = locator or BackendLocator()
        self.session = requests.Session()
        # O destino do cliente é estritamente loopback. Não herdar proxies,
        # netrc ou outras variáveis de ambiente evita que a chamada local seja
        # desviada por configuração ambiental fora do contrato do MCP.
        self.session.trust_env = False
        # Cada tool MCP costumava fazer um health check HTTP antes da chamada
        # real. Um burst de tools transformava isso em tráfego e latência
        # duplicados. O cache é curto, process-local e só guarda sucesso; uma
        # falha de transporte o invalida imediatamente.
        self._health_cache: Optional[tuple[float, str]] = None
        # FastMCP pode executar tools simultâneas. Serializar apenas o probe
        # evita dois health checks concorrentes; a chamada real continua fora
        # do lock e mantém o throughput normal.
        self._health_cache_lock = threading.Lock()

    def _get_base_url(self) -> str:
        with self._health_cache_lock:
            agora = time.monotonic()
            if self._health_cache and agora - self._health_cache[0] < _HEALTH_CACHE_TTL_SECONDS:
                return self._health_cache[1]
            online, base_url, _ = self.locator.check_health()
            if not online:
                self._health_cache = None
                raise MCPError(
                    codigo="BACKEND_OFFLINE",
                    mensagem="O aplicativo ProspectOS não está aberto ou respondendo. Abra o ProspectOS antes de executar esta ação.",
                    detalhes={"target_url": base_url},
                )
            # Marca o sucesso depois do probe: um health check lento não deve
            # entregar uma entrada já vencida ao próximo tool call.
            self._health_cache = (time.monotonic(), base_url)
            return base_url

    def _invalidate_health_cache(self) -> None:
        with self._health_cache_lock:
            self._health_cache = None

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
        retries: int = 0,
    ) -> Any:
        base_url = self._get_base_url()
        url = f"{base_url}{path}"
        method_upper = method.upper()

        max_attempts = 1 + (retries if method_upper == "GET" else 0)

        last_exception: Optional[Exception] = None
        for attempt in range(max_attempts):
            try:
                resp = self.session.request(
                    method=method_upper,
                    url=url,
                    params=params,
                    json=json_data,
                    timeout=timeout,
                    # O backend é local; nunca transforme uma resposta 3xx
                    # em uma saída automática para outro host. Redirects,
                    # quando necessários, precisam ser tratados por uma
                    # operação explícita e validada.
                    allow_redirects=False,
                )

                if resp.status_code == 200:
                    try:
                        return resp.json()
                    except ValueError:
                        raise MCPError(
                            codigo="BACKEND_INCOMPATIVEL",
                            mensagem="O backend retornou uma resposta em formato inválido (não JSON).",
                        )

                # Tratamento de códigos de erro específicos da API
                try:
                    err_json = resp.json()
                    msg = err_json.get("erro") or err_json.get("mensagem") or f"Erro HTTP {resp.status_code}"
                except Exception:
                    msg = f"Erro HTTP {resp.status_code}"

                if resp.status_code == 400:
                    raise MCPError(codigo="PARAMETRO_INVALIDO", mensagem=str(msg))
                elif resp.status_code == 404:
                    raise MCPError(codigo="LEAD_NAO_ENCONTRADO", mensagem=str(msg))
                elif resp.status_code == 409:
                    raise MCPError(codigo="OPERACAO_EM_ANDAMENTO", mensagem=str(msg))
                else:
                    logger.error("Erro no backend %s %s: status=%s, msg=%s", method_upper, path, resp.status_code, msg)
                    raise MCPError(
                        codigo="ERRO_INTERNO",
                        mensagem="Ocorreu um erro interno no servidor do ProspectOS ao processar a requisição.",
                    )

            except requests.Timeout:
                self._invalidate_health_cache()
                raise MCPError(
                    codigo="TIMEOUT",
                    mensagem=f"A operação na API excedeu o tempo limite de {timeout}s.",
                )
            except requests.RequestException as exc:
                self._invalidate_health_cache()
                last_exception = exc
                if attempt == max_attempts - 1:
                    logger.exception("Falha de conexão com a API ProspectOS")
                    raise MCPError(
                        codigo="BACKEND_OFFLINE",
                        mensagem="Não foi possível se comunicar com o backend do ProspectOS.",
                    )

        if last_exception:
            raise last_exception
