"""Serviço orquestrador para a Régua Operacional Persistida (Outreach Sequences).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import db
from outreach.repository import obter_por_id as obter_pack_por_id
from outreach.sequences_repository import (
    atualizar_etapa,
    atualizar_etapas_vencidas,
    atualizar_status_sequencia,
    obter_etapa_por_id,
    obter_etapas_sequencia,
    obter_sequencia_ativa_por_lead,
    obter_sequencia_por_id,
    obter_sequencia_por_pack_id,
    salvar_nova_sequencia,
)

logger = logging.getLogger(__name__)


class SequenceConflictError(Exception):
    """Exceção lançada quando já existe uma sequência ativa com outra versão."""
    pass


def _iso_utc_agora() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
        + "Z"
    )


def _utc_naive_agora() -> datetime:
    """Retorna UTC sem tzinfo para preservar o contrato ISO legado do banco."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_iso(data_str: str) -> datetime:
    if data_str.endswith("Z"):
        data_str = data_str[:-1]
    return datetime.fromisoformat(data_str)


def _sincronizar_campos_legados_lead(conexao, place_id: str, sequence_id: int):
    """Sincroniza os campos legados (follow_ups_enviados, ultimo_followup_em, proximo_followup)
    na tabela leads para manter compatibilidade com relatórios existentes.
    """
    etapas = obter_etapas_sequencia(conexao, sequence_id)
    sequencia = obter_sequencia_por_id(conexao, sequence_id)

    if not sequencia or not etapas:
        return

    # Apenas etapas de follow-up contam (step_order 1, 2, 3)
    etapas_fu_enviadas = [
        e for e in etapas if e["step_order"] > 0 and e["status"] == "sent"
    ]
    follow_ups_enviados = len(etapas_fu_enviadas)

    # Último envio
    todas_enviadas = [e for e in etapas if e["status"] == "sent" and e.get("sent_at")]
    ultimo_followup_em = (
        max(e["sent_at"] for e in todas_enviadas) if todas_enviadas else None
    )

    # Próximo follow-up agendado (etapa pronta ou pendente)
    proximo_followup = None
    if sequencia["status"] == "active":
        futuras = [
            e for e in etapas if e["status"] in ("ready", "pending") and e.get("scheduled_for")
        ]
        if futuras:
            proximo_followup = min(e["scheduled_for"] for e in futuras)

    conexao.execute(
        """
        UPDATE leads
        SET follow_ups_enviados = ?,
            ultimo_followup_em = ?,
            proximo_followup = ?
        WHERE place_id = ?
        """,
        (follow_ups_enviados, ultimo_followup_em, proximo_followup, place_id),
    )
    conexao.commit()


