"""Testes do ProspectOSApiClient."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import MagicMock, patch
import pytest
import requests
from mcp_server.api_client import ProspectOSApiClient
from mcp_server.errors import MCPError


def test_api_client_backend_offline():
    locator_mock = MagicMock()
    locator_mock.check_health.return_value = (False, "http://127.0.0.1:5000", None)

    client = ProspectOSApiClient(locator=locator_mock)
    with pytest.raises(MCPError) as exc_info:
        client.request("GET", "/api/health")

    assert exc_info.value.codigo == "BACKEND_OFFLINE"


@patch.object(requests.Session, "request")
def test_api_client_http_404_error(mock_request):
    locator_mock = MagicMock()
    locator_mock.check_health.return_value = (True, "http://127.0.0.1:5000", {"ok": True})

    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.json.return_value = {"erro": "Lead não encontrado"}
    mock_request.return_value = mock_resp

    client = ProspectOSApiClient(locator=locator_mock)
    with pytest.raises(MCPError) as exc_info:
        client.request("GET", "/api/leads/invalido")

    assert exc_info.value.codigo == "LEAD_NAO_ENCONTRADO"
    assert "Lead não encontrado" in exc_info.value.mensagem


@patch.object(requests.Session, "request")
def test_api_client_http_400_error(mock_request):
    locator_mock = MagicMock()
    locator_mock.check_health.return_value = (True, "http://127.0.0.1:5000", {"ok": True})

    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"erro": "Status inválido: teste"}
    mock_request.return_value = mock_resp

    client = ProspectOSApiClient(locator=locator_mock)
    with pytest.raises(MCPError) as exc_info:
        client.request("POST", "/api/leads/123/status", json_data={"status": "invalido"})

    assert exc_info.value.codigo == "PARAMETRO_INVALIDO"


@patch.object(requests.Session, "request")
def test_api_client_nao_segue_redirects_do_backend(mock_request):
    """Uma resposta local 3xx não pode provocar egress automático."""
    locator_mock = MagicMock()
    locator_mock.check_health.return_value = (True, "http://127.0.0.1:5000", {"ok": True})

    mock_resp = MagicMock()
    mock_resp.status_code = 302
    mock_resp.json.return_value = {"erro": "redirect não esperado"}
    mock_request.return_value = mock_resp

    client = ProspectOSApiClient(locator=locator_mock)
    with pytest.raises(MCPError) as exc_info:
        client.request("GET", "/api/health")

    assert exc_info.value.codigo == "ERRO_INTERNO"
    assert mock_request.call_args.kwargs["allow_redirects"] is False


def test_api_client_nao_herda_proxy_ambiental():
    """O cliente loopback não deve confiar em proxy/netrc do ambiente."""
    client = ProspectOSApiClient(locator=MagicMock())
    assert client.session.trust_env is False


@patch.object(requests.Session, "request")
def test_api_client_reutiliza_health_check_em_burst_curto(mock_request):
    """Tools consecutivas não devem duplicar o probe HTTP do backend."""
    locator_mock = MagicMock()
    locator_mock.check_health.return_value = (True, "http://127.0.0.1:5000", {"ok": True})

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True}
    mock_request.return_value = mock_resp

    client = ProspectOSApiClient(locator=locator_mock)
    assert client.request("GET", "/api/health") == {"ok": True}
    assert client.request("GET", "/api/health") == {"ok": True}

    assert locator_mock.check_health.call_count == 1
    assert mock_request.call_count == 2


@patch.object(requests.Session, "request")
def test_api_client_invalida_health_cache_apos_falha_de_transporte(mock_request):
    locator_mock = MagicMock()
    locator_mock.check_health.return_value = (True, "http://127.0.0.1:5000", {"ok": True})
    mock_request.side_effect = requests.ConnectionError("backend caiu")

    client = ProspectOSApiClient(locator=locator_mock)
    with pytest.raises(MCPError):
        client.request("GET", "/api/health")
    with pytest.raises(MCPError):
        client.request("GET", "/api/health")

    # A segunda chamada precisa reprobar o backend, não reutilizar a URL cacheada.
    assert locator_mock.check_health.call_count == 2


@patch.object(requests.Session, "request")
def test_api_client_marca_cache_depois_de_health_lento(mock_request):
    """Um probe lento deve iniciar o TTL depois de terminar, não antes."""
    locator_mock = MagicMock()
    clock = [0.0]

    def slow_health():
        clock[0] = 2.0
        return True, "http://127.0.0.1:5000", {"ok": True}

    locator_mock.check_health.side_effect = slow_health
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True}
    mock_request.return_value = mock_resp

    client = ProspectOSApiClient(locator=locator_mock)
    with patch("mcp_server.api_client.time.monotonic", side_effect=lambda: clock[0]):
        assert client.request("GET", "/api/health") == {"ok": True}
        assert client.request("GET", "/api/health") == {"ok": True}

    assert locator_mock.check_health.call_count == 1


@patch.object(requests.Session, "request")
def test_api_client_deduplica_health_probe_concorrente(mock_request):
    """Calls MCP simultâneas compartilham o mesmo probe em voo."""
    locator_mock = MagicMock()
    probe_started = Event()
    release_probe = Event()

    def slow_health():
        probe_started.set()
        assert release_probe.wait(timeout=2)
        return True, "http://127.0.0.1:5000", {"ok": True}

    locator_mock.check_health.side_effect = slow_health
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"ok": True}
    mock_request.return_value = mock_resp

    client = ProspectOSApiClient(locator=locator_mock)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(client.request, "GET", "/api/health")
        assert probe_started.wait(timeout=2)
        second = executor.submit(client.request, "GET", "/api/health")
        release_probe.set()
        assert first.result(timeout=2) == {"ok": True}
        assert second.result(timeout=2) == {"ok": True}

    assert locator_mock.check_health.call_count == 1
    assert mock_request.call_count == 2
