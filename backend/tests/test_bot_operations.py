"""Synthetic contact identity, outcomes, noop decisions and runtime visibility."""
import sqlite3
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
import bot
import bot_operations as ops
import bot_strategy as strategy
import bot_delivery as delivery
import processar
import db


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path/"operations.db")
    with sqlite3.connect(db.CAMINHO_BANCO) as c:
        processar.preparar_banco(c); bot.preparar_banco(c); strategy.preparar_banco(c); delivery.preparar_banco(c)
    monkeypatch.setattr(bot, "_scheduler_thread", None)
    monkeypatch.setattr(bot, "_scheduler_last_tick", None)
    monkeypatch.setattr(bot, "_scheduler_error", None)
    def forbidden(*args, **kwargs): pytest.fail("Real network/model prohibited")
    monkeypatch.setattr(bot, "capturar", forbidden)
    monkeypatch.setattr(strategy, "chamar_modelo", forbidden)
    monkeypatch.setattr(delivery.requests, "post", forbidden)


def lead(pid="p1", phone="11999999999", status="novo"):
    with bot.conectar() as c:
        c.execute("INSERT INTO leads(place_id,nome,telefone,status,site_status,nota,num_avaliacoes) VALUES(?, 'Synthetic', ?, ?, 'sem_site',5,100)", (pid,phone,status))


def run():
    cid=bot.criar({"oferta":"sites locais"})["id"]
    bot.executar(cid,False)
    return cid


def sent():
    lead(); run()
    with bot.conectar() as c: m=dict(c.execute("SELECT * FROM bot_messages WHERE step_order=0").fetchone())
    bot.agir(m["id"],"approve",{"text":m["text"]})
    bot.agir(m["id"],"sent",{"confirmado":True})
    return m


def test_normalized_phone_not_place_id_defines_duplicate():
    lead(); lead("p2","+55 (11) 99999-9999")
    run(); run()
    assert bot.painel()["counts"]["pending"]==1
    with bot.conectar() as c: assert c.execute("SELECT COUNT(*) FROM bot_targets").fetchone()[0]==1


def test_previous_crm_contact_blocks_new_id():
    lead("old",status="recusou"); lead()
    run()
    assert not bot.painel()["counts"]


def test_new_duplicate_after_approval_blocks_release():
    lead(); run()
    with bot.conectar() as c: m=dict(c.execute("SELECT * FROM bot_messages WHERE step_order=0").fetchone())
    bot.agir(m["id"],"approve",{"text":m["text"]})
    lead("duplicate",status="contatado")
    with pytest.raises(bot.Conflict,match="duplicidade"): bot.agir(m["id"],"open",{})


@pytest.mark.parametrize("outcome,status",[("replied","respondeu"),("won","fechou"),("declined","recusou"),("do_not_contact","ignorado")])
def test_outcome_confirmation_atomic_cancellation_and_idempotence(outcome,status):
    sent()
    with pytest.raises(ValueError): ops.registrar("p1",{"outcome":outcome})
    ops.registrar("p1",{"outcome":outcome,"confirmed":True})
    assert ops.registrar("p1",{"outcome":outcome,"confirmed":True})["already_recorded"]
    with bot.conectar() as c:
        assert tuple(c.execute("SELECT status,proximo_followup FROM leads").fetchone())==(status,None)
        assert c.execute("SELECT COUNT(*) FROM bot_contact_events").fetchone()[0]==1
        assert c.execute("SELECT COUNT(*) FROM bot_messages WHERE state='scheduled'").fetchone()[0]==0


def test_suppression_survives_recapture_and_lead_deletion():
    sent(); lead("same_phone")
    ops.registrar("p1",{"outcome":"do_not_contact","confirmed":True})
    with bot.conectar() as c:
        assert c.execute("SELECT status FROM leads WHERE place_id='same_phone'").fetchone()[0]=="ignorado"
        c.execute("DELETE FROM leads")
    lead("recaptured"); run()
    assert not bot.painel()["counts"].get("pending",0)
    assert ops.painel()["metrics"]["suppressed"]==1


