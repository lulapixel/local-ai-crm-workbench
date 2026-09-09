"""Serviço orquestrador para o Histórico de Conversas e Tratamento de Respostas (Outreach Conversations).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import db
from ia import executar_com_fallback
from outreach.conversations_repository import (
    atualizar_conversa as repo_atualizar_conversa,
    atualizar_interacao as repo_atualizar_interacao,
    criar_conversa as repo_criar_conversa,
    criar_interacao as repo_criar_interacao,
    excluir_interacao as repo_excluir_interacao,
    obter_conversa_por_id as repo_obter_conversa_por_id,
    obter_conversa_por_place_id as repo_obter_conversa_por_place_id,
    obter_interacao_por_id as repo_obter_interacao_por_id,
    obter_interacoes_conversa as repo_obter_interacoes_conversa,
)
from outreach.service import obter_pacote_por_place_id as obter_pack_por_place_id
from outreach.sequences_repository import obter_sequencia_ativa_por_lead

logger = logging.getLogger(__name__)

CLASSIFICACOES_PERMITIDAS = {
    "interested": "Interessado",
    "requested_information": "Pediu mais informações",
    "requested_price": "Pediu preço",
    "requested_callback": "Pediu contato depois",
    "not_now": "Não é o momento",
    "declined": "Recusou",
    "already_has_provider": "Já possui fornecedor",
    "invalid_contact": "Contato inválido",
    "wrong_person": "Pessoa errada",
    "won": "Venda fechada",
    "other": "Outro",
}

MAREADOR_PROXIMA_ACAO = {
    "interested": ("reply", "Responder e agendar demonstração/reunião"),
    "requested_information": ("reply", "Enviar mais informações sobre o serviço"),
    "requested_price": ("send_proposal", "Enviar proposta comercial"),
    "requested_callback": ("follow_up_later", "Retornar contato na data agendada"),
    "not_now": ("follow_up_later", "Agendar acompanhamento futuro"),
    "declined": ("close_as_lost", "Encerrar prospecção como perdida"),
    "already_has_provider": ("close_as_lost", "Encerrar prospecção (já possui fornecedor)"),
    "invalid_contact": ("close_as_lost", "Marcar contato como inválido"),
    "wrong_person": ("manual", "Identificar responsável correto"),
    "won": ("close_as_won", "Venda fechada - iniciar integração"),
    "other": ("manual", "Analisar resposta manualmente"),
}


def _iso_utc_agora() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
        + "Z"
    )


def obter_ou_criar_conversa(conexao, place_id: str) -> Dict[str, Any]:
    """Obtém a conversa existente para o place_id ou cria uma nova em estado 'open'."""
    conv = repo_obter_conversa_por_place_id(conexao, place_id)
    if conv:
        return conv

    # Verifica se existe sequência ativa
    seq_ativa = obter_sequencia_ativa_por_lead(conexao, place_id)
    seq_id = seq_ativa["id"] if seq_ativa else None

    agora = _iso_utc_agora()
    return repo_criar_conversa(
        conexao=conexao,
        place_id=place_id,
        active_sequence_id=seq_id,
        status="open",
        created_at=agora,
        updated_at=agora,
    )


def obter_conversa_completa(place_id: str) -> Dict[str, Any]:
    """Retorna os dados da conversa do lead juntamente com sua timeline de interações."""
    conexao = db.conectar()
    try:
        conv = obter_ou_criar_conversa(conexao, place_id)
        interacoes = repo_obter_interacoes_conversa(conexao, conv["id"])
        conv["interactions"] = interacoes
        return conv
    finally:
        conexao.close()


def registrar_resposta_lead(
    place_id: str,
    classification: str,
    content: str,
    channel: str = "whatsapp",
    occurred_at: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Registra uma resposta inbound recebida do prospect, interrompe sequências ativas
    e calcula deterministicamente a próxima ação comercial."""
    if classification not in CLASSIFICACOES_PERMITIDAS:
        raise ValueError(f"Classificação '{classification}' é inválida.")

    agora = _iso_utc_agora()
    data_ocorrencia = occurred_at or agora

    conexao = db.conectar()
    try:
        # Transação SQLite
        conexao.execute("BEGIN TRANSACTION")

        conv = repo_obter_conversa_por_place_id(conexao, place_id)
        if not conv:
            conv = repo_criar_conversa(
                conexao=conexao,
                place_id=place_id,
                status="open",
                created_at=agora,
                updated_at=agora,
            )

        # 1. Interrompe sequência ativa se houver
        seq_ativa = obter_sequencia_ativa_por_lead(conexao, place_id)
        seq_id = seq_ativa["id"] if seq_ativa else None
        if seq_ativa:
            # Cancela etapas pendentes/ready
            conexao.execute(
                """
                UPDATE outreach_sequence_steps
                SET status = 'cancelled', cancelled_at = ?
                WHERE sequence_id = ? AND status IN ('pending', 'ready')
                """,
                (agora, seq_ativa["id"]),
            )
            # Atualiza status da sequência para 'replied'
            conexao.execute(
                """
                UPDATE outreach_sequences
                SET status = 'replied', stopped_at = ?, stop_reason = 'replied', updated_at = ?
                WHERE id = ?
                """,
                (agora, agora, seq_ativa["id"]),
            )

        # 2. Registra interação Inbound Response
        interacao = repo_criar_interacao(
            conexao=conexao,
            conversation_id=conv["id"],
            sequence_id=seq_id,
            direction="inbound",
            interaction_type="response",
            channel=channel,
            content=content,
            classification=classification,
            occurred_at=data_ocorrencia,
            created_at=agora,
        )

        # Se houver observação do usuário, grava como nota interna
        if note and note.strip():
            repo_criar_interacao(
                conexao=conexao,
                conversation_id=conv["id"],
                direction="internal",
                interaction_type="note",
                channel=channel,
                content=note.strip(),
                occurred_at=data_ocorrencia,
                created_at=agora,
            )

        # 3. Determina próximo estado e ação comercial
        proxima_acao_tipo, proxima_acao_nota = MAREADOR_PROXIMA_ACAO.get(
            classification, ("manual", "Analisar resposta")
        )

        novo_status_conversa = "waiting_user"
        if classification == "won":
            novo_status_conversa = "won"
        elif classification in ("declined", "already_has_provider", "invalid_contact"):
            novo_status_conversa = "lost"

        # Atualiza a conversa
        conv_atualizada = repo_atualizar_conversa(
            conexao,
            conv["id"],
            active_sequence_id=None,
            status=novo_status_conversa,
            last_interaction_at=data_ocorrencia,
            last_inbound_at=data_ocorrencia,
            next_action_type=proxima_acao_tipo,
            next_action_note=proxima_acao_nota,
            updated_at=agora,
        )

        # Atualiza status legado no lead
        status_lead_novo = "respondido"
        if classification == "won":
            status_lead_novo = "venda_fechada"
        elif classification in ("declined", "already_has_provider", "invalid_contact"):
            status_lead_novo = "perdido"

        conexao.execute(
            "UPDATE leads SET status = ? WHERE place_id = ?",
            (status_lead_novo, place_id),
        )

        conexao.commit()

        interacoes = repo_obter_interacoes_conversa(conexao, conv["id"])
        conv_atualizada["interactions"] = interacoes
        return conv_atualizada

    except Exception:
        conexao.rollback()
        logger.exception("Erro ao registrar resposta do lead %s", place_id)
        raise
    finally:
        conexao.close()


