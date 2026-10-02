"""Private research workflow. Local records only; never provider calls or sends."""
import hashlib
import json
import os
import re
from collections import defaultdict
from datetime import date, datetime, timezone

from flask import Blueprint, jsonify, request

import bot
import paths
import pilot_review

bp = Blueprint("research_desk", __name__)
STATES = ("research", "qualified", "approved", "contacted", "replied", "won", "closed", "suppressed")


def preparar_banco(c):
    c.execute("""CREATE TABLE IF NOT EXISTS research_candidates (
        id INTEGER PRIMARY KEY, origin TEXT NOT NULL, external_id TEXT NOT NULL,
        name TEXT NOT NULL, city TEXT NOT NULL, segment TEXT NOT NULL,
        source_url TEXT NOT NULL, evidence TEXT NOT NULL, hypothesis TEXT NOT NULL,
        source_fingerprint TEXT NOT NULL, researched_on TEXT NOT NULL,
        phone TEXT NOT NULL DEFAULT '', contact_verified INTEGER NOT NULL DEFAULT 0,
        question TEXT NOT NULL DEFAULT '', draft TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
        state TEXT NOT NULL DEFAULT 'research', followup_on TEXT NOT NULL DEFAULT '',
        approval_hash TEXT, approved_at TEXT, sent_at TEXT,
        revision INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL,
        UNIQUE(origin,external_id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS research_events (
        id INTEGER PRIMARY KEY, candidate_id INTEGER NOT NULL REFERENCES research_candidates(id),
        action TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL)""")
    c.execute("CREATE INDEX IF NOT EXISTS research_state_due ON research_candidates(state,followup_on)")
    c.execute("CREATE INDEX IF NOT EXISTS research_event_candidate ON research_events(candidate_id,id DESC)")


def now():
    return datetime.now(timezone.utc).isoformat()