def test_queued_send_cancelled_by_manual_response():
    lead(); run()
    with bot.conectar() as c:
        mid=c.execute("SELECT id FROM bot_messages WHERE step_order=0").fetchone()[0]
        c.execute("INSERT INTO bot_deliveries(message_id,channel,recipient,final_text,payload_json,state,approved_at) VALUES(?,'email','lead@example.test','text','{}','queued',?)",(mid,bot.agora()))
    ops.registrar("p1",{"outcome":"do_not_contact","confirmed":True})
    with bot.conectar() as c: did=c.execute("SELECT id FROM bot_deliveries").fetchone()[0]
    delivery.enviar(did)
    assert delivery.painel()["deliveries"][0]["state"]=="blocked"


def test_in_flight_is_disclosed_not_claimed_cancelled():
    sent()
    with bot.conectar() as c:
        mid=c.execute("SELECT id FROM bot_messages WHERE step_order=0").fetchone()[0]
        c.execute("INSERT INTO bot_deliveries(message_id,channel,recipient,final_text,payload_json,state,approved_at) VALUES(?,'email','lead@example.test','text','{}','sending',?)",(mid,bot.agora()))
    result=ops.registrar("p1",{"outcome":"do_not_contact","confirmed":True})
    assert result["in_flight"] and "iniciada" in result["note"]


def test_empty_or_full_queue_skips_model(monkeypatch):
    lead(); run()
    strategy.configurar({"enabled":True})
    monkeypatch.setattr(strategy,"now",lambda:datetime(2026,9,30,15,0,tzinfo=strategy.BRASILIA))
    assert strategy.executar(False)["skipped"]
    assert strategy.painel()["used_today"]==0
    with bot.conectar() as c: assert c.execute("SELECT COUNT(*) FROM bot_strategy_runs").fetchone()[0]==0


def test_due_followup_is_useful_but_future_is_not():
    sent()
    with bot.conectar() as c:
        assert not strategy.snapshot(c)["campaigns"]
        c.execute("UPDATE bot_messages SET due_at=? WHERE step_order=1",((datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat(),))
        assert strategy.snapshot(c)["campaigns"][0]["retornos_vencidos"]==1


def test_heartbeat_states_and_unknown_cost(monkeypatch):
    assert ops.painel()["scheduler"]["state"]=="stopped"
    monkeypatch.setattr(bot,"_scheduler_thread",SimpleNamespace(is_alive=lambda:True))
    assert ops.painel()["scheduler"]["state"]=="starting"
    monkeypatch.setattr(bot,"_scheduler_last_tick",bot.agora())
    assert ops.painel()["scheduler"]["state"]=="active"
    monkeypatch.setattr(bot,"_scheduler_last_tick",(datetime.now(timezone.utc)-timedelta(minutes=3)).isoformat())
    assert ops.painel()["scheduler"]["state"]=="attention"
    assert ops.painel()["metrics"]["monetary_cost"] is None


def test_suppression_blocks_central_even_under_new_id():
    from outreach.service import obter_ou_gerar_pacote, aprovar_pacote_conversao
    from outreach.sequences_service import iniciar_sequencia, SequenceConflictError
    sent(); ops.registrar("p1",{"outcome":"do_not_contact","confirmed":True})
    lead("recapture")
    pack=obter_ou_gerar_pacote("recapture"); aprovar_pacote_conversao(pack["id"])
    with pytest.raises(SequenceConflictError,match="bloqueada"): iniciar_sequencia(pack["id"])


def test_read_api_and_outcome_keep_csrf_boundary():
    import app
    sent()
    with app.app.test_client() as client:
        assert client.get('/api/bot/operations').status_code==200
        url='/api/bot/contacts/p1/outcome'
        body={'outcome':'replied','confirmed':True}
        assert client.post(url,json=body,headers={'Origin':'https://evil.example'}).status_code==403
        token=client.get('/api/csrf-token').get_json()['csrf_token']
        assert client.post(url,json=body,headers={'Origin':'http://localhost:5000','X-CSRF-Token':token}).status_code==200
