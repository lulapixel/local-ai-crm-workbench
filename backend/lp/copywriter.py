"""Geração de conteúdo para Landing Pages via IA ou fallback determinístico.

Combina dados reais coletados do lead (nome, cidade, telefone, avaliações)
com IA (quando disponível) para gerar copy de alta conversão.
"""

import json
import logging
import re
from typing import Any, Dict, Tuple

from .template_catalog import TEMPLATES
from .validators import sanitizar_telefone_whatsapp, sanitizar_texto, validar_e_sanitizar_spec


logger = logging.getLogger(__name__)


def extrair_fatos_deterministicos(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Extrai informações conhecidas do lead para preenchimento direto no spec."""
    nome = (lead.get("nome") or "Empresa").strip()
    cidade = (lead.get("cidade") or "").strip()
    telefone = lead.get("telefone") or lead.get("whatsapp_link") or ""
    whatsapp = sanitizar_telefone_whatsapp(telefone)
    instagram = (lead.get("instagram_url") or "").strip()
    nota = lead.get("nota")
    num_avaliacoes = lead.get("num_avaliacoes")

    trust = []
    if nota is not None and str(nota).strip() != "":
        try:
            nota_num = float(nota)
            txt_avaliacoes = f"({num_avaliacoes} avaliações)" if num_avaliacoes else ""
            trust.append({"label": "Avaliação no Google", "value": f"{nota_num:.1f} ★ {txt_avaliacoes}".strip()})
        except (ValueError, TypeError):
            pass

    if cidade:
        trust.append({"label": "Localização", "value": f"Atendimento em {cidade}"})

    return {
        "nome": nome,
        "cidade": cidade,
        "whatsapp": whatsapp,
        "instagram": instagram,
        "nota": nota,
        "num_avaliacoes": num_avaliacoes,
        "trust": trust,
    }


def gerar_spec_fallback(lead: Dict[str, Any], template_key: str, slug: str) -> Dict[str, Any]:
    """Gera um spec completo usando o template padrão e os fatos determinísticos do lead."""
    tmpl = TEMPLATES.get(template_key) or TEMPLATES["geral-conversao"]
    is_general_template = tmpl["key"] == "geral-conversao"
    fatos = extrair_fatos_deterministicos(lead)

    nome_empresa = fatos["nome"]
    cidade = fatos["cidade"]
    cidade_str = f" em {cidade}" if cidade else ""

    hero = dict(tmpl["default_hero"])
    hero["title"] = f"{hero['title']}{cidade_str}"
    hero["imageAlt"] = f"Atendimento {nome_empresa}"

    seo = (
        {
            "title": f"{nome_empresa}{cidade_str} | Serviços e atendimento",
            "description": f"Conheça os serviços de {nome_empresa}{cidade_str}. Confirme detalhes pelo WhatsApp.",
        }
        if is_general_template
        else {
            "title": f"{nome_empresa}{cidade_str} | Agende seu Atendimento",
            "description": f"Conheça os tratamentos de {nome_empresa}{cidade_str}. Agendamento rápido via WhatsApp.",
        }
    )

    brand = {
        "name": nome_empresa,
        "eyebrow": f"Atendimento Exclusivo{cidade_str}",
        "logoUrl": "",
    }

    contact = {
        "whatsappNumber": fatos["whatsapp"],
        "whatsappMessage": (
            f"Olá! Vi a apresentação de {nome_empresa} e gostaria de confirmar detalhes dos serviços."
            if is_general_template
            else f"Olá! Vi a apresentação de {nome_empresa} e gostaria de agendar uma consulta."
        ),
        "city": cidade,
        "instagram": fatos["instagram"],
    }

    spec = {
        "schema_version": 1,
        "slug": slug,
        "brand": brand,
        "seo": seo,
        "palette": dict(tmpl["default_palette"]),
        "contact": contact,
        "hero": hero,
        "trust": fatos["trust"] if is_general_template else fatos["trust"] or [
            {"label": "Avaliação Google", "value": "4.9 ★ (Atendimento Excelente)"},
            {"label": "Atendimento", "value": "Personalizado e Exclusivo"},
        ],
        "services": [dict(s) for s in tmpl["default_services"]],
        "testimonials": [] if is_general_template else [
            {
                "name": "Cliente Atendido",
                "role": "Depoimento Demonstrativo",
                "quote": "Excelente experiência! Atendimento muito atencioso do início ao fim.",
                "rating": 5.0,
            }
        ],
        "faqs": [dict(f) for f in tmpl["default_faqs"]],
        "budget": (
            {
                "title": "Seleção de Serviços",
                "description": "Selecione os serviços para receber uma estimativa e confirmar detalhes.",
                "basePrice": 0.0,
                "consultationLabel": "Atendimento e detalhes",
            }
            if is_general_template
            else {
                "title": "Simulador de Atendimento",
                "description": "Selecione os procedimentos para simular uma estimativa de atendimento.",
                "basePrice": 0.0,
                "consultationLabel": "Avaliação presencial/online",
            }
        ),
        "finalCta": (
            {
                "title": f"Pronto para falar com {nome_empresa}?",
                "description": "Clique no botão abaixo para falar no WhatsApp e confirmar detalhes.",
                "buttonLabel": "Falar no WhatsApp Agora",
            }
            if is_general_template
            else {
                "title": f"Pronto para agendar seu horário com {nome_empresa}?",
                "description": "Clique no botão abaixo para falar direto no WhatsApp e agendar sua avaliação.",
                "buttonLabel": "Falar no WhatsApp Agora",
            }
        ),
    }

    return spec


def montar_system_prompt_lp() -> str:
    return """Você é um especialista em Copywriting de alta conversão e UX Design para Landing Pages locais.
Seu objetivo é gerar um spec JSON no formato exatamente conforme a estrutura especificada.

REGRAS DE CONTEÚDO E SEGURANÇA:
1. Use APENAS informações reais fornecidas sobre o lead (nome, cidade, avaliações do Google).
2. NUNCA invente depoimentos de pessoas reais com sobrenome e foto se não fornecidos, use textos com foco na experiência ou indicados como demonstrativos.
3. NUNCA invente número de anos de mercado, prêmios ou certificados inexistentes.
4. NUNCA invente preços exatos se não informados; use priceFrom=0 ou descrições amigáveis.
5. Devolva estritamente um código JSON válido, sem markdown ou explicações fora do JSON.
"""


def montar_user_prompt_lp(lead: Dict[str, Any], template_key: str, base_spec: Dict[str, Any]) -> str:
    fatos = extrair_fatos_deterministicos(lead)
    nicho = lead.get("nicho") or lead.get("categoria") or "Serviços"

    return f"""Gere a copy de alta conversão para a Landing Page do lead abaixo.

DADOS DO LEAD:
- Nome da Empresa: {fatos['nome']}
- Cidade: {fatos['cidade']}
- Nicho/Categoria: {nicho}
- Nota Google: {fatos['nota']}
- Número de Avaliações: {fatos['num_avaliacoes']}
- Instagram: {fatos['instagram']}

TEMPLATE BASE (ESTRUTURA JSON DESEJADA):
{json.dumps(base_spec, ensure_ascii=False, indent=2)}

Responda APENAS com o JSON modificado e aprimorado para este lead mantendo a mesma estrutura.
"""


def gerar_lp_content(lead: Dict[str, Any], template_key: str, slug: str) -> Tuple[Dict[str, Any], str, list]:
    """Gera o spec da Landing Page usando IA com fallback determinístico.

    Retorna uma tupla: (spec_validado, provedor_usado, lista_de_avisos)
    """
    base_spec = gerar_spec_fallback(lead, template_key, slug)

    # Tenta usar a IA via backend/ia.py
    try:
        from ia import gerar_com_fallback

        system_prompt = montar_system_prompt_lp()
        user_prompt = montar_user_prompt_lp(lead, template_key, base_spec)

        resposta_raw, provedor = gerar_com_fallback(system_prompt, user_prompt)
        if resposta_raw and provedor != "nenhum":
            # Extrai bloco JSON se vier encapsulado em ```json ... ```
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", resposta_raw, re.DOTALL)
            json_str = match.group(1) if match else resposta_raw.strip()

            try:
                raw_spec = json.loads(json_str)
                spec_validado, avisos = validar_e_sanitizar_spec(raw_spec, slug)
                logger.info("Landing page gerada via IA (provedor: %s) para lead place_id=%s", provedor, lead.get("place_id"))
                return spec_validado, provedor, avisos
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("Falha ao interpretar JSON retornado pela IA (%s). Usando fallback.", exc)
    except Exception as e:
        logger.warning("IA indisponível ou erro na geração (%s). Usando fallback determinístico.", e)

    # Fallback determinístico
    spec_validado, avisos = validar_e_sanitizar_spec(base_spec, slug)
    return spec_validado, "fallback_deterministico", avisos


TONES_MAP = {
    "direct": "direto e objetivo",
    "premium": "sofisticado, exclusivo e premium",
    "welcoming": "acolhedor, empático e humanizado",
    "short": "curto, dinâmico e direto ao ponto",
    "commercial": "comercial e altamente persuasivo para conversão",
}


def gerar_secoes_lp_content(
    lead: Dict[str, Any],
    template_key: str,
    slug: str,
    spec_atual: Dict[str, Any],
    secoes: list,
    tone: str = "premium",
    instruction: str = "",
) -> Tuple[Dict[str, Any], str, list]:
    """Regenera via IA apenas as seções solicitadas de uma Landing Page.

    Garante o isolamento absoluto de todas as outras seções do spec.
    """
    tom_desc = TONES_MAP.get(tone, TONES_MAP["premium"])
    instrucao_limpa = sanitizar_texto(instruction, 300)

    fatos = extrair_fatos_deterministicos(lead)
    sub_spec_desejado = {k: spec_atual.get(k) for k in secoes if k in spec_atual}

    system_prompt = f"""Você é um copywriter especialista. Seu objetivo é reescrever APENAS as seções especificadas de uma Landing Page em tom {tom_desc}.

REGRAS:
1. Responda APENAS com um objeto JSON contendo exclusivamente as chaves solicitadas: {', '.join(secoes)}.
2. Mantenha os nomes das propriedades JSON intactos.
3. Instrução adicional do usuário: "{instrucao_limpa or 'Nenhuma'}"
4. Não altere fatos reais da empresa ({fatos['nome']}).
5. Devolva estritamente um JSON válido, sem markdown ou textos fora do JSON.
"""

    user_prompt = f"""Empresa: {fatos['nome']} | Cidade: {fatos['cidade']} | Nicho: {lead.get('nicho') or 'Serviços'}

CONTEÚDO ATUAL DAS SEÇÕES SOLICITADAS:
{json.dumps(sub_spec_desejado, ensure_ascii=False, indent=2)}

Reescreva estas seções em tom {tom_desc}.
"""

    try:
        from ia import gerar_com_fallback

        resposta_raw, provedor = gerar_com_fallback(system_prompt, user_prompt)
        if resposta_raw and provedor != "nenhum":
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", resposta_raw, re.DOTALL)
            json_str = match.group(1) if match else resposta_raw.strip()

            try:
                raw_secoes = json.loads(json_str)
                if isinstance(raw_secoes, dict):
                    nuevo_spec = dict(spec_atual)
                    for sec in secoes:
                        if sec in raw_secoes:
                            nuevo_spec[sec] = raw_secoes[sec]

                    spec_validado, avisos = validar_e_sanitizar_spec(nuevo_spec, slug)
                    return spec_validado, provedor, avisos
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("Falha ao interpretar JSON da regeneração parcial de IA (%s).", exc)
    except Exception as e:
        logger.warning("IA indisponível para regeneração parcial (%s). Usando fallback.", e)

    # Fallback determinístico parcial
    spec_fallback = gerar_spec_fallback(lead, template_key, slug)
    nuevo_spec = dict(spec_atual)
    for sec in secoes:
        if sec in spec_fallback:
            nuevo_spec[sec] = spec_fallback[sec]

    spec_validado, avisos = validar_e_sanitizar_spec(nuevo_spec, slug)
    return spec_validado, "fallback_deterministico", avisos
