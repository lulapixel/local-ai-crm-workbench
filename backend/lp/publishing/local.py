"""Provider local/preview para publicação de Landing Pages.

Usado em desenvolvimento ou visualização interna local.
"""

from typing import Any, Dict
from .base import LandingPagePublisher


class LocalPublisher(LandingPagePublisher):
    def is_configured(self) -> bool:
        return True

    def publish(self, landing_page: Dict[str, Any], public_payload: Dict[str, Any]) -> Dict[str, Any]:
        slug = landing_page.get("slug", "")
        return {
            "public_id": f"local-{slug}",
            "public_url": f"/demos/{slug}",
            "publish_provider": "local",
            "status": "published",
        }

    def unpublish(self, landing_page: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "public_id": None,
            "public_url": None,
            "publish_provider": "local",
            "status": "draft",
        }

    def update(self, landing_page: Dict[str, Any], public_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.publish(landing_page, public_payload)
