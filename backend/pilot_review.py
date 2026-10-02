"""Read-only review material in the configured data directory, never CRM imports."""
import json
from urllib.parse import urlsplit

import paths

MAX_BYTES = 262144


def _text(value, limit=4000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("Invalid review text")
    return value


def _source(value):
    value = _text(value, 2048)
    url = urlsplit(value)
    if url.scheme != "https" or not url.hostname or url.username or url.password or any(c.isspace() for c in value):
        raise ValueError("Invalid source URL")
    return value


def listar():
    data_root = paths.DIR_DADOS.resolve()
    root = paths.caminho_dados("pilots")
    pilots, rejected = [], 0
    if not root.is_dir() or not root.resolve().is_relative_to(data_root):
        return {"pilots": [], "unavailable": 0}
    for filename in sorted(root.glob("*/review.json"))[:20]:
        try:
            if not filename.resolve().is_relative_to(data_root):
                raise ValueError("Review outside data directory")
            with filename.open("rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("Oversized review")
            data = json.loads(raw)
            if not isinstance(data, dict) or not isinstance(data.get("prospects"), list) or not 1 <= len(data["prospects"]) <= 30:
                raise ValueError("Invalid review")
            prospects, ids = [], set()
            for row in data["prospects"]:
                if not isinstance(row, dict):
                    raise ValueError("Invalid prospect")
                clean = {key: _text(row.get(key)) for key in
                         ("id", "name", "segment", "phone", "evidence", "hypothesis", "question", "draft", "contact_check")}
                if clean["id"] in ids:
                    raise ValueError("Duplicate prospect")
                ids.add(clean["id"])
                clean["source_url"] = _source(row.get("source_url"))
                prospects.append(clean)
            pilots.append({"id": _text(data.get("id"), 100), "title": _text(data.get("title"), 180),
                           "checked_on": _text(data.get("checked_on"), 40), "prospects": prospects})
        except (OSError, ValueError, TypeError, KeyError, UnicodeError):
            rejected += 1
    return {"pilots": pilots, "unavailable": rejected}
