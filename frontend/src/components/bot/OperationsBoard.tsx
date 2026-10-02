import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Activity, ArrowUpRight, Check, MessageCircle } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { httpClient } from "@/services/httpClient"

interface Contact { place_id: string; nome: string; telefone: string; status: string }
interface Operations {
  demo: boolean
  scheduler: { state: string; last_tick: string | null; error: string | null }
  metrics: { prepared: number; sent: number; replied: number; won: number; suppressed: number; useful_campaigns: number; uncertain: number; monetary_cost: null }
  actions: { title: string; detail: string; href: string; level: string }[]
  contacts: Contact[]
  measurement_note: string
}
const clocks: Record<string, string> = { active: "Relógio ativo", starting: "Aguardando primeiro ciclo", attention: "Relógio requer atenção", stopped: "Relógio não iniciado" }
const statuses: Record<string, string> = { contatado: "Aguardando resposta", respondeu: "Respondeu", fechou: "Fechou", recusou: "Recusou", ignorado: "Não contatar" }

function ContactResult({ contact, refresh }: { contact: Contact; refresh: () => void }) {
  const [outcome, setOutcome] = useState("replied")
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  async function save() {
    setBusy(true)
    try {
      const result = await httpClient.post<{ note: string }>(`/api/bot/contacts/${encodeURIComponent(contact.place_id)}/outcome`, { outcome, confirmed })
      toast.success(result.note || "Resultado já registrado.")
      setConfirmed(false)
      refresh()
    } catch (error) { toast.error(error instanceof Error ? error.message : "Não foi possível registrar.") }
    finally { setBusy(false) }
  }
  return <article className="bot-contact-result">
    <div><strong>{contact.nome}</strong><p>{contact.telefone} · {statuses[contact.status] ?? contact.status}</p></div>
    <fieldset disabled={busy}>
      <label className="bot-label" htmlFor={`outcome-${contact.place_id}`}>Resultado observado</label>
      <select id={`outcome-${contact.place_id}`} value={outcome} onChange={e => { setOutcome(e.target.value); setConfirmed(false) }}>
        <option value="replied">Respondeu · encerrar cadência automática</option><option value="won">Fechou negócio</option>
        <option value="declined">Recusou esta oferta</option><option value="do_not_contact">Pediu para não ser contatado novamente</option>
      </select>
      <label className="bot-outcome-confirm"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} /> Eu observei esse resultado e confirmo o registro manual.</label>
      <Button size="sm" variant="outline" disabled={!confirmed || busy} onClick={save}><Check size={15} /> Registrar resultado</Button>
    </fieldset>
  </article>
}

export function OperationsBoard({ refreshBot }: { refreshBot: () => void }) {
  const query = useQuery({ queryKey: ["bot-operations"], queryFn: () => httpClient.get<Operations>("/api/bot/operations"), refetchInterval: 10000 })
  const refresh = () => { void query.refetch(); refreshBot() }
  if (query.isPending) return <section className="bot-panel" role="status">Consultando a operação…</section>
  if (query.isError || !query.data) return <section className="bot-panel" role="alert">Não foi possível consultar a operação. <Button variant="outline" onClick={refresh}>Tentar novamente</Button></section>
  const data = query.data
  return <>
    <section className="bot-control-room" aria-labelledby="operation-title">
      {data.demo && <p className="bot-measurement" role="status">Demonstração com dados de teste. Os resultados exibidos não representam uma operação comercial real.</p>}
      <div className="bot-control-heading"><div><p className="bot-kicker">ESTAÇÃO DE PROSPECÇÃO</p><h1 id="operation-title">Sua próxima ação, com contexto.</h1><p>Revise contatos, acompanhe respostas e veja o que a automação realmente está fazendo.</p></div>
        <div className={`bot-clock ${data.scheduler.state}`} role="status"><Activity size={17} /><span>{clocks[data.scheduler.state] ?? data.scheduler.state}<small>{data.scheduler.last_tick ? `Último ciclo: ${new Date(data.scheduler.last_tick).toLocaleTimeString("pt-BR")}` : "Backend normal necessário para executar a agenda"}</small></span></div>
      </div>
      <div className="bot-next-actions">{data.actions.map((action, index) => <a key={action.title} href={action.href} className={action.level}><span className="bot-action-order">{index + 1}</span><div><strong>{action.title}</strong><p>{action.detail}</p></div><ArrowUpRight size={18} /></a>)}</div>
      <div className="bot-operation-metrics">{[["Textos para revisar", data.metrics.prepared], ["Envios registrados", data.metrics.sent], ["Leads que responderam", data.metrics.replied], ["Negócios fechados", data.metrics.won], ["Contatos bloqueados", data.metrics.suppressed]].map(([label, value]) => <div key={label}><strong>{value}</strong><span>{label}</span></div>)}</div>
      <p className="bot-measurement">{data.measurement_note} Custo monetário ainda não medido.</p>
    </section>
    <nav className="bot-section-nav" aria-label="Seções da operação"><a href="/operacao">Organizar sessão</a><a href="#bot-review">Revisar contatos</a><a href="#bot-results">Registrar respostas</a><a href="#bot-config">Campanhas</a><a href="#bot-strategy">Gestão e agenda</a><a href="#bot-channels">Canais</a></nav>
    <section id="bot-results" className="bot-panel bot-results"><div className="bot-section-title"><MessageCircle size={22} /><div><h2>Respostas e próximos passos</h2><p>Registro humano. Uma resposta encerra a cadência; pedido de não contato bloqueia também recapturas desse telefone.</p></div></div>
      {data.contacts.length ? <div className="bot-contact-grid">{data.contacts.map(contact => <ContactResult key={`${contact.place_id}-${contact.status}`} contact={contact} refresh={refresh} />)}</div> : <p className="bot-muted">Após um envio registrado, o contato aparecerá aqui para acompanhar a resposta. Nada é enviado por esta seção.</p>}
    </section>
  </>
}
