const path = require("node:path");
const { app, BrowserWindow, ipcMain } = require("electron");

const DEFAULT_RELAY_BASE_URL = "http://127.0.0.1:8000";
const RELAY_TIMEOUT_MS = 3000;

function getRelayBaseUrl() {
  return process.env.RELAY_BASE_URL || DEFAULT_RELAY_BASE_URL;
}

async function fetchJson(url, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      headers: {
        Accept: "application/json",
      },
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`relay responded with ${response.status}`);
    }

    return response.json();
  } catch (error) {
    if (error && error.name === "AbortError") {
      throw new Error(`relay request timed out after ${timeoutMs}ms`);
    }

    throw error;
  } finally {
    clearTimeout(timer);
  }
}

async function getSnapshotPayload() {
  const relayBaseUrl = getRelayBaseUrl();
  const snapshotUrl = new URL("/v1/snapshot", relayBaseUrl).toString();
  const snapshot = await fetchJson(snapshotUrl, RELAY_TIMEOUT_MS);

  return {
    relayBaseUrl,
    fetchedAt: new Date().toISOString(),
    snapshot,
  };
}

function createMainWindow() {
  const window = new BrowserWindow({
    width: 1120,
    height: 760,
    minWidth: 960,
    minHeight: 640,
    title: "Agent Control Plane",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  window.loadFile(path.join(__dirname, "src", "index.html"));
}

ipcMain.handle("relay:getConfig", async () => {
  return {
    relayBaseUrl: getRelayBaseUrl(),
  };
});

ipcMain.handle("relay:getSnapshot", async () => {
  return getSnapshotPayload();
});

app.whenReady().then(() => {
  createMainWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