def registrar_nota_interna(place_id: str, content: str, channel: str = "whatsapp") -> Dict[str, Any]:
    """Registra uma observação interna do usuário na conversa do lead."""
    if not content or not content.strip():
        raise ValueError("O conteúdo da nota não pode ser vazio.")

    agora = _iso_utc_agora()
    conexao = db.conectar()
    try:
        conv = obter_ou_criar_conversa(conexao, place_id)
        repo_criar_interacao(
            conexao=conexao,
            conversation_id=conv["id"],
            direction="internal",
            interaction_type="note",
            channel=channel,
            content=content.strip(),
            occurred_at=agora,
            created_at=agora,
        )
        repo_atualizar_conversa(
            conexao, conv["id"], last_interaction_at=agora, updated_at=agora
        )
        conexao.commit()
        return obter_conversa_completa(place_id)
    finally:
        conexao.close()


def registrar_ligacao(
    place_id: str,
    content: Optional[str] = None,
    classification: Optional[str] = None,
    objection_type: Optional[str] = None,
    channel: str = "phone",
) -> Dict[str, Any]:
    """Registra um contato via ligação telefônica."""
    agora = _iso_utc_agora()
    conexao = db.conectar()
    try:
        conv = obter_ou_criar_conversa(conexao, place_id)
        repo_criar_interacao(
            conexao=conexao,
            conversation_id=conv["id"],
            direction="outbound",
            interaction_type="call",
            channel=channel,
            content=content,
            classification=classification,
            objection_type=objection_type,
            occurred_at=agora,
            created_at=agora,
        )
        repo_atualizar_conversa(
            conexao, conv["id"], last_interaction_at=agora, last_outbound_at=agora, updated_at=agora
        )
        conexao.commit()
        return obter_conversa_completa(place_id)
    finally:
        conexao.close()


