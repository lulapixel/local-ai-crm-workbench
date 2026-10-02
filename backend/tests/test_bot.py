"""Workflow local com SQLite isolado; nenhuma captura ou mensagem real."""
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

import bot
import db
import processar


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "CAMINHO_BANCO", tmp_path / "bot.db")
    with sqlite3.connect(db.CAMINHO_BANCO) as c:
        processar.preparar_banco(c)
        bot.preparar_banco(c)
    def forbidden(*args, **kwargs):
        pytest.fail("Captura real proibida no teste")
    monkeypatch.setattr(bot, "capturar", forbidden)


def lead(pid="p1", **changes):
    phone = "11999999999" if pid == "p1" else "119" + str(sum((i+1)*ord(ch) for i,ch in enumerate(pid))).zfill(8)
    data = dict(place_id=pid, nome="Empresa fictícia", telefone=phone, status="novo",
                site_status="sem_site", nota=5.0, num_avaliacoes=100, cidade="Recife", nicho="dentista")
    data.update(changes)
    with bot.conectar() as c:
        c.execute(f"INSERT INTO leads({','.join(data)}) VALUES({','.join('?' for _ in data)})", tuple(data.values()))


def config(**changes):
    return {"oferta": "sites locais", **changes}


def start(**changes):
    campaign = bot.criar(config(**changes))
    bot.executar(campaign["id"], background=False)
    return campaign["id"]


def message(step=0):
    with bot.conectar() as c:
        return dict(c.execute("SELECT * FROM bot_messages WHERE step_order=? ORDER BY id LIMIT 1", (step,)).fetchone())


def approve(m):
    return bot.agir(m["id"], "approve", {"text": m["text"]})


def test_preview_readonly_and_filters():
    lead()
    lead("responded", status="respondido")
    lead("no-phone", telefone="")
    lead("site", site_status="site_ok")
    lead("low", nota=4, num_avaliacoes=0)
    lead("other-city", cidade="Olinda")
    preview = bot.previa(config(cidade="Recife", nicho="dentista"))
    assert [r["place_id"] for r in preview["leads"]] == ["p1"]
    assert preview["chamadas_ia"] == 0 and not preview["captura_planejada"]
    with bot.conectar() as c:
        assert c.execute("SELECT COUNT(*) FROM bot_campaigns").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM bot_messages").fetchone()[0] == 0
        assert c.execute("SELECT status FROM leads WHERE place_id='p1'").fetchone()[0] == "novo"


@pytest.mark.parametrize("body", [None, [], {"oferta": ""}, config(limite_dia=True), config(limite_dia=31), config(score_min=-1), config(intervalo_horas=1), config(captar="yes"), config(captar=True, queries="dentistas Recife"), config(captar=True, autorizar_captura=True, queries="a\nb\nc\nd")])
def test_invalid_config(body):
    with pytest.raises(ValueError):
        bot.criar(body)


def test_queue_limit_daily_and_cross_campaign_dedup(monkeypatch):
    for n in range(4):
        lead(f"p{n}")
    cid = start(limite_dia=2)
    bot.executar(cid, background=False)
    assert bot.painel()["counts"]["pending"] == 2
    assert bot.painel()["runs"][0]["summary"]["preparadas"] == 0
    second = start(limite_dia=4)
    with bot.conectar() as c:
        assert c.execute("SELECT COUNT(*) FROM bot_targets").fetchone()[0] == 4
        assert c.execute("SELECT COUNT(*) FROM bot_messages WHERE campaign_id=? AND step_order=0", (second,)).fetchone()[0] == 2
    assert bot.painel()["counts"].get("sent", 0) == 0


def test_approval_exact_edit_invalidates_and_open_does_not_send():
    lead(); start(); m = message()
    with pytest.raises(bot.Conflict):
        bot.agir(m["id"], "approve", {"text": "outra versão"})
    with pytest.raises(bot.Conflict):
        bot.agir(m["id"], "open", {})
    approve(m)
    assert bot.agir(m["id"], "open", {})["url"].startswith("https://wa.me/5511999999999?text=")
    assert message()["state"] == "approved"
    with bot.conectar() as c:
        assert c.execute("SELECT status FROM leads").fetchone()[0] == "novo"
    bot.agir(m["id"], "edit", {"text": "Texto revisado"})
    assert message()["approved_text"] is None
    with pytest.raises(bot.Conflict):
        bot.agir(m["id"], "open", {})


