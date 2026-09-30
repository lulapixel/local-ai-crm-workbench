import json
import sqlite3
from datetime import datetime
from types import SimpleNamespace

import pytest

import bot
import bot_strategy as strategy
import bot_policy as policy
import bot_delivery as delivery
import db
import processar


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "strategy.db")
    with sqlite3.connect(db.CAMINHO_BANCO) as c:
        processar.preparar_banco(c); bot.preparar_banco(c); strategy.preparar_banco(c); delivery.preparar_banco(c)
        c.execute("INSERT INTO leads(place_id,nome,telefone,status,site_status,nota,num_avaliacoes) VALUES('p1','Fictícia','11999999999','novo','sem_site',5,100)")
    monkeypatch.setattr(strategy, "now", lambda: datetime(2026, 9, 30, 15, 0, tzinfo=strategy.BRASILIA))
    def forbidden(*args, **kwargs):
        pytest.fail("Chamada real proibida")
    monkeypatch.setattr(strategy, "chamar_modelo", forbidden)
    monkeypatch.setattr(delivery.requests, "post", forbidden)
    for key in ("PROSPECTOS_RESEND_API_KEY", "PROSPECTOS_EMAIL_FROM", "PROSPECTOS_WA_TOKEN", "PROSPECTOS_WA_PHONE_ID", "PROSPECTOS_WA_API_VERSION", "PROSPECTOS_WA_TEMPLATE", "PROSPECTOS_WA_TEMPLATE_BODY", "PROSPECTOS_BOT_LIVE_SENDS"):
        monkeypatch.delenv(key, raising=False)


def campaign():
    return bot.criar({"oferta": "sites locais"})["id"]


def enable(mode="solo", **changes):
    strategy.configurar({"enabled": True, "mode": mode, **changes})


def mock_model(monkeypatch, abstain=False):
    calls = []
    def fake(snap, role, proposal=None, decision=None):
        calls.append({"role": role, "proposal": proposal, "decision": decision})
        return {"campaign_ids": [] if abstain else [snap["campaigns"][0]["id"]], "reason": "Base disponível", "hypothesis": "Evitar nova captura", "abstain": abstain}, {"model": decision["model"], "effort": decision["effort"], "duration_ms": 100, "tokens": None}
    monkeypatch.setattr(strategy, "chamar_modelo", fake)
    return calls


@pytest.mark.parametrize("selection", list(policy.CHOICES))
def test_all_requested_combinations(selection, monkeypatch):
    cid = campaign(); enable(selection=selection)
    calls = mock_model(monkeypatch)
    strategy.executar(background=False)
    assert calls[0]["decision"]["choice"] == selection
    result = strategy.painel()
    assert result["runs"][0]["state"] == "completed"
    assert result["runs"][0]["calls"][0]["observed_model"] == policy.CHOICES[selection]["model"]
    assert bot.painel()["counts"]["pending"] == 1
    assert result["used_today"] == 1
    assert bot.painel()["runs"][0]["campaign_id"] == cid


def test_window_and_disabled_no_call(monkeypatch):
    campaign()
    with pytest.raises(bot.Conflict, match="desativada"):
        strategy.executar(False)
    enable()
    monkeypatch.setattr(strategy, "now", lambda: datetime(2026,9,30,14,59,tzinfo=strategy.BRASILIA))
    with pytest.raises(bot.Conflict, match="15h"):
        strategy.executar(False)
    assert strategy.painel()["used_today"] == 0


def test_duo_two_calls_context_separation_and_daily_lock(monkeypatch):
    campaign(); enable("duo"); calls = mock_model(monkeypatch)
    strategy.executar(False)
    assert len(calls) == 2 and calls[0]["proposal"] is None and calls[1]["proposal"] is not None
    assert strategy.painel()["used_today"] == 2
    with pytest.raises(bot.Conflict, match="janela"):
        strategy.executar(False)
    assert len(calls) == 2


def test_mismatched_pin_disarms_without_fallback(monkeypatch):
    campaign(); enable("duo")
    def fake(*args):
        return {"campaign_ids": [1], "reason": "a", "hypothesis": "b", "abstain": False}, {"model": "different", "effort": "low"}
    monkeypatch.setattr(strategy, "chamar_modelo", fake)
    strategy.executar(False)
    result = strategy.painel()
    assert result["used_today"] == 1
    assert result["runs"][0]["state"] == "error"
    assert not bot.painel()["runs"]


