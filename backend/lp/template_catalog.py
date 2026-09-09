"""Catálogo de templates de Landing Page para o ProspectOS.

Define os templates disponíveis e a lógica de seleção automática baseada no nicho e categoria do lead.
"""

TEMPLATES = {
    "estetica-premium": {
        "key": "estetica-premium",
        "nome": "Estética Premium",
        "descricao": "Visual sofisticado e acolhedor em tons rosa champanhe e dourado, ideal para clínicas de estética, spas e procedimentos de beleza.",
        "nichos": [
            "clínica de estética",
            "estética",
            "harmonização facial",
            "spa",
            "dermatologia",
            "salão de beleza",
            "sobrancelhas",
            "micropigmentação",
            "podologia",
            "massagem",
            "esteticista",
        ],
        "default_palette": {
            "background": "#0F0C10",
            "surface": "#1A151E",
            "accent": "#E5B869",
            "accentStrong": "#F3D08C",
            "text": "#F5F3F7",
            "muted": "#A19AA8",
        },
        "default_hero": {
            "badge": "Atendimento exclusivo com agendamento rápido",
            "title": "Realce sua beleza natural com tratamentos de alto padrão",
            "highlightedText": "beleza natural",
            "description": "Protocolos personalizados desenvolvidos para oferecer resultados visíveis e duradouros em um ambiente seguro e relaxante.",
            "primaryCta": "Agendar Consulta via WhatsApp",
            "secondaryCta": "Ver Procedimentos",
            "imageUrl": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?q=80&w=1200&auto=format&fit=crop",
            "imageAlt": "Ambiente de tratamento estético moderno",
            "availabilityLabel": "Horários disponíveis para esta semana",
        },
        "default_services": [
            {
                "id": "srv-1",
                "title": "Harmonização Facial Personalizada",
                "shortDescription": "Técnicas avançadas para valorização dos traços faciais com naturalidade.",
                "description": "Avaliação detalhada para alinhar proporções faciais mantendo a expressão individual de cada paciente.",
                "imageUrl": "https://images.unsplash.com/photo-1616394584738-fc6e612e71b9?q=80&w=800&auto=format&fit=crop",
                "priceFrom": 0,
                "duration": "60 min",
                "highlight": "Mais Procurado",
            },
            {
                "id": "srv-2",
                "title": "Rejuvenescimento & Bioestimuladores",
                "shortDescription": "Estimulação natural de colágeno para firmeza e viço da pele.",
                "description": "Tratamento focado na firmeza da pele, suavizando linhas e devolvendo a luminosidade natural.",
                "imageUrl": "https://images.unsplash.com/photo-1512290900673-70024fe74923?q=80&w=800&auto=format&fit=crop",
                "priceFrom": 0,
                "duration": "45 min",
            },
            {
                "id": "srv-3",
                "title": "Limpeza de Pele Profunda",
                "shortDescription": "Remoção de impurezas, hidratação profunda e renovação celular.",
                "description": "Higienização completa com vapor de ozônio, extração delicada e máscara calmante adequada ao seu tipo de pele.",
                "imageUrl": "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?q=80&w=800&auto=format&fit=crop",
                "priceFrom": 0,
                "duration": "60 min",
            },
        ],
        "default_faqs": [
            {
                "question": "Como funciona a primeira avaliação?",
                "answer": "Na primeira consulta realizamos uma análise detalhada das suas necessidades para indicar o protocolo mais seguro e eficaz.",
            },
            {
                "question": "Os procedimentos exigem tempo de repouso?",
                "answer": "A maioria dos procedimentos permite retornar às atividades rotineiras no mesmo dia, com orientações pós-atendimento simples.",
            },
            {
                "question": "Como posso agendar meu horário?",
                "answer": "O agendamento é feito diretamente pelo WhatsApp. Nossa equipe confirma a disponibilidade em poucos minutos.",
            },
        ],
    },
    "geral-conversao": {
        "key": "geral-conversao",
        "nome": "Geral Alta Conversão",
        "descricao": "Template versátil de alto impacto e carregamento rápido para prestadores de serviços em geral.",
        "nichos": [],
        "default_palette": {
            "background": "#0D1117",
            "surface": "#161B22",
            "accent": "#2F81F7",
            "accentStrong": "#58A6FF",
            "text": "#F0F6FC",
            "muted": "#8B949E",
        },
        "default_hero": {
            "badge": "Atendimento direto com especialistas",
            "title": "Soluções profissionais e atendimento rápido para você",
            "highlightedText": "atendimento rápido",
            "description": "Atendimento transparente com foco na solução do seu problema e agilidade no agendamento.",
            "primaryCta": "Falar pelo WhatsApp",
            "secondaryCta": "Conhecer Serviços",
            "imageUrl": "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?q=80&w=1200&auto=format&fit=crop",
            "imageAlt": "Atendimento profissional",
            "availabilityLabel": "Orçamentos e detalhes via WhatsApp",
        },
        "default_services": [
            {
                "id": "srv-1",
                "title": "Atendimento Personalizado",
                "shortDescription": "Atendimento inicial e proposta sob medida.",
                "description": "Análise técnica detalhada das suas necessidades para entregar o melhor custo-benefício.",
                "imageUrl": "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?q=80&w=800&auto=format&fit=crop",
                "priceFrom": 0,
                "duration": "A confirmar",
                "highlight": "Recomendado",
            }
        ],
        "default_faqs": [
            {
                "question": "Como solicitar um orçamento?",
                "answer": "Clique no botão de WhatsApp para ser atendido diretamente pela equipe responsável.",
            },
            {
                "question": "Qual é o prazo de resposta?",
                "answer": "Respondemos o WhatsApp o mais breve possível dentro do horário comercial.",
            },
        ],
    },
}

CANONICAL_FALLBACK_TEMPLATE = "geral-conversao"


def normalizar_template_key(value: object) -> str:
    """Retorna somente chaves do catálogo, usando o fallback canônico para legados/inválidos."""
    template_key = value.strip() if isinstance(value, str) else ""
    if template_key in TEMPLATES:
        return template_key
    return CANONICAL_FALLBACK_TEMPLATE


def selecionar_template(lead: dict) -> str:
    """Seleciona o template mais adequado com base nas informações do lead.

    Tenta encontrar correspondência no nicho ou categoria. Se não houver,
    retorna o template fallback ("estetica-premium" se for área de beleza/saúde,
    ou "geral-conversao").
    """
    nicho = (lead.get("nicho") or "").strip().lower()
    categoria = (lead.get("categoria") or "").strip().lower()
    texto_busca = f"{nicho} {categoria}"

    for template_key, info in TEMPLATES.items():
        if template_key == "geral-conversao":
            continue
        for termo in info.get("nichos", []):
            if termo in texto_busca:
                return template_key

    # Se a palavra estetica/clinica/beleza/spa aparecer no texto, usa estetica-premium
    palavras_chave_estetica = ["estetica", "estética", "beleza", "clinica", "clínica", "spa", "laser", "sobrancelha"]
    if any(p in texto_busca for p in palavras_chave_estetica):
        return "estetica-premium"

    return CANONICAL_FALLBACK_TEMPLATE