def test_contact_change_and_status_change_block_actions():
    lead(); start(); m = message(); approve(m)
    with bot.conectar() as c:
        c.execute("UPDATE leads SET telefone='21988888888'")
    with pytest.raises(bot.Conflict):
        bot.agir(m["id"], "open", {})
    bot.agir(m["id"], "edit", {"text": m["text"]}); approve(message())
    with bot.conectar() as c:
        c.execute("UPDATE leads SET status='respondido'")
    with pytest.raises(bot.Conflict):
        bot.agir(m["id"], "sent", {"confirmado": True})


def test_manual_confirmation_idempotence_and_followup_timing():
    lead(); cid = start(); m = message(); approve(m)
    with pytest.raises(ValueError):
        bot.agir(m["id"], "sent", {"confirmado": "yes"})
    bot.agir(m["id"], "sent", {"confirmado": True})
    assert bot.agir(m["id"], "sent", {"confirmado": True})["ja_registrado"]
    due = message(1)["due_at"]
    assert 1.9 < (datetime.fromisoformat(due)-datetime.now(timezone.utc)).total_seconds()/86400 < 2.1
    assert message(2)["due_at"] is None
    with pytest.raises(bot.Conflict):
        approve(message(1))
    with bot.conectar() as c:
        assert c.execute("SELECT COUNT(*) FROM historico_status").fetchone()[0] == 1
        assert c.execute("SELECT status FROM leads").fetchone()[0] == "contatado"
        c.execute("UPDATE bot_messages SET due_at=? WHERE step_order=1", ((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),))
    bot.executar(cid, background=False)
    assert message(1)["state"] == "pending"
    approve(message(1)); bot.agir(message(1)["id"], "sent", {"confirmado": True})
    assert message(2)["due_at"] is not None
    with bot.conectar() as c:
        assert c.execute("SELECT follow_ups_enviados FROM leads").fetchone()[0] == 1
        c.execute("UPDATE leads SET status='respondido'")
    bot.executar(cid, background=False)
    assert message(2)["state"] == "cancelled"


def test_reject_cancels_future_without_reenrollment():
    lead(); cid = start(); m = message()
    bot.agir(m["id"], "reject", {})
    assert message(1)["state"] == "cancelled"
    bot.executar(cid, background=False)
    assert bot.painel()["counts"]["rejected"] == 1
    assert bot.painel()["counts"].get("pending", 0) == 0


def test_pause_resume_and_restart_no_retry():
    lead(); cid = start(intervalo_horas=24); m = message()
    assert bot.painel()["campaigns"][0]["next_run"]
    bot.pausar(cid)
    with pytest.raises(bot.Conflict):
        approve(m)
    assert bot.painel()["campaigns"][0]["next_run"] is None
    bot.executar(cid, background=False); approve(m)
    with bot.conectar() as c:
        c.execute("UPDATE bot_campaigns SET state='running'")
        c.execute("UPDATE bot_runs SET state='running'")
    bot.recuperar()
    campaign = bot.painel()["campaigns"][0]
    assert campaign["paused"] and campaign["state"] == "interrupted" and campaign["next_run"] is None


def test_capture_only_shortage_and_one_attempt_daily(monkeypatch):
    lead(); calls = []
    def fake(config, limit):
        calls.append(limit); lead("captured")
        return {"novos": 1}
    monkeypatch.setattr(bot, "capturar", fake)
    cid = start(limite_dia=3, captar=True, autorizar_captura=True, queries="Dentistas Recife\ndentistas recife")
    assert calls == [2]
    assert bot.painel()["counts"]["pending"] == 2
    bot.executar(cid, background=False)
    assert calls == [2]


def test_capture_failure_preserves_local_queue_and_disarms_schedule(monkeypatch):
    lead()
    def fail(*args):
        raise bot.Conflict("Fonte indisponível")
    monkeypatch.setattr(bot, "capturar", fail)
    start(captar=True, autorizar_captura=True, queries="dentistas Recife", intervalo_horas=24)
    overview = bot.painel()
    assert overview["counts"]["pending"] == 1
    assert overview["runs"][0]["state"] == "error"
    assert overview["campaigns"][0]["next_run"] is None


