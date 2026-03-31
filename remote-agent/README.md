# remote-agent

`remote-agent` is the minimal P4 foundation for remote native execution.

This package intentionally does only two things right now:

- start a minimal remote-agent HTTP service with `remote-agent serve`
- accept a placeholder Kimi task with `remote-agent kimi start --task "..."`

It does not yet integrate relay, `kimi --wire`, `systemctl --user`, or multi-remote orchestration.

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

### Long-Running Limitation

This P4 setup prefers `systemctl --user`, but it still depends on the target host's user-systemd policy.

If `loginctl show-user "$USER" -p Linger --value` returns `no`, the service can run while the user has an active session, but it is not guaranteed to survive logout. In that case the blocker is host policy, not the `remote-agent` package.

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
        │       └── worker.py
        ├── relay/
        │   ├── __init__.py
        │   └── client.py
        └── supervisor/
            ├── __init__.py
            └── runtime.py
```

## Future Drop Points

- `remote_agent.supervisor.runtime`: remote session lifecycle and worker orchestration
- `remote_agent.providers.kimi.worker`: real `kimi --wire` execution
- `remote_agent.relay.client`: relay status and approval reporting
