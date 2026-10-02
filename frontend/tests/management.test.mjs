import { test } from "node:test"
import assert from "node:assert/strict"
import { parseMoney, moneyInput, offerPresentation } from "../src/lib/management.ts"

test("currency keeps exact cents and handles empty targets", () => {
  assert.equal(parseMoney("123,45"), 12345)
  assert.equal(parseMoney("0.01"), 1)
  assert.equal(parseMoney("10,1"), 1010)
  assert.equal(parseMoney(""), null)
  assert.equal(parseMoney(moneyInput(100010)), 100010)
})
test("currency rejects ambiguous thousands, extra decimals and invalid magnitudes", () => {
  for (const bad of ["1.500,00", "1e5", "NaN", "Infinity", "-1", "1,234", "0", "1000000.01"]) assert.throws(() => parseMoney(bad))
})
test("unfinished proposal exposes missing terms and remains a proposal", () => {
  const result = offerPresentation({ title: "Synthetic", audience: "", outcome: "", scope: "", price_cents: null, delivery_days: null, demo_url: "" })
  assert.match(result, /\[definir preço\]/)
  assert.match(result, /\[definir prazo\]/)
  assert.match(result, /sujeitos à confirmação/)
})
