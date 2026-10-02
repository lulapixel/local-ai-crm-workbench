"""Isolated management data and actual workbench integration, no live calls."""
import copy
from datetime import date, datetime, timezone
import json
import sqlite3
from uuid import uuid4

import pytest
from flask import Flask

import bot
import bot_delivery
import bot_strategy
import db
import local_workbench
import management as manager
import processar


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "manager.db")
    monkeypatch.setattr(manager, "today", lambda: date(2026, 10, 2))
    with sqlite3.connect(db.CAMINHO_BANCO) as c:
        processar.preparar_banco(c)
        bot.preparar_banco(c)
        bot_strategy.preparar_banco(c)
        bot_delivery.preparar_banco(c)
        manager.preparar_banco(c)
    def forbidden(*args, **kwargs):
        pytest.fail("Live model/provider/transmission forbidden")
    monkeypatch.setattr(bot, "capturar", forbidden)
    monkeypatch.setattr(bot_strategy, "chamar_modelo", forbidden)
    monkeypatch.setattr(bot_delivery.requests, "post", forbidden)


def configuration(revision=0, **profile):
    return {"revision": revision,
            "profile": {"focus": "parallel", "city": "Caruaru", "monthly_received_target_cents": 150000,
                        "explanation": "reasoned", **profile}, "offer": copy.deepcopy(manager.DEFAULT_OFFER)}


def receipt(**changes):
    return {"id": str(uuid4()), "received_on": "2026-10-02", "amount_cents": 12345,
            "description": "Synthetic payment", "lane": "websites", **changes}


def test_read_only_defaults_do_not_claim_personal_profile_or_receipts():
    with bot.conectar() as c:
        before = list(c.iterdump())
    dashboard = manager.painel()
    with bot.conectar() as c:
        assert list(c.iterdump()) == before
    assert dashboard["profile"]["monthly_received_target_cents"] is None
    assert dashboard["profile"]["source"] == "not_configured"
    assert dashboard["recommendation"]["kind"] == "offer"
    assert dashboard["finance"]["count"] == 0
    assert not dashboard["readiness"]["ready"]


def test_save_is_atomic_and_stale_revision_cannot_overwrite():
    body = configuration()
    first = manager.save_settings(body)
    assert first["revision"] == 1
    assert first["profile"]["reviewed_on"] == "2026-10-02"
    with pytest.raises(bot.Conflict):
        manager.save_settings(body)
    invalid = configuration(1); invalid["offer"]["price_cents"] = True
    with pytest.raises(ValueError):
        manager.save_settings(invalid)
    with bot.conectar() as c:
        assert manager.settings(c) == first


@pytest.mark.parametrize("key,value", [("enabled", True), ("model", "unapproved"), ("source", "forged"), ("monthly_received_target_cents", True)])
def test_profile_cannot_grant_permissions_or_forge_source(key, value):
    body = configuration(); body["profile"][key] = value
    with pytest.raises(ValueError):
        manager.save_settings(body)


@pytest.mark.parametrize("url", ["javascript:alert(1)", "file:///c:/secret", "//evil.test/demo", "https://user:pass@example.com", "https://example.com\\@evil.test", "https://["])
def test_demo_url_rejects_unsafe_links(url):
    body = configuration(); body["offer"]["demo_url"] = url
    with pytest.raises(ValueError):
        manager.save_settings(body)


def test_changed_offer_invalidates_review_and_requires_new_explicit_confirmation():
    body = configuration()
    body["offer"].update(audience="Synthetic services", outcome="Clear catalogue", scope="One page", price_cents=100000,
                         delivery_days=7, demo_url="/demos/estetica-premium", demo_reviewed=True, fulfillment_reviewed=True)
    assert manager.offer_readiness(manager.save_settings(body)["offer"])["ready"]
    body["revision"] = 1; body["offer"].update(scope="Two pages", demo_url="https://example.com/demo")
    changed = manager.save_settings(body)
    assert not changed["offer"]["demo_reviewed"] and not changed["offer"]["fulfillment_reviewed"]
    body["revision"] = 2
    assert manager.offer_readiness(manager.save_settings(body)["offer"])["ready"]


