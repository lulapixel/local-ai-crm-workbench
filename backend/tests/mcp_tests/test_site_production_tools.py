"""Testes do contrato mínimo ProspectOS → Sol Advisor."""

import json
from unittest.mock import MagicMock

from mcp_server.errors import MCPError
from mcp_server.server import create_mcp_server


def _tool(gateway, name):
    mcp = create_mcp_server(gateway=gateway)
    return mcp._tool_manager._tools[name].fn


def _lead(**overrides):
    result = {
        "place_id": "ChIJ123",
        "nome": "Clínica Alpha",
        "categoria": "Clínica",
        "nicho": "saúde",
        "cidade": "Recife",
        "endereco": "Rua A, 10",
        "nota": 4.8,
        "num_avaliacoes": 42,
        "telefone": "5581999999999",
        "whatsapp_link": "https://wa.me/5581999999999",
        "instagram_url": "https://instagram.com/clinicaalpha",
        "site_url": "",
        "site_status": "sem_site",
        "site_problemas": None,
        "site_checklist": None,
        "status": "respondeu",
        "score": 91,
        "observacoes": "nota manual",
    }
    result.update(overrides)
    return result


def _pack(status="approved", template_key="clean_pro"):
    return {
        "id": 7,
        "placeId": "ChIJ123",
        "landingPageId": 8,
        "status": status,
        "provider": "fallback_deterministico",
        "version": 1,
        "strategy": {
            "opportunity": "Converter reputação em agendamentos",
            "commercialAngle": "Prova social no topo",
            "confidence": "high",
        },
        "messages": {"initial": "Posso enviar uma demonstração?"},
        "objections": [],
        "prototype": {"templateKey": template_key, "heroAngle": "Atendimento local"},
    }


def _page(status="published", template_key="clean_pro"):
    return {
        "id": 8,
        "place_id": "ChIJ123",
        "slug": "clinica-alpha-recife-123",
        "template_key": template_key,
        "status": status,
        "spec": {
            "brand": {"name": "Clínica Alpha"},
            "hero": {"title": "Atendimento local", "primaryCta": "Agendar pelo WhatsApp"},
            "services": [],
            "finalCta": {"title": "Agende seu atendimento"},
        },
        "preview_url": "/demos/clinica-alpha-recife-123?preview=1",
        "public_url": "https://demo.example/clinica-alpha-recife-123",
    }


def test_contexto_reutiliza_lead_pack_e_landing_page():
    gateway = MagicMock()
    gateway.request.side_effect = [_lead(), _pack(), _page()]

    result = _tool(gateway, "obter_contexto_producao_site")("ChIJ123", "full")

    assert result["ok"] is True
    data = result["data"]
    assert data["contract_version"] == "site-opportunity/v1"
    assert data["company"]["name"] == "Clínica Alpha"
    assert data["commercial_strategy"]["commercialAngle"] == "Prova social no topo"
    assert data["conversion_pack"]["prototype"]["template_key"] == "geral-conversao"
    assert data["landing_page"]["slug"] == "clinica-alpha-recife-123"
    assert data["landing_page"]["template_key"] == "geral-conversao"
    assert data["investment"]["eligible"] is True
    assert gateway.request.call_count == 3


def test_contexto_preserva_template_valido_no_pack_e_na_landing_page():
    gateway = MagicMock()
    gateway.request.side_effect = [
        _lead(),
        _pack(template_key="estetica-premium"),
        _page(template_key="estetica-premium"),
    ]

    result = _tool(gateway, "obter_contexto_producao_site")("ChIJ123", "full")

    assert result["ok"] is True
    data = result["data"]
    assert data["conversion_pack"]["prototype"]["template_key"] == "estetica-premium"
    assert data["landing_page"]["template_key"] == "estetica-premium"


def test_contexto_full_respeita_gate_exato_de_pack_e_sinal_comercial():
    casos = [
        ("approved", "respondeu", True, set()),
        ("approved", "fechou", True, set()),
        ("draft", "respondeu", False, {"conversion_pack_not_approved"}),
        ("approved", "novo", False, {"human_sales_signal_missing"}),
        ("approved", "ignorado", False, {"human_sales_signal_missing"}),
    ]

    for pack_status, crm_status, eligible, blockers in casos:
        gateway = MagicMock()
        gateway.request.side_effect = [_lead(status=crm_status), _pack(status=pack_status), _page()]

        result = _tool(gateway, "obter_contexto_producao_site")("ChIJ123", "full")

        assert result["ok"] is True
        investment = result["data"]["investment"]
        assert investment["eligible"] is eligible
        assert set(investment["blockers"]) == blockers


def test_contexto_parcial_nao_mascara_recursos_ausentes():
    gateway = MagicMock()
    gateway.request.side_effect = [
        _lead(),
        MCPError("LEAD_NAO_ENCONTRADO", "pack ausente"),
        MCPError("LEAD_NAO_ENCONTRADO", "lp ausente"),
    ]

    result = _tool(gateway, "obter_contexto_producao_site")("ChIJ123", "demo")

    assert result["ok"] is True
    assert result["meta"]["partial"] is True
    assert result["data"]["conversion_pack"] is None
    assert "landing_page_missing" in result["data"]["investment"]["blockers"]


