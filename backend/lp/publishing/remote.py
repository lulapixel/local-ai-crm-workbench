"""Scaffold de publicação remota/externa para Landing Pages.

As configurações abaixo são reconhecidas para diagnóstico, mas ainda não
existe um contrato de API remoto implementado neste checkout. O provider,
portanto, falha fechado e nunca marca uma LP como publicada sem confirmar um
deploy real. O publisher local continua sendo o caminho padrão até existir uma
integração HTTP autenticada, com verify/rollback e teste E2E.
"""

import os
from typing import Any, Dict, Optional
import db
from .base import LandingPagePublisher


class RemotePublishingUnavailableError(ValueError):
    """Publicação remota não pode alegar sucesso sem um adapter real."""


REMOTE_PUBLISHING_IMPLEMENTED = False


def obter_config_publicacao(chave: str) -> Optional[str]:
    """Obtém configuração da publicação via db.obter_config ou variáveis de ambiente."""
    valor_db = db.obter_config(chave)
    if valor_db:
        return str(valor_db).strip()
    env_name = chave.upper()
    valor_env = os.environ.get(env_name)
    if valor_env:
        return valor_env.strip()
    return None


class RemotePublisher(LandingPagePublisher):
    def is_configured(self) -> bool:
        # URLs/chaves presentes não bastam: este checkout ainda não tem um
        # adapter que faça a chamada remota e confirme o resultado.
        if not REMOTE_PUBLISHING_IMPLEMENTED:
            return False
        base_url = obter_config_publicacao("lp_public_base_url") or os.environ.get("LP_PUBLIC_BASE_URL")
        api_url = obter_config_publicacao("lp_publish_api_url") or os.environ.get("LP_PUBLISH_API_URL")
        api_key = obter_config_publicacao("lp_publish_api_key") or os.environ.get("LP_PUBLISH_API_KEY")
        return bool((base_url or api_url) and api_key)

    @staticmethod
    def _indisponivel() -> None:
        raise RemotePublishingUnavailableError(
            "Publicação remota ainda não está implementada; use o publisher local "
            "ou configure um adapter remoto com verify/rollback e teste E2E."
        )

    def _obter_base_url(self) -> str:
        base_url = obter_config_publicacao("lp_public_base_url") or os.environ.get("LP_PUBLIC_BASE_URL") or ""
        return base_url.rstrip("/")

    def publish(self, landing_page: Dict[str, Any], public_payload: Dict[str, Any]) -> Dict[str, Any]:
        self._indisponivel()

    def unpublish(self, landing_page: Dict[str, Any]) -> Dict[str, Any]:
        self._indisponivel()

    def update(self, landing_page: Dict[str, Any], public_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.publish(landing_page, public_payload)
