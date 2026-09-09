/**
 * Normaliza URLs que vieram de dados do CRM/API antes de chegarem a href ou
 * window.open. Caminhos relativos são opt-in; URLs protocol-relative,
 * credenciais embutidas e esquemas que não sejam HTTP(S) são rejeitados.
 */
export function safeExternalUrl(
  value: unknown,
  options: { allowRelative?: boolean; allowedHosts?: readonly string[] } = {},
): string | undefined {
  if (typeof value !== "string") return undefined
  const raw = value.trim()
  if (!raw || raw.length > 2048) return undefined

  if (raw.startsWith("/") && !raw.startsWith("//")) {
    if (!options.allowRelative) return undefined
    try {
      const relative = new URL(raw, "https://relative.invalid")
      if (relative.origin !== "https://relative.invalid" || relative.username || relative.password) {
        return undefined
      }
      relative.hash = ""
      return `${relative.pathname}${relative.search}`
    } catch {
      return undefined
    }
  }
  if (raw.startsWith("//")) return undefined

  // O CRM historicamente aceitou hostname sem esquema. Trate-o como HTTPS,
  // mas nunca infira um esquema para algo que já carrega um protocolo.
  const candidate = /^[a-z][a-z\d+.-]*:/i.test(raw) ? raw : `https://${raw}`
  try {
    const url = new URL(candidate)
    if (url.protocol !== "http:" && url.protocol !== "https:") return undefined
    if (url.username || url.password || !url.hostname) return undefined
    if (
      options.allowedHosts &&
      !options.allowedHosts.some((host) => url.hostname.toLowerCase() === host.toLowerCase())
    ) {
      return undefined
    }
    url.hash = ""
    return url.toString()
  } catch {
    return undefined
  }
}

const WHATSAPP_HOSTS = ["wa.me", "www.wa.me", "api.whatsapp.com", "web.whatsapp.com"] as const

/** Produz um link de WhatsApp apenas para hosts oficiais. */
export function safeWhatsAppUrl(value: unknown, message?: string | null): string | undefined {
  const normalized = safeExternalUrl(value, { allowedHosts: WHATSAPP_HOSTS })
  if (!normalized) return undefined

  try {
    const url = new URL(normalized)
    if (message) url.searchParams.set("text", message)
    return url.toString()
  } catch {
    return undefined
  }
}

/** Aceita apenas o identificador visual de um perfil Instagram. */
export function safeInstagramProfileUrl(username: unknown): string | undefined {
  if (typeof username !== "string") return undefined
  const clean = username.trim().replace(/^@/, "")
  if (!/^[a-z\d._]{1,30}$/i.test(clean)) return undefined
  return `https://www.instagram.com/${encodeURIComponent(clean)}/`
}
