"""Private local management preferences, offer preparation and declared receipts.

This module never changes bot permissions, calls providers or transmits messages.
Personal settings belong to the local database, never to source-code defaults.
"""
import json
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import UUID

from flask import Blueprint, jsonify, request

import bot

bp = Blueprint("management", __name__)
BRASILIA = timezone(timedelta(hours=-3))
DEFAULT_PROFILE = {"focus": "parallel", "city": "", "monthly_received_target_cents": None,
                   "explanation": "reasoned", "source": "not_configured", "reviewed_on": None}
DEFAULT_OFFER = {"title": "Website para negócios locais", "audience": "", "outcome": "",
                 "scope": "", "price_cents": None, "delivery_days": None, "demo_url": "",
                 "demo_reviewed": False, "fulfillment_reviewed": False}


def today():
    return datetime.now(BRASILIA).date()


def preparar_banco(c):
    c.executescript("""
        CREATE TABLE IF NOT EXISTS management_settings (
            id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL,
            profile_json TEXT NOT NULL, offer_json TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS management_receipts (
            id TEXT PRIMARY KEY, received_on TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
            description TEXT NOT NULL, lane TEXT NOT NULL CHECK(lane IN ('websites','remote')),
            created_at TEXT NOT NULL, voided_at TEXT
        );
        CREATE INDEX IF NOT EXISTS management_receipts_month ON management_receipts(received_on);
    """)


def settings(c):
    # Older tests/consumers can read the neutral defaults without a write migration.
    exists = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='management_settings'").fetchone()
    row = c.execute("SELECT * FROM management_settings WHERE id=1").fetchone() if exists else None
    return {"revision": row["revision"] if row else 0,
            "profile": json.loads(row["profile_json"]) if row else DEFAULT_PROFILE.copy(),
            "offer": json.loads(row["offer_json"]) if row else DEFAULT_OFFER.copy()}


def _text(body, key, maximum):
    value = body.get(key)
    if not isinstance(value, str) or len(value.strip()) > maximum or any(ord(ch) < 32 and ch not in "\n\t" for ch in value):
        raise ValueError(f"Campo {key} inválido; limite de {maximum} caracteres.")
    return value.strip()


def _integer(value, label, maximum, nullable=True):
    if nullable and value is None:
        return None
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"{label}: informe um inteiro positivo dentro do limite.")
    return value


def validate_profile(body, source="operator"):
    keys = {"focus", "city", "monthly_received_target_cents", "explanation"}
    if not isinstance(body, dict) or set(body) != keys:
        raise ValueError("Preferências fora do contrato. Permissões do bot não fazem parte do perfil.")
    if body["focus"] not in ("websites", "remote", "parallel") or body["explanation"] not in ("brief", "reasoned"):
        raise ValueError("Escolha a frente de trabalho e o nível de explicação.")
    return {**body, "city": _text(body, "city", 100),
            "monthly_received_target_cents": _integer(body["monthly_received_target_cents"], "Referência mensal", 100_000_000),
            "source": source, "reviewed_on": today().isoformat()}


def validate_offer(body):
    if not isinstance(body, dict) or set(body) != set(DEFAULT_OFFER):
        raise ValueError("Oferta fora do contrato.")
    result = {key: _text(body, key, maximum) for key, maximum in
              (("title", 120), ("audience", 200), ("outcome", 400), ("scope", 1200), ("demo_url", 500))}
    url = result["demo_url"]
    # Only known internal demo routes or ordinary HTTPS links, never filesystem/script URLs.
    if url:
        internal = bool(re.fullmatch(r"/demos/[a-z0-9-]+", url))
        try:
            parts = urlsplit(url)
            external = (parts.scheme == "https" and bool(parts.hostname) and not parts.username and
                        not parts.password and not re.search(r"[\s\\]", url))
        except ValueError:
            external = False
        if not (internal or external):
            raise ValueError("Use uma demonstração interna /demos/… ou um endereço HTTPS válido.")
    for key in ("demo_reviewed", "fulfillment_reviewed"):
        if type(body[key]) is not bool:
            raise ValueError("Informe a revisão da demonstração e da capacidade de entrega.")
        result[key] = body[key]
    result["price_cents"] = _integer(body["price_cents"], "Preço proposto", 100_000_000)
    result["delivery_days"] = _integer(body["delivery_days"], "Prazo proposto", 365)
    if result["demo_reviewed"] and not result["demo_url"]:
        raise ValueError("Inclua a demonstração antes de registrar sua revisão.")
    return result


