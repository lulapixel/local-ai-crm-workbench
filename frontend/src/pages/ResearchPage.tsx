import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useSearchParams, Link } from "react-router-dom"
import { ArrowUpRight, Check, Clipboard, Download, FileSearch, RefreshCw, Search, ShieldCheck } from "lucide-react"
import { toast } from "sonner"
import { Header } from "@/components/layout/Header"
import { RESEARCH_STATES, researchService } from "@/services/researchService"
import type { Candidate } from "@/services/researchService"
import { ApiError } from "@/services/httpClient"
import { formFromCandidate, nextCandidate, qualificationIssues } from "@/lib/researchWorkflow"
import "./workspace.css"

const eventNames: Record<string, string> = { imported: "Pesquisa incorporada", edit: "Informações atualizadas", qualify: "Qualificação registrada", approve: "Texto e contato aprovados", sent: "Envio manual declarado", reply: "Resposta registrada", win: "Fechamento registrado", close: "Acompanhamento encerrado", suppress: "Contato bloqueado" }

function CandidateDetail({ row, save, pending, setDirty, conflict }: { row: Candidate; save: (body: Record<string, unknown>) => void; pending: boolean; setDirty: (v: boolean) => void; conflict: boolean }) {
  const [form, setForm] = useState(() => formFromCandidate(row))
  const [reviewed, setReviewed] = useState(false)
  const [sent, setSent] = useState(false)
  const [copied, setCopied] = useState(false)
  const dirty = JSON.stringify(form) !== JSON.stringify(formFromCandidate(row))
  const qualification = qualificationIssues(row, form)
  const currentStage = row.state === "research" ? 0 : row.state === "qualified" ? 1 : 2
  const terminal = ["won", "closed", "suppressed"].includes(row.state)
  function edit(key: keyof typeof form, value: string | boolean) {
    const next = { ...form, [key]: value }
    if (key === "phone" && value !== form.phone) next.contact_verified = false
    setForm(next)
    setDirty(JSON.stringify(next) !== JSON.stringify(formFromCandidate(row)))
  }
  function action(action: string) { save({ action, human_confirmed: true }) }
  return <section className="desk-detail" aria-label={`Acompanhamento de ${row.name}`}>
    <div className="desk-detail-head"><div><span className={`desk-badge state-${row.state}`}>{RESEARCH_STATES[row.state]}</span><h2>{row.name}</h2><p>{row.city} · {row.segment} · {row.external_id}</p></div><span className="desk-monogram" aria-hidden="true">{row.name.slice(0, 2).toUpperCase()}</span></div>
    <ol className="desk-workflow" aria-label="Etapas do acompanhamento">{["Qualificar", "Preparar e revisar", "Acompanhar"].map((label, index) => <li key={label} aria-current={index === currentStage ? "step" : undefined} className={index <= currentStage ? "reached" : ""}><span>{index + 1}</span>{label}</li>)}</ol>
    <div className="desk-next-action"><span className="desk-section-label">PRÓXIMO TRABALHO</span><strong>{row.next_action.label}</strong><p>{row.next_action.reason}</p></div>
    <div className="desk-evidence"><div className="desk-section-label"><FileSearch size={16} /> Evidência pública · registro original <span>{row.researched_on}</span></div><p>{row.evidence}</p><a href={row.source_url} target="_blank" rel="noopener noreferrer">Consultar fonte <ArrowUpRight size={14} /></a><div className="desk-hypothesis"><strong>O que ainda precisa ser confirmado</strong><p>{row.hypothesis}</p></div></div>
    <form onSubmit={event => { event.preventDefault(); save({ action: "edit", ...form }) }} className="desk-form">
      <div className="desk-section-label">01 / Qualificação</div>
      <div className="desk-form-row"><label>Contato publicado<input disabled={terminal || pending} value={form.phone} maxLength={40} placeholder="+55 DDD número" onChange={e => edit("phone", e.target.value)} /></label><label>Próximo retorno<input disabled={terminal || pending} type="date" value={form.followup_on} onInput={e => edit("followup_on", e.currentTarget.value)} onChange={e => edit("followup_on", e.target.value)} /></label></div>
      <label className="desk-check"><input type="checkbox" disabled={terminal || pending} checked={form.contact_verified} onChange={e => edit("contact_verified", e.target.checked)} /><span>Conferi que o contato pertence a este negócio.</span></label>
      <label>Notas de qualificação<textarea disabled={terminal || pending} rows={3} maxLength={4000} value={form.notes} placeholder="Como o negócio trabalha hoje? Qual necessidade foi realmente observada? Quem decide?" onChange={e => edit("notes", e.target.value)} /></label>
      <label>Pergunta de descoberta<input disabled={terminal || pending} maxLength={4000} value={form.question} onChange={e => edit("question", e.target.value)} /></label>
      {row.state === "research" && <div className="desk-qualification"><p>Qualificação registra contato e necessidade conferidos. O rascunho será preparado na próxima etapa.</p>{qualification.length > 0 ? <ul>{qualification.map(issue => <li key={issue}>{issue}</li>)}</ul> : <p role="status">Contato e notas preenchidos. Bloqueios e duplicidades serão conferidos ao salvar.</p>}<button className="desk-primary" disabled={pending || !!qualification.length} type="button" onClick={() => save({ action: "qualify", human_confirmed: true, ...form })}>Salvar e qualificar</button></div>}
      <details className="desk-draft" open={row.state !== "research" || !!form.draft}><summary>02 / Preparar o texto para revisão {row.state === "research" && !form.draft ? "· depois de qualificar" : ""}</summary>
        <label>Texto para revisão<textarea disabled={terminal || pending} rows={5} maxLength={4000} value={form.draft} onChange={e => { edit("draft", e.target.value); setCopied(false) }} /></label>
        <button className="desk-secondary" disabled={!form.draft || pending} type="button" onClick={async () => { try { await navigator.clipboard.writeText(form.draft); setCopied(true) } catch { toast.error("Não foi possível copiar. Selecione o texto no campo.") } }}>{copied ? <Check size={15} /> : <Clipboard size={15} />}{copied ? "Texto copiado" : "Copiar rascunho"}</button>
      </details>
      <div className="desk-form-actions"><button className="desk-secondary" disabled={!dirty || pending || terminal} type="submit">{pending ? "Salvando…" : "Salvar alterações"}</button></div>
      <p className="desk-caption" role="status">{dirty ? "Há alterações locais. Salve antes de avançar a etapa." : "Registro salvo localmente."} Copiar um rascunho não aprova nem registra envio.</p>
      {conflict && <p className="desk-notice" role="alert">O registro mudou em outra janela. Seu texto local foi preservado. Revise ou copie suas alterações antes de usar Atualizar, que pedirá confirmação para descartá-las.</p>}
    </form>
    {!terminal && <div className="desk-stage-actions"><div className="desk-section-label"><ShieldCheck size={16} /> 03 / Sua decisão</div>
      {row.state !== "research" && row.blockers.length > 0 && <ul className="desk-blockers">{row.blockers.map(issue => <li key={issue}>{issue}</li>)}</ul>}
      {row.state === "research" && <p>Primeiro conclua a qualificação acima. Preparar e aprovar uma mensagem são decisões posteriores.</p>}
      {row.state === "qualified" && <><label className="desk-check"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} /><span>Revisei o texto e o contato exibidos; aprovo esta versão.</span></label><button className="desk-primary" disabled={pending || dirty || !reviewed || !!row.blockers.length} onClick={() => action("approve")}>Aprovar esta versão</button></>}
      {row.state === "approved" && <><p>Esta aprovação não envia mensagens. Faça o contato manualmente pelo seu canal e só depois registre abaixo.</p><label className="desk-check"><input type="checkbox" checked={sent} onChange={e => setSent(e.target.checked)} /><span>Enviei manualmente este texto para este contato.</span></label><button className="desk-primary" disabled={pending || dirty || !sent || !row.approval_valid} onClick={() => action("sent")}>Registrar envio manual realizado</button></>}
      {row.state === "contacted" && <button className="desk-primary" disabled={pending || dirty} onClick={() => action("reply")}>Registrar resposta recebida</button>}
      {row.state === "replied" && <button className="desk-primary" disabled={pending || dirty} onClick={() => action("win")}>Registrar fechamento informado</button>}
      <div className="desk-end-actions"><button disabled={pending || dirty} onClick={() => { if (window.confirm(`Encerrar o acompanhamento de ${row.name}?`)) action("close") }}>Encerrar acompanhamento</button><button disabled={pending || dirty} onClick={() => { if (window.confirm(`Bloquear ${row.name} e este telefone para futuras abordagens?`)) action("suppress") }}>Não contatar</button></div>
    </div>}
    <details className="desk-history"><summary>Histórico · {row.events.length} registros recentes</summary><ol>{row.events.map((event, index) => <li key={`${event.created_at}-${index}`}><strong>{eventNames[event.action] ?? event.action}</strong><time>{new Date(event.created_at).toLocaleString("pt-BR")}</time>{["approve", "sent"].includes(event.action) && <details><summary>Texto e contato desta versão</summary><pre>{event.detail}</pre></details>}</li>)}</ol><small>Origem: {row.origin} · revisão {row.revision}. Fonte preservada na importação.</small></details>
  </section>
}

