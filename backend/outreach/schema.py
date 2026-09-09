"""Schema das tabelas conversion_packs e conversion_pack_versions.

Armazena a estratégia comercial unificada, mensagens de cadência, tratamento de objeções
e diretrizes do protótipo visual (Landing Page) por lead.
"""

import json
import logging

from lp.template_catalog import normalizar_template_key

logger = logging.getLogger(__name__)

TABELA_CONVERSION_PACKS_SQL = """
CREATE TABLE IF NOT EXISTS conversion_packs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT NOT NULL UNIQUE,
    landing_page_id INTEGER,
    strategy_json TEXT NOT NULL,
    messages_json TEXT NOT NULL,
    objections_json TEXT NOT NULL,
    prototype_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    provider TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    approved_at TEXT,
    FOREIGN KEY (place_id)
        REFERENCES leads(place_id)
        ON DELETE CASCADE,
    FOREIGN KEY (landing_page_id)
        REFERENCES landing_pages(id)
        ON DELETE SET NULL
);
"""

INDICES_CONVERSION_PACKS_SQL = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_conversion_packs_place_id ON conversion_packs(place_id)",
    "CREATE INDEX IF NOT EXISTS idx_conversion_packs_landing_page_id ON conversion_packs(landing_page_id)",
    "CREATE INDEX IF NOT EXISTS idx_conversion_packs_status ON conversion_packs(status)",
    "CREATE INDEX IF NOT EXISTS idx_conversion_packs_updated_at ON conversion_packs(updated_at DESC)",
]

TABELA_CONVERSION_PACK_VERSIONS_SQL = """
CREATE TABLE IF NOT EXISTS conversion_pack_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversion_pack_id INTEGER NOT NULL,
    version INTEGER NOT NULL,
    snapshot_json TEXT NOT NULL,
    change_type TEXT NOT NULL,
    provider TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversion_pack_id)
        REFERENCES conversion_packs(id)
        ON DELETE CASCADE
);
"""

INDICES_CONVERSION_PACK_VERSIONS_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_pack_versions_pack_id ON conversion_pack_versions(conversion_pack_id)",
    "CREATE INDEX IF NOT EXISTS idx_pack_versions_pack_ver ON conversion_pack_versions(conversion_pack_id, version)",
]


TABELA_OUTREACH_SEQUENCES_SQL = """
CREATE TABLE IF NOT EXISTS outreach_sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT NOT NULL,
    conversion_pack_id INTEGER NOT NULL,
    conversion_pack_version INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    current_step_order INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    paused_at TEXT,
    resumed_at TEXT,
    completed_at TEXT,
    stopped_at TEXT,
    stop_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (place_id)
        REFERENCES leads(place_id)
        ON DELETE CASCADE,
    FOREIGN KEY (conversion_pack_id)
        REFERENCES conversion_packs(id)
        ON DELETE CASCADE
);
"""

INDICES_OUTREACH_SEQUENCES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_sequences_place_id ON outreach_sequences(place_id)",
    "CREATE INDEX IF NOT EXISTS idx_sequences_pack_id ON outreach_sequences(conversion_pack_id)",
    "CREATE INDEX IF NOT EXISTS idx_sequences_status ON outreach_sequences(status)",
]

TABELA_OUTREACH_SEQUENCE_STEPS_SQL = """
CREATE TABLE IF NOT EXISTS outreach_sequence_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_id INTEGER NOT NULL,
    step_order INTEGER NOT NULL,
    step_type TEXT NOT NULL,
    objective TEXT,
    message_snapshot TEXT NOT NULL,
    delay_days INTEGER NOT NULL DEFAULT 0,
    scheduled_for TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    channel TEXT NOT NULL DEFAULT 'whatsapp',
    sent_at TEXT,
    skipped_at TEXT,
    cancelled_at TEXT,
    failure_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (sequence_id)
        REFERENCES outreach_sequences(id)
        ON DELETE CASCADE,
    UNIQUE(sequence_id, step_order)
);
"""

INDICES_OUTREACH_SEQUENCE_STEPS_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_steps_seq_order ON outreach_sequence_steps(sequence_id, step_order)",
    "CREATE INDEX IF NOT EXISTS idx_steps_status ON outreach_sequence_steps(status)",
    "CREATE INDEX IF NOT EXISTS idx_steps_scheduled ON outreach_sequence_steps(scheduled_for)",
    "CREATE INDEX IF NOT EXISTS idx_steps_status_sched ON outreach_sequence_steps(status, scheduled_for)",
]


