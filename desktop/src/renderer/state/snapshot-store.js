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

export function createSnapshotStore() {
  const listeners = new Set();
  let state = {
    relayBaseUrl: "",
    snapshot: EMPTY_SNAPSHOT,
    status: "idle",
    error: null,
    lastUpdated: null,
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

    async refresh() {
      const nextStatus = state.status === "idle" ? "loading" : "refreshing";
      setState({
        status: nextStatus,
        error: null,
      });

      try {
        const payload = await window.desktopApi.getSnapshot();

        setState({
          relayBaseUrl: payload.relayBaseUrl,
          snapshot: normalizeSnapshot(payload.snapshot),
          status: "ready",
          error: null,
          lastUpdated: payload.fetchedAt,
        });
      } catch (error) {
        setState({
          status: "error",
          error: error instanceof Error ? error.message : String(error),
        });
      }
    },
  };
}
