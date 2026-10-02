import { httpClient } from "./httpClient"
import type { OperationPlan } from "./workbenchService"

export type ManagementProfile = {
  focus: "websites" | "remote" | "parallel"; city: string; monthly_received_target_cents: number | null;
  explanation: "brief" | "reasoned"; source: string; reviewed_on: string | null;
}
export type Offer = {
  title: string; audience: string; outcome: string; scope: string; price_cents: number | null;
  delivery_days: number | null; demo_url: string; demo_reviewed: boolean; fulfillment_reviewed: boolean;
}
export type ManagementSettings = { revision: number; profile: ManagementProfile; offer: Offer }
export type Receipt = { id: string; received_on: string; amount_cents: number; description: string; lane: "websites" | "remote" }
export type ManagementDashboard = ManagementSettings & {
  finance: { month: string; received_cents: number; count: number; target_cents: number | null; remaining_cents: number | null;
    rows: (Receipt & { voided_at: string | null })[]; history_limit: number };
  readiness: { ready: boolean; completed: number; total: number; checks: { id: string; label: string; done: boolean }[] };
  recommendation: { kind: string; title: string; reason: string; alternative: string; href: string; label: string; evidence: string };
  operation: OperationPlan; today: string;
  demo_asset: { href: string; label: string; status: string }; planning_only: boolean; new_spending_authorized: boolean;
}
export const getManagement = (month = "") => httpClient.get<ManagementDashboard>(`/api/management${month ? `?month=${encodeURIComponent(month)}` : ""}`)
export const saveManagement = (data: ManagementSettings) => {
  const { source: _source, reviewed_on: _reviewed, ...profile } = data.profile
  return httpClient.put<ManagementSettings>("/api/management/settings", { ...data, profile })
}
export const recordReceipt = (receipt: Receipt) => httpClient.post("/api/management/receipts", receipt)
export const voidReceipt = (id: string) => httpClient.post(`/api/management/receipts/${encodeURIComponent(id)}/void`)
