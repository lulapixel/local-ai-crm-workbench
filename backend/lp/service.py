"""Regras de negócio do domínio de Landing Pages.

Gerencia a criação idempotente, regeneração assistida por IA, atualização e
formatação padronizada das respostas da API.
"""

import json
import re
import unicodedata
from typing import Any, Dict, List, Optional

from .copywriter import gerar_lp_content, gerar_secoes_lp_content
from .repository import (
    arquivar_landing_page as repo_arquivar,
    atualizar_landing_page as repo_atualizar,
    atualizar_publicacao_lp as repo_atualizar_publicacao,
    criar_landing_page as repo_criar,
    obter_historico_lp as repo_obter_historico,
    obter_metricas_analytics_lp as repo_obter_analytics,
    obter_por_id as repo_obter_por_id,
    obter_por_place_id as repo_obter_por_place_id,
    obter_por_slug as repo_obter_por_slug,
    obter_versao_lp as repo_obter_versao,
    registrar_evento_lp as repo_registrar_evento,
    salvar_historico_brief as repo_salvar_historico,
    slug_existe as repo_slug_existe,
)
from .publishing import get_publisher, sanitizar_payload_publico
from .template_catalog import normalizar_template_key, selecionar_template
from .validators import validar_e_sanitizar_spec



def normalizar_texto_slug(texto: str) -> str:
    """Normaliza texto removendo acentos, caracteres especiais e espaços."""
    if not texto:
        return ""
    # NFKD decomposição de caracteres acentuados
    nfkd = unicodedata.normalize("NFKD", texto)
    sem_acentos = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Limpa caracteres não-alfanuméricos
    limpo = re.sub(r"[^a-zA-Z0-9\s-]", "", sem_acentos).strip().lower()
    # Substitui espaços e múltiplos hífens por um único hífen
    slug = re.sub(r"[\s-]+", "-", limpo)
    return slug


def gerar_slug_unico(conexao, nome_lead: str, cidade_lead: str, place_id: str, ignore_id: Optional[int] = None) -> str:
    """Gera um slug amigável e único no formato: nome-normalizado-cidade-sufixo."""
    nome_norm = normalizar_texto_slug(nome_lead) or "lead"
    cidade_norm = normalizar_texto_slug(cidade_lead)

    # Sufixo determinístico curto a partir do place_id
    sufixo_base = re.sub(r"[^a-z0-9]", "", place_id.lower())[-4:] if place_id else "a7f3"
    if len(sufixo_base) < 4:
        sufixo_base = (sufixo_base + "a7f3")[:4]

    partes = [nome_norm]
    if cidade_norm:
        partes.append(cidade_norm)
    partes.append(sufixo_base)

    base_slug = "-".join(partes)
    candidato = base_slug
    contador = 1

    while repo_slug_existe(conexao, candidato, ignore_id=ignore_id):
        candidato = f"{base_slug}-{contador}"
        contador += 1

    return candidato


def formatar_resposta_lp(lp_dict: Dict[str, Any], avisos: Optional[List[str]] = None) -> Dict[str, Any]:
    """Formata o objeto de retorno da API conforme a especificação do contrato."""
    publisher = get_publisher()

    slug = lp_dict.get("slug", "")
    status = lp_dict.get("status", "draft")

    public_url = lp_dict.get("public_url")
    if not public_url and status == "published":
        public_url = f"/demos/{slug}"

    preview_url = f"/demos/{slug}?preview=1"

    return {
        "id": lp_dict.get("id"),
        "place_id": lp_dict.get("place_id"),
        "slug": slug,
        "template_key": lp_dict.get("template_key"),
        "status": status,
        "schema_version": lp_dict.get("schema_version", 1),
        "spec": lp_dict.get("spec", {}),
        "preview_url": preview_url,
        "public_url": public_url,
        "public_id": lp_dict.get("public_id"),
        "publish_provider": lp_dict.get("publish_provider"),
        "publication_revision": lp_dict.get("publication_revision", 0),
        "last_published_at": lp_dict.get("last_published_at"),
        "unpublished_at": lp_dict.get("unpublished_at"),
        "publication_configured": publisher.is_configured(),
        "created_at": lp_dict.get("created_at"),
        "updated_at": lp_dict.get("updated_at"),
        "published_at": lp_dict.get("published_at"),
        "warnings": avisos or [],
    }


