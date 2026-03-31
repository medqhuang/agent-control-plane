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

export function renderApprovalList(container, approvals) {
  container.replaceChildren();

  if (approvals.length === 0) {
    container.append(createEmptyState("No approvals available in relay snapshot."));
    return;
  }

  for (const approval of approvals) {
    const item = document.createElement("li");
    item.className = "list-item";

    const title = document.createElement("div");
    title.className = "item-title";
    title.textContent = approval.summary || approval.request_id || "Approval request";

    const meta = document.createElement("div");
    meta.className = "item-meta";
    meta.append(
      createMetaPill(`status: ${approval.status || "unknown"}`),
      createMetaPill(`kind: ${approval.kind || "unknown"}`),
      createMetaPill(`session: ${approval.session_id || "-"}`),
    );

    const detail = document.createElement("p");
    detail.className = "item-detail";
    detail.textContent = `request_id=${approval.request_id || "-"}`;

    item.append(title, meta, detail);
    container.append(item);
  }
}
