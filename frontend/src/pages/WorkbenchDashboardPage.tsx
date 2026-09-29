import { useQuery } from "@tanstack/react-query"
import { ArrowRight, ArrowUpRight, BarChart3, Compass, ListTodo, MapPin, Radar, Send, Sparkles } from "lucide-react"
import { Link } from "react-router-dom"
import { Header } from "@/components/layout/Header"
import { DailyOutreachWidget } from "@/components/dashboard/DailyOutreachWidget"
import { VisaoGeralCombinada } from "@/components/dashboard/VisaoGeralCombinada"
import { FunilConversaoCombinado } from "@/components/dashboard/FunilConversaoCombinado"
import { BreakdownNichoCombinado } from "@/components/dashboard/BreakdownNichoCombinado"
import { useMetricasCombinadas } from "@/hooks/useCombinado"
import { tarefasService } from "@/services/tarefasService"
import "./dashboard.css"

const atalhos = [
  { to: "/tarefas", icon: ListTodo, title: "Fila de oportunidades", detail: "Comece pelos contatos com mais potencial", number: "01" },
  { to: "/leads", icon: MapPin, title: "Captar no Maps", detail: "Planeje consultas e evite reanálises", number: "02" },
  { to: "/outreach/hoje", icon: Send, title: "Prospecção do dia", detail: "Avance conversas e retornos pendentes", number: "03" },
  { to: "/analytics", icon: BarChart3, title: "Analisar resultados", detail: "Veja onde a captação rende mais", number: "04" },
]

export function DashboardPage() {
  const { data: metricas } = useMetricasCombinadas()
  const { data: tarefas, isError } = useQuery({
    queryKey: ["tarefas-hoje", "dashboard"],
    queryFn: tarefasService.tarefasHoje,
  })
  const sinais = tarefas?.novos_quentes ?? []

  return (
    <div className="workbench min-h-screen bg-background text-foreground">
      <Header />
      <main className="mx-auto w-full max-w-7xl px-4 pb-16 pt-7 sm:px-6 lg:px-8">
        <div className="wb-heading-row">
          <div>
            <p className="wb-eyebrow"><span className="wb-live-dot" /> Central de trabalho</p>
            <h1>Encontre o próximo <em>bom contato.</em></h1>
            <p className="wb-intro">Um lugar para decidir onde buscar, quem abordar e o que merece seu tempo.</p>
          </div>
          <Link className="wb-heading-link" to="/leads">Abrir captação <ArrowUpRight size={17} /></Link>
        </div>

        <section className="wb-hero" aria-label="Prioridades de prospecção">
          <div className="wb-hero-main">
            <div className="wb-grid-pattern" aria-hidden="true" />
            <div className="wb-hero-top"><Radar size={20} /><span>Seu radar de oportunidades</span></div>
            <div className="wb-hero-content">
              <p className="wb-hero-kicker">PRIORIZE ANTES DE CAPTAR MAIS</p>
              <h2>{sinais.length > 0 ? "Há oportunidades esperando por você." : "Comece com uma busca mais inteligente."}</h2>
              <p>{sinais.length > 0
                ? "A fila destaca leads novos com melhor pontuação. Trabalhe os contatos existentes antes de ampliar a captura."
                : "Defina nichos e regiões com intenção. O modo econômico evita repetir análises de leads que já estão no CRM."}</p>
              <div className="wb-hero-actions">
                <Link to={sinais.length > 0 ? "/tarefas" : "/leads"} className="wb-primary-action">
                  {sinais.length > 0 ? "Abrir fila prioritária" : "Explorar leads"} <ArrowRight size={17} />
                </Link>
                <Link to="/leads" className="wb-secondary-action">Ver minha base <ArrowUpRight size={15} /></Link>
              </div>
            </div>
            <div className="wb-hero-foot"><span>MAPS + INSTAGRAM</span><span>BASE LOCAL</span><span>VOCÊ NO CONTROLE</span></div>
          </div>
          <div className="wb-signal-panel">
            <div className="wb-panel-header">
              <div><span className="wb-panel-overline">SINAIS ATIVOS</span><h3>Na sua mira</h3></div>
              <Compass size={24} aria-hidden="true" />
            </div>
            {sinais.length > 0 ? (
              <div className="wb-signal-list">
                {sinais.slice(0, 3).map((lead, index) => (
                  <Link to="/tarefas" key={lead.id} className="wb-signal-item">
                    <span className="wb-signal-index">{String(index + 1).padStart(2, "0")}</span>
                    <span className="wb-signal-copy"><strong>{lead.titulo}</strong><small>{lead.site_status === "sem_site" ? "Sem site" : lead.site_status === "site_ruim" ? "Site com melhorias" : "Lead novo"} · {lead.categoria || "Google Maps"}</small></span>
                    <span className="wb-score">{lead.score}</span>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="wb-signal-empty">
                <Sparkles size={22} aria-hidden="true" />
                <p>{isError ? "Não foi possível carregar a fila agora." : "Nenhum lead novo priorizado ainda."}</p>
                <span>{isError ? "Verifique se o servidor local está ativo." : "Os melhores contatos aparecem aqui após a primeira captura."}</span>
              </div>
            )}
            <Link to="/tarefas" className="wb-panel-footer">Ver todas as prioridades <ArrowRight size={16} /></Link>
          </div>
        </section>

        <section className="wb-overview" aria-label="Resumo do CRM">
          <div><span>Leads na base</span><strong>{metricas?.total ?? "—"}</strong><small>Maps e Instagram</small></div>
          <div><span>Para retomar hoje</span><strong>{metricas?.lembretes_hoje ?? "—"}</strong><small>Follow-ups pendentes</small></div>
          <div><span>Conversão</span><strong>{metricas ? `${metricas.taxa_conversao}%` : "—"}</strong><small>De contatos a clientes</small></div>
          <div><span>Novos em destaque</span><strong>{tarefas ? sinais.length : "—"}</strong><small>Até cinco na fila</small></div>
        </section>

        <section className="wb-section" aria-labelledby="wb-workflow-title">
          <div className="wb-section-heading"><div><p className="wb-section-kicker">SEU FLUXO</p><h2 id="wb-workflow-title">Do sinal à conversa</h2></div><p>Escolha o próximo passo sem perder o contexto.</p></div>
          <div className="wb-shortcuts">{atalhos.map(({ to, icon: Icon, title, detail, number }) => (
            <Link className="wb-shortcut" to={to} key={to}>
              <div className="wb-shortcut-top"><Icon size={21} /><span>{number}</span></div>
              <strong>{title}</strong><p>{detail}</p><ArrowUpRight className="wb-shortcut-arrow" size={19} />
            </Link>
          ))}</div>
        </section>

        <section className="wb-section wb-existing" aria-labelledby="wb-performance-title">
          <div className="wb-section-heading"><div><p className="wb-section-kicker">ACOMPANHAMENTO</p><h2 id="wb-performance-title">Ritmo e resultados</h2></div><p>Dados da sua operação, atualizados pelo CRM local.</p></div>
          <DailyOutreachWidget />
          <VisaoGeralCombinada />
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2"><FunilConversaoCombinado /><BreakdownNichoCombinado /></div>
        </section>
      </main>
    </div>
  )
}
