"""Operational read model and human-recorded outcomes; no provider calls."""
from datetime import datetime, timezone
import os

from flask import Blueprint, request

import bot

bp = Blueprint("bot_operations", __name__)
OUTCOMES = {"replied": "respondeu", "won": "fechou", "declined": "recusou", "do_not_contact": "ignorado"}


def preparar_banco(c):
    c.executescript("""
        CREATE TABLE IF NOT EXISTS bot_suppressions (
            contact TEXT PRIMARY KEY, reason TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bot_contact_events (
            id INTEGER PRIMARY KEY, place_id TEXT NOT NULL, outcome TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'human', created_at TEXT NOT NULL
        );
    """)


def contato_bloqueado(c, place_id):
    if not c.execute("SELECT 1 FROM sqlite_master WHERE name='bot_suppressions'").fetchone():
        return False
    row = c.execute("SELECT telefone FROM leads WHERE place_id=?", (place_id,)).fetchone()
    contact = bot._contato(dict(row)) if row else None
    return bool(contact and c.execute("SELECT 1 FROM bot_suppressions WHERE contact=?", (contact,)).fetchone())


def registrar(place_id, body):
    if not isinstance(body, dict) or body.get("outcome") not in OUTCOMES or body.get("confirmed") is not True:
        raise ValueError("Escolha um resultado observado e confirme o registro manual.")
    outcome = body["outcome"]
    status = OUTCOMES[outcome]
    with bot.conectar() as c:
        c.execute("BEGIN IMMEDIATE")
        row = c.execute("SELECT l.* FROM leads l JOIN bot_targets t ON t.place_id=l.place_id WHERE l.place_id=?", (place_id,)).fetchone()
        if not row:
            raise ValueError("Contato do bot não encontrado.")
        contact = bot._contato(dict(row))
        if outcome == "do_not_contact" and not contact:
            raise bot.Conflict("Corrija o telefone antes de bloquear a identidade do contato.")
        previous = c.execute("SELECT outcome FROM bot_contact_events WHERE place_id=? ORDER BY id DESC LIMIT 1", (place_id,)).fetchone()
        if previous and previous[0] == outcome and row["status"] == status:
            return {"ok": True, "already_recorded": True}
        if outcome == "do_not_contact":
            c.execute("INSERT OR IGNORE INTO bot_suppressions VALUES(?, 'Pedido registrado pelo operador', ?)", (contact, bot.agora()))
            ids = [r["place_id"] for r in c.execute("SELECT place_id,telefone FROM leads") if bot._contato(dict(r)) == contact]
        else:
            ids = [place_id]
        in_flight = False
        for pid in ids:
            old = c.execute("SELECT status FROM leads WHERE place_id=?", (pid,)).fetchone()[0]
            c.execute("UPDATE leads SET status=?,proximo_followup=NULL,atualizado_em=? WHERE place_id=?", (status, bot.agora(), pid))
            if old != status:
                c.execute("INSERT INTO historico_status(place_id,status_anterior,status_novo,alterado_em) VALUES(?,?,?,?)", (pid, old, status, bot.agora()))
            c.execute("UPDATE bot_messages SET state='cancelled' WHERE place_id=? AND state IN ('pending','approved','scheduled')", (pid,))
            c.execute("UPDATE outreach_sequence_steps SET status='cancelled',cancelled_at=? WHERE status IN ('pending','ready') AND sequence_id IN (SELECT id FROM outreach_sequences WHERE place_id=? AND status IN ('active','paused'))", (bot.agora(), pid))
            c.execute("UPDATE outreach_sequences SET status='cancelled',stopped_at=?,stop_reason=?,updated_at=? WHERE place_id=? AND status IN ('active','paused')", (bot.agora(), outcome, bot.agora(), pid))
            if c.execute("SELECT 1 FROM sqlite_master WHERE name='bot_deliveries'").fetchone():
                in_flight = in_flight or bool(c.execute("SELECT 1 FROM bot_deliveries d JOIN bot_messages m ON m.id=d.message_id WHERE m.place_id=? AND d.state='sending'", (pid,)).fetchone())
                c.execute("UPDATE bot_deliveries SET state='blocked',error='Contato encerrado pelo operador antes da transmissão.' WHERE state='queued' AND message_id IN (SELECT id FROM bot_messages WHERE place_id=?)", (pid,))
        c.execute("INSERT INTO bot_contact_events(place_id,outcome,created_at) VALUES(?,?,?)", (place_id, outcome, bot.agora()))
    return {"ok": True, "already_recorded": False, "in_flight": in_flight,
            "note": "Registro salvo; uma requisição já iniciada pode terminar." if in_flight else "Registro salvo; próximos contatos do bot cancelados."}


