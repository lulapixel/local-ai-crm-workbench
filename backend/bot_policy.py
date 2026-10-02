"""Padrão versionado de decisão. Heurísticas observáveis, não um benchmark."""
VERSION = "SOL-OPS-1"
CHOICES = {
    "luna_high": {"model": "gpt-6-luna", "effort": "high", "label": "Luna 6 · high"},
    "luna_xhigh": {"model": "gpt-6-luna", "effort": "xhigh", "label": "Luna 6 · xhigh"},
    "luna_max": {"model": "gpt-6-luna", "effort": "max", "label": "Luna 6 · max"},
    "sol_medium": {"model": "gpt-6.1-sol", "effort": "medium", "label": "Sol 6.1 · medium"},
    "sol_high": {"model": "gpt-6.1-sol", "effort": "high", "label": "Sol 6.1 · high"},
}
TASK_TYPES = {"auto": "Bot decide pelo contexto", "triage": "Triagem e prioridades", "planning": "Planejamento entre setores", "review": "Revisão de estratégia", "diagnosis": "Diagnóstico de resultados"}


def decidir(snapshot, config, reviewer=False):
    campaigns = snapshot.get("campaigns", [])
    history = snapshot.get("history", [])
    rejected = sum(r.get("feedback") == "rejected" for r in history)
    partial = sum(r.get("feedback") == "partial" for r in history)
    niches = len({c.get("nicho") for c in campaigns if c.get("nicho")})
    factors = {"campaigns": len(campaigns), "niches": niches, "rejected": rejected, "partial": partial}
    # Uma falha de infraestrutura nunca eleva esforço/modelo.
    complexity = min(len(campaigns), 10) * 2 + min(niches, 5) * 3 + rejected * 8 + partial * 3
    task = "review" if reviewer else config.get("task_type", "auto")
    if task == "auto":
        task = "diagnosis" if rejected >= 2 else "planning" if niches >= 3 else "triage"
    forced = config.get("selection", "auto")
    if forced != "auto":
        if forced not in CHOICES:
            raise ValueError("Modelo/esforço fora da lista permitida.")
        choice, why = forced, "Escolha explícita do operador; não haverá substituição."
    elif task == "diagnosis" and rejected >= 3:
        choice, why = "sol_high", "Três ou mais estratégias rejeitadas exigem diagnóstico amplo."
    elif task in ("diagnosis", "review") and (rejected >= 2 or complexity >= 35):
        choice, why = "sol_medium", "Revisão de decisões com contestação ou complexidade elevada."
    elif complexity >= 35:
        choice, why = "luna_max", "Muitas campanhas ou decisões contestadas; maior profundidade na mesma família."
    elif complexity >= 20 or task == "planning":
        choice, why = "luna_xhigh", "Planejamento entre setores ou várias alternativas concorrentes."
    else:
        choice, why = "luna_high", "Triagem delimitada; usar a base autorizada e evitar esforço extra."
    return {**CHOICES[choice], "choice": choice, "task_type": task, "standard": VERSION,
            "complexity_points": complexity, "factors": factors, "reason": why,
            "qualification": "Heurística configurada; vantagem econômica e qualidade ainda não medidas."}
