"""Acesso ao banco de dados para conversion_packs e conversion_pack_versions.
"""

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from lp.template_catalog import normalizar_template_key


def _normalizar_prototipo(prototype: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    resultado = dict(prototype or {})
    resultado["templateKey"] = normalizar_template_key(resultado.get("templateKey"))
    return resultado


def _linha_para_dict_pack(linha: Any) -> Dict[str, Any]:
    if not linha:
        return None
    if hasattr(linha, "keys") or isinstance(linha, sqlite3.Row):
        d = dict(linha)
    else:
        d = {
            "id": linha[0],
            "place_id": linha[1],
            "landing_page_id": linha[2],
            "strategy_json": linha[3],
            "messages_json": linha[4],
            "objections_json": linha[5],
            "prototype_json": linha[6],
            "status": linha[7],
            "provider": linha[8] if len(linha) > 8 else None,
            "version": linha[9] if len(linha) > 9 else 1,
            "created_at": linha[10] if len(linha) > 10 else "",
            "updated_at": linha[11] if len(linha) > 11 else "",
            "approved_at": linha[12] if len(linha) > 12 else None,
        }

    return {
        "id": d["id"],
        "placeId": d["place_id"],
        "landingPageId": d["landing_page_id"],
        "strategy": json.loads(d["strategy_json"]) if d.get("strategy_json") else {},
        "messages": json.loads(d["messages_json"]) if d.get("messages_json") else {},
        "objections": json.loads(d["objections_json"]) if d.get("objections_json") else [],
        "prototype": json.loads(d["prototype_json"]) if d.get("prototype_json") else {},
        "status": d["status"],
        "provider": d.get("provider"),
        "version": d["version"],
        "createdAt": d["created_at"],
        "updatedAt": d["updated_at"],
        "approvedAt": d.get("approved_at"),
    }


def obter_por_place_id(conexao: sqlite3.Connection, place_id: str) -> Optional[Dict[str, Any]]:
    linha = conexao.execute(
        "SELECT * FROM conversion_packs WHERE place_id = ?", (place_id,)
    ).fetchone()
    return _linha_para_dict_pack(linha) if linha else None


def obter_por_id(conexao: sqlite3.Connection, pack_id: int) -> Optional[Dict[str, Any]]:
    linha = conexao.execute(
        "SELECT * FROM conversion_packs WHERE id = ?", (pack_id,)
    ).fetchone()
    return _linha_para_dict_pack(linha) if linha else None


def registrar_versao(
    conexao: sqlite3.Connection,
    pack_id: int,
    version: int,
    snapshot: Dict[str, Any],
    change_type: str,
    provider: Optional[str] = None
) -> None:
    agora = datetime.now().isoformat(timespec="seconds")
    conexao.execute(
        """
        INSERT INTO conversion_pack_versions (
            conversion_pack_id, version, snapshot_json, change_type, provider, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            pack_id,
            version,
            json.dumps(snapshot, ensure_ascii=False),
            change_type,
            provider,
            agora
        ),
    )


def salvar_novo_pacote(
    conexao: sqlite3.Connection,
    place_id: str,
    landing_page_id: Optional[int],
    strategy: Dict[str, Any],
    messages: Dict[str, Any],
    objections: List[Dict[str, Any]],
    prototype: Dict[str, Any],
    provider: Optional[str] = "fallback",
    status: str = "draft"
) -> Dict[str, Any]:
    prototype = _normalizar_prototipo(prototype)
    agora = datetime.now().isoformat(timespec="seconds")
    version = 1

    cursor = conexao.execute(
        """
        INSERT INTO conversion_packs (
            place_id, landing_page_id, strategy_json, messages_json,
            objections_json, prototype_json, status, provider, version,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            place_id,
            landing_page_id,
            json.dumps(strategy, ensure_ascii=False),
            json.dumps(messages, ensure_ascii=False),
            json.dumps(objections, ensure_ascii=False),
            json.dumps(prototype, ensure_ascii=False),
            status,
            provider,
            version,
            agora,
            agora
        ),
    )
    pack_id = cursor.lastrowid

    snapshot = {
        "strategy": strategy,
        "messages": messages,
        "objections": objections,
        "prototype": prototype,
        "status": status,
        "landing_page_id": landing_page_id,
    }
    registrar_versao(conexao, pack_id, version, snapshot, "initial_generation", provider)
    conexao.commit()

    return obter_por_id(conexao, pack_id)


def atualizar_pacote(
    conexao: sqlite3.Connection,
    pack_id: int,
    strategy: Optional[Dict[str, Any]] = None,
    messages: Optional[Dict[str, Any]] = None,
    objections: Optional[List[Dict[str, Any]]] = None,
    prototype: Optional[Dict[str, Any]] = None,
    landing_page_id: Optional[int] = None,
    change_type: str = "manual_edit",
    provider: Optional[str] = None
) -> Dict[str, Any]:
    pacote_atual = obter_por_id(conexao, pack_id)
    if not pacote_atual:
        raise ValueError(f"Pacote com id {pack_id} não encontrado.")

    nova_strategy = strategy if strategy is not None else pacote_atual["strategy"]
    novas_messages = messages if messages is not None else pacote_atual["messages"]
    novas_objections = objections if objections is not None else pacote_atual["objections"]
    novo_prototype = _normalizar_prototipo(
        prototype if prototype is not None else pacote_atual["prototype"]
    )
    novo_lp_id = landing_page_id if landing_page_id is not None else pacote_atual["landingPageId"]

    nova_versao = pacote_atual["version"] + 1
    agora = datetime.now().isoformat(timespec="seconds")

    novo_status = "draft" if pacote_atual["status"] == "approved" else pacote_atual["status"]
    approved_at = None if pacote_atual["status"] == "approved" else pacote_atual.get("approvedAt")

    conexao.execute(
        """
        UPDATE conversion_packs
        SET landing_page_id = ?,
            strategy_json = ?,
            messages_json = ?,
            objections_json = ?,
            prototype_json = ?,
            status = ?,
            approved_at = ?,
            version = ?,
            provider = COALESCE(?, provider),
            updated_at = ?
        WHERE id = ?
        """,
        (
            novo_lp_id,
            json.dumps(nova_strategy, ensure_ascii=False),
            json.dumps(novas_messages, ensure_ascii=False),
            json.dumps(novas_objections, ensure_ascii=False),
            json.dumps(novo_prototype, ensure_ascii=False),
            novo_status,
            approved_at,
            nova_versao,
            provider,
            agora,
            pack_id
        ),
    )

    snapshot = {
        "strategy": nova_strategy,
        "messages": novas_messages,
        "objections": novas_objections,
        "prototype": novo_prototype,
        "landing_page_id": novo_lp_id,
        "status": novo_status,
    }
    registrar_versao(conexao, pack_id, nova_versao, snapshot, change_type, provider)
    conexao.commit()

    return obter_por_id(conexao, pack_id)


def alterar_status_pacote(
    conexao: sqlite3.Connection,
    pack_id: int,
    novo_status: str
) -> Dict[str, Any]:
    pacote_atual = obter_por_id(conexao, pack_id)
    if not pacote_atual:
        raise ValueError(f"Pacote com id {pack_id} não encontrado.")

    agora = datetime.now().isoformat(timespec="seconds")
    approved_at = agora if novo_status == "approved" else pacote_atual["approvedAt"]
    nova_versao = pacote_atual["version"] + 1

    conexao.execute(
        """
        UPDATE conversion_packs
        SET status = ?,
            version = ?,
            updated_at = ?,
            approved_at = ?
        WHERE id = ?
        """,
        (novo_status, nova_versao, agora, approved_at, pack_id),
    )

    change_type = "approval" if novo_status == "approved" else "status_change"
    snapshot = {
        "strategy": pacote_atual["strategy"],
        "messages": pacote_atual["messages"],
        "objections": pacote_atual["objections"],
        "prototype": pacote_atual["prototype"],
        "landing_page_id": pacote_atual["landingPageId"],
        "status": novo_status,
    }
    registrar_versao(conexao, pack_id, nova_versao, snapshot, change_type, pacote_atual.get("provider"))
    conexao.commit()

    return obter_por_id(conexao, pack_id)


def obter_versoes_pacote(conexao: sqlite3.Connection, pack_id: int) -> List[Dict[str, Any]]:
    linhas = conexao.execute(
        """
        SELECT * FROM conversion_pack_versions
        WHERE conversion_pack_id = ?
        ORDER BY version DESC
        """,
        (pack_id,),
    ).fetchall()

    resultado = []
    for l in linhas:
        if hasattr(l, "keys") or isinstance(l, sqlite3.Row):
            d = dict(l)
        else:
            d = {
                "id": l[0],
                "conversion_pack_id": l[1],
                "version": l[2],
                "snapshot_json": l[3],
                "change_type": l[4],
                "provider": l[5] if len(l) > 5 else None,
                "created_at": l[6] if len(l) > 6 else "",
            }
        resultado.append({
            "id": d["id"],
            "conversionPackId": d["conversion_pack_id"],
            "version": d["version"],
            "snapshot": json.loads(d["snapshot_json"]),
            "changeType": d["change_type"],
            "provider": d.get("provider"),
            "createdAt": d["created_at"],
        })
    return resultado
