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

function buildApprovalActionKey(requestId, remoteId = "") {
  return `${String(remoteId || "").trim()}::${String(requestId || "").trim()}`;
}

function createGroupHeader(title, subtitle, count) {
  const header = document.createElement("div");
  header.className = "group-header";

  const heading = document.createElement("div");
  heading.className = "group-heading";

  const groupTitle = document.createElement("div");
  groupTitle.className = "group-title";
  groupTitle.textContent = title;

  const groupSubtitle = document.createElement("p");
  groupSubtitle.className = "group-subtitle";
  groupSubtitle.textContent = subtitle;

  const countPill = document.createElement("span");
  countPill.className = "count-pill group-count-pill";
  countPill.textContent = String(count);

  heading.append(groupTitle, groupSubtitle);
  header.append(heading, countPill);
  return header;
}

function readApprovalField(approval, fieldName, fallback) {
  if (!approval || typeof approval !== "object") {
    return fallback;
  }

  const value = approval[fieldName];
  if (value === null || value === undefined) {
    return fallback;
  }

  const normalizedValue = String(value).trim();
  return normalizedValue === "" ? fallback : normalizedValue;
}

function normalizeApproval(approval) {
  const remoteId = readApprovalField(
    approval,
    "remote_id",
    readApprovalField(approval, "remote", "unknown"),
  );
  const server = approval && typeof approval === "object"
    ? approval.server
    : null;
  const remoteLabel = server && typeof server === "object"
    ? readApprovalField(server, "display_name", remoteId)
    : remoteId;
  return {
    requestId: readApprovalField(approval, "request_id", ""),
    remoteId,
    remoteLabel,
    sessionId: readApprovalField(approval, "session_id", "-"),
    status: readApprovalField(approval, "status", "unknown"),
    kind: readApprovalField(approval, "kind", "unknown"),
    summary: readApprovalField(approval, "summary", "Approval request"),
  };
}

function createActionButton(
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
  button.textContent = isSubmitting
    ? `${verb}...`
    : label;
  return button;
}

export function renderApprovalList(
  container,
  approvals,
  {
    approvalActionByKey = {},
  } = {},
) {
  container.replaceChildren();

  if (approvals.length === 0) {
    container.append(createEmptyState("No pending approvals in relay snapshot."));
    return;
  }

  const groupedApprovals = new Map();
  for (const rawApproval of approvals) {
    const approval = normalizeApproval(rawApproval);
    if (!groupedApprovals.has(approval.remoteId)) {
      groupedApprovals.set(approval.remoteId, {
        remoteId: approval.remoteId,
        remoteLabel: approval.remoteLabel,
        items: [],
      });
    }
    groupedApprovals.get(approval.remoteId).items.push(approval);
  }

  const groups = [...groupedApprovals.values()].sort((left, right) => {
    const leftLabel = `${left.remoteLabel} ${left.remoteId}`.toLowerCase();
    const rightLabel = `${right.remoteLabel} ${right.remoteId}`.toLowerCase();
    return leftLabel.localeCompare(rightLabel);
  });

  for (const group of groups) {
    const groupSection = document.createElement("li");
    groupSection.className = "group-section";
    groupSection.append(
      createGroupHeader(
        group.remoteLabel,
        `remote_id: ${group.remoteId}`,
        group.items.length,
      ),
    );

    const groupList = document.createElement("ul");
    groupList.className = "group-item-list";

    for (const approval of group.items) {
      const approvalKey = buildApprovalActionKey(
        approval.requestId,
        approval.remoteId,
      );
      const submittingDecision = approvalActionByKey[approvalKey];
      const item = document.createElement("li");
      item.className = submittingDecision
        ? "list-item is-busy"
        : "list-item";

      const title = document.createElement("div");
      title.className = "item-title";
      title.textContent = approval.summary || approval.requestId || "Approval request";

      const meta = document.createElement("div");
      meta.className = "item-meta";
      meta.append(
        createMetaPill(`status: ${approval.status}`),
        createMetaPill(`kind: ${approval.kind}`),
        createMetaPill(`remote: ${approval.remoteId}`),
        createMetaPill(`session: ${approval.sessionId}`),
      );

      const detailGrid = document.createElement("div");
      detailGrid.className = "item-detail-grid";
      detailGrid.append(
        createDetailRow("request_id", approval.requestId),
        createDetailRow("remote_id", approval.remoteId),
        createDetailRow("session_id", approval.sessionId),
      );

      const actions = document.createElement("div");
      actions.className = "approval-actions";
      actions.append(
        createActionButton(
          "Approve",
          "Approving",
          approval.requestId,
          approval.remoteId,
          "approve",
          submittingDecision,
        ),
        createActionButton(
          "Reject",
          "Rejecting",
          approval.requestId,
          approval.remoteId,
          "reject",
          submittingDecision,
        ),
      );

      item.append(title, meta, detailGrid, actions);
      groupList.append(item);
    }

    groupSection.append(groupList);
    container.append(groupSection);
  }
}
