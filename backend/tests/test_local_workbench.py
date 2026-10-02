"""Isolated session planning; never execute providers or transmissions."""
import sqlite3
from datetime import datetime, timezone

import pytest
import bot
import bot_delivery
import bot_strategy
import db
import local_workbench as workbench
import processar

AT = datetime(2026,9,30,15,0,tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(db,"CAMINHO_BANCO",tmp_path/"workbench.db")
    with sqlite3.connect(db.CAMINHO_BANCO) as c:
        processar.preparar_banco(c)
        bot.preparar_banco(c)
        bot_strategy.preparar_banco(c)
        bot_delivery.preparar_banco(c)
    def forbidden(*args, **kwargs):
        pytest.fail("No real provider/model/send allowed")
    monkeypatch.setattr(bot,"capturar",forbidden)
    monkeypatch.setattr(bot_strategy,"chamar_modelo",forbidden)
    monkeypatch.setattr(bot_delivery.requests,"post",forbidden)


def lead(pid="p1", phone="11999999999", status="novo", due=None, city="Recife", niche="Salão"):
    with bot.conectar() as c:
        c.execute("""INSERT INTO leads(place_id,nome,telefone,status,site_status,nota,num_avaliacoes,proximo_followup,cidade,nicho)
            VALUES(?,?,?,?,'sem_site',5,100,?,?,?)""",(pid,"Synthetic "+pid,phone,status,due,city,niche))


def test_empty_returns_direction_and_unknown_cost():
    plan=workbench.planejar(at=AT)
    assert not plan["actions"]
    assert plan["total_leads"]==0
    assert plan["model_calls"]==0 and plan["monetary_cost"] is None
    assert not plan["strategy"]["enabled"]


def test_read_planning_keeps_all_business_tables_unchanged():
    lead()
    with bot.conectar() as c:
        before=list(c.iterdump())
    plan=workbench.planejar(at=AT)
    with bot.conectar() as c:
        assert list(c.iterdump())==before
    assert plan["actions"][0]["kind"]=="opportunity"
    assert "não chance de venda" in plan["actions"][0]["reason"]
    assert plan["actions"][0]["href"]=="/leads?lead=p1"


def test_commercial_and_due_tasks_precede_new_contacts_and_fit_budget():
    lead("new","11999999991")
    lead("due","11999999992","contatado","2026-09-29")
    lead("response","11999999993","respondeu")
    lead("future","11999999994","contatado","2026-10-10")
    plan=workbench.planejar(15,at=AT)
    assert [a["kind"] for a in plan["actions"]]==["conversation","followup","opportunity"]
    assert plan["estimated_minutes"]==15
    assert all(a["lead_id"]!="future" for a in plan["actions"])


def test_duplicates_suppressed_and_active_identity_not_suggested():
    lead("a");lead("duplicate")
    lead("blocked","11988888888")
    lead("active","11977777777","contatado")
    lead("recapture","11977777777")
    with bot.conectar() as c:
        contact=bot._contato(dict(c.execute("SELECT * FROM leads WHERE place_id='blocked'").fetchone()))
        c.execute("INSERT INTO bot_suppressions VALUES(?, 'synthetic', ?)",(contact,bot.agora()))
    plan=workbench.planejar(at=AT)
    assert len(plan["actions"])==1
    assert plan["quality"]["duplicate_contact"]==2
    assert plan["quality"]["suppressed"]==1


def test_uncertain_delivery_is_warning_never_retry_action():
    lead()
    cid=bot.criar({"oferta":"synthetic"})["id"]
    bot.executar(cid,False)
    with bot.conectar() as c:
        mid=c.execute("SELECT id FROM bot_messages WHERE step_order=0").fetchone()[0]
        c.execute("""INSERT INTO bot_deliveries(message_id,channel,recipient,final_text,payload_json,state,approved_at)
            VALUES(?,'email','synthetic@example.invalid','text','{}','unknown',?)""",(mid,bot.agora()))
    # A second record with the same phone must not bypass the uncertainty gate.
    lead("same-contact", status="contatado", due="2026-09-01T09:00:00-03:00")
    plan=workbench.planejar(at=AT)
    assert not plan["actions"]
    assert plan["quality"]["uncertain_delivery"]==2


def test_prepared_bot_message_routes_to_review_instead_of_duplicate_contact():
    lead()
    cid=bot.criar({"oferta":"synthetic"})["id"]
    bot.executar(cid,False)
    plan=workbench.planejar(at=AT)
    assert len(plan["actions"])==1
    assert plan["actions"][0]["kind"]=="review"
    assert plan["actions"][0]["href"]=="/bot#bot-review"


def test_filters_literal_and_malformed_reminder_is_not_due():
    lead("one",due="invalid")
    lead("two","11999999992",city="Olinda",niche="Clínica")
    plan=workbench.planejar(city="RECIFE",niche="salão",at=AT)
    assert [a["lead_id"] for a in plan["actions"]]==["one"]
    assert not workbench.planejar(niche="%",at=AT)["actions"]


@pytest.mark.parametrize("options",[{"minutes":1},{"minutes":True},{"minimum":101},{"city":"x"*101}])
def test_invalid_planning_inputs(options):
    with pytest.raises(ValueError):workbench.planejar(**options)


def test_scan_limit_is_visible_and_response_is_bounded(monkeypatch):
    lead("a");lead("b","11999999992")
    monkeypatch.setattr(workbench,"SCAN_LIMIT",1)
    plan=workbench.planejar(at=AT)
    assert plan["limited"] and plan["scanned"]==1 and len(plan["actions"])==1


def test_api_health_has_no_paths_or_credentials_and_validates_input(monkeypatch):
    import app
    monkeypatch.setenv("PROSPECTOS_DESKTOP_INSTANCE","synthetic-instance")
    with app.app.test_client() as client:
        health=client.get("/api/system/health").get_json()
        assert health["service"]=="prospectos" and health["ready"]
        assert health["instance"]=="synthetic-instance"
        assert not any(key in health for key in ("path","token","credentials","database"))
        assert client.get("/api/workbench/plan").status_code==200
        assert client.get("/api/workbench/plan?minutes=no").status_code==400


def test_disabled_scheduler_does_not_start_thread(monkeypatch):
    monkeypatch.setenv("PROSPECTOS_AUTOMATION_DISABLED","1")
    monkeypatch.setattr(bot,"_scheduler_started",False)
    monkeypatch.setattr(bot,"_scheduler_thread",None)
    bot.iniciar_scheduler()
    assert not bot._scheduler_started and bot._scheduler_thread is None


def test_ineligible_duplicate_does_not_hide_eligible_contact():
    lead("a-ineligible");lead("b-eligible")
    with bot.conectar() as c:
        c.execute("UPDATE leads SET site_status='desconhecido' WHERE place_id='a-ineligible'")
    plan=workbench.planejar(at=AT)
    assert [a["lead_id"] for a in plan["actions"]]==["b-eligible"]


def test_malformed_rating_does_not_break_other_actions():
    lead("malformed")
    with bot.conectar() as c:
        c.execute("UPDATE leads SET nota='invalid' WHERE place_id='malformed'")
    plan=workbench.planejar(minimum=0,at=AT)
    assert "não validada" in plan["actions"][0]["reason"]


def test_due_dates_compare_instants_across_timezones():
    lead("early","11900000001","contatado","2026-09-30T09:00:00-03:00")
    lead("later","11900000002","contatado","2026-09-30T11:00:00-02:00")
    assert [a["lead_id"] for a in workbench.planejar(at=AT)["actions"]]==["early","later"]
