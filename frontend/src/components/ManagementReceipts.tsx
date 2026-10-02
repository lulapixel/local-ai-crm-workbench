import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { brl, parseMoney } from "@/lib/management"
import { recordReceipt, voidReceipt, type ManagementDashboard, type Receipt } from "@/services/managementService"

export function ManagementReceipts({ data, month, onMonth, onSaved }: { data: ManagementDashboard; month: string; onMonth: (value: string) => void; onSaved: () => void }) {
  const [amount, setAmount] = useState("")
  const [description, setDescription] = useState("")
  const [receivedOn, setReceivedOn] = useState(data.today)
  const [lane, setLane] = useState<Receipt["lane"]>("websites")
  const [error, setError] = useState("")
  const [confirmVoid, setConfirmVoid] = useState<string | null>(null)
  const [pendingReceipt, setPendingReceipt] = useState<Receipt | null>(null)
  const [notice, setNotice] = useState("")
  const add = useMutation({ mutationFn: recordReceipt, onSuccess: () => {
    const savedMonth = pendingReceipt?.received_on.slice(0, 7)
    setPendingReceipt(null); setAmount(""); setDescription(""); setNotice("Recebimento registrado localmente.")
    if (savedMonth) onMonth(savedMonth)
    onSaved()
  } })
  const cancel = useMutation({ mutationFn: voidReceipt, onSuccess: () => { setConfirmVoid(null); setNotice("Registro anulado; o histórico foi preservado. Nenhum dinheiro foi movimentado."); onSaved() } })
  const submit = (event: React.FormEvent) => {
    event.preventDefault(); setError(""); setNotice(""); add.reset()
    try {
      const cents = parseMoney(amount)
      if (cents === null) throw new Error("Informe o valor efetivamente recebido.")
      const receipt = { id: crypto.randomUUID(), received_on: receivedOn, amount_cents: cents, description: description.trim(), lane }
      setPendingReceipt(receipt); add.mutate(receipt)
    } catch (err) { setError((err as Error).message) }
  }
  const finance = data.finance
  return <section className="manager-panel" id="recebimentos" aria-labelledby="receipts-title"><div className="manager-panel-heading"><div><p className="desk-eyebrow">RESULTADO FINANCEIRO</p><h2 id="receipts-title">Dinheiro recebido.</h2></div><label className="manager-month">Mês<input type="month" value={month || finance.month} onChange={e => { if (e.target.value) onMonth(e.target.value) }} /></label></div>
    <p className="manager-description">Registre pagamentos que já recebeu. Propostas e negócios marcados como fechados não entram automaticamente aqui.</p>
    <div className="manager-cash"><strong>{brl(finance.received_cents)}</strong><span>{finance.count} recebimento(s) registrado(s) neste mês<br />{finance.target_cents !== null ? `Referência: ${brl(finance.target_cents)} · faltam ${brl(finance.remaining_cents ?? 0)}` : "Referência mensal ainda não definida"}</span></div>
    {finance.target_cents !== null && <progress aria-label="Recebimentos registrados em relação à referência mensal" value={Math.min(finance.received_cents, finance.target_cents)} max={finance.target_cents} />}
    <p className="desk-caption">Valores declarados por você, sem conciliação bancária ou dedução de custos. Ausência de registros não comprova ausência de receita.</p>
    <details className="manager-receipt-form"><summary>Registrar um recebimento</summary><form onSubmit={submit} className="manager-form"><fieldset disabled={add.isPending || !!pendingReceipt}><div className="manager-form-grid"><label>Valor recebido (R$)<input required inputMode="decimal" value={amount} onChange={e => setAmount(e.target.value)} /></label><label>Data do recebimento<input required type="date" min="2000-01-01" max={data.today} value={receivedOn} onChange={e => setReceivedOn(e.target.value)} /></label><label>Frente<select value={lane} onChange={e => setLane(e.target.value as Receipt["lane"])}><option value="websites">Serviços de websites</option><option value="remote">Contratos remotos</option></select></label><label>Descrição curta<input required maxLength={120} value={description} onChange={e => setDescription(e.target.value)} placeholder="Ex.: sinal do projeto; evite dados pessoais" /></label></div></fieldset>
      <button type="submit" className="desk-primary" disabled={add.isPending || !!pendingReceipt}>{add.isPending ? "Registrando…" : "Registrar valor recebido"}</button></form>
      {add.isError && pendingReceipt && <div role="alert" className="manager-error"><p>{add.error.message}</p><p>Para evitar duplicidade, repita o mesmo registro ou confira o histórico antes de editar.</p><button className="desk-secondary" onClick={() => add.mutate(pendingReceipt)}>Repetir com o mesmo identificador</button> <button className="desk-secondary" onClick={() => { setPendingReceipt(null); add.reset(); onSaved() }}>Conferir histórico e liberar formulário</button></div>}
    </details>
    {(error || cancel.isError) && <p className="manager-error" role="alert">{error || cancel.error?.message}</p>}{notice && <p role="status" className="manager-success">{notice}</p>}
    <ul className="manager-receipts">{finance.rows.map(row => <li key={row.id}><div><strong>{row.description}</strong><small>{row.received_on.split("-").reverse().join("/")} · {row.lane === "websites" ? "Websites" : "Contratos remotos"}</small></div><strong>{brl(row.amount_cents)}</strong>{row.voided_at ? <span className="manager-tag">Anulado</span> : confirmVoid === row.id ? <div className="manager-void"><span>Anular só este registro?</span><button disabled={cancel.isPending} onClick={() => cancel.mutate(row.id)}>Confirmar</button><button disabled={cancel.isPending} onClick={() => setConfirmVoid(null)}>Manter</button></div> : <button onClick={() => setConfirmVoid(row.id)} aria-label={`Anular registro ${row.description}`}>Anular</button>}</li>)}</ul>
    {!finance.rows.length && <p className="manager-empty">Nenhum recebimento registrado neste mês. Quando houver pagamento, você poderá acompanhar aqui.</p>}
    <p className="desk-caption">Últimos {finance.history_limit} registros do mês; o total inclui todos os registros válidos. Anular corrige o controle local, sem estornar pagamentos.</p>
  </section>
}
