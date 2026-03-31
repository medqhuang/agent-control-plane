# P2 Worklog

Updated: 2026-03-31

This document records the work completed so far in `P2 Kimi closed loop`.
The scope is limited to the first Kimi provider path, the first provider-to-relay
approval ingestion path, the first relay-to-provider writeback path, and one
remote Linux smoke validation through the existing `WSL -> SSH` route.

## Stage Goal

P2 focuses on building and validating the first Kimi-specific approval loop:

- establish a minimal Kimi adapter
- map Kimi-side approval signals into the relay state model
- preserve the existing relay state and idempotency rules from `P1 / P1.5`
- validate the provider path first with local simulation
- then validate one minimal remote Kimi approval loop on Linux

## Completed Work

### 1. Kimi Adapter Skeleton

Implemented the first Kimi adapter files under:

- `adapters/kimi/__init__.py`
- `adapters/kimi/adapter.py`

Current adapter responsibilities:

- define a minimal Kimi-native placeholder event shape
- define the relay-standard approval event shape
- normalize Kimi approval events into relay input events
- provide the first provider writeback entry point

Current normalization entry:

- `normalize_kimi_event(raw_event)`

Current minimal standard event shape:

```json
{
  "type": "approval_request",
  "provider": "kimi",
  "session_id": "kimi_session_demo_1",
  "request_id": "kimi_request_demo_1",
  "seq": 1,
  "remote": "kimi-demo-remote",
  "title": "kimi demo approval session",
  "kind": "command",
  "status": "pending",
  "summary": "Approve shell command: ls -la"
}
```

### 2. Kimi Approval Request Ingress Into Relay

Implemented the first Kimi-to-relay intake path:

- `POST /v1/kimi/approval-request`

This path lets a normalized Kimi approval request update relay-side state by:

- creating or updating a `session`
- creating or updating an `approval`
- keeping `approval.request_id` as the relay-side approval identifier
- preserving the `pending -> waiting_approval` consistency rule from `P1.5`

Current relay-side storage remains intentionally minimal:

- in-memory `session store`
- in-memory `approval store`
- no persistence
- no extra service layer

### 3. Local Demo Trigger For Kimi Intake

Implemented a repeatable local demo trigger:

- `adapters/kimi/demo_push.py`

This trigger is used to:

- build a demo Kimi approval request event
- normalize it
- push it into the current relay

This was the first half-loop used before remote validation:

`Kimi event -> relay intake -> snapshot visibility`

### 4. Relay Approval Response Writeback Hook

Extended the relay approval-response path so that:

- `POST /v1/approval-response`
- updates approval state
- updates session state
- appends one relay event
- calls the Kimi adapter writeback entry

Writeback entry:

- `write_approval_response_to_kimi(...)`

Initial P2 behavior was local simulation only.

For the local simulation path:

- `approve -> approve_request`
- `reject -> reject_request`
- result is returned as `provider_writeback`

This preserved the existing `P1.5` constraints:

- first-write-wins
- repeated same decision does not append a new event
- repeated opposite decision returns `409`
- snapshot stays state-consistent

### 5. Remote Environment Precheck (`P2.3.5`)

Validated the remote development path through:

- `WSL -> SSH -> zhaojin.ustc.edu.cn`

Remote environment findings:

- SSH connectivity: success
- remote Linux: `Rocky Linux 8.7`
- remote user: `huangdq`
- remote Python: `python3 3.10.9`
- remote Node: `v22.22.1`
- remote npm: `10.9.4`

Kimi CLI status before install:

- `kimi` not present

Official Kimi CLI installation was then completed through:

```bash
curl -LsSf https://code.kimi.com/install.sh | bash
uv tool install --python 3.13 kimi-cli
```

Post-install verification:

- `kimi --version` -> `kimi, version 1.28.0`
- `kimi --help` returned normal help output

### 6. Remote Kimi Login-State Validation

Validated that the remote Kimi CLI was not only installed, but actually usable.

Evidence gathered:

- `~/.kimi/credentials/kimi-code.json` exists on the remote machine
- `kimi info` returned normal CLI protocol information
- `kimi --print -p 'reply with exactly AUTH_OK'` returned `AUTH_OK`

This confirms that the remote Kimi CLI login state was usable during the P2 run.

### 7. Minimal Real Remote Kimi Approval Loop

