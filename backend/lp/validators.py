"""Validação e sanitização do JSON de LandingPageData.

Garante que nenhum JSON vindo da IA ou do usuário seja persistido com dados corrompidos,
HTML malicioso, telefones inválidos ou estruturas ausentes.
"""

import re
from typing import Any, Dict, List, Tuple

RE_HEX_COLOR = re.compile(r"^#([A-Fa-f0-9]{3,4}|[A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$")
RE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RE_HTML_TAGS = re.compile(r"<[^>]*>")


RE_SCRIPT_STYLE = re.compile(r"<(script|style).*?>.*?</\1>", re.DOTALL | re.IGNORECASE)


def sanitizar_texto(valor: Any, max_len: int = 1000) -> str:
    """Remove scripts, estilos, HTML bruto e trunca no limite de caracteres."""
    if valor is None:
        return ""
    texto = str(valor)
    texto = RE_SCRIPT_STYLE.sub("", texto)
    texto = RE_HTML_TAGS.sub("", texto).strip()
    return texto[:max_len]


def sanitizar_telefone_whatsapp(num: Any) -> str:
    """Higieniza número de telefone para o formato E.164 (apenas dígitos, DDI 55)."""
    if not num:
        return ""
    digitos = re.sub(r"\D", "", str(num))
    if not digitos:
        return ""
    if not digitos.startswith("55") and len(digitos) in (10, 11):
        digitos = "55" + digitos
    return digitos


def validar_cor(cor: str, fallback: str) -> str:
    """Garante formato Hex CSS válido."""
    cor_clean = str(cor or "").strip()
    if RE_HEX_COLOR.match(cor_clean):
        return cor_clean
    return fallback


