"""Sanitização de respostas e allowlists de campos seguros para o MCP."""

from typing import Any, Dict, List, Optional, Set

LEAD_MAPS_ALLOWLIST: Set[str] = {
    "place_id",
    "nome",
    "categoria",
    "endereco",
    "telefone",
    "whatsapp_link",
    "site",
    "site_url",
    "nicho",
    "cidade",
    "instagram_url",
    "query_origem",
    "nota",
    "num_avaliacoes",
    "status",
    "site_status",
    "site_problemas",
    "site_checklist",
    "score",
    "tags",
    "observacoes",
    "proximo_followup",
    "follow_ups_enviados",
    "ultimo_followup_em",
    "visto_em",
    "atualizado_em",
    "estrategia_cached",
    "mensagem_cached",
    "provedor_mensagem",
}

LEAD_INSTAGRAM_ALLOWLIST: Set[str] = {
    "id",
    "post_id",
    "username",
    "nome_completo",
    "perfil_url",
    "biografia",
    "seguidores",
    "seguindo",
    "num_posts",
    "email",
    "telefone",
    "site_bio",
    "e_comercial",
    "categoria",
    "nicho_detectado",
    "justificativa_nicho",
    "status",
    "score",
    "tags",
    "observacoes",
    "proximo_followup",
    "follow_ups_enviados",
    "ultimo_followup_em",
    "criado_em",
    "atualizado_em",
    "sugestao_dm",
}

SENSITIVE_KEY_PATTERNS: Set[str] = {
    "gemini",
    "groq",
    "nvidia",
    "places",
    "pagespeed",
    "api_key",
    "password",
    "senha",
    "cookie",
    "proxy",
    "session",
    "keyring",
}


def sanitize_maps_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Filtra um lead do Maps apenas com os campos permitidos na allowlist."""
    if not isinstance(lead, dict):
        return {}
    res = {k: v for k, v in lead.items() if k in LEAD_MAPS_ALLOWLIST}
    return res


def sanitize_instagram_lead(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Filtra um lead do Instagram apenas com os campos permitidos na allowlist."""
    if not isinstance(lead, dict):
        return {}
    res = {k: v for k, v in lead.items() if k in LEAD_INSTAGRAM_ALLOWLIST}
    return res


def contains_sensitive_data(obj: Any) -> Optional[str]:
    """Verifica recursivamente se um objeto JSON contém chaves ou valores sensíveis."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            k_lower = str(k).lower()
            for pattern in SENSITIVE_KEY_PATTERNS:
                if pattern in k_lower:
                    return f"Chave sensível encontrada: {k}"
            res = contains_sensitive_data(v)
            if res:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = contains_sensitive_data(item)
            if res:
                return res
    return None
