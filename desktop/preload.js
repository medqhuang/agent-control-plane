const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopApi", {
  getRelayConfig: () => ipcRenderer.invoke("relay:getConfig"),
  getSnapshot: () => ipcRenderer.invoke("relay:getSnapshot"),
});
