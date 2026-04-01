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

function buildApprovalActionKey(requestId, remoteId = "") {
  return `${String(remoteId || "").trim()}::${String(requestId || "").trim()}`;
}

function findSelectedSessionApproval(selectedSession, sessionDetail, approvals) {
  if (!selectedSession) {
    return null;
  }

  const detailPayload = sessionDetail && typeof sessionDetail === "object"
    ? sessionDetail.detail
    : null;
  const hostedSession = detailPayload && typeof detailPayload === "object"
    ? detailPayload.session
    : null;
  const lastTurn = hostedSession && typeof hostedSession === "object"
    ? hostedSession.last_turn
    : null;
  const lastTurnApproval = lastTurn && typeof lastTurn === "object"
    ? lastTurn.approval_request
    : null;
  const providerObservation = detailPayload && typeof detailPayload === "object"
    ? detailPayload.provider_observation
    : null;
  const observedApproval = lastTurnApproval && typeof lastTurnApproval === "object"
    ? lastTurnApproval
    : providerObservation && typeof providerObservation === "object"
      ? providerObservation.approval_request
      : null;

  const sessionId = readRecordField(selectedSession, "id", "");
  const remoteId = readRecordField(
    selectedSession,
    "remote_id",
    readRecordField(selectedSession, "remote", ""),
  );
  const pendingRequestId = hostedSession && typeof hostedSession === "object"
    ? readRecordField(hostedSession, "pending_request_id", "")
    : "";
  const observedRequestId = observedApproval && typeof observedApproval === "object"
    ? readRecordField(observedApproval, "request_id", "")
    : "";

  for (const approval of approvals) {
    const approvalSessionId = readRecordField(approval, "session_id", "");
    const approvalRemoteId = readRecordField(
      approval,
      "remote_id",
      readRecordField(approval, "remote", ""),
    );
    const approvalRequestId = readRecordField(approval, "request_id", "");

    if (approvalSessionId === sessionId && approvalRemoteId === remoteId) {
      return approval;
    }

    if (
      approvalRemoteId === remoteId &&
      approvalRequestId !== "" &&
      (approvalRequestId === pendingRequestId || approvalRequestId === observedRequestId)
    ) {
      return approval;
    }
  }

  return null;
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
  const hasSessionReplyAction = state.sessionReplySubmittingKey !== "";
  const selectedSession = sessions.find((session) =>
    buildSessionKey(session) === state.selectedSessionKey
  ) || null;
  const selectedSessionReplyDraft = state.selectedSessionKey
    ? state.sessionReplyDraftByKey[state.selectedSessionKey] || ""
    : "";
  const selectedSessionReplyError = state.selectedSessionKey
    ? state.sessionReplyErrorByKey[state.selectedSessionKey] || ""
    : "";
  const selectedSessionReplyProgress = state.selectedSessionKey
    ? state.sessionReplyProgressByKey[state.selectedSessionKey] || null
    : null;
  const selectedSessionApproval = findSelectedSessionApproval(
    selectedSession,
    state.sessionDetail,
    pendingApprovals,
  );
  const selectedSessionApprovalKey = selectedSessionApproval
    ? buildApprovalActionKey(
      readRecordField(selectedSessionApproval, "request_id", ""),
      readRecordField(
        selectedSessionApproval,
        "remote_id",
        readRecordField(selectedSessionApproval, "remote", ""),
      ),
    )
    : "";
  const selectedSessionApprovalSubmittingDecision = selectedSessionApprovalKey
    ? state.approvalActionByKey[selectedSessionApprovalKey] || ""
    : "";

  elements.relayEndpoint.textContent = state.relayBaseUrl || "-";
  elements.lastUpdated.textContent = formatLastUpdated(state.lastUpdated);
  elements.remoteCount.textContent = String(servers.length);
  elements.sessionCount.textContent = String(sessions.length);
  elements.approvalCount.textContent = String(pendingApprovals.length);
  elements.refreshButton.disabled =
    state.status === "loading" || hasApprovalAction || hasSessionReplyAction;

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
    sessionReplyDraft: selectedSessionReplyDraft,
    sessionReplySubmitting:
      state.sessionReplySubmittingKey === state.selectedSessionKey,
    sessionReplyError: selectedSessionReplyError,
    sessionReplyProgress: selectedSessionReplyProgress,
    sessionApproval: selectedSessionApproval,
    sessionApprovalSubmittingDecision: selectedSessionApprovalSubmittingDecision,
  });
  renderApprovalList(elements.approvalList, pendingApprovals, {
    approvalActionByKey: state.approvalActionByKey,
    contextApprovalKey: selectedSessionApprovalKey,
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
  const currentState = store.getState();
  if (
    currentState.sessionReplySubmittingKey !== "" ||
    Object.keys(currentState.approvalActionByKey).length > 0
  ) {
    return;
  }

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

elements.sessionDetail.addEventListener("input", (event) => {
  if (!(event.target instanceof HTMLTextAreaElement)) {
    return;
  }

  if (!event.target.matches("[data-session-reply-input]")) {
    return;
  }

  const {
    sessionId,
    remoteId = "",
  } = event.target.dataset;
  if (!sessionId) {
    return;
  }

  store.setSessionReplyDraft(sessionId, remoteId, event.target.value);
});

elements.sessionDetail.addEventListener("submit", async (event) => {
  const form = event.target.closest("[data-session-reply-form]");
  if (!form) {
    return;
  }

  event.preventDefault();

  const {
    sessionId,
    remoteId = "",
  } = form.dataset;
  if (!sessionId) {
    return;
  }

  try {
    await store.submitSessionReply(sessionId, remoteId);
  } catch {
    // Store state already carries the reply submission error for the UI.
  }
});

elements.sessionDetail.addEventListener("click", async (event) => {
  const decisionButton = event.target.closest("[data-approval-decision]");
  if (decisionButton) {
    const {
      approvalDecision,
      requestId,
      remoteId = "",
    } = decisionButton.dataset;
    if (!requestId || !approvalDecision) {
      return;
    }

    try {
      await store.submitApprovalDecision(requestId, remoteId, approvalDecision);
    } catch {
      // Store state already carries the error message for the UI.
    }
    return;
  }

  const locateButton = event.target.closest("[data-open-approval]");
  if (!locateButton) {
    return;
  }

  const {
    requestId,
    remoteId = "",
  } = locateButton.dataset;
  if (!requestId) {
    return;
  }

  const approvalKey = buildApprovalActionKey(requestId, remoteId);
  const approvalItems = elements.approvalList.querySelectorAll("[data-approval-key]");
  const matchedItem = [...approvalItems].find((item) =>
    item.dataset.approvalKey === approvalKey
  );
  if (!matchedItem) {
    return;
  }

  matchedItem.scrollIntoView({
    block: "center",
    behavior: "smooth",
  });
  const primaryAction = matchedItem.querySelector("[data-approval-decision]");
  if (primaryAction instanceof HTMLElement) {
    primaryAction.focus();
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
