"""Bot local: preparar, revisar e acompanhar. Nunca transmite mensagens."""

import json
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from flask import Blueprint, jsonify, request

import db

bp = Blueprint("bot", __name__)
logger = logging.getLogger(__name__)
_scheduler_lock = threading.Lock()
_scheduler_started = False
_scheduler_thread = None
_scheduler_last_tick = None
_scheduler_error = None


class Conflict(ValueError):
    pass


def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def preparar_banco(c):
    c.executescript("""
        CREATE TABLE IF NOT EXISTS bot_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT, config_json TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'idle', paused INTEGER NOT NULL DEFAULT 0,
            next_run TEXT, last_capture TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bot_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id INTEGER NOT NULL,
            state TEXT NOT NULL, started_at TEXT NOT NULL, finished_at TEXT,
            summary_json TEXT NOT NULL DEFAULT '{}', error TEXT,
            FOREIGN KEY(campaign_id) REFERENCES bot_campaigns(id)
        );
        CREATE TABLE IF NOT EXISTS bot_targets (
            place_id TEXT PRIMARY KEY, campaign_id INTEGER NOT NULL,
            FOREIGN KEY(place_id) REFERENCES leads(place_id) ON DELETE CASCADE,
            FOREIGN KEY(campaign_id) REFERENCES bot_campaigns(id)
        );
        CREATE TABLE IF NOT EXISTS bot_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id INTEGER NOT NULL,
            place_id TEXT NOT NULL, step_order INTEGER NOT NULL, text TEXT NOT NULL,
            reason TEXT NOT NULL, score INTEGER NOT NULL, state TEXT NOT NULL,
            due_at TEXT, ready_at TEXT, approved_text TEXT, approved_contact TEXT,
            approved_at TEXT, sent_at TEXT,
            UNIQUE(place_id, step_order),
            FOREIGN KEY(place_id) REFERENCES leads(place_id) ON DELETE CASCADE,
            FOREIGN KEY(campaign_id) REFERENCES bot_campaigns(id)
        );
        CREATE INDEX IF NOT EXISTS idx_bot_due ON bot_messages(state, due_at);
        CREATE INDEX IF NOT EXISTS idx_bot_campaign ON bot_messages(campaign_id, state);
        CREATE TRIGGER IF NOT EXISTS guard_outreach_bot_target
        BEFORE INSERT ON outreach_sequences
        WHEN EXISTS(SELECT 1 FROM bot_targets WHERE place_id=NEW.place_id)
        BEGIN
            SELECT RAISE(ABORT, 'bot_target_conflict');
        END;
    """)
    import bot_operations
    bot_operations.preparar_banco(c)


@contextmanager
def conectar():
    c = db.conectar()
    try:
        with c:
            yield c
    finally:
        c.close()


def _campanha(c, campaign_id):
    row = c.execute("SELECT * FROM bot_campaigns WHERE id=?", (campaign_id,)).fetchone()
    if not row:
        raise ValueError("Campanha não encontrada.")
    result = dict(row)
    result["config"] = json.loads(result.pop("config_json"))
    return result


