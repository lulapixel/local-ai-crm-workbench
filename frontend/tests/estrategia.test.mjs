import { test } from "node:test"
import assert from "node:assert/strict"
import { montarEstrategia } from "../src/lib/estrategia.ts"

const base = { nome: "Synthetic", site_status: "sem_site", nota: 5, num_avaliacoes: 100, follow_ups_enviados: 2 }
test("response takes precedence over previous follow-ups", () => {
  const next = montarEstrategia({ ...base, status: "respondeu" }).proximoPasso
  assert.match(next, /negociação/)
  assert.doesNotMatch(next, /Gere a copy de follow-up/)
})
test("won and refused contacts do not restart prospecting", () => {
  assert.match(montarEstrategia({ ...base, status: "fechou" }).proximoPasso, /pós-venda/)
  for (const status of ["recusou", "ignorado"])
    assert.match(montarEstrategia({ ...base, status }).proximoPasso, /Não iniciar outra abordagem/)
})
test("waiting contact keeps follow-up guidance", () => {
  assert.match(montarEstrategia({ ...base, status: "contatado" }).proximoPasso, /Gere a copy de follow-up/)
})
