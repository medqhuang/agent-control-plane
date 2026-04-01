function createMetaPill(label) {
  const pill = document.createElement("span");
  pill.className = "meta-pill";
  pill.textContent = label;
  return pill;
}

function createRemoteStatusPill(status) {
  const pill = document.createElement("span");
  pill.className = `remote-status-pill is-${status}`;
  pill.textContent = status;
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

function readServerField(server, fieldName, fallback) {
  if (!server || typeof server !== "object") {
    return fallback;
  }

  const value = server[fieldName];
  if (value === null || value === undefined) {
    return fallback;
  }

  const normalizedValue = String(value).trim();
  return normalizedValue === "" ? fallback : normalizedValue;
}

function readStatusFlag(server, flagName) {
  if (!server || typeof server !== "object") {
    return false;
  }

  const status = server.status;
  if (!status || typeof status !== "object") {
    return false;
  }

  return Boolean(status[flagName]);
}

function readStatusValue(server, fieldName, fallback) {
  if (!server || typeof server !== "object") {
    return fallback;
  }

  const status = server.status;
  if (!status || typeof status !== "object") {
    return fallback;
  }

  const value = status[fieldName];
  if (value === null || value === undefined) {
    return fallback;
  }

  const normalizedValue = String(value).trim().toLowerCase();
  return normalizedValue === "" ? fallback : normalizedValue;
}

function readProviders(server) {
  if (!server || typeof server !== "object" || !Array.isArray(server.providers)) {
    return [];
  }

  return server.providers
    .map((provider) => String(provider).trim())
    .filter((provider) => provider !== "");
}

function countByRemote(records, remoteId, predicate = () => true) {
  return records.filter((record) => {
    if (!record || typeof record !== "object") {
      return false;
    }
    const recordRemoteId = String(
      record.remote_id || record.remote || "",
    ).trim();
    return recordRemoteId === remoteId && predicate(record);
  }).length;
}

function normalizeServer(server, sessions, approvals) {
  const remoteId = readServerField(server, "remote_id", "unknown");
  const providers = readProviders(server);
  return {
    remoteId,
    displayName: readServerField(server, "display_name", remoteId),
    endpoint: readServerField(server, "endpoint", "-"),
    currentProvider: readServerField(
      server,
      "current_provider",
      providers[0] || "unknown",
    ),
    providersLabel: providers.length > 0 ? providers.join(", ") : "-",
    configured: readStatusFlag(server, "configured"),
    eventSeen: readStatusFlag(server, "event_seen"),
    writebackReady: readStatusFlag(server, "writeback_ready"),
    connectionStatus: readStatusValue(server, "connection", "unreachable"),
    lastEventAt: readServerField(server, "last_event_at", "-"),
    sessionCount: countByRemote(sessions, remoteId),
    pendingApprovalCount: countByRemote(
      approvals,
      remoteId,
      (approval) => approval.status === "pending",
    ),
  };
}

export function renderRemoteList(
  container,
  servers,
  {
    sessions = [],
    approvals = [],
  } = {},
) {
  container.replaceChildren();

  const serverItems = Array.isArray(servers) ? servers : [];
  if (serverItems.length === 0) {
    container.append(createEmptyState("No remotes discovered in relay snapshot."));
    return;
  }

  const normalizedServers = serverItems
    .map((server) => normalizeServer(server, sessions, approvals))
    .sort((left, right) => {
      const leftLabel = `${left.displayName} ${left.remoteId}`.toLowerCase();
      const rightLabel = `${right.displayName} ${right.remoteId}`.toLowerCase();
      return leftLabel.localeCompare(rightLabel);
    });

  for (const server of normalizedServers) {
    const item = document.createElement("li");
    item.className = `list-item server-card is-${server.connectionStatus}`;

    const title = document.createElement("div");
    title.className = "item-title";
    title.textContent = server.displayName;

    const meta = document.createElement("div");
    meta.className = "item-meta";
    meta.append(
      createRemoteStatusPill(server.connectionStatus),
      createMetaPill(`remote: ${server.remoteId}`),
      createMetaPill(`provider: ${server.currentProvider}`),
      createMetaPill(`sessions: ${server.sessionCount}`),
      createMetaPill(`pending: ${server.pendingApprovalCount}`),
    );
    if (server.configured) {
      meta.append(createMetaPill("configured"));
    }
    if (server.eventSeen) {
      meta.append(createMetaPill("event-seen"));
    }
    if (server.writebackReady) {
      meta.append(createMetaPill("writeback-ready"));
    }

    const detailGrid = document.createElement("div");
    detailGrid.className = "item-detail-grid";
    detailGrid.append(
      createDetailRow("endpoint", server.endpoint),
      createDetailRow("providers", server.providersLabel),
      createDetailRow("last_event_at", server.lastEventAt),
    );

    item.append(title, meta, detailGrid);
    container.append(item);
  }
}
