"""Repository para as tabelas outreach_sequences e outreach_sequence_steps.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _linha_para_dict_sequence(linha: Any) -> Optional[Dict[str, Any]]:
    if not linha:
        return None
    d = dict(linha) if hasattr(linha, "keys") or isinstance(linha, sqlite3.Row) else {
        "id": linha[0],
        "place_id": linha[1],
        "conversion_pack_id": linha[2],
        "conversion_pack_version": linha[3],
        "status": linha[4],
        "channel": linha[5],
        "current_step_order": linha[6],
        "started_at": linha[7],
        "paused_at": linha[8],
        "resumed_at": linha[9],
        "completed_at": linha[10],
        "stopped_at": linha[11],
        "stop_reason": linha[12],
        "created_at": linha[13],
        "updated_at": linha[14],
    }
    return {
        "id": d["id"],
        "place_id": d["place_id"],
        "conversion_pack_id": d["conversion_pack_id"],
        "conversion_pack_version": d["conversion_pack_version"],
        "status": d["status"],
        "channel": d["channel"],
        "current_step_order": d["current_step_order"],
        "started_at": d["started_at"],
        "paused_at": d.get("paused_at"),
        "resumed_at": d.get("resumed_at"),
        "completed_at": d.get("completed_at"),
        "stopped_at": d.get("stopped_at"),
        "stop_reason": d.get("stop_reason"),
        "created_at": d["created_at"],
        "updated_at": d["updated_at"],
    }


def _linha_para_dict_step(linha: Any) -> Optional[Dict[str, Any]]:
    if not linha:
        return None
    d = dict(linha) if hasattr(linha, "keys") or isinstance(linha, sqlite3.Row) else {
        "id": linha[0],
        "sequence_id": linha[1],
        "step_order": linha[2],
        "step_type": linha[3],
        "objective": linha[4],
        "message_snapshot": linha[5],
        "delay_days": linha[6],
        "scheduled_for": linha[7],
        "status": linha[8],
        "channel": linha[9],
        "sent_at": linha[10],
        "skipped_at": linha[11],
        "cancelled_at": linha[12],
        "failure_reason": linha[13],
        "created_at": linha[14],
        "updated_at": linha[15],
    }
    return {
        "id": d["id"],
        "sequence_id": d["sequence_id"],
        "step_order": d["step_order"],
        "step_type": d["step_type"],
        "objective": d.get("objective") or "",
        "message": d["message_snapshot"],
        "delay_days": d["delay_days"],
        "scheduled_for": d.get("scheduled_for"),
        "status": d["status"],
        "channel": d["channel"],
        "sent_at": d.get("sent_at"),
        "skipped_at": d.get("skipped_at"),
        "cancelled_at": d.get("cancelled_at"),
        "failure_reason": d.get("failure_reason"),
        "created_at": d["created_at"],
        "updated_at": d["updated_at"],
    }


def obter_sequencia_por_id(conexao: sqlite3.Connection, sequence_id: int) -> Optional[Dict[str, Any]]:
    linha = conexao.execute(
        "SELECT * FROM outreach_sequences WHERE id = ?", (sequence_id,)
    ).fetchone()
    return _linha_para_dict_sequence(linha)


def obter_sequencia_ativa_por_lead(conexao: sqlite3.Connection, place_id: str) -> Optional[Dict[str, Any]]:
    linha = conexao.execute(
        "SELECT * FROM outreach_sequences WHERE place_id = ? AND status IN ('active', 'paused')", (place_id,)
    ).fetchone()
    return _linha_para_dict_sequence(linha)


def obter_sequencia_por_pack_id(conexao: sqlite3.Connection, pack_id: int) -> Optional[Dict[str, Any]]:
    """Obtém a sequência mais recente associada a um pacote."""
    linha = conexao.execute(
        """
        SELECT * FROM outreach_sequences
        WHERE conversion_pack_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (pack_id,),
    ).fetchone()
    return _linha_para_dict_sequence(linha)


def obter_etapas_sequencia(conexao: sqlite3.Connection, sequence_id: int) -> List[Dict[str, Any]]:
    linhas = conexao.execute(
        """
        SELECT * FROM outreach_sequence_steps
        WHERE sequence_id = ?
        ORDER BY step_order ASC
        """,
        (sequence_id,),
    ).fetchall()
    return [_linha_para_dict_step(l) for l in linhas if l]


def obter_etapa_por_id(conexao: sqlite3.Connection, step_id: int) -> Optional[Dict[str, Any]]:
    linha = conexao.execute(
        "SELECT * FROM outreach_sequence_steps WHERE id = ?", (step_id,)
    ).fetchone()
    return _linha_para_dict_step(linha)


