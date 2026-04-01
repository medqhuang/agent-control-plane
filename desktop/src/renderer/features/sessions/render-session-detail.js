function createMetaPill(label) {
  const pill = document.createElement("span");
  pill.className = "meta-pill";
  pill.textContent = label;
  return pill;
}

function createEmptyState(message) {
  const item = document.createElement("div");
  item.className = "empty-state";
  item.textContent = message;
  return item;
}

function createDetailRow(label, value) {
  const row = document.createElement("div");
  row.className = "detail-row";

  const key = document.createElement("span");
  key.className = "detail-key";
  key.textContent = label;

  const detailValue = document.createElement("span");
  detailValue.className = "detail-value";
  detailValue.textContent = value || "-";

  row.append(key, detailValue);
  return row;
}

function createSectionTitle(title) {
  const heading = document.createElement("h3");
  heading.className = "subsection-title";
  heading.textContent = title;
  return heading;
}

function readField(record, fieldName, fallback = "") {
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

function readObject(record, fieldName) {
  if (!record || typeof record !== "object") {
    return {};
  }

  const value = record[fieldName];
  return value && typeof value === "object" && !Array.isArray(value)
    ? value
    : {};
}

function hasObjectData(value) {
  return Boolean(
    value &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.keys(value).length > 0,
  );
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString();
}

function formatJson(value) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function extractReplyText(value, depth = 0) {
  if (depth > 3 || value === null || value === undefined) {
    return "";
  }

  if (typeof value === "string") {
    return value.trim();
  }

  if (Array.isArray(value)) {
    for (const item of value) {
      const nestedText = extractReplyText(item, depth + 1);
      if (nestedText) {
        return nestedText;
      }
    }
    return "";
  }

  if (typeof value !== "object") {
    return "";
  }

  const candidateKeys = [
    "output_text",
    "outputText",
    "text",
    "content",
    "response",
    "answer",
    "result",
    "parts",
    "items",
  ];

  for (const key of candidateKeys) {
    const nestedValue = value[key];
    const nestedText = extractReplyText(nestedValue, depth + 1);
    if (nestedText) {
      return nestedText;
    }
  }

  return "";
}

function createTranscriptEntry(label, value, { code = false } = {}) {
  const entry = document.createElement("section");
  entry.className = "transcript-entry";

  const title = document.createElement("div");
  title.className = "transcript-label";
  title.textContent = label;

  const body = code
    ? document.createElement("pre")
    : document.createElement("div");
  body.className = code
    ? "transcript-body transcript-code"
    : "transcript-body";
  body.textContent = value || "-";

  entry.append(title, body);
  return entry;
}

function createApprovalDecisionButton(
  label,
  verb,
  requestId,
  remoteId,
  decision,
  submittingDecision,
) {
  const button = document.createElement("button");
  const isSubmitting = submittingDecision === decision;
  button.type = "button";
  button.className = `action-button is-${decision}`;
  button.dataset.requestId = requestId;
  button.dataset.remoteId = remoteId;
  button.dataset.approvalDecision = decision;
  button.disabled = Boolean(submittingDecision) || requestId === "";
  button.textContent = isSubmitting ? `${verb}...` : label;
  return button;
}

function createApprovalContextSection(
  sessionId,
  remoteId,
  {
    hostedState = "",
    pendingRequestId = "",
    approvalRequest = {},
    sessionApproval = null,
    sessionApprovalSubmittingDecision = "",
  } = {},
) {
  const approval = sessionApproval && typeof sessionApproval === "object"
    ? sessionApproval
    : {};
  const requestId = readField(
    approval,
    "request_id",
    readField(approvalRequest, "request_id", pendingRequestId),
  );
  const summary = readField(
    approval,
    "summary",
    readField(approvalRequest, "summary", "This hosted session is waiting for approval."),
  );
  const kind = readField(
    approval,
    "kind",
    readField(approvalRequest, "kind", "-"),
  );
  const section = document.createElement("section");
  section.className = "detail-section approval-context-section";
  section.append(createSectionTitle("Approval Context"));

  const statusText = document.createElement("p");
  statusText.className = "reply-status is-running";
  if (sessionApprovalSubmittingDecision === "approve") {
    statusText.textContent =
      "Approving through relay. Waiting for the hosted session to continue.";
  } else if (sessionApprovalSubmittingDecision === "reject") {
    statusText.textContent =
      "Rejecting through relay. Waiting for the hosted session to continue.";
  } else {
    statusText.textContent =
      "This session is paused at approval_pending. Resolve the approval here or locate it in the approvals list.";
  }
  section.append(statusText);

  const detailGrid = document.createElement("div");
  detailGrid.className = "item-detail-grid";
  detailGrid.append(
    createDetailRow("session_id", sessionId),
    createDetailRow("remote_id", remoteId),
    createDetailRow("request_id", requestId || "-"),
    createDetailRow("kind", kind || "-"),
    createDetailRow("hosted_state", hostedState || "-"),
    createDetailRow("summary", summary || "-"),
  );
  section.append(detailGrid);

  const actions = document.createElement("div");
  actions.className = "approval-actions";
  actions.append(
    createApprovalDecisionButton(
      "Approve",
      "Approving",
      requestId,
      remoteId,
      "approve",
      sessionApprovalSubmittingDecision,
    ),
    createApprovalDecisionButton(
      "Reject",
      "Rejecting",
      requestId,
      remoteId,
      "reject",
      sessionApprovalSubmittingDecision,
    ),
  );

  const locateButton = document.createElement("button");
  locateButton.type = "button";
  locateButton.className = "action-button approval-link-button";
  locateButton.dataset.openApproval = "true";
  locateButton.dataset.requestId = requestId;
  locateButton.dataset.remoteId = remoteId;
  locateButton.disabled = requestId === "";
  locateButton.textContent = "Locate In Approvals";
  actions.append(locateButton);

  section.append(actions);
  return section;
}

function createReplyComposer(
  sessionId,
  remoteId,
  {
    sessionReplyDraft = "",
    sessionReplySubmitting = false,
    sessionReplyError = "",
    sessionReplyProgress = null,
    replyBlockedReason = "",
  } = {},
) {
  const progress = sessionReplyProgress && typeof sessionReplyProgress === "object"
    ? sessionReplyProgress
    : {};
  const progressPhase = readField(progress, "phase", "");
  const completedAt = readField(progress, "completedAt", "");
  const turnStatus = readField(progress, "turnStatus", "");
  const replySection = document.createElement("section");
  replySection.className = "detail-section";
  replySection.append(createSectionTitle("Reply"));

  const form = document.createElement("form");
  form.className = "reply-form";
  form.dataset.sessionReplyForm = "true";
  form.dataset.sessionId = sessionId;
  form.dataset.remoteId = remoteId;

  const inputLabel = document.createElement("label");
  inputLabel.className = "detail-key";
  inputLabel.textContent = "Reply Message";

  const textarea = document.createElement("textarea");
  textarea.className = "reply-input";
  textarea.rows = 4;
  textarea.placeholder = "Forward a reply to this hosted session through relay.";
  textarea.value = sessionReplyDraft;
  textarea.disabled = sessionReplySubmitting || replyBlockedReason !== "";
  textarea.dataset.sessionReplyInput = "true";
  textarea.dataset.sessionId = sessionId;
  textarea.dataset.remoteId = remoteId;

  const actions = document.createElement("div");
  actions.className = "reply-actions";

  const button = document.createElement("button");
  button.type = "submit";
  button.className = "action-button reply-submit-button";
  button.disabled =
    sessionReplySubmitting ||
    sessionReplyDraft.trim() === "" ||
    replyBlockedReason !== "";
  button.textContent = sessionReplySubmitting
    ? progressPhase === "running"
      ? "Running..."
      : "Sending..."
    : "Submit Reply";
  actions.append(button);

  form.append(inputLabel, textarea, actions);
  replySection.append(form);

  if (sessionReplyError) {
    const errorMessage = document.createElement("p");
    errorMessage.className = "reply-status is-error";
    errorMessage.textContent = sessionReplyError;
    replySection.append(errorMessage);
  } else if (progressPhase === "sending") {
    const sendingMessage = document.createElement("p");
    sendingMessage.className = "reply-status is-running";
    sendingMessage.textContent = "Sending reply through relay...";
    replySection.append(sendingMessage);
  } else if (progressPhase === "running") {
    const runningMessage = document.createElement("p");
    runningMessage.className = "reply-status is-running";
    runningMessage.textContent =
      "Reply sent. Waiting for the hosted session result to refresh...";
    replySection.append(runningMessage);
  } else if (progressPhase === "approval_pending") {
    const pausedMessage = document.createElement("p");
    pausedMessage.className = "reply-status is-running";
    pausedMessage.textContent =
      "Reply is paused for approval. Resolve the approval below to continue this turn.";
    replySection.append(pausedMessage);
  } else if (progressPhase === "completed" && sessionReplyDraft.trim() === "") {
    const successMessage = document.createElement("p");
    successMessage.className = "reply-status is-success";
    successMessage.textContent =
      `Completed at ${formatDateTime(completedAt)}${turnStatus ? ` (${turnStatus})` : ""}.`;
    replySection.append(successMessage);
  } else if (progressPhase === "failed") {
    const failedMessage = document.createElement("p");
    failedMessage.className = "reply-status is-error";
    failedMessage.textContent =
      `Hosted session failed${turnStatus ? ` (${turnStatus})` : ""}.`;
    replySection.append(failedMessage);
  }

  if (replyBlockedReason) {
    const blockedMessage = document.createElement("p");
    blockedMessage.className = "reply-status";
    blockedMessage.textContent = replyBlockedReason;
    replySection.append(blockedMessage);
  }

  const helperText = document.createElement("p");
  helperText.className = "reply-status";
  helperText.textContent =
    "P7-D keeps reply and approval continuation in the same control surface.";
  replySection.append(helperText);

  return replySection;
}

export function renderSessionDetail(
  container,
  {
    selectedSession = null,
    sessionDetail = null,
    sessionDetailLoading = false,
    sessionDetailError = null,
    sessionReplyDraft = "",
    sessionReplySubmitting = false,
    sessionReplyError = "",
    sessionReplyProgress = null,
    sessionApproval = null,
    sessionApprovalSubmittingDecision = "",
  } = {},
) {
  container.replaceChildren();

  if (!selectedSession && !sessionDetail) {
    container.append(
      createEmptyState(
        "Select a hosted session from the list to load detail through relay.",
      ),
    );
    return;
  }

  const relaySession = sessionDetail && typeof sessionDetail === "object"
    ? readObject(sessionDetail, "session")
    : {};
  const fallbackSession = selectedSession && typeof selectedSession === "object"
    ? selectedSession
    : {};
  const detailPayload = sessionDetail && typeof sessionDetail === "object"
    ? readObject(sessionDetail, "detail")
    : {};
  const hostedSession = readObject(detailPayload, "session");
  const providerObservation = readObject(detailPayload, "provider_observation");
  const lastTurn = readObject(hostedSession, "last_turn");
  const promptResult = hasObjectData(readObject(lastTurn, "prompt_result"))
    ? readObject(lastTurn, "prompt_result")
    : readObject(providerObservation, "prompt_result");
  const approvalRequest = hasObjectData(readObject(lastTurn, "approval_request"))
    ? readObject(lastTurn, "approval_request")
    : readObject(providerObservation, "approval_request");
  const pendingRequestId = readField(hostedSession, "pending_request_id", "");
  const hostedState = readField(hostedSession, "state", "");
  const replyText = extractReplyText(promptResult);
  const sessionId = readField(
    relaySession,
    "id",
    readField(fallbackSession, "id", readField(hostedSession, "session_id", "-")),
  );
  const remoteId = readField(
    relaySession,
    "remote_id",
    readField(fallbackSession, "remote_id", readField(fallbackSession, "remote", "-")),
  );
  const provider = readField(
    relaySession,
    "provider",
    readField(hostedSession, "provider", "-"),
  );
  const title = readField(
    relaySession,
    "title",
    readField(fallbackSession, "title", readField(hostedSession, "title", "-")),
  );

  const summary = document.createElement("section");
  summary.className = "detail-summary";

  const detailTitle = document.createElement("div");
  detailTitle.className = "item-title";
  detailTitle.textContent = sessionId;

  const meta = document.createElement("div");
  meta.className = "item-meta";
  meta.append(
    createMetaPill(`remote: ${remoteId || "-"}`),
    createMetaPill(`provider: ${provider || "-"}`),
    createMetaPill(`relay_status: ${readField(relaySession, "status", "-")}`),
    createMetaPill(`hosted_state: ${hostedState || "-"}`),
  );
  if (sessionDetailLoading) {
    meta.append(createMetaPill("loading detail"));
  }
  if (
    sessionReplyProgress &&
    typeof sessionReplyProgress === "object" &&
    readField(sessionReplyProgress, "phase", "")
  ) {
    meta.append(
      createMetaPill(`reply: ${readField(sessionReplyProgress, "phase", "-")}`),
    );
  }

  const titleLine = document.createElement("p");
  titleLine.className = "item-detail";
  titleLine.textContent = `title: ${title}`;

  summary.append(detailTitle, meta, titleLine);
  container.append(summary);

  if (sessionDetailError) {
    const errorMessage = document.createElement("p");
    errorMessage.className = "error-message detail-error-message";
    errorMessage.textContent = sessionDetailError;
    container.append(errorMessage);
  }

  const metadata = document.createElement("section");
  metadata.className = "detail-section";
  metadata.append(
    createSectionTitle("Session Metadata"),
  );

  const metadataGrid = document.createElement("div");
  metadataGrid.className = "item-detail-grid";
  metadataGrid.append(
    createDetailRow("session_id", sessionId),
    createDetailRow("remote_id", remoteId),
    createDetailRow("workdir", readField(hostedSession, "workdir", "-")),
    createDetailRow("turn_count", readField(hostedSession, "turn_count", "0")),
    createDetailRow("created_at", formatDateTime(readField(hostedSession, "created_at", ""))),
    createDetailRow("updated_at", formatDateTime(readField(hostedSession, "updated_at", ""))),
    createDetailRow("pending_request_id", readField(hostedSession, "pending_request_id", "-")),
    createDetailRow("detail_fetched_at", formatDateTime(readField(sessionDetail, "fetchedAt", ""))),
  );
  metadata.append(metadataGrid);
  container.append(metadata);

  const turnSection = document.createElement("section");
  turnSection.className = "detail-section";
  turnSection.append(createSectionTitle("Recent Turn"));

  const turnGrid = document.createElement("div");
  turnGrid.className = "item-detail-grid";
  turnGrid.append(
    createDetailRow("action", readField(lastTurn, "action", "-")),
    createDetailRow("status", readField(lastTurn, "status", "-")),
    createDetailRow("started_at", formatDateTime(readField(lastTurn, "started_at", ""))),
    createDetailRow("completed_at", formatDateTime(readField(lastTurn, "completed_at", ""))),
  );
  turnSection.append(turnGrid);
  container.append(turnSection);

  const transcriptSection = document.createElement("section");
  transcriptSection.className = "detail-section";
  transcriptSection.append(createSectionTitle("Recent Transcript"));

  const transcript = document.createElement("div");
  transcript.className = "transcript-list";

  const recentInput = readField(lastTurn, "message", "");
  if (recentInput) {
    transcript.append(
      createTranscriptEntry("Last input", recentInput),
    );
  }

  if (replyText) {
    transcript.append(
      createTranscriptEntry("Recent reply", replyText),
    );
  } else if (hasObjectData(promptResult)) {
    transcript.append(
      createTranscriptEntry("prompt_result", formatJson(promptResult), {
        code: true,
      }),
    );
  } else if (hasObjectData(approvalRequest)) {
    transcript.append(
      createTranscriptEntry("approval_request", formatJson(approvalRequest), {
        code: true,
      }),
    );
  } else if (readField(hostedSession, "error", "")) {
    transcript.append(
      createTranscriptEntry("error", readField(hostedSession, "error", "")),
    );
  } else {
    transcript.append(
      createTranscriptEntry(
        "detail",
        "Current remote-agent detail payload does not expose a reply body for this session yet.",
      ),
    );
  }

  transcriptSection.append(transcript);
  container.append(transcriptSection);

  if (
    hostedState === "approval_pending" ||
    pendingRequestId !== "" ||
    hasObjectData(approvalRequest) ||
    (sessionApproval && typeof sessionApproval === "object")
  ) {
    container.append(
      createApprovalContextSection(sessionId, remoteId === "-" ? "" : remoteId, {
        hostedState,
        pendingRequestId,
        approvalRequest,
        sessionApproval,
        sessionApprovalSubmittingDecision,
      }),
    );
  }

  if (sessionId && sessionId !== "-") {
    container.append(
      createReplyComposer(sessionId, remoteId === "-" ? "" : remoteId, {
        sessionReplyDraft,
        sessionReplySubmitting,
        sessionReplyError,
        sessionReplyProgress,
        replyBlockedReason: hostedState === "approval_pending"
          ? "Current turn is waiting for approval. Resolve the approval before sending another reply."
          : hostedState === "running"
            ? "Current turn is still running. Wait for this result to finish before sending another reply."
            : "",
      }),
    );
  }
}