def _text(value, limit=4000, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValueError("Texto ausente ou acima do tamanho permitido.")
    return value.strip()


def _phone(value):
    value = _text(value, 40)
    if not value:
        return ""
    if not re.fullmatch(r"[+0-9 ().-]+", value):
        raise ValueError("Telefone contém caracteres inválidos.")
    digits = re.sub(r"\D", "", value)
    if len(digits) not in (12, 13) or not digits.startswith("55"):
        raise ValueError("Use telefone brasileiro com +55, DDD e número, ou deixe vazio.")
    return "+" + digits


def _contact(phone):
    return bot._contato({"telefone": phone}) if phone else None


def contact_context(c):
    """Transaction/request-local snapshot; never cache suppressions across requests."""
    candidates = defaultdict(set)
    for row in c.execute("SELECT id,phone FROM research_candidates"):
        contact = _contact(row["phone"])
        if contact:
            candidates[contact].add(row["id"])
    return {"research": candidates, "blocked": bot._contatos_bloqueados(c),
            "maps": {bot._contato(dict(row)) for row in c.execute("SELECT telefone FROM leads")} - {None, ""}}


def qualification_blockers(c, row, context=None):
    contact = _contact(row["phone"])
    context = contact_context(c) if context is None else context
    issues = []
    if not contact:
        issues.append("Contato utilizável ainda não informado.")
    if not row["contact_verified"]:
        issues.append("Confirme que o contato pertence a este negócio.")
    if not row["notes"].strip():
        issues.append("Registre a qualificação; a pesquisa não comprova necessidade.")
    if contact:
        if contact in context["blocked"] or row["state"] == "suppressed":
            issues.append("Contato bloqueado para abordagem.")
        # A shared number is not evidence of independent businesses. Never auto-merge.
        if context["research"].get(contact, set()) - {row["id"]}:
            issues.append("Número compartilhado com outro candidato; resolva a duplicidade.")
        if contact in context["maps"]:
            issues.append("Número já presente no Maps; acompanhe pela fila existente.")
    return issues


def blockers(c, row, context=None):
    """Approval/send requirements; qualification intentionally has its own gate."""
    issues = qualification_blockers(c, row, context)
    if not row["draft"].strip():
        issues.append("Escreva o texto que será revisado.")
    return issues


def next_action(row, qualification_issues, approval_issues, today=None):
    today = today or datetime.now(bot_strategy_timezone()).date().isoformat()
    state = row["state"]
    def action(kind, label, reason, priority, actionable=True):
        return {"kind": kind, "label": label, "reason": reason, "priority": priority, "actionable": actionable}
    if state in ("won", "closed", "suppressed"):
        return action("none", "Acompanhamento encerrado", "Este registro não volta à fila de abordagem.", 9, False)
    if "Contato bloqueado para abordagem." in qualification_issues:
        return action("blocked", "Não abordar", "Bloqueio vigente. Nenhum envio ou aprovação disponível.", 8, False)
    if any("duplicidade" in issue or "Maps" in issue for issue in qualification_issues):
        return action("resolve_contact", "Resolver contato compartilhado", "Confira a fila existente antes de iniciar outra abordagem.", 6)
    if state == "replied":
        return action("conversation", "Revisar resposta", "Há uma resposta registrada; confirme o próximo passo com contexto.", 0)
    if state == "contacted":
        due = row["followup_on"]
        if due and due <= today:
            return action("followup", "Revisar retorno vencido", "Retorno agendado por você; confira a conversa antes de agir.", 1)
        return action("waiting", "Aguardar retorno", "Retorno em " + due if due else "Nenhum retorno agendado; defina uma data quando necessário.", 8, False)
    if qualification_issues:
        return action("research", "Completar qualificação", " · ".join(qualification_issues), 5 if not row["phone"] else 4)
    if state == "research":
        return action("qualify", "Registrar qualificação", "Contato e notas salvos; confira e confirme a qualificação.", 3)
    if approval_issues:
        return action("prepare_text", "Preparar texto", "A qualificação permanece registrada. Escreva a versão que será revisada.", 3)
    if state == "qualified":
        return action("review", "Revisar esta versão", "Texto disponível; a aprovação exige sua revisão explícita.", 2)
    if state == "approved" and row["approval_hash"] == _signature(row):
        return action("manual_contact", "Conferir contato autorizado", "Aprovação vigente não envia mensagens. Registre apenas o contato que realmente ocorreu.", 3)
    return action("review", "Conferir aprovação", "A versão atual não possui aprovação válida. Atualize o registro antes de agir.", 4)


def _signature(row):
    return hashlib.sha256(json.dumps([row["phone"], row["draft"], bool(row["contact_verified"])],
                                    ensure_ascii=False).encode()).hexdigest()


def _event(c, row, action, detail=""):
    c.execute("INSERT INTO research_events(candidate_id,action,detail,created_at) VALUES(?,?,?,?)",
              (row["id"], action, detail, now()))


def _public(c, row, context=None, histories=None):
    row = dict(row)
    context = contact_context(c) if context is None else context
    row["qualification_blockers"] = qualification_blockers(c, row, context)
    row["blockers"] = blockers(c, row, context)
    row["qualification_ready"] = not row["qualification_blockers"]
    row["next_action"] = next_action(row, row["qualification_blockers"], row["blockers"])
    row["approval_valid"] = bool(row["approval_hash"] == _signature(row) and not row["blockers"]
                                  and row["state"] == "approved")
    row.pop("approval_hash", None)
    row["contact_verified"] = bool(row["contact_verified"])
    row["events"] = histories.get(row["id"], []) if histories is not None else [dict(r) for r in c.execute("SELECT action,detail,created_at FROM research_events WHERE candidate_id=? ORDER BY id DESC LIMIT 20", (row["id"],))]
    return row


def public_candidates(c, rows):
    """Bounded list serialization without a per-candidate SQL scan/history query."""
    if not rows:
        return []
    context = contact_context(c)
    ids = [row["id"] for row in rows]
    histories = defaultdict(list)
    for event in c.execute(f"""SELECT candidate_id,action,detail,created_at FROM (
            SELECT *,ROW_NUMBER() OVER(PARTITION BY candidate_id ORDER BY id DESC) AS position
            FROM research_events WHERE candidate_id IN ({','.join('?' for _ in ids)}))
            WHERE position<=20 ORDER BY candidate_id,position""", ids):
        histories[event["candidate_id"]].append({key:event[key] for key in ("action", "detail", "created_at")})
    return [_public(c, row, context, histories) for row in rows]


EDIT_FIELDS = {"phone", "contact_verified", "notes", "draft", "question", "followup_on"}


def _edit(c, row, body, context):
    old_phone, old_verified, signature = row["phone"], row["contact_verified"], _signature(row)
    for key in ("notes", "draft", "question"):
        if key in body:
            row[key] = _text(body[key])
    if "phone" in body:
        phone = _phone(body["phone"])
        if phone != row["phone"]:
            row["contact_verified"] = 0
        row["phone"] = phone
    if "contact_verified" in body:
        if type(body["contact_verified"]) is not bool:
            raise ValueError("Confirmação de contato deve ser verdadeira ou falsa.")
        row["contact_verified"] = int(body["contact_verified"])
    if "followup_on" in body:
        row["followup_on"] = _text(body["followup_on"], 10)
        if row["followup_on"]:
            date.fromisoformat(row["followup_on"])
    qualification_changed = old_phone != row["phone"] or old_verified != row["contact_verified"] or not row["notes"]
    if signature != _signature(row) or not row["notes"]:
        row["approval_hash"] = row["approved_at"] = None
        if row["state"] in ("qualified", "approved"):
            row["state"] = "research" if qualification_changed or qualification_blockers(c, row, context) else "qualified"


def summary(c):
    if not c.execute("SELECT 1 FROM sqlite_master WHERE name='research_candidates'").fetchone():
        return {"total": 0, "states": {}, "due": 0}
    states = dict(c.execute("SELECT state,COUNT(*) FROM research_candidates GROUP BY state"))
    due = c.execute("SELECT COUNT(*) FROM research_candidates WHERE followup_on!='' AND followup_on<=? AND state IN ('contacted','replied')",
                    (datetime.now(bot_strategy_timezone()).date().isoformat(),)).fetchone()[0]
    return {"total": sum(states.values()), "states": states, "due": due}


def bot_strategy_timezone():
    from datetime import timedelta
    return timezone(timedelta(hours=-3))


def _load_pilot(pilot_id):
    if not isinstance(pilot_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", pilot_id):
        raise ValueError("Piloto local inválido.")
    root = paths.DIR_DADOS.resolve()
    file = paths.caminho_dados("pilots", pilot_id, "pilot.json")
    if not file.resolve().is_relative_to(root):
        raise ValueError("Fonte fora da base local.")
    try:
        with file.open("rb") as stream:
            raw = stream.read(pilot_review.MAX_BYTES + 1)
        if len(raw) > pilot_review.MAX_BYTES:
            raise ValueError("Piloto excede o limite local.")
        data = json.loads(raw)
        if data.get("id") != pilot_id or not isinstance(data.get("prospects"), list) or not 1 <= len(data["prospects"]) <= 30:
            raise ValueError("Formato de piloto inválido.")
        city = _text(data.get("city"), 100, True)
        checked = date.fromisoformat(data["researched_on"]).isoformat()
        rows, seen = [], set()
        for source in data["prospects"]:
            identity = _text(source.get("id"), 100, True)
            if identity in seen:
                raise ValueError("Identidade duplicada no piloto.")
            seen.add(identity)
            rows.append(dict(origin=pilot_id, external_id=identity, city=city, researched_on=checked,
                source_fingerprint=hashlib.sha256(raw).hexdigest(),
                name=_text(source.get("name"), 180, True), segment=_text(source.get("segment"), 100, True),
                source_url=pilot_review._source(source.get("source_url")), evidence=_text(source.get("evidence"), required=True),
                hypothesis="Necessidade, orçamento e responsável ainda não confirmados.",
                phone=_phone(source.get("published_phone") or ""),
                question=_text(source.get("discovery_question", "")), draft=_text(source.get("draft", "")), updated_at=now()))
        return rows
    except (OSError, KeyError, TypeError, AttributeError, UnicodeError) as exc:
        raise ValueError("Não foi possível validar o piloto local.") from exc


def importar(pilot_id):
    rows = _load_pilot(pilot_id)  # Validate everything before any write.
    added = 0
    with bot.conectar() as c:
        c.execute("BEGIN IMMEDIATE")
        for row in rows:
            names = list(row)
            cursor = c.execute(f"INSERT INTO research_candidates({','.join(names)}) VALUES({','.join('?' for _ in names)}) ON CONFLICT(origin,external_id) DO NOTHING", tuple(row.values()))
            if cursor.rowcount:
                row["id"] = cursor.lastrowid
                _event(c, row, "imported", "Fonte local validada; sem qualificação ou aprovação automática.")
                added += 1
    return {"added": added, "existing": len(rows)-added}


class Conflict(ValueError):
    pass


def change(identity, body):
    if not isinstance(body, dict) or type(body.get("revision")) is not int:
        raise ValueError("Informe a revisão atual do registro.")
    action = body.get("action", "edit")
    with bot.conectar() as c:
        c.execute("BEGIN IMMEDIATE")
        found = c.execute("SELECT * FROM research_candidates WHERE id=?", (identity,)).fetchone()
        if not found:
            raise LookupError("Candidato não encontrado.")
        row = dict(found)
        if body["revision"] != row["revision"]:
            raise Conflict("Este registro mudou em outra janela. Atualize antes de salvar.")
        context = contact_context(c)
        if action == "edit":
            allowed = {"revision", "action"} | EDIT_FIELDS
            if set(body)-allowed:
                raise ValueError("Campo não editável.")
            if row["state"] == "suppressed":
                raise ValueError("Contato bloqueado; edição de abordagem indisponível.")
            _edit(c, row, body, context)
        elif action in ("qualify", "approve", "sent", "reply", "win", "close", "suppress"):
            allowed = {"revision", "action", "human_confirmed"} | (EDIT_FIELDS if action == "qualify" else set())
            if set(body)-allowed:
                raise ValueError("Campos inesperados para esta ação.")
            if body.get("human_confirmed") is not True:
                raise ValueError("Esta ação exige confirmação humana explícita.")
            if row["state"] in ("suppressed", "won", "closed"):
                raise ValueError("Registro encerrado; nova abordagem indisponível.")
            if action == "qualify":
                _edit(c, row, body, context)
            transitions = {"qualify": (("research",), "qualified"), "approve": (("qualified",), "approved"),
                "sent": (("approved",), "contacted"), "reply": (("contacted",), "replied"),
                "win": (("replied",), "won")}
            if action in transitions:
                before, after = transitions[action]
                if row["state"] not in before:
                    raise ValueError("Etapa anterior ainda não concluída.")
                issues = qualification_blockers(c, row, context) if action == "qualify" else blockers(c, row, context) if action in ("approve", "sent") else []
                if issues:
                    raise ValueError(" ".join(issues))
                if action == "sent" and row["approval_hash"] != _signature(row):
                    raise ValueError("O texto e contato atuais não possuem aprovação vigente.")
                row["state"] = after
                if action == "approve":
                    row["approval_hash"], row["approved_at"] = _signature(row), now()
                if action == "sent":
                    row["sent_at"] = now()
            elif action == "close":
                row["state"] = "closed"
            else:
                row["state"] = "suppressed"
                contact = _contact(row["phone"])
                if contact:
                    c.execute("INSERT INTO bot_suppressions(contact,reason,created_at) VALUES(?,?,?) ON CONFLICT(contact) DO NOTHING",
                              (contact, "Bloqueado pelo operador na pesquisa", now()))
            if action in ("close", "suppress", "win"):
                row["followup_on"] = ""
                row["approval_hash"] = row["approved_at"] = None
        else:
            raise ValueError("Ação desconhecida.")
        row["revision"] += 1
        row["updated_at"] = now()
        fields = ("phone", "contact_verified", "notes", "draft", "question", "state", "followup_on", "approval_hash", "approved_at", "sent_at", "revision", "updated_at")
        c.execute(f"UPDATE research_candidates SET {','.join(f'{key}=?' for key in fields)} WHERE id=?", tuple(row[key] for key in fields)+(identity,))
        detail = json.dumps({"phone": row["phone"], "draft": row["draft"]}, ensure_ascii=False) if action in ("approve", "sent") else ""
        _event(c, row, action, detail)
        return _public(c, row, context)


def _respond(fn):
    try:
        response = jsonify(fn())
        response.headers["Cache-Control"] = "no-store"
        return response
    except Conflict as exc:
        return jsonify(erro=str(exc)), 409
    except LookupError as exc:
        return jsonify(erro=str(exc)), 404
    except ValueError as exc:
        return jsonify(erro=str(exc)), 400


@bp.get("/api/research")
def listing():
    def run():
        with bot.conectar() as c:
            rows = c.execute("SELECT * FROM research_candidates ORDER BY id LIMIT 500").fetchall()
            candidates = public_candidates(c, rows)
            candidates.sort(key=lambda row: (row["next_action"]["priority"], row["followup_on"] or "9999-12-31", row["id"]))
            result = {"candidates": candidates, "summary": summary(c), "limit": 500,
                      "demo": os.environ.get("PROSPECTOS_TEST_MODE", "").lower() in ("1", "true", "yes")}
        # Metadata only; no source contents or private credentials outside the configured root.
        result["pilots"] = []
        for pilot in pilot_review.listar()["pilots"]:
            try:
                material = _load_pilot(pilot["id"])
                result["pilots"].append({"id": pilot["id"], "title": f"{material[0]['city']} · pesquisa local",
                                         "count": len(material)})
            except ValueError:
                continue
        return result
    return _respond(run)


@bp.post("/api/research/import")
def import_route():
    body = request.get_json(silent=True)
    def run():
        if not isinstance(body, dict) or set(body) != {"pilot_id"}:
            raise ValueError("Informe somente o piloto local que deseja incorporar.")
        return importar(body["pilot_id"])
    return _respond(run)


@bp.patch("/api/research/<int:identity>")
def patch_route(identity):
    return _respond(lambda: change(identity, request.get_json(silent=True)))


@bp.get("/api/research/export")
def export_route():
    response = listing()
    if not isinstance(response, tuple):
        response.headers["Content-Disposition"] = 'attachment; filename="prospectos-pesquisa.json"'
    return response
