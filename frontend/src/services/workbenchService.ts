import { httpClient } from "./httpClient"
import type { ResearchSummary } from "./researchService"
export type SessionAction = { id: string; kind: string; name: string; city: string; niche: string; reason: string; score: number; estimated_minutes: number; href: string; department: string; human_decision: string; learning: string }
export type OperationPlan = {
  generated_at: string; minutes: number; estimated_minutes: number; actions: SessionAction[]; available_actions: number; unselected_actions: number;
  quality: Record<string, number>; scanned: number; scan_limit: number; limited: boolean; total_leads: number; instagram_leads: number;
  commercial: { conversations: number; waiting: number; won: number }; research: ResearchSummary;
  strategy: { enabled: boolean; hour: string; daily_limit: number; used_today: number; codex_available: boolean; useful_campaigns: number; active_campaigns: number };
  channels: { email: boolean; whatsapp: boolean; live_enabled: boolean }; demo: boolean; note: string;
}
export function getOperationPlan(minutes = 30, filters = { city: "", niche: "", minimum: "60" }) {
  return httpClient.get<OperationPlan>(`/api/workbench/plan?${new URLSearchParams({ minutes: String(minutes), ...filters })}`)
}