def test_single_running_campaign_and_thread_start_failure(monkeypatch):
    cid = bot.criar(config())["id"]
    with bot.conectar() as c:
        c.execute("UPDATE bot_campaigns SET state='running'")
    with pytest.raises(bot.Conflict):
        bot.executar(cid)
    bot.recuperar()
    def fail(self):
        raise RuntimeError("thread unavailable")
    monkeypatch.setattr(bot.threading.Thread, "start", fail)
    with pytest.raises(bot.Conflict):
        bot.executar(cid)
    assert bot.painel()["campaigns"][0]["state"] == "error"


def test_bot_api_contract_and_csrf(monkeypatch):
    import app as app_module
    with app_module.app.test_client() as client:
        assert client.get("/api/bot").status_code == 200
        assert client.post("/api/bot/preview", json=[]).status_code == 400
        assert client.post("/api/bot/campaigns", json=config(), headers={"Origin": "https://evil.example"}).status_code == 403
        token = client.get("/api/csrf-token").get_json()["csrf_token"]
        headers = {"Origin": "http://localhost:5000", "X-CSRF-Token": token}
        assert client.post("/api/bot/campaigns", json=config(), headers={"Origin": "http://localhost:5000"}).status_code == 403
        response = client.post("/api/bot/campaigns", json=config(), headers=headers)
        assert response.status_code == 201
        cid = response.get_json()["id"]
        monkeypatch.setattr(bot, "executar", lambda id: {"run_id": 99})
        assert client.post(f"/api/bot/campaigns/{cid}/run", json={}, headers=headers).status_code == 202
        assert client.post(f"/api/bot/campaigns/{cid}/pause", json={}, headers=headers).status_code == 200
        assert client.post("/api/bot/messages/999/approve", json={}, headers=headers).status_code == 400


def test_existing_outreach_blocks_bot_and_bot_blocks_new_outreach():
    from outreach.service import obter_ou_gerar_pacote, aprovar_pacote_conversao
    from outreach.sequences_service import iniciar_sequencia, SequenceConflictError
    lead("legacy")
    pack = obter_ou_gerar_pacote("legacy")
    aprovar_pacote_conversao(pack["id"])
    iniciar_sequencia(pack["id"])
    lead("bot-owned")
    start()
    with bot.conectar() as c:
        assert [r[0] for r in c.execute("SELECT place_id FROM bot_targets")] == ["bot-owned"]
    other = obter_ou_gerar_pacote("bot-owned")
    aprovar_pacote_conversao(other["id"])
    with pytest.raises(SequenceConflictError, match="inscrito no bot"):
        iniciar_sequencia(other["id"])
    with bot.conectar() as c:
        assert c.execute("SELECT COUNT(*) FROM outreach_sequences").fetchone()[0] == 1


def test_reject_followup_clears_legacy_agenda_and_scheduler_only_prepares(monkeypatch):
    lead(); cid = start(intervalo_horas=24); m = message(); approve(m)
    bot.agir(m["id"], "sent", {"confirmado": True})
    with bot.conectar() as c:
        c.execute("UPDATE bot_messages SET due_at=? WHERE step_order=1", ((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),))
        c.execute("UPDATE bot_campaigns SET next_run=?", ((datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(),))
    calls = []
    def run_sync(id, **kwargs):
        calls.append(id); bot.rodar(id, 1)
    monkeypatch.setattr(bot, "executar", run_sync)
    bot.tick()
    assert calls == [cid] and message(1)["state"] == "pending"
    assert message(1)["sent_at"] is None
    bot.agir(message(1)["id"], "reject", {})
    with bot.conectar() as c:
        assert c.execute("SELECT proximo_followup FROM leads").fetchone()[0] is None
    assert message(2)["state"] == "cancelled"


def test_automatic_run_cannot_resume_human_pause():
    lead(); cid = start(); bot.pausar(cid)
    with pytest.raises(bot.Conflict, match="pausa humana"):
        bot.executar(cid, background=False, resume=False)
    assert bot.painel()["campaigns"][0]["paused"] == 1
