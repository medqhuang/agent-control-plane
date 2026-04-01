# P9 Worklog

Updated: 2026-04-01
Current Stage: `P9 Codex Support`
Current Subgoal: `P9 Codex Support`
Previous Completed Stage: `P8 V1.0 Release`
Next Stage: `P10 Reliability Reinforcement`

## Current Baseline

- `P8 v1.0` live release gate has already passed.
- Current formally verified provider for `v1.0` remains `Kimi`.
- Top-level architecture remains fixed:
  - `desktop -> relay -> remote-agent -> provider native interface`
- multi-remote remains complete.
- approval remains uniquely identified by `remote_id + request_id`.
- `P10` reconnect / checkpoint / replay / restart recovery are still out of scope.
- `V2 Claude` remains out of scope.

## Immediate Goal

- Start `P9 Codex Support` without regressing the current `Kimi` mainline.
- Keep `v1.0` documentation truthful: only `Kimi` is formally verified today.
- Do not write `Codex` as already complete until the real chain is implemented and accepted.
