import { renderRemoteList } from "/desktop/src/renderer/features/remotes/render-remote-list.js";
import { renderApprovalList } from "/desktop/src/renderer/features/approvals/render-approval-list.js";
import { renderSessionList } from "/desktop/src/renderer/features/sessions/render-session-list.js";
import { renderSessionDetail } from "/desktop/src/renderer/features/sessions/render-session-detail.js";

const now = "2026-04-01T20:24:56Z";

const remotes = [
  {
    remote_id: "alpha-linux",
    display_name: "Alpha Build Box",
    endpoint: "http://alpha-linux:8711",
    current_provider: "kimi",
    providers: ["kimi"],
    status: {
      configured: true,
      event_seen: true,
      writeback_ready: true,
      connection: "connected",
    },
    last_event_at: now,
  },
  {
    remote_id: "beta-linux",
    display_name: "Beta Review Box",
    endpoint: "http://beta-linux:8711",
    current_provider: "kimi",
    providers: ["kimi"],
    status: {
      configured: true,
      event_seen: true,
      writeback_ready: true,
      connection: "connected",
    },
    last_event_at: "2026-04-01T20:22:18Z",
  },
];

const sessions = [
  {
    id: "sess-ui-20260401-001",
    remote: "alpha-linux",
    remote_id: "alpha-linux",
    provider: "kimi",
    status: "active",
    title: "Prepare the release README screenshots and explain the UI flow.",
    server: remotes[0],
  },
  {
    id: "sess-ui-20260401-002",
    remote: "beta-linux",
    remote_id: "beta-linux",
    provider: "kimi",
    status: "active",
    title: "Review approval prompts before merge.",
    server: remotes[1],
  },
  {
    id: "sess-ui-20260401-003",
    remote: "beta-linux",
    remote_id: "beta-linux",
    provider: "kimi",
    status: "idle",
    title: "Summarize open release blockers for the next checkpoint.",
    server: remotes[1],
  },
];

const overviewReplyText =
  "I checked the current release surface and the safest next step is to add three UI screenshots: overview, session detail, and approval continuation. That keeps the README concrete without overclaiming unfinished roadmap items.";

const replyDraftText =
  "Turn this into a polished GitHub README section with screenshots, short captions, and a crisp explanation of the local UI workflow.";

const approvalSummary =
  "Approve running shell access to collect the current working directory before returning the answer.";

function createSessionDetail({
  session,
  hostedState,
  lastTurnStatus,
  lastTurnMessage,
  replyText,
  pendingRequestId = "",
  approvalRequest = null,
  updatedAt = now,
  turnStatus = lastTurnStatus,
}) {
  const promptResult = replyText
    ? {
      output_text: replyText,
    }
    : {};

  return {
    session,
    detail: {
      session: {
        session_id: session.id,
        title: session.title,
        provider: session.provider,
        workdir: "/srv/projects/agent-control-plane",
        turn_count: "4",
        created_at: "2026-04-01T19:58:10Z",
        updated_at: updatedAt,
        state: hostedState,
        pending_request_id: pendingRequestId,
        last_turn: {
          action: "reply",
          status: turnStatus,
          started_at: "2026-04-01T20:23:41Z",
          completed_at: turnStatus === "completed" ? updatedAt : "",
          message: lastTurnMessage,
          prompt_result: promptResult,
          approval_request: approvalRequest || undefined,
        },
      },
      provider_observation: {
        prompt_result: promptResult,
        ...(approvalRequest ? { approval_request: approvalRequest } : {}),
      },
    },
    fetchedAt: now,
  };
}

const approvalRecord = {
  request_id: "req-ui-approve-001",
  remote: "beta-linux",
  remote_id: "beta-linux",
  session_id: "sess-ui-20260401-002",
  status: "pending",
  kind: "shell",
  summary: approvalSummary,
  server: remotes[1],
};