def save_settings(body):
    if not isinstance(body, dict) or set(body) != {"revision", "profile", "offer"} or type(body["revision"]) is not int:
        raise ValueError("Informe a versão e os campos completos da configuração.")
    profile, offer = validate_profile(body["profile"]), validate_offer(body["offer"])
    with bot.conectar() as c:
        c.execute("BEGIN IMMEDIATE")
        old = settings(c)
        if body["revision"] != old["revision"]:
            raise bot.Conflict("As preferências mudaram em outra janela. Copie suas alterações e recarregue antes de salvar.")
        # Reviewing a demo or delivery promise does not survive changing its basis.
        if old["revision"]:
            if offer["demo_url"] != old["offer"]["demo_url"]:
                offer["demo_reviewed"] = False
            if any(offer[k] != old["offer"][k] for k in ("scope", "delivery_days", "price_cents", "outcome", "audience")):
                offer["fulfillment_reviewed"] = False
        c.execute("""INSERT INTO management_settings VALUES(1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
            revision=excluded.revision,profile_json=excluded.profile_json,offer_json=excluded.offer_json,updated_at=excluded.updated_at""",
            (old["revision"] + 1, json.dumps(profile, ensure_ascii=False), json.dumps(offer, ensure_ascii=False), bot.agora()))
        return settings(c)


def offer_readiness(offer):
    checks = [("audience", "Defina para quem é a oferta", bool(offer["audience"])),
              ("promise", "Descreva resultado e escopo", all(offer[k] for k in ("title", "outcome", "scope"))),
              ("terms", "Defina preço e prazo propostos", bool(offer["price_cents"] and offer["delivery_days"])),
              ("demo", "Confira uma demonstração", bool(offer["demo_url"] and offer["demo_reviewed"])),
              ("delivery", "Confira sua capacidade de entregar", offer["fulfillment_reviewed"])]
    return {"ready": all(ok for _, _, ok in checks), "completed": sum(bool(ok) for _, _, ok in checks),
            "total": len(checks), "checks": [{"id": key, "label": label, "done": bool(ok)} for key, label, ok in checks]}


def strategy_context(c):
    """Bounded operational context only: no financial goal, personal history or offer text."""
    data = settings(c)
    return {"focus": data["profile"]["focus"], "offer_ready": offer_readiness(data["offer"])["ready"],
            "decision_style": data["profile"]["explanation"], "new_spending_authorized": False,
            "profile_grants_permissions": False}


def decorate_action(action):
    descriptions = {
        "conversation": ("Negociação", "Confirmar a necessidade e decidir o próximo passo", "Uma resposta permite aprender com demanda real antes de captar mais contatos."),
        "followup": ("Relacionamento", "Conferir a conversa antes de retomar", "Um retorno só faz sentido com contexto e respeito à decisão do contato."),
        "review": ("Aprovação", "Revisar texto, destinatário e proposta", "A aprovação vale para uma versão específica da abordagem."),
        "manual_contact": ("Contato", "Decidir e realizar o contato autorizado", "Texto preparado, contato feito e receita recebida são etapas diferentes."),
        "research": ("Pesquisa", "Validar evidências e oportunidade", "Ausência de site pode sugerir uma necessidade; não comprova interesse em comprar."),
        "opportunity": ("Qualificação", "Verificar se a oferta resolve um problema", "Pontuação ajuda a organizar investigação, não mede probabilidade de venda."),
    }
    department, decision, learning = descriptions.get(action["kind"], ("Operação", "Revisar o próximo passo", "Confira as evidências antes de decidir."))
    return {**action, "department": department, "human_decision": decision, "learning": learning}


def record_receipt(body):
    if not isinstance(body, dict) or set(body) != {"id", "received_on", "amount_cents", "description", "lane"}:
        raise ValueError("Recebimento fora do contrato.")
    try:
        identifier = str(UUID(body["id"]))
        received = date.fromisoformat(body["received_on"])
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Informe um identificador e uma data válidos.") from None
    if received.isoformat() != body["received_on"] or received > today() or received.year < 2000:
        raise ValueError("Registre somente recebimentos já ocorridos, com data a partir de 2000.")
    amount = _integer(body["amount_cents"], "Valor recebido", 100_000_000, False)
    description = _text(body, "description", 120)
    if not description or body["lane"] not in ("websites", "remote"):
        raise ValueError("Informe a descrição e a frente de receita.")
    values = (received.isoformat(), amount, description, body["lane"])
    with bot.conectar() as c:
        c.execute("BEGIN IMMEDIATE")
        old = c.execute("SELECT * FROM management_receipts WHERE id=?", (identifier,)).fetchone()
        if old:
            if tuple(old[k] for k in ("received_on", "amount_cents", "description", "lane")) != values:
                raise bot.Conflict("Este registro já existe com outros valores. Confira o histórico antes de tentar novamente.")
            return {"id": identifier, "duplicate": True, "voided": bool(old["voided_at"])}
        c.execute("INSERT INTO management_receipts VALUES(?,?,?,?,?,?,NULL)", (identifier, *values, bot.agora()))
    return {"id": identifier, "duplicate": False, "voided": False}


