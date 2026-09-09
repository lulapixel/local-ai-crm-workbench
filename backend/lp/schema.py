"""Schema da tabela lp_briefs - armazena os briefs de LP gerados por IA.

A tabela guarda um spec JSON com as seções de copy de alta conversão
(hero, prova_social, features, pricing, faq, objeções) por lead.
"""

# Schema com idempotência (CREATE TABLE IF NOT EXISTS) - seguro rodar
# múltiplas vezes no startup. FK para leads por place_id.
TABELA_LP_BRIEFS_SQL = """
CREATE TABLE IF NOT EXISTS lp_briefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT NOT NULL,
    landing_page_id INTEGER,
    change_type TEXT DEFAULT 'initial_generation',
    sections_json TEXT,
    restored_from_version INTEGER,
    description TEXT,
    spec_json TEXT NOT NULL,
    provedor TEXT,
    versao INTEGER NOT NULL DEFAULT 1,
    gerado_em TEXT NOT NULL,
    FOREIGN KEY (place_id) REFERENCES leads(place_id) ON DELETE CASCADE,
    FOREIGN KEY (landing_page_id) REFERENCES landing_pages(id) ON DELETE CASCADE
)
"""

# Índices pra consultas comuns: listar briefs por lead, por LP e ordenar por data.
INDICES_LP_BRIEFS_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_lp_briefs_place_id ON lp_briefs(place_id)",
    "CREATE INDEX IF NOT EXISTS idx_lp_briefs_landing_page_id ON lp_briefs(landing_page_id)",
    "CREATE INDEX IF NOT EXISTS idx_lp_briefs_gerado_em ON lp_briefs(gerado_em DESC)",
]


TABELA_LANDING_PAGES_SQL = """
CREATE TABLE IF NOT EXISTS landing_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    template_key TEXT NOT NULL,
    current_spec_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    schema_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    published_at TEXT,
    FOREIGN KEY (place_id)
        REFERENCES leads(place_id)
        ON DELETE CASCADE
)
"""

INDICES_LANDING_PAGES_SQL = [
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_landing_pages_slug ON landing_pages(slug)",
    "CREATE INDEX IF NOT EXISTS idx_landing_pages_status ON landing_pages(status)",
    "CREATE INDEX IF NOT EXISTS idx_landing_pages_place_id ON landing_pages(place_id)",
]


def migrar_lp_briefs(conexao):
    """Cria a tabela lp_briefs e seus índices se ainda não existirem.
    Idempotente: pode ser chamada múltiplas vezes sem efeito colateral."""
    conexao.execute(TABELA_LP_BRIEFS_SQL)

    # Migração incremental idempotente para bancos pré-existentes
    colunas_existentes = [
        row["name"] if isinstance(row, dict) or hasattr(row, "keys") else row[1]
        for row in conexao.execute("PRAGMA table_info(lp_briefs)").fetchall()
    ]

    novas_colunas = [
        ("landing_page_id", "INTEGER"),
        ("change_type", "TEXT"),
        ("sections_json", "TEXT"),
        ("restored_from_version", "INTEGER"),
        ("description", "TEXT"),
    ]

    for nome_coluna, tipo_coluna in novas_colunas:
        if nome_coluna not in colunas_existentes:
            conexao.execute(f"ALTER TABLE lp_briefs ADD COLUMN {nome_coluna} {tipo_coluna}")

    for indice_sql in INDICES_LP_BRIEFS_SQL:
        conexao.execute(indice_sql)
    conexao.commit()



def migrar_landing_pages(conexao):
    """Cria a tabela landing_pages e seus índices se ainda não existirem.
    Idempotente."""
    conexao.execute(TABELA_LANDING_PAGES_SQL)

    colunas_existentes = [
        row["name"] if isinstance(row, dict) or hasattr(row, "keys") else row[1]
        for row in conexao.execute("PRAGMA table_info(landing_pages)").fetchall()
    ]

    novas_colunas = [
        ("public_id", "TEXT"),
        ("public_url", "TEXT"),
        ("publish_provider", "TEXT"),
        ("publication_revision", "INTEGER DEFAULT 0"),
        ("last_published_at", "TEXT"),
        ("unpublished_at", "TEXT"),
    ]

    for nome_coluna, tipo_coluna in novas_colunas:
        if nome_coluna not in colunas_existentes:
            conexao.execute(f"ALTER TABLE landing_pages ADD COLUMN {nome_coluna} {tipo_coluna}")

    for indice_sql in INDICES_LANDING_PAGES_SQL:
        conexao.execute(indice_sql)
    conexao.commit()


TABELA_LANDING_PAGE_EVENTS_SQL = """
CREATE TABLE IF NOT EXISTS landing_page_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    landing_page_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    session_id TEXT,
    metadata_json TEXT,
    occurred_at TEXT NOT NULL,
    FOREIGN KEY (landing_page_id)
        REFERENCES landing_pages(id)
        ON DELETE CASCADE
)
"""

INDICES_LANDING_PAGE_EVENTS_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_lp_events_lp_id ON landing_page_events(landing_page_id)",
    "CREATE INDEX IF NOT EXISTS idx_lp_events_type ON landing_page_events(event_type)",
    "CREATE INDEX IF NOT EXISTS idx_lp_events_occurred_at ON landing_page_events(occurred_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_lp_events_lp_date ON landing_page_events(landing_page_id, occurred_at)",
]


def migrar_landing_page_events(conexao):
    """Cria a tabela landing_page_events e seus índices se ainda não existirem."""
    conexao.execute(TABELA_LANDING_PAGE_EVENTS_SQL)
    for indice_sql in INDICES_LANDING_PAGE_EVENTS_SQL:
        conexao.execute(indice_sql)
    conexao.commit()


def migrar_template_clean_pro_para_geral_conversao(conexao):
    """Converte o legado clean_pro sem tocar em timestamps ou outros dados.

    Retorna a quantidade de landing pages alteradas para permitir regressão
    explícita da migração idempotente.
    """
    cursor = conexao.execute(
        "UPDATE landing_pages SET template_key = ? WHERE template_key = ?",
        ("geral-conversao", "clean_pro"),
    )
    conexao.commit()
    return cursor.rowcount


def migrar_lp(conexao):
    """Executa todas as migrações do domínio de Landing Pages."""
    migrar_lp_briefs(conexao)
    migrar_landing_pages(conexao)
    migrar_template_clean_pro_para_geral_conversao(conexao)
    migrar_landing_page_events(conexao)
