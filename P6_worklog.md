# P6 Worklog

Updated: 2026-04-01
Status: P6 Complete
Current Stage: P6.5 Public Beta Release
Next Stage: P7 Codex Support

This document records completed `P6-1 Platform Assumption Audit`, completed
`P6-2 Runbook And Text Policy Cleanup`, and completed
`P6-3 Boundary Cleanup`.
`P6 Cross-Platform Cleanup` is now complete, and the project has entered
`P6.5 Public Beta Release`.

## Audit Scope

- `relay/`
- `remote-agent/`
- `desktop/`
- Windows path hardcodes
- PowerShell-only command assumptions
- path separator assumptions
- encoding and line-ending assumptions
- direct Windows/macOS-only API usage in core/runtime code

## P6-2 Completed Work

- `README.md` and `DEV.md` now use repo-relative runbook wording instead of
  machine-local Windows paths.
- The docs no longer prescribe `.venv\\Scripts\\Activate.ps1`; virtualenv
  activation is now described as shell-specific.
- Root `.gitattributes` now pins LF for docs, scripts, templates, and common
  source/config text files.
- Root `.editorconfig` now sets UTF-8, LF, and final-newline defaults for text
  editing.
- The Linux deploy shell remains explicitly scoped to
  `remote-agent/deploy/` and `remote-agent/scripts/`.

## P6-3 Completed Boundary Closures

- Closed the remaining P6 blocker by fixing the boundary between shared runtime
  code and Linux deploy shell.
- Kept Linux deploy assumptions scoped to `remote-agent/deploy/` and
  `remote-agent/scripts/`.
- Kept desktop platform branching scoped to `desktop/main.js`; no platform
  branch was added to `desktop/preload.js`, renderer, state, or `relay/`.
- Removed the shared-runtime Linux home fallback for provider binary discovery
  from `remote-agent/src/remote_agent/providers/kimi/worker.py`; shared runtime
  now relies on PATH plus explicit `KIMI_BIN` / `--kimi-bin` override.
- Confirmed that `relay/` and `remote-agent/src/remote_agent/` do not absorb
  `systemctl`, `/bin/bash`, `loginctl`, or Linux deploy-path assumptions.

## Module Findings

### relay

- No Windows path hardcodes were found in runtime files under `relay/`.
- No PowerShell-only command assumptions were found in runtime files under
  `relay/`.
- No filesystem separator parsing or string-built local path handling was
  found. The module mainly works with HTTP URLs, in-memory ids, and
  timestamps.
- JSON transport is already explicit UTF-8 in
  `relay/remote_agent_client.py:32-39` and
  `relay/remote_agent_client.py:49-61`. This is a positive contract, not a
  portability issue.
- No Windows/macOS-specific API usage was found in `relay/`.
- P6 blocker status: none.

### remote-agent

- The runtime code under `remote-agent/src/remote_agent/` does not directly
  depend on Windows or macOS APIs.
- The current deploy shell is intentionally Linux-specific:
- `remote-agent/scripts/install-systemd-user.sh:1-180` assumes `bash`,
  `systemctl --user`, `loginctl`, `python3`, `~/.config`, `~/.local`, and
  venv `bin/python`.
- `remote-agent/deploy/systemd/remote-agent.service.template:11` hardcodes
  `/bin/bash`.
- `remote-agent/deploy/remote-agent.env.example:4-5` hardcodes
  `/home/your-user/...`.
- `remote-agent/README.md:55-99` documents the same Linux-only service layout.
- Provider startup no longer carries a shared-runtime Linux home fallback; PATH
  plus explicit `KIMI_BIN` / `--kimi-bin` override is now the boundary-safe
  discovery path.
- HTTP JSON is explicit UTF-8 in
  `remote-agent/src/remote_agent/service_client.py:67-80` and
  `remote-agent/src/remote_agent/relay/client.py:82-105`.
- The Kimi wire transport is explicit newline-delimited UTF-8 JSON in
  `remote-agent/src/remote_agent/providers/kimi/worker.py:560` and
  `remote-agent/src/remote_agent/providers/kimi/worker.py:595-624`.
- P6 blocker status: closed.

### desktop