export function ResearchPage() {
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState("")
  const [state, setState] = useState("all")
  const [segment, setSegment] = useState("all")
  const [actionableOnly, setActionableOnly] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [detailReset, setDetailReset] = useState(0)
  useEffect(() => {
    if (!dirty) return
    const leaving = (event: BeforeUnloadEvent) => { event.preventDefault() }
    const navigating = (event: MouseEvent) => {
      const anchor = event.target instanceof Element ? event.target.closest("a") : null
      if (anchor && !anchor.hasAttribute("download") && anchor.target !== "_blank" && !window.confirm("Descartar alterações ainda não salvas para sair da pesquisa?")) { event.preventDefault(); event.stopPropagation() }
    }
    window.addEventListener("beforeunload", leaving)
    document.addEventListener("click", navigating, true)
    return () => { window.removeEventListener("beforeunload", leaving); document.removeEventListener("click", navigating, true) }
  }, [dirty])
  const client = useQueryClient()
  const query = useQuery({ queryKey: ["research"], queryFn: researchService.list, refetchOnWindowFocus: false })
  const mutation = useMutation({ mutationFn: ({ row, body }: { row: Candidate; body: Record<string, unknown> }) => researchService.update(row, body), onSuccess: async () => { setDirty(false); await Promise.all([client.invalidateQueries({ queryKey: ["research"] }), client.invalidateQueries({ queryKey: ["operation-plan"] }), client.invalidateQueries({ queryKey: ["bot-operations"] })]); toast.success("Registro atualizado") }, onError: error => toast.error(error.message) })
  const importing = useMutation({ mutationFn: researchService.import, onSuccess: async data => { await Promise.all([client.invalidateQueries({ queryKey: ["research"] }), client.invalidateQueries({ queryKey: ["operation-plan"] }), client.invalidateQueries({ queryKey: ["bot-operations"] })]); toast.success(`${data.added} incorporados · ${data.existing} já existentes`) }, onError: error => toast.error(error.message) })
  const data = query.data
  const refresh = () => { if (dirty && !window.confirm("Descartar as alterações locais e carregar o registro salvo?")) return; setDirty(false); setDetailReset(value => value + 1); mutation.reset(); void query.refetch() }
  const rows = (data?.candidates ?? []).filter(row => (!actionableOnly || row.next_action.actionable) && (state === "all" || row.state === state) && (segment === "all" || row.segment === segment) && `${row.name} ${row.city} ${row.segment}`.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().includes(search.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase()))
  const selected = rows.find(row => String(row.id) === params.get("candidate")) ?? rows[0]
  const choose = (row: Candidate) => { if (dirty && !window.confirm("Descartar alterações ainda não salvas para abrir outro candidato?")) return; setDirty(false); setDetailReset(value => value + 1); mutation.reset(); setParams({ candidate: String(row.id) }) }
  const next = selected ? nextCandidate(rows, selected.id) : undefined
  return <><Header /><main className="desk-page"><div className="desk-page-heading"><div><p className="desk-eyebrow">PESQUISA / RELACIONAMENTO</p><h1>Uma conversa começa<br /><em>com contexto.</em></h1><p>Evidências, decisões e retornos em uma mesa de trabalho.</p></div><div className="desk-heading-actions"><button className="desk-secondary" disabled={query.isFetching} onClick={refresh} aria-label="Atualizar pesquisa"><RefreshCw size={16} /> Atualizar</button><a className="desk-secondary" href="/api/research/export" download><Download size={16} /> Exportar JSON</a></div></div>
    {data?.demo && <p className="desk-notice" role="status">Ambiente de teste isolado. Dados e resultados fictícios; automação desativada.</p>}
    {query.isPending && <p role="status">Carregando sua pesquisa…</p>}{query.isError && <div className="desk-notice" role="alert">{query.error.message} <button onClick={() => void query.refetch()}>Tentar novamente</button></div>}
    {data && <><div className="desk-metrics"><div><span>Candidatos pesquisados</span><strong>{data.summary.total}</strong><small>Proveniência separada do Maps e Instagram</small></div><div><span>Textos aprovados</span><strong>{data.summary.states.approved ?? 0}</strong><small>Aprovação individual, sem transmissão</small></div><div><span>Respostas registradas</span><strong>{data.summary.states.replied ?? 0}</strong><small>Informadas pelo operador</small></div><div><span>Retornos vencidos</span><strong>{data.summary.due}</strong><small>Agendados por você</small></div></div>
      {data.pilots.length > 0 && <details className="desk-import"><summary>Incorporar pesquisa local existente</summary><p>Incorpora candidatos como pesquisa. Mantém fontes e não qualifica, aprova ou envia automaticamente. Repetir preserva edições.</p>{data.pilots.map(pilot => <div key={pilot.id}><span>{pilot.title} · {pilot.count} candidatos</span><button className="desk-secondary" disabled={importing.isPending || dirty} onClick={() => importing.mutate(pilot.id)}>{importing.isPending ? "Incorporando…" : "Incorporar candidatos"}</button></div>)}</details>}
      <div className="desk-toolbar"><label className="desk-search"><Search size={17} /><input disabled={dirty} aria-label="Buscar candidato" placeholder="Buscar negócio, cidade ou segmento" value={search} onChange={e => setSearch(e.target.value)} /></label><select disabled={dirty} aria-label="Filtrar etapa" value={state} onChange={e => setState(e.target.value)}><option value="all">Todas as etapas</option>{Object.entries(RESEARCH_STATES).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select><select disabled={dirty} aria-label="Filtrar segmento" value={segment} onChange={e => setSegment(e.target.value)}><option value="all">Todos os segmentos</option>{[...new Set(data.candidates.map(row => row.segment))].map(value => <option key={value}>{value}</option>)}</select><span>{rows.length} de {data.summary.total}{data.summary.total > data.limit ? ` · primeiros ${data.limit}` : ""}</span></div>
      <div className="desk-queue-controls"><label className="desk-check"><input type="checkbox" disabled={dirty} checked={actionableOnly} onChange={e => setActionableOnly(e.target.checked)} /><span>Somente candidatos com trabalho disponível</span></label><button className="desk-secondary" disabled={!next || mutation.isPending} onClick={() => { if (next) choose(next) }}>Próximo candidato</button><small>Ordem por etapa e retorno agendado; não representa chance de venda.</small></div>
      <div className="desk-workspace"><section className="desk-list" aria-label="Candidatos"><div className="desk-list-label">NEGÓCIO / PRÓXIMO TRABALHO</div>{rows.map(row => <button key={row.id} aria-pressed={selected?.id === row.id} className={`desk-candidate ${selected?.id === row.id ? "selected" : ""}`} onClick={() => choose(row)}><span className="desk-candidate-icon">{row.name.slice(0, 1)}</span><span><strong>{row.name}</strong><small>{row.segment} · {row.city}</small><span className={`desk-badge state-${row.state}`}>{RESEARCH_STATES[row.state]}</span><small>{row.next_action.label}</small></span><ArrowUpRight size={15} /></button>)}{!rows.length && <div className="desk-empty"><FileSearch size={26} /><h2>{data.summary.total ? "Nenhum resultado neste filtro" : "Sua pesquisa pode virar trabalho"}</h2><p>{data.summary.total ? "Ajuste os filtros para recuperar os candidatos." : "Incorpore o piloto local acima. Nenhum contato será enviado."}</p><Link to="/operacao">Organizar sessão <ArrowUpRight size={14} /></Link></div>}</section>
      {selected ? <CandidateDetail key={`${selected.id}-${selected.revision}-${detailReset}`} row={selected} pending={mutation.isPending} setDirty={setDirty} conflict={mutation.error instanceof ApiError && mutation.error.status === 409} save={body => mutation.mutate({ row: selected, body })} /> : <div className="desk-placeholder"><ShieldCheck size={32} /><h2>Primeiro evidência. Depois decisão.</h2><p>Selecione um candidato para conferir a fonte, registrar a necessidade e revisar a abordagem.</p></div>}</div>
      <p className="desk-caption">Qualificação e envio são registros humanos. Número publicado não comprova permissão ou disponibilidade. Fechamento informado não é receita verificada. Nenhuma chamada de IA ou transmissão nesta mesa.</p></>}
  </main></>
}
