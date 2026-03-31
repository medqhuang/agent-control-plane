import { renderApprovalList } from "./features/approvals/render-approval-list.js";
import { renderSessionList } from "./features/sessions/render-session-list.js";
import { createSnapshotStore } from "./state/snapshot-store.js";

const AUTO_REFRESH_INTERVAL_MS = 5000;

const elements = {
  relayEndpoint: document.querySelector("#relay-endpoint"),
  connectionStatus: document.querySelector("#connection-status"),
  lastUpdated: document.querySelector("#last-updated"),
  errorMessage: document.querySelector("#error-message"),
  refreshButton: document.querySelector("#refresh-button"),
  sessionCount: document.querySelector("#session-count"),
  approvalCount: document.querySelector("#approval-count"),
  sessionList: document.querySelector("#session-list"),
  approvalList: document.querySelector("#approval-list"),
};

const statusLabels = {
  idle: "Idle",
  loading: "Connecting",
  refreshing: "Refreshing",
  ready: "Connected",
  error: "Error",
};

const store = createSnapshotStore();

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
  const approvals = state.snapshot.approvals;
  const sessions = state.snapshot.sessions;
  const pendingApprovals = approvals.filter(
    (approval) => approval.status === "pending",
  );

  elements.relayEndpoint.textContent = state.relayBaseUrl || "-";
  elements.lastUpdated.textContent = formatLastUpdated(state.lastUpdated);
  elements.sessionCount.textContent = String(sessions.length);
  elements.approvalCount.textContent = `${pendingApprovals.length}/${approvals.length}`;
  elements.refreshButton.disabled =
    state.status === "loading" || state.status === "refreshing";

  updateStatusBadge(state.status);
  renderSessionList(elements.sessionList, sessions);
  renderApprovalList(elements.approvalList, approvals);

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

store.subscribe(renderApp);
renderApp(store.getState());
store.refresh();

const pollTimer = window.setInterval(() => {
  store.refresh();
}, AUTO_REFRESH_INTERVAL_MS);

window.addEventListener("beforeunload", () => {
  window.clearInterval(pollTimer);
});
