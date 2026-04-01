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
  const remoteId = readSessionField(
    session,
    "remote_id",
    readSessionField(session, "remote", "unknown"),
  );
  const server = session && typeof session === "object"
    ? session.server
    : null;
  const remoteLabel = server && typeof server === "object"
    ? readSessionField(server, "display_name", remoteId)
    : remoteId;
  return {
    id: readSessionField(session, "id", "-"),
    provider: readSessionField(session, "provider", "unknown"),
    remote: readSessionField(session, "remote", remoteId),
    remoteId,
    remoteLabel,
    status: readSessionField(session, "status", "unknown"),
    title: readSessionField(session, "title", "-"),
  };
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

export function renderSessionList(
  container,
  sessions,
  {
    selectedSessionKey = "",
  } = {},
) {
  container.replaceChildren();

  const sessionItems = Array.isArray(sessions) ? sessions : [];

  if (sessionItems.length === 0) {
    container.append(createEmptyState("No sessions available in relay snapshot."));
    return;
  }

  const groupedSessions = new Map();
  for (const rawSession of sessionItems) {
    const session = normalizeSession(rawSession);
    const groupKey = session.remoteId;
    if (!groupedSessions.has(groupKey)) {
      groupedSessions.set(groupKey, {
        remoteId: session.remoteId,
        remoteLabel: session.remoteLabel,
        items: [],
      });
    }
    groupedSessions.get(groupKey).items.push(session);
  }

  const groups = [...groupedSessions.values()].sort((left, right) => {
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

    for (const session of group.items) {
      const sessionKey = `${session.remoteId}::${session.id}`;
      const isSelected = sessionKey === selectedSessionKey;
      const item = document.createElement("li");
      item.className = isSelected
        ? "list-item is-selected"
        : "list-item";

      const button = document.createElement("button");
      button.type = "button";
      button.className = "session-card-button";
      button.dataset.sessionId = session.id;
      button.dataset.remoteId = session.remoteId;
      button.setAttribute("aria-pressed", String(isSelected));

      const title = document.createElement("div");
      title.className = "item-title";
      title.textContent = session.id;

      const meta = document.createElement("div");
      meta.className = "item-meta";
      meta.append(
        createMetaPill(`provider: ${session.provider}`),
        createMetaPill(`remote: ${session.remoteId}`),
        createMetaPill(`status: ${session.status}`),
      );

      const detail = document.createElement("p");
      detail.className = "item-detail";
      detail.textContent = `title: ${session.title}`;

      button.append(title, meta, detail);
      item.append(button);
      groupList.append(item);
    }

    groupSection.append(groupList);
    container.append(groupSection);
  }
}
