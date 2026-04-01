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

export function renderSessionDetail(
  container,
  {
    selectedSession = null,
    sessionDetail = null,
    sessionDetailLoading = false,
    sessionDetailError = null,
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
    createMetaPill(`hosted_state: ${readField(hostedSession, "state", "-")}`),
  );
  if (sessionDetailLoading) {
    meta.append(createMetaPill("loading detail"));
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
}
