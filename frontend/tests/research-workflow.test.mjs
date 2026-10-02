import { test } from "node:test"
import assert from "node:assert/strict"
import { formFromCandidate, nextCandidate, qualificationIssues } from "../src/lib/researchWorkflow.ts"

const base = { id: 1, phone: "+5581999999999", contact_verified: true, notes: "Fixture evidence",
  draft: "", question: "Discovery", followup_on: "", qualification_blockers: [],
  next_action: { actionable: true } }
test("qualification is independent from message preparation", () => {
  assert.deepEqual(qualificationIssues(base, formFromCandidate(base)), [])
  assert.match(qualificationIssues(base, { ...formFromCandidate(base), notes: " " }).join(" "), /notas/)
  assert.match(qualificationIssues(base, { ...formFromCandidate(base), contact_verified: false }).join(" "), /Confirme/)
})
test("shared and suppressed saved contacts cannot be qualified in the local preview", () => {
  const shared = { ...base, qualification_blockers: ["Número compartilhado; resolva a duplicidade."] }
  assert.equal(qualificationIssues(shared, { ...formFromCandidate(shared), phone: "+55 (81) 99999-9999" }).length, 1)
  assert.equal(qualificationIssues(shared, { ...formFromCandidate(shared), phone: "+5581999999998" }).length, 0)
  assert.match(qualificationIssues(base, { ...formFromCandidate(base), phone: "invalid" }).join(" "), /utilizável/)
})
test("next candidate wraps through current filtered rows and skips inactive work", () => {
  const rows = [base, { ...base, id: 2, next_action: { actionable: false } }, { ...base, id: 3 }]
  assert.equal(nextCandidate(rows, 1).id, 3)
  assert.equal(nextCandidate(rows, 3).id, 1)
  assert.equal(nextCandidate([base], 1), undefined)
  assert.equal(nextCandidate([], 9), undefined)
})
