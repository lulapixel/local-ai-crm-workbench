import { useEffect, useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { Check, Copy, ExternalLink, Save } from "lucide-react"
import { moneyInput, offerPresentation, parseMoney } from "@/lib/management"
import { saveManagement, type ManagementDashboard, type ManagementSettings, type Offer } from "@/services/managementService"
import { ApiError } from "@/services/httpClient"

export function ManagementEditor({ data, onSaved }: { data: ManagementDashboard; onSaved: () => void }) {
  const [draft, setDraft] = useState<ManagementSettings>(() => ({ revision: data.revision, profile: data.profile, offer: data.offer }))
  const [baseline, setBaseline] = useState(draft)
  const [price, setPrice] = useState(moneyInput(draft.offer.price_cents))
  const [target, setTarget] = useState(moneyInput(draft.profile.monthly_received_target_cents))
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [copied, setCopied] = useState(false)
  const dirty = JSON.stringify(draft) !== JSON.stringify(baseline) || price !== moneyInput(baseline.offer.price_cents) || target !== moneyInput(baseline.profile.monthly_received_target_cents)
  const stale = data.revision !== baseline.revision
  const updateOffer = (patch: Partial<Offer>) => { setDraft(prev => ({ ...prev, offer: { ...prev.offer, ...patch } })); setNotice(""); setCopied(false) }
  const reset = (next: ManagementSettings) => {
    const value = { revision: next.revision, profile: next.profile, offer: next.offer }
    setDraft(value); setBaseline(value); setPrice(moneyInput(next.offer.price_cents)); setTarget(moneyInput(next.profile.monthly_received_target_cents)); setError("")
  }
  useEffect(() => {
    if (!dirty) return
    const handler = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = "" }
    window.addEventListener("beforeunload", handler)
    return () => window.removeEventListener("beforeunload", handler)
  }, [dirty])
  const mutation = useMutation({ mutationFn: saveManagement, onSuccess: result => {
    reset(result); setNotice("Preferências e oferta salvas. Confira as revisões pendentes antes de apresentar."); onSaved()
  }, onError: err => { if (err instanceof ApiError && err.status === 409) onSaved() } })
  const save = (event: React.FormEvent) => {
    event.preventDefault(); setError(""); setNotice(""); mutation.reset()
    try { mutation.mutate({ ...draft, profile: { ...draft.profile, monthly_received_target_cents: parseMoney(target) }, offer: { ...draft.offer, price_cents: parseMoney(price) } }) }
    catch (err) { setError((err as Error).message) }
  }
  const demoChanged = draft.offer.demo_url !== baseline.offer.demo_url
  const promiseChanged = price !== moneyInput(baseline.offer.price_cents) || (["scope", "outcome", "delivery_days", "audience"] as const).some(key => draft.offer[key] !== baseline.offer[key])
  const presentation = offerPresentation(baseline.offer)
  return <section className="manager-panel" id="oferta" aria-labelledby="offer-title">
    <div className="manager-panel-heading"><div><p className="desk-eyebrow">PREPARAÇÃO COMERCIAL</p><h2 id="offer-title">Uma oferta para colocar à prova.</h2></div><span className="manager-tag">{data.readiness.completed}/{data.readiness.total} revisões</span></div>
    <p className="manager-description">Prepare uma proposta demonstrável. Os campos abaixo organizam sua oferta; não alteram campanhas nem enviam mensagens.</p>
    <ul className="manager-checklist">{data.readiness.checks.map(check => <li key={check.id} className={check.done ? "done" : ""}><span aria-hidden="true">{check.done ? <Check size={12} /> : "·"}</span>{check.label}</li>)}</ul>
    <form onSubmit={save} className="manager-form">
      <details className="manager-preferences"><summary>Meu perfil de operação <span>{data.profile.source === "not_configured" ? "Configurar" : "Local e editável"}</span></summary>
        <p>Você direciona a operação e valida decisões essenciais. Novos gastos, agenda, modelos e permissões continuam nos controles próprios.</p>
        <div className="manager-form-grid">
          <label>Frente prioritária<select value={draft.profile.focus} onChange={e => setDraft({ ...draft, profile: { ...draft.profile, focus: e.target.value as typeof draft.profile.focus } })}><option value="parallel">Serviços e contratos remotos</option><option value="websites">Serviços de websites</option><option value="remote">Contratos remotos</option></select></label>
          <label>Cidade de preferência<input maxLength={100} value={draft.profile.city} onChange={e => setDraft({ ...draft, profile: { ...draft.profile, city: e.target.value } })} /><small>Desempata prioridades; respostas e retornos continuam primeiro.</small></label>
          <label>Referência mensal recebida (R$)<input inputMode="decimal" value={target} onChange={e => setTarget(e.target.value)} placeholder="Ainda não definida" /><small>Objetivo de recebimentos, sem descontar custos.</small></label>
          <label>Explicações<select value={draft.profile.explanation} onChange={e => setDraft({ ...draft, profile: { ...draft.profile, explanation: e.target.value as "brief" | "reasoned" } })}><option value="reasoned">Recomendação com raciocínio</option><option value="brief">Resumo direto</option></select></label>
        </div>
      </details>
      <div className="manager-form-grid">
        <label>Nome da oferta<input value={draft.offer.title} maxLength={120} onChange={e => updateOffer({ title: e.target.value })} /></label>
        <label>Para quem<input value={draft.offer.audience} maxLength={200} onChange={e => updateOffer({ audience: e.target.value })} placeholder="Defina o público que pretende atender" /></label>
        <label className="manager-full">Problema e resultado proposto<textarea rows={2} maxLength={400} value={draft.offer.outcome} onChange={e => updateOffer({ outcome: e.target.value })} placeholder="Qual problema a entrega ajuda a resolver? Evite prometer vendas." /></label>
        <label className="manager-full">O que está incluído e o que depende do cliente<textarea rows={3} maxLength={1200} value={draft.offer.scope} onChange={e => updateOffer({ scope: e.target.value })} placeholder="Páginas, revisões, materiais, manutenção e limites da entrega" /></label>
        <label>Preço proposto (R$)<input inputMode="decimal" value={price} onChange={e => { setPrice(e.target.value); setCopied(false) }} placeholder="Defina após conferir o escopo" /></label>
        <label>Prazo proposto (dias)<input type="number" min={1} max={365} step={1} value={draft.offer.delivery_days ?? ""} onChange={e => updateOffer({ delivery_days: e.target.value === "" ? null : Number(e.target.value) })} /></label>
        <label className="manager-full">Endereço da demonstração<input maxLength={500} value={draft.offer.demo_url} onChange={e => updateOffer({ demo_url: e.target.value, demo_reviewed: false })} placeholder="/demos/… ou https://…" /></label>
      </div>
      <div className="manager-demo"><div><strong>Existe uma demonstração no projeto</strong><p>{data.demo_asset.label}. Disponível para inspeção; adequação comercial ainda depende da sua revisão.</p></div><a className="desk-secondary" href={data.demo_asset.href} target="_blank" rel="noreferrer">Ver exemplo <ExternalLink size={13} /></a><button className="desk-secondary" type="button" onClick={() => updateOffer({ demo_url: data.demo_asset.href, demo_reviewed: false })}>Usar este endereço</button></div>
      {(demoChanged || promiseChanged) && baseline.revision > 0 && <p className="manager-inline-note">Salve as alterações primeiro. Depois confira novamente a demonstração ou a capacidade de entrega que mudou.</p>}
      <label className="manager-checkbox"><input type="checkbox" checked={!demoChanged && draft.offer.demo_reviewed} disabled={!draft.offer.demo_url || (baseline.revision > 0 && demoChanged)} onChange={e => updateOffer({ demo_reviewed: e.target.checked })} />Conferi a demonstração e ela representa esta oferta.</label>
      <label className="manager-checkbox"><input type="checkbox" checked={!promiseChanged && draft.offer.fulfillment_reviewed} disabled={baseline.revision > 0 && promiseChanged} onChange={e => updateOffer({ fulfillment_reviewed: e.target.checked })} />Conferi que consigo entregar o escopo, pelo preço e prazo propostos.</label>
      {(error || mutation.isError) && <p className="manager-error" role="alert">{error || mutation.error?.message}</p>}
      {notice && <p role="status" className="manager-success">{notice}</p>}
      {stale && <p className="manager-inline-note">Há uma versão mais recente. Suas alterações continuam neste formulário. <button type="button" onClick={() => { reset(data); mutation.reset() }}>Descartar minhas alterações e carregar a versão atual</button></p>}
      <div className="manager-save"><span>{dirty ? "Alterações ainda não salvas" : "Usando a versão salva"}</span><button className="desk-primary" type="submit" disabled={mutation.isPending || !dirty}><Save size={14} />{mutation.isPending ? "Salvando…" : "Salvar perfil e oferta"}</button></div>
    </form>
    <details className="manager-presentation"><summary>Apresentação reutilizável da oferta salva</summary><p>Rascunho para revisão. Copiar não envia. Para contratos remotos, acrescente sua contribuição pessoal e o apoio de IA.</p><pre>{presentation}</pre><button className="desk-secondary" onClick={async () => { try { await navigator.clipboard.writeText(presentation); setCopied(true) } catch { setError("Não foi possível copiar. Selecione o texto da apresentação e copie manualmente.") } }}><Copy size={14} />{copied ? "Copiado" : "Copiar rascunho salvo"}</button></details>
  </section>
}