def test_contexto_parcial_propaga_falha_real_do_backend():
    gateway = MagicMock()
    gateway.request.side_effect = [
        _lead(),
        MCPError("LEAD_NAO_ENCONTRADO", "pack ausente"),
        MCPError("BACKEND_OFFLINE", "lp indisponível"),
    ]

    result = _tool(gateway, "obter_contexto_producao_site")("ChIJ123", "demo")

    assert result["ok"] is False
    assert result["erro"]["codigo"] == "BACKEND_OFFLINE"


def test_contexto_lead_inexistente_retorna_erro_padronizado():
    gateway = MagicMock()
    gateway.request.side_effect = MCPError("LEAD_NAO_ENCONTRADO", "lead ausente")

    result = _tool(gateway, "obter_contexto_producao_site")("inexistente", "demo")

    assert result["ok"] is False
    assert result["erro"]["codigo"] == "LEAD_NAO_ENCONTRADO"


def test_contexto_sanitiza_spec_por_allowlist_e_recursivamente():
    gateway = MagicMock()
    page = _page()
    page["spec"] = {
        "sections": {"hero": {"headline": "Atendimento local", "access_token": "nao-vazar"}},
        "brand": {"name": "Clínica Alpha", "api_key": "nao-vazar"},
        "internal_notes": "remover",
    }
    gateway.request.side_effect = [_lead(), _pack(), page]

    result = _tool(gateway, "obter_contexto_producao_site")("ChIJ123", "demo")

    assert result["ok"] is True
    spec = result["data"]["landing_page"]["spec"]
    assert spec["sections"]["hero"]["headline"] == "Atendimento local"
    assert spec["brand"]["name"] == "Clínica Alpha"
    assert "access_token" not in spec["sections"]["hero"]
    assert "api_key" not in spec["brand"]
    assert "internal_notes" not in spec


def test_registrar_resultado_preserva_notas_e_e_idempotente():
    state = {
        "observacoes": (
            "nota manual antes\n\n[PROSPECTOS_SITE_PRODUCTION]\n"
            '{"branch":"old","contract_version":"site-result/v1","preview_url":"/old",'
            '"repository":"old/repo","status":"in_progress"}\n'
            "[/PROSPECTOS_SITE_PRODUCTION]\n\nnota manual depois"
        )
    }
    gateway = MagicMock()

    def request(method, path, **kwargs):
        if method == "GET":
            return {"observacoes": state["observacoes"]}
        state["observacoes"] = kwargs["json_data"]["observacoes"]
        return {"ok": True}

    gateway.request.side_effect = request
    tool = _tool(gateway, "registrar_resultado_site")
    repository = r"jhrvo0\g<0>\alpha-$site"
    branch = r"prospectos\1-$preview"

    first = tool("ChIJ123", "preview_ready", preview_url="/demos/alpha?preview=1", repository=repository, branch=branch)
    second = tool("ChIJ123", "preview_ready", preview_url="/demos/alpha?preview=1", repository=repository, branch=branch)

    assert first["ok"] is True
    assert second["ok"] is True
    assert first["meta"]["idempotent"] is True
    assert second["meta"]["idempotent"] is True
    assert state["observacoes"].count("[PROSPECTOS_SITE_PRODUCTION]") == 1
    assert state["observacoes"].startswith("nota manual antes\n\n")
    assert state["observacoes"].endswith("\n\nnota manual depois")
    payload_text = state["observacoes"].split("[PROSPECTOS_SITE_PRODUCTION]\n", 1)[1]
    payload = json.loads(payload_text.split("\n[/PROSPECTOS_SITE_PRODUCTION]", 1)[0])
    assert payload["repository"] == repository
    assert payload["branch"] == branch


def test_registrar_resultado_valida_preview_local_e_http():
    aceitas = ["/demos/cliente-x?preview=1", "https://preview.example.com/cliente"]
    rejeitadas = [
        "/admin",
        "/tmp/site",
        "//evil.com",
        "javascript:alert(1)",
        "file:///tmp/site",
        "data:text/html,site",
        "https://user:password@example.com",
    ]

    for preview_url in aceitas:
        gateway = MagicMock()
        gateway.request.side_effect = [{"observacoes": ""}, {"ok": True}]
        result = _tool(gateway, "registrar_resultado_site")("ChIJ123", "preview_ready", preview_url=preview_url)
        assert result["ok"] is True

    for preview_url in rejeitadas:
        gateway = MagicMock()
        result = _tool(gateway, "registrar_resultado_site")("ChIJ123", "preview_ready", preview_url=preview_url)
        assert result["ok"] is False
        assert result["erro"]["codigo"] == "PARAMETRO_INVALIDO"
        gateway.request.assert_not_called()


def test_registrar_resultado_valida_preview_obrigatorio_e_estado():
    gateway = MagicMock()
    tool = _tool(gateway, "registrar_resultado_site")

    missing_preview = tool("ChIJ123", "preview_ready")
    invalid_status = tool("ChIJ123", "unknown")

    assert missing_preview["erro"]["codigo"] == "PARAMETRO_INVALIDO"
    assert invalid_status["erro"]["codigo"] == "PARAMETRO_INVALIDO"
    gateway.request.assert_not_called()


def test_registrar_resultado_propaga_erro_externo():
    gateway = MagicMock()
    gateway.request.side_effect = MCPError("BACKEND_OFFLINE", "offline")

    result = _tool(gateway, "registrar_resultado_site")("ChIJ123", "failed")

    assert result["ok"] is False
    assert result["erro"]["codigo"] == "BACKEND_OFFLINE"