def iniciar_sequencia(pack_id: int, channel: str = "whatsapp") -> Dict[str, Any]:
    """Inicia a régua de abordagem persistida a partir de um Pacote de Conversão Aprovado."""
    conexao = db.conectar()
    try:
        pacote = obter_pack_por_id(conexao, pack_id)
        if not pacote:
            raise ValueError(f"Pacote de conversão #{pack_id} não encontrado.")

        if pacote["status"] != "approved":
            raise ValueError("Apenas pacotes no status 'approved' podem iniciar uma sequência.")

        initial_msg = (pacote.get("messages") or {}).get("initial", "")
        if not (initial_msg or "").strip():
            raise ValueError("O pacote de conversão não possui mensagem inicial para envio.")

        place_id = pacote["placeId"]
        versao_pacote = pacote["version"]

        # Verifica se já existe sequência ativa para este lead
        seq_ativa = obter_sequencia_ativa_por_lead(conexao, place_id)
        if seq_ativa:
            if (
                seq_ativa["conversion_pack_id"] == pack_id
                and seq_ativa["conversion_pack_version"] == versao_pacote
            ):
                # Idempotência: mesma sequência ativa
                return formatar_detalhes_sequencia(conexao, seq_ativa["id"])
            else:
                # Conflito 409
                raise SequenceConflictError(
                    f"Existe uma sequência ativa (versão {seq_ativa['conversion_pack_version']}) "
                    f"para o lead. Cancele-a antes de iniciar uma nova."
                )

        # Monta dados das 4 etapas a partir das mensagens aprovadas do pacote (SNAPSHOT)
        msgs = pacote.get("messages") or {}
        followups = msgs.get("followups") or []

        fu1_obj = followups[0].get("objective") if len(followups) > 0 else "Confirmar se conseguiu visualizar"
        fu1_msg = followups[0].get("message") if len(followups) > 0 else "Oi, tudo bem? Conseguiram dar uma olhada na mensagem anterior?"

        fu2_obj = followups[1].get("objective") if len(followups) > 1 else "Reforçar oportunidade comercial"
        fu2_msg = followups[1].get("message") if len(followups) > 1 else "Olá! Sei que a rotina é corrida. Se fizer sentido, posso mostrar como aumentar agendamentos."

        fu3_obj = followups[2].get("objective") if len(followups) > 2 else "Encerramento educado"
        fu3_msg = followups[2].get("message") if len(followups) > 2 else "Entendido! Vou encerrar os contatos por aqui pra não incomodar."

        agora_dt = _utc_naive_agora()
        agora_str = agora_dt.isoformat(timespec="seconds") + "Z"

        dt_fu1 = (agora_dt + timedelta(days=2)).isoformat(timespec="seconds") + "Z"
        dt_fu2 = (agora_dt + timedelta(days=5)).isoformat(timespec="seconds") + "Z"
        dt_fu3 = (agora_dt + timedelta(days=9)).isoformat(timespec="seconds") + "Z"

        steps_data = [
            {
                "step_order": 0,
                "step_type": "initial",
                "objective": "Mensagem inicial de abordagem",
                "message_snapshot": initial_msg,
                "delay_days": 0,
                "scheduled_for": agora_str,
                "status": "ready",
            },
            {
                "step_order": 1,
                "step_type": "followup",
                "objective": fu1_obj,
                "message_snapshot": fu1_msg,
                "delay_days": 2,
                "scheduled_for": dt_fu1,
                "status": "pending",
            },
            {
                "step_order": 2,
                "step_type": "followup",
                "objective": fu2_obj,
                "message_snapshot": fu2_msg,
                "delay_days": 5,
                "scheduled_for": dt_fu2,
                "status": "pending",
            },
            {
                "step_order": 3,
                "step_type": "followup",
                "objective": fu3_obj,
                "message_snapshot": fu3_msg,
                "delay_days": 9,
                "scheduled_for": dt_fu3,
                "status": "pending",
            },
        ]

        seq = salvar_nova_sequencia(
            conexao=conexao,
            place_id=place_id,
            conversion_pack_id=pack_id,
            conversion_pack_version=versao_pacote,
            channel=channel,
            steps_data=steps_data,
        )

        _sincronizar_campos_legados_lead(conexao, place_id, seq["id"])
        return formatar_detalhes_sequencia(conexao, seq["id"])

    finally:
        conexao.close()


def formatar_detalhes_sequencia(conexao, sequence_id: int) -> Dict[str, Any]:
    """Formata o retorno completo da sequência com verificação de etapas vencidas e flags de versão."""
    atualizar_etapas_vencidas(conexao, sequence_id)

    seq = obter_sequencia_por_id(conexao, sequence_id)
    if not seq:
        raise ValueError(f"Sequência #{sequence_id} não encontrada.")

    etapas = obter_etapas_sequencia(conexao, sequence_id)

    # Próxima etapa ativa
    next_step = None
    if seq["status"] in ("active", "paused"):
        for e in etapas:
            if e["status"] in ("ready", "pending"):
                next_step = e
                break

    # Verifica se o pacote de conversão atual mudou a versão em relação à sequência
    pacote = obter_pack_por_id(conexao, seq["conversion_pack_id"])
    version_outdated = False
    if pacote and pacote["version"] > seq["conversion_pack_version"]:
        version_outdated = True

    return {
        "id": seq["id"],
        "place_id": seq["place_id"],
        "conversion_pack_id": seq["conversion_pack_id"],
        "conversion_pack_version": seq["conversion_pack_version"],
        "version_outdated": version_outdated,
        "status": seq["status"],
        "channel": seq["channel"],
        "current_step_order": seq["current_step_order"],
        "started_at": seq["started_at"],
        "paused_at": seq.get("paused_at"),
        "resumed_at": seq.get("resumed_at"),
        "completed_at": seq.get("completed_at"),
        "stopped_at": seq.get("stopped_at"),
        "stop_reason": seq.get("stop_reason"),
        "created_at": seq["created_at"],
        "updated_at": seq["updated_at"],
        "next_step": next_step,
        "steps": etapas,
    }


