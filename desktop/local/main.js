"use strict";
const { app, BrowserWindow, Menu, ipcMain, shell } = require("electron");
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { startBackend, sameOrigin, externalUrl } = require("./runtime");
const config = JSON.parse(fs.readFileSync(path.join(__dirname, "local-config.json"), "utf8"));
// Optional compatibility mode; preserve Chromium's normal rendering by default.
if (process.argv.includes("--software-rendering")) app.disableHardwareAcceleration();
const smoke = process.argv.includes("--smoke");
const dataDir = smoke ? path.join(config.validation, "smoke-data") : config.data;
fs.mkdirSync(dataDir, { recursive: true });
app.setName("ProspectOS Local");
app.setPath("userData", path.join(dataDir, "desktop-profile"));
const startup = pathToFileURL(path.join(__dirname, "startup.html")).href;
let window, server, origin, starting = false, quitting = false, recovering = false;

function status(message, failed = false) {
  if (window && !window.isDestroyed()) window.webContents.send("local-status", { message, failed });
}
async function unavailable(message) {
  origin = null;
  if (!window || window.isDestroyed() || quitting || recovering) return;
  recovering = true;
  try { await window.loadURL(startup); status(message, true); }
  catch {
    server?.stop();
    if (smoke) fs.writeFileSync(path.join(config.validation, "desktop-smoke.json"), JSON.stringify({ ready: false, error: "O renderer local não pôde ser iniciado." }));
    app.exit(1);
  } finally { recovering = false; }
}
async function launch() {
  if (starting || quitting) return;
  starting = true;
  server?.stop();
  status("Preparando sua base e iniciando o serviço local…");
  try {
    server = startBackend({ ...config, data: dataDir }, { smoke, onExit: () => void unavailable("O serviço local encerrou. Você pode tentar iniciar novamente.") });
    const ready = await server.ready;
    if (quitting) return;
    origin = ready.origin;
    await window.loadURL(origin + "/");
    if (smoke) {
      // Artifact from this application's own test window, no computer-control driver.
      await new Promise(resolve => setTimeout(resolve, 1500));
      let screenshotSaved = false, screenshotError = null;
      try {
        const image = await window.webContents.capturePage();
        fs.writeFileSync(path.join(config.validation, "desktop-smoke.png"), image.toPNG());
        screenshotSaved = true;
      } catch (error) { screenshotError = error.message; }
      fs.writeFileSync(path.join(config.validation, "desktop-smoke.json"), JSON.stringify({ ready: true,
        origin, backend_pid: ready.pid, versions: process.versions, sandbox: true, contextIsolation: true,
        frontendLoaded: window.webContents.getURL() === origin + "/", screenshotSaved, screenshotError,
        automationDisabled: true, timestamp: new Date().toISOString() }, null, 2));
      app.quit();
    }
  } catch (error) {
    server?.stop();
    await unavailable(error.message);
    if (smoke) { fs.writeFileSync(path.join(config.validation, "desktop-smoke.json"), JSON.stringify({ ready: false, error: error.message })); app.exit(1); }
  } finally { starting = false; }
}

if (!app.requestSingleInstanceLock()) app.quit();
else {
  app.on("second-instance", () => { if (window) { if (window.isMinimized()) window.restore(); window.show(); window.focus(); } });
  app.whenReady().then(async () => {
    window = new BrowserWindow({ title: "ProspectOS Local", width: 1340, height: 920, minWidth: 780, minHeight: 580,
      backgroundColor: "#edf4f6", icon: path.join(__dirname, "prospectos.ico"),
      webPreferences: { sandbox: true, contextIsolation: true, nodeIntegration: false, preload: path.join(__dirname, "preload.js") } });
    const session = window.webContents.session;
    session.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));
    session.setPermissionCheckHandler(() => false);
    window.webContents.on("will-navigate", (event, url) => {
      if (url !== startup && !(origin && sameOrigin(url, origin))) { event.preventDefault(); const safe = externalUrl(url); if (safe) void shell.openExternal(safe); }
    });
    window.webContents.setWindowOpenHandler(({ url }) => {
      const safe = externalUrl(url);
      if (safe && !(origin && sameOrigin(safe, origin))) void shell.openExternal(safe);
      return { action: "deny" };
    });
    window.webContents.on("will-attach-webview", event => event.preventDefault());
    window.webContents.on("render-process-gone", () => void unavailable("A interface parou de responder. Reinicie o serviço pelo botão abaixo."));
    ipcMain.handle("local-retry", event => {
      if (event.sender === window.webContents && event.senderFrame?.url === startup) void launch();
    });
    Menu.setApplicationMenu(Menu.buildFromTemplate([
      { label: "ProspectOS", submenu: [
        { label: "Central de operação", click: () => origin && window.loadURL(origin + "/operacao") },
        { label: "Mesa do gestor", click: () => origin && window.loadURL(origin + "/") },
        { label: "Bot e agenda", click: () => origin && window.loadURL(origin + "/bot") },
        { type: "separator" }, { label: "Sair", role: "quit" }] },
      { label: "Editar", submenu: [{ role: "undo" }, { role: "redo" }, { type: "separator" }, { role: "cut" }, { role: "copy" }, { role: "paste" }, { role: "selectAll" }] },
      { label: "Visualizar", submenu: [{ role: "reload" }, { role: "resetZoom" }, { role: "zoomIn" }, { role: "zoomOut" }, { role: "togglefullscreen" }] }
    ]));
    try { await window.loadURL(startup); void launch(); }
    catch { await unavailable("Não foi possível carregar a interface de inicialização."); }
  });
}
app.on("window-all-closed", () => app.quit());
app.on("before-quit", () => { quitting = true; server?.stop(); });
