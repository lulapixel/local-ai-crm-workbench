"""Testes do BackendLocator do MCP."""

import os
import socket
import requests
from unittest.mock import MagicMock, patch
from mcp_server.backend_locator import BackendLocator


def test_backend_locator_env_override(monkeypatch):
    monkeypatch.setenv("PROSPECTOS_API_URL", "http://127.0.0.1:8080")
    locator = BackendLocator()
    assert locator.get_base_url() == "http://127.0.0.1:8080"


def test_backend_locator_rejeita_endpoint_remoto(monkeypatch):
    monkeypatch.setenv("PROSPECTOS_API_URL", "https://example.com/api")
    locator = BackendLocator()
    assert locator.get_base_url() == "http://127.0.0.1:5000"


def test_backend_locator_rejeita_credenciais_e_query(monkeypatch):
    monkeypatch.setenv("PROSPECTOS_API_URL", "http://user:pass@127.0.0.1:8080/?x=1")
    locator = BackendLocator()
    assert locator.get_base_url() == "http://127.0.0.1:5000"


def test_backend_locator_rejeita_localhost_que_resolve_para_rede_remota(monkeypatch):
    monkeypatch.setenv("PROSPECTOS_API_URL", "http://localhost:5000")
    monkeypatch.setattr(
        "mcp_server.backend_locator.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.20", 0)),
        ],
    )
    locator = BackendLocator()
    assert locator.get_base_url() == "http://127.0.0.1:5000"


def test_backend_locator_aceita_localhost_resolvendo_apenas_loopback(monkeypatch):
    monkeypatch.setenv("PROSPECTOS_API_URL", "http://localhost:5000")
    monkeypatch.setattr(
        "mcp_server.backend_locator.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 0, 0, 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
        ],
    )
    locator = BackendLocator()
    assert locator.get_base_url() == "http://127.0.0.1:5000"


def test_backend_locator_aceita_loopback_ipv4_mapeado_em_ipv6(monkeypatch):
    monkeypatch.setenv("PROSPECTOS_API_URL", "http://localhost:5000")
    monkeypatch.setattr(
        "mcp_server.backend_locator.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::ffff:127.0.0.1", 0, 0, 0)),
        ],
    )
    locator = BackendLocator()
    assert locator.get_base_url() == "http://127.0.0.1:5000"


def test_backend_locator_preserva_hostname_local_em_https_para_manter_sni(monkeypatch):
    monkeypatch.setenv("PROSPECTOS_API_URL", "https://localhost:5443")
    monkeypatch.setattr(
        "mcp_server.backend_locator.socket.getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
        ],
    )
    locator = BackendLocator()
    assert locator.get_base_url() == "https://localhost:5443"


def test_backend_locator_porta_txt(tmp_path, monkeypatch):
    monkeypatch.delenv("PROSPECTOS_API_URL", raising=False)
    porta_file = tmp_path / "porta.txt"
    porta_file.write_text("5555", encoding="utf-8")

    with patch("paths.caminho_dados", return_value=porta_file):
        locator = BackendLocator()
        assert locator.get_base_url() == "http://127.0.0.1:5555"


def test_backend_locator_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("PROSPECTOS_API_URL", raising=False)
    porta_file = tmp_path / "inexistente.txt"

    with patch("paths.caminho_dados", return_value=porta_file):
        locator = BackendLocator()
        assert locator.get_base_url() == "http://127.0.0.1:5000"


@patch.object(requests.Session, "get")
def test_backend_locator_check_health_online(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True, "app": "ProspectOS"}
    mock_get.return_value = mock_resp

    locator = BackendLocator("http://127.0.0.1:5000")
    online, url, data = locator.check_health()
    assert online is True
    assert url == "http://127.0.0.1:5000"
    assert data["app"] == "ProspectOS"
    assert locator.session.trust_env is False
    mock_get.assert_called_once_with(
        "http://127.0.0.1:5000/api/health",
        timeout=2.0,
        allow_redirects=False,
    )


@patch.object(requests.Session, "get")
def test_backend_locator_check_health_offline(mock_get):
    mock_get.side_effect = Exception("Connection refused")

    locator = BackendLocator("http://127.0.0.1:5000")
    online, url, data = locator.check_health()
    assert online is False
    assert url == "http://127.0.0.1:5000"
    assert data is None
