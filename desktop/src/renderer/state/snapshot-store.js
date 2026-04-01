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

function clearRecordKey(record, recordKey) {
  const nextRecord = {
    ...record,
  };
  delete nextRecord[recordKey];
  return nextRecord;
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

function normalizeSessionInteractionDetail(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  return {
    session: payload.session && typeof payload.session === "object"
      ? payload.session
      : {},
    detail: payload.detail && typeof payload.detail === "object"
      ? payload.detail
      : payload.reply && typeof payload.reply === "object"
        ? payload.reply
        : {},
    proxy: payload.proxy && typeof payload.proxy === "object"
      ? payload.proxy
      : {},
    fetchedAt: typeof payload.fetched_at === "string"
      ? payload.fetched_at
      : typeof payload.relayed_at === "string"
        ? payload.relayed_at
        : "",
  };
}

function readHostedSessionFromDetail(sessionDetail) {
  if (!sessionDetail || typeof sessionDetail !== "object") {
    return {};
  }

  const detailPayload = sessionDetail.detail;
  if (!detailPayload || typeof detailPayload !== "object") {
    return {};
  }

  const hostedSession = detailPayload.session;
  return hostedSession && typeof hostedSession === "object"
    ? hostedSession
    : {};
}

function readLastTurnFromDetail(sessionDetail) {
  const hostedSession = readHostedSessionFromDetail(sessionDetail);
  const lastTurn = hostedSession.last_turn;
  return lastTurn && typeof lastTurn === "object"
    ? lastTurn
    : {};
}

function inferReplyPhase(sessionDetail, expectedMessage) {
  const normalizedExpectedMessage = String(expectedMessage || "").trim();
  if (normalizedExpectedMessage === "") {
    return "";
  }

  const hostedSession = readHostedSessionFromDetail(sessionDetail);
  const lastTurn = readLastTurnFromDetail(sessionDetail);
  const lastTurnMessage = readRecordField(lastTurn, "message", "");
  if (lastTurnMessage !== normalizedExpectedMessage) {
    return "";
  }

  const hostedState = readRecordField(hostedSession, "state", "");
  const lastTurnStatus = readRecordField(lastTurn, "status", "");
  if (hostedState === "approval_pending" || lastTurnStatus === "approval_pending") {
    return "approval_pending";
  }
  if (hostedState === "running" || lastTurnStatus === "running") {
    return "running";
  }
  if (
    lastTurnStatus !== "" ||
    readRecordField(lastTurn, "completed_at", "") !== ""
  ) {
    return "completed";
  }

  return "";
}

function readReplyTurnStatus(sessionDetail) {
  const lastTurn = readLastTurnFromDetail(sessionDetail);
  return readRecordField(lastTurn, "status", "");
}

function readReplyCompletedAt(sessionDetail) {
  const lastTurn = readLastTurnFromDetail(sessionDetail);
  const completedAt = readRecordField(lastTurn, "completed_at", "");
  if (completedAt !== "") {
    return completedAt;
  }

  const hostedSession = readHostedSessionFromDetail(sessionDetail);
  return readRecordField(hostedSession, "updated_at", "");
}

function readHostedSessionState(sessionDetail) {
  const hostedSession = readHostedSessionFromDetail(sessionDetail);
  return readRecordField(hostedSession, "state", "");
}

function readPendingRequestId(sessionDetail) {
  const hostedSession = readHostedSessionFromDetail(sessionDetail);
  return readRecordField(hostedSession, "pending_request_id", "");
}

function findApprovalRecord(approvals, requestId, remoteId = "") {
  const normalizedRequestId = String(requestId || "").trim();
  const normalizedRemoteId = String(remoteId || "").trim();
  if (normalizedRequestId === "") {
    return null;
  }

  for (const approval of approvals) {
    if (!approval || typeof approval !== "object") {
      continue;
    }

    const approvalRequestId = readRecordField(approval, "request_id", "");
    const approvalRemoteId = readRecordField(
      approval,
      "remote_id",
      readRecordField(approval, "remote", ""),
    );
    if (
      approvalRequestId === normalizedRequestId &&
      approvalRemoteId === normalizedRemoteId
    ) {
      return approval;
    }
  }

  return null;
}

function resolveSessionIdentityForApproval(approval, fallbackSession = null) {
  if (approval && typeof approval === "object") {
    const sessionId = readRecordField(approval, "session_id", "");
    const remoteId = readRecordField(
      approval,
      "remote_id",
      readRecordField(approval, "remote", ""),
    );
    if (sessionId !== "") {
      return {
        sessionId,
        remoteId,
      };
    }
  }

  if (fallbackSession && typeof fallbackSession === "object") {
    return normalizeSessionIdentity(
      fallbackSession.sessionId,
      fallbackSession.remoteId,
    );
  }

  return null;
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
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
    sessionReplyDraftByKey: {},
    sessionReplySubmittingKey: "",
    sessionReplyErrorByKey: {},
    sessionReplyProgressByKey: {},
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
    return clearRecordKey(state.approvalActionByKey, approvalKey);
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

  function setSessionReplyProgress(sessionKey, progressPatch) {
    const currentProgress = state.sessionReplyProgressByKey[sessionKey] || {};
    setState({
      sessionReplyProgressByKey: {
        ...state.sessionReplyProgressByKey,
        [sessionKey]: {
          ...currentProgress,
          ...progressPatch,
        },
      },
    });
  }

  async function continueSessionAfterApproval({
    requestId,
    sessionIdentity,
  }) {
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
    const normalizedRequestId = String(requestId || "").trim();
    const deadline = Date.now() + 95000;

    for (;;) {
      await delay(350);

      const detailPayload = await refreshSessionDetail(normalizedSession, {
        preserveData: true,
        surfaceError: false,
        markLoading: false,
      });
      const observedDetail = detailPayload
        ? normalizeSessionInteractionDetail(detailPayload.detail)
        : state.selectedSessionKey === sessionKey
          ? state.sessionDetail
          : null;
      const hostedState = readHostedSessionState(observedDetail);
      const pendingRequestId = readPendingRequestId(observedDetail);
      const completedAt = readReplyCompletedAt(observedDetail);
      const turnStatus = readReplyTurnStatus(observedDetail);

      if (
        hostedState === "approval_pending" ||
        pendingRequestId === normalizedRequestId
      ) {
        setSessionReplyProgress(sessionKey, {
          phase: "approval_pending",
          requestId: normalizedRequestId,
        });
        continue;
      }

      if (hostedState === "running") {
        setSessionReplyProgress(sessionKey, {
          phase: "running",
          requestId: normalizedRequestId,
        });
        continue;
      }

      if (hostedState === "failed") {
        setSessionReplyProgress(sessionKey, {
          phase: "failed",
          requestId: normalizedRequestId,
          completedAt: completedAt || "",
          turnStatus,
        });
        return observedDetail;
      }

      if (completedAt !== "" || hostedState === "idle" || hostedState === "finished") {
        setSessionReplyProgress(sessionKey, {
          phase: "completed",
          requestId: normalizedRequestId,
          completedAt: completedAt || "",
          turnStatus,
        });
        return observedDetail;
      }

      if (Date.now() >= deadline) {
        return observedDetail;
      }
    }
  }

  async function refreshSessionDetail(
    sessionIdentity = state.selectedSession,
    {
      preserveData = true,
      surfaceError = true,
      markLoading = true,
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
      sessionDetailLoading: markLoading,
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
          sessionDetail: normalizeSessionInteractionDetail(payload.detail),
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
    const matchedApproval = findApprovalRecord(
      state.snapshot.approvals,
      requestId,
      normalizedRemoteId,
    );
    const targetSession = resolveSessionIdentityForApproval(
      matchedApproval,
      state.selectedSession,
    );
    const targetSessionKey = targetSession
      ? buildSessionKey(targetSession.sessionId, targetSession.remoteId)
      : "";

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
      if (targetSession) {
        setSessionReplyProgress(targetSessionKey, {
          phase: "running",
          requestId,
        });
        await continueSessionAfterApproval({
          requestId,
          sessionIdentity: targetSession,
        });
        void refresh().catch(() => {});
      }
      return payload;
    } catch (error) {
      setState({
        approvalActionByKey: clearApprovalAction(approvalKey),
        error: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
  }

  function setSessionReplyDraft(sessionId, remoteId = "", message = "") {
    const normalizedSession = normalizeSessionIdentity(sessionId, remoteId);
    const sessionKey = buildSessionKey(
      normalizedSession.sessionId,
      normalizedSession.remoteId,
    );

    setState({
      sessionReplyDraftByKey: {
        ...state.sessionReplyDraftByKey,
        [sessionKey]: typeof message === "string" ? message : "",
      },
      sessionReplyErrorByKey: clearRecordKey(state.sessionReplyErrorByKey, sessionKey),
    });
  }

  async function submitSessionReply(sessionId, remoteId = "", message) {
    const normalizedSession = normalizeSessionIdentity(sessionId, remoteId);
    const sessionKey = buildSessionKey(
      normalizedSession.sessionId,
      normalizedSession.remoteId,
    );
    const draftMessage = typeof message === "string"
      ? message
      : state.sessionReplyDraftByKey[sessionKey] || "";
    const normalizedMessage = draftMessage.trim();

    if (normalizedMessage === "") {
      throw new Error("reply message is required");
    }

    if (state.sessionReplySubmittingKey === sessionKey) {
      return null;
    }

    const startedAt = new Date().toISOString();
    setState({
      sessionReplySubmittingKey: sessionKey,
      sessionReplyErrorByKey: clearRecordKey(state.sessionReplyErrorByKey, sessionKey),
      sessionReplyProgressByKey: {
        ...state.sessionReplyProgressByKey,
        [sessionKey]: {
          message: normalizedMessage,
          phase: "sending",
          startedAt,
          completedAt: "",
          turnStatus: "",
        },
      },
    });

    try {
      const progressObserver = (async () => {
        while (state.sessionReplySubmittingKey === sessionKey) {
          await delay(350);
          if (state.sessionReplySubmittingKey !== sessionKey) {
            return;
          }

          const detailPayload = await refreshSessionDetail(normalizedSession, {
            preserveData: true,
            surfaceError: false,
            markLoading: false,
          });
          const observedDetail = detailPayload
            ? normalizeSessionInteractionDetail(detailPayload.detail)
            : state.selectedSessionKey === sessionKey
              ? state.sessionDetail
              : null;
          const observedPhase = inferReplyPhase(observedDetail, normalizedMessage);

          if (observedPhase === "approval_pending") {
            setSessionReplyProgress(sessionKey, {
              phase: "approval_pending",
              requestId: readPendingRequestId(observedDetail) || "",
            });
            continue;
          }

          if (observedPhase === "running") {
            setSessionReplyProgress(sessionKey, {
              phase: "running",
            });
            continue;
          }

          if (observedPhase === "completed") {
            setSessionReplyProgress(sessionKey, {
              phase: "completed",
              completedAt: readReplyCompletedAt(observedDetail) || "",
              turnStatus: readReplyTurnStatus(observedDetail) || "",
            });
          }
        }
      })().catch(() => {});

      const payload = await window.desktopApi.submitSessionReply({
        sessionId: normalizedSession.sessionId,
        remoteId: normalizedSession.remoteId,
        message: normalizedMessage,
      });
      const replyDetail = normalizeSessionInteractionDetail(payload.reply);
      const completedAt = payload.respondedAt ||
        readReplyCompletedAt(replyDetail) ||
        startedAt;
      const replyPhase = inferReplyPhase(replyDetail, normalizedMessage);
      const pendingRequestId = readPendingRequestId(replyDetail);

      setState({
        relayBaseUrl: payload.relayBaseUrl || state.relayBaseUrl,
        ...(state.selectedSessionKey === sessionKey
          ? {
            sessionDetail: replyDetail,
            sessionDetailLoading: false,
            sessionDetailError: null,
          }
          : {}),
        sessionReplyDraftByKey: {
          ...state.sessionReplyDraftByKey,
          [sessionKey]: "",
        },
        sessionReplySubmittingKey: "",
        sessionReplyErrorByKey: clearRecordKey(state.sessionReplyErrorByKey, sessionKey),
        sessionReplyProgressByKey: {
          ...state.sessionReplyProgressByKey,
          [sessionKey]: {
            message: normalizedMessage,
            phase: replyPhase === "approval_pending" ? "approval_pending" : "completed",
            startedAt,
            completedAt: replyPhase === "approval_pending" ? "" : completedAt,
            turnStatus: readReplyTurnStatus(replyDetail) || "",
            requestId: pendingRequestId,
          },
        },
      });
      await progressObserver;
      if (replyPhase === "approval_pending" && pendingRequestId !== "") {
        await refresh();
      } else {
        await refreshSessionDetail(normalizedSession, {
          preserveData: true,
          surfaceError: false,
          markLoading: false,
        });
      }
      void refresh().catch(() => {});
      return payload;
    } catch (error) {
      setState({
        sessionReplySubmittingKey: "",
        sessionReplyErrorByKey: {
          ...state.sessionReplyErrorByKey,
          [sessionKey]: error instanceof Error ? error.message : String(error),
        },
        sessionReplyProgressByKey: clearRecordKey(state.sessionReplyProgressByKey, sessionKey),
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
    setSessionReplyDraft,
    submitSessionReply,
    submitApprovalDecision,
  };
}
