"""Fixtures de rede determinísticas para testes do cliente HTTP."""

import pytest

import url_security


@pytest.fixture(autouse=True)
def resolver_publico_por_padrao(request, monkeypatch):
    """Evita DNS real nos testes legados; o teste do resolvedor opta fora."""
    if request.module.__name__.endswith("test_url_security"):
        return
    monkeypatch.setattr(
        url_security,
        "resolver_enderecos_publicos",
        lambda host: ("93.184.216.34",),
    )