def void_receipt(identifier):
    with bot.conectar() as c:
        row = c.execute("SELECT id FROM management_receipts WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise ValueError("Recebimento não encontrado.")
        c.execute("UPDATE management_receipts SET voided_at=COALESCE(voided_at,?) WHERE id=?", (bot.agora(), identifier))
    return {"id": identifier, "voided": True}


def financial_summary(c, month, target):
    if not isinstance(month, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("Selecione um mês válido, no formato AAAA-MM.")
    received, count = c.execute("""SELECT COALESCE(SUM(amount_cents),0),COUNT(*) FROM management_receipts
        WHERE substr(received_on,1,7)=? AND voided_at IS NULL""", (month,)).fetchone()
    rows = [dict(r) for r in c.execute("""SELECT id,received_on,amount_cents,description,lane,voided_at FROM management_receipts
        WHERE substr(received_on,1,7)=? ORDER BY received_on DESC,created_at DESC,id LIMIT 30""", (month,))]
    return {"month": month, "received_cents": received, "count": count, "target_cents": target,
            "remaining_cents": max(0, target-received) if target is not None else None,
            "rows": rows, "history_limit": 30, "basis": "operator_records"}


def recommendation(plan, data):
    actions = plan["actions"]
    urgent = next((a for a in actions if a["kind"] in ("conversation", "followup")), None)
    if urgent:
        return {"kind": "relationship", "title": f"Avance a conversa com {urgent['name']}",
                "reason": urgent["reason"], "alternative": "Amplie a pesquisa depois de tratar respostas e retornos pendentes.",
                "href": urgent["href"], "label": "Conferir conversa", "evidence": "Registro local de resposta ou retorno"}
    if not offer_readiness(data["offer"])["ready"]:
        return {"kind": "offer", "title": "Prepare uma oferta que você consiga demonstrar e entregar.",
                "reason": "A prontidão comercial ainda não foi confirmada. Definir escopo, preço e demonstração torna a próxima abordagem mais concreta.",
                "alternative": "A mesma demonstração pode apoiar serviços locais e candidaturas a contratos remotos; demanda ainda precisa ser validada.",
                "href": "#oferta", "label": "Preparar minha oferta", "evidence": "Checklist local de prontidão"}
    if actions:
        a = actions[0]
        return {"kind": "operation", "title": f"{a['human_decision']}: {a['name']}", "reason": a["reason"],
                "alternative": "A oferta está revisada pelo operador; acompanhe respostas antes de aumentar o volume.",
                "href": a["href"], "label": "Abrir próxima ação", "evidence": "Fila elegível da operação"}
    focus = data["profile"]["focus"]
    return {"kind": "discover", "title": "Use sua demonstração para investigar uma oportunidade concreta.",
            "reason": "A oferta foi revisada, mas não há ação elegível no recorte atual. Revisão não comprova demanda.",
            "alternative": "Para contratos remotos, descreva o que você produziu e onde a IA ajudou no mesmo material de apresentação.",
            "href": "#oferta" if focus == "remote" else "/pesquisa", "label": "Revisar apresentação" if focus == "remote" else "Abrir pesquisa",
            "evidence": "Oferta revisada e fila sem ações elegíveis"}


def painel(month=None):
    import local_workbench
    plan = local_workbench.planejar()
    with bot.conectar() as c:
        data = settings(c)
        finance = financial_summary(c, month or today().strftime("%Y-%m"), data["profile"]["monthly_received_target_cents"])
    return {**data, "finance": finance, "readiness": offer_readiness(data["offer"]),
            "recommendation": recommendation(plan, data), "operation": plan, "today": today().isoformat(),
            "demo_asset": {"href": "/demos/estetica-premium", "label": "Demonstração de estética", "status": "available_for_review"},
            "planning_only": True, "new_spending_authorized": False}


@bp.after_request
def no_cache(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.get("/api/management")
def get_dashboard():
    return bot._responder(painel, request.args.get("month"))


@bp.put("/api/management/settings")
def put_settings():
    return bot._responder(save_settings, request.get_json(silent=True))


@bp.post("/api/management/receipts")
def post_receipt():
    return bot._responder(record_receipt, request.get_json(silent=True), status=201)


@bp.post("/api/management/receipts/<identifier>/void")
def post_void(identifier):
    return bot._responder(void_receipt, identifier)
