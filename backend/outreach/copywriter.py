"""Gerador do Pacote de Conversão via IA e Fallback Determinístico.

Produz mensagens personalizadas de prospecção, objeções realistas e orientações
para a Landing Page com base na estratégia comercial determinística.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import ia
from lp.template_catalog import normalizar_template_key

logger = logging.getLogger(__name__)

EXPRESSOES_PROIBIDAS = [
    "analisei profundamente sua empresa",
    "analisei profundamente o seu negócio",
    "estudei minuciosamente",
    "fizemos uma auditoria completa",
    "descobri um erro grave no seu sistema",
]


def validar_e_sanitizar_pacote_copy(payload: Dict[str, Any], lead: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitiza e valida a integridade do pacote gerado.
    Garante ausência de frases proibidas, integridade de fatos do Google e estrutura correta.
    """
    nome_empresa = (lead.get("nome") or "").strip()

    # Check messages
    messages = payload.get("messages") or {}
    for key in ["initial", "afterInterest", "prototypeDelivery", "closing"]:
        texto = messages.get(key) or ""
        for proibida in EXPRESSOES_PROIBIDAS:
            if proibida in texto.lower():
                texto = re.sub(re.escape(proibida), "analisei as informações públicas do seu negócio", texto, flags=re.IGNORECASE)
        messages[key] = texto.strip()

    followups = messages.get("followups") or []
    sanitized_followups = []
    default_delays = [2, 5, 9]
    default_objectives = [
        "Confirmar se conseguiu visualizar o protótipo",
        "Reforçar o benefício de prova social e conversão no WhatsApp",
        "Encerrar o contato de maneira educada e profissional"
    ]

    for idx, f in enumerate(followups[:3]):
        msg = (f.get("message") if isinstance(f, dict) else str(f)) or ""
        for proibida in EXPRESSOES_PROIBIDAS:
            if proibida in msg.lower():
                msg = re.sub(re.escape(proibida), "conforme mencionei antes", msg, flags=re.IGNORECASE)

        sanitized_followups.append({
            "order": idx + 1,
            "delayDays": f.get("delayDays", default_delays[idx]) if isinstance(f, dict) else default_delays[idx],
            "objective": f.get("objective", default_objectives[idx]) if isinstance(f, dict) else default_objectives[idx],
            "message": msg.strip()
        })

    # Garante 3 followups se vierem vazios
    if len(sanitized_followups) < 3:
        for idx in range(len(sanitized_followups), 3):
            sanitized_followups.append({
                "order": idx + 1,
                "delayDays": default_delays[idx],
                "objective": default_objectives[idx],
                "message": f"Olá! Passando apenas para saber se conseguiu dar uma olhada na proposta demonstrativa que enviei para a {nome_empresa or 'sua empresa'}. Fico à disposição!" if idx == 0 else
                           ("Um dos pontos principais da demonstração é agilizar o atendimento de novos clientes. Se fizer sentido conversar, é só me avisar." if idx == 1 else
                            "Imagino que a rotina esteja corrida por aí. Vou encerrar meus contatos por aqui para não incomodar. Se precisar no futuro, conte comigo!")
            })

    messages["followups"] = sanitized_followups
    payload["messages"] = messages

    # Check objections
    objections = payload.get("objections") or []
    sanitized_objections = []
    for item in objections:
        if isinstance(item, dict) and item.get("objection") and item.get("response"):
            sanitized_objections.append({
                "objection": str(item["objection"]).strip(),
                "response": str(item["response"]).strip()
            })

    if not sanitized_objections:
        sanitized_objections = [
            {
                "objection": "Já temos Instagram",
                "response": "O Instagram é ótimo para atrair atenção, mas nossa página serve para organizar os serviços e levar o cliente pronto para fechar direto no seu WhatsApp."
            },
            {
                "objection": "Não queremos investir nisso agora",
                "response": "Sem problemas! A demonstração visual é 100% gratuita para você visualizar como ficaria. Caso decida evoluir no futuro, você já tem a estrutura pronta."
            }
        ]
    payload["objections"] = sanitized_objections

    # Check prototype instructions
    prototype = payload.get("prototype") or {}
    payload["prototype"] = {
        "templateKey": normalizar_template_key(prototype.get("templateKey")),
        "focus": prototype.get("focus") if isinstance(prototype.get("focus"), list) and prototype.get("focus") else ["google_reviews", "whatsapp_conversion"],
        "heroAngle": prototype.get("heroAngle") or f"Atendimento de excelência em {lead.get('categoria') or 'serviços'} com agendamento rápido",
        "primaryCta": prototype.get("primaryCta") or "Falar pelo WhatsApp",
        "sectionsToHighlight": prototype.get("sectionsToHighlight") if isinstance(prototype.get("sectionsToHighlight"), list) and prototype.get("sectionsToHighlight") else ["trust", "services", "whatsapp_cta"]
    }

    return payload


