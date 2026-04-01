const EMPTY_SNAPSHOT = Object.freeze({
  servers: [],
  sessions: [],
  approvals: [],
});

function normalizeSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object") {
    return {
      servers: [],
      sessions: [],
      approvals: [],
    };
  }

  return {
    servers: Array.isArray(snapshot.servers) ? snapshot.servers : [],
    sessions: Array.isArray(snapshot.sessions) ? snapshot.sessions : [],
    approvals: Array.isArray(snapshot.approvals) ? snapshot.approvals : [],
  };
}

function buildApprovalActionKey(requestId, remoteId = "") {
  return `${String(remoteId || "").trim()}::${String(requestId || "").trim()}`;
}

function buildSessionKey(sessionId, remoteId = "") {
  return `${String(remoteId || "").trim()}::${String(sessionId || "").trim()}`;
}

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

function buildSessionKeyFromRecord(session) {
  return buildSessionKey(
    readRecordField(session, "id", ""),
    readRecordField(
      session,
      "remote_id",
      readRecordField(session, "remote", ""),
    ),
  );
}

function normalizeSessionIdentity(sessionId, remoteId = "") {
  const normalizedSessionId = String(sessionId || "").trim();
  const normalizedRemoteId = String(remoteId || "").trim();

  if (normalizedSessionId === "") {
    throw new Error("session_id is required");
  }

  return {
    sessionId: normalizedSessionId,
    remoteId: normalizedRemoteId,
  };
}

function normalizeSessionDetail(detail) {
  if (!detail || typeof detail !== "object") {
    return null;
  }

  return {
    session: detail.session && typeof detail.session === "object"
      ? detail.session
      : {},
    detail: detail.detail && typeof detail.detail === "object"
      ? detail.detail
      : {},
    proxy: detail.proxy && typeof detail.proxy === "object"
      ? detail.proxy
      : {},
    fetchedAt: typeof detail.fetched_at === "string"
      ? detail.fetched_at
      : "",
  };
}

function getConnectionStatusForRefreshError(error) {
  const message = error instanceof Error ? error.message : String(error);
  const normalizedMessage = message.toLowerCase();

  if (
    normalizedMessage.includes("fetch failed") ||
    normalizedMessage.includes("timed out") ||
    normalizedMessage.includes("refused") ||
    normalizedMessage.includes("network")
  ) {
    return "disconnected";
  }

  return "error";
}

