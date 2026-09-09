"""Contrato MCP mínimo entre o CRM ProspectOS e a produção de sites.

O ProspectOS continua dono do contexto comercial. O Sol Advisor continua dono
da execução do site. Estas ferramentas apenas compõem o contexto já existente
e registram o resultado no CRM sem criar uma segunda fila ou banco.
"""

import json
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP

from lp.template_catalog import normalizar_template_key
from mcp_server.errors import MCPError, format_error_response
from mcp_server.gateway import ProspectOSGateway
from mcp_server.sanitization import sanitize_maps_lead
from mcp_server.schemas import build_success_response


CONTRACT_VERSION = "site-opportunity/v1"
RESULT_VERSION = "site-result/v1"
SITE_RESULT_STATUSES = {
    "planned",
    "in_progress",
    "preview_ready",
    "reviewed",
    "deployed",
    "failed",
    "blocked",
}
PRODUCTION_LEVELS = {"demo", "full"}
RESULT_BLOCK_START = "[PROSPECTOS_SITE_PRODUCTION]"
RESULT_BLOCK_END = "[/PROSPECTOS_SITE_PRODUCTION]"
MAX_RESULT_FIELD_LENGTH = 500
MAX_OBSERVATIONS_LENGTH = 5000

# O spec real possui estes campos no topo. Tudo fora desta allowlist é interno
# ao ProspectOS e não faz parte do handoff comercial para produção.
LP_SPEC_ALLOWLIST = {
    "schema_version",
    "slug",
    "sections",
    "brand",
    "seo",
    "palette",
    "contact",
    "hero",
    "trust",
    "services",
    "testimonials",
    "faqs",
    "budget",
    "finalCta",
}
SENSITIVE_KEY_PARTS = {
    "api_key",
    "authorization",
    "credential",
    "password",
    "senha",
    "cookie",
    "session",
    "token",
    "secret",
    "proxy",
    "keyring",
    "gemini",
    "groq",
    "nvidia",
    "places",
    "pagespeed",
}


def _validate_place_id(place_id: str) -> str:
    if not isinstance(place_id, str) or not place_id.strip():
        raise ValueError("O parâmetro 'place_id' é obrigatório.")
    value = place_id.strip()
    if len(value) > 200 or any(char in value for char in "/?#\\\r\n"):
        raise ValueError("O parâmetro 'place_id' contém caracteres inválidos.")
    return value


def _validate_level(level: str) -> str:
    value = (level or "demo").strip().lower() if isinstance(level, str) else ""
    if value not in PRODUCTION_LEVELS:
        raise ValueError("O nível deve ser 'demo' ou 'full'.")
    return value


def _optional_request(gateway: ProspectOSGateway, path: str) -> Optional[Dict[str, Any]]:
    """Retorna None para um recurso ausente, mas não mascara falhas do backend."""
    try:
        result = gateway.request("GET", path)
    except MCPError as err:
        if err.codigo == "LEAD_NAO_ENCONTRADO":
            return None
        raise
    return result if isinstance(result, dict) else None


def _trim_text(value: Any, limit: int = 4000) -> str:
    if value is None:
        return ""
    return str(value).strip()[:limit]


def _sanitize_strategy(strategy: Any) -> Dict[str, Any]:
    if not isinstance(strategy, dict):
        return {}
    fields = (
        "opportunity",
        "problem",
        "evidence",
        "commercialAngle",
        "recommendedCta",
        "confidence",
        "primaryRule",
    )
    result: Dict[str, Any] = {}
    for field in fields:
        value = strategy.get(field)
        if field == "evidence" and isinstance(value, list):
            result[field] = [_trim_text(item, 600) for item in value[:12]]
        elif value is not None:
            result[field] = _trim_text(value)
    return result


