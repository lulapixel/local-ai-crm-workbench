import { useCallback, useMemo } from "react"
import { landingPagesService, type EventType } from "@/services/landingPagesService"

export function useTrackEvent(slug?: string, isPreview?: boolean) {
  const sessionId = useMemo(() => {
    if (!slug || typeof window === "undefined") return undefined
    const storageKey = `lp_session_${slug}`
    let sid = sessionStorage.getItem(storageKey)
    if (!sid) {
      sid = typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `sess_${Math.random().toString(36).substring(2)}`
      sessionStorage.setItem(storageKey, sid)
    }
    return sid
  }, [slug])

  const trackEvent = useCallback(
    (eventType: EventType, metadata?: Record<string, string>) => {
      if (!slug || isPreview) return
      landingPagesService
        .registrarEventoPublico(slug, {
          event_type: eventType,
          session_id: sessionId,
          metadata,
        })
        .catch(() => {
          // Silenciosamente ignora falhas de analytics para não interromper navegação
        })
    },
    [slug, isPreview, sessionId]
  )

  return { trackEvent }
}
