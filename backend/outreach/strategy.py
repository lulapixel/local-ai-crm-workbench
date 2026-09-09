"""Diagnóstico comercial determinístico para geração do Pacote de Conversão.

Analisa os dados reais e verificados do lead (status do site, raio-X, avaliações do Google,
Instagram) para extrair evidências concretas e selecionar a oportunidade principal sem depender de IA.
"""

from typing import Any, Dict, List


def extrair_evidencias_e_estrategia(lead: Dict[str, Any]) -> Dict[str, Any]:
    """Analisa um lead e produz um diagnóstico comercial determinístico.

    Retorna uma estrutura com:
      - opportunity (string)
      - problem (string)
      - evidence (list[str])
      - commercial_angle (string)
      - recommended_cta (string)
      - confidence ("low" | "medium" | "high")
      - primary_rule (string)
    """
    nome = (lead.get("nome") or "A empresa").strip()
    categoria = (lead.get("categoria") or lead.get("nicho") or "serviços").strip()
    cidade = (lead.get("cidade") or "").strip()
    nota = float(lead.get("nota") or 0.0)
    avaliacoes = int(lead.get("num_avaliacoes") or 0)
    site_status = (lead.get("site_status") or "").strip()
    site_url = (lead.get("site_url") or "").strip()
    site_problemas = (lead.get("site_problemas") or "").strip()
    instagram_url = (lead.get("instagram_url") or "").strip()

    evidencias: List[str] = []

    if avaliacoes > 0:
        evidencias.append(f"Nota {nota:.1f} com {avaliacoes} avaliações no Google Maps.")
    else:
        evidencias.append("Empresa cadastrada no Google Maps.")

    if not site_url or site_status == "sem_site":
        evidencias.append("Não possui site próprio registrado.")
    elif site_status == "site_ruim":
        if site_problemas:
            evidencias.append(f"Site atual com gargalos identificados: {site_problemas}.")
        else:
            evidencias.append("Site atual apresenta problemas de clareza ou conversão.")

    if instagram_url:
        evidencias.append("Possui presença no Instagram.")

    # Regras determinísticas de priorização de oportunidade (hierarquia 1 a 6)
    # 1. Ausência de site
    if not site_url or site_status == "sem_site":
        problema = "Empresa sem site próprio para concentrar a reputação e converter visitantes."
        if avaliacoes >= 10 and nota >= 4.2:
            oportunidade = "Transformar a excelente reputação do Google em um canal direto de vendas."
            angulo = "Destacar a nota 5 estrelas e avaliações já conquistadas como prova social no topo da página."
            cta = "Pedir autorização para enviar a demonstração visual pronta."
            confiabilidade = "high"
        else:
            oportunidade = "Criar um canal central de apresentação de serviços e agendamento via WhatsApp."
            angulo = "Apresentar uma estrutura digital profissional e direta para atendimento."
            cta = "Sugerir o envio do protótipo visual sem compromisso."
            confiabilidade = "medium" if avaliacoes > 0 else "low"
        regra_chave = "sem_site"

    # 2. Site com problemas graves
    elif site_status == "site_ruim":
        problema = f"O site atual não transmite o valor do negócio ({site_problemas or 'gargalos de conversão'})."
        oportunidade = "Reposicionar a experiência digital com foco em agendamentos no WhatsApp."
        angulo = "Mostrar uma versão modernizada que resolve os problemas do site atual."
        cta = "Apresentar a proposta de reformulação focada em rápida conversão."
        confiabilidade = "high"
        regra_chave = "site_ruim"

    # 3. Reputação digital não aproveitada
    elif avaliacoes >= 20 and nota >= 4.5:
        problema = "Falta de aproveitamento estratégico das dezenas de avaliações 5 estrelas como motor de atração."
        oportunidade = "Usar a forte prova social do Google como principal argumento de conversão."
        angulo = "Colocar os depoimentos reais em posição de destaque supremo na jornada do cliente."
        cta = "Enviar o protótipo focado em reputação e WhatsApp."
        confiabilidade = "high"
        regra_chave = "reputacao_alta"

    # 4. Instagram forte sem canal de conversão
    elif instagram_url and (not site_url or site_status == "sem_site"):
        problema = "Dependência exclusiva de redes sociais sem uma página própria de fechamento."
        oportunidade = "Transformar o tráfego do Instagram em pedidos diretos e organizados."
        angulo = "Integrar o apelo visual do Instagram com um botão de agendamento ágil."
        cta = "Mostrar a demonstração de Landing Page complementar ao Instagram."
        confiabilidade = "medium"
        regra_chave = "instagram_sem_site"

    # 5. Serviços mal apresentados ou falta de CTA direto (Fallback padrão)
    else:
        problema = "Página comercial genérica sem chamada para ação (CTA) direta e clara."
        oportunidade = "Estruturar uma apresentação objetiva com agendamento direto em 1 clique."
        angulo = "Focar na clareza dos serviços oferecidos e facilidade de contato."
        cta = "Apresentar o protótipo com canal direto de atendimento."
        confiabilidade = "medium"
        regra_chave = "cta_geral"

    return {
        "opportunity": oportunidade,
        "problem": problema,
        "evidence": evidencias,
        "commercialAngle": angulo,
        "recommendedCta": cta,
        "confidence": confiabilidade,
        "primaryRule": regra_chave,
    }