def validar_config(body):
    if not isinstance(body, dict):
        raise ValueError("Informe um objeto com a configuração da campanha.")
    config = {}
    for key, default, maximum in (("nome", "Minha campanha", 80), ("oferta", "", 180),
                                  ("nicho", "", 100), ("cidade", "", 100), ("queries", "", 360)):
        value = body.get(key, default)
        if not isinstance(value, str) or len(value.strip()) > maximum:
            raise ValueError(f"{key}: texto com até {maximum} caracteres.")
        config[key] = value.strip()
    if not config["nome"] or not config["oferta"]:
        raise ValueError("Informe o nome e o serviço que você oferece.")
    for key, default, lo, hi in (("limite_dia", 10, 1, 30), ("score_min", 60, 0, 100),
                                  ("intervalo_horas", 0, 0, 168)):
        value = body.get(key, default)
        if type(value) is not int or not lo <= value <= hi:
            raise ValueError(f"{key}: inteiro entre {lo} e {hi}.")
        if key == "intervalo_horas" and 0 < value < 6:
            raise ValueError("A agenda precisa de intervalo de pelo menos 6 horas.")
        config[key] = value
    for key in ("captar", "autorizar_captura"):
        value = body.get(key, False)
        if type(value) is not bool:
            raise ValueError(f"{key}: use verdadeiro ou falso.")
        config[key] = value
    queries = list(dict.fromkeys(line.strip().casefold() for line in config["queries"].splitlines() if line.strip()))
    if len(queries) > 3 or any(len(q) > 120 for q in queries):
        raise ValueError("Use até 3 consultas de captura, com até 120 caracteres cada.")
    config["queries"] = "\n".join(queries)
    if config["captar"] and (not queries or not config["autorizar_captura"]):
        raise ValueError("A captura exige consultas e autorização explícita de acesso à fonte externa.")
    return config


def _contato(lead):
    from processar import telefone_para_whatsapp
    return telefone_para_whatsapp(lead.get("telefone"))


def _contatos_ocupados(c, exclude=None):
    rows = c.execute("""SELECT place_id,telefone FROM leads l WHERE
        status!='novo' OR EXISTS(SELECT 1 FROM bot_targets t WHERE t.place_id=l.place_id)
        OR EXISTS(SELECT 1 FROM outreach_sequences s WHERE s.place_id=l.place_id)""")
    return {_contato(dict(r)) for r in rows if r["place_id"] != exclude} - {None, ""}


def _contatos_bloqueados(c):
    return {r[0] for r in c.execute("SELECT contact FROM bot_suppressions")}