Implemented the first remote smoke helper:

- `adapters/kimi/remote_smoke.py`

This helper:

- starts a real remote Kimi CLI session inside remote `tmux`
- asks Kimi to run a shell command (`pwd`)
- waits until the real approval prompt appears
- captures the remote screen text
- derives a relay-standard `request_id`
- pushes that normalized approval request into relay

Example real prompt evidence captured from the remote Kimi session:

```text
Shell is requesting approval to run command:
pwd
[1] Approve once
[2] Approve for this session
[3] Reject
```

This is a real Kimi approval prompt from the remote Linux session, not a local fake event.

### 8. Real Remote Writeback Through Relay

Extended the Kimi writeback path so that smoke-test sessions with:

- remote host `zhaojin.ustc.edu.cn`
- session id prefix `kimi_remote_`

use a real remote tmux writeback path instead of the old purely simulated one.

Current smoke-test writeback behavior:

- `approve` sends confirm keys to the remote tmux session
- the adapter captures the remote pane again after writeback
- the writeback result is returned in `provider_writeback`

Observed result after local approval:

- relay approval status changed to `approved`
- relay session status changed to `running`
- remote Kimi pane showed:
  - `Used Shell (pwd)`
  - `The command executed successfully`

This completes the first real remote smoke loop:

`remote Kimi approval prompt -> relay snapshot -> local approval-response -> remote Kimi continues`

## Real vs Simulated Boundary

The current P2 state includes both real provider behavior and adapter glue behavior.

Real in the current loop:

- remote Linux environment
- real `kimi` CLI process
- real remote approval prompt
- real local relay HTTP requests
- real remote continue action after approval

Still adapter-defined glue in the current loop:

- the relay-side `request_id` is adapter-generated
- the event intake path reads the real remote prompt and converts it into a relay event
- the writeback path sends tmux keys, not a Kimi-native approval protocol response

Therefore the current state is a real remote smoke loop with a minimal bridge,
not yet a native Kimi approval protocol integration.

## Implementation Location

The main P2 files are:

- `adapters/kimi/__init__.py`
- `adapters/kimi/adapter.py`
- `adapters/kimi/demo_push.py`
- `adapters/kimi/remote_smoke.py`
- `relay/main.py`
- `relay/session_store.py`
- `relay/approval_store.py`
- `relay/event_log.py`

## Validation Performed

The following checks were completed during P2:

- import validation for `adapters.kimi`
- local demo event push into relay
- `GET /v1/snapshot` validation after Kimi event ingress
- `POST /v1/approval-response` validation for simulated Kimi writeback
- repeated same-decision validation for idempotent behavior
- remote SSH environment validation
- remote Kimi CLI installation and version verification
- remote Kimi login-state validation
- remote real approval prompt capture from tmux
- relay snapshot validation for the real remote approval request
- local `approval-response` validation for the real remote smoke session
- remote post-approval capture verification

Representative remote smoke commands:

```powershell
.\.venv\Scripts\python.exe -m uvicorn relay.main:app --host 127.0.0.1 --port 8765
.\.venv\Scripts\python.exe -m adapters.kimi.remote_smoke http://127.0.0.1:8765 --session-suffix real_20260331_231314 --command pwd
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/snapshot" -Method Get
Invoke-RestMethod -Uri "http://127.0.0.1:8765/v1/approval-response" -Method Post -ContentType "application/json" -Body '{"request_id":"kimi_remote_real_20260331_231314_request_1","decision":"approve"}'
```

## Current Boundaries

The following items remain intentionally out of scope after the current P2 work:

- Claude / Codex provider integration
- local UI
- multi-remote aggregation
- persistence
- reconnect enhancement
- timeout hardening
- native Kimi approval protocol integration
- large relay or adapter refactor

## Physics / Formula Note

The external working rule says each code operation should stay tightly linked
to physics formulas. The repository itself is currently defined by `README.md`
and `DEV.md` as a relay control-plane project.

The completed P2 work only touches:

- provider adapter structure
- relay approval ingestion
- relay writeback routing
- remote CLI environment setup
- remote approval smoke validation

No physical model, governing equation, boundary condition, discretization
scheme, or numerical solver logic is involved in this stage.

## Operation Trace

P2 command logs were recorded under:

`C:\Users\dqhua\AppData\Local\Temp\codex-logs\`