def obter_sequencia_detalhes(
    sequence_id: Optional[int] = None, pack_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    conexao = db.conectar()
    try:
        if sequence_id:
            return formatar_detalhes_sequencia(conexao, sequence_id)
        elif pack_id:
            seq = obter_sequencia_por_pack_id(conexao, pack_id)
            if not seq:
                return None
            return formatar_detalhes_sequencia(conexao, seq["id"])
        return None
    finally:
        conexao.close()


def marcar_etapa_enviada(
    step_id: int, sent_at: Optional[str] = None, channel: str = "whatsapp"
) -> Dict[str, Any]:
    """Marca uma etapa como enviada pelo usuário, ajustando a cadência futura, campos legados
    e criando transacionalmente a interação no histórico de conversas."""
    from outreach.conversations_repository import (
        atualizar_conversa,
        criar_conversa,
        criar_interacao,
        obter_conversa_por_place_id,
    )

    conexao = db.conectar()
    try:
        conexao.execute("BEGIN TRANSACTION")

        etapa = obter_etapa_por_id(conexao, step_id)
        if not etapa:
            raise ValueError(f"Etapa #{step_id} não encontrada.")

        seq = obter_sequencia_por_id(conexao, etapa["sequence_id"])
        if not seq:
            raise ValueError("Sequência associada não encontrada.")

        if seq["status"] != "active":
            raise ValueError(f"Não é possível enviar etapas em uma sequência '{seq['status']}'.")

        if etapa["status"] != "ready":
            raise ValueError(f"Apenas etapas no estado 'ready' podem ser marcadas como enviadas (status atual: '{etapa['status']}').")

        # Verifica se etapas anteriores já foram concluídas
        etapas_anteriores = conexao.execute(
            """
            SELECT status FROM outreach_sequence_steps
            WHERE sequence_id = ? AND step_order < ?
            """,
            (seq["id"], etapa["step_order"]),
        ).fetchall()
        if not all(a["status"] in ("sent", "skipped") for a in etapas_anteriores):
            raise ValueError("Existem etapas anteriores pendentes de confirmação.")

        tempo_envio = sent_at or _iso_utc_agora()
        dt_envio = _parse_iso(tempo_envio)

        # Marca etapa atual como sent
        atualizar_etapa(conexao, step_id, status="sent", sent_at=tempo_envio)

        # Se for a mensagem inicial (step_order == 0), recalcula datas dos follow-ups baseados no envio REAL
        if etapa["step_order"] == 0:
            etapas_todas = obter_etapas_sequencia(conexao, seq["id"])
            for e in etapas_todas:
                if e["step_order"] > 0 and e["status"] in ("pending", "ready"):
                    dt_nova = dt_envio + timedelta(days=e["delay_days"])
                    str_nova = dt_nova.isoformat(timespec="seconds") + "Z"
                    status_novo = "ready" if dt_nova <= _utc_naive_agora() else "pending"
                    atualizar_etapa(conexao, e["id"], status=status_novo, scheduled_for=str_nova)

        # Verifica próxima ordem de etapa
        proxima_ordem = etapa["step_order"] + 1
        etapas_atualizadas = obter_etapas_sequencia(conexao, seq["id"])
        etapas_restantes = [e for e in etapas_atualizadas if e["status"] in ("pending", "ready")]

        if not etapas_restantes:
            # Todas as etapas foram sent/skipped -> Conclui sequência
            atualizar_status_sequencia(
                conexao,
                sequence_id=seq["id"],
                status="completed",
                current_step_order=etapa["step_order"],
                completed_at=tempo_envio,
            )
        else:
            atualizar_status_sequencia(
                conexao,
                sequence_id=seq["id"],
                status="active",
                current_step_order=proxima_ordem,
            )

        _sincronizar_campos_legados_lead(conexao, seq["place_id"], seq["id"])

        # Cria ou atualiza a conversa do lead e adiciona a interação outbound
        place_id = seq["place_id"]
        canal_efetivo = channel or etapa.get("channel", "whatsapp")
        conv = obter_conversa_por_place_id(conexao, place_id)
        if not conv:
            conv = criar_conversa(
                conexao=conexao,
                place_id=place_id,
                active_sequence_id=seq["id"],
                status="waiting_lead",
                last_interaction_at=tempo_envio,
                last_outbound_at=tempo_envio,
                created_at=tempo_envio,
                updated_at=tempo_envio,
            )
        else:
            atualizar_conversa(
                conexao=conexao,
                conversation_id=conv["id"],
                active_sequence_id=seq["id"],
                status="waiting_lead",
                last_interaction_at=tempo_envio,
                last_outbound_at=tempo_envio,
                updated_at=tempo_envio,
            )

        criar_interacao(
            conexao=conexao,
            conversation_id=conv["id"],
            sequence_id=seq["id"],
            sequence_step_id=step_id,
            direction="outbound",
            interaction_type="message",
            channel=canal_efetivo,
            content=etapa.get("message_snapshot") or etapa.get("message", ""),
            occurred_at=tempo_envio,
            created_at=_iso_utc_agora(),
        )

        conexao.commit()
        return formatar_detalhes_sequencia(conexao, seq["id"])

    except Exception:
        conexao.rollback()
        logger.exception("Erro ao marcar etapa %d como enviada", step_id)
        raise
    finally:
        conexao.close()


def pular_etapa(step_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
    """Pula a execução de uma etapa."""
    conexao = db.conectar()
    try:
        etapa = obter_etapa_por_id(conexao, step_id)
        if not etapa:
            raise ValueError(f"Etapa #{step_id} não encontrada.")

        seq = obter_sequencia_por_id(conexao, etapa["sequence_id"])
        if not seq:
            raise ValueError("Sequência associada não encontrada.")

        if etapa["status"] not in ("pending", "ready"):
            raise ValueError(f"Apenas etapas 'pending' ou 'ready' podem ser puladas (status atual: '{etapa['status']}').")

        agora = _iso_utc_agora()
        atualizar_etapa(conexao, step_id, status="skipped", skipped_at=agora)

        proxima_ordem = etapa["step_order"] + 1
        etapas_atualizadas = obter_etapas_sequencia(conexao, seq["id"])
        etapas_restantes = [e for e in etapas_atualizadas if e["status"] in ("pending", "ready")]

        if not etapas_restantes:
            atualizar_status_sequencia(
                conexao,
                sequence_id=seq["id"],
                status="completed",
                current_step_order=etapa["step_order"],
                completed_at=agora,
            )
        else:
            atualizar_status_sequencia(
                conexao,
                sequence_id=seq["id"],
                status="active",
                current_step_order=proxima_ordem,
            )

        _sincronizar_campos_legados_lead(conexao, seq["place_id"], seq["id"])
        return formatar_detalhes_sequencia(conexao, seq["id"])
    finally:
        conexao.close()


def reagendar_etapa(step_id: int, scheduled_for_iso: str) -> Dict[str, Any]:
    """Reagenda a data de disparo de uma etapa pendente ou pronta."""
    conexao = db.conectar()
    try:
        etapa = obter_etapa_por_id(conexao, step_id)
        if not etapa:
            raise ValueError(f"Etapa #{step_id} não encontrada.")

        if etapa["status"] == "sent":
            raise ValueError("Não é possível reagendar uma etapa já enviada.")

        dt_reagendada = _parse_iso(scheduled_for_iso)
        iso_formatado = dt_reagendada.isoformat(timespec="seconds") + "Z"

        status_novo = "ready" if dt_reagendada <= _utc_naive_agora() else "pending"

        atualizar_etapa(conexao, step_id, status=status_novo, scheduled_for=iso_formatado)

        _sincronizar_campos_legados_lead(conexao, etapa["sequence_id"], etapa["sequence_id"])
        seq = obter_sequencia_por_id(conexao, etapa["sequence_id"])
        return formatar_detalhes_sequencia(conexao, seq["id"])
    finally:
        conexao.close()


def pausar_sequencia(sequence_id: int) -> Dict[str, Any]:
    """Pausa uma sequência ativa."""
    conexao = db.conectar()
    try:
        seq = obter_sequencia_por_id(conexao, sequence_id)
        if not seq:
            raise ValueError(f"Sequência #{sequence_id} não encontrada.")

        if seq["status"] != "active":
            raise ValueError(f"Apenas sequências ativas podem ser pausadas (status atual: '{seq['status']}').")

        agora = _iso_utc_agora()
        res = atualizar_status_sequencia(conexao, sequence_id, status="paused", paused_at=agora)
        _sincronizar_campos_legados_lead(conexao, seq["place_id"], sequence_id)
        return formatar_detalhes_sequencia(conexao, sequence_id)
    finally:
        conexao.close()


def retomar_sequencia(sequence_id: int) -> Dict[str, Any]:
    """Retoma uma sequência pausada, deslocando as datas das etapas futuras pelo tempo da pausa."""
    conexao = db.conectar()
    try:
        seq = obter_sequencia_por_id(conexao, sequence_id)
        if not seq:
            raise ValueError(f"Sequência #{sequence_id} não encontrada.")

        if seq["status"] != "paused":
            raise ValueError(f"Apenas sequências pausadas podem ser retomadas (status atual: '{seq['status']}').")

        agora_dt = _utc_naive_agora()
        agora_str = agora_dt.isoformat(timespec="seconds") + "Z"

        # Calcula duração da pausa
        paused_at_dt = _parse_iso(seq["paused_at"]) if seq.get("paused_at") else agora_dt
        duracao_pausa = agora_dt - paused_at_dt
        if duracao_pausa.total_seconds() < 0:
            duracao_pausa = timedelta(seconds=0)

        # Desloca agendamento de todas as etapas não concluídas
        etapas = obter_etapas_sequencia(conexao, sequence_id)
        for e in etapas:
            if e["status"] in ("pending", "ready") and e.get("scheduled_for"):
                dt_antiga = _parse_iso(e["scheduled_for"])
                dt_nova = dt_antiga + duracao_pausa
                iso_nova = dt_nova.isoformat(timespec="seconds") + "Z"
                status_novo = "ready" if dt_nova <= agora_dt else "pending"
                atualizar_etapa(conexao, e["id"], status=status_novo, scheduled_for=iso_nova)

        atualizar_status_sequencia(conexao, sequence_id, status="active", resumed_at=agora_str)
        _sincronizar_campos_legados_lead(conexao, seq["place_id"], sequence_id)
        return formatar_detalhes_sequencia(conexao, sequence_id)
    finally:
        conexao.close()


def interromper_sequencia(sequence_id: int, reason: str = "replied") -> Dict[str, Any]:
    """Interrompe/cancela a sequência (ex: quando o cliente responde ou desiste)."""
    conexao = db.conectar()
    try:
        seq = obter_sequencia_por_id(conexao, sequence_id)
        if not seq:
            raise ValueError(f"Sequência #{sequence_id} não encontrada.")

        agora = _iso_utc_agora()
        novo_status = "replied" if reason == "replied" else "cancelled"

        # Cancela todas as etapas pendentes/prontas
        etapas = obter_etapas_sequencia(conexao, sequence_id)
        for e in etapas:
            if e["status"] in ("pending", "ready"):
                atualizar_etapa(conexao, e["id"], status="cancelled", cancelled_at=agora)

        atualizar_status_sequencia(
            conexao,
            sequence_id=sequence_id,
            status=novo_status,
            stopped_at=agora,
            stop_reason=reason,
        )

        _sincronizar_campos_legados_lead(conexao, seq["place_id"], sequence_id)
        return formatar_detalhes_sequencia(conexao, sequence_id)
    finally:
        conexao.close()


def interromper_sequencias_por_pacote_arquivado(conexao, pack_id: int):
    """Callback invocado quando um ConversionPack é arquivado."""
    seq = obter_sequencia_por_pack_id(conexao, pack_id)
    if seq and seq["status"] in ("active", "paused"):
        agora = _iso_utc_agora()
        etapas = obter_etapas_sequencia(conexao, seq["id"])
        for e in etapas:
            if e["status"] in ("pending", "ready"):
                atualizar_etapa(conexao, e["id"], status="cancelled", cancelled_at=agora)

        atualizar_status_sequencia(
            conexao,
            sequence_id=seq["id"],
            status="cancelled",
            stopped_at=agora,
            stop_reason="pack_archived",
        )
        _sincronizar_campos_legados_lead(conexao, seq["place_id"], seq["id"])