def test_receipt_retry_exactly_once_and_conflicting_retry_refused():
    body = receipt()
    assert manager.record_receipt(body)["duplicate"] is False
    assert manager.record_receipt(body)["duplicate"] is True
    with pytest.raises(bot.Conflict):
        manager.record_receipt({**body, "amount_cents": 30000})
    assert manager.painel()["finance"]["received_cents"] == 12345
    manager.void_receipt(body["id"])
    manager.void_receipt(body["id"])
    assert manager.record_receipt(body)["voided"] is True
    summary = manager.painel()["finance"]
    assert summary["received_cents"] == 0 and summary["rows"][0]["voided_at"]


@pytest.mark.parametrize("changes", [{"amount_cents": 0}, {"amount_cents": True}, {"amount_cents": 1.5},
    {"amount_cents": 100_000_001}, {"received_on": "2026-10-03"}, {"received_on": "2026-02-30"},
    {"received_on": "20261002"}, {"lane": "unknown"}, {"description": " "}])
def test_invalid_receipts_do_not_write(changes):
    with pytest.raises(ValueError):
        manager.record_receipt(receipt(**changes))
    assert manager.painel()["finance"]["count"] == 0


def test_monthly_cash_is_not_won_leads_and_aggregates_beyond_history_limit():
    manager.save_settings(configuration())
    with bot.conectar() as c:
        c.execute("INSERT INTO leads(place_id,nome,status) VALUES('won','Synthetic','fechou')")
    manager.record_receipt(receipt(received_on="2026-09-30", amount_cents=99999))
    for _ in range(32):
        manager.record_receipt(receipt(amount_cents=10))
    data = manager.painel()
    assert data["finance"]["received_cents"] == 320
    assert data["finance"]["count"] == 32 and len(data["finance"]["rows"]) == 30
    assert data["finance"]["remaining_cents"] == 149680
    assert manager.painel("2026-09")["finance"]["received_cents"] == 99999
    with pytest.raises(ValueError):
        manager.painel("2026-13")


def test_profile_affects_real_priority_ties_but_never_displaces_replies():
    manager.save_settings(configuration())
    with bot.conectar() as c:
        for pid, city, status, phone in [("z", "Caruaru", "novo", "81999999991"),
                                       ("a", "Recife", "novo", "81999999992"),
                                       ("r", "Recife", "respondeu", "81999999993")]:
            c.execute("""INSERT INTO leads(place_id,nome,cidade,status,telefone,site_status,nota,num_avaliacoes)
                VALUES(?,?,?,?,?,'sem_site',5,100)""", (pid, "Synthetic " + pid, city, status, phone))
    plan = local_workbench.planejar(at=datetime(2026, 10, 2, tzinfo=timezone.utc))
    assert [a["lead_id"] for a in plan["actions"]] == ["r", "z", "a"]
    assert all(a["human_decision"] and a["learning"] for a in plan["actions"])
    assert manager.painel()["recommendation"]["kind"] == "relationship"


def test_strategy_only_receives_allowlisted_operational_context():
    body = configuration(); body["offer"]["scope"] = "PRIVATE marker"
    manager.save_settings(body)
    with bot.conectar() as c:
        context = bot_strategy.snapshot(c)["management_context"]
        cfg = bot_strategy.settings(c)
    assert set(context) == {"focus", "offer_ready", "decision_style", "new_spending_authorized", "profile_grants_permissions"}
    assert "PRIVATE" not in json.dumps(context) and "150000" not in json.dumps(context)
    assert not context["profile_grants_permissions"] and not cfg["enabled"]


def test_http_errors_and_private_cache_headers():
    app = Flask(__name__); app.register_blueprint(manager.bp)
    client = app.test_client()
    assert client.get("/api/management").headers["Cache-Control"] == "no-store"
    assert client.put("/api/management/settings", json=configuration()).status_code == 200
    assert client.put("/api/management/settings", json=configuration()).status_code == 409
    assert client.post("/api/management/receipts", json={}).status_code == 400
