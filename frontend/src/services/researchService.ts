import { httpClient } from "./httpClient"

export type ResearchState = "research" | "qualified" | "approved" | "contacted" | "replied" | "won" | "closed" | "suppressed"
export const RESEARCH_STATES: Record<ResearchState, string> = {
  research: "Em pesquisa", qualified: "Qualificado", approved: "Texto aprovado", contacted: "Contato registrado",
  replied: "Respondeu", won: "Fechamento registrado", closed: "Encerrado", suppressed: "Não contatar",
}
export type ResearchSummary = { total: number; states: Partial<Record<ResearchState, number>>; due: number }
export type Candidate = {
  id: number; name: string; city: string; segment: string; origin: string; external_id: string; state: ResearchState;
  source_url: string; evidence: string; hypothesis: string; researched_on: string; source_fingerprint: string;
  phone: string; contact_verified: boolean; question: string; draft: string; notes: string; followup_on: string;
  revision: number; approval_valid: boolean; blockers: string[]; updated_at: string; sent_at: string | null;
  qualification_ready: boolean; qualification_blockers: string[];
  next_action: { kind: string; label: string; reason: string; priority: number; actionable: boolean };
  events: { action: string; detail: string; created_at: string }[];
}
export type ResearchData = { candidates: Candidate[]; summary: ResearchSummary; limit: number; demo: boolean; pilots: { id: string; title: string; count: number }[] }
export const researchService = {
  list: () => httpClient.get<ResearchData>("/api/research"),
  import: (pilot_id: string) => httpClient.post<{ added: number; existing: number }>("/api/research/import", { pilot_id }),
  update: (row: Candidate, body: Record<string, unknown>) => httpClient.patch<Candidate>(`/api/research/${row.id}`, { revision: row.revision, ...body }),
}
