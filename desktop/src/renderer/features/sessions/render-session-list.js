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

export function renderSessionList(container, sessions) {
  container.replaceChildren();

  if (sessions.length === 0) {
    container.append(createEmptyState("No sessions available in relay snapshot."));
    return;
  }

  for (const session of sessions) {
    const item = document.createElement("li");
    item.className = "list-item";

    const title = document.createElement("div");
    title.className = "item-title";
    title.textContent = session.title || session.id || "Untitled session";

    const meta = document.createElement("div");
    meta.className = "item-meta";
    meta.append(
      createMetaPill(`status: ${session.status || "unknown"}`),
      createMetaPill(`provider: ${session.provider || "unknown"}`),
      createMetaPill(`remote: ${session.remote || "unknown"}`),
    );

    const detail = document.createElement("p");
    detail.className = "item-detail";
    detail.textContent = `session_id=${session.id || "-"}`;

    item.append(title, meta, detail);
    container.append(item);
  }
}