def obter_lead_por_place_id(conexao, place_id: str) -> Dict[str, Any]:
    linha = conexao.execute("SELECT * FROM leads WHERE place_id = ?", (place_id,)).fetchone()
    if not linha:
        raise ValueError(f"Lead com place_id '{place_id}' não encontrado.")
    return dict(linha)


def obter_ou_criar_landing_page(
    conexao, place_id: str, template_key: Optional[str] = None, force_regenerate: bool = False
) -> Dict[str, Any]:
    lead = obter_lead_por_place_id(conexao, place_id)
    lp_existente = repo_obter_por_place_id(conexao, place_id)

    if lp_existente and not force_regenerate:
        return formatar_resposta_lp(lp_existente)

    selected_tmpl = template_key or (lp_existente.get("template_key") if lp_existente else None)
    selected_tmpl = normalizar_template_key(selected_tmpl or selecionar_template(lead))

    if lp_existente:
        slug = lp_existente["slug"]
    else:
        slug = gerar_slug_unico(conexao, lead.get("nome", ""), lead.get("cidade", ""), place_id)

    spec_limpo, provedor, avisos = gerar_lp_content(lead, selected_tmpl, slug)
    spec_json_str = json.dumps(spec_limpo, ensure_ascii=False)

    if lp_existente:
        lp_id = lp_existente["id"]
        repo_salvar_historico(
            conexao,
            place_id,
            spec_json_str,
            provedor=provedor,
            landing_page_id=lp_id,
            change_type="initial_generation",
            description="Geração inicial da Landing Page",
        )
        repo_atualizar(conexao, lp_id, spec_json_str, template_key=selected_tmpl)
        lp_atualizada = repo_obter_por_id(conexao, lp_id)
        return formatar_resposta_lp(lp_atualizada, avisos=avisos)
    else:
        lp_id = repo_criar(conexao, place_id, slug, selected_tmpl, spec_json_str)
        repo_salvar_historico(
            conexao,
            place_id,
            spec_json_str,
            provedor=provedor,
            landing_page_id=lp_id,
            change_type="initial_generation",
            description="Geração inicial da Landing Page",
        )
        nova_lp = repo_obter_por_id(conexao, lp_id)
        return formatar_resposta_lp(nova_lp, avisos=avisos)


def obter_landing_page_por_place_id(conexao, place_id: str) -> Dict[str, Any]:
    lp = repo_obter_por_place_id(conexao, place_id)
    if not lp:
        raise ValueError(f"Nenhuma Landing Page encontrada para o lead '{place_id}'.")
    return formatar_resposta_lp(lp)


def obter_landing_page_por_slug(conexao, slug: str) -> Dict[str, Any]:
    lp = repo_obter_por_slug(conexao, slug)
    if not lp:
        raise ValueError(f"Landing Page com slug '{slug}' não encontrada.")
    return formatar_resposta_lp(lp)


def obter_landing_page_por_id(conexao, lp_id: int) -> Dict[str, Any]:
    lp = repo_obter_por_id(conexao, lp_id)
    if not lp:
        raise ValueError(f"Landing Page id={lp_id} não encontrada.")
    return formatar_resposta_lp(lp)


def atualizar_landing_page_spec(
    conexao, lp_id: int, novo_spec: Dict[str, Any], novo_status: Optional[str] = None
) -> Dict[str, Any]:
    lp_existente = repo_obter_por_id(conexao, lp_id)
    if not lp_existente:
        raise ValueError(f"Landing Page id={lp_id} não encontrada.")

    spec_validado, avisos = validar_e_sanitizar_spec(novo_spec, lp_existente["slug"])
    spec_json_str = json.dumps(spec_validado, ensure_ascii=False)

    current_json = lp_existente.get("current_spec_json", "")

    # Só cria registro no histórico se houver alteração real no spec JSON
    if current_json != spec_json_str:
        repo_salvar_historico(
            conexao,
            place_id=lp_existente["place_id"],
            spec_json_str=spec_json_str,
            provedor="user",
            landing_page_id=lp_id,
            change_type="manual_edit",
            description="Alterações salvas pelo editor visual",
        )

    repo_atualizar(conexao, lp_id, spec_json_str, status=novo_status)
    lp_atualizada = repo_obter_por_id(conexao, lp_id)
    return formatar_resposta_lp(lp_atualizada, avisos=avisos)


