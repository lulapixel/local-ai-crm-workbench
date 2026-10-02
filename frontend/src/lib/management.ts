import type { Offer } from "../services/managementService"

export const brl = (cents: number) => new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(cents / 100)

/** Currency input is decimal, not a float calculation. No silently truncated cents. */
export function parseMoney(value: string): number | null {
  if (!value.trim()) return null
  if (!/^\d{1,7}([.,]\d{1,2})?$/.test(value.trim())) throw new Error("Informe o valor sem separador de milhar, com até dois centavos decimais.")
  const [whole, fraction = ""] = value.trim().replace(",", ".").split(".")
  const cents = Number(whole) * 100 + Number(fraction.padEnd(2, "0"))
  if (cents < 1 || cents > 100_000_000) throw new Error("O valor deve ser maior que zero e até R$ 1.000.000.")
  return cents
}
export const moneyInput = (cents: number | null) => cents === null ? "" : (cents / 100).toFixed(2).replace(".", ",")

export function offerPresentation(offer: Offer): string {
  return [offer.title, `Para: ${offer.audience || "[definir público]"}`,
    `Resultado proposto: ${offer.outcome || "[definir resultado]"}`, `Escopo: ${offer.scope || "[definir escopo]"}`,
    `Investimento proposto: ${offer.price_cents === null ? "[definir preço]" : brl(offer.price_cents)}.`,
    `Prazo proposto: ${offer.delivery_days === null ? "[definir prazo]" : `${offer.delivery_days} dias`}, após confirmar escopo e materiais.`,
    `Demonstração: ${offer.demo_url || "[incluir demonstração]"}`,
    "Valores e prazo sujeitos à confirmação. O resultado comercial depende da operação do negócio."].join("\n\n")
}
