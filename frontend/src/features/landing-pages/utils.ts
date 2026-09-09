import { safeWhatsAppUrl } from "@/lib/safeExternalUrl"

export function buildWhatsAppUrl(phone: string, message: string): string | undefined {
  const normalizedPhone = phone.replace(/\D/g, "")
  if (!/^\d{10,15}$/.test(normalizedPhone)) return undefined
  return safeWhatsAppUrl(`https://wa.me/${normalizedPhone}`, message)
}

export function formatCurrency(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value)
}