TABELA_OUTREACH_CONVERSATIONS_SQL = """
CREATE TABLE IF NOT EXISTS outreach_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT NOT NULL UNIQUE,
    active_sequence_id INTEGER,
    status TEXT NOT NULL DEFAULT 'open',
    last_interaction_at TEXT,
    last_inbound_at TEXT,
    last_outbound_at TEXT,
    next_action_type TEXT,
    next_action_at TEXT,
    next_action_note TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (place_id)
        REFERENCES leads(place_id)
        ON DELETE CASCADE,
    FOREIGN KEY (active_sequence_id)
        REFERENCES outreach_sequences(id)
        ON DELETE SET NULL
);
"""

INDICES_OUTREACH_CONVERSATIONS_SQL = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_conversations_place_id ON outreach_conversations(place_id)",
    "CREATE INDEX IF NOT EXISTS idx_conversations_status ON outreach_conversations(status)",
]

TABELA_OUTREACH_INTERACTIONS_SQL = """
CREATE TABLE IF NOT EXISTS outreach_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sequence_id INTEGER,
    sequence_step_id INTEGER,
    direction TEXT NOT NULL,
    interaction_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    content TEXT,
    classification TEXT,
    objection_type TEXT,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id)
        REFERENCES outreach_conversations(id)
        ON DELETE CASCADE,
    FOREIGN KEY (sequence_id)
        REFERENCES outreach_sequences(id)
        ON DELETE SET NULL,
    FOREIGN KEY (sequence_step_id)
        REFERENCES outreach_sequence_steps(id)
        ON DELETE SET NULL
);
"""

INDICES_OUTREACH_INTERACTIONS_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_interactions_conv_id ON outreach_interactions(conversation_id)",
    "CREATE INDEX IF NOT EXISTS idx_interactions_occurred_at ON outreach_interactions(occurred_at DESC)",
]


def migrar_template_legacy_conversion_packs(conexao) -> int:
    """Normaliza o template do estado atual dos packs sem alterar versão ou timestamps."""
    alterados = 0
    linhas = conexao.execute("SELECT id, prototype_json FROM conversion_packs").fetchall()
    for pack_id, prototype_json in linhas:
        try:
            prototype = json.loads(prototype_json)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(prototype, dict) or prototype.get("templateKey") != "clean_pro":
            continue
        prototype["templateKey"] = normalizar_template_key(prototype["templateKey"])
        conexao.execute(
            "UPDATE conversion_packs SET prototype_json = ? WHERE id = ?",
            (json.dumps(prototype, ensure_ascii=False), pack_id),
        )
        alterados += 1
    return alterados


def migrar_outreach(conexao):
    """Cria as tabelas do domínio de outreach (packs, versões, sequências, etapas, conversas e interações) e seus índices.
    Idempotente: seguro para rodar múltiplas vezes no startup."""
    conexao.execute(TABELA_CONVERSION_PACKS_SQL)
    for idx_sql in INDICES_CONVERSION_PACKS_SQL:
        conexao.execute(idx_sql)
    migrar_template_legacy_conversion_packs(conexao)

    conexao.execute(TABELA_CONVERSION_PACK_VERSIONS_SQL)
    for idx_sql in INDICES_CONVERSION_PACK_VERSIONS_SQL:
        conexao.execute(idx_sql)

    conexao.execute(TABELA_OUTREACH_SEQUENCES_SQL)
    for idx_sql in INDICES_OUTREACH_SEQUENCES_SQL:
        conexao.execute(idx_sql)

    conexao.execute(TABELA_OUTREACH_SEQUENCE_STEPS_SQL)
    for idx_sql in INDICES_OUTREACH_SEQUENCE_STEPS_SQL:
        conexao.execute(idx_sql)

    conexao.execute(TABELA_OUTREACH_CONVERSATIONS_SQL)
    for idx_sql in INDICES_OUTREACH_CONVERSATIONS_SQL:
        conexao.execute(idx_sql)

    conexao.execute(TABELA_OUTREACH_INTERACTIONS_SQL)
    for idx_sql in INDICES_OUTREACH_INTERACTIONS_SQL:
        conexao.execute(idx_sql)

    conexao.commit()
    logger.debug("Migrações de outreach executadas com sucesso.")