SECOES_PERMITIDAS = {"hero", "services", "trust", "testimonials", "faqs", "budget", "finalCta", "seo", "contact", "brand", "palette"}
TONS_PERMITIDOS = {"direct", "premium", "welcoming", "short", "commercial"}


def regenerar_conteudo_lp(
    conexao,
    lp_id: int,
    secoes: Optional[List[str]] = None,
    tone: str = "premium",
    instruction: str = "",
) -> Dict[str, Any]:
    lp_existente = repo_obter_por_id(conexao, lp_id)
    if not lp_existente:
        raise ValueError(f"Landing Page id={lp_id} não encontrada.")

    if tone and tone not in TONS_PERMITIDOS:
        raise ValueError(f"Tom de escrita '{tone}' é inválido. Tons permitidos: {', '.join(sorted(TONS_PERMITIDOS))}.")

    lead = obter_lead_por_place_id(conexao, lp_existente["place_id"])
    spec_anterior = lp_existente.get("spec", {})

    if secoes is not None:
        if not isinstance(secoes, list) or len(secoes) == 0:
            raise ValueError("A lista de seções para regeneração parcial deve conter ao menos uma seção.")

        for sec in secoes:
            if sec not in SECOES_PERMITIDAS:
                raise ValueError(f"Seção '{sec}' é inválida para regeneração.")

        spec_final, provedor, avisos = gerar_secoes_lp_content(
            lead,
            lp_existente["template_key"],
            lp_existente["slug"],
            spec_anterior,
            secoes,
            tone=tone,
            instruction=instruction,
        )

        # Garantir isolamento absoluto: seções não solicitadas devem ser exatamente iguais ao spec_anterior
        for key in spec_anterior:
            if key not in secoes:
                spec_final[key] = spec_anterior[key]

        desc = f"Reescrita IA ({', '.join(secoes)}) em tom {tone}"
        sections_json_str = json.dumps(secoes)
    else:
        spec_final, provedor, avisos = gerar_lp_content(
            lead, lp_existente["template_key"], lp_existente["slug"]
        )
        desc = "Regeneração completa via IA"
        sections_json_str = None

    spec_validado, avisos_val = validar_e_sanitizar_spec(spec_final, lp_existente["slug"])
    spec_json_str = json.dumps(spec_validado, ensure_ascii=False)

    repo_salvar_historico(
        conexao,
        place_id=lp_existente["place_id"],
        spec_json_str=spec_json_str,
        provedor=provedor,
        landing_page_id=lp_id,
        change_type="ai_regeneration",
        sections_json=sections_json_str,
        description=desc,
    )
    repo_atualizar(conexao, lp_id, spec_json_str)

    lp_atualizada = repo_obter_por_id(conexao, lp_id)
    return formatar_resposta_lp(lp_atualizada, avisos=avisos + avisos_val)


def listar_historico_landing_page(conexao, lp_id: int) -> Dict[str, Any]:
    lp = repo_obter_por_id(conexao, lp_id)
    if not lp:
        raise ValueError(f"Landing Page id={lp_id} não encontrada.")
    versoes = repo_obter_historico(conexao, lp_id)
    return {"versions": versoes}


def obter_versao_historico_landing_page(conexao, lp_id: int, versao: int) -> Dict[str, Any]:
    lp = repo_obter_por_id(conexao, lp_id)
    if not lp:
        raise ValueError(f"Landing Page id={lp_id} não encontrada.")

    versao_item = repo_obter_versao(conexao, lp_id, versao)
    if not versao_item:
        raise ValueError(f"Versão {versao} não encontrada para a Landing Page id={lp_id}.")

    sections = []
    if versao_item.get("sections_json"):
        try:
            sections = json.loads(versao_item["sections_json"])
        except Exception:
            sections = []

    return {
        "id": versao_item["id"],
        "landing_page_id": lp_id,
        "version": versao_item["versao"],
        "change_type": versao_item.get("change_type") or "initial_generation",
        "sections": sections,
        "provider": versao_item.get("provedor") or "ai",
        "description": versao_item.get("description") or "",
        "restored_from_version": versao_item.get("restored_from_version"),
        "created_at": versao_item["gerado_em"],
        "spec": versao_item.get("spec", {}),
    }