- No Windows path hardcodes were found in `desktop/main.js`,
  `desktop/preload.js`, or the renderer/state files.
- No PowerShell-only runtime assumptions were found. `desktop/package.json`
  uses `electron .`, which is shell-neutral.
- Path construction in the main process already uses `path.join` in
  `desktop/main.js:132` and `desktop/main.js:138`.
- The only platform-specific runtime branch found is the standard Electron
  macOS lifecycle guard in `desktop/main.js:186-188`.
- No Windows/macOS-specific tray, notification, or menu-bar API dependency is
  currently spread into `preload.js`, renderer code, or snapshot state.
- P6 blocker status: none in current runtime code.

## Cross-Module Blockers That Should Be Closed In P6

- Closed in `P6-2`: `README.md` and `DEV.md` no longer bind local runbook
  commands to `C:\\Users\\...`, PowerShell code fences, or
  `.venv\\Scripts\\Activate.ps1`.
- Closed in `P6-2`: the repo now has root `.gitattributes` and `.editorconfig`
  so LF-sensitive docs, scripts, templates, and common source/config text files
  are protected by repo-level policy.
- Closed in `P6-3`: the boundary between "cross-platform core" and
  "Linux-only remote deploy shell" is now explicit enough that later work does
  not need to generalize `systemctl` or `/bin/bash` into shared runtime
  abstractions.

Status after current update: closed for `P6`.

## Non-Blocking Items That Can Stay Deferred

- `remote-agent/scripts/install-systemd-user.sh` staying Linux-only is
  acceptable for V1 as long as it remains outside `src/remote_agent/`.
- `remote-agent/deploy/systemd/remote-agent.service.template` may keep
  `/bin/bash` if the file stays clearly scoped to Linux service deployment.
- `remote-agent/deploy/remote-agent.env.example` may keep a Linux home-path
  example if the file is explicitly documented as a Linux example.
- Non-PATH provider binaries must now be passed explicitly through `KIMI_BIN`
  or `--kimi-bin`; shared runtime no longer keeps a Linux home fallback.
- `desktop/main.js:186-188` may keep the macOS lifecycle branch because it is a
  shell-level concern, not a cross-module core dependency.
- The current UTF-8 HTTP and wire encoding paths are explicit and should be
  preserved, not removed.

## Minimal Cleanup Order

### 1. P6-2 Runbook And Text Policy Cleanup

- Rewrite local run commands in `README.md` and `DEV.md` so they are
  repo-relative and no longer tied to `C:\\Users\\dqhua\\...` or PowerShell
  activation paths.
- Add a repo text-file policy in a later code step via root `.gitattributes`,
  and optionally `.editorconfig`, to lock LF for shell/script/template/docs
  files and make UTF-8 the default editing assumption.

Status: done.

### 2. P6-3 Boundary Cleanup

- Keep Linux-only deployment surfaces under `remote-agent/scripts/` and
  `remote-agent/deploy/`.
- Keep desktop platform branches confined to `desktop/main.js`.
- Do not introduce new platform branches into `relay/`,
  `remote-agent/src/remote_agent/`, `desktop/preload.js`, or renderer/state
  files.

Status: done.

### 3. P6-3 Optional Provider Surface Tightening

- Shared runtime no longer keeps a Linux-home provider fallback. If provider
  discovery needs to expand later, add an explicit provider config surface
  outside the shared core instead of restoring an implicit fallback layer.

Status: done with the minimal boundary-safe path: PATH plus explicit
`KIMI_BIN` / `--kimi-bin` override.

### 4. Pre-P7 Re-Audit

- Before `P7 Codex Support`, re-scan for Windows local paths, PowerShell-only
  commands, missing LF policy, and new OS-specific APIs in shared runtime code.

## Audit Conclusion

- `relay/` is already close to platform-neutral.
- `desktop/` currently keeps platform-specific behavior confined to the
  Electron main-process shell.
- `remote-agent/` runtime code is mostly clean, but its Linux deployment shell
  must remain explicitly outside the cross-platform core.
- The first P6 cleanup work should therefore start with docs/runbook surface
  and repo text-file policy, not with a large runtime rewrite.
- `P6-3` has now closed the remaining boundary blocker without changing the
  current multi-remote approval / session / snapshot semantics.