def atualizar_interacao_existente(
    interaction_id: int,
    classification: Optional[str] = None,
    content: Optional[str] = None,
    objection_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Edita a classificação ou conteúdo de uma interação manual existente."""
    conexao = db.conectar()
    try:
        inter = repo_obter_interacao_por_id(conexao, interaction_id)
        if not inter:
            raise ValueError(f"Interação #{interaction_id} não encontrada.")

        campos = {}
        if classification is not None:
            if classification and classification not in CLASSIFICACOES_PERMITIDAS:
                raise ValueError(f"Classificação '{classification}' é inválida.")
            campos["classification"] = classification
            # Se for resposta inbound, atualiza também a próxima ação sugerida
            if inter["interaction_type"] == "response" and classification in MAREADOR_PROXIMA_ACAO:
                next_act, next_note = MAREADOR_PROXIMA_ACAO[classification]
                repo_atualizar_conversa(
                    conexao,
                    inter["conversation_id"],
                    next_action_type=next_act,
                    next_action_note=next_note,
                )

        if content is not None:
            campos["content"] = content
        if objection_type is not None:
            campos["objection_type"] = objection_type

        repo_atualizar_interacao(conexao, interaction_id, **campos)
        conexao.commit()

        conv = repo_obter_conversa_por_id(conexao, inter["conversation_id"])
        return obter_conversa_completa(conv["place_id"])
    finally:
        conexao.close()


def excluir_interacao_existente(interaction_id: int) -> Dict[str, Any]:
    """Exclui uma interação manual. Impede a exclusão de mensagens enviadas por automação."""
    conexao = db.conectar()
    try:
        inter = repo_obter_interacao_por_id(conexao, interaction_id)
        if not inter:
            raise ValueError(f"Interação #{interaction_id} não encontrada.")

        if inter["direction"] == "outbound" and inter.get("sequence_step_id"):
            raise ValueError("Mensagens enviadas por sequências automáticas não podem ser apagadas.")

        conv = repo_obter_conversa_por_id(conexao, inter["conversation_id"])
        place_id = conv["place_id"]

        repo_excluir_interacao(conexao, interaction_id)
        conexao.commit()

        return obter_conversa_completa(place_id)
    finally:
        conexao.close()


def sugerir_resposta_assistida(interaction_id: int) -> Dict[str, Any]:
    """Gera uma sugestão de resposta curta assistida por IA baseada na resposta recebida."""
    conexao = db.conectar()
    try:
        inter = repo_obter_interacao_por_id(conexao, interaction_id)
        if not inter:
            raise ValueError(f"Interação #{interaction_id} não encontrada.")

        conv = repo_obter_conversa_por_id(conexao, inter["conversation_id"])
        place_id = conv["place_id"]

        # Busca dados do lead
        linha_lead = conexao.execute(
            "SELECT nome, nicho, categoria, cidade FROM leads WHERE place_id = ?", (place_id,)
        ).fetchone()
        lead_nome = linha_lead["nome"] if linha_lead else "Cliente"

        # Busca pacote de conversão do lead para estratégia e objeções
        pack = obter_pack_por_place_id(place_id)
        estrategia = pack.get("strategy") or {} if pack else {}
        objecoes = pack.get("objections") or [] if pack else []

        # Mensagens anteriores enviadas
        interacoes = repo_obter_interacoes_conversa(conexao, conv["id"])
        mensagens_enviadas = [
            i["content"] for i in interacoes if i["direction"] == "outbound" and i.get("content")
        ]

        resposta_recebida = inter.get("content") or ""
        classificacao = inter.get("classification") or "interested"
        label_classificacao = CLASSIFICACOES_PERMITIDAS.get(classificacao, classificacao)

        # Gera sugestão via IA com fallback determinístico
        sugestao = None
        try:
            system_prompt = (
                "Você é um consultor comercial B2B experiente. Seu objetivo é sugerir "
                "uma resposta muito curta, empática, direta e profissional (no máximo 3 frases) "
                "para ser enviada via WhatsApp ao prospect."
            )
            user_prompt = (
                f"Lead: {lead_nome}\n"
                f"Estratégia comercial: {estrategia.get('commercialAngle', 'Abordagem consultiva')}\n"
                f"Mensagens já enviadas: {' | '.join(mensagens_enviadas[-2:])}\n"
                f"Resposta do cliente: \"{resposta_recebida}\"\n"
                f"Classificação: {label_classificacao}\n"
                f"Objeções conhecidas: {objecoes}\n"
            )
            res, _, _ = executar_com_fallback(
                system=system_prompt,
                user=user_prompt,
                descricao_log="sugerir resposta assistida",
            )
            sugestao = res
        except Exception:
            logger.warning("Falha ao chamar IA para sugestão de resposta. Usando fallback.")

        if not sugestao or not sugestao.strip():
            # Fallback determinístico por classificação
            if classificacao in ("requested_price", "requested_information"):
                sugestao = f"Perfeito, {lead_nome}! Montei um resumo objetivo do que podemos fazer pela sua empresa. Posso te enviar por aqui ou prefere um rápido bate-papo de 5 minutos?"
            elif classificacao == "interested":
                sugestao = f"Excelente, {lead_nome}! Qual o melhor horário para conversarmos brevemente sobre como implementar essa estrutura no seu negócio?"
            elif classificacao == "requested_callback":
                sugestao = f"Combinado, {lead_nome}! Entro em contato novamente na data solicitada. Um abraço!"
            else:
                sugestao = f"Entendido, {lead_nome}! Agradeço pelo retorno. Fico à disposição se precisar futuramente."

        return {
            "interaction_id": interaction_id,
            "place_id": place_id,
            "received_response": resposta_recebida,
            "classification": classificacao,
            "suggested_reply": sugestao.strip(),
        }

    finally:
        conexao.close()
