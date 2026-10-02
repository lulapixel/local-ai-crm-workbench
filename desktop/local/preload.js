"use strict";
const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("prospectosLocal", {
  retry: () => ipcRenderer.invoke("local-retry"),
  onStatus: callback => {
    if (typeof callback !== "function") return;
    ipcRenderer.on("local-status", (_event, status) => callback({ message: String(status.message), failed: Boolean(status.failed) }));
  }
});
