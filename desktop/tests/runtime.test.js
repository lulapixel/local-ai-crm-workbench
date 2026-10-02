"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events");
const { PassThrough } = require("node:stream");
const http = require("node:http");
const { sameOrigin, externalUrl, startBackend, health } = require("../local/runtime");
const config = { python: "python", backend: "backend", data: "isolated-data" };
function fakeChild() {
  const child = new EventEmitter();
  child.stdout = new PassThrough(); child.stderr = new PassThrough(); child.exitCode = null; child.pid = 123;
  child.kill = () => { child.killed = true; child.exitCode = 0; child.emit("exit", 0); };
  return child;
}
test("origin guards reject lookalikes and external schemes", () => {
  assert.equal(sameOrigin("http://127.0.0.1:5003/operacao", "http://127.0.0.1:5003"), true);
  for (const url of ["http://127.0.0.1:50030", "http://127.0.0.1:5003.evil.test", "https://127.0.0.1:5003", "file:///secret", "javascript:alert(1)"])
    assert.equal(sameOrigin(url, "http://127.0.0.1:5003"), false);
  for (const url of ["file:///secret", "javascript:alert(1)", "https://user:password@example.org", "not a URL"])
    assert.equal(externalUrl(url), null);
  assert.equal(externalUrl("https://wa.me/5511999999999"), "https://wa.me/5511999999999");
});
test("split port announcement requires instance-matched health", async () => {
  const child = fakeChild(); let checks = 0, options;
  const server = startBackend(config, { timeout: 1500, spawnProcess: (_exe, _args, opts) => { options = opts; return child; },
    checkHealth: async (port, instance) => { assert.equal(port, 51234); assert.equal(instance, options.env.PROSPECTOS_DESKTOP_INSTANCE); return ++checks > 1; } });
  child.stdout.write("LISTENING_"); child.stdout.write("ON=51234\r\n");
  const ready = await server.ready;
  assert.equal(ready.origin, "http://127.0.0.1:51234"); assert.equal(checks, 2);
  assert.equal(options.windowsHide, true); assert.equal(options.env.PROSPECTOS_BOT_LIVE_SENDS, "0");
  assert.equal(options.env.PROSPECCAO_DEBUG, "false"); server.stop(); assert.equal(child.killed, true);
});
test("foreign health cannot attach and timeout kills only owned child", async () => {
  const child = fakeChild();
  const server = startBackend(config, { timeout: 450, spawnProcess: () => child, checkHealth: async () => false });
  child.stdout.write("LISTENING_ON=5003\n");
  await assert.rejects(server.ready, /prazo/); assert.equal(child.killed, true);
});
test("startup failure yields recovery message and closes owned child", async () => {
  const child = fakeChild();
  const server = startBackend(config, { spawnProcess: () => child });
  child.emit("error", new Error("private path should not appear"));
  await assert.rejects(server.ready, /Python configurado/); assert.equal(child.killed, true);
});
test("offline smoke overrides inherited test flags and disables automation", async () => {
  const child = fakeChild(); let env;
  const server = startBackend(config, { smoke: true, spawnProcess: (_exe, _args, opts) => { env = opts.env; return child; }, checkHealth: async () => true });
  child.stdout.write("LISTENING_ON=5003\n"); await server.ready;
  assert.equal(env.PROSPECTOS_TEST_DATA_DIR, config.data); assert.equal(env.PROSPECTOS_AUTOMATION_DISABLED, "1"); server.stop();
});
test("unexpected exit is reported, intentional shutdown is not", async () => {
  const child = fakeChild(); let exits = 0;
  const server = startBackend(config, { spawnProcess: () => child, checkHealth: async () => true, onExit: () => exits++ });
  child.stdout.write("LISTENING_ON=5003\n"); await server.ready; server.stop(); assert.equal(exits, 0);
  const other = fakeChild();
  const another = startBackend(config, { spawnProcess: () => other, checkHealth: async () => true, onExit: () => exits++ });
  other.stdout.write("LISTENING_ON=5004\n"); await another.ready; other.exitCode = 1; other.emit("exit", 1); assert.equal(exits, 1);
});
test("real HTTP probe rejects another instance, validates own and handles timeout", async () => {
  const service = http.createServer((_req, res) => { res.setHeader("Content-Type", "application/json"); res.end(JSON.stringify({ ready: true, service: "prospectos", instance: "own" })); });
  await new Promise(resolve => service.listen(0, "127.0.0.1", resolve));
  try { const port = service.address().port; assert.equal(await health(port, "foreign"), false); assert.equal(await health(port, "own"), true); }
  finally { await new Promise(resolve => service.close(resolve)); }
});