def painel():
    import bot_strategy
    import bot_delivery
    import research_desk
    stamp = bot._scheduler_last_tick
    alive = bool(bot._scheduler_thread and bot._scheduler_thread.is_alive())
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(stamp)).total_seconds() if stamp else None
    scheduler = {"state": "active" if alive and age is not None and age < 90 and not bot._scheduler_error else "attention" if alive and (bot._scheduler_error or age is not None) else "starting" if alive else "stopped",
                 "last_tick": stamp, "error": bot._scheduler_error}
    with bot.conectar() as c:
        counts = {r[0]: r[1] for r in c.execute("SELECT state,COUNT(*) FROM bot_messages GROUP BY state")}
        useful = len(bot_strategy.snapshot(c)["campaigns"])
        outcomes = {r[0]: r[1] for r in c.execute("SELECT l.status,COUNT(*) FROM leads l JOIN bot_targets t ON t.place_id=l.place_id GROUP BY l.status")}
        contacts = [dict(r) for r in c.execute("""SELECT l.place_id,l.nome,l.telefone,l.status,MAX(m.sent_at) AS last_sent
            FROM leads l JOIN bot_targets t ON t.place_id=l.place_id JOIN bot_messages m ON m.place_id=l.place_id
            WHERE m.state='sent' GROUP BY l.place_id ORDER BY last_sent DESC LIMIT 50""")]
        uncertain = c.execute("SELECT COUNT(*) FROM bot_deliveries WHERE state='unknown'").fetchone()[0]
        suppressed = c.execute("SELECT COUNT(*) FROM bot_suppressions").fetchone()[0]
        metrics = {"prepared": counts.get("pending",0)+counts.get("approved",0), "sent": counts.get("sent",0),
                   "replied": outcomes.get("respondeu",0), "won": outcomes.get("fechou",0), "suppressed": suppressed,
                   "useful_campaigns": useful, "uncertain": uncertain, "monetary_cost": None}
        config = bot_strategy.settings(c)
        research = research_desk.summary(c)
    actions = []
    if research["total"]:
        actions.append({"title": "Trabalhar a pesquisa local", "detail": f"{research['total']} candidato(s) em acompanhamento; {research['due']} retorno(s) vencidos. Qualificação e aprovação continuam individuais.", "href": "/pesquisa", "level": "normal"})
    if uncertain:
        actions.append({"title":"Conferir envios incertos", "detail":f"{uncertain} tentativa(s) precisam de consulta ao provedor antes de repetir.", "href":"#bot-channels", "level":"attention"})
    if metrics["prepared"]:
        actions.append({"title":"Revisar contatos preparados", "detail":f"{metrics['prepared']} texto(s) aguardam sua decisão individual.", "href":"#bot-review", "level":"normal"})
    if config["enabled"] and scheduler["state"] != "active":
        actions.append({"title":"Conferir o relógio da automação", "detail":"Gestão habilitada não garante execução: abra o backend normal e confira o próximo ciclo.", "href":"#bot-strategy", "level":"attention"})
    if useful:
        actions.append({"title":"Preparar campanhas com trabalho disponível", "detail":f"{useful} campanha(s) com saldo e oportunidades, retornos ou captura autorizada.", "href":"#bot-config", "level":"normal"})
    if not actions:
        actions.append({"title":"Ensaiar uma campanha", "detail":"Defina sua oferta e confira a base antes de executar.", "href":"#bot-config", "level":"normal"})
    return {"scheduler":scheduler, "metrics":metrics, "research":research, "actions":actions, "contacts":contacts,
            "demo":os.environ.get("PROSPECTOS_TEST_MODE","").lower() in ('1','true','yes'),
            "channels":bot_delivery.readiness(), "measurement_note":"Contagens do CRM; não demonstram entrega, receita ou causalidade."}


@bp.get("/api/bot/operations")
def get_operations():
    return bot._responder(painel)


@bp.post("/api/bot/contacts/<path:place_id>/outcome")
def post_outcome(place_id):
    return bot._responder(registrar, place_id, request.get_json(silent=True))
