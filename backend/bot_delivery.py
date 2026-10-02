"""Conectores preparados; ativação externa e destinatário exato exigidos.

Nenhum token é recebido pela API/browser ou registrado no banco.
"""
import hashlib
import json
import os
import re
import threading

import requests
from flask import Blueprint, request

import bot

bp = Blueprint("bot_delivery", __name__)


def preparar_banco(c):
    c.executescript("""
        CREATE TABLE IF NOT EXISTS bot_deliveries (
            id INTEGER PRIMARY KEY, message_id INTEGER NOT NULL UNIQUE,
            channel TEXT NOT NULL, recipient TEXT NOT NULL, final_text TEXT NOT NULL,
            payload_json TEXT NOT NULL, state TEXT NOT NULL, provider_id TEXT,
            approved_at TEXT NOT NULL, error TEXT,
            FOREIGN KEY(message_id) REFERENCES bot_messages(id) ON DELETE CASCADE
        );
    """)


def readiness():
    email = all(os.environ.get(k) for k in ("PROSPECTOS_RESEND_API_KEY", "PROSPECTOS_EMAIL_FROM"))
    whatsapp = all(os.environ.get(k) for k in ("PROSPECTOS_WA_TOKEN", "PROSPECTOS_WA_PHONE_ID", "PROSPECTOS_WA_API_VERSION", "PROSPECTOS_WA_TEMPLATE", "PROSPECTOS_WA_TEMPLATE_BODY"))
    return {"email": bool(email), "whatsapp": bool(whatsapp), "live_enabled": os.environ.get("PROSPECTOS_BOT_LIVE_SENDS") == "1",
            "note": "Conectores preparados. Requerem conta, remetente e credenciais locais. A aprovação autoriza apenas esta mensagem e este destinatário."}


def preview(message_id, body):
    if not isinstance(body, dict) or body.get("channel") not in ("email", "whatsapp"):
        raise ValueError("Escolha e-mail ou WhatsApp oficial.")
    with bot.conectar() as c:
        m = bot._message(c, message_id)
        contact = bot._validar_destino(c, m)
        if m["state"] != "approved" or m["approved_text"] != m["text"] or m["approved_contact"] != contact:
            raise bot.Conflict("Revise e aprove a mensagem atual antes de preparar o envio.")
    channel = body["channel"]
    if channel == "email":
        recipient = body.get("recipient", "")
        if not isinstance(recipient, str) or len(recipient) > 254 or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", recipient):
            raise ValueError("Informe o e-mail verificado do destinatário, sem inferir endereços.")
        final = m["text"]
        payload = {"from": os.environ.get("PROSPECTOS_EMAIL_FROM", ""), "to": [recipient], "subject": "Uma ideia para seu negócio", "text": final}
    else:
        template = os.environ.get("PROSPECTOS_WA_TEMPLATE_BODY", "")
        if template.count("{{1}}") != 1 or re.search(r"\{\{(?!1\}\})", template):
            raise bot.Conflict("Configure o corpo exato do template aprovado no WhatsApp, com um parâmetro {{1}}.")
        recipient = contact.removeprefix("https://wa.me/")
        final = template.replace("{{1}}", m["text"])
        payload = {"messaging_product": "whatsapp", "to": recipient, "type": "template",
                   "template": {"name": os.environ.get("PROSPECTOS_WA_TEMPLATE", ""), "language": {"code": os.environ.get("PROSPECTOS_WA_LANGUAGE", "pt_BR")},
                                "components": [{"type": "body", "parameters": [{"type": "text", "text": m["text"]}]}]}}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return {"channel": channel, "recipient": recipient, "final_text": final, "payload": payload,
            "fingerprint": fingerprint, "ready": readiness()[channel] and readiness()["live_enabled"]}


def aprovar_envio(message_id, body):
    view = preview(message_id, body)
    if not view["ready"]:
        raise bot.Conflict("Envio não ativado. Configure o serviço e habilite envios locais primeiro.")
    if body.get("consent") is not True or body.get("fingerprint") != view["fingerprint"]:
        raise bot.Conflict("Revise o texto final e destinatário e confirme a autorização de contato nesse canal.")
    with bot.conectar() as c:
        c.execute("BEGIN IMMEDIATE")
        # Nova checagem dentro da transação impede uma edição entre prévia e reserva.
        m = bot._message(c, message_id)
        contact = bot._validar_destino(c, m)
        if m["state"] != "approved" or m["approved_text"] != m["text"] or m["approved_contact"] != contact:
            raise bot.Conflict("Aprovação da mensagem mudou. Refaça a revisão.")
        parameters_text = view["payload"]["text"] if view["channel"] == "email" else view["payload"]["template"]["components"][0]["parameters"][0]["text"]
        if parameters_text != m["text"]:
            raise bot.Conflict("O texto mudou durante a revisão.")
        existing = c.execute("SELECT id,state FROM bot_deliveries WHERE message_id=?", (message_id,)).fetchone()
        payload_json = json.dumps(view["payload"], ensure_ascii=False)
        if existing:
            if existing["state"] != "blocked":
                raise bot.Conflict("Já existe uma tentativa de envio para esta mensagem. Consulte o resultado antes de repetir.")
            delivery_id = existing["id"]
            c.execute("UPDATE bot_deliveries SET channel=?,recipient=?,final_text=?,payload_json=?,state='queued',approved_at=?,error=NULL WHERE id=?",
                      (view["channel"],view["recipient"],view["final_text"],payload_json,bot.agora(),delivery_id))
        else:
            cur = c.execute("INSERT INTO bot_deliveries(message_id,channel,recipient,final_text,payload_json,state,approved_at) VALUES(?,?,?,?,?,'queued',?)",
                            (message_id, view["channel"], view["recipient"], view["final_text"], payload_json, bot.agora()))
            delivery_id = cur.lastrowid
    try:
        threading.Thread(target=enviar, args=(delivery_id,), daemon=True).start()
    except RuntimeError:
        with bot.conectar() as c:
            c.execute("UPDATE bot_deliveries SET state='blocked',error='Não foi possível iniciar; nenhuma chamada efetuada.' WHERE id=?", (delivery_id,))
        raise bot.Conflict("Não foi possível iniciar o envio.")
    return {"delivery_id": delivery_id}