def restaurar_versao_landing_page(conexao, lp_id: int, versao: int) -> Dict[str, Any]:
    lp_existente = repo_obter_por_id(conexao, lp_id)
    if not lp_existente:
        raise ValueError(f"Landing Page id={lp_id} não encontrada.")

    versao_item = repo_obter_versao(conexao, lp_id, versao)
    if not versao_item:
        raise ValueError(f"Versão {versao} não encontrada para restauração.")

    spec_restaurado = versao_item.get("spec", {})
    spec_validado, avisos = validar_e_sanitizar_spec(spec_restaurado, lp_existente["slug"])
    spec_json_str = json.dumps(spec_validado, ensure_ascii=False)

    desc = f"Restauração da versão {versao}"
    repo_salvar_historico(
        conexao,
        place_id=lp_existente["place_id"],
        spec_json_str=spec_json_str,
        provedor="user",
        landing_page_id=lp_id,
        change_type="version_restore",
        restored_from_version=versao,
        description=desc,
    )

    repo_atualizar(conexao, lp_id, spec_json_str)
    lp_atualizada = repo_obter_por_id(conexao, lp_id)
    return formatar_resposta_lp(lp_atualizada, avisos=avisos)



def arquivar_lp(conexao, lp_id: int) -> Dict[str, Any]:
    lp_existente = repo_obter_por_id(conexao, lp_id)
    if not lp_existente:
        raise ValueError(f"Landing Page id={lp_id} não encontrada.")

    repo_arquivar(conexao, lp_id)
    lp_atualizada = repo_obter_por_id(conexao, lp_id)
    return formatar_resposta_lp(lp_atualizada)


def validar_lp_para_publicacao(lp_dict: Dict[str, Any], lead: Dict[str, Any]) -> List[str]:
    """Valida se a Landing Page satisfaz todas as pré-condições de publicação."""
    if lp_dict.get("status") == "archived":
        raise ValueError("Landing Page arquivada não pode ser publicada.")

    spec = lp_dict.get("spec", {})
    if not isinstance(spec, dict):
        raise ValueError("Estrutura da Landing Page inválida.")

    contact = spec.get("contact", {})
    phone = contact.get("whatsapp") or contact.get("phone") or lead.get("telefone") or ""
    if not str(phone).strip():
        raise ValueError("Telefone de contato/WhatsApp é obrigatório para publicação.")

    # Verificar depoimentos fictícios apresentados como reais
    testimonials = spec.get("testimonials", [])
    for t in testimonials:
        if isinstance(t, dict):
            if t.get("fake") is True or t.get("ficticio") is True:
                raise ValueError("Depoimentos fictícios não podem ser apresentados como reais na publicação.")

    return []


def publicar_landing_page(conexao, lp_id: int) -> Dict[str, Any]:
    """Publica a Landing Page usando o provedor de publicação configurado."""
    lp_existente = repo_obter_por_id(conexao, lp_id)
    if not lp_existente:
        raise ValueError(f"Landing Page id={lp_id} não encontrada.")

    lead = obter_lead_por_place_id(conexao, lp_existente["place_id"])
    validar_lp_para_publicacao(lp_existente, lead)

    publisher = get_publisher()
    payload_publico = sanitizar_payload_publico(lp_existente, lead)
    res_pub = publisher.publish(lp_existente, payload_publico)

    nova_revisao = int(lp_existente.get("publication_revision") or 0) + 1
    repo_atualizar_publicacao(
        conexao,
        lp_id=lp_id,
        status="published",
        public_id=res_pub.get("public_id"),
        public_url=res_pub.get("public_url"),
        publish_provider=res_pub.get("publish_provider"),
        publication_revision=nova_revisao,
        published_at=lp_existente.get("published_at"),
        unpublished_at=None,
    )

    lp_atualizada = repo_obter_por_id(conexao, lp_id)
    return formatar_resposta_lp(lp_atualizada)