def test_feedback_drives_routing_not_infra_errors():
    snap = {"campaigns": [{"id": 1, "nicho": "a"}], "history": [{"state": "error"}]*5}
    assert policy.decidir(snap, {})["choice"] == "luna_high"
    snap["history"] = [{"feedback": "rejected"}]*2
    assert policy.decidir(snap, {})["choice"] == "sol_medium"
    snap["history"].append({"feedback": "rejected"})
    assert policy.decidir(snap, {})["choice"] == "sol_high"
    snap["history"] = []; snap["campaigns"] = [{"id": n,"nicho": str(n)} for n in range(10)]
    assert policy.decidir(snap, {"task_type": "triage"})["choice"] == "luna_max"


def test_abstain_and_learning_feedback(monkeypatch):
    campaign(); enable(); mock_model(monkeypatch, abstain=True)
    run = strategy.executar(False)
    assert not bot.painel()["runs"]
    strategy.feedback(run["run_id"], {"feedback": "partial"})
    with bot.conectar() as c:
        snap = strategy.snapshot(c)
    assert snap["history"][0]["feedback"] == "partial"
    assert "telefone" not in json.dumps(snap) and "Fictícia" not in json.dumps(snap)


def test_plan_cannot_add_authority_or_unknown_campaign():
    snap = {"campaigns": [{"id": 1}]}
    plan = {"campaign_ids": [999], "reason": "a", "hypothesis": "b", "abstain": False}
    with pytest.raises(ValueError): strategy.validar_plano(plan, snap)
    plan["campaign_ids"] = [1,1]
    with pytest.raises(ValueError): strategy.validar_plano(plan, snap)
    plan["campaign_ids"] = [1]; plan["send"] = True
    with pytest.raises(ValueError): strategy.validar_plano(plan, snap)


def test_restart_never_repeats_calls(monkeypatch):
    campaign(); enable(); mock_model(monkeypatch)
    run = strategy.executar(False)
    with bot.conectar() as c:
        c.execute("UPDATE bot_strategy_runs SET state='running'")
        c.execute("UPDATE bot_strategy_calls SET state='running'")
    strategy.recuperar()
    assert strategy.painel()["runs"][0]["state"] == "interrupted"
    with pytest.raises(bot.Conflict): strategy.executar(False)


def approved_message():
    cid = campaign(); bot.executar(cid, False)
    with bot.conectar() as c:
        m = dict(c.execute("SELECT * FROM bot_messages WHERE step_order=0").fetchone())
    bot.agir(m["id"], "approve", {"text": m["text"]})
    return m


def email_env(monkeypatch):
    monkeypatch.setenv("PROSPECTOS_RESEND_API_KEY", "synthetic-key")
    monkeypatch.setenv("PROSPECTOS_EMAIL_FROM", "bot@example.test")
    monkeypatch.setenv("PROSPECTOS_BOT_LIVE_SENDS", "1")


def test_unconfigured_email_preview_and_live_send_blocked():
    m = approved_message()
    view = delivery.preview(m["id"], {"channel":"email", "recipient":"lead@example.test"})
    assert not view["ready"]
    with pytest.raises(bot.Conflict, match="não ativado"):
        delivery.aprovar_envio(m["id"], {"channel":"email", "recipient":"lead@example.test", "consent":True,"fingerprint":view["fingerprint"]})


def test_approved_external_send_idempotent_and_provider_acceptance(monkeypatch):
    m = approved_message(); email_env(monkeypatch)
    calls=[]
    def fake(url, **kwargs):
        calls.append((url,kwargs)); return SimpleNamespace(status_code=200, json=lambda: {"id":"synthetic-id"})
    monkeypatch.setattr(delivery.requests, "post", fake)
    # Retain worker reservation, execute it synchronously only after checking approval.
    monkeypatch.setattr(delivery.threading.Thread, "start", lambda self: None)
    body={"channel":"email","recipient":"lead@example.test"}
    view=delivery.preview(m["id"],body)
    with pytest.raises(bot.Conflict): delivery.aprovar_envio(m["id"],body)
    body.update(consent=True,fingerprint=view["fingerprint"])
    result=delivery.aprovar_envio(m["id"],body)
    delivery.enviar(result["delivery_id"]); delivery.enviar(result["delivery_id"])
    assert len(calls)==1 and calls[0][0]=="https://api.resend.com/emails"
    assert calls[0][1]["json"]["to"]==["lead@example.test"]
    assert calls[0][1]["allow_redirects"] is False
    assert delivery.painel()["deliveries"][0]["state"]=="provider_accepted"
    assert bot.painel()["counts"]["sent"]==1
    with pytest.raises(bot.Conflict): delivery.aprovar_envio(m["id"],body)