def gerar_pacote_fallback(lead: Dict[str, Any], estrategia: Dict[str, Any], modo: str = "consultative") -> Dict[str, Any]:
    """Gera um pacote de conversão determinístico e completo sem depender de IA."""
    nome = (lead.get("nome") or "sua empresa").strip()
    categoria = (lead.get("categoria") or lead.get("nicho") or "serviços").strip()
    cidade = (lead.get("cidade") or "").strip()
    nota = float(lead.get("nota") or 0.0)
    avaliacoes = int(lead.get("num_avaliacoes") or 0)
    site_status = (lead.get("site_status") or "").strip()
    site_url = (lead.get("site_url") or "").strip()

    loc_str = f" em {cidade}" if cidade else ""
    rep_str = f"com avaliação {nota:.1f} e {avaliacoes} avaliações no Google Maps" if avaliacoes > 0 else "com excelente presença local"

    if not site_url or site_status == "sem_site":
        msg_inicial = (
            f"Olá! Vi que a {nome} tem uma presença muito forte{loc_str} ({rep_str}), "
            f"mas não encontrei um site próprio organizando seus serviços e direcionando novos clientes para o WhatsApp.\n\n"
            f"Montei uma demonstração rápida de como a sua página oficial poderia ficar. Posso te enviar para você dar uma olhada sem compromisso?"
        )
    elif site_status == "site_ruim":
        msg_inicial = (
            f"Olá! Estava navegando pela presença digital da {nome}{loc_str} e notei que a experiência do site atual "
            f"pode estar dificultando a conversão de novos clientes no WhatsApp.\n\n"
            f"Preparei uma demonstração visual com uma estrutura mais direta e focada em agendamentos. Posso te enviar a prévia?"
        )
    else:
        msg_inicial = (
            f"Olá! Vi que a {nome} possui uma ótima reputação{loc_str}. "
            f"Preparei uma proposta visual focada em transformar essa confiança em agendamentos mais rápidos pelo WhatsApp. Posso te mandar a demonstração?"
        )

    payload = {
        "strategy": {
            "opportunity": estrategia["opportunity"],
            "problem": estrategia["problem"],
            "evidence": estrategia["evidence"],
            "commercialAngle": estrategia["commercialAngle"],
            "recommendedCta": estrategia["recommendedCta"],
            "confidence": estrategia["confidence"],
        },
        "messages": {
            "initial": msg_inicial,
            "afterInterest": f"Excelente! Montei a demonstração utilizando as informações públicas da {nome}, destacando a prova social e os seus principais serviços.",
            "prototypeDelivery": "Aqui está a demonstração interativa: [link]\n\nEla mostra exatamente como os clientes visualizam os serviços e iniciam o contato via WhatsApp.",
            "followups": [
                {
                    "order": 1,
                    "delayDays": 2,
                    "objective": "Confirmar se conseguiu visualizar o protótipo",
                    "message": f"Olá! Tudo bem? Passando para confirmar se conseguiu abrir a demonstração da {nome} que te enviei."
                },
                {
                    "order": 2,
                    "delayDays": 5,
                    "objective": "Reforçar benefício de conversão no WhatsApp",
                    "message": f"Um dos grandes diferenciais dessa estrutura para a {nome} é facilitar o contato direto no WhatsApp de quem pesquisa no Google. Caso queira ajustar algo na proposta, me avise!"
                },
                {
                    "order": 3,
                    "delayDays": 9,
                    "objective": "Encerrar de maneira educada",
                    "message": "Imagino que a rotina aí esteja bem movimentada. Vou encerrar minhas mensagens por aqui para não tomar seu tempo. Se decidir estruturar o atendimento digital no futuro, fico à disposição!"
                }
            ],
            "closing": f"Agradeço pela atenção! Se quiser colocar essa estrutura no ar para a {nome}, conseguimos ativar rapidamente."
        },
        "objections": [
            {
                "objection": "Já temos Instagram",
                "response": "O Instagram é ótimo para criar conexão, mas nossa Landing Page serve como o canal final de fechamento, levando o cliente decidido direto para o seu WhatsApp."
            },
            {
                "objection": "Não queremos investir agora",
                "response": "Compreendo perfeitamente! A demonstração é 100% gratuita para você guardar a ideia. Se fizer sentido no futuro, já teremos metade do caminho andado."
            },
            {
                "objection": "Já temos uma pessoa que cuida do marketing",
                "response": "Excelente! O objetivo dessa demonstração não é substituir sua equipe, mas oferecer uma estrutura otimizada que eles mesmos podem usar para converter mais."
            }
        ],
        "prototype": {
            "templateKey": "geral-conversao",
            "focus": ["google_reviews", "whatsapp_conversion"],
            "heroAngle": f"A melhor experiência em {categoria} para clientes de {cidade or 'sua região'}",
            "primaryCta": "Solicitar Atendimento pelo WhatsApp",
            "sectionsToHighlight": ["trust", "services", "whatsapp_cta"]
        },
        "provider": "fallback_deterministico"
    }

    return validar_e_sanitizar_pacote_copy(payload, lead)


