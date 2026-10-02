import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { httpClient } from "@/services/httpClient"
import { toast } from "sonner"

interface Preview { channel: string; recipient: string; final_text: string; fingerprint: string; ready: boolean }
export function DeliveryApproval({ messageId, refresh }: { messageId: number; refresh: () => void }) {
  const [channel, setChannel] = useState("email")
  const [recipient, setRecipient] = useState("")
  const [preview, setPreview] = useState<Preview | null>(null)
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  async function run(send: boolean) { setBusy(true); try {
    if (send && preview) { await httpClient.post(`/api/bot/messages/${messageId}/approve-delivery`, { channel, recipient, fingerprint: preview.fingerprint, consent }); setPreview(null); setConsent(false); toast.success("Envio aprovado e colocado em processamento. Consulte o resultado no painel."); refresh() }
    else setPreview(await httpClient.post<Preview>(`/api/bot/messages/${messageId}/delivery-preview`, { channel, recipient }))
  } catch (error) { setPreview(null); setConsent(false); toast.error(error instanceof Error ? error.message : "Falha ao preparar envio.") } finally { setBusy(false) } }
  return <details className="bot-external"><summary>Envio automático após aprovação</summary><p className="bot-muted">Requer uma conta WhatsApp oficial ou Resend configurada localmente. Conectores desativados até a configuração.</p><label className="bot-label" htmlFor={`channel-${messageId}`}>Canal</label><select id={`channel-${messageId}`} value={channel} onChange={e => { setChannel(e.target.value); setPreview(null); setConsent(false) }}><option value="email">E-mail · Resend</option><option value="whatsapp">WhatsApp · API oficial / template aprovado</option></select>{channel === "email" && <><label className="bot-label" htmlFor={`email-${messageId}`}>E-mail verificado do destinatário</label><Input id={`email-${messageId}`} type="email" value={recipient} onChange={e => { setRecipient(e.target.value); setPreview(null); setConsent(false) }} /></>}<Button className="mt-3" variant="outline" size="sm" disabled={busy} onClick={() => run(false)}>Revisar envio final</Button>{preview && <div className="bot-preview"><strong>{preview.channel} · {preview.recipient}</strong><p className="whitespace-pre-wrap">{preview.final_text}</p>{!preview.ready ? <p className="bot-muted">Serviço ainda não ativado. Nenhuma mensagem será enviada.</p> : <><label><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} /> Confirmei a autorização de contato nesse canal e aprovo este texto final para este destinatário.</label><Button size="sm" disabled={!consent || busy} onClick={() => run(true)}>Aprovar e enviar esta mensagem</Button></>}</div>}</details>
}
