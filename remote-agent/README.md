# remote-agent

`remote-agent` is the hosted remote execution base for `P4` and `P4.5`.

Current implemented capabilities:

- run a minimal remote-agent HTTP service with `remote-agent serve`
- keep the service alive on remote Linux via `systemctl --user`
- start a hosted Kimi session with `remote-agent kimi start --task "..."`
- list, inspect, reply to, and stop hosted sessions with `remote-agent sessions / watch / reply / stop`
- launch Kimi through `kimi --wire`
- report provider-agnostic session and approval events back to `relay`
- accept approval decisions from `relay` and write them back to hosted Kimi sessions

Current gaps before `P4.5` can close:

- `attach` is not implemented yet
- recovery is documented at the contract level, but checkpoint persistence and replay are not implemented yet

## Fixed Minimal Stack

- Python package with `setuptools`
- CLI with Python stdlib `argparse`
- HTTP service with `FastAPI`
- ASGI runtime with `uvicorn`
- remote long-running process via `systemctl --user`

## Install

```bash
python -m pip install -e ./remote-agent
```

## Commands

```bash
remote-agent serve
remote-agent kimi start --task "refactor auth module"
remote-agent sessions
remote-agent watch <session_id>
remote-agent reply <session_id> --message "..."
remote-agent stop <session_id>
```

`remote-agent attach <session_id>` is not implemented in the current hosted-session contract.

`remote-agent serve` also accepts these environment variables:

- `REMOTE_AGENT_HOST`
- `REMOTE_AGENT_PORT`
- `REMOTE_AGENT_LOG_LEVEL`

CLI flags still override environment values.

## Remote User Service

Current P4 remote contract is fixed as:

- service file: `~/.config/systemd/user/remote-agent.service`
- environment file: `~/.config/remote-agent/remote-agent.env`
- service env keys: `REMOTE_AGENT_HOST`, `REMOTE_AGENT_PORT`, `REMOTE_AGENT_LOG_LEVEL`, `REMOTE_AGENT_LOG_FILE`
- working directory: the deployed `remote-agent/` directory on the remote Linux host
- log file: `~/.local/state/remote-agent/remote-agent.log`

The repo includes:

- service template: `deploy/systemd/remote-agent.service.template`
- env example: `deploy/remote-agent.env.example`
- install script: `scripts/install-systemd-user.sh`

### Install On A Remote Linux Host

Copy this directory to the remote host, then run:

```bash
cd ~/agent-control-plane/remote-agent
bash scripts/install-systemd-user.sh --start
```

The install script will:

- create a venv at `~/.venvs/agent-control-plane`
- install `remote-agent` in editable mode from the current workdir
- write `~/.config/remote-agent/remote-agent.env`
- render `~/.config/systemd/user/remote-agent.service`
- run `systemctl --user daemon-reload`
- run `systemctl --user enable remote-agent.service`
- optionally start the service when `--start` is passed

### Service Commands

```bash
systemctl --user start remote-agent.service
systemctl --user stop remote-agent.service
systemctl --user restart remote-agent.service
systemctl --user status remote-agent.service --no-pager
tail -n 50 ~/.local/state/remote-agent/remote-agent.log
tail -f ~/.local/state/remote-agent/remote-agent.log
```

## Current Service APIs

The current hosted-session path uses these service APIs:

- `GET /healthz`
- `GET /v1/runtime`
- `POST /v1/kimi/start`
- `POST /v1/approval-response`
- `GET /v1/sessions`
- `GET /v1/sessions/{session_id}`
- `POST /v1/sessions/{session_id}/reply`
- `POST /v1/sessions/{session_id}/stop`

## Hosted Session Contract

- `remote-agent kimi start --task "..."` creates a hosted background session. The CLI waits only until the first checkpoint and then returns. The checkpoint is either:
  - the current turn finishes
  - an approval request is observed