def test_unknown_delivery_no_retry_after_restart(monkeypatch):
    m=approved_message(); email_env(monkeypatch)
    monkeypatch.setattr(delivery.threading.Thread,"start",lambda self: None)
    body={"channel":"email","recipient":"lead@example.test"}
    body.update(consent=True,fingerprint=delivery.preview(m["id"],body)["fingerprint"])
    result=delivery.aprovar_envio(m["id"],body)
    delivery.recuperar(); delivery.enviar(result["delivery_id"])
    assert delivery.painel()["deliveries"][0]["state"]=="unknown"
    assert bot.painel()["counts"].get("sent",0)==0


def test_edit_revokes_queued_delivery(monkeypatch):
    m=approved_message(); email_env(monkeypatch)
    monkeypatch.setattr(delivery.threading.Thread,"start",lambda self: None)
    body={"channel":"email","recipient":"lead@example.test"}
    body.update(consent=True,fingerprint=delivery.preview(m["id"],body)["fingerprint"])
    result=delivery.aprovar_envio(m["id"],body)
    bot.agir(m["id"],"edit",{"text":"Nova versão"})
    delivery.enviar(result["delivery_id"])
    assert delivery.painel()["deliveries"][0]["state"]=="blocked"


def test_whatsapp_template_exact_preview_and_safe_destination(monkeypatch):
    m=approved_message()
    for key,value in {"PROSPECTOS_WA_TOKEN":"synthetic", "PROSPECTOS_WA_PHONE_ID":"123", "PROSPECTOS_WA_API_VERSION":"v99.0", "PROSPECTOS_WA_TEMPLATE":"approved_name", "PROSPECTOS_WA_TEMPLATE_BODY":"Apresentação: {{1}}"}.items():
        monkeypatch.setenv(key,value)
    view=delivery.preview(m["id"],{"channel":"whatsapp"})
    assert view["recipient"]=="5511999999999"
    assert view["final_text"]=="Apresentação: "+m["text"]
    assert view["payload"]["type"]=="template"
    assert not view["ready"]


def test_codex_adapter_arguments_no_paid_key_or_context_files(monkeypatch, tmp_path):
    # Exercise the actual adapter with a fake CLI, no model/network invocation.
    # Fixture blocks real calls; exercise the saved adapter with subprocess fully mocked.
    monkeypatch.setattr(strategy, "codex_binary", lambda: "codex.exe")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-inherit")
    import paths
    monkeypatch.setattr(paths, "caminho_dados", lambda *args,**kw: tmp_path/"runtime")
    calls=[]
    plan={"campaign_ids":[],"reason":"Nenhuma ação necessária","hypothesis":"Aguardar","abstain":True}
    def fake(args, **kwargs):
        calls.append((args,kwargs))
        if args[1]=="login": return SimpleNamespace(stdout="Logged in using ChatGPT",stderr="",returncode=0)
        from pathlib import Path
        Path(args[args.index("-o")+1]).write_text(json.dumps(plan),encoding="utf-8")
        return SimpleNamespace(stdout="",stderr="model: gpt-6-luna\nreasoning effort: high\ntokens used\n100",returncode=0)
    monkeypatch.setattr(strategy.subprocess,"run",fake)
    result,meta=ORIGINAL_ADAPTER({"campaigns":[],"history":[]},"gestor")
    assert result==plan and meta["tokens"]==100
    args,kwargs=calls[-1]
    assert "--ignore-user-config" in args and "--ephemeral" in args
    assert "features.shell_tool=false" in args and "mcp_servers={}" in args
    assert "OPENAI_API_KEY" not in kwargs["env"]


ORIGINAL_ADAPTER = strategy.chamar_modelo
