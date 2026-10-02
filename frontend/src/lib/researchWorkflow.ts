import type { Candidate } from "../services/researchService"

export type ResearchForm = Pick<Candidate, "phone" | "contact_verified" | "notes" | "draft" | "question" | "followup_on">
export function formFromCandidate(row: Candidate): ResearchForm {
  return { phone: row.phone, contact_verified: row.contact_verified, notes: row.notes,
    draft: row.draft, question: row.question, followup_on: row.followup_on }
}
export function qualificationIssues(row: Candidate, form: ResearchForm): string[] {
  const issues: string[] = []
  const phone = form.phone.replace(/\D/g, "")
  if (!/^[+0-9 ().-]+$/.test(form.phone) || !/^55\d{10,11}$/.test(phone)) issues.push("Informe um contato brasileiro utilizável.")
  if (!form.contact_verified) issues.push("Confirme que o contato pertence a este negócio.")
  if (!form.notes.trim()) issues.push("Registre as notas de qualificação.")
  // A changed contact is revalidated by the atomic server transaction, never trusted for approval.
  if (phone === row.phone.replace(/\D/g, "")) {
    issues.push(...row.qualification_blockers.filter(issue => /bloqueado|duplicidade|Maps/.test(issue)))
  }
  return issues
}
export function nextCandidate(rows: Candidate[], selectedId: number): Candidate | undefined {
  const start = rows.findIndex(row => row.id === selectedId)
  const ordered = [...rows.slice(start + 1), ...rows.slice(0, Math.max(start, 0))]
  return ordered.find(row => row.next_action.actionable && row.id !== selectedId)
}
