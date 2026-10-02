"""Local planning/readiness: read-only CRM queries, no models or transmissions."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import os
import math
import shutil
from urllib.parse import urlencode

from flask import Blueprint, jsonify, request

import bot
import bot_delivery
import bot_strategy
import db
import pilot_review
import research_desk
import management
from rotas_leads import SQL_SCORE

bp = Blueprint("local_workbench", __name__)
BRASILIA = timezone(timedelta(hours=-3))
SCAN_LIMIT = 5000
MINUTES = {15, 30, 60}


@bp.get("/api/workbench/pilots")
def get_pilots():
    response = jsonify(pilot_review.listar())
    response.headers["Cache-Control"] = "no-store"
    return response


def _instant(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        # Legacy date-only/local reminders use the business timezone.
        return parsed.replace(tzinfo=BRASILIA) if parsed.tzinfo is None else parsed
    except (ValueError, TypeError):
        return None


def _href(lead):
    return "/leads?" + urlencode({"lead": lead["place_id"]})


def _rating(value):
    try:
        number = float(value)
        return f"{number:g}" if math.isfinite(number) and 0 <= number <= 5 else "não validada"
    except (TypeError, ValueError):
        return "não validada"


def planejar(minutes=30, city="", niche="", minimum=60, at=None):
    if type(minutes) is not int or minutes not in MINUTES:
        raise ValueError("Escolha uma sessão de 15, 30 ou 60 minutos.")
    if type(minimum) is not int or not 0 <= minimum <= 100:
        raise ValueError("A pontuação mínima deve estar entre 0 e 100.")
    if any(not isinstance(v, str) or len(v) > 100 for v in (city, niche)):
        raise ValueError("Cidade e nicho devem ter até 100 caracteres.")
    stamp = at or datetime.now(timezone.utc)
    today = stamp.astimezone(BRASILIA).date().isoformat()
    actions, warnings = [], Counter()
    with bot.conectar() as c:
        counts = dict(c.execute("SELECT status,COUNT(*) FROM leads GROUP BY status"))
        total = sum(counts.values())
        ig_total = c.execute("SELECT COUNT(*) FROM instagram_leads").fetchone()[0]
        # Fixed cap and stable order; the response exposes the sampling limit.
        rows = [dict(row) for row in c.execute(f"""SELECT *,ROUND({SQL_SCORE}) AS priority_score FROM leads
            ORDER BY CASE WHEN status='respondeu' THEN 0
                WHEN proximo_followup IS NOT NULL AND status='contatado' THEN 1
                WHEN status='novo' THEN 2 ELSE 3 END, priority_score DESC, place_id LIMIT ?""", (SCAN_LIMIT,))]
        blocked = bot._contatos_bloqueados(c)
        occupied = bot._contatos_ocupados(c)
        targets = {row[0] for row in c.execute("SELECT place_id FROM bot_targets")}
        sequences = {row[0] for row in c.execute("SELECT place_id FROM outreach_sequences WHERE status IN ('active','paused')")}
        review = {row["place_id"]: dict(row) for row in c.execute("""SELECT place_id,
            MIN(id) AS message_id, COUNT(*) AS count FROM bot_messages
            WHERE state IN ('pending','approved') GROUP BY place_id""")}
        uncertain_rows = [dict(row) for row in c.execute("""SELECT DISTINCT l.* FROM bot_deliveries d
            JOIN bot_messages m ON m.id=d.message_id JOIN leads l ON l.place_id=m.place_id
            WHERE d.state IN ('unknown','sending')""")]
        uncertain = {row["place_id"] for row in uncertain_rows}
        uncertain_contacts = {bot._contato(row) for row in uncertain_rows} - {None, ""}
        cfg = bot_strategy.settings(c)
        strategy_used = c.execute("SELECT COUNT(*) FROM bot_strategy_calls WHERE day=?", (today,)).fetchone()[0]
        campaigns = c.execute("SELECT COUNT(*) FROM bot_campaigns WHERE paused=0").fetchone()[0]
        useful = len(bot_strategy.snapshot(c)["campaigns"])
        seen_actions = set()
        for lead in rows:
            if city and (lead.get("cidade") or "").casefold() != city.strip().casefold():
                continue
            if niche and niche.strip().casefold() not in (lead.get("nicho") or lead.get("categoria") or "").casefold():
                continue
            pid, status = lead["place_id"], lead["status"]
            contact = bot._contato(lead)
            if status in ("fechou", "recusou", "ignorado"):
                continue
            if not contact:
                warnings["missing_contact"] += 1
            if not lead.get("nome") or not lead["nome"].strip():
                warnings["missing_name"] += 1
            if lead.get("site_status") not in ("sem_site", "site_ruim", "site_ok"):
                warnings["unknown_site"] += 1
            if contact in blocked:
                warnings["suppressed"] += 1
                continue
            # Never suggest retrying uncertain/in-flight transmissions.
            if pid in uncertain or contact in uncertain_contacts:
                warnings["uncertain_delivery"] += 1
                continue
            key = contact or "id:" + pid
            if key in seen_actions:
                warnings["duplicate_contact"] += 1
                continue
            kind, reason, duration, href, priority = None, "", 0, _href(lead), 0
            due = _instant(lead.get("proximo_followup"))
            if status == "respondeu":
                kind, reason, duration, priority = "conversation", "Resposta registrada: revise a conversa e defina o próximo passo comercial.", 6, 0
            elif pid in review:
                kind, reason, duration, href, priority = "review", "Texto preparado pelo bot aguardando decisão; use a revisão existente.", 3, "/bot#bot-review", 1
            elif status == "contatado" and due and due <= stamp:
                kind, reason, duration, priority = "followup", "Retorno vencido; confira a conversa antes de uma nova abordagem.", 4, 2
                if pid in targets or pid in sequences:
                    href = "/bot#bot-review" if pid in targets else "/outreach/hoje"
            elif status == "novo" and contact:
                if contact in occupied or pid in targets or pid in sequences:
                    warnings["duplicate_contact"] += 1
                    continue
                if lead["priority_score"] >= minimum and lead.get("site_status") in ("sem_site", "site_ruim") and lead.get("nome"):
                    kind, duration, priority = "opportunity", 5, 3
                    site = "sem site próprio" if lead["site_status"] == "sem_site" else "site com melhorias"
                    reason = f"{site}; nota {_rating(lead.get('nota'))} e {lead.get('num_avaliacoes') or 0} avaliações. Pontuação heurística, não chance de venda."
            if kind:
                seen_actions.add(key)
                actions.append({"id": kind + ":" + pid, "kind": kind, "lead_id": pid,
                    "name": lead.get("nome") or "Contato sem nome", "city": lead.get("cidade") or "",
                    "niche": lead.get("nicho") or lead.get("categoria") or "", "reason": reason,
                    "score": int(lead["priority_score"]), "estimated_minutes": duration,
                    "href": href, "priority": priority, "due_at": due.isoformat() if due else None})
        research = research_desk.summary(c)
        if research["total"]:
            candidates = c.execute("SELECT * FROM research_candidates WHERE state NOT IN ('won','closed','suppressed') ORDER BY id LIMIT ?", (SCAN_LIMIT,)).fetchall()
            research_context = research_desk.contact_context(c)
            for raw in candidates:
                candidate = dict(raw)
                if city and candidate["city"].casefold() != city.strip().casefold():
                    continue
                if niche and niche.strip().casefold() not in candidate["segment"].casefold():
                    continue
                next_step = research_desk.next_action(candidate,
                    research_desk.qualification_blockers(c, candidate, research_context),
                    research_desk.blockers(c, candidate, research_context), today)
                if not next_step["actionable"]:
                    continue
                state = candidate["state"]
                due = _instant(candidate["followup_on"])
                if state == "replied":
                    kind, reason, duration, priority = "conversation", "Resposta registrada: continue a conversa e confirme a necessidade.", 6, 0
                elif state == "contacted" and due and due <= stamp:
                    kind, reason, duration, priority = "followup", "Retorno manual agendado. Revise a conversa antes de preparar outro texto.", 4, 2
                elif state == "qualified" and next_step["kind"] == "review":
                    kind, reason, duration, priority = "review", "Qualificação registrada: revise o texto e decida se aprova esta versão.", 3, 1
                elif state == "approved" and next_step["kind"] == "manual_contact":
                    kind, reason, duration, priority = "manual_contact", "Texto aprovado. Faça o contato manual somente se autorizado e registre o que realmente ocorreu.", 5, 3
                else:
                    kind, reason, duration, priority = "research", "Conferir evidências e contato; qualificação e aprovação continuam humanas.", 5, 4
                    if not research_desk._contact(candidate["phone"]):
                        priority = 5
                if next_step["kind"] == "resolve_contact":
                    kind, reason, duration, priority = "research", "Contato não está pronto: confira bloqueios e duplicidades antes de qualquer abordagem.", 3, 4
                reason = next_step["reason"]
                actions.append({"id": f"research:{candidate['id']}", "lead_id": f"research:{candidate['id']:010d}",
                    "kind": kind, "name": candidate["name"], "city": candidate["city"], "niche": candidate["segment"],
                    "reason": reason, "score": 0, "estimated_minutes": duration, "href": f"/pesquisa?candidate={candidate['id']}",
                    "priority": priority, "due_at": due.isoformat() if due else None})
        profile = management.settings(c)["profile"]
        preferred_city = profile["city"].strip().casefold()
        actions = [management.decorate_action(action) for action in actions]
        # Personal city preference breaks ties only; responses/due work stay first.
        actions.sort(key=lambda row: (row["priority"], _instant(row["due_at"]).timestamp() if row["due_at"] else 0,
            bool(preferred_city and row["city"].strip().casefold() != preferred_city), -row["score"], row["lead_id"]))
        selected, elapsed = [], 0
        for action in actions:
            if elapsed + action["estimated_minutes"] <= minutes:
                selected.append(action)
                elapsed += action["estimated_minutes"]
        strategy = {"enabled": cfg["enabled"], "mode": cfg["mode"], "hour": cfg["hora"],
            "daily_limit": cfg["max_calls"], "used_today": strategy_used,
            "codex_available": bool(shutil.which("codex")), "useful_campaigns": useful,
            "active_campaigns": campaigns, "selection": cfg["selection"]}
    return {"generated_at": stamp.isoformat(), "minutes": minutes, "estimated_minutes": elapsed,
        "actions": selected, "available_actions": len(actions), "unselected_actions": len(actions)-len(selected),
        "quality": dict(warnings), "scanned": len(rows), "scan_limit": SCAN_LIMIT,
        "limited": total > len(rows), "total_leads": total, "instagram_leads": ig_total,
        "research": research,
        "commercial": {"conversations": counts.get("respondeu",0), "waiting": counts.get("contatado",0), "won": counts.get("fechou",0)},
        "strategy": strategy, "channels": bot_delivery.readiness(), "model_calls": 0,
        "monetary_cost": None, "demo": os.environ.get("PROSPECTOS_TEST_MODE", "").lower() in ("1","true","yes"),
        "note": "Planejamento local somente de leitura. Minutos são estimativas fixas; nenhuma mensagem ou chamada de IA é executada. Qualidade refere-se ao recorte Maps examinado; Instagram mantém sua fila própria."}


@bp.get("/api/workbench/plan")
def get_plan():
    def run():
        try:
            minutes, minimum = int(request.args.get("minutes","30")), int(request.args.get("minimum","60"))
        except ValueError:
            raise ValueError("Tempo e pontuação devem ser números inteiros.")
        return planejar(minutes, request.args.get("city",""), request.args.get("niche",""), minimum)
    return bot._responder(run)


@bp.get("/api/system/health")
def get_health():
    try:
        with bot.conectar() as c:
            c.execute("SELECT 1 FROM leads LIMIT 1").fetchone()
        return jsonify({"service":"prospectos", "ready":True,
            "instance":os.environ.get("PROSPECTOS_DESKTOP_INSTANCE", ""),
            "automation_runtime_enabled":os.environ.get("PROSPECTOS_AUTOMATION_DISABLED") != "1"})
    except Exception:
        return jsonify({"service":"prospectos", "ready":False, "error":"Base local indisponível."}), 503
