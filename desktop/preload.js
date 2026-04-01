const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopApi", {
  getRelayConfig: () => ipcRenderer.invoke("relay:getConfig"),
  getSnapshot: () => ipcRenderer.invoke("relay:getSnapshot"),
  getSessionDetail: (payload) =>
    ipcRenderer.invoke("relay:getSessionDetail", payload),
  submitApprovalDecision: (payload) =>
    ipcRenderer.invoke("relay:submitApprovalDecision", payload),
});
