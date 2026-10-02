import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Copy, ExternalLink } from "lucide-react"
import { httpClient } from "@/services/httpClient"
import "./pilot-review.css"

type Prospect = { id: string; name: string; segment: string; phone: string; evidence: string; hypothesis: string; question: string; draft: string; contact_check: string; source_url: string }
type Pilot = { id: string; title: string; checked_on: string; prospects: Prospect[] }

export function PilotReview() {
  const review = useQuery({ queryKey: ["pilot-review"], queryFn: () => httpClient.get<{ pilots: Pilot[]; unavailable: number }>("/api/workbench/pilots"), staleTime: 30_000 })
  const [feedback, setFeedback] = useState("")
  async function copy(text: string, name: string) {
    try { await navigator.clipboard.writeText(text); setFeedback(`Texto de ${name} copiado. Nenhuma mensagem enviada.`) }
    catch { setFeedback("Não foi possível copiar. Selecione o texto do rascunho e copie manualmente.") }
  }
  return <section className="pilot-review" aria-labelledby="pilot-review-title" id="pilot-review">
    <header className="operation-section-title"><div><p className="operation-eyebrow">PILOTO COMERCIAL</p><h2 id="pilot-review-title">Confira antes de abordar</h2></div><span className="pilot-status">Revisão humana pendente</span></header>
    <p>Confira empresa, contato e rascunho. Copiar o texto não aprova nem envia a abordagem. Os candidatos desta seção ainda não estão na fila do CRM.</p>
    {review.isPending && <p role="status">Carregando material de revisão…</p>}
    {review.isError && <p role="alert">Não foi possível carregar o piloto. <button className="operation-button" onClick={() => void review.refetch()}>Tentar novamente</button></p>}
    {review.data?.unavailable ? <p role="alert">Há material de revisão indisponível. Confira o arquivo local antes de continuar.</p> : null}
    {review.data && !review.data.pilots.length && <p>Nenhum material de revisão preparado para esta instalação.</p>}
    {review.data?.pilots.map(pilot => <div key={pilot.id}><div className="pilot-caption"><h3>{pilot.title}</h3><span>Fontes conferidas em {pilot.checked_on}</span></div>
      <div className="pilot-grid">{pilot.prospects.map(prospect => <article key={prospect.id} className="pilot-prospect">
        <p className="operation-eyebrow">{prospect.segment} · {prospect.id}</p><h3>{prospect.name}</h3><p className="pilot-phone">{prospect.phone}</p>
        <dl><div><dt>Observado na fonte</dt><dd>{prospect.evidence}</dd></div><div><dt>Possibilidade a confirmar</dt><dd>{prospect.hypothesis}</dd></div><div><dt>Contato publicado</dt><dd>{prospect.contact_check} Número ativo e interesse ainda não confirmados.</dd></div></dl>
        <a href={prospect.source_url} target="_blank" rel="noopener noreferrer">Consultar fonte <ExternalLink size={14} aria-hidden="true" /></a>
        <details><summary>Ler abordagem de {prospect.name}</summary><p className="pilot-draft">{prospect.draft}</p><p><strong>Se houver interesse:</strong> {prospect.question}</p><button className="operation-button" onClick={() => void copy(prospect.draft, prospect.name)}><Copy size={15} aria-hidden="true" />Copiar rascunho</button></details>
      </article>)}</div>
    </div>)}
    <p role="status" aria-live="polite" className="pilot-feedback">{feedback}</p>
  </section>
}