def enviar(delivery_id):
    attempted = False
    try:
        with bot.conectar() as c:
            c.execute("BEGIN IMMEDIATE")
            row = c.execute("SELECT * FROM bot_deliveries WHERE id=? AND state='queued'", (delivery_id,)).fetchone()
            if not row:
                return
            delivery = dict(row)
            m = bot._message(c, delivery["message_id"])
            bot._validar_destino(c, m)
            view = preview(m["id"], {"channel": delivery["channel"], "recipient": delivery["recipient"]})
            if not view["ready"] or view["payload"] != json.loads(delivery["payload_json"]):
                raise bot.Conflict("Mensagem, destino, remetente ou template mudou. Envio bloqueado.")
            c.execute("UPDATE bot_deliveries SET state='sending' WHERE id=?", (delivery_id,))
        payload = json.loads(delivery["payload_json"])
        if delivery["channel"] == "email":
            url = "https://api.resend.com/emails"
            headers = {"Authorization": "Bearer " + os.environ["PROSPECTOS_RESEND_API_KEY"], "Idempotency-Key": f"prospectos-bot-{delivery_id}-{hashlib.sha256(delivery['approved_at'].encode()).hexdigest()[:16]}"}
        else:
            version, phone_id = os.environ["PROSPECTOS_WA_API_VERSION"], os.environ["PROSPECTOS_WA_PHONE_ID"]
            if not re.fullmatch(r"v\d+\.\d+", version) or not phone_id.isdigit():
                raise bot.Conflict("Versão ou identificador da API WhatsApp inválido.")
            url = f"https://graph.facebook.com/{version}/{phone_id}/messages"
            headers = {"Authorization": "Bearer " + os.environ["PROSPECTOS_WA_TOKEN"]}
        attempted = True
        response = requests.post(url, json=payload, headers=headers, timeout=(10, 30), allow_redirects=False)
        if not 200 <= response.status_code < 300:
            raise bot.Conflict(f"O provedor retornou HTTP {response.status_code}. Confira o painel do serviço antes de repetir.")
        result = response.json()
        provider_id = result.get("id") if delivery["channel"] == "email" else (result.get("messages") or [{}])[0].get("id")
        if not isinstance(provider_id, str) or not provider_id:
            raise bot.Conflict("O provedor não devolveu um identificador. Verifique o resultado antes de repetir.")
        with bot.conectar() as c:
            c.execute("UPDATE bot_deliveries SET state='provider_accepted',provider_id=? WHERE id=?", (provider_id, delivery_id))
        # Aceitação não prova leitura/entrega. Atualização do CRM ocorre apenas se a aprovação continuar válida.
        try:
            bot.agir(m["id"], "sent", {"confirmado": True})
        except (ValueError, bot.Conflict):
            with bot.conectar() as c:
                c.execute("UPDATE bot_deliveries SET error='Aceito pelo provedor; atualização do CRM requer reconciliação.' WHERE id=?", (delivery_id,))
    except Exception as exc:
        with bot.conectar() as c:
            c.execute("UPDATE bot_deliveries SET state=?,error=? WHERE id=?", ("unknown" if attempted else "blocked",
                      str(exc) if isinstance(exc, bot.Conflict) else "Resultado incerto; verifique o provedor. Sem repetição automática.", delivery_id))


def painel():
    with bot.conectar() as c:
        rows = [dict(r) for r in c.execute("SELECT id,message_id,channel,recipient,state,provider_id,error FROM bot_deliveries ORDER BY id DESC LIMIT 50")]
    return {**readiness(), "deliveries": rows}


def recuperar():
    with bot.conectar() as c:
        c.execute("UPDATE bot_deliveries SET state='unknown',error='Backend reiniciado; conferir provedor antes de repetir.' WHERE state IN ('queued','sending')")


@bp.get("/api/bot/delivery")
def get_delivery():
    return bot._responder(painel)


@bp.post("/api/bot/messages/<int:message_id>/delivery-preview")
def post_preview(message_id):
    return bot._responder(preview, message_id, request.get_json(silent=True))


@bp.post("/api/bot/messages/<int:message_id>/approve-delivery")
def post_delivery(message_id):
    return bot._responder(aprovar_envio, message_id, request.get_json(silent=True), status=202)
