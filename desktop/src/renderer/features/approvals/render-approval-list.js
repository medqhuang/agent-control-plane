function createMetaPill(label) {
  const pill = document.createElement("span");
  pill.className = "meta-pill";
  pill.textContent = label;
  return pill;
}

function createEmptyState(message) {
  const item = document.createElement("li");
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

function createActionButton(label, verb, requestId, decision, submittingDecision) {
  const button = document.createElement("button");
  const isSubmitting = submittingDecision === decision;

  button.type = "button";
  button.className = `action-button is-${decision}`;
  button.dataset.requestId = requestId;
  button.dataset.approvalDecision = decision;
  button.disabled = Boolean(submittingDecision) || requestId === "";
  button.textContent = isSubmitting
    ? `${verb}...`
    : label;
  return button;
}

export function renderApprovalList(
  container,
  approvals,
  {
    approvalActionByRequestId = {},
  } = {},
) {
  container.replaceChildren();

  if (approvals.length === 0) {
    container.append(createEmptyState("No pending approvals in relay snapshot."));
    return;
  }

  for (const approval of approvals) {
    const requestId = approval.request_id || "";
    const submittingDecision = approvalActionByRequestId[requestId];
    const item = document.createElement("li");
    item.className = submittingDecision
      ? "list-item is-busy"
      : "list-item";

    const title = document.createElement("div");
    title.className = "item-title";
    title.textContent = approval.summary || requestId || "Approval request";

    const meta = document.createElement("div");
    meta.className = "item-meta";
    meta.append(
      createMetaPill(`status: ${approval.status || "unknown"}`),
      createMetaPill(`kind: ${approval.kind || "unknown"}`),
      createMetaPill(`session: ${approval.session_id || "-"}`),
    );

    const detailGrid = document.createElement("div");
    detailGrid.className = "item-detail-grid";
    detailGrid.append(
      createDetailRow("request_id", requestId),
      createDetailRow("session_id", approval.session_id || "-"),
    );

    const actions = document.createElement("div");
    actions.className = "approval-actions";
    actions.append(
      createActionButton(
        "Approve",
        "Approving",
        requestId,
        "approve",
        submittingDecision,
      ),
      createActionButton(
        "Reject",
        "Rejecting",
        requestId,
        "reject",
        submittingDecision,
      ),
    );

    item.append(title, meta, detailGrid, actions);
    container.append(item);
  }
}
