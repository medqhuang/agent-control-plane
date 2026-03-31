# P1 Worklog

Updated: 2026-03-31

This document records the work completed so far in `P1 Relay Core`.
The scope is limited to the minimal relay runtime, in-memory state, and
the first approval state loop.

## Stage Goal

P1 focuses on standing up the relay core with the smallest workable local loop:

- start the relay locally
- return a fixed snapshot
- keep session and approval state in memory
- accept one approval response
- reflect the approval change in snapshot

## Completed Work

### 1. Relay Runtime Entry

The relay runtime entry is fixed as:

```powershell
python -m uvicorn relay.main:app --reload
```

Current app entry file:

- `relay/main.py`

The relay uses the minimal Python web stack:

- `fastapi`
- `uvicorn`

### 2. Snapshot Endpoint

Implemented:

- `GET /v1/snapshot`

Current behavior:

- returns JSON with `sessions` and `approvals`
- response shape is stable
- approval objects use `request_id`
- current demo data size is exactly:
  - `1` session
  - `1` approval

Current snapshot example:

```json
{
  "sessions": [
    {
      "id": "session_demo_1",
      "provider": "kimi",
      "remote": "demo-remote",
      "status": "waiting_approval",
      "title": "demo approval session"
    }
  ],
  "approvals": [
    {
      "request_id": "approval_demo_1",
      "session_id": "session_demo_1",
      "status": "pending",
      "kind": "command",
      "summary": "Approve the pending command for the demo session."
    }
  ]
}
```

### 3. In-Memory Session Store

Implemented:

- `relay/session_store.py`

Responsibilities:

- hold relay-side session state in memory
- keep the session state model aligned with `README.md`
- provide the state source for snapshot

Current data model decisions:

- sessions are keyed by `session.id`
- status model is limited to:
  - `running`
  - `waiting_approval`
  - `completed`
  - `failed`
  - `disconnected`

Current public functions:

- `list_sessions()`
- `get_session(session_id)`

### 4. In-Memory Approval Store

Implemented:

- `relay/approval_store.py`

Responsibilities:

- hold approval request state in memory
- use `request_id` as the unique approval identifier
- support snapshot reads
- support approval decision updates

Current public functions:

- `list_approvals()`
- `get_approval(request_id)`
- `apply_decision(request_id, decision)`

Current decision mapping:

- `approve -> approved`
- `reject -> rejected`

### 5. Minimal Event Log

Implemented:

- `relay/event_log.py`

Responsibilities:

- append in-memory relay events for approval responses
- keep event ordering through `seq`

Current public functions:

- `append_approval_response_event(...)`
- `list_events()`

Current event shape:

```json
{
  "seq": 1,
  "type": "approval_response",
  "request_id": "approval_demo_1",
  "session_id": "session_demo_1",
  "decision": "approve",
  "approval_status": "approved"
}
```

Note:

- no separate API endpoint is exposed for event log yet
- event visibility currently comes from the `POST /v1/approval-response` response

### 6. Approval Response Endpoint

Implemented:

- `POST /v1/approval-response`

Request body is intentionally minimal:

```json
{
  "request_id": "approval_demo_1",
  "decision": "approve"
}
```

Current behavior:

- validates `decision` as only `approve` or `reject`
- finds approval by `request_id`
- updates approval status in memory
- appends one event log entry
- returns the updated approval plus the appended event

Example response:

```json
{
  "approval": {
    "request_id": "approval_demo_1",
    "session_id": "session_demo_1",
    "status": "approved",
    "kind": "command",
    "summary": "Approve the pending command for the demo session."
  },
  "event": {
    "seq": 1,
    "type": "approval_response",
    "request_id": "approval_demo_1",
    "session_id": "session_demo_1",
    "decision": "approve",
    "approval_status": "approved"
  }
}
```

## Current Relay File Set

Current relay files are:

```text
relay/
|-- __init__.py
|-- approval_store.py
|-- event_log.py
|-- main.py
`-- session_store.py
```

## Validation Performed

The following checks were completed during P1 work:

- Python syntax check for relay modules
- direct Python import and function call checks
- `uvicorn` startup verification
- `GET /v1/snapshot` request verification
- `POST /v1/approval-response` request verification
- follow-up `GET /v1/snapshot` verification to confirm state change

Validation commands:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn relay.main:app --reload
```

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/snapshot" -Method Get
```

```powershell
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/v1/approval-response" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"request_id":"approval_demo_1","decision":"reject"}'
```

## Current Boundaries

The following items are still intentionally out of scope for the current P1 state:

- real provider integration
- remote session write-back
- desktop UI
- multi-remote aggregation
- persistence
- reconnect handling
- timeout handling improvements
- extra service layers or complex abstractions

## Current Repository Notes

At the time of writing, the current uncommitted P1-relevant files are:

- `relay/__init__.py`
- `relay/session_store.py`
- `relay/approval_store.py`
- `relay/event_log.py`
- `relay/main.py`
- `requirements-relay.txt`

This worklog file itself is also currently uncommitted:

- `P1_worklog.md`

## Physics / Formula Note

The external working rule says each code operation should stay tightly linked
to physics formulas. The current repository, however, is defined by
`README.md` and `DEV.md` as a relay control-plane project.

The completed P1 work only touches:

- HTTP relay entry
- in-memory state
- approval request state transition
- relay event recording

No physical model, governing equation, boundary condition, discretization
scheme, or numerical solver logic is involved in this stage.

## Suggested Next Step

If P1 continues after this point, the next controlled move should be one of:

1. tighten approval-response edge-case handling
2. define a minimal event read path
3. start preparing the Kimi-side write path for P2

Command traces for the work are recorded under:

`C:\Users\dqhua\AppData\Local\Temp\codex-logs\`
