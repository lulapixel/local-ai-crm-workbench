"""Camada Gateway de abstração para operações do ProspectOS."""

from typing import Any, Dict, Optional
from mcp_server.api_client import ProspectOSApiClient


class ProspectOSGateway:
    """Abstração base para operações do ProspectOS."""

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> Any:
        raise NotImplementedError


class HttpProspectOSGateway(ProspectOSGateway):
    """Implementação HTTP do Gateway sobre a API Flask local."""

    def __init__(self, client: Optional[ProspectOSApiClient] = None):
        self.client = client or ProspectOSApiClient()

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: float = 10.0,
    ) -> Any:
        return self.client.request(
            method=method,
            path=path,
            params=params,
            json_data=json_data,
            timeout=timeout,
        )
