"""Repositório de dados SQLite para conversas e interações do domínio Outreach.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def obter_conversa_por_place_id(conexao, place_id: str) -> Optional[Dict[str, Any]]:
    linha = conexao.execute(
        "SELECT * FROM outreach_conversations WHERE place_id = ?", (place_id,)
    ).fetchone()
    return dict(linha) if linha else None


def obter_conversa_por_id(conexao, conversation_id: int) -> Optional[Dict[str, Any]]:
    linha = conexao.execute(
        "SELECT * FROM outreach_conversations WHERE id = ?", (conversation_id,)
    ).fetchone()
    return dict(linha) if linha else None


def criar_conversa(
    conexao,
    place_id: str,
    active_sequence_id: Optional[int] = None,
    status: str = "open",
    last_interaction_at: Optional[str] = None,
    last_inbound_at: Optional[str] = None,
    last_outbound_at: Optional[str] = None,
    next_action_type: Optional[str] = None,
    next_action_at: Optional[str] = None,
    next_action_note: Optional[str] = None,
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> Dict[str, Any]:
    cursor = conexao.execute(
        """
        INSERT INTO outreach_conversations (
            place_id, active_sequence_id, status, last_interaction_at,
            last_inbound_at, last_outbound_at, next_action_type,
            next_action_at, next_action_note, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            place_id,
            active_sequence_id,
            status,
            last_interaction_at,
            last_inbound_at,
            last_outbound_at,
            next_action_type,
            next_action_at,
            next_action_note,
            created_at,
            updated_at,
        ),
    )
    conv_id = cursor.lastrowid
    return obter_conversa_por_id(conexao, conv_id)


def atualizar_conversa(conexao, conversation_id: int, **campos) -> Optional[Dict[str, Any]]:
    if not campos:
        return obter_conversa_por_id(conexao, conversation_id)

    set_clauses = []
    valores = []
    for chave, valor in campos.items():
        set_clauses.append(f"{chave} = ?")
        valores.append(valor)

    valores.append(conversation_id)
    sql = f"UPDATE outreach_conversations SET {', '.join(set_clauses)} WHERE id = ?"
    conexao.execute(sql, valores)
    return obter_conversa_por_id(conexao, conversation_id)


def criar_interacao(
    conexao,
    conversation_id: int,
    direction: str,
    interaction_type: str,
    channel: str,
    occurred_at: str,
    created_at: str,
    content: Optional[str] = None,
    sequence_id: Optional[int] = None,
    sequence_step_id: Optional[int] = None,
    classification: Optional[str] = None,
    objection_type: Optional[str] = None,
) -> Dict[str, Any]:
    cursor = conexao.execute(
        """
        INSERT INTO outreach_interactions (
            conversation_id, sequence_id, sequence_step_id, direction,
            interaction_type, channel, content, classification,
            objection_type, occurred_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            conversation_id,
            sequence_id,
            sequence_step_id,
            direction,
            interaction_type,
            channel,
            content,
            classification,
            objection_type,
            occurred_at,
            created_at,
        ),
    )
    inter_id = cursor.lastrowid
    return obter_interacao_por_id(conexao, inter_id)


def obter_interacao_por_id(conexao, interaction_id: int) -> Optional[Dict[str, Any]]:
    linha = conexao.execute(
        "SELECT * FROM outreach_interactions WHERE id = ?", (interaction_id,)
    ).fetchone()
    return dict(linha) if linha else None


def obter_interacoes_conversa(conexao, conversation_id: int) -> List[Dict[str, Any]]:
    linhas = conexao.execute(
        """
        SELECT * FROM outreach_interactions
        WHERE conversation_id = ?
        ORDER BY occurred_at ASC, id ASC
        """,
        (conversation_id,),
    ).fetchall()
    return [dict(l) for l in linhas]


def atualizar_interacao(conexao, interaction_id: int, **campos) -> Optional[Dict[str, Any]]:
    if not campos:
        return obter_interacao_por_id(conexao, interaction_id)

    set_clauses = []
    valores = []
    for chave, valor in campos.items():
        set_clauses.append(f"{chave} = ?")
        valores.append(valor)

    valores.append(interaction_id)
    sql = f"UPDATE outreach_interactions SET {', '.join(set_clauses)} WHERE id = ?"
    conexao.execute(sql, valores)
    return obter_interacao_por_id(conexao, interaction_id)


def excluir_interacao(conexao, interaction_id: int) -> bool:
    cursor = conexao.execute(
        "DELETE FROM outreach_interactions WHERE id = ?", (interaction_id,)
    )
    return cursor.rowcount > 0