def salvar_nova_sequencia(
    conexao: sqlite3.Connection,
    place_id: str,
    conversion_pack_id: int,
    conversion_pack_version: int,
    channel: str,
    steps_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    agora = (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
        + "Z"
    )

    cursor = conexao.execute(
        """
        INSERT INTO outreach_sequences (
            place_id, conversion_pack_id, conversion_pack_version, status, channel,
            current_step_order, started_at, created_at, updated_at
        ) VALUES (?, ?, ?, 'active', ?, 0, ?, ?, ?)
        """,
        (place_id, conversion_pack_id, conversion_pack_version, channel, agora, agora, agora),
    )
    sequence_id = cursor.lastrowid

    for s in steps_data:
        conexao.execute(
            """
            INSERT INTO outreach_sequence_steps (
                sequence_id, step_order, step_type, objective, message_snapshot,
                delay_days, scheduled_for, status, channel, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sequence_id,
                s["step_order"],
                s["step_type"],
                s.get("objective", ""),
                s["message_snapshot"],
                s["delay_days"],
                s.get("scheduled_for"),
                s["status"],
                channel,
                agora,
                agora,
            ),
        )

    conexao.commit()
    seq = obter_sequencia_por_id(conexao, sequence_id)
    seq["steps"] = obter_etapas_sequencia(conexao, sequence_id)
    return seq


def atualizar_status_sequencia(
    conexao: sqlite3.Connection,
    sequence_id: int,
    status: str,
    current_step_order: Optional[int] = None,
    stopped_at: Optional[str] = None,
    stop_reason: Optional[str] = None,
    paused_at: Optional[str] = None,
    resumed_at: Optional[str] = None,
    completed_at: Optional[str] = None,
) -> Dict[str, Any]:
    agora = (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
        + "Z"
    )

    seq = obter_sequencia_por_id(conexao, sequence_id)
    if not seq:
        raise ValueError(f"Sequência #{sequence_id} não encontrada.")

    novo_step_order = current_step_order if current_step_order is not None else seq["current_step_order"]

    conexao.execute(
        """
        UPDATE outreach_sequences
        SET status = ?,
            current_step_order = ?,
            stopped_at = COALESCE(?, stopped_at),
            stop_reason = COALESCE(?, stop_reason),
            paused_at = COALESCE(?, paused_at),
            resumed_at = COALESCE(?, resumed_at),
            completed_at = COALESCE(?, completed_at),
            updated_at = ?
        WHERE id = ?
        """,
        (
            status,
            novo_step_order,
            stopped_at,
            stop_reason,
            paused_at,
            resumed_at,
            completed_at,
            agora,
            sequence_id,
        ),
    )
    conexao.commit()
    res = obter_sequencia_por_id(conexao, sequence_id)
    res["steps"] = obter_etapas_sequencia(conexao, sequence_id)
    return res


def atualizar_etapa(
    conexao: sqlite3.Connection,
    step_id: int,
    status: str,
    sent_at: Optional[str] = None,
    skipped_at: Optional[str] = None,
    cancelled_at: Optional[str] = None,
    scheduled_for: Optional[str] = None,
    failure_reason: Optional[str] = None,
) -> Dict[str, Any]:
    agora = (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
        + "Z"
    )

    etapa = obter_etapa_por_id(conexao, step_id)
    if not etapa:
        raise ValueError(f"Etapa #{step_id} não encontrada.")

    novo_scheduled = scheduled_for if scheduled_for is not None else etapa["scheduled_for"]

    conexao.execute(
        """
        UPDATE outreach_sequence_steps
        SET status = ?,
            sent_at = COALESCE(?, sent_at),
            skipped_at = COALESCE(?, skipped_at),
            cancelled_at = COALESCE(?, cancelled_at),
            scheduled_for = ?,
            failure_reason = COALESCE(?, failure_reason),
            updated_at = ?
        WHERE id = ?
        """,
        (
            status,
            sent_at,
            skipped_at,
            cancelled_at,
            novo_scheduled,
            failure_reason,
            agora,
            step_id,
        ),
    )
    conexao.commit()
    return obter_etapa_por_id(conexao, step_id)


def atualizar_etapas_vencidas(conexao: sqlite3.Connection, sequence_id: Optional[int] = None) -> int:
    """Função de domínio que transforma etapas 'pending' vencidas em 'ready'
    quando scheduled_for <= agora, a sequência está 'active' e as etapas anteriores
    já foram concluídas (sent ou skipped).
    """
    agora = (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
        + "Z"
    )

    sql_cond = "AND s.id = ?" if sequence_id else ""
    params = [agora, sequence_id] if sequence_id else [agora]

    # Busca todas as etapas pending com data <= agora em sequências ativas
    sql = f"""
        SELECT st.id, st.sequence_id, st.step_order
        FROM outreach_sequence_steps st
        JOIN outreach_sequences s ON st.sequence_id = s.id
        WHERE s.status = 'active'
          AND st.status = 'pending'
          AND st.scheduled_for IS NOT NULL
          AND st.scheduled_for <= ?
          {sql_cond}
        ORDER BY st.sequence_id, st.step_order ASC
    """
    candidatas = conexao.execute(sql, params).fetchall()

    alteradas = 0
    for c in candidatas:
        sid = c["sequence_id"]
        order = c["step_order"]

        # Verifica se todas as etapas anteriores foram sent ou skipped
        anteriores = conexao.execute(
            """
            SELECT status FROM outreach_sequence_steps
            WHERE sequence_id = ? AND step_order < ?
            """,
            (sid, order),
        ).fetchall()

        if all(a["status"] in ("sent", "skipped") for a in anteriores):
            conexao.execute(
                """
                UPDATE outreach_sequence_steps
                SET status = 'ready', updated_at = ?
                WHERE id = ?
                """,
                (agora, c["id"]),
            )
            alteradas += 1

    if alteradas > 0:
        conexao.commit()

    return alteradas