const scenarios = {
  overview: {
    kicker: "Desktop Overview",
    eyebrow: "v1.0 Release Surface",
    subtitle: "Monitor remotes, inspect hosted sessions, and continue work from one local control surface.",
    selectedSessionKey: "alpha-linux::sess-ui-20260401-001",
    selectedSession: sessions[0],
    sessionDetail: createSessionDetail({
      session: sessions[0],
      hostedState: "idle",
      lastTurnStatus: "completed",
      lastTurnMessage:
        "Summarize the current UI release surface and identify the strongest screenshot set for the README.",
      replyText: overviewReplyText,
      updatedAt: "2026-04-01T20:24:56Z",
    }),
    sessionReplyDraft: "",
    sessionReplyProgress: {
      phase: "completed",
      completedAt: "2026-04-01T20:24:56Z",
      turnStatus: "completed",
    },
    approvals: [approvalRecord],
    sessionApproval: null,
  },
  reply: {
    kicker: "Session Detail",
    eyebrow: "Reply Continuation",
    subtitle: "Open a hosted session, inspect the latest output, and send the next instruction from the local desktop.",
    selectedSessionKey: "alpha-linux::sess-ui-20260401-001",
    selectedSession: sessions[0],
    sessionDetail: createSessionDetail({
      session: sessions[0],
      hostedState: "idle",
      lastTurnStatus: "completed",
      lastTurnMessage:
        "Draft a concise README section that explains the local UI workflow without sounding internal.",
      replyText:
        "Here is a tighter README section: show the overview, show the session detail, and explain that reply and approval happen in the same local UI.",
      updatedAt: "2026-04-01T20:26:10Z",
    }),
    sessionReplyDraft: replyDraftText,
    sessionReplyProgress: {
      phase: "completed",
      completedAt: "2026-04-01T20:26:10Z",
      turnStatus: "completed",
    },
    approvals: [],
    sessionApproval: null,
  },
  approval: {
    kicker: "Approval Continuation",
    eyebrow: "P7-D Closure",
    subtitle: "When a reply pauses for approval, the decision and the result continuation stay in the same UI context.",
    selectedSessionKey: "beta-linux::sess-ui-20260401-002",
    selectedSession: sessions[1],
    sessionDetail: createSessionDetail({
      session: sessions[1],
      hostedState: "approval_pending",
      lastTurnStatus: "approval_pending",
      lastTurnMessage:
        "Use the shell tool to run pwd and return only the absolute path. Do not answer from memory.",
      replyText: "",
      pendingRequestId: approvalRecord.request_id,
      approvalRequest: {
        request_id: approvalRecord.request_id,
        kind: "shell",
        summary: approvalSummary,
      },
      updatedAt: "2026-04-01T20:27:18Z",
      turnStatus: "approval_pending",
    }),
    sessionReplyDraft: "",
    sessionReplyProgress: {
      phase: "approval_pending",
      requestId: approvalRecord.request_id,
      turnStatus: "approval_pending",
    },
    approvals: [approvalRecord],
    sessionApproval: approvalRecord,
  },
};

const scenarioName = new URLSearchParams(window.location.search).get("state") || "overview";
const scenario = scenarios[scenarioName] || scenarios.overview;

const elements = {
  showcaseKicker: document.querySelector("#showcase-kicker"),
  showcaseEyebrow: document.querySelector("#showcase-eyebrow"),
  showcaseSubtitle: document.querySelector("#showcase-subtitle"),
  relayEndpoint: document.querySelector("#relay-endpoint"),
  connectionStatus: document.querySelector("#connection-status"),
  lastUpdated: document.querySelector("#last-updated"),
  errorMessage: document.querySelector("#error-message"),
  remoteCount: document.querySelector("#remote-count"),
  sessionCount: document.querySelector("#session-count"),
  approvalCount: document.querySelector("#approval-count"),
  serverList: document.querySelector("#server-list"),
  sessionList: document.querySelector("#session-list"),
  sessionDetail: document.querySelector("#session-detail"),
  approvalList: document.querySelector("#approval-list"),
};

function formatDateTime(value) {
  return new Date(value).toLocaleString();
}

elements.showcaseKicker.textContent = scenario.kicker;
elements.showcaseEyebrow.textContent = scenario.eyebrow;
elements.showcaseSubtitle.textContent = scenario.subtitle;
elements.relayEndpoint.textContent = "http://127.0.0.1:8000";
elements.connectionStatus.textContent = "Connected";
elements.connectionStatus.className = "value status-badge is-connected";
elements.lastUpdated.textContent = formatDateTime(now);
elements.errorMessage.hidden = true;
elements.remoteCount.textContent = String(remotes.length);
elements.sessionCount.textContent = String(sessions.length);
elements.approvalCount.textContent = String(scenario.approvals.length);

renderRemoteList(elements.serverList, remotes, {
  sessions,
  approvals: scenario.approvals,
});
renderSessionList(elements.sessionList, sessions, {
  selectedSessionKey: scenario.selectedSessionKey,
});
renderSessionDetail(elements.sessionDetail, {
  selectedSession: scenario.selectedSession,
  sessionDetail: scenario.sessionDetail,
  sessionDetailLoading: false,
  sessionDetailError: null,
  sessionReplyDraft: scenario.sessionReplyDraft,
  sessionReplySubmitting: false,
  sessionReplyError: "",
  sessionReplyProgress: scenario.sessionReplyProgress,
  sessionApproval: scenario.sessionApproval,
  sessionApprovalSubmittingDecision: "",
});
renderApprovalList(elements.approvalList, scenario.approvals, {
  approvalActionByKey: {},
  contextApprovalKey: scenario.sessionApproval
    ? `${scenario.sessionApproval.remote_id}::${scenario.sessionApproval.request_id}`
    : "",
});

window.__showcaseReady = true;
