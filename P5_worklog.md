# P5 Worklog

Updated: 2026-04-01
Status: Complete

This document records the closure work completed in `P5 Multi-Remote`.
The scope is limited to extending the single-remote control-plane baseline into a
minimal multi-remote aggregation path without claiming that reconnect, persistence,
or full recovery has already been implemented.

## Stage Goal

P5 focused on turning the single-remote hosted-session control plane into a minimal
multi-remote control plane:

- add a minimal multi-remote server registry in `relay`
- remove the hidden assumption that approval `request_id` is globally unique
- let desktop consume multi-remote snapshot data
- let desktop show multiple remotes, sessions, and approvals in one place
- add minimal remote status marking without expanding into a reconnect system
- keep the existing single-remote path working

## Completed Work

### 1. P5-1 Server Registry Completed

`relay` now has a minimal in-memory server registry keyed by `remote_id`.

Completed pieces:

- configurable multi-remote registry entries
- minimal per-remote identity fields:
  - `remote_id`
  - `display_name`
  - `endpoint / base_url`
  - provider information
  - base status flags
- snapshot expansion from:
  - sessions + approvals
  - to `servers + sessions + approvals`
- server enrichment on session and approval records
- compatibility with the old single-remote path

This closed the first P5 requirement:

`relay` can now distinguish multiple remote sources instead of treating all remote
events as one implicit origin.

### 2. P5-1.5 Approval Identity Hardening Completed

Approval identity no longer depends on “pending `request_id` is globally unique”.

Completed pieces:

- relay-side unique approval identity now uses `remote_id + request_id`
- request matching remains compatible with old single-remote use
- request-id-only approval response still works when the lookup is unambiguous
- request-id-only approval response now returns a clear ambiguity error when multiple
  remotes share the same `request_id`
- approval response still commits local state only after provider writeback succeeds

This matters because multi-remote aggregation without identity hardening would have
made approval routing unsafe.

### 3. P5-2 Desktop Multi-Remote View Completed

Desktop now consumes the multi-remote snapshot instead of assuming one remote view.

Completed pieces:

- desktop reads `snapshot.servers`
- a Remotes panel shows the discovered remote list
- sessions are grouped by `remote_id`
- approvals are grouped by `remote_id`
- approval actions carry `remote_id`
- single-remote usage remains valid

This closed the MVP viewing requirement for P5:

one local control surface can now show multiple remote sources at the same time.

### 4. P5-3 Remote Status Marking Completed

The remote list now distinguishes basic availability states.

Completed pieces:

- relay computes minimal remote connection status
- desktop renders that status in the Remotes panel
- the minimal state set is:
  - `connected`
  - `disconnected`
  - `unreachable`
- status stays intentionally simple and does not claim reconnect support

The current rule is intentionally lightweight:

- if a remote endpoint answers `GET /healthz`, it is `connected`
- if a configured endpoint does not answer but the remote had previously reported events,
  it is `disconnected`
- if a configured endpoint has not been observed yet and is not reachable, it is
  `unreachable`
- if no endpoint is available, relay falls back to recent-event timing

## Key Implementation Location

The main files touched across P5 were:

- `relay/server_registry.py`
- `relay/main.py`
- `relay/session_store.py`
- `relay/approval_store.py`
- `relay/event_log.py`
- `relay/remote_agent_client.py`
- `desktop/main.js`
- `desktop/src/index.html`
- `desktop/src/styles.css`
- `desktop/src/renderer/app.js`
- `desktop/src/renderer/state/snapshot-store.js`
- `desktop/src/renderer/features/remotes/render-remote-list.js`
- `desktop/src/renderer/features/sessions/render-session-list.js`
- `desktop/src/renderer/features/approvals/render-approval-list.js`

## Validation Performed

The following checks were completed during P5:

- registry bootstrap with at least two remote entries
- relay snapshot validation for:
  - `servers`
  - `sessions[*].remote_id`
  - `approvals[*].remote_id`
- single-remote approval compatibility using request-id-only submit
- multi-remote approval identity validation with duplicate `request_id` across remotes
- ambiguity protection validation for request-id-only approval response
- desktop multi-remote rendering validation for:
  - remote cards
  - grouped sessions
  - grouped approvals
- approval action payload validation including `remote_id`
- remote status marking validation for:
  - connected remote
  - disconnected remote
  - unreachable remote

Representative validation commands:

```powershell
$env:RELAY_SERVER_REGISTRY='[
  {"remote_id":"alpha","display_name":"Alpha Remote","endpoint":"http://127.0.0.1:8711","providers":["kimi"]},
  {"remote_id":"beta","display_name":"Beta Remote","endpoint":"http://127.0.0.1:8712","providers":["kimi"]}
]'
python -m uvicorn relay.main:app --reload
```

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v1/servers
Invoke-RestMethod http://127.0.0.1:8000/v1/snapshot | ConvertTo-Json -Depth 8
```

```powershell
$body = @{
  remote_id = "beta"
  request_id = "req-dup-1"
  decision = "approve"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/approval-response" -Method Post -ContentType "application/json" -Body $body
```

```powershell
cd desktop
npm start
```

## Current Multi-Remote Boundaries After P5

P5 is complete, but the following boundaries remain explicit:

- no reconnect system
- no persisted registry, snapshot, or approval state
- no relay restart rehydration
- no pending approvals replay
- no control-plane event replay across restart
- no provider execution-scene recovery
- no Codex support yet
- no Claude support yet
- no desktop redesign beyond the MVP multi-remote view

P5 is therefore closed as a multi-remote aggregation stage, not as a reliability stage.

## Why P6 Can Start

P6 can start because the multi-remote baseline is now stable enough to clean up
platform coupling without reopening the P5 feature scope.

The main prerequisites already closed by the end of P5 are:

- relay can register and expose multiple remotes
- approval identity is safe in multi-remote scenarios
- desktop can present multiple remotes in one local control surface
- approval actions still reach the correct remote
- remote availability has a minimal visible state

This is enough to shift focus from “can one local control plane aggregate multiple
remotes?” to “can this baseline be cleaned up for cross-platform use?”

## Why P8 Still Keeps Recovery Implementation

P8 still owns the actual recovery and reliability system because the hard work remains open:

- persistence
- reconnect hardening
- heartbeat and stale-state protection beyond minimal status marking
- restart-time state rehydration
- approval replay after restart
- control-plane event replay after restart
- provider-dependent execution-scene recovery

P5 completed the multi-remote control-plane baseline.
It did not complete the recovery system, and it should not be documented as if it did.
