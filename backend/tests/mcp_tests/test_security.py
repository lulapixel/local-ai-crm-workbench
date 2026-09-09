"""Testes de segurança e sanitização de dados do MCP."""

from mcp_server.sanitization import contains_sensitive_data, sanitize_instagram_lead, sanitize_maps_lead


def test_sanitize_maps_lead_removes_sensitive_fields():
    lead_bruto = {
        "place_id": "ChIJ_TEST",
        "nome": "Padaria Teste",
        "nota": 4.5,
        "gemini_api_key": "AIzaSy_SECRET_KEY",
        "proxy_auth": "user:pass@proxy",
    }

    sanitizado = sanitize_maps_lead(lead_bruto)
    assert "place_id" in sanitizado
    assert "nome" in sanitizado
    assert "gemini_api_key" not in sanitizado
    assert "proxy_auth" not in sanitizado
    assert contains_sensitive_data(sanitizado) is None


def test_sanitize_instagram_lead_removes_sensitive_fields():
    lead_bruto = {
        "id": 10,
        "username": "usuario_teste",
        "score": 75,
        "instagram_password": "MinhaSenha123",
        "session_cookie": "sessionid=xyz",
    }

    sanitizado = sanitize_instagram_lead(lead_bruto)
    assert "id" in sanitizado
    assert "username" in sanitizado
    assert "instagram_password" not in sanitizado
    assert "session_cookie" not in sanitizado
    assert contains_sensitive_data(sanitizado) is None


def test_contains_sensitive_data_detector():
    objeto_com_segredo = {
        "ok": True,
        "config": {
            "groq_api_key": "gsk_12345",
        },
    }
    resultado = contains_sensitive_data(objeto_com_segredo)
    assert resultado is not None
    assert "groq_api_key" in resultado