def gerar_pacote_com_ia(
    lead: Dict[str, Any],
    estrategia: Dict[str, Any],
    modo: str = "consultative",
    instrucao_adicional: Optional[str] = None
) -> Dict[str, Any]:
    """Tenta gerar o pacote via IA (usando ia.executar_com_fallback) com fallback gracioso."""
    nome = (lead.get("nome") or "Empresa").strip()
    categoria = (lead.get("categoria") or lead.get("nicho") or "Serviços").strip()
    cidade = (lead.get("cidade") or "").strip()
    nota = float(lead.get("nota") or 0.0)
    avaliacoes = int(lead.get("num_avaliacoes") or 0)

    prompt_sistema = (
        "Você é um Copywriter e Estrategista Comercial B2B especialista em prospecção direta.\n"
        "Sua tarefa é gerar um Pacote de Conversão completo em formato JSON estrito para um lead local.\n\n"
        "REGRAS DE CONTEÚDO E SEGURANÇA:\n"
        "1. Mantenha total fidelidade aos fatos (nota, avaliações e nome da empresa vindos do Google Maps). NUNCA invente preços ou depoimentos falsos.\n"
        "2. NUNCA use frases como 'Analisei profundamente sua empresa' ou 'Auditei seu negócio'. Use tom transparente e consultivo.\n"
        "3. A mensagem inicial deve ser curta, objetiva e focar em pedir autorização para enviar uma demonstração visual (sem tentar vender tudo na primeira mensagem).\n"
        "4. A sequência deve ter exatamente 3 followups com objetivos e dias diferentes (Dia 2, Dia 5, Dia 9).\n"
        "5. As respostas a objeções devem ser curtas, não agressivas e respeitosas.\n"
        "6. O protótipo deve indicar o foco visual e os títulos comerciais alinhados com o mesmo argumento da mensagem.\n\n"
        "FORMATO DE SAÍDA EXIGIDO (JSON ESTRITO):\n"
        "{\n"
        '  "messages": {\n'
        '    "initial": "...",\n'
        '    "afterInterest": "...",\n'
        '    "prototypeDelivery": "...",\n'
        '    "followups": [\n'
        '      {"order": 1, "delayDays": 2, "objective": "...", "message": "..."},\n'
        '      {"order": 2, "delayDays": 5, "objective": "...", "message": "..."},\n'
        '      {"order": 3, "delayDays": 9, "objective": "...", "message": "..."}\n'
        '    ],\n'
        '    "closing": "..."\n'
        '  },\n'
        '  "objections": [\n'
        '    {"objection": "...", "response": "..."}\n'
        '  ],\n'
        '  "prototype": {\n'
        '    "templateKey": "geral-conversao",\n'
        '    "focus": ["google_reviews", "whatsapp_conversion"],\n'
        '    "heroAngle": "...",\n'
        '    "primaryCta": "...",\n'
        '    "sectionsToHighlight": ["trust", "services", "whatsapp_cta"]\n'
        '  }\n'
        "}"
    )

    prompt_usuario = (
        f"DADOS DO LEAD:\n"
        f"- Nome: {nome}\n"
        f"- Categoria: {categoria}\n"
        f"- Cidade: {cidade}\n"
        f"- Nota Google: {nota} ({avaliacoes} avaliações)\n"
        f"- Status do Site: {lead.get('site_status')}\n"
        f"- Site Atual: {lead.get('site_url') or 'Não tem'}\n"
        f"- Instagram: {lead.get('instagram_url') or 'Não informado'}\n\n"
        f"DIAGNÓSTICO ESTRATÉGICO:\n"
        f"- Oportunidade: {estrategia['opportunity']}\n"
        f"- Problema: {estrategia['problem']}\n"
        f"- Evidências: {json.dumps(estrategia['evidence'], ensure_ascii=False)}\n"
        f"- Ângulo Comercial: {estrategia['commercialAngle']}\n"
        f"- CTA Recomendado: {estrategia['recommendedCta']}\n"
        f"- Modo de Abordagem: {modo}\n"
    )

    if instrucao_adicional:
        prompt_usuario += f"\nINSTRUÇÃO ADICIONAL DO USUÁRIO:\n{instrucao_adicional}\n"

    def _parser_json(texto_bruto):
        match = re.search(r"\{.*\}", texto_bruto, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(texto_bruto)

    try:
        dados_ia, provedor, _ = ia.executar_com_fallback(
            system=prompt_sistema,
            user=prompt_usuario,
            parser=_parser_json,
            descricao_log="pacote de conversao"
        )

        if dados_ia and isinstance(dados_ia, dict):
            dados_ia["strategy"] = {
                "opportunity": estrategia["opportunity"],
                "problem": estrategia["problem"],
                "evidence": estrategia["evidence"],
                "commercialAngle": estrategia["commercialAngle"],
                "recommendedCta": estrategia["recommendedCta"],
                "confidence": estrategia["confidence"],
            }
            dados_ia["provider"] = provedor
            return validar_e_sanitizar_pacote_copy(dados_ia, lead)

    except Exception:
        logger.exception("Falha ao chamar IA para pacote de conversão. Usando fallback.")

    return gerar_pacote_fallback(lead, estrategia, modo)
