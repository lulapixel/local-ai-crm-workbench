"""Camada de persistência para o domínio de Landing Pages.

Operações SQL seguras para as tabelas `landing_pages` e `lp_briefs`.
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from .template_catalog import normalizar_template_key


def dict_da_linha(linha) -> Optional[Dict[str, Any]]:
    if not linha:
        return None
    d = dict(linha)
    if "current_spec_json" in d and isinstance(d["current_spec_json"], str):
        try:
            d["spec"] = json.loads(d["current_spec_json"])
        except (json.JSONDecodeError, TypeError):
            d["spec"] = {}
    return d


def obter_por_place_id(conexao, place_id: str) -> Optional[Dict[str, Any]]:
    linha = conexao.execute(
        "SELECT * FROM landing_pages WHERE place_id = ?", (place_id,)
    ).fetchone()
    return dict_da_linha(linha)


def obter_por_slug(conexao, slug: str) -> Optional[Dict[str, Any]]:
    linha = conexao.execute(
        "SELECT * FROM landing_pages WHERE slug = ?", (slug,)
    ).fetchone()
    return dict_da_linha(linha)


def obter_por_id(conexao, lp_id: int) -> Optional[Dict[str, Any]]:
    linha = conexao.execute(
        "SELECT * FROM landing_pages WHERE id = ?", (lp_id,)
    ).fetchone()
    return dict_da_linha(linha)


def slug_existe(conexao, slug: str, ignore_id: Optional[int] = None) -> bool:
    if ignore_id:
        row = conexao.execute(
            "SELECT 1 FROM landing_pages WHERE slug = ? AND id != ?", (slug, ignore_id)
        ).fetchone()
    else:
        row = conexao.execute(
            "SELECT 1 FROM landing_pages WHERE slug = ?", (slug,)
        ).fetchone()
    return row is not None


def obter_proxima_versao_brief(conexao, place_id: str, landing_page_id: Optional[int] = None) -> int:
    if landing_page_id:
        row = conexao.execute(
            "SELECT MAX(versao) as max_v FROM lp_briefs WHERE landing_page_id = ?", (landing_page_id,)
        ).fetchone()
        if row and row["max_v"] is not None:
            return int(row["max_v"]) + 1
    row = conexao.execute(
        "SELECT MAX(versao) as max_v FROM lp_briefs WHERE place_id = ?", (place_id,)
    ).fetchone()
    if row and row["max_v"] is not None:
        return int(row["max_v"]) + 1
    return 1


def salvar_historico_brief(
    conexao,
    place_id: str,
    spec_json_str: str,
    provedor: str = "ai",
    landing_page_id: Optional[int] = None,
    change_type: str = "initial_generation",
    sections_json: Optional[str] = None,
    restored_from_version: Optional[int] = None,
    description: Optional[str] = None,
) -> int:
    versao = obter_proxima_versao_brief(conexao, place_id, landing_page_id=landing_page_id)
    agora = datetime.now().isoformat(timespec="seconds")
    cursor = conexao.execute(
        """
        INSERT INTO lp_briefs (
            place_id, landing_page_id, spec_json, provedor, versao, gerado_em,
            change_type, sections_json, restored_from_version, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            place_id,
            landing_page_id,
            spec_json_str,
            provedor,
            versao,
            agora,
            change_type,
            sections_json,
            restored_from_version,
            description,
        ),
    )
    conexao.commit()
    return cursor.lastrowid


def obter_historico_lp(conexao, lp_id: int) -> list:
    """Lista as versões do histórico de uma Landing Page sem retornar o JSON completo de cada spec."""
    lp = conexao.execute("SELECT place_id FROM landing_pages WHERE id = ?", (lp_id,)).fetchone()
    if not lp:
        return []
    place_id = lp["place_id"]

    linhas = conexao.execute(
        """
        SELECT id, versao, change_type, sections_json, provedor, description, restored_from_version, gerado_em
        FROM lp_briefs
        WHERE landing_page_id = ? OR (landing_page_id IS NULL AND place_id = ?)
        ORDER BY versao DESC
        """,
        (lp_id, place_id),
    ).fetchall()

    resultado = []
    for row in linhas:
        d = dict(row)
        sections = []
        if d.get("sections_json"):
            try:
                sections = json.loads(d["sections_json"])
            except Exception:
                sections = []
        resultado.append(
            {
                "id": d["id"],
                "version": d["versao"],
                "change_type": d.get("change_type") or "initial_generation",
                "sections": sections,
                "provider": d.get("provedor") or "ai",
                "description": d.get("description") or "",
                "restored_from_version": d.get("restored_from_version"),
                "created_at": d["gerado_em"],
            }
        )
    return resultado


def obter_versao_lp(conexao, lp_id: int, versao: int) -> Optional[Dict[str, Any]]:
    """Obtém os detalhes de uma versão específica, incluindo o spec JSON completo."""
    lp = conexao.execute("SELECT place_id FROM landing_pages WHERE id = ?", (lp_id,)).fetchone()
    if not lp:
        return None
    place_id = lp["place_id"]

    linha = conexao.execute(
        """
        SELECT * FROM lp_briefs
        WHERE (landing_page_id = ? OR (landing_page_id IS NULL AND place_id = ?))
          AND versao = ?
        """,
        (lp_id, place_id, versao),
    ).fetchone()

    if not linha:
        return None

    d = dict(linha)
    try:
        d["spec"] = json.loads(d["spec_json"])
    except Exception:
        d["spec"] = {}
    return d



