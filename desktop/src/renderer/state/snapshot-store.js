const EMPTY_SNAPSHOT = Object.freeze({
  sessions: [],
  approvals: [],
});

function normalizeSnapshot(snapshot) {
  if (!snapshot || typeof snapshot !== "object") {
    return {
      sessions: [],
      approvals: [],
    };
  }

  return {
    sessions: Array.isArray(snapshot.sessions) ? snapshot.sessions : [],
    approvals: Array.isArray(snapshot.approvals) ? snapshot.approvals : [],
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
  let state = {
    relayBaseUrl: "",
    snapshot: EMPTY_SNAPSHOT,
    status: "loading",
    error: null,
    lastUpdated: null,
    approvalActionByRequestId: {},
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

  function clearApprovalAction(requestId) {
    const nextActions = {
      ...state.approvalActionByRequestId,
    };
    delete nextActions[requestId];
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

  async function submitApprovalDecision(requestId, decision) {
    if (!requestId) {
      throw new Error("approval request_id is required");
    }

    if (decision !== "approve" && decision !== "reject") {
      throw new Error("approval decision must be approve or reject");
    }

    if (state.approvalActionByRequestId[requestId]) {
      return null;
    }

    setState({
      approvalActionByRequestId: {
        ...state.approvalActionByRequestId,
        [requestId]: decision,
      },
      error: null,
    });

    try {
      const payload = await window.desktopApi.submitApprovalDecision({
        requestId,
        decision,
      });

      setState({
        approvalActionByRequestId: clearApprovalAction(requestId),
        error: null,
      });
      await refresh();
      return payload;
    } catch (error) {
      setState({
        approvalActionByRequestId: clearApprovalAction(requestId),
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