export function createSnapshotStore() {
  const listeners = new Set();
  let refreshPromise = null;
  let sessionDetailPromise = null;
  let sessionDetailPromiseKey = "";
  let sessionDetailRequestToken = 0;
  let state = {
    relayBaseUrl: "",
    snapshot: EMPTY_SNAPSHOT,
    status: "loading",
    error: null,
    lastUpdated: null,
    approvalActionByKey: {},
    selectedSessionKey: "",
    selectedSession: null,
    sessionDetail: null,
    sessionDetailLoading: false,
    sessionDetailError: null,
  };

  function emit() {
    for (const listener of listeners) {
      listener(state);
    }
  }

  function setState(partialState) {
    state = {
      ...state,
      ...partialState,
    };
    emit();
  }

  function clearApprovalAction(approvalKey) {
    const nextActions = {
      ...state.approvalActionByKey,
    };
    delete nextActions[approvalKey];
    return nextActions;
  }

  function clearSelectedSession() {
    setState({
      selectedSessionKey: "",
      selectedSession: null,
      sessionDetail: null,
      sessionDetailLoading: false,
      sessionDetailError: null,
    });
  }

  async function refreshSessionDetail(
    sessionIdentity = state.selectedSession,
    {
      preserveData = true,
      surfaceError = true,
    } = {},
  ) {
    if (!sessionIdentity) {
      return null;
    }

    const normalizedSession = normalizeSessionIdentity(
      sessionIdentity.sessionId,
      sessionIdentity.remoteId,
    );
    const sessionKey = buildSessionKey(
      normalizedSession.sessionId,
      normalizedSession.remoteId,
    );

    if (sessionDetailPromise && sessionDetailPromiseKey === sessionKey) {
      return sessionDetailPromise;
    }

    const requestToken = ++sessionDetailRequestToken;
    sessionDetailPromiseKey = sessionKey;

    setState({
      selectedSessionKey: sessionKey,
      selectedSession: normalizedSession,
      sessionDetail: preserveData && state.selectedSessionKey === sessionKey
        ? state.sessionDetail
        : null,
      sessionDetailLoading: true,
      sessionDetailError: null,
    });

    sessionDetailPromise = (async () => {
      try {
        const payload = await window.desktopApi.getSessionDetail({
          sessionId: normalizedSession.sessionId,
          remoteId: normalizedSession.remoteId,
        });

        if (
          requestToken !== sessionDetailRequestToken ||
          state.selectedSessionKey !== sessionKey
        ) {
          return payload;
        }

        setState({
          relayBaseUrl: payload.relayBaseUrl || state.relayBaseUrl,
          sessionDetail: normalizeSessionDetail(payload.detail),
          sessionDetailLoading: false,
          sessionDetailError: null,
        });

        return payload;
      } catch (error) {
        if (
          requestToken === sessionDetailRequestToken &&
          state.selectedSessionKey === sessionKey
        ) {
          setState({
            sessionDetailLoading: false,
            sessionDetailError: error instanceof Error ? error.message : String(error),
          });
        }

        if (surfaceError) {
          throw error;
        }

        return null;
      } finally {
        if (sessionDetailPromiseKey === sessionKey) {
          sessionDetailPromise = null;
          sessionDetailPromiseKey = "";
        }
      }
    })();

    return sessionDetailPromise;
  }

  async function refresh() {
    if (refreshPromise) {
      return refreshPromise;
    }

    setState({
      status: "loading",
      error: null,
    });

    refreshPromise = (async () => {
      try {
        const payload = await window.desktopApi.getSnapshot();
        const normalizedSnapshot = normalizeSnapshot(payload.snapshot);
        const selectedSession = state.selectedSession;
        const hasSelectedSession = Boolean(selectedSession);
        const selectedSessionStillPresent = hasSelectedSession
          ? normalizedSnapshot.sessions.some((session) =>
            buildSessionKeyFromRecord(session) === buildSessionKey(
              selectedSession.sessionId,
              selectedSession.remoteId,
            ))
          : false;

        setState({
          relayBaseUrl: payload.relayBaseUrl,
          snapshot: normalizedSnapshot,
          status: "connected",
          error: null,
          lastUpdated: payload.fetchedAt,
          ...(hasSelectedSession && !selectedSessionStillPresent
            ? {
              selectedSessionKey: "",
              selectedSession: null,
              sessionDetail: null,
              sessionDetailLoading: false,
              sessionDetailError: null,
            }
            : {}),
        });

        if (hasSelectedSession && selectedSessionStillPresent) {
          void refreshSessionDetail(selectedSession, {
            preserveData: true,
            surfaceError: false,
          }).catch(() => {});
        }

        return payload;
      } catch (error) {
        setState({
          status: getConnectionStatusForRefreshError(error),
          error: error instanceof Error ? error.message : String(error),
        });
        throw error;
      } finally {
        refreshPromise = null;
      }
    })();

    return refreshPromise;
  }

  async function submitApprovalDecision(requestId, remoteId, decision) {
    let nextRemoteId = remoteId;
    let nextDecision = decision;
    if (
      nextDecision === undefined &&
      (nextRemoteId === "approve" || nextRemoteId === "reject")
    ) {
      nextDecision = nextRemoteId;
      nextRemoteId = "";
    }

    if (!requestId) {
      throw new Error("approval request_id is required");
    }

    if (nextDecision !== "approve" && nextDecision !== "reject") {
      throw new Error("approval decision must be approve or reject");
    }

    if (nextRemoteId !== undefined && typeof nextRemoteId !== "string") {
      throw new Error("approval remote_id must be a string when provided");
    }

    const normalizedRemoteId = typeof nextRemoteId === "string"
      ? nextRemoteId.trim()
      : "";
    const approvalKey = buildApprovalActionKey(requestId, normalizedRemoteId);

    if (state.approvalActionByKey[approvalKey]) {
      return null;
    }

    setState({
      approvalActionByKey: {
        ...state.approvalActionByKey,
        [approvalKey]: nextDecision,
      },
      error: null,
    });

    try {
      const payload = await window.desktopApi.submitApprovalDecision({
        requestId,
        remoteId: normalizedRemoteId,
        decision: nextDecision,
      });

      setState({
        approvalActionByKey: clearApprovalAction(approvalKey),
        error: null,
      });
      await refresh();
      return payload;
    } catch (error) {
      setState({
        approvalActionByKey: clearApprovalAction(approvalKey),
        error: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
  }

  async function selectSession(sessionId, remoteId = "") {
    const sessionIdentity = normalizeSessionIdentity(sessionId, remoteId);
    return refreshSessionDetail(sessionIdentity, {
      preserveData: false,
      surfaceError: true,
    });
  }

  return {
    getState() {
      return state;
    },

    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },

    refresh,
    selectSession,
    clearSelectedSession,
    submitApprovalDecision,
  };
}