def validar_e_sanitizar_spec(spec: Dict[str, Any], slug_esperado: str = None) -> Tuple[Dict[str, Any], List[str]]:
    """Valida e sanitiza a estrutura LandingPageData.

    Retorna uma tupla (spec_limpo, lista_de_avisos).
    Lança ValueError se houver violação estrutural grave.
    """
    if not isinstance(spec, dict):
        raise ValueError("O spec da Landing Page deve ser um objeto JSON (dict).")

    avisos: List[str] = []
    limpo: Dict[str, Any] = {}

    # 1. Schema Version & Slug
    limpo["schema_version"] = 1
    raw_slug = sanitizar_texto(spec.get("slug") or slug_esperado or "demo-landing-page", 100).lower()
    if not RE_SLUG.match(raw_slug):
        import unicodedata
        raw_slug = "".join(c for c in unicodedata.normalize("NFKD", raw_slug) if not unicodedata.combining(c))
        raw_slug = re.sub(r"[^a-z0-9]+", "-", raw_slug).strip("-") or "demo-landing-page"
    limpo["slug"] = raw_slug

    # 2. Brand
    brand_in = spec.get("brand") if isinstance(spec.get("brand"), dict) else {}
    limpo["brand"] = {
        "name": sanitizar_texto(brand_in.get("name") or "Empresa Exemplo", 120),
        "eyebrow": sanitizar_texto(brand_in.get("eyebrow") or "Atendimento Especializado", 100),
        "logoUrl": sanitizar_texto(brand_in.get("logoUrl") or "", 500),
    }
    if not limpo["brand"]["name"]:
        limpo["brand"]["name"] = "Empresa Exemplo"

    # 3. SEO
    seo_in = spec.get("seo") if isinstance(spec.get("seo"), dict) else {}
    limpo["seo"] = {
        "title": sanitizar_texto(seo_in.get("title") or f"{limpo['brand']['name']} | Atendimento Especializado", 150),
        "description": sanitizar_texto(
            seo_in.get("description") or f"Conheça os serviços e agende seu horário com {limpo['brand']['name']}.",
            300,
        ),
    }

    # 4. Palette
    pal_in = spec.get("palette") if isinstance(spec.get("palette"), dict) else {}
    limpo["palette"] = {
        "background": validar_cor(pal_in.get("background"), "#0F0C10"),
        "surface": validar_cor(pal_in.get("surface"), "#1A151E"),
        "accent": validar_cor(pal_in.get("accent"), "#E5B869"),
        "accentStrong": validar_cor(pal_in.get("accentStrong"), "#F3D08C"),
        "text": validar_cor(pal_in.get("text"), "#F5F3F7"),
        "muted": validar_cor(pal_in.get("muted"), "#A19AA8"),
    }

    # 5. Contact
    ct_in = spec.get("contact") if isinstance(spec.get("contact"), dict) else {}
    num_wa = sanitizar_telefone_whatsapp(ct_in.get("whatsappNumber"))
    if not num_wa:
        avisos.append("Número do WhatsApp não informado ou inválido.")
    limpo["contact"] = {
        "whatsappNumber": num_wa,
        "whatsappMessage": sanitizar_texto(ct_in.get("whatsappMessage") or "Olá! Gostaria de mais informações.", 300),
        "city": sanitizar_texto(ct_in.get("city") or "", 100),
        "instagram": sanitizar_texto(ct_in.get("instagram") or "", 200),
    }

    # 6. Hero
    hero_in = spec.get("hero") if isinstance(spec.get("hero"), dict) else {}
    limpo["hero"] = {
        "badge": sanitizar_texto(hero_in.get("badge") or "Atendimento Exclusivo", 150),
        "title": sanitizar_texto(hero_in.get("title") or "Tratamentos e Serviços de Alto Padrão", 200),
        "highlightedText": sanitizar_texto(hero_in.get("highlightedText") or "Alto Padrão", 100),
        "description": sanitizar_texto(
            hero_in.get("description") or "Entre em contato e agende sua avaliação personalizada.", 500
        ),
        "primaryCta": sanitizar_texto(hero_in.get("primaryCta") or "Agendar via WhatsApp", 80),
        "secondaryCta": sanitizar_texto(hero_in.get("secondaryCta") or "Ver Serviços", 80),
        "imageUrl": sanitizar_texto(hero_in.get("imageUrl") or "", 500),
        "imageAlt": sanitizar_texto(hero_in.get("imageAlt") or limpo["brand"]["name"], 200),
        "availabilityLabel": sanitizar_texto(hero_in.get("availabilityLabel") or "Horários disponíveis para esta semana", 150),
    }

    # 7. Trust items
    trust_in = spec.get("trust") if isinstance(spec.get("trust"), list) else []
    limpo["trust"] = []
    for item in trust_in:
        if isinstance(item, dict):
            lbl = sanitizar_texto(item.get("label"), 100)
            val = sanitizar_texto(item.get("value"), 100)
            if lbl or val:
                limpo["trust"].append({"label": lbl, "value": val})

    # 8. Services
    srv_in = spec.get("services") if isinstance(spec.get("services"), list) else []
    limpo["services"] = []
    for idx, srv in enumerate(srv_in[:20]):  # máximo 20 serviços
        if isinstance(srv, dict):
            price_from = 0.0
            try:
                price_from = float(srv.get("priceFrom", 0))
                if price_from < 0:
                    price_from = 0.0
            except (ValueError, TypeError):
                price_from = 0.0

            limpo["services"].append(
                {
                    "id": sanitizar_texto(srv.get("id") or f"srv-{idx+1}", 50),
                    "title": sanitizar_texto(srv.get("title") or f"Serviço {idx+1}", 120),
                    "shortDescription": sanitizar_texto(srv.get("shortDescription") or "", 250),
                    "description": sanitizar_texto(srv.get("description") or "", 600),
                    "imageUrl": sanitizar_texto(srv.get("imageUrl") or "", 500),
                    "priceFrom": price_from,
                    "duration": sanitizar_texto(srv.get("duration") or "Sob consulta", 50),
                    "highlight": sanitizar_texto(srv.get("highlight") or "", 50) or None,
                }
            )

    if not limpo["services"]:
        avisos.append("Lista de serviços vazia. Foi incluído um serviço demonstrativo.")
        limpo["services"].append(
            {
                "id": "srv-1",
                "title": "Atendimento Especializado",
                "shortDescription": "Agende uma avaliação completa.",
                "description": "Entre em contato pelo WhatsApp para mais informações sobre os procedimentos disponíveis.",
                "imageUrl": "",
                "priceFrom": 0.0,
                "duration": "Sob consulta",
            }
        )

    # 9. Testimonials
    tst_in = spec.get("testimonials") if isinstance(spec.get("testimonials"), list) else []
    limpo["testimonials"] = []
    for tst in tst_in[:10]:
        if isinstance(tst, dict):
            rating = 5.0
            try:
                rating = float(tst.get("rating", 5.0))
                rating = max(1.0, min(5.0, rating))
            except (ValueError, TypeError):
                rating = 5.0

            limpo["testimonials"].append(
                {
                    "name": sanitizar_texto(tst.get("name") or "Cliente", 100),
                    "role": sanitizar_texto(tst.get("role") or "Cliente Atendido", 100),
                    "quote": sanitizar_texto(tst.get("quote") or "Excelente atendimento!", 500),
                    "rating": rating,
                    "avatarUrl": sanitizar_texto(tst.get("avatarUrl") or "", 500) or None,
                }
            )

    # 10. FAQs
    faq_in = spec.get("faqs") if isinstance(spec.get("faqs"), list) else []
    limpo["faqs"] = []
    for f in faq_in[:15]:
        if isinstance(f, dict):
            q = sanitizar_texto(f.get("question"), 200)
            a = sanitizar_texto(f.get("answer"), 500)
            if q and a:
                limpo["faqs"].append({"question": q, "answer": a})

    # 11. Budget
    bdg_in = spec.get("budget") if isinstance(spec.get("budget"), dict) else {}
    base_price = 0.0
    try:
        base_price = float(bdg_in.get("basePrice", 0))
        if base_price < 0:
            base_price = 0.0
    except (ValueError, TypeError):
        base_price = 0.0

    limpo["budget"] = {
        "title": sanitizar_texto(bdg_in.get("title") or "Simulador de Investimento", 120),
        "description": sanitizar_texto(
            bdg_in.get("description") or "Selecione os procedimentos desejados para simular uma estimativa de atendimento.",
            300,
        ),
        "basePrice": base_price,
        "consultationLabel": sanitizar_texto(bdg_in.get("consultationLabel") or "Avaliação presencial/online", 100),
    }

    # 12. Final CTA
    fcta_in = spec.get("finalCta") if isinstance(spec.get("finalCta"), dict) else {}
    limpo["finalCta"] = {
        "title": sanitizar_texto(fcta_in.get("title") or "Pronto para agendar seu atendimento?", 150),
        "description": sanitizar_texto(
            fcta_in.get("description") or "Fale com nossa equipe agora mesmo e garanta as melhores opções de horários.",
            300,
        ),
        "buttonLabel": sanitizar_texto(fcta_in.get("buttonLabel") or "Agendar Horário no WhatsApp", 80),
    }

    return limpo, avisos
