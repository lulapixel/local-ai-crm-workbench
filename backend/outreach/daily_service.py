"""Serviço orquestrador para o Cockpit Diário de Prospecção (Daily Outreach Cockpit).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import db
from outreach.daily_repository import (
    buscar_itens_cockpit_diario,
    obter_contadores_cockpit_diario,
)
from outreach.sequences_repository import atualizar_etapas_vencidas
from outreach.service import calcular_score_lead

logger = logging.getLogger(__name__)


def obter_cockpit_diario(
    date_str: Optional[str] = None,
    tz_str: str = "America/Recife",
    category: str = "all",
    search: str = "",
    channel: str = "all",
    min_score: Optional[float] = None,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    """Retorna a visão consolidada do Cockpit Diário de Prospecção para a data e filtros especificados."""
    dt_atual = datetime.now(timezone.utc).date().isoformat()
    data_ref = date_str or dt_atual

    conexao = db.conectar()
    try:
        # 1. Garante que todas as etapas vencidas no banco mudem para 'ready'
        atualizar_etapas_vencidas(conexao)

        # 2. Obtém contagens globais das abas/categorias
        counts = obter_contadores_cockpit_diario(conexao, data_ref, tz_str)

        # 3. Busca itens paginados e priorizados
        raw_items = buscar_itens_cockpit_diario(
            conexao=conexao,
            date_str=data_ref,
            tz_str=tz_str,
            category=category,
            search=search,
            channel=channel,
            min_score=min_score,
            page=page,
            page_size=page_size,
        )

        formatted_items = []
        for r in raw_items:
            score = calcular_score_lead(r["nota"], r["num_avaliacoes"], r["site_status"])

            lead_data = {
                "place_id": r["place_id"],
                "name": r["nome"] or "",
                "score": score,
                "niche": r["nicho"] or r["categoria"] or "",
                "city": r["cidade"] or "",
                "phone": r["telefone"] or "",
                "whatsapp_link": r["whatsapp_link"] or "",
                "rating": r["nota"] or 0.0,
                "review_count": r["num_avaliacoes"] or 0,
            }

            has_wa = bool(r.get("whatsapp_link") or r.get("telefone"))
            warnings = []
            if not has_wa:
                warnings.append("missing_whatsapp")

            lp_data = None
            if r.get("lp_id"):
                lp_data = {
                    "id": r["lp_id"],
                    "status": r["lp_status"],
                    "preview_url": f"/landing-pages/{r['lp_id']}/preview" if r.get("lp_id") else "",
                    "public_url": r.get("lp_public_url") or "",
                }
                if r["lp_status"] != "published":
                    warnings.append("landing_page_not_published")
                elif r["lp_status"] == "published" and not r.get("lp_public_url"):
                    warnings.append("prototype_without_public_url")

            sequence_data = None
            step_data = None

            if r["action_type"] == "sequence_step":
                version_outdated = False
                if r.get("pack_version") and r.get("sequence_pack_version"):
                    if r["pack_version"] > r["sequence_pack_version"]:
                        version_outdated = True
                        warnings.append("pack_version_changed")

                sequence_data = {
                    "id": r["sequence_id"],
                    "status": r["sequence_status"],
                    "conversion_pack_version": r["sequence_pack_version"],
                    "version_outdated": version_outdated,
                }

                step_data = {
                    "id": r["step_id"],
                    "step_order": r["step_order"],
                    "step_type": r["step_type"],
                    "objective": r["objective"] or "",
                    "message": r["message"] or "",
                    "scheduled_for": r["scheduled_for"],
                    "status": r["step_status"],
                }

                if not (r["message"] or "").strip():
                    warnings.append("empty_initial_message")
            else:
                # Novo contato (novo pacote aprovado sem sequência)
                msg_ini = ""
                if r.get("message"):
                    try:
                        parsed_msgs = json.loads(r["message"]) if isinstance(r["message"], str) else r["message"]
                        msg_ini = parsed_msgs.get("initial", "")
                    except Exception:
                        msg_ini = str(r["message"])

                if not msg_ini.strip():
                    warnings.append("empty_initial_message")

                step_data = {
                    "id": 0,
                    "step_order": 0,
                    "step_type": "initial",
                    "objective": "Iniciar abordagem inicial",
                    "message": msg_ini,
                    "scheduled_for": None,
                    "status": "ready",
                }

            conversation_data = None
            if r.get("conv_id"):
                # Busca última interação inbound para alimentar o card de resposta
                linha_inbound = conexao.execute(
                    """
                    SELECT content, classification, occurred_at FROM outreach_interactions
                    WHERE conversation_id = ? AND direction = 'inbound'
                    ORDER BY occurred_at DESC, id DESC LIMIT 1
                    """,
                    (r["conv_id"],),
                ).fetchone()

                conversation_data = {
                    "id": r["conv_id"],
                    "status": r.get("conv_status") or "open",
                    "next_action_type": r.get("conv_next_action_type"),
                    "next_action_note": r.get("conv_next_action_note"),
                    "last_inbound_at": r.get("conv_last_inbound_at"),
                    "last_inbound_content": linha_inbound["content"] if linha_inbound else None,
                    "last_inbound_classification": linha_inbound["classification"] if linha_inbound else None,
                }

            formatted_items.append({
                "action_type": r["action_type"],
                "priority": r["category_item"],
                "lead": lead_data,
                "sequence": sequence_data,
                "step": step_data,
                "landing_page": lp_data,
                "conversation": conversation_data,
                "warnings": warnings,
            })

        return {
            "date": data_ref,
            "timezone": tz_str,
            "counts": counts,
            "items": formatted_items,
        }

    finally:
        conexao.close()
