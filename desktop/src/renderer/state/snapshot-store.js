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
  let state = {
    relayBaseUrl: "",
    snapshot: EMPTY_SNAPSHOT,
    status: "loading",
    error: null,
    lastUpdated: null,
    approvalActionByKey: {},
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

        setState({
          relayBaseUrl: payload.relayBaseUrl,
          snapshot: normalizeSnapshot(payload.snapshot),
          status: "connected",
          error: null,
          lastUpdated: payload.fetchedAt,
        });

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
    submitApprovalDecision,
  };
}
