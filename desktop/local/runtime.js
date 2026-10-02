"use strict";
const http = require("node:http");
const { spawn } = require("node:child_process");
const { randomUUID } = require("node:crypto");
const path = require("node:path");

function sameOrigin(url, origin) {
  try { return new URL(url).origin === origin && new URL(url).protocol === "http:"; }
  catch { return false; }
}
function externalUrl(value) {
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}
function health(port, instance) {
  return new Promise((resolve, reject) => {
    const req = http.get({ hostname: "127.0.0.1", port, path: "/api/system/health", timeout: 1500 }, res => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", chunk => { body += chunk; if (body.length > 8192) res.destroy(); });
      res.on("error", reject);
      res.on("end", () => {
        try { const data = JSON.parse(body); resolve(res.statusCode === 200 && data.ready === true && data.service === "prospectos" && data.instance === instance); }
        catch { resolve(false); }
      });
    });
    req.on("timeout", () => req.destroy(new Error("health timeout")));
    req.on("error", reject);
  });
}

function startBackend(config, { smoke = false, timeout = 60000, onExit = () => {}, spawnProcess = spawn, checkHealth = health } = {}) {
  const instance = randomUUID();
  const env = { ...process.env, PYTHONUNBUFFERED: "1", PROSPECCAO_DEBUG: "false", PROSPECTOS_NO_BROWSER: "1",
    PROSPECTOS_PORT: "5003", PROSPECTOS_LOCAL_DESKTOP: "1", PROSPECTOS_LOCAL_DATA_DIR: config.data,
    PROSPECTOS_DESKTOP_INSTANCE: instance };
  // Ignore test/provider enablement left over in the launching terminal.
  delete env.PROSPECTOS_TEST_MODE;
  delete env.PROSPECTOS_TEST_DATA_DIR;
  delete env.PROSPECTOS_AUTOMATION_DISABLED;
  env.PROSPECTOS_BOT_LIVE_SENDS = "0";
  if (smoke) {
    env.PROSPECTOS_AUTOMATION_DISABLED = "1";
    env.PROSPECTOS_TEST_MODE = "1";
    env.PROSPECTOS_TEST_DATA_DIR = config.data;
  }
  const child = spawnProcess(config.python, [path.join(config.backend, "app.py")], { cwd: config.backend, env,
    windowsHide: true, stdio: ["ignore", "pipe", "pipe"] });
  let intentional = false;
  let finished = false;
  const stop = () => { intentional = true; if (child.exitCode === null && !child.killed) child.kill(); };
  const ready = new Promise((resolve, reject) => {
    let buffer = "", port = null, checking = false;
    const settle = (error) => {
      if (finished) return;
      finished = true;
      clearTimeout(deadline); clearInterval(poll);
      child.stdout.removeListener("data", readPort);
      if (error) { stop(); reject(error); }
      else resolve({ port, origin: `http://127.0.0.1:${port}`, instance, pid: child.pid });
    };
    const readPort = chunk => {
      buffer = (buffer + String(chunk)).slice(-4096);
      const found = buffer.match(/(?:^|\n)LISTENING_ON=(\d+)\r?(?:\n|$)/);
      if (found) { const value = Number(found[1]); if (Number.isInteger(value) && value >= 1 && value <= 65535) port = value; }
    };
    const deadline = setTimeout(() => settle(new Error("O serviço não ficou disponível no prazo. Confira o runtime Python e tente novamente.")), timeout);
    const poll = setInterval(async () => {
      if (!port || checking || finished) return;
      checking = true;
      try { if (await checkHealth(port, instance)) settle(); } catch { /* A porta é anunciada antes de o Waitress aceitar conexões. */ }
      finally { checking = false; }
    }, 200);
    child.stdout.on("data", readPort);
    // Drain stderr without exposing credentials, payloads or arbitrary paths in the renderer.
    child.stderr.on("data", () => {});
    child.once("error", () => settle(new Error("Não foi possível iniciar o Python configurado para esta instalação.")));
    child.once("exit", () => {
      if (!finished) settle(new Error("O serviço local encerrou durante a inicialização."));
      else if (!intentional) onExit();
    });
  });
  return { ready, stop, child };
}
module.exports = { sameOrigin, externalUrl, health, startBackend };
