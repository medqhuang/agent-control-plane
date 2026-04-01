# P8 Worklog

Updated: 2026-04-01
Current Stage: `P9 Codex Support`
Completed Milestone: `P8 V1.0 Release`
Completed Subgoal: `P8 Live End-to-End Trial Verification And Blocker Triage`

## Scope

This worklog records the live release-gate run that closed `P8` and allowed the
docs to move forward to `P9 Codex Support`.

## Live Environment

- Local control host: Windows desktop app + local relay access through `127.0.0.1`
- Local verification relay used in the passing run: WSL-hosted `relay` on `127.0.0.1:18181`
- Local verification control tunnel: `127.0.0.1:18781 -> remote 127.0.0.1:8711`
- Remote relay ingress tunnel: remote `127.0.0.1:28181 -> local 127.0.0.1:18181`
- Remote host: Linux user service with `systemd --user`
- Provider: real `Kimi --wire` (`kimi info` confirmed, CLI version `1.28.0`)

## Commands Actually Used

### Local

```powershell
wsl bash -lc 'python3 -m venv ~/.venvs/acp-relay && ~/.venvs/acp-relay/bin/pip install fastapi uvicorn'
```

```powershell
wsl.exe bash /mnt/c/Users/dqhua/AppData/Local/Temp/acp-p8-wsl-relay-18181.sh
```

```powershell
wsl.exe bash /mnt/c/Users/dqhua/AppData/Local/Temp/acp-p8-tunnel-28181.sh
```

```powershell
cmd.exe /c "set RELAY_BASE_URL=http://127.0.0.1:18181 && C:\Users\dqhua\Desktop\agent-control-plane\desktop\node_modules\electron\dist\electron.exe . --remote-debugging-port=9225"
```

### Remote

```bash
cd ~/acp-p8-live-20260401-202456/remote-agent
bash scripts/install-systemd-user.sh --start
systemctl --user restart remote-agent.service
```

```bash
mkdir -p ~/acp-v1-trial-20260401-202456
cd ~/acp-v1-trial-20260401-202456
remote-agent kimi start --workdir ~/acp-v1-trial-20260401-202456 --kimi-bin ~/.local/bin/kimi --timeout-seconds 120 --task "Reply with exactly ACP-P8-UI-20260401-202456 and then wait for my next instruction."
```

```text
UI reply prompt used for the passing approval round:
Use the shell tool to run pwd and return only the absolute path. Do not answer from memory.
```

## Paths Verified End-to-End

### Passed

- Local relay reachable from remote through the tunnel:
  - remote `curl http://127.0.0.1:28181/v1/snapshot`
- Local control path reachable back to the remote-agent service:
  - local `http://127.0.0.1:18781/healthz`
- Remote install/start path:
  - `install-systemd-user.sh --start`
  - `systemctl --user restart remote-agent.service`
- Real hosted session creation:
  - `remote-agent kimi start ...`
- Local UI session visibility:
  - session list showed the remote `Kimi` session
- Local UI detail path:
  - session detail loaded and refreshed through relay
- Local UI reply path:
  - `reply` submission reached the hosted session and updated turn state
- Local UI approval path:
  - approval request appeared in the approvals list
  - `Approve` in UI wrote back through relay to remote-agent
  - hosted session continued and finished
  - final result flowed back into session detail
- Workdir default fix verification:
  - after the fix, `cd <trial-dir> && remote-agent kimi start --task "..."` used the CLI cwd without requiring `--workdir`

### Failed Or Non-Deterministic During Triage

- Early remote HTTP checks using remote-side `urllib.request` returned false
  `RemoteDisconnected` results even for healthy local HTTP services on the
  remote machine. `curl` was used for authoritative verification afterward.
- Generic file-write prompts such as
  `Create a file named acp-v1-proof.txt ...`
  did not deterministically trigger provider approval in this environment.
- The passing approval round used an explicit shell-tool prompt instead.

### Still Not Verified

- Codex support
- Claude support
- reconnect / checkpoint / replay / pending approvals replay
- remote-agent restart recovery
- provider `resume / reattach`
- attach

## Confirmed Release Blocker

- Blocker: in service mode, `remote-agent kimi start` ignored the CLI invocation
  directory when `--workdir` was omitted, so the documented
  `cd <trial-dir> && remote-agent kimi start --task "..."`
  flow could run in the service install directory instead of the operator's
  intended workspace.
- Fix: `remote-agent/src/remote_agent/cli.py`
- Change: when `--workdir` is omitted, the CLI now sends `os.getcwd()` to the
  service explicitly.
- Status: fixed and rerun-verified on 2026-04-01.

## Known Limitations After Gate Pass

- `desktop` remains source-run.
- `relay` remains operator-started.
- `remote-agent` still requires manual env wiring.
- Network reachability checks remain manual.
- `desktop` currently relies on manual refresh for timely state observation.
- `watch` is a single read, not continuous follow.
- `attach` is not implemented.
- `relay` and `remote-agent` remain memory-backed and do not recover old
  sessions or pending approvals after restart.

## Gate Decision

- `P8` release gate: passed
- Remaining confirmed `P8` blockers: none
- Document state: pushed forward to `P9 Codex Support`
- Next implementation stage: `P9 Codex Support`
