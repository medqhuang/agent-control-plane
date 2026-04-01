# P4 Worklog

Updated: 2026-04-01
Status: Complete

This document records the closure work completed in `P4 Remote-Agent Foundation`.
The scope is limited to establishing the remote hosted-execution base, fixing the
remote deployment contract, and replacing the old bridge as the main forward path
for Kimi session startup on remote Linux.

## Stage Goal

P4 focused on moving the execution boundary to the remote host:

- create a minimal runnable `remote-agent/` package
- freeze one remote service entry with `remote-agent serve`
- freeze one provider entry with `remote-agent kimi start --task "..."`
- prefer `systemctl --user` for long-running remote hosting
- prefer `kimi --wire` over extending the old `tmux + TUI` bridge
- leave clear drop points for later supervisor, relay integration, and hosted-session work

## Completed Work

### 1. Minimal `remote-agent/` Skeleton Added

The repository now contains a dedicated `remote-agent/` package with:

- package metadata and console entrypoint
- `remote-agent serve`
- `remote-agent kimi start --task "..."`
- minimal structured CLI output
- minimal FastAPI service surface for remote hosting

This fixed the first hard requirement of P4:

`remote-agent` became a real remote runtime surface instead of a planning-only placeholder.

### 2. Remote User-Service Contract Frozen

The remote long-running process contract was fixed around `systemctl --user`.

P4 established:

- a user-systemd service template
- an install script
- one environment-file entrypoint
- one working-directory contract
- one file-log location

This made `remote-agent serve` operable as a real remote user service instead of a
foreground shell-only process.

### 3. Logout-Survival Requirement Closed On The Target Host

P4 did not stop at “`systemctl --user` can start”.

The target host path was pushed through the actual logout-survival requirement:

- `loginctl show-user ... -p Linger` was checked
- linger was enabled on the target host
- the service was verified before SSH disconnect
- the service was verified again after re-login
- `127.0.0.1:8711/healthz` remained reachable after reconnect

This closed the host-policy gap that would otherwise have left P4 only partially true.

### 4. Minimal Kimi Provider Start Path Moved To `kimi --wire`

`remote-agent kimi start --task "..."` now launches Kimi through `kimi --wire`
on the remote host.

The P4 foundation fixed the provider-facing minimal stack as:

- remote `remote-agent`
- remote `kimi --wire`
- no new dependency on the old local bridge main line

At this stage the command could already start, run, and return minimal structured
results suitable for later hosted-session evolution.

### 5. Remote Service Drop Points Reserved

P4 left explicit extension points for later stages without changing the top-level route.

The main drop points were:

- service app entry
- supervisor runtime
- Kimi worker
- relay client placeholder

This was important because later P4.5 work needed to add hosted sessions, relay
reporting, approval writeback, and session CLI without re-opening the stage boundary.

### 6. Old Bridge Main-Path Problems Addressed

P4 resolved the most important structural problems of the old bridge route:

- remote execution no longer had to be owned by the local machine
- the new main path no longer depended on `WSL -> SSH -> tmux -> TUI` for startup
- provider-facing execution moved toward a provider-native interface
- remote long-running hosting stopped being a best-effort shell convention

This does not delete the historical bridge path.
It does change which path is treated as the project’s main architecture.

## Key Implementation Location

The main P4 files are:

- `remote-agent/pyproject.toml`
- `remote-agent/src/remote_agent/cli.py`
- `remote-agent/src/remote_agent/app.py`
- `remote-agent/src/remote_agent/providers/kimi/worker.py`
- `remote-agent/src/remote_agent/supervisor/runtime.py`
- `remote-agent/deploy/systemd/remote-agent.service.template`
- `remote-agent/deploy/remote-agent.env.example`
- `remote-agent/scripts/install-systemd-user.sh`

## Validation Performed

The following checks were completed during P4:

- editable install validation for `remote-agent/`
- local CLI parse validation for:
  - `remote-agent serve`
  - `remote-agent kimi start --task "..."`
- remote `systemctl --user` install and start validation
- remote service `status / restart / logs` validation
- remote logout-survival validation with `Linger=yes`
- remote health check validation through:
  - `GET /healthz`
  - `GET /v1/runtime`
- remote `kimi --wire` launch validation through:
  - `remote-agent kimi start --task "..."`

Representative remote verification commands:

```bash
cd ~/agent-control-plane/remote-agent
bash scripts/install-systemd-user.sh --start
systemctl --user status remote-agent.service --no-pager
```

```bash
remote-agent serve
```

```bash
remote-agent kimi start --task "Reply with exactly READY and nothing else."
```

```bash
curl -s http://127.0.0.1:8711/healthz
curl -s http://127.0.0.1:8711/v1/runtime
```

## Old Bridge Problems Solved In P4

P4 specifically removed these old main-path problems:

- startup of a remote session no longer required the local bridge to own the launch path
- remote hosting no longer depended on keeping one SSH shell or terminal multiplexer layout alive
- the project stopped treating `tmux + TUI` as the preferred future-facing provider interface
- the remote service contract became explicit instead of being spread across ad-hoc shell steps

## Current Boundaries After P4

P4 intentionally stopped before hosted-session usability closure.

At the end of P4, the remaining boundaries were:

- no relay integration yet
- no hosted session list / watch / reply / stop CLI yet
- no approval decision round-trip through `relay`
- no hosted-session contract write-up yet
- no recovery implementation beyond service revival and host-level logout survival

Those items were intentionally carried into `P4.5 Hosted Session Usability`,
not folded back into P4.