def _sanitize_messages(messages: Any) -> Dict[str, Any]:
    if not isinstance(messages, dict):
        return {}
    result: Dict[str, Any] = {}
    for field in ("initial", "afterInterest", "prototypeDelivery", "closing"):
        if messages.get(field) is not None:
            result[field] = _trim_text(messages[field], 3000)

    followups = messages.get("followups")
    if isinstance(followups, list):
        safe_followups: List[Dict[str, Any]] = []
        for item in followups[:3]:
            if not isinstance(item, dict):
                continue
            safe_followups.append(
                {
                    "order": item.get("order"),
                    "delayDays": item.get("delayDays"),
                    "objective": _trim_text(item.get("objective"), 500),
                    "message": _trim_text(item.get("message"), 3000),
                }
            )
        result["followups"] = safe_followups
    return result


def _sanitize_pack(pack: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(pack, dict):
        return None
    result: Dict[str, Any] = {
        "id": pack.get("id"),
        "place_id": pack.get("placeId") or pack.get("place_id"),
        "landing_page_id": pack.get("landingPageId") or pack.get("landing_page_id"),
        "status": pack.get("status"),
        "provider": pack.get("provider"),
        "version": pack.get("version"),
        "created_at": pack.get("createdAt") or pack.get("created_at"),
        "updated_at": pack.get("updatedAt") or pack.get("updated_at"),
        "approved_at": pack.get("approvedAt") or pack.get("approved_at"),
        "strategy": _sanitize_strategy(pack.get("strategy")),
        "messages": _sanitize_messages(pack.get("messages")),
    }

    objections = pack.get("objections")
    if isinstance(objections, list):
        result["objections"] = [
            {
                "objection": _trim_text(item.get("objection"), 600),
                "response": _trim_text(item.get("response"), 1200),
            }
            for item in objections[:10]
            if isinstance(item, dict)
        ]
    else:
        result["objections"] = []

    prototype = pack.get("prototype")
    if isinstance(prototype, dict):
        result["prototype"] = {
            "template_key": normalizar_template_key(prototype.get("templateKey")),
            "focus": [
                _trim_text(item, 120)
                for item in (prototype.get("focus") or [])[:12]
                if isinstance(item, str)
            ],
            "hero_angle": _trim_text(prototype.get("heroAngle"), 1200),
            "primary_cta": _trim_text(prototype.get("primaryCta"), 500),
            "sections_to_highlight": [
                _trim_text(item, 120)
                for item in (prototype.get("sectionsToHighlight") or [])[:12]
                if isinstance(item, str)
            ],
        }
    else:
        result["prototype"] = {}
    return result


def _sanitize_landing_page(page: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(page, dict):
        return None

    def strip_sensitive(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: strip_sensitive(item)
                for key, item in value.items()
                if not any(part in str(key).lower() for part in SENSITIVE_KEY_PARTS)
            }
        if isinstance(value, list):
            return [strip_sensitive(item) for item in value]
        return value

    raw_spec = page.get("spec") if isinstance(page.get("spec"), dict) else {}
    safe_spec = strip_sensitive(
        {key: raw_spec[key] for key in LP_SPEC_ALLOWLIST if key in raw_spec}
    )
    return {
        "id": page.get("id"),
        "place_id": page.get("place_id"),
        "slug": _trim_text(page.get("slug"), 200),
        "template_key": normalizar_template_key(page.get("template_key")),
        "status": page.get("status"),
        "schema_version": page.get("schema_version"),
        "spec": safe_spec,
        "preview_url": _trim_text(page.get("preview_url"), 1000),
        "public_url": _trim_text(page.get("public_url"), 1000),
        "public_id": _trim_text(page.get("public_id"), 300),
        "publish_provider": _trim_text(page.get("publish_provider"), 120),
        "publication_revision": page.get("publication_revision", 0),
        "last_published_at": page.get("last_published_at"),
        "published_at": page.get("published_at"),
        "unpublished_at": page.get("unpublished_at"),
        "created_at": page.get("created_at"),
        "updated_at": page.get("updated_at"),
    }


def _build_investment_gate(
    level: str, lead: Dict[str, Any], pack: Optional[Dict[str, Any]], page: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    blockers: List[str] = []
    crm_status = (lead.get("status") or "").strip()
    pack_status = pack.get("status") if pack else None

    if level == "demo":
        if not page:
            blockers.append("landing_page_missing")
        if pack_status == "archived":
            blockers.append("conversion_pack_archived")
    else:
        if not pack:
            blockers.append("conversion_pack_missing")
        elif pack_status != "approved":
            blockers.append("conversion_pack_not_approved")
        if crm_status not in {"respondeu", "fechou"}:
            blockers.append("human_sales_signal_missing")

    return {
        "level": level,
        "eligible": not blockers,
        "blockers": blockers,
        "human_approval_required": level == "full",
        "owner": "sol_advisor",
    }


def _build_site_context(gateway: ProspectOSGateway, place_id: str, level: str) -> Dict[str, Any]:
    raw_lead = gateway.request("GET", f"/api/leads/{place_id}")
    lead = sanitize_maps_lead(raw_lead)
    if not lead:
        raise MCPError("BACKEND_INCOMPATIVEL", "O backend não retornou um lead compatível.")

    raw_pack = _optional_request(gateway, f"/api/leads/{place_id}/conversion-pack")
    raw_page = _optional_request(gateway, f"/api/leads/{place_id}/landing-page")
    pack = _sanitize_pack(raw_pack)
    page = _sanitize_landing_page(raw_page)

    return {
        "contract_version": CONTRACT_VERSION,
        "place_id": place_id,
        "production_level": level,
        "company": {
            "name": _trim_text(lead.get("nome"), 300),
            "category": _trim_text(lead.get("categoria"), 200),
            "niche": _trim_text(lead.get("nicho"), 200),
            "city": _trim_text(lead.get("cidade"), 200),
            "address": _trim_text(lead.get("endereco"), 500),
        },
        "crm": {"status": lead.get("status"), "score": lead.get("score")},
        "current_website": {
            "url": _trim_text(lead.get("site_url") or lead.get("site"), 1000),
            "status": lead.get("site_status"),
            "problems": _trim_text(lead.get("site_problemas"), 2000),
            "checklist": lead.get("site_checklist") if isinstance(lead.get("site_checklist"), dict) else None,
        },
        "reputation": {"rating": lead.get("nota"), "review_count": lead.get("num_avaliacoes")},
        "contact": {
            "phone": _trim_text(lead.get("telefone"), 80),
            "whatsapp_link": _trim_text(lead.get("whatsapp_link"), 1000),
            "instagram_url": _trim_text(lead.get("instagram_url"), 1000),
        },
        "commercial_strategy": pack.get("strategy") if pack else {},
        "conversion_pack": pack,
        "landing_page": page,
        "investment": _build_investment_gate(level, lead, pack, page),
        "handoff": {
            "prospectos_owns": ["commercial_context", "crm", "conversion_pack", "landing_page_demo"],
            "sol_advisor_owns": ["planning", "implementation", "review", "preview", "deploy"],
        },
    }


def _validate_result_field(value: Any, name: str, required: bool = False) -> Optional[str]:
    if value is None or value == "":
        if required:
            raise ValueError(f"O parâmetro '{name}' é obrigatório para este status.")
        return None
    if not isinstance(value, str):
        raise ValueError(f"O parâmetro '{name}' deve ser texto.")
    clean = value.strip()
    if not clean or len(clean) > MAX_RESULT_FIELD_LENGTH or any(ord(char) < 32 for char in clean):
        raise ValueError(f"O parâmetro '{name}' é inválido ou excede o limite permitido.")
    if "|" in clean:
        raise ValueError(f"O parâmetro '{name}' não pode conter '|'.")
    return clean


def _validate_preview_url(value: Optional[str], required: bool) -> Optional[str]:
    clean = _validate_result_field(value, "preview_url", required=required)
    if not clean:
        return None
    if clean.startswith("/"):
        path = urlparse(clean).path
        if clean.startswith("//") or not path.startswith("/demos/") or path == "/demos/":
            raise ValueError("'preview_url' local deve usar o caminho '/demos/<...>'.")
        return clean
    parsed = urlparse(clean)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("'preview_url' deve ser uma URL HTTP(S) sem credenciais embutidas.")
    return clean


def _merge_result_block(existing: Any, record: Dict[str, Any]) -> str:
    current = str(existing or "").strip()
    block = (
        f"{RESULT_BLOCK_START}\n"
        f"{json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}\n"
        f"{RESULT_BLOCK_END}"
    )
    pattern = re.compile(re.escape(RESULT_BLOCK_START) + r".*?" + re.escape(RESULT_BLOCK_END), re.DOTALL)
    if pattern.search(current):
        merged = pattern.sub(lambda _: block, current)
    elif current:
        merged = f"{current}\n\n{block}"
    else:
        merged = block
    if len(merged) > MAX_OBSERVATIONS_LENGTH:
        raise ValueError("As observações do lead excederiam o limite de 5000 caracteres.")
    return merged


def register_site_production_tools(mcp: FastMCP, gateway: ProspectOSGateway) -> None:
    """Registra o contrato pequeno de handoff comercial → produção."""

    @mcp.tool(
        name="obter_contexto_producao_site",
        description=(
            "Compõe o contexto comercial existente de um lead para o Sol Advisor. "
            "Reutiliza lead, conversion pack e Landing Page; não gera IA, não cria site e não altera dados. "
            "Use nivel='demo' para protótipo e nivel='full' para avaliar elegibilidade de produção completa."
        ),
    )
    def obter_contexto_producao_site(place_id: str, nivel: str = "demo") -> Dict[str, Any]:
        try:
            pid = _validate_place_id(place_id)
            level = _validate_level(nivel)
            context = _build_site_context(gateway, pid, level)
            return build_success_response(
                context,
                meta={
                    "read_only": True,
                    "partial": context["conversion_pack"] is None or context["landing_page"] is None,
                },
            )
        except ValueError as err:
            return format_error_response("PARAMETRO_INVALIDO", str(err))
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao obter contexto de produção: {str(exc)}")

    @mcp.tool(
        name="registrar_resultado_site",
        description=(
            "Registra no CRM o resultado do trabalho do Sol Advisor usando as observações existentes do lead. "
            "A operação é idempotente, não cria tabelas e não publica o site. "
            "Para preview_ready, reviewed ou deployed, informe uma preview_url HTTP(S) ou /demos/<...>."
        ),
    )
    def registrar_resultado_site(
        place_id: str,
        status: str,
        preview_url: Optional[str] = None,
        repository: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            pid = _validate_place_id(place_id)
            result_status = (status or "").strip().lower() if isinstance(status, str) else ""
            if result_status not in SITE_RESULT_STATUSES:
                return format_error_response(
                    "PARAMETRO_INVALIDO",
                    "Status inválido. Use planned, in_progress, preview_ready, reviewed, deployed, failed ou blocked.",
                )
            requires_url = result_status in {"preview_ready", "reviewed", "deployed"}
            url = _validate_preview_url(preview_url, required=requires_url)
            repo = _validate_result_field(repository, "repository")
            ref = _validate_result_field(branch, "branch")

            lead_response = gateway.request("GET", f"/api/leads/{pid}")
            if not isinstance(lead_response, dict):
                raise MCPError("BACKEND_INCOMPATIVEL", "O backend não retornou o lead para registrar o resultado.")

            record = {
                "contract_version": RESULT_VERSION,
                "status": result_status,
                "preview_url": url,
                "repository": repo,
                "branch": ref,
            }
            merged_observations = _merge_result_block(lead_response.get("observacoes"), record)
            gateway.request(
                "POST",
                f"/api/leads/{pid}/observacoes",
                json_data={"observacoes": merged_observations},
            )
            return build_success_response(
                {
                    "place_id": pid,
                    "status": result_status,
                    "preview_url": url,
                    "repository": repo,
                    "branch": ref,
                    "recorded_in": "lead.observacoes",
                },
                meta={"idempotent": RESULT_BLOCK_START in str(lead_response.get("observacoes") or "")},
            )
        except ValueError as err:
            return format_error_response("PARAMETRO_INVALIDO", str(err))
        except MCPError as err:
            return format_error_response(err.codigo, err.mensagem, err.detalhes)
        except Exception as exc:
            return format_error_response("ERRO_INTERNO", f"Falha ao registrar resultado do site: {str(exc)}")
