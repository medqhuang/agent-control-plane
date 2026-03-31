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

function readSessionField(session, fieldName, fallback) {
  if (!session || typeof session !== "object") {
    return fallback;
  }

  const value = session[fieldName];
  if (value === null || value === undefined) {
    return fallback;
  }

  const normalizedValue = String(value).trim();
  return normalizedValue === "" ? fallback : normalizedValue;
}

function normalizeSession(session) {
  return {
    id: readSessionField(session, "id", "-"),
    provider: readSessionField(session, "provider", "unknown"),
    remote: readSessionField(session, "remote", "unknown"),
    status: readSessionField(session, "status", "unknown"),
    title: readSessionField(session, "title", "-"),
  };
}

export function renderSessionList(container, sessions) {
  container.replaceChildren();

  const sessionItems = Array.isArray(sessions) ? sessions : [];

  if (sessionItems.length === 0) {
    container.append(createEmptyState("No sessions available in relay snapshot."));
    return;
  }

  for (const rawSession of sessionItems) {
    const session = normalizeSession(rawSession);
    const item = document.createElement("li");
    item.className = "list-item";

    const title = document.createElement("div");
    title.className = "item-title";
    title.textContent = session.id;

    const meta = document.createElement("div");
    meta.className = "item-meta";
    meta.append(
      createMetaPill(`provider: ${session.provider}`),
      createMetaPill(`remote: ${session.remote}`),
      createMetaPill(`status: ${session.status}`),
    );

    const detail = document.createElement("p");
    detail.className = "item-detail";
    detail.textContent = `title: ${session.title}`;

    item.append(title, meta, detail);
    container.append(item);
  }
}
