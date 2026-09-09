"""Schemas de dados e auxiliares de formatação de resposta do MCP."""

from typing import Any, Dict, Optional


def build_success_response(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Monta uma resposta de sucesso no padrão {ok: true, data: ..., meta: ...}."""
    res: Dict[str, Any] = {
        "ok": True,
        "data": data,
    }
    if meta is not None:
        res["meta"] = meta
    return res
