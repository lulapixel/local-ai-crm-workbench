import { httpClient } from "@/services/httpClient"
import type { LandingPageData } from "@/features/landing-pages/types"

export type LandingPageStatus = "draft" | "published" | "archived"

export type LandingPageResponse = {
  id: number
  place_id: string
  slug: string
  template_key: string
  status: LandingPageStatus
  schema_version: number
  spec: LandingPageData
  preview_url: string
  public_url: string | null
  public_id?: string | null
  publish_provider?: string | null
  publication_revision?: number
  last_published_at?: string | null
  unpublished_at?: string | null
  publication_configured?: boolean
  created_at: string
  updated_at: string
  published_at?: string | null
  warnings: string[]
}

export type GerarLandingPageOptions = {
  templateKey?: string
  forceRegenerate?: boolean
}

export type LandingPageVersionSummary = {
  id: number
  version: number
  change_type: "initial_generation" | "manual_edit" | "ai_regeneration" | "version_restore"
  sections: string[]
  provider: string
  description: string
  restored_from_version?: number | null
  created_at: string
}

export type LandingPageVersionDetail = LandingPageVersionSummary & {
  landing_page_id: number
  spec: LandingPageData
}

export type RegenerarOptions = {
  sections?: string[]
  tone?: "direct" | "premium" | "welcoming" | "short" | "commercial"
  instruction?: string
}

export type PublicationStatusResponse = {
  id: number
  slug: string
  status: LandingPageStatus
  published: boolean
  public_id?: string | null
  public_url?: string | null
  publish_provider?: string | null
  publication_revision: number
  last_published_at?: string | null
  unpublished_at?: string | null
  publication_configured: boolean
}

export type LandingPageAnalytics = {
  page_views: number
  estimated_sessions: number
  whatsapp_clicks: number
  instagram_clicks: number
  simulator_starts: number
  simulator_completions: number
  service_opens: number
  last_view_at: string | null
}

export type EventType =
  | "page_view"
  | "service_open"
  | "simulator_start"
  | "simulator_complete"
  | "whatsapp_click"
  | "instagram_click"

export type TrackEventPayload = {
  event_type: EventType
  session_id?: string
  metadata?: Record<string, string>
}

export const landingPagesService = {
  obterPorLead: (placeId: string) =>
    httpClient.get<LandingPageResponse>(
      `/api/leads/${encodeURIComponent(placeId)}/landing-page`
    ),

  gerarParaLead: (placeId: string, options?: GerarLandingPageOptions) =>
    httpClient.post<LandingPageResponse>(
      `/api/leads/${encodeURIComponent(placeId)}/landing-page`,
      {
        template_key: options?.templateKey,
        force_regenerate: options?.forceRegenerate ?? false,
      }
    ),

  obterPorSlug: (slug: string) =>
    httpClient.get<LandingPageResponse>(
      `/api/landing-pages/by-slug/${encodeURIComponent(slug)}`
    ),

  obterPublicaPorSlug: (slug: string) =>
    httpClient.get<LandingPageResponse>(
      `/api/public/landing-pages/${encodeURIComponent(slug)}`
    ),

  obterPorId: (id: number) =>
    httpClient.get<LandingPageResponse>(`/api/landing-pages/${id}`),

  atualizarSpec: (
    id: number,
    spec: Partial<LandingPageData>,
    status?: LandingPageStatus
  ) =>
    httpClient.patch<LandingPageResponse>(`/api/landing-pages/${id}`, {
      spec,
      status,
    }),

  alterarStatus: (id: number, status: LandingPageStatus) =>
    httpClient.patch<LandingPageResponse>(`/api/landing-pages/${id}`, {
      status,
    }),

  publicar: (id: number) =>
    httpClient.post<LandingPageResponse>(`/api/landing-pages/${id}/publish`),

  despublicar: (id: number) =>
    httpClient.post<LandingPageResponse>(`/api/landing-pages/${id}/unpublish`),

  republicar: (id: number) =>
    httpClient.post<LandingPageResponse>(`/api/landing-pages/${id}/republish`),

  obterStatusPublicacao: (id: number) =>
    httpClient.get<PublicationStatusResponse>(`/api/landing-pages/${id}/publication-status`),

  obterAnalytics: (id: number) =>
    httpClient.get<LandingPageAnalytics>(`/api/landing-pages/${id}/analytics`),

  registrarEventoPublico: (slug: string, payload: TrackEventPayload) =>
    httpClient.post<{ ok: boolean }>(
      `/api/public/landing-pages/${encodeURIComponent(slug)}/events`,
      payload
    ),

  regenerar: (id: number, options?: RegenerarOptions) =>
    httpClient.post<LandingPageResponse>(`/api/landing-pages/${id}/regenerate`, options),

  obterHistorico: (id: number) =>
    httpClient.get<{ versions: LandingPageVersionSummary[] }>(`/api/landing-pages/${id}/history`),

  obterVersaoHistorico: (id: number, version: number) =>
    httpClient.get<LandingPageVersionDetail>(`/api/landing-pages/${id}/history/${version}`),

  restaurarVersao: (id: number, version: number) =>
    httpClient.post<LandingPageResponse>(`/api/landing-pages/${id}/history/${version}/restore`),

  arquivar: (id: number) =>
    httpClient.post<LandingPageResponse>(`/api/landing-pages/${id}/archive`),
}
