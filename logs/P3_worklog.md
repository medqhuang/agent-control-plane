# P3 Worklog

Updated: 2026-04-01
Status: Complete

This document records the work completed in `P3 Local Control MVP`.
The scope is limited to the first usable single-relay desktop control app,
including session visibility, pending approval visibility, local approval
submission, and minimal relay connection-state feedback.

## Stage Goal

P3 focuses on delivering the first local control loop that can be used without
watching the remote SSH terminal:

- establish the minimal local desktop shell under `desktop/`
- keep the desktop stack intentionally small and single-relay only
- read relay state from `GET /v1/snapshot`
- display session state and pending approvals
- submit `approve / reject` decisions through `POST /v1/approval-response`
- surface whether the local control app is connected to relay

## Completed Work

### 1. Minimal Desktop Stack Frozen

The local control app now has a stable minimal stack:

- `Electron`
- `Node.js`
- native `HTML / CSS / JavaScript`

No large frontend framework, persistence layer, tray shell, or multi-remote
aggregation was introduced in this stage.

The current structure keeps the MVP small while leaving clear extension points
for later `sessions` and `approvals` work.

### 2. Minimal Desktop Shell Added Under `desktop/`

The first runnable desktop shell was added under:

- `desktop/main.js`
- `desktop/preload.js`
- `desktop/src/index.html`
- `desktop/src/styles.css`

Current shell responsibilities:

- create one main Electron window
- expose a minimal relay API through preload
- render one local control page
- keep renderer logic isolated from direct Node integration

### 3. Single-Relay Snapshot Read Path Added

The desktop app now reads the relay state from:

- `GET /v1/snapshot`

Current single-relay behavior:

- default relay endpoint is `http://127.0.0.1:8000`
- snapshot polling is handled inside the renderer store
- success refreshes local UI state
- failure updates the local connection state

This keeps relay as the state source of truth, consistent with the existing
project rule.

### 4. Session List Added

The desktop renderer now shows the minimal session list for the current relay
snapshot.

Current session view includes:

- `id`
- `provider`
- `remote`
- `status`
- `title`

This is the first local session surface for the control plane, without adding
step-level provider details or multi-remote grouping.

The session-list renderer was later tightened inside the existing session
feature boundary to keep the display stable while still directly consuming the
current relay snapshot shape.

Current renderer behavior for the session list:

- uses `desktop/src/renderer/features/sessions/render-session-list.js`
- renders the minimal session fields explicitly from snapshot data:
  - `id`
  - `provider`
  - `remote`
  - `status`
  - `title`
- falls back to `-` or `unknown` when a session field is missing
- keeps `status` updates visible on the next snapshot refresh
- does not change approval logic, relay behavior, or shared architecture

### 5. Pending Approvals List Added

The desktop renderer now shows the minimal pending approval list from relay.

Current approval view includes:

- `summary`
- `request_id`
- `session_id`
- `kind`
- `status`

Only `pending` approvals are surfaced as actionable items in the current MVP.

### 6. Local Approve / Reject Loop Added

The desktop app now submits approval decisions back to relay through:

- `POST /v1/approval-response`

Current desktop approval behavior:

- each pending approval shows `Approve` and `Reject` buttons
- submit path uses the relay `request_id`
- in-flight approvals are disabled locally while the request is running
- after success, the renderer refreshes snapshot state

This completes the first usable local approval loop:

`desktop approvals list -> local approval submission -> relay state update -> refreshed local UI`

### 7. Relay Connection State Added

The desktop app now shows a minimal single-relay connection state.

Current connection states exposed to the user:

- `loading`
- `connected`
- `disconnected`
- `error`

Current behavior:

- successful `GET /v1/snapshot` => `connected`
- request timeout / network failure => `disconnected`
- other request failures => `error`
- relay recovery on a later poll => `connected`

This closes the basic usability gap where the local operator needed the terminal
to know whether the desktop app was actually connected to relay.

## Implementation Location

The main P3 files are:

- `desktop/main.js`
- `desktop/preload.js`
- `desktop/src/index.html`
- `desktop/src/styles.css`
- `desktop/src/renderer/app.js`
- `desktop/src/renderer/state/snapshot-store.js`
- `desktop/src/renderer/features/sessions/render-session-list.js`
- `desktop/src/renderer/features/approvals/render-approval-list.js`

## Validation Performed

The following checks were completed during P3:

- desktop main-process syntax validation
- desktop preload syntax validation
- relay snapshot read validation
- local demo `approve` path validation:
  - `approval.status: pending -> approved`
  - `session.status: waiting_approval -> running`
- local demo `reject` path validation:
  - `approval.status: pending -> rejected`
  - `session.status: waiting_approval -> failed`
- renderer connection-state transition validation:
  - `loading -> connected -> disconnected -> connected -> error`
- session list rerender validation:
  - initial session render shows `id / provider / remote / status / title`
  - refreshed snapshot updates `session.status: waiting_approval -> running`
- Electron short-start verification with relay running

Representative validation commands:

```powershell
cd C:\Users\dqhua\Desktop\agent-control-plane
.\.venv\Scripts\uvicorn.exe relay.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd C:\Users\dqhua\Desktop\agent-control-plane\desktop
npm start
```

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/approval-response" -Method Post -ContentType "application/json" -Body '{"request_id":"approval_demo_1","decision":"approve"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/approval-response" -Method Post -ContentType "application/json" -Body '{"request_id":"approval_demo_1","decision":"reject"}'
```

## Current Boundaries

The following items remain intentionally out of scope after P3:

- multi-remote aggregation
- Claude local support
- Codex local support
- tray / menu bar / desktop pet shells
- persistence
- reconnect enhancement beyond simple polling
- large state-management frameworks
- large visual redesign

P3 is a usable single-relay MVP, not a finished multi-server control console.

## Physics / Formula Note

The external working rule says each code operation should stay tightly linked
to physics formulas. The repository itself is currently defined by `README.md`
and `DEV.md` as a relay control-plane project.

The completed P3 work only touches:

- desktop shell structure
- relay snapshot reading
- local approval submission
- connection state feedback

No physical model, governing equation, boundary condition, discretization
scheme, or numerical solver logic is involved in this stage.

## Operation Trace

P3 command logs were recorded under:

`C:\Users\dqhua\AppData\Local\Temp\codex-logs\`
