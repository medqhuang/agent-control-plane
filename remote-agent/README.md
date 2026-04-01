# remote-agent

`remote-agent` is the hosted remote execution base for `P4` and `P4.5`.

Current implemented capabilities:

- run a minimal remote-agent HTTP service with `remote-agent serve`
- keep the service alive on remote Linux via `systemctl --user`
- start a hosted Kimi session with `remote-agent kimi start --task "..."`
- launch Kimi through `kimi --wire`
- report provider-agnostic session and approval events back to `relay`
- accept approval decisions from `relay` and write them back to hosted Kimi sessions

Current gaps before `P4.5` can close:

- hosted session CLI is not complete yet
- hosted session interaction contract is not fully documented yet
- recovery contract is not fully documented or implemented yet

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
```

Current `P4.5-B` target commands:

```bash
remote-agent sessions
remote-agent watch <session_id>
remote-agent reply <session_id> --message "..."
remote-agent stop <session_id>
```

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
