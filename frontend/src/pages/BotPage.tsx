import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Bot, ArrowRight, Play, Pause, ShieldCheck, Clock3, Check, ExternalLink, SlidersHorizontal, Radar } from "lucide-react"
import { toast } from "sonner"
import { Header } from "@/components/layout/Header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { botService, type BotConfig, type BotMessage, type BotPreview } from "@/services/bot"
import "./bot.css"
import { StrategyBoard } from "@/components/bot/StrategyBoard"
import { DeliveryApproval } from "@/components/bot/DeliveryApproval"
import { DeliveryStatus } from "@/components/bot/DeliveryStatus"

const initial: BotConfig = { nome: "Minha primeira campanha", oferta: "criação de sites para negócios locais", nicho: "", cidade: "", queries: "", limite_dia: 10, score_min: 60, intervalo_horas: 0, captar: false, autorizar_captura: false }
const states: Record<string, string> = { idle: "Pronta", running: "Em execução", paused: "Pausada", interrupted: "Interrompida", error: "Requer atenção", completed: "Concluída" }
const date = (value: string | null) => value ? new Date(value).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "Sem agenda"
const errorText = (error: unknown) => error instanceof Error ? error.message : "Não foi possível concluir esta ação."

function MessageCard({ message, refresh, paused }: { message: BotMessage; refresh: () => void; paused: boolean }) {
  const [text, setText] = useState(message.text)
  const [busy, setBusy] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const dirty = text !== message.text
  const approved = message.state === "approved"
  async function act(action: string) {
    setBusy(true)
    // A janela nasce no clique para evitar bloqueio de pop-up após a resposta da API.
    const target = action === "open" ? window.open("about:blank", "_blank") : null
    if (target) target.opener = null
    try {
      const result = await botService.action(message.id, action, action === "edit" || action === "approve" ? { text } : action === "sent" ? { confirmado: confirmed } : {})
      if (action === "open") {
        if (!result.url || !/^https:\/\/wa\.me\/\d+\?text=/.test(result.url)) throw new Error("Destino de contato inválido.")
        if (!target) throw new Error("Permita abrir a janela do WhatsApp e tente novamente.")
        target.location.href = result.url
      } else {
        toast.success(action === "sent" ? "Envio manual registrado. Próximo retorno agendado, quando aplicável." : action === "approve" ? "Texto e destinatário aprovados." : action === "edit" ? "Texto salvo. Revise antes de aprovar." : "Mensagem rejeitada; próximos retornos cancelados.")
        setConfirmed(false)
      }
      refresh()
    } catch (error) { target?.close(); toast.error(errorText(error)); refresh() }
    finally { setBusy(false) }
  }
  return <article className="bot-message">
    <div className="bot-message-head"><div><span className="bot-kicker">{message.step_order === 0 ? "PRIMEIRO CONTATO" : `RETORNO ${message.step_order} DE 3`}</span><h3>{message.nome}</h3><p>{message.telefone} · campanha #{message.campaign_id}</p></div><span className={`bot-badge ${approved ? "approved" : ""}`}>{approved ? "Aprovada" : "Revisar"}</span></div>
    <p className="bot-reason"><Radar size={14} /> {message.reason}</p>
    <label className="bot-label" htmlFor={`message-${message.id}`}>Mensagem para revisão</label>
    <Textarea id={`message-${message.id}`} value={text} onChange={e => { setText(e.target.value); setConfirmed(false) }} maxLength={2000} rows={4} disabled={busy} />
    <div className="bot-actions">
      {dirty ? <Button size="sm" onClick={() => act("edit")} disabled={busy || !text.trim()}>Salvar alteração</Button> : !approved ? <Button size="sm" onClick={() => act("approve")} disabled={busy || paused}><ShieldCheck size={15} /> Aprovar texto e contato</Button> : <Button size="sm" onClick={() => act("open")} disabled={busy || paused}><ExternalLink size={15} /> Abrir no WhatsApp</Button>}
      <Button size="sm" variant="ghost" onClick={() => act("reject")} disabled={busy}>Rejeitar e encerrar</Button>
      {approved && !dirty && <Button size="sm" variant="ghost" onClick={() => act("edit")} disabled={busy}>Revisar aprovação</Button>}
    </div>
    {approved && !dirty && <div className="bot-confirm"><label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} disabled={busy || paused} /> Eu enviei este texto manualmente para este contato.</label><Button size="sm" variant="outline" disabled={!confirmed || busy || paused} onClick={() => act("sent")}><Check size={15} /> Registrar envio</Button></div>}
    {paused && <p className="bot-muted">Campanha pausada. Execute uma rodada para retomar.</p>}
    {approved && !dirty && !paused && <DeliveryApproval messageId={message.id} refresh={refresh} />}
  </article>
}

