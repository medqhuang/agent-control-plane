const path = require("node:path");
const { app, BrowserWindow, ipcMain } = require("electron");

const DEFAULT_RELAY_BASE_URL = "http://127.0.0.1:8000";
const RELAY_TIMEOUT_MS = 3000;

function getRelayBaseUrl() {
  return process.env.RELAY_BASE_URL || DEFAULT_RELAY_BASE_URL;
}

function buildRelayErrorMessage(status, payload, fallbackText = "") {
  const detail = payload && typeof payload === "object" && "detail" in payload
    ? payload.detail
    : payload;

  if (typeof detail === "string" && detail !== "") {
    return `relay responded with ${status}: ${detail}`;
  }

  if (detail && typeof detail === "object") {
    if ("message" in detail && typeof detail.message === "string") {
      return `relay responded with ${status}: ${detail.message}`;
    }

    return `relay responded with ${status}: ${JSON.stringify(detail)}`;
  }

  if (fallbackText !== "") {
    return `relay responded with ${status}: ${fallbackText}`;
  }

  return `relay responded with ${status}`;
}

async function requestJson(
  url,
  {
    method = "GET",
    body,
    timeoutMs = RELAY_TIMEOUT_MS,
  } = {},
) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method,
      headers: {
        Accept: "application/json",
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });

    const responseText = await response.text();
    let payload = null;

    if (responseText !== "") {
      try {
        payload = JSON.parse(responseText);
      } catch {
        payload = null;
      }
    }

    if (!response.ok) {
      throw new Error(
        buildRelayErrorMessage(response.status, payload, responseText),
      );
    }

    return payload;
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
  const snapshot = await requestJson(snapshotUrl);

  return {
    relayBaseUrl,
    fetchedAt: new Date().toISOString(),
    snapshot,
  };
}

async function submitApprovalDecisionPayload({
  requestId,
  remoteId = "",
  decision,
}) {
  const relayBaseUrl = getRelayBaseUrl();
  const approvalResponseUrl = new URL(
    "/v1/approval-response",
    relayBaseUrl,
  ).toString();
  const response = await requestJson(approvalResponseUrl, {
    method: "POST",
    body: {
      request_id: requestId,
      remote_id: remoteId,
      decision,
    },
  });

  return {
    relayBaseUrl,
    respondedAt: new Date().toISOString(),
    response,
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

ipcMain.handle("relay:submitApprovalDecision", async (_event, payload) => {
  if (!payload || typeof payload !== "object") {
    throw new Error("approval payload is required");
  }

  if (typeof payload.requestId !== "string" || payload.requestId === "") {
    throw new Error("approval request_id is required");
  }

  if (payload.decision !== "approve" && payload.decision !== "reject") {
    throw new Error("approval decision must be approve or reject");
  }

  if ("remoteId" in payload && typeof payload.remoteId !== "string") {
    throw new Error("approval remote_id must be a string when provided");
  }

  return submitApprovalDecisionPayload({
    requestId: payload.requestId,
    remoteId: typeof payload.remoteId === "string" ? payload.remoteId : "",
    decision: payload.decision,
  });
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
