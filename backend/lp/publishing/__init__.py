"""Módulo de provedores de publicação de Landing Pages.
"""

from typing import Any, Dict, Optional
from .base import LandingPagePublisher
from .local import LocalPublisher
from .remote import (
    RemotePublisher,
    RemotePublishingUnavailableError,
    obter_config_publicacao,
)


def get_publisher(provider_name: Optional[str] = None) -> LandingPagePublisher:
    """Retorna a instância do publisher configurado.

    Se provider_name for informado ('remote' ou 'local'), usa o especificado.
    O provider local é sempre o padrão até existir um adapter remoto real que
    confirme deploy/rollback. `provider_name="remote"` permite que uma futura
    integração seja testada explicitamente, mas o scaffold atual falha fechado.
    """
    if provider_name == "local":
        return LocalPublisher()
    elif provider_name == "remote":
        return RemotePublisher()

    # Não selecionar o scaffold remoto apenas porque uma URL foi preenchida:
    # isso antes permitia registrar "published" sem qualquer chamada externa.
    return LocalPublisher()


def sanitizar_payload_publico(lp_dict: Dict[str, Any], lead_dict: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extrai estritamente apenas o conteúdo público da Landing Page.

    Garante que dados sensíveis/internos (score, observações, histórico, tags,
    dados do lead não pertencentes à LP) NUNCA sejam vazados no payload público.
    """
    spec = lp_dict.get("spec", {})
    if not isinstance(spec, dict):
        spec = {}

    return {
        "slug": lp_dict.get("slug"),
        "template_key": lp_dict.get("template_key"),
        "schema_version": lp_dict.get("schema_version", 1),
        "spec": {
            "brand": spec.get("brand", {}),
            "hero": spec.get("hero", {}),
            "services": spec.get("services", []),
            "testimonials": spec.get("testimonials", []),
            "faqs": spec.get("faqs", []),
            "budget": spec.get("budget", {}),
            "finalCta": spec.get("finalCta", {}),
            "contact": spec.get("contact", {}),
            "palette": spec.get("palette", {}),
            "seo": spec.get("seo", {}),
        },
    }


__all__ = [
    "LandingPagePublisher",
    "LocalPublisher",
    "RemotePublisher",
    "RemotePublishingUnavailableError",
    "get_publisher",
    "sanitizar_payload_publico",
    "obter_config_publicacao",
]
