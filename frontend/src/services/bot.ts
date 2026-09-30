import { httpClient } from "./httpClient"

export interface BotConfig {
  nome: string; oferta: string; nicho: string; cidade: string; queries: string
  limite_dia: number; score_min: number; intervalo_horas: number
  captar: boolean; autorizar_captura: boolean
}
export interface Campaign { id: number; config: BotConfig; state: string; paused: number; next_run: string | null }
export interface BotMessage {
  id: number; campaign_id: number; place_id: string; nome: string; telefone: string
  text: string; reason: string; score: number; state: string; step_order: number; due_at: string | null
}
export interface BotRun {
  id: number; campaign_id: number; state: string; started_at: string; error: string | null
  summary: { preparadas?: number; followups?: number; canceladas?: number; captura?: boolean }
}
export interface BotOverview { campaigns: Campaign[]; messages: BotMessage[]; runs: BotRun[]; counts: Record<string, number> }
export interface BotPreview { leads: { nome: string; score: number; place_id: string }[]; na_base: number; captura_planejada: boolean; consultas_max: number; limite_analises: number; observacao: string }
export const botService = {
  overview: () => httpClient.get<BotOverview>("/api/bot"),
  preview: (config: BotConfig) => httpClient.post<BotPreview>("/api/bot/preview", config),
  create: (config: BotConfig) => httpClient.post<Campaign>("/api/bot/campaigns", config),
  run: (id: number) => httpClient.post(`/api/bot/campaigns/${id}/run`, {}),
  pause: (id: number) => httpClient.post(`/api/bot/campaigns/${id}/pause`, {}),
  action: (id: number, action: string, body: object = {}) => httpClient.post<{ url?: string }>(`/api/bot/messages/${id}/${action}`, body),
}
