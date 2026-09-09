"""Repository para consultas agregadas do Cockpit Diário de Prospecção.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import db


def _calcular_limites_dia_utc(date_str: str) -> Tuple[str, str]:
    """Calcula o início (00:00:00Z) e fim (23:59:59Z) do dia em formato UTC ISO string."""
    try:
        dt = datetime.fromisoformat(date_str.split("T")[0])
    except Exception:
        dt = datetime.now(timezone.utc).replace(tzinfo=None)

    inicio = dt.strftime("%Y-%m-%dT00:00:00Z")
    fim = dt.strftime("%Y-%m-%dT23:59:59Z")
    return inicio, fim


def obter_contadores_cockpit_diario(
    conexao: sqlite3.Connection,
    date_str: str,
    tz_str: str = "America/Recife"
) -> Dict[str, int]:
    """Calcula as contagens globais das categorias do cockpit diário."""
    inicio_dia, fim_dia = _calcular_limites_dia_utc(date_str)

    # 1. Overdue (atrasados)
    overdue = conexao.execute(
        """
        SELECT COUNT(*) FROM outreach_sequence_steps st
        JOIN outreach_sequences s ON st.sequence_id = s.id
        WHERE s.status = 'active'
          AND st.status = 'ready'
          AND st.scheduled_for < ?
        """,
        (inicio_dia,),
    ).fetchone()[0]

    # 2. Ready Today (prontos hoje)
    ready_today = conexao.execute(
        """
        SELECT COUNT(*) FROM outreach_sequence_steps st
        JOIN outreach_sequences s ON st.sequence_id = s.id
        WHERE s.status = 'active'
          AND st.status = 'ready'
          AND st.scheduled_for >= ?
        """,
        (inicio_dia,),
    ).fetchone()[0]

    # 3. New Contacts (novos pacotes aprovados sem sequência ativa)
    new_contacts = conexao.execute(
        """
        SELECT COUNT(*) FROM conversion_packs cp
        WHERE cp.status = 'approved'
          AND cp.place_id NOT IN (
              SELECT place_id FROM outreach_sequences WHERE status IN ('active', 'paused')
          )
        """,
    ).fetchone()[0]

    # 4. Paused (sequências pausadas)
    paused = conexao.execute(
        "SELECT COUNT(*) FROM outreach_sequences WHERE status = 'paused'",
    ).fetchone()[0]

    # 5. Replied / Respostas Pendentes (conversas aguardando usuário ou sequências respondidas)
    replied_recently = conexao.execute(
        """
        SELECT COUNT(DISTINCT place_id) FROM (
            SELECT place_id FROM outreach_sequences WHERE status = 'replied'
            UNION
            SELECT place_id FROM outreach_conversations WHERE status = 'waiting_user'
        )
        """,
    ).fetchone()[0]

    # 6. Upcoming (próximas etapas futuras)
    upcoming = conexao.execute(
        """
        SELECT COUNT(*) FROM outreach_sequence_steps st
        JOIN outreach_sequences s ON st.sequence_id = s.id
        WHERE s.status = 'active'
          AND st.status = 'pending'
          AND st.scheduled_for > ?
        """,
        (fim_dia,),
    ).fetchone()[0]

    return {
        "overdue": overdue,
        "ready_today": ready_today,
        "new_contacts": new_contacts,
        "paused": paused,
        "replied_recently": replied_recently,
        "upcoming": upcoming,
    }


def buscar_itens_cockpit_diario(
    conexao: sqlite3.Connection,
    date_str: str,
    tz_str: str = "America/Recife",
    category: str = "all",
    search: str = "",
    channel: str = "all",
    min_score: Optional[float] = None,
    page: int = 1,
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """Busca e prioriza as ações do cockpit diário (seleciona 1 etapa por sequência ou conversa respondida)."""
    inicio_dia, fim_dia = _calcular_limites_dia_utc(date_str)
    agora_utc = (
        datetime.now(timezone.utc)
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
        + "Z"
    )

    # Seleciona a próxima etapa ativa/pendente por sequência (mínimo step_order)
    sql_steps = """
        SELECT
            'sequence_step' as action_type,
            s.id as sequence_id,
            s.status as sequence_status,
            s.conversion_pack_version as sequence_pack_version,
            st.id as step_id,
            st.step_order,
            st.step_type,
            st.objective,
            st.message_snapshot as message,
            st.scheduled_for,
            st.status as step_status,
            l.place_id,
            l.nome,
            l.categoria,
            l.nicho,
            l.cidade,
            l.nota,
            l.num_avaliacoes,
            l.telefone,
            l.whatsapp_link,
            l.site_status,
            cp.id as pack_id,
            cp.status as pack_status,
            cp.version as pack_version,
            cp.strategy_json,
            lp.id as lp_id,
            lp.status as lp_status,
            lp.public_url as lp_public_url,
            lp.slug as lp_slug,
            conv.id as conv_id,
            conv.status as conv_status,
            conv.next_action_type as conv_next_action_type,
            conv.next_action_note as conv_next_action_note,
            conv.last_inbound_at as conv_last_inbound_at
        FROM outreach_sequence_steps st
        JOIN outreach_sequences s ON st.sequence_id = s.id
        JOIN leads l ON s.place_id = l.place_id
        LEFT JOIN conversion_packs cp ON s.conversion_pack_id = cp.id
        LEFT JOIN landing_pages lp ON l.place_id = lp.place_id
        LEFT JOIN outreach_conversations conv ON l.place_id = conv.place_id
        WHERE st.id IN (
            SELECT id FROM outreach_sequence_steps
            WHERE sequence_id = s.id AND status IN ('ready', 'pending')
            ORDER BY step_order ASC
            LIMIT 1
        )
        OR (s.status IN ('paused', 'replied') AND st.step_order = (
            SELECT MIN(step_order) FROM outreach_sequence_steps WHERE sequence_id = s.id
        ))
    """

    # Novos contatos (Pacotes aprovados sem sequência ativa)
    sql_new = """
        SELECT
            'new_contact' as action_type,
            NULL as sequence_id,
            NULL as sequence_status,
            NULL as sequence_pack_version,
            NULL as step_id,
            NULL as step_order,
            NULL as step_type,
            'Iniciar sequência de abordagem' as objective,
            cp.messages_json as message,
            NULL as scheduled_for,
            'approved' as step_status,
            l.place_id,
            l.nome,
            l.categoria,
            l.nicho,
            l.cidade,
            l.nota,
            l.num_avaliacoes,
            l.telefone,
            l.whatsapp_link,
            l.site_status,
            cp.id as pack_id,
            cp.status as pack_status,
            cp.version as pack_version,
            cp.strategy_json,
            lp.id as lp_id,
            lp.status as lp_status,
            lp.public_url as lp_public_url,
            lp.slug as lp_slug,
            conv.id as conv_id,
            conv.status as conv_status,
            conv.next_action_type as conv_next_action_type,
            conv.next_action_note as conv_next_action_note,
            conv.last_inbound_at as conv_last_inbound_at
        FROM conversion_packs cp
        JOIN leads l ON cp.place_id = l.place_id
        LEFT JOIN landing_pages lp ON l.place_id = lp.place_id
        LEFT JOIN outreach_conversations conv ON l.place_id = conv.place_id
        WHERE cp.status = 'approved'
          AND cp.place_id NOT IN (
              SELECT place_id FROM outreach_sequences WHERE status IN ('active', 'paused')
          )
    """

    linhas_steps = conexao.execute(sql_steps).fetchall()
    linhas_new = conexao.execute(sql_new).fetchall()

    todos_itens = []
    sequencias_vistas = set()

    for r in linhas_steps:
        d = dict(r)
        sid = d["sequence_id"]
        if sid in sequencias_vistas:
            continue
        sequencias_vistas.add(sid)

        st_status = d["step_status"]
        seq_status = d["sequence_status"]
        sched = d["scheduled_for"] or ""

        prioridade = 99
        categoria_item = "other"

        if seq_status == "active":
            if st_status == "ready":
                if sched < inicio_dia:
                    prioridade = 1  # Atrasado
                    categoria_item = "overdue"
                elif sched <= fim_dia or sched <= agora_utc:
                    prioridade = 2  # Pronto hoje
                    categoria_item = "ready_today"
                else:
                    prioridade = 2
                    categoria_item = "ready_today"
            elif st_status == "pending":
                if sched > fim_dia:
                    prioridade = 6  # Próximos
                    categoria_item = "upcoming"
                elif sched <= fim_dia:
                    prioridade = 2
                    categoria_item = "ready_today"
        elif seq_status == "paused":
            prioridade = 5  # Pausado
            categoria_item = "paused"
        elif seq_status == "replied":
            prioridade = 7  # Respondido
            categoria_item = "replied_recently"

        d["priority_rank"] = prioridade
        d["category_item"] = categoria_item
        todos_itens.append(d)

    for r in linhas_new:
        d = dict(r)
        d["priority_rank"] = 4  # Novo pacote aprovado sem sequência
        d["category_item"] = "new_contacts"
        todos_itens.append(d)

    # Filtra por Categoria
    if category != "all":
        if category == "overdue":
            todos_itens = [i for i in todos_itens if i["category_item"] == "overdue"]
        elif category in ("ready_today", "today"):
            todos_itens = [i for i in todos_itens if i["category_item"] in ("ready_today", "overdue")]
        elif category in ("new_contacts", "new"):
            todos_itens = [i for i in todos_itens if i["category_item"] == "new_contacts"]
        elif category == "paused":
            todos_itens = [i for i in todos_itens if i["category_item"] == "paused"]
        elif category == "upcoming":
            todos_itens = [i for i in todos_itens if i["category_item"] == "upcoming"]
        elif category == "replied":
            todos_itens = [i for i in todos_itens if i["category_item"] == "replied_recently"]

    # Filtra por Busca
    if search:
        termo = search.lower().strip()
        todos_itens = [
            i for i in todos_itens
            if termo in (i["nome"] or "").lower()
            or termo in (i["nicho"] or "").lower()
            or termo in (i["cidade"] or "").lower()
        ]

    # Importa a função de cálculo determinístico de score
    from outreach.service import calcular_score_lead

    for i in todos_itens:
        i["score"] = calcular_score_lead(i.get("nota"), i.get("num_avaliacoes"), i.get("site_status"))

    # Filtra por min_score
    if min_score is not None:
        todos_itens = [i for i in todos_itens if (i.get("score") or 0) >= min_score]

    # Ordenação por prioridade
    def chave_ordenacao(i):
        rank = i["priority_rank"]
        sched = i.get("scheduled_for") or "9999-99-99"
        avaliacoes = i.get("num_avaliacoes") or 0
        nome = (i.get("nome") or "").lower()
        return (rank, sched, -avaliacoes, nome)

    todos_itens.sort(key=chave_ordenacao)

    # Paginação
    offset = (page - 1) * page_size
    itens_paginados = todos_itens[offset : offset + page_size]

    return itens_paginados
