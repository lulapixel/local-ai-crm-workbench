import { useState } from "react"
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowRight, ArrowUpRight, Bot, CircleCheck, Compass, FileSearch, ShieldCheck } from "lucide-react"
import { Link } from "react-router-dom"
import { Header } from "@/components/layout/Header"
import { ManagementEditor } from "@/components/ManagementEditor"
import { ManagementReceipts } from "@/components/ManagementReceipts"
import { getManagement } from "@/services/managementService"
import { brl } from "@/lib/management"
import "./workspace.css"
import "./management.css"

export function DashboardPage() {
  const [month, setMonth] = useState("")
  const client = useQueryClient()
  const query = useQuery({ queryKey: ["management", month], queryFn: () => getManagement(month), staleTime: 30_000, refetchOnWindowFocus: false, placeholderData: keepPreviousData })
  const data = query.data
  const saved = () => {
    void client.invalidateQueries({ queryKey: ["management"] })
    void client.invalidateQueries({ queryKey: ["operation-plan"] })
  }
  return <><Header /><main className="desk-page manager-page">
    <div className="desk-page-heading"><div><p className="desk-eyebrow">PROSPECTOS / MESA DO GESTOR</p><h1>Direcione o trabalho.<br /><em>Acompanhe o que avança.</em></h1><p>Seu ponto de decisão entre pesquisa, proposta e resultado.</p></div><Link className="desk-secondary" to="/operacao">Abrir fila de trabalho <ArrowUpRight size={15} /></Link></div>
    {query.isPending && <div className="manager-loading" role="status">Conferindo suas prioridades e registros locais…</div>}
    {query.isPlaceholderData && <p role="status" className="desk-caption">Carregando o mês selecionado; os valores anteriores continuam visíveis até a atualização.</p>}
    {query.isError && <div className="desk-notice" role="alert">{query.error.message} <button className="desk-secondary" onClick={() => void query.refetch()}>Tentar novamente</button></div>}
    {data && <>
      {data.operation.demo && <p className="desk-notice" role="status">Demonstração isolada com dados fictícios. Automação e envios desativados.</p>}
      <div className="manager-briefing">
        <section className="manager-recommendation" aria-labelledby="recommendation-title"><p className="desk-eyebrow"><Compass size={14} /> RECOMENDAÇÃO PRINCIPAL</p><h2 id="recommendation-title">{data.recommendation.title}</h2><p>{data.recommendation.reason}</p>
          {data.profile.explanation === "reasoned" && <div className="manager-reasoning"><strong>Por que esta direção</strong><p>{data.recommendation.alternative}</p><small>Base: {data.recommendation.evidence.toLowerCase()}.</small></div>}
          {data.recommendation.href.startsWith("#") ? <a href={data.recommendation.href} className="desk-primary">{data.recommendation.label}<ArrowRight size={15} /></a> : <Link to={data.recommendation.href} className="desk-primary">{data.recommendation.label}<ArrowRight size={15} /></Link>}
        </section>
        <aside className="manager-mandate"><p className="desk-eyebrow">SEU MODO DE OPERAÇÃO</p><h2>Gestão com contexto.</h2><dl><div><dt>Frentes de trabalho</dt><dd>{data.profile.focus === "parallel" ? "Serviços + contratos remotos" : data.profile.focus === "websites" ? "Serviços de websites" : "Contratos remotos"}</dd></div><div><dt>Território preferido</dt><dd>{data.profile.city || "Ainda não definido"}</dd></div><div><dt>Novos gastos nesta preparação</dt><dd>Sem autorização de gasto novo</dd></div><div><dt>Referência mensal recebida</dt><dd>{data.profile.monthly_received_target_cents === null ? "Ainda não definida" : brl(data.profile.monthly_received_target_cents)}</dd></div></dl><a href="#oferta">Ajustar perfil e oferta <ArrowUpRight size={13} /></a><p>Preferências orientam decisões. Os limites e aprovações do bot continuam valendo.</p></aside>
      </div>
      <section className="manager-evidence-path" aria-label="Etapas observadas da operação"><div><span>PREPARAÇÃO</span><strong>{data.readiness.completed}/{data.readiness.total}</strong><p>itens da oferta revisados</p></div><ArrowRight aria-hidden="true" size={16} /><div><span>EXECUÇÃO</span><strong>{data.operation.available_actions}</strong><p>ações elegíveis no recorte</p></div><ArrowRight aria-hidden="true" size={16} /><div><span>RECEBIMENTOS</span><strong>{brl(data.finance.received_cents)}</strong><p>registrados em {data.finance.month.split("-").reverse().join("/")}</p></div><p className="manager-path-note">Cada etapa tem sua evidência.<br />Preparação não é venda.</p></section>
      <div className="desk-section-heading"><h2>Decisões com trabalho preparado</h2><Link to="/operacao">Ver fila completa <ArrowUpRight size={14} /></Link></div>
      {data.operation.actions.length ? <div className="manager-decisions">{data.operation.actions.slice(0, 3).map(action => <article key={action.id}><span className="manager-tag">{action.department}</span><h3>{action.name}</h3><p>{action.reason}</p><strong className="manager-decision-label">Sua decisão: {action.human_decision.toLowerCase()}.</strong>{data.profile.explanation === "reasoned" && <details><summary>Entender o critério</summary><p>{action.learning}</p></details>}<Link className="desk-secondary" to={action.href}>Conferir contexto <ArrowUpRight size={13} /></Link></article>)}</div> : <div className="manager-empty">Nenhuma ação elegível no recorte da sessão. Prepare a oferta ou <Link to="/pesquisa">abra a mesa de pesquisa</Link> para investigar oportunidades.</div>}
      {data.operation.limited && <p className="desk-caption">A fila considera até {data.operation.scan_limit} registros Maps. Use filtros na sessão para trabalhar outro recorte.</p>}
      <div className="manager-lanes"><div><FileSearch size={19} /><div><h3>Serviços locais</h3><p>Use uma oferta específica para investigar necessidades, qualificar contatos e revisar abordagens.</p></div><Link to="/pesquisa" aria-label="Abrir pesquisa de serviços locais"><ArrowUpRight size={17} /></Link></div><div><CircleCheck size={19} /><div><h3>Contratos remotos</h3><p>Reaproveite a demonstração como amostra de trabalho e explique sua contribuição e o apoio da IA.</p></div><a href="#oferta" aria-label="Preparar material para contratos remotos"><ArrowUpRight size={17} /></a></div></div>
      <ManagementEditor data={data} onSaved={saved} />
      <ManagementReceipts data={data} month={month} onMonth={setMonth} onSaved={saved} />
      <section className="manager-control"><Bot size={20} /><div><h2>O que a automação pode fazer agora</h2><p>Agenda estratégica {data.operation.strategy.enabled ? `às ${data.operation.strategy.hour} (Brasília)` : "desativada"} · {data.operation.strategy.used_today}/{data.operation.strategy.daily_limit} chamadas hoje. Transmissão automática {data.operation.channels.live_enabled ? "sujeita às regras e aprovações dos canais" : "desativada"}.</p><p>Esta mesa usa regras locais. O contexto de frente e prontidão estará disponível nas chamadas estratégicas já autorizadas; nenhuma chamada é feita ao abrir a página.</p></div><Link to="/bot" className="desk-secondary"><ShieldCheck size={14} />Conferir controles</Link></section>
      <p className="desk-caption">Perfil aplicado ao planejamento local. Utilidade comercial e satisfação ainda precisam ser observadas no uso; não há promessa de renda ou de prazo para venda.</p>
    </>}
  </main></>
}