def criar_landing_page(
    conexao,
    place_id: str,
    slug: str,
    template_key: str,
    spec_json_str: str,
    status: str = "draft",
    schema_version: int = 1,
) -> int:
    template_key = normalizar_template_key(template_key)
    agora = datetime.now().isoformat(timespec="seconds")
    cursor = conexao.execute(
        """
        INSERT INTO landing_pages (
            place_id, slug, template_key, current_spec_json, status, schema_version, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (place_id, slug, template_key, spec_json_str, status, schema_version, agora, agora),
    )
    conexao.commit()
    return cursor.lastrowid


def atualizar_landing_page(
    conexao,
    lp_id: int,
    spec_json_str: str,
    status: Optional[str] = None,
    template_key: Optional[str] = None,
) -> None:
    if template_key is not None:
        template_key = normalizar_template_key(template_key)
    agora = datetime.now().isoformat(timespec="seconds")
    if status and template_key:
        conexao.execute(
            """
            UPDATE landing_pages
            SET current_spec_json = ?, status = ?, template_key = ?, updated_at = ?
            WHERE id = ?
            """,
            (spec_json_str, status, template_key, agora, lp_id),
        )
    elif status:
        conexao.execute(
            """
            UPDATE landing_pages
            SET current_spec_json = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (spec_json_str, status, agora, lp_id),
        )
    elif template_key:
        conexao.execute(
            """
            UPDATE landing_pages
            SET current_spec_json = ?, template_key = ?, updated_at = ?
            WHERE id = ?
            """,
            (spec_json_str, template_key, agora, lp_id),
        )
    else:
        conexao.execute(
            """
            UPDATE landing_pages
            SET current_spec_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (spec_json_str, agora, lp_id),
        )
    conexao.commit()


def arquivar_landing_page(conexao, lp_id: int) -> None:
    agora = datetime.now().isoformat(timespec="seconds")
    conexao.execute(
        "UPDATE landing_pages SET status = 'archived', updated_at = ? WHERE id = ?",
        (agora, lp_id),
    )
    conexao.commit()


def atualizar_publicacao_lp(
    conexao,
    lp_id: int,
    status: str,
    public_id: Optional[str] = None,
    public_url: Optional[str] = None,
    publish_provider: Optional[str] = None,
    publication_revision: Optional[int] = None,
    published_at: Optional[str] = None,
    unpublished_at: Optional[str] = None,
) -> None:
    agora = datetime.now().isoformat(timespec="seconds")
    conexao.execute(
        """
        UPDATE landing_pages
        SET status = ?,
            public_id = ?,
            public_url = ?,
            publish_provider = ?,
            publication_revision = COALESCE(?, publication_revision, 0),
            last_published_at = CASE WHEN ? = 'published' THEN ? ELSE last_published_at END,
            published_at = COALESCE(published_at, ?),
            unpublished_at = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            status,
            public_id,
            public_url,
            publish_provider,
            publication_revision,
            status,
            agora,
            published_at if status == "published" else None,
            unpublished_at,
            agora,
            lp_id,
        ),
    )
    conexao.commit()


def registrar_evento_lp(
    conexao,
    landing_page_id: int,
    event_type: str,
    session_id: Optional[str] = None,
    metadata_json: Optional[str] = None,
) -> int:
    agora = datetime.now().isoformat(timespec="seconds")
    cursor = conexao.execute(
        """
        INSERT INTO landing_page_events (landing_page_id, event_type, session_id, metadata_json, occurred_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (landing_page_id, event_type, session_id, metadata_json, agora),
    )
    conexao.commit()
    return cursor.lastrowid


def obter_metricas_analytics_lp(conexao, landing_page_id: int) -> Dict[str, Any]:
    linhas = conexao.execute(
        """
        SELECT event_type, session_id, occurred_at
        FROM landing_page_events
        WHERE landing_page_id = ?
        ORDER BY occurred_at DESC
        """,
        (landing_page_id,),
    ).fetchall()

    page_views = 0
    sessions_set = set()
    whatsapp_clicks = 0
    instagram_clicks = 0
    simulator_starts = 0
    simulator_completions = 0
    service_opens = 0
    last_view_at = None

    for row in linhas:
        evt = row["event_type"]
        sess = row["session_id"]
        occurred = row["occurred_at"]

        if evt == "page_view":
            page_views += 1
            if sess:
                sessions_set.add(sess)
            if not last_view_at:
                last_view_at = occurred
        elif evt == "whatsapp_click":
            whatsapp_clicks += 1
        elif evt == "instagram_click":
            instagram_clicks += 1
        elif evt == "simulator_start":
            simulator_starts += 1
        elif evt == "simulator_complete":
            simulator_completions += 1
        elif evt == "service_open":
            service_opens += 1

        if not last_view_at and occurred:
            last_view_at = occurred

    estimated_sessions = len(sessions_set) if sessions_set else (1 if page_views > 0 else 0)

    return {
        "page_views": page_views,
        "estimated_sessions": estimated_sessions,
        "whatsapp_clicks": whatsapp_clicks,
        "instagram_clicks": instagram_clicks,
        "simulator_starts": simulator_starts,
        "simulator_completions": simulator_completions,
        "service_opens": service_opens,
        "last_view_at": last_view_at,
    }
