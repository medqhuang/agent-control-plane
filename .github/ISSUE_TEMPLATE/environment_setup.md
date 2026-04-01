---
name: Beta Environment Or Setup Report
about: Capture setup, version, env, and network facts for a first public Beta trial
title: "[beta env] "
---

## Purpose Of This Report

- [ ] blocked setup
- [ ] attach environment facts to another issue
- [ ] record environment after a successful trial

## Role

- [ ] operator
- [ ] remote trial user
- [ ] observer

## Local Setup

- Local platform:
- Local shell:
- Relay URL:
- Desktop launch command:

## Remote Setup

- Remote platform:
- Access method:
- Remote control base URL:
- `REMOTE_AGENT_REMOTE_NAME`:

## Versions And Discovery

- Local Python version:
- Remote Python version:
- Node.js version:
- `kimi` discovery mode: PATH / `KIMI_BIN` / `--kimi-bin` / unknown
- `kimi info` summary:

## Network Checks

- Remote -> relay result:
- Local -> remote control result:

## Service Checks

- `systemctl --user status remote-agent.service --no-pager`:
- `remote-agent sessions`:

## Minimal Reproduction Path Or Setup Steps

1.
2.
3.

## Commands Run

```text
paste the exact commands you used during setup or triage
```

## Relevant Logs Or Snippets

```text
paste the smallest useful env, status, or log excerpt
```

## Linked Issues Or Notes