def despublicar_landing_page(conexao, lp_id: int) -> Dict[str, Any]:
    """Despublica a Landing Page retornando para status draft."""
    lp_existente = repo_obter_por_id(conexao, lp_id)
    if not lp_existente:
        raise ValueError(f"Landing Page id={lp_id} não encontrada.")

    publisher = get_publisher()
    res_pub = publisher.unpublish(lp_existente)

    from datetime import datetime
    agora = datetime.now().isoformat(timespec="seconds")

    repo_atualizar_publicacao(
        conexao,
        lp_id=lp_id,
        status="draft",
        public_id=None,
        public_url=None,
        publish_provider=res_pub.get("publish_provider"),
        publication_revision=lp_existente.get("publication_revision"),
        published_at=lp_existente.get("published_at"),
        unpublished_at=agora,
    )

    lp_atualizada = repo_obter_por_id(conexao, lp_id)
    return formatar_resposta_lp(lp_atualizada)


def republicar_landing_page(conexao, lp_id: int) -> Dict[str, Any]:
    """Republica a Landing Page atualizando seu conteúdo público."""
    return publicar_landing_page(conexao, lp_id)


def obter_status_publicacao(conexao, lp_id: int) -> Dict[str, Any]:
    """Retorna os detalhes de status de publicação da Landing Page."""
    lp = repo_obter_por_id(conexao, lp_id)
    if not lp:
        raise ValueError(f"Landing Page id={lp_id} não encontrada.")

    publisher = get_publisher()

    return {
        "id": lp["id"],
        "slug": lp["slug"],
        "status": lp["status"],
        "published": lp["status"] == "published",
        "public_id": lp.get("public_id"),
        "public_url": lp.get("public_url"),
        "publish_provider": lp.get("publish_provider"),
        "publication_revision": lp.get("publication_revision", 0),
        "last_published_at": lp.get("last_published_at"),
        "unpublished_at": lp.get("unpublished_at"),
        "publication_configured": publisher.is_configured(),
    }


def obter_landing_page_publica(conexao, slug: str) -> Dict[str, Any]:
    """Retorna apenas o payload público e sanitizado de uma Landing Page publicada."""
    lp = repo_obter_por_slug(conexao, slug)
    if not lp:
        raise ValueError(f"Landing Page com slug '{slug}' não encontrada.")

    if lp.get("status") != "published":
        raise ValueError(f"A Landing Page '{slug}' não está publicada.")

    lead = obter_lead_por_place_id(conexao, lp["place_id"])
    return sanitizar_payload_publico(lp, lead)


EVENTOS_PERMITIDOS = {
    "page_view",
    "service_open",
    "simulator_start",
    "simulator_complete",
    "whatsapp_click",
    "instagram_click",
}


def registrar_evento_publico_lp(
    conexao,
    slug: str,
    event_type: str,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Registra evento de interações/conversões da Landing Page pública."""
    if not event_type or event_type not in EVENTOS_PERMITIDOS:
        raise ValueError(
            f"Tipo de evento '{event_type}' é inválido. Eventos permitidos: {', '.join(sorted(EVENTOS_PERMITIDOS))}."
        )

    lp = repo_obter_por_slug(conexao, slug)
    if not lp:
        raise ValueError(f"Landing Page com slug '{slug}' não encontrada.")

    if lp.get("status") != "published":
        raise ValueError(f"Eventos não são registrados para a Landing Page '{slug}' pois não está publicada.")

    sess_id_limpo = str(session_id).strip()[:100] if session_id else None

    metadata_limpa = {}
    if isinstance(metadata, dict):
        count = 0
        for k, v in metadata.items():
            if count >= 5:
                break
            chave_norm = re.sub(r"[^a-zA-Z0-9_-]", "", str(k))[:50]
            val_norm = str(v)[:200]
            if chave_norm:
                metadata_limpa[chave_norm] = val_norm
            count += 1

    metadata_json_str = json.dumps(metadata_limpa, ensure_ascii=False) if metadata_limpa else None

    repo_registrar_evento(
        conexao,
        landing_page_id=lp["id"],
        event_type=event_type,
        session_id=sess_id_limpo,
        metadata_json=metadata_json_str,
    )

    return {"ok": True}


def obter_analytics_landing_page(conexao, lp_id: int) -> Dict[str, Any]:
    """Retorna estatísticas agregadas de visualizações e conversões da Landing Page."""
    lp = repo_obter_por_id(conexao, lp_id)
    if not lp:
        raise ValueError(f"Landing Page id={lp_id} não encontrada.")

    return repo_obter_analytics(conexao, lp_id)
