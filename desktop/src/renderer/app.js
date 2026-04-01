import { renderRemoteList } from "./features/remotes/render-remote-list.js";
import { renderApprovalList } from "./features/approvals/render-approval-list.js";
import { renderSessionDetail } from "./features/sessions/render-session-detail.js";
import { renderSessionList } from "./features/sessions/render-session-list.js";
import { createSnapshotStore } from "./state/snapshot-store.js";

const AUTO_REFRESH_INTERVAL_MS = 5000;

const elements = {
  relayEndpoint: document.querySelector("#relay-endpoint"),
  connectionStatus: document.querySelector("#connection-status"),
  lastUpdated: document.querySelector("#last-updated"),
  errorMessage: document.querySelector("#error-message"),
  refreshButton: document.querySelector("#refresh-button"),
  remoteCount: document.querySelector("#remote-count"),
  serverList: document.querySelector("#server-list"),
  sessionCount: document.querySelector("#session-count"),
  approvalCount: document.querySelector("#approval-count"),
  sessionList: document.querySelector("#session-list"),
  sessionDetail: document.querySelector("#session-detail"),
  approvalList: document.querySelector("#approval-list"),
};

const statusLabels = {
  loading: "Loading",
  connected: "Connected",
  disconnected: "Disconnected",
  error: "Error",
};

const store = createSnapshotStore();

function readRecordField(record, fieldName, fallback = "") {
  if (!record || typeof record !== "object") {
    return fallback;
  }

  const value = record[fieldName];
  if (value === null || value === undefined) {
    return fallback;
  }

  const normalizedValue = String(value).trim();
  return normalizedValue === "" ? fallback : normalizedValue;
}

function buildSessionKey(session) {
  return `${readRecordField(
    session,
    "remote_id",
    readRecordField(session, "remote", ""),
  )}::${readRecordField(session, "id", "")}`;
}

function formatLastUpdated(value) {
  if (!value) {
    return "Never";
  }

  return new Date(value).toLocaleString();
}

function updateStatusBadge(status) {
  elements.connectionStatus.textContent = statusLabels[status] || status;
  elements.connectionStatus.className = `value status-badge is-${status}`;
}

function renderApp(state) {
  const servers = state.snapshot.servers;
  const approvals = state.snapshot.approvals;
  const sessions = state.snapshot.sessions;
  const pendingApprovals = approvals.filter(
    (approval) => approval.status === "pending",
  );
  const hasApprovalAction =
    Object.keys(state.approvalActionByKey).length > 0;
  const selectedSession = sessions.find((session) =>
    buildSessionKey(session) === state.selectedSessionKey
  ) || null;

  elements.relayEndpoint.textContent = state.relayBaseUrl || "-";
  elements.lastUpdated.textContent = formatLastUpdated(state.lastUpdated);
  elements.remoteCount.textContent = String(servers.length);
  elements.sessionCount.textContent = String(sessions.length);
  elements.approvalCount.textContent = String(pendingApprovals.length);
  elements.refreshButton.disabled =
    state.status === "loading" || hasApprovalAction;

  updateStatusBadge(state.status);
  renderRemoteList(elements.serverList, servers, {
    sessions,
    approvals,
  });
  renderSessionList(elements.sessionList, sessions, {
    selectedSessionKey: state.selectedSessionKey,
  });
  renderSessionDetail(elements.sessionDetail, {
    selectedSession,
    sessionDetail: state.sessionDetail,
    sessionDetailLoading: state.sessionDetailLoading,
    sessionDetailError: state.sessionDetailError,
  });
  renderApprovalList(elements.approvalList, pendingApprovals, {
    approvalActionByKey: state.approvalActionByKey,
  });

  if (state.error) {
    elements.errorMessage.hidden = false;
    elements.errorMessage.textContent = state.error;
    return;
  }

  elements.errorMessage.hidden = true;
  elements.errorMessage.textContent = "";
}

elements.refreshButton.addEventListener("click", () => {
  store.refresh();
});

elements.sessionList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-session-id]");
  if (!button) {
    return;
  }

  const {
    sessionId,
    remoteId = "",
  } = button.dataset;
  if (!sessionId) {
    return;
  }

  try {
    await store.selectSession(sessionId, remoteId);
  } catch {
    // Store state already carries the detail error for the UI.
  }
});

elements.approvalList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-approval-decision]");
  if (!button) {
    return;
  }

  const {
    approvalDecision,
    requestId,
    remoteId = "",
  } = button.dataset;
  if (!requestId || !approvalDecision) {
    return;
  }

  try {
    await store.submitApprovalDecision(requestId, remoteId, approvalDecision);
  } catch {
    // Store state already carries the error message for the UI.
  }
});

store.subscribe(renderApp);
renderApp(store.getState());
store.refresh();

const pollTimer = window.setInterval(() => {
  store.refresh();
}, AUTO_REFRESH_INTERVAL_MS);

window.addEventListener("beforeunload", () => {
  window.clearInterval(pollTimer);
});