export function BotPage() {
  const [config, setConfig] = useState(initial)
  const [preview, setPreview] = useState<BotPreview | null>(null)
  const [busy, setBusy] = useState(false)
  const overview = useQuery({ queryKey: ["bot"], queryFn: botService.overview, refetchInterval: query => query.state.data?.campaigns.some(c => c.state === "running") ? 3000 : 10000 })
  const refresh = () => { void overview.refetch() }
  function update<K extends keyof BotConfig>(key: K, value: BotConfig[K]) { setConfig(c => ({ ...c, [key]: value })); setPreview(null) }
  async function action(fn: () => Promise<unknown>, success?: string) { setBusy(true); try { await fn(); if (success) toast.success(success); refresh() } catch (error) { toast.error(errorText(error)) } finally { setBusy(false) } }
  const data = overview.data
  const queue = data?.messages.filter(m => m.state !== "scheduled") ?? []
  const scheduled = data?.messages.filter(m => m.state === "scheduled") ?? []
  const running = data?.campaigns.some(c => c.state === "running")
  return <div className="min-h-screen bg-background text-foreground"><Header /><main className="bot-page">
    <section className="bot-hero"><div><p className="bot-kicker"><Bot size={18} /> COPILOTO DE PROSPECÇÃO</p><h1>Menos tarefas repetidas.<br /><em>Mais conversas relevantes.</em></h1><p>Seu bot organiza a base, prioriza oportunidades e prepara os próximos contatos. Você decide o que merece ser enviado.</p><span className="bot-hero-note"><ShieldCheck size={16} /> Aprovação individual · envio manual · base local</span></div><div className="bot-orbit" aria-hidden="true"><div><Bot size={48} /><span>VOCÊ NO CONTROLE</span></div></div></section>
    <div className="bot-stats">{[["Para revisar", (data?.counts.pending ?? 0) + (data?.counts.approved ?? 0)], ["Retornos com data", scheduled.length], ["Envios registrados", data?.counts.sent ?? 0], ["IA na preparação local", 0]].map(([label, value]) => <div key={label}><strong>{value}</strong><span>{label}</span></div>)}</div>
    <ol className="bot-flow" aria-label="Etapas do bot">{["Reutilizar a base", "Captar se faltar", "Priorizar", "Preparar", "Você aprova"].map((step, i) => <li key={step}><span>{String(i + 1).padStart(2, "0")}</span>{step}{i < 4 && <ArrowRight size={14} aria-hidden="true" />}</li>)}</ol>
    <StrategyBoard />
    <DeliveryStatus />
    {overview.isError && <div role="alert" className="bot-error">{errorText(overview.error)} <Button variant="outline" size="sm" onClick={refresh}>Tentar novamente</Button></div>}
    <div className="bot-columns"><section className="bot-panel"><div className="bot-section-title"><SlidersHorizontal size={20} /><div><h2>Desenhe sua campanha</h2><p>Comece com um ensaio. Nada será captado ou enviado.</p></div></div>
      <div className="bot-presets"><span>Ponto de partida</span>{[["Sites locais", "criação de sites para negócios locais", ""], ["Estética", "sites e agendamento digital para clínicas", "estética"], ["Serviços", "páginas de apresentação e pedido de orçamento", "serviços"]].map(([label, oferta, nicho]) => <button key={label} onClick={() => { setConfig(c => ({ ...c, oferta, nicho })); setPreview(null) }}>{label}</button>)}</div>
      <form onSubmit={e => { e.preventDefault(); void action(async () => setPreview(await botService.preview(config))) }}>
        <label className="bot-label" htmlFor="campaign-name">Nome da campanha</label><Input id="campaign-name" value={config.nome} maxLength={80} required onChange={e => update("nome", e.target.value)} />
        <label className="bot-label" htmlFor="offer">O que você oferece</label><Input id="offer" value={config.oferta} maxLength={180} required onChange={e => update("oferta", e.target.value)} />
        <div className="bot-fields"><div><label className="bot-label" htmlFor="niche">Nicho (opcional)</label><Input id="niche" value={config.nicho} maxLength={100} placeholder="Todos os nichos" onChange={e => update("nicho", e.target.value)} /></div><div><label className="bot-label" htmlFor="city">Cidade (opcional)</label><Input id="city" value={config.cidade} maxLength={100} placeholder="Todas as cidades" onChange={e => update("cidade", e.target.value)} /></div></div>
        <div className="bot-fields"><div><label className="bot-label" htmlFor="limit">Mensagens por dia / fila</label><Input id="limit" type="number" min={1} max={30} required value={config.limite_dia} onChange={e => update("limite_dia", Number(e.target.value))} /></div><div><label className="bot-label" htmlFor="score">Pontuação mínima</label><Input id="score" type="number" min={0} max={100} required value={config.score_min} onChange={e => update("score_min", Number(e.target.value))} /></div></div>
        <label className="bot-label" htmlFor="schedule">Agenda de preparação</label><select id="schedule" value={config.intervalo_horas} onChange={e => update("intervalo_horas", Number(e.target.value))}><option value={0}>Somente quando eu executar</option><option value={24}>A cada 24 horas</option><option value={168}>A cada 7 dias</option></select><p className="bot-muted">A agenda começa após a primeira rodada e funciona enquanto o backend estiver aberto. O limite diário usa UTC.</p>
        <div className="bot-capture"><label><input type="checkbox" checked={config.captar} onChange={e => { update("captar", e.target.checked); update("autorizar_captura", false) }} /> Captar somente se faltarem leads elegíveis na base</label>{config.captar && <><label className="bot-label" htmlFor="queries">Até 3 consultas, uma por linha</label><Textarea id="queries" value={config.queries} maxLength={360} required rows={3} placeholder="dentistas em Recife" onChange={e => update("queries", e.target.value)} /><p className="bot-muted">Usa a fonte já configurada no projeto, até uma tentativa por dia/campanha. Consultas podem ter custo; o limite de análises não limita o preço da fonte.</p><label><input type="checkbox" required checked={config.autorizar_captura} onChange={e => update("autorizar_captura", e.target.checked)} /> Autorizo a captura externa para esta campanha.</label></>}</div>
        <Button type="submit" variant="outline" disabled={busy || overview.isError}><Radar size={16} /> Ensaiar sem executar</Button>
      </form>
      {preview && <div className="bot-preview"><strong>{preview.na_base} oportunidade(s) elegível(is) na base</strong><p>{preview.captura_planejada ? `Captura planejada se ainda houver falta: até ${preview.consultas_max} consulta(s).` : "A próxima rodada priorizará a base local."}</p>{preview.leads.length > 0 && <ul>{preview.leads.map(l => <li key={l.place_id}>{l.nome}<span>{l.score}/100</span></li>)}</ul>}<p className="bot-muted">{preview.observacao}</p><Button disabled={busy} onClick={() => action(() => botService.create(config), "Campanha criada. Execute a primeira rodada quando estiver pronto.")}>Criar campanha <ArrowRight size={16} /></Button></div>}
    </section><div className="bot-right"><section className="bot-panel"><div className="bot-section-title"><Play size={20} /><div><h2>Operação</h2><p>Preparar, pausar e acompanhar cada rodada.</p></div></div>{overview.isPending ? <p>Carregando campanhas…</p> : !data?.campaigns.length ? <div className="bot-empty"><Bot size={30} /><h3>Seu primeiro fluxo começa aqui</h3><p>Faça o ensaio ao lado e crie uma campanha. Uma rodada gera a fila de revisão.</p></div> : data.campaigns.map(c => <div className="bot-campaign" key={c.id}><div><strong>{c.config.nome}</strong><span className="bot-badge">{states[c.state] ?? c.state}</span></div><p>{c.config.oferta}</p><small>{c.config.limite_dia} mensagens/dia · mínimo {c.config.score_min}/100 · {c.config.captar ? "captura autorizada" : "base local"}</small><p className="bot-muted"><Clock3 size={13} /> Próxima rodada: {date(c.next_run)}</p><div className="bot-actions"><Button size="sm" disabled={busy || running} onClick={() => action(() => botService.run(c.id), "Rodada iniciada. Acompanhe a fila de revisão.")}><Play size={14} /> {c.paused ? "Retomar e executar" : "Executar rodada"}</Button><Button size="sm" variant="outline" disabled={busy || !!c.paused} onClick={() => action(() => botService.pause(c.id), "Pausa solicitada. Uma captura já iniciada termina antes de parar.")}><Pause size={14} /> Pausar</Button></div></div>)}</section>
      <section className="bot-panel"><div className="bot-section-title"><Clock3 size={20} /><div><h2>Diário do bot</h2><p>O que ocorreu, sem confundir plano com resultado.</p></div></div>{!data?.runs.length ? <p className="bot-muted">As rodadas aparecerão aqui.</p> : data.runs.slice(0, 6).map(r => <div className="bot-run" key={r.id}><strong>Rodada #{r.id} · {states[r.state] ?? r.state}</strong><small>{date(r.started_at)} · campanha #{r.campaign_id}</small><p>{r.summary.preparadas ?? 0} novos textos · {r.summary.followups ?? 0} retornos liberados · {r.summary.canceladas ?? 0} cancelados{r.summary.captura ? " · captura tentada" : ""}</p>{r.error && <p role="alert" className="bot-error-text">{r.error}</p>}</div>)}</section></div></div>
    <section className="bot-review"><div className="bot-section-title"><ShieldCheck size={22} /><div><h2>Seu ponto de decisão <span>{queue.length}</span></h2><p>Revise destinatário e texto. Abrir o WhatsApp não envia a mensagem; confirme somente após enviar manualmente.</p></div></div>{queue.length ? <div className="bot-review-grid">{queue.map(m => <MessageCard key={`${m.id}-${m.text}-${m.state}`} message={m} refresh={refresh} paused={!!data?.campaigns.find(c => c.id === m.campaign_id)?.paused} />)}</div> : <div className="bot-empty">Nenhuma mensagem aguardando revisão. Execute uma campanha para preparar sua fila.</div>}</section>
    {!!scheduled.length && <section className="bot-panel bot-future"><h2>Retornos em espera</h2><p className="bot-muted">Somente o próximo retorno fica agendado. Cada um passa por nova aprovação e para quando o status do lead muda para respondido, fechado ou ignorado.</p>{scheduled.map(m => <div key={m.id}><strong>{m.nome}</strong><span>Retorno {m.step_order} · {date(m.due_at)}</span></div>)}</section>}
  </main></div>
}