def _disponiveis(c, config, limit):
    if limit <= 0:
        return []
    from rotas_leads import SQL_SCORE
    rows = c.execute(f"""
        SELECT *, ROUND({SQL_SCORE}) AS bot_score FROM leads
        WHERE status='novo' AND site_status IN ('sem_site','site_ruim')
        AND ROUND({SQL_SCORE}) >= ?
        AND (?='' OR LOWER(cidade)=LOWER(?))
        AND (?='' OR LOWER(COALESCE(nicho,categoria,'')) LIKE LOWER(?) ESCAPE '\\')
        AND NOT EXISTS(SELECT 1 FROM bot_targets t WHERE t.place_id=leads.place_id)
        AND NOT EXISTS(SELECT 1 FROM outreach_sequences s WHERE s.place_id=leads.place_id)
        ORDER BY bot_score DESC, place_id LIMIT 1000
    """, (config["score_min"], config["cidade"], config["cidade"], config["nicho"],
             "%" + config["nicho"].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")).fetchall()
    result = []
    seen = _contatos_ocupados(c) | _contatos_bloqueados(c)
    for row in rows:
        lead = dict(row)
        contact = _contato(lead)
        if contact and contact not in seen:
            seen.add(contact)
            result.append(lead)
            if len(result) >= limit:
                break
    return result if limit > 0 else []


def trabalho_disponivel(c, camp):
    saldo = _saldo(c, camp["id"], camp["config"])
    available = _disponiveis(c, camp["config"], saldo)
    due = 0
    for row in c.execute("SELECT * FROM bot_messages WHERE campaign_id=? AND state='scheduled' AND due_at<=?", (camp["id"], agora())):
        try:
            _validar_destino(c, dict(row))
            due += 1
        except Conflict:
            continue
    capture = bool(camp["config"]["captar"] and saldo > len(available) and (camp["last_capture"] or "")[:10] != agora()[:10])
    useful = not camp["paused"] and camp["state"] == "idle" and saldo > 0 and bool(available or due or capture)
    return {"useful": useful, "saldo": saldo, "available": available, "due": min(due, saldo), "capture": capture}


def _saldo(c, campaign_id, config):
    used = c.execute("SELECT COUNT(*) FROM bot_messages WHERE campaign_id=? AND ready_at LIKE ?",
                     (campaign_id, agora()[:10] + "%")).fetchone()[0]
    pending = c.execute("SELECT COUNT(*) FROM bot_messages WHERE campaign_id=? AND state IN ('pending','approved')",
                        (campaign_id,)).fetchone()[0]
    return max(0, min(config["limite_dia"] - used, config["limite_dia"] - pending))


def previa(body):
    config = validar_config(body)
    with conectar() as c:
        leads = _disponiveis(c, config, config["limite_dia"])
    return {"leads": [{"nome": l["nome"], "score": l["bot_score"], "place_id": l["place_id"]} for l in leads],
            "na_base": len(leads), "captura_planejada": config["captar"] and len(leads) < config["limite_dia"],
            "consultas_max": len(config["queries"].splitlines()) if config["captar"] else 0,
            "limite_analises": config["limite_dia"], "chamadas_ia": 0,
            "observacao": "Ensaio local: nenhuma captura, mensagem ou alteração no CRM foi executada."}


def criar(body):
    config = validar_config(body)
    with conectar() as c:
        cur = c.execute("INSERT INTO bot_campaigns(config_json,created_at) VALUES(?,?)",
                        (json.dumps(config, ensure_ascii=False), agora()))
        return _campanha(c, cur.lastrowid)


def _textos(lead, oferta):
    nome = lead.get("nome") or "sua empresa"
    fact = "Não encontrei um site próprio nos dados que consultei." if lead.get("site_status") == "sem_site" else "O cadastro indica pontos de melhoria no site; posso conferir com você."
    return [
        f"Olá, equipe da {nome}! {fact} Trabalho com {oferta}. Faz sentido eu apresentar uma ideia para o negócio?",
        f"Olá, equipe da {nome}! Retomando minha mensagem sobre {oferta}: esse assunto faz sentido para vocês neste momento?",
        f"Se for útil para a {nome}, posso explicar uma opção simples de {oferta}, alinhada à necessidade de vocês. Prefere que eu detalhe ou deixe para outra ocasião?",
        "Vou encerrar meus contatos por aqui para respeitar seu tempo. Se esse assunto se tornar uma prioridade, fico à disposição. Obrigado!",
    ]


def _cancelar_inaptos(c, campaign_id):
    cur = c.execute("""UPDATE bot_messages SET state='cancelled'
        WHERE campaign_id=? AND state IN ('pending','approved','scheduled')
        AND (NOT EXISTS(SELECT 1 FROM leads l WHERE l.place_id=bot_messages.place_id
                        AND l.status IN ('novo','contatado'))
             OR EXISTS(SELECT 1 FROM leads l WHERE l.place_id=bot_messages.place_id AND l.status='contatado'
                        AND NOT EXISTS(SELECT 1 FROM bot_messages initial WHERE initial.place_id=l.place_id AND initial.step_order=0 AND initial.state='sent'))
             OR EXISTS(SELECT 1 FROM outreach_sequences s WHERE s.place_id=bot_messages.place_id))""", (campaign_id,))
    total = cur.rowcount
    blocked = _contatos_bloqueados(c)
    for row in c.execute("SELECT DISTINCT l.place_id,l.telefone FROM leads l JOIN bot_messages m ON m.place_id=l.place_id WHERE m.campaign_id=? AND m.state IN ('pending','approved','scheduled')", (campaign_id,)).fetchall():
        if _contato(dict(row)) in blocked:
            total += c.execute("UPDATE bot_messages SET state='cancelled' WHERE place_id=? AND state IN ('pending','approved','scheduled')", (row["place_id"],)).rowcount
    return total


def _paused(campaign_id):
    with conectar() as c:
        return bool(_campanha(c, campaign_id)["paused"])


def capturar(config, limit):
    import jobs
    import paths
    if not jobs.tentar_reservar_busca():
        raise Conflict("Já existe uma captura em andamento. Nenhuma nova captura foi iniciada.")
    try:
        paths.escrever_texto_atomico(paths.caminho_dados("queries.txt", criar_pai=True), config["queries"] + "\n")
        result = jobs._rodar_busca_em_background(apenas_novos=True, limite_analises=limit)
        if result is None:
            raise Conflict(jobs.estado_busca["mensagem"])
        return result
    finally:
        jobs.liberar_busca()


def executar(campaign_id, background=True, resume=True):
    with conectar() as c:
        c.execute("BEGIN IMMEDIATE")
        campaign = _campanha(c, campaign_id)
        if not resume and (campaign["paused"] or campaign["state"] != "idle"):
            raise Conflict("Campanha pausada ou indisponível. Uma agenda não pode retomar a pausa humana.")
        if c.execute("SELECT 1 FROM bot_campaigns WHERE state='running'").fetchone():
            raise Conflict("Uma rodada do bot já está em andamento.")
        c.execute("UPDATE bot_campaigns SET state='running',paused=0,next_run=NULL WHERE id=?", (campaign_id,))
        cur = c.execute("INSERT INTO bot_runs(campaign_id,state,started_at) VALUES(?,'running',?)", (campaign_id, agora()))
        run_id = cur.lastrowid
    if background:
        try:
            threading.Thread(target=rodar, args=(campaign_id, run_id), daemon=True).start()
        except RuntimeError:
            with conectar() as c:
                c.execute("UPDATE bot_campaigns SET state='error',paused=1 WHERE id=?", (campaign_id,))
                c.execute("UPDATE bot_runs SET state='error',finished_at=?,error='Não foi possível iniciar a rodada.' WHERE id=?", (agora(), run_id))
            raise Conflict("Não foi possível iniciar a rodada. Retome manualmente.")
    else:
        rodar(campaign_id, run_id)
    return {"run_id": run_id}


def rodar(campaign_id, run_id):
    summary = {"preparadas": 0, "followups": 0, "canceladas": 0, "captura": False, "chamadas_ia": 0}
    state, error = "completed", None
    try:
        with conectar() as c:
            campaign = _campanha(c, campaign_id)
            config = campaign["config"]
            summary["canceladas"] = _cancelar_inaptos(c, campaign_id)
            saldo = _saldo(c, campaign_id, config)
            due = c.execute("SELECT id FROM bot_messages WHERE campaign_id=? AND state='scheduled' AND due_at<=? ORDER BY due_at,id LIMIT ?",
                            (campaign_id, agora(), saldo)).fetchall()
            for row in due:
                c.execute("UPDATE bot_messages SET state='pending',ready_at=? WHERE id=?", (agora(), row["id"]))
            summary["followups"] = len(due)
            saldo = _saldo(c, campaign_id, config)
            leads = _disponiveis(c, config, saldo)
        if _paused(campaign_id):
            state = "paused"
            return
        # Backlog primeiro; uma captura por dia/campanha, inclusive em falhas.
        if saldo > len(leads) and config["captar"] and (campaign["last_capture"] or "")[:10] != agora()[:10]:
            with conectar() as c:
                c.execute("UPDATE bot_campaigns SET last_capture=? WHERE id=?", (agora(), campaign_id))
            summary["captura"] = True
            try:
                summary["contagens_captura"] = capturar(config, saldo - len(leads))
            except Conflict as exc:
                state, error = "error", str(exc)
            with conectar() as c:
                leads = _disponiveis(c, config, saldo)
        for lead in leads:
            if _paused(campaign_id):
                state = "paused"
                break
            with conectar() as c:
                c.execute("BEGIN IMMEDIATE")
                from rotas_leads import SQL_SCORE
                fresh = c.execute(f"SELECT *,ROUND({SQL_SCORE}) AS bot_score FROM leads WHERE place_id=?", (lead["place_id"],)).fetchone()
                if not fresh or fresh["status"] != "novo" or fresh["site_status"] not in ('sem_site','site_ruim') or fresh["bot_score"] < config["score_min"] or not _saldo(c, campaign_id, config):
                    continue
                contact = _contato(dict(fresh))
                if not contact or contact in (_contatos_ocupados(c) | _contatos_bloqueados(c)):
                    continue
                if c.execute("SELECT 1 FROM outreach_sequences WHERE place_id=?", (lead["place_id"],)).fetchone():
                    continue
                cur = c.execute("INSERT OR IGNORE INTO bot_targets(place_id,campaign_id) VALUES(?,?)", (lead["place_id"], campaign_id))
                if not cur.rowcount:
                    continue
                lead = dict(fresh)
                reason = f"Score {lead['bot_score']}/100 · {'sem site próprio' if lead['site_status']=='sem_site' else 'site com melhorias'} · contato disponível"
                for step, text in enumerate(_textos(lead, config["oferta"])):
                    c.execute("""INSERT INTO bot_messages(campaign_id,place_id,step_order,text,reason,score,state,ready_at)
                        VALUES(?,?,?,?,?,?,?,?)""", (campaign_id, lead["place_id"], step, text, reason, lead["bot_score"],
                        "pending" if step == 0 else "scheduled", agora() if step == 0 else None))
                summary["preparadas"] += 1
    except Exception as exc:
        logger.exception("Rodada do bot interrompida: %s", run_id)
        state, error = "error", "A rodada falhou. Confira a fonte de captura e os logs locais antes de tentar novamente."
        if isinstance(exc, Conflict):
            error = str(exc)
    finally:
        with conectar() as c:
            campaign = _campanha(c, campaign_id)
            if campaign["paused"]:
                state = "paused"
            interval = campaign["config"]["intervalo_horas"]
            next_run = (datetime.now(timezone.utc) + timedelta(hours=interval)).isoformat(timespec="seconds") if interval and state == "completed" else None
            c.execute("UPDATE bot_runs SET state=?,finished_at=?,summary_json=?,error=? WHERE id=?",
                      (state, agora(), json.dumps(summary, ensure_ascii=False), error, run_id))
            c.execute("UPDATE bot_campaigns SET state=?,next_run=? WHERE id=?",
                      ("idle" if state == "completed" else state, next_run, campaign_id))


def pausar(campaign_id):
    with conectar() as c:
        _campanha(c, campaign_id)
        c.execute("UPDATE bot_campaigns SET paused=1,state=CASE WHEN state='running' THEN state ELSE 'paused' END,next_run=NULL WHERE id=?", (campaign_id,))
    return {"ok": True, "mensagem": "Pausa solicitada. A etapa de captura já iniciada termina antes de parar."}


def _message(c, message_id):
    row = c.execute("SELECT * FROM bot_messages WHERE id=?", (message_id,)).fetchone()
    if not row:
        raise ValueError("Mensagem não encontrada.")
    return dict(row)


def _validar_destino(c, message):
    campaign = _campanha(c, message["campaign_id"])
    if campaign["paused"]:
        raise Conflict("Campanha pausada. Retome uma rodada antes de liberar contatos.")
    lead = c.execute("SELECT * FROM leads WHERE place_id=?", (message["place_id"],)).fetchone()
    if not lead or lead["status"] not in ("novo", "contatado"):
        raise Conflict("O status do lead mudou. Este contato não está mais elegível.")
    if message["step_order"] == 0 and lead["status"] != "novo":
        raise Conflict("O lead já foi contatado. A mensagem inicial não será repetida.")
    if c.execute("SELECT 1 FROM outreach_sequences WHERE place_id=?", (message["place_id"],)).fetchone():
        raise Conflict("Este lead já tem uma sequência na central de abordagens.")
    contact = _contato(dict(lead))
    if not contact:
        raise Conflict("O lead não possui um contato utilizável.")
    if contact in _contatos_bloqueados(c):
        raise Conflict("Este contato pediu para não ser contatado. A liberação está bloqueada.")
    if contact in _contatos_ocupados(c, exclude=message["place_id"]):
        raise Conflict("Este telefone já pertence a outro contato em acompanhamento. Resolva a duplicidade antes de liberar.")
    if message["step_order"] > 0:
        prev = c.execute("SELECT sent_at FROM bot_messages WHERE place_id=? AND step_order=? AND state='sent'",
                         (message["place_id"], message["step_order"]-1)).fetchone()
        if not prev or not message["due_at"] or message["due_at"] > agora():
            raise Conflict("O follow-up ainda não está disponível.")
    return contact


def agir(message_id, action, body):
    if not isinstance(body, dict):
        raise ValueError("Informe um objeto JSON.")
    with conectar() as c:
        c.execute("BEGIN IMMEDIATE")
        m = _message(c, message_id)
        if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='bot_deliveries'").fetchone():
            delivery = c.execute("SELECT state FROM bot_deliveries WHERE message_id=?", (message_id,)).fetchone()
            if delivery and delivery["state"] == "sending":
                raise Conflict("Envio em andamento. Aguarde o resultado antes de editar ou registrar outro envio.")
            if delivery and delivery["state"] == "queued":
                if action in ("edit", "reject"):
                    c.execute("UPDATE bot_deliveries SET state='blocked',error='Aprovação revogada antes de enviar.' WHERE message_id=?", (message_id,))
                else:
                    raise Conflict("Uma tentativa aprovada já está na fila de envio.")
        if action == "edit":
            text = body.get("text")
            if m["state"] not in ("pending", "approved") or not isinstance(text, str) or not 1 <= len(text.strip()) <= 2000:
                raise Conflict("Edite somente mensagens em revisão, com 1 a 2000 caracteres.")
            c.execute("UPDATE bot_messages SET text=?,state='pending',approved_text=NULL,approved_contact=NULL,approved_at=NULL WHERE id=?", (text.strip(), message_id))
        elif action == "reject":
            if m["state"] not in ("pending", "approved"):
                raise Conflict("Somente mensagens em revisão podem ser rejeitadas.")
            c.execute("UPDATE bot_messages SET state='rejected' WHERE id=?", (message_id,))
            c.execute("UPDATE bot_messages SET state='cancelled' WHERE place_id=? AND step_order>? AND state='scheduled'", (m["place_id"], m["step_order"]))
            c.execute("UPDATE leads SET proximo_followup=NULL WHERE place_id=?", (m["place_id"],))
        elif action == "approve":
            if m["state"] != "pending" or body.get("text") != m["text"]:
                raise Conflict("O texto mudou. Recarregue e revise a versão atual antes de aprovar.")
            contact = _validar_destino(c, m)
            c.execute("UPDATE bot_messages SET state='approved',approved_text=text,approved_contact=?,approved_at=? WHERE id=?", (contact, agora(), message_id))
        elif action in ("open", "sent"):
            # Idempotência sem avançar a cadência duas vezes.
            if action == "sent" and m["state"] == "sent" and body.get("confirmado") is True:
                return {"ok": True, "ja_registrado": True}
            contact = _validar_destino(c, m)
            if m["state"] != "approved" or m["approved_text"] != m["text"] or m["approved_contact"] != contact:
                raise Conflict("Aprovação ausente ou desatualizada. Revise texto e destinatário novamente.")
            if action == "open":
                return {"url": contact + "?text=" + quote(m["text"], safe="")}
            if body.get("confirmado") is not True:
                raise ValueError("Confirme explicitamente que você enviou a mensagem.")
            now = agora()
            c.execute("UPDATE bot_messages SET state='sent',sent_at=? WHERE id=?", (now, message_id))
            if m["step_order"] == 0:
                c.execute("UPDATE leads SET status='contatado',atualizado_em=? WHERE place_id=? AND status='novo'", (now, m["place_id"]))
                c.execute("INSERT INTO historico_status(place_id,status_anterior,status_novo,alterado_em) VALUES(?,'novo','contatado',?)", (m["place_id"], now))
            delays = (2, 3, 4)
            if m["step_order"] < 3:
                due = (datetime.now(timezone.utc) + timedelta(days=delays[m["step_order"]])).isoformat(timespec="seconds")
                c.execute("UPDATE bot_messages SET due_at=? WHERE place_id=? AND step_order=? AND state='scheduled'", (due, m["place_id"], m["step_order"]+1))
                c.execute("UPDATE leads SET proximo_followup=? WHERE place_id=?", (due[:10], m["place_id"]))
            else:
                c.execute("UPDATE leads SET proximo_followup=NULL WHERE place_id=?", (m["place_id"],))
            if m["step_order"] > 0:
                c.execute("UPDATE leads SET follow_ups_enviados=COALESCE(follow_ups_enviados,0)+1,ultimo_followup_em=? WHERE place_id=?", (now, m["place_id"]))
        else:
            raise ValueError("Ação desconhecida.")
        return {"ok": True}


def painel():
    with conectar() as c:
        campaigns = [_campanha(c, r["id"]) for r in c.execute("SELECT id FROM bot_campaigns ORDER BY id DESC LIMIT 50")]
        messages = [dict(r) for r in c.execute("""SELECT m.*,l.nome,l.status AS lead_status,l.telefone FROM bot_messages m
            JOIN leads l ON l.place_id=m.place_id
            WHERE m.state IN ('pending','approved') OR (m.state='scheduled' AND m.due_at IS NOT NULL)
            ORDER BY CASE m.state WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END,m.id LIMIT 200""")]
        runs = []
        for row in c.execute("SELECT * FROM bot_runs ORDER BY id DESC LIMIT 20"):
            run = dict(row)
            run["summary"] = json.loads(run.pop("summary_json"))
            runs.append(run)
        counts = {r["state"]: r["total"] for r in c.execute("SELECT state,COUNT(*) AS total FROM bot_messages GROUP BY state")}
    return {"campaigns": campaigns, "messages": messages, "runs": runs, "counts": counts}


def recuperar():
    with conectar() as c:
        c.execute("UPDATE bot_campaigns SET state='interrupted',paused=1,next_run=NULL WHERE state='running'")
        c.execute("UPDATE bot_runs SET state='interrupted',finished_at=?,error='Backend reiniciado; retome manualmente.' WHERE state='running'", (agora(),))


def tick():
    with conectar() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM bot_campaigns WHERE paused=0 AND state='idle' AND next_run<=? ORDER BY next_run", (agora(),))]
    for campaign_id in ids:
        try:
            executar(campaign_id, resume=False)
        except Conflict:
            break


def iniciar_scheduler():
    global _scheduler_started, _scheduler_thread
    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True
    recuperar()
    import bot_strategy
    bot_strategy.recuperar()
    import bot_delivery
    bot_delivery.recuperar()
    def loop():
        global _scheduler_last_tick, _scheduler_error
        event = threading.Event()
        while not event.wait(30):
            _scheduler_last_tick = agora()
            try:
                tick()
                bot_strategy.tick()
                _scheduler_error = None
            except Exception:
                _scheduler_error = "Falha no ciclo; consulte os logs locais."
                logger.exception("Falha no relógio do bot local")
    _scheduler_thread = threading.Thread(target=loop, daemon=True)
    _scheduler_thread.start()


def _responder(fn, *args, status=200):
    try:
        return jsonify(fn(*args)), status
    except Conflict as exc:
        return jsonify({"erro": str(exc)}), 409
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400


@bp.get("/api/bot")
def get_painel():
    return _responder(painel)


@bp.post("/api/bot/preview")
def post_preview():
    return _responder(previa, request.get_json(silent=True))


@bp.post("/api/bot/campaigns")
def post_campaign():
    return _responder(criar, request.get_json(silent=True), status=201)


@bp.post("/api/bot/campaigns/<int:campaign_id>/run")
def post_run(campaign_id):
    return _responder(executar, campaign_id, status=202)


@bp.post("/api/bot/campaigns/<int:campaign_id>/pause")
def post_pause(campaign_id):
    return _responder(pausar, campaign_id)


@bp.post("/api/bot/messages/<int:message_id>/<action>")
def post_action(message_id, action):
    return _responder(agir, message_id, action, request.get_json(silent=True))
