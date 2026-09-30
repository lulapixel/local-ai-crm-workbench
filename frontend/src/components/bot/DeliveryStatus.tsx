import { useQuery } from "@tanstack/react-query"
import { httpClient } from "@/services/httpClient"
interface Data { email: boolean; whatsapp: boolean; live_enabled: boolean; deliveries: { id: number; channel: string; recipient: string; state: string; error: string | null }[] }
const labels: Record<string,string> = { queued: "Na fila", sending: "Em processamento", blocked: "Bloqueado", unknown: "Resultado incerto; conferir provedor", provider_accepted: "Aceito pelo provedor; entrega não confirmada" }
export function DeliveryStatus() {
  const { data, isError } = useQuery({ queryKey: ["bot-delivery"], queryFn: () => httpClient.get<Data>("/api/bot/delivery"), refetchInterval: 10000 })
  return <section id="bot-channels" className="bot-panel bot-management"><h2>Canais e resultados de envio</h2>{isError ? <p role="alert" className="bot-error-text">Não foi possível consultar os canais de envio.</p> : <p className="bot-muted">E-mail: {data?.email ? "configurado" : "aguardando conta"} · WhatsApp oficial: {data?.whatsapp ? "configurado" : "aguardando conta/template"} · Envios automáticos: {data?.live_enabled ? "habilitados" : "desativados"}</p>}<p className="bot-muted">O WhatsApp manual continua disponível. Os conectores só transmitem uma mensagem após revisão e aprovação específicas.</p>{data?.deliveries.map(d => <div className="bot-run" key={d.id}><strong>{d.channel} · {d.recipient}</strong><span>{labels[d.state] ?? d.state}</span>{d.error && <p role="alert" className="bot-error-text">{d.error}</p>}</div>)}</section>
}
