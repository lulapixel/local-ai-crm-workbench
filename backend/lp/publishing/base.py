"""Classe abstrata base para provedores de publicação de Landing Pages.

Define a interface que todos os publishers (local, remoto, webhook, etc.)
devem implementar.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class LandingPagePublisher(ABC):
    @abstractmethod
    def is_configured(self) -> bool:
        """Indica se o provedor possui todas as configurações/credenciais necessárias."""
        pass

    @abstractmethod
    def publish(self, landing_page: Dict[str, Any], public_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Publica a Landing Page. Retorna um dicionário contendo public_id, public_url e provedor."""
        pass

    @abstractmethod
    def unpublish(self, landing_page: Dict[str, Any]) -> Dict[str, Any]:
        """Despublica a Landing Page."""
        pass

    @abstractmethod
    def update(self, landing_page: Dict[str, Any], public_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza o conteúdo publicado de uma Landing Page."""
        pass
