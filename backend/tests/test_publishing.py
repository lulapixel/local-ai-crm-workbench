"""Contratos dos providers de publicação de Landing Pages."""

import pytest

from lp.publishing import (
    LocalPublisher,
    RemotePublisher,
    RemotePublishingUnavailableError,
    get_publisher,
)


def _landing_page():
    return {"slug": "clinica-alpha"}


def test_publisher_local_continua_padrao_mesmo_com_configuracao_remota(monkeypatch):
    """URL configurada não pode transformar um scaffold em deploy falso."""
    monkeypatch.setenv("LP_PUBLIC_BASE_URL", "https://lp.example")
    monkeypatch.setenv("LP_PUBLISH_API_URL", "https://api.example/v1/publish")
    monkeypatch.setenv("LP_PUBLISH_API_KEY", "synthetic-test-key")

    publisher = get_publisher()

    assert isinstance(publisher, LocalPublisher)
    assert publisher.is_configured() is True


def test_publisher_remoto_falha_fechado_sem_adapter_real():
    publisher = RemotePublisher()

    assert publisher.is_configured() is False
    with pytest.raises(RemotePublishingUnavailableError, match="ainda não está implementada"):
        publisher.publish(_landing_page(), {"slug": "clinica-alpha"})
    with pytest.raises(RemotePublishingUnavailableError, match="ainda não está implementada"):
        publisher.unpublish(_landing_page())


def test_publisher_remoto_nao_finge_update():
    with pytest.raises(RemotePublishingUnavailableError, match="ainda não está implementada"):
        RemotePublisher().update(_landing_page(), {"slug": "clinica-alpha"})