- After `start` returns, the hosted session belongs to `remote-agent serve`, not to the shell process that launched `start`.
- `remote-agent sessions` lists only sessions that are still hosted in the current in-memory runtime. It is not a persisted history view.
- `remote-agent watch <session_id>` is a single read of the latest hosted-session state. It is not a streaming follow mode.
- `remote-agent reply <session_id> --message "..."` appends one more user input turn to an existing hosted session without attaching an interactive TTY.
- `remote-agent stop <session_id>` stops a hosted session only when the session is idle. After stop succeeds, the session is removed from the current runtime list.
- `remote-agent stop <session_id>` currently rejects:
  - a session in `approval_pending`
  - a session with a turn still running
- The `approval_pending` stop rejection is intentional. The current contract prefers keeping hosted-session state aligned with relay-side pending approval state over allowing force-stop semantics.
- `remote-agent attach <session_id>` is not implemented yet. It may be added later, but current docs and UX must treat it as unsupported.

## Recovery Contract

- Recovery must be split into three different layers:
  - service revival: `systemd --user` brings `remote-agent serve` back up
  - control-plane state restoration: session, approval, snapshot, and event views are rebuilt
  - provider execution-state restoration: the original provider subprocess can continue or be reattached
- Current implemented behavior for local desktop disconnect or shutdown is: hosted sessions keep running as long as `remote-agent serve` and the provider subprocess are still alive on the remote host. The desktop is not the hosted-session owner.
- Current implemented behavior for desktop restart is limited to reconnecting to the current relay and reading the snapshot relay still has in memory. Desktop restart does not restore provider execution state.
- `online`, `offline`, and `awaiting_reconnect` are target recovery-state terms. They are not current stable API fields and must not be documented as already implemented snapshot fields.
- The minimal checkpoint schema is a target contract, not a current persisted artifact. It should eventually contain at least:
  - recent conversation context
  - current working directory
  - pending approvals
  - timestamp
  - client connection identifier
- Pending approvals currently keep `request_id` as the stable key, but the pending state only exists in relay memory and remote-agent process memory. There is no automatic approval recovery or replay after restart yet.
- Control-plane events currently provide live standard events with ordering information, but there is no persisted event buffer and no cross-restart replay path yet.
- Current promise after `remote-agent` service revival is limited to: the service can start again and accept new requests. It does not currently restore prior hosted sessions, request-to-session mappings, pending approvals, or provider subprocess state.
- Current promise after relay restart is limited to: relay can accept new session, approval, and event reports again. It does not currently restore the old snapshot or rehydrate remote state by itself.
- Current boundary after provider subprocess exit is: the hosted session may fail or disappear. `remote-agent` does not currently promise full `resume` or `reattach` of the original Kimi execution scene.
- This project must not describe “the service came back up” as “control-plane state has been restored”, and must not describe “control-plane state can be rebuilt” as “provider execution state is fully recoverable”.

## Long-Running Requirement

This setup prefers `systemctl --user` and requires user-systemd to support logout survival.

The install script now checks `loginctl show-user "$USER" -p Linger --value` and attempts to enable linger automatically. If linger cannot be enabled, the script fails clearly instead of pretending logout-safe hosting already works.

Some hosts also restrict `journalctl --user` access even for the owning user. This repo therefore treats the file log above as the minimal reliable log surface for P4.

## Directory Layout

```text
remote-agent/
├── deploy/
│   ├── remote-agent.env.example
│   └── systemd/
│       └── remote-agent.service.template
├── README.md
├── pyproject.toml
├── scripts/
│   └── install-systemd-user.sh
└── src/
    └── remote_agent/
        ├── __init__.py
        ├── __main__.py
        ├── app.py
        ├── cli.py
        ├── output.py
        ├── providers/
        │   ├── __init__.py
        │   └── kimi/
        │       ├── __init__.py
        │       ├── host.py
        │       └── worker.py
        ├── relay/
        │   ├── __init__.py
        │   └── client.py
        ├── service_client.py
        └── supervisor/
            ├── __init__.py
            └── runtime.py
```

## Future Drop Points

- `remote_agent.supervisor.runtime`: hosted-session lifecycle and request-to-session mapping
- `remote_agent.providers.kimi.worker`: `kimi --wire` execution and standard event production
- `remote_agent.providers.kimi.host`: hosted Kimi session runtime and decision writeback
- `remote_agent.relay.client`: relay event reporting
- `remote_agent.service_client`: local CLI to hosted remote-agent service routing
