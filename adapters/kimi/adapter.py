"""Minimal Kimi adapter skeleton for approval-request mapping."""

import json
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from shlex import quote
from typing import Any
from typing import Mapping


# Placeholder Kimi-native event shape for the first approval-request loop.
DEMO_KIMI_APPROVAL_EVENT: dict[str, object] = {
    "event": "approval_request",
    "session_id": "kimi_session_demo_1",
    "request_id": "kimi_request_demo_1",
    "seq": 1,
    "remote": "kimi-demo-remote",
    "title": "kimi demo approval session",
    "kind": "command",
    "summary": "Approve shell command: ls -la",
}


# Relay-standard approval event shape expected by the next intake step.
DEMO_RELAY_APPROVAL_EVENT: dict[str, object] = {
    "type": "approval_request",
    "provider": "kimi",
    "session_id": "kimi_session_demo_1",
    "request_id": "kimi_request_demo_1",
    "seq": 1,
    "remote": "kimi-demo-remote",
    "title": "kimi demo approval session",
    "kind": "command",
    "status": "pending",
    "summary": "Approve shell command: ls -la",
}

_SIMULATED_WRITEBACKS: list[dict[str, object]] = []
_REAL_REMOTE_SESSION_PREFIX = "kimi_remote_"
_REMOTE_REQUEST_PREFIX = "kimi_request__"
_REMOTE_POLL_ATTEMPTS = 30
_REMOTE_POLL_INTERVAL_SECONDS = 2.0
_REMOTE_SCRIPT_TIMEOUT_SECONDS = 90
_FORCE_WRITEBACK_FAILURE_ENV = "KIMI_BRIDGE_FORCE_WRITEBACK_FAILURE"


def build_demo_kimi_approval_event(
    suffix: str,
    *,
    seq: int = 1,
) -> dict[str, object]:
    return {
        "event": "approval_request",
        "session_id": f"kimi_session_{suffix}",
        "request_id": f"kimi_request_{suffix}",
        "seq": seq,
        "remote": "kimi-demo-remote",
        "title": f"kimi demo approval session {suffix}",
        "kind": "command",
        "summary": f"Approve shell command for demo {suffix}",
    }


def normalize_kimi_event(raw_event: Mapping[str, Any]) -> dict[str, object] | None:
    if raw_event.get("event") != "approval_request":
        return None

    return {
        "type": "approval_request",
        "provider": "kimi",
        "session_id": str(raw_event["session_id"]),
        "request_id": str(raw_event["request_id"]),
        "seq": int(raw_event["seq"]),
        "remote": str(raw_event.get("remote", "kimi-demo-remote")),
        "title": str(raw_event.get("title", raw_event["session_id"])),
        "kind": str(raw_event.get("kind", "command")),
        "status": "pending",
        "summary": str(raw_event["summary"]),
    }


def build_remote_kimi_session_id(session_suffix: str) -> str:
    normalized_suffix = _normalize_bridge_segment(session_suffix)
    return f"{_REAL_REMOTE_SESSION_PREFIX}{normalized_suffix}"


def build_remote_kimi_request_id(
    *,
    remote_host: str,
    session_id: str,
    seq: int,
) -> str:
    normalized_remote = _normalize_bridge_segment(remote_host)
    return f"{_REMOTE_REQUEST_PREFIX}{normalized_remote}__{session_id}__seq_{seq}"


def build_remote_kimi_ingress_event(
    *,
    remote_host: str,
    session_id: str,
    seq: int,
    command: str,
) -> dict[str, object]:
    return {
        "event": "approval_request",
        "session_id": session_id,
        "request_id": build_remote_kimi_request_id(
            remote_host=remote_host,
            session_id=session_id,
            seq=seq,
        ),
        "seq": seq,
        "remote": remote_host,
        "title": f"remote Kimi approval session {session_id}",
        "kind": "command",
        "summary": f"Approve shell command: {command}",
    }


def start_remote_kimi_approval_smoke(
    *,
    relay_base_url: str,
    remote_host: str,
    session_id: str,
    command: str = "pwd",
    workdir: str = "~/kimi-web/p2-smoke",
) -> dict[str, object]:
    seq = 1
    prompt = f"Run the shell command {command} and then stop."
    tmux_command = _build_tmux_kimi_command(workdir=workdir, prompt=prompt)
    script = f"""#!/usr/bin/env bash
set -euo pipefail
ssh {quote(remote_host)} <<'EOSSH'
source ~/.bashrc >/dev/null 2>&1 || true
mkdir -p {quote(workdir)}
if tmux has-session -t {quote(session_id)} 2>/dev/null; then
  tmux kill-session -t {quote(session_id)}
fi
tmux new-session -d -s {quote(session_id)} {quote(tmux_command)}
attempt=0
while [ "$attempt" -lt {_REMOTE_POLL_ATTEMPTS} ]; do
  capture=$(tmux capture-pane -pt {quote(session_id)} -S -200 || true)
  if printf "%s\\n" "$capture" | grep -q "ACTION REQUIRED"; then
    echo "__CAPTURE_BEGIN__"
    printf "%s\\n" "$capture"
    echo "__CAPTURE_END__"
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep {_REMOTE_POLL_INTERVAL_SECONDS}
done
echo "__CAPTURE_BEGIN__"
tmux capture-pane -pt {quote(session_id)} -S -200 || true
echo "__CAPTURE_END__"
echo "approval prompt not observed" >&2
exit 1
EOSSH
"""
    result = _run_wsl_bash_script(script)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "remote Kimi smoke trigger failed")

    capture_excerpt = _extract_marked_block(result.stdout)
    raw_event = build_remote_kimi_ingress_event(
        remote_host=remote_host,
        session_id=session_id,
        seq=seq,
        command=command,
    )
    relay_response = push_kimi_event_to_relay(relay_base_url, raw_event)
    return {
        "mode": "real_tmux_smoke",
        "remote_host": remote_host,
        "session_id": session_id,
        "source_seq": seq,
        "request_id": raw_event["request_id"],
        "capture_excerpt": capture_excerpt,
        "relay_response": relay_response,
    }


def write_approval_response_to_kimi(
    *,
    session_id: str,
    request_id: str,
    decision: str,
    source_seq: int,
    remote: str | None = None,
) -> dict[str, object]:
    provider_action = "approve_request" if decision == "approve" else "reject_request"
    if remote and session_id.startswith(_REAL_REMOTE_SESSION_PREFIX):
        _maybe_raise_forced_remote_writeback_failure(
            remote=remote,
            session_id=session_id,
            request_id=request_id,
        )
        capture_excerpt = _write_remote_tmux_decision(
            remote_host=remote,
            session_id=session_id,
            decision=decision,
        )
        return _build_provider_writeback(
            remote=remote,
            session_id=session_id,
            request_id=request_id,
            decision=decision,
            provider_action=provider_action,
            source_seq=source_seq,
            mode="real_tmux_smoke",
            result="real_tmux_ok",
            capture_excerpt=capture_excerpt,
        )

    writeback = _build_provider_writeback(
        remote=remote,
        session_id=session_id,
        request_id=request_id,
        decision=decision,
        provider_action=provider_action,
        source_seq=source_seq,
        mode="simulated",
        result="simulated_ok",
    )
    _SIMULATED_WRITEBACKS.append(writeback)
    return dict(writeback)


def list_simulated_writebacks() -> list[dict[str, object]]:
    return [dict(writeback) for writeback in _SIMULATED_WRITEBACKS]


def push_kimi_event_to_relay(
    relay_base_url: str,
    raw_event: Mapping[str, Any],
) -> dict[str, object]:
    normalized_event = normalize_kimi_event(raw_event)
    if normalized_event is None:
        raise ValueError("unsupported Kimi event")

    endpoint = relay_base_url.rstrip("/") + "/v1/kimi/approval-request"
    request_body = json.dumps(normalized_event).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def _build_tmux_kimi_command(*, workdir: str, prompt: str) -> str:
    shell_command = (
        "source ~/.bashrc >/dev/null 2>&1 || true; "
        f"cd {quote(workdir)}; "
        f"kimi -p {quote(prompt)}"
    )
    return f"bash -lc {quote(shell_command)}"


def _build_provider_writeback(
    *,
    remote: str | None,
    session_id: str,
    request_id: str,
    decision: str,
    provider_action: str,
    source_seq: int,
    mode: str,
    result: str,
    capture_excerpt: str | None = None,
) -> dict[str, object]:
    writeback: dict[str, object] = {
        "type": "approval_response_writeback",
        "provider": "kimi",
        "remote": remote,
        "session_id": session_id,
        "request_id": request_id,
        "source_seq": source_seq,
        "decision": decision,
        "provider_action": provider_action,
        "mode": mode,
        "result": result,
    }
    if capture_excerpt:
        writeback["capture_excerpt"] = capture_excerpt
    return writeback


def _write_remote_tmux_decision(
    *,
    remote_host: str,
    session_id: str,
    decision: str,
) -> str:
    keys = ["Enter"] if decision == "approve" else ["Down", "Down", "Enter"]
    send_keys_lines = "\n".join(
        f"tmux send-keys -t {quote(session_id)} {quote(key)}" for key in keys
    )
    script = f"""#!/usr/bin/env bash
set -euo pipefail
ssh {quote(remote_host)} <<'EOSSH'
source ~/.bashrc >/dev/null 2>&1 || true
tmux has-session -t {quote(session_id)}
{send_keys_lines}
attempt=0
while [ "$attempt" -lt {_REMOTE_POLL_ATTEMPTS} ]; do
  capture=$(tmux capture-pane -pt {quote(session_id)} -S -200 || true)
  if ! printf "%s\\n" "$capture" | grep -q "ACTION REQUIRED"; then
    echo "__CAPTURE_BEGIN__"
    printf "%s\\n" "$capture"
    echo "__CAPTURE_END__"
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep {_REMOTE_POLL_INTERVAL_SECONDS}
done
echo "__CAPTURE_BEGIN__"
tmux capture-pane -pt {quote(session_id)} -S -200 || true
echo "__CAPTURE_END__"
echo "approval prompt still present after writeback" >&2
exit 1
EOSSH
"""
    result = _run_wsl_bash_script(script)
    if result.returncode != 0:
        error_text = result.stderr.strip() or result.stdout.strip() or "remote Kimi writeback failed"
        if "approval prompt still present after writeback" in error_text:
            raise TimeoutError(error_text)
        raise RuntimeError(error_text)
    return _extract_marked_block(result.stdout)


def _extract_marked_block(output: str) -> str:
    if output is None:
        return ""

    start_marker = "__CAPTURE_BEGIN__"
    end_marker = "__CAPTURE_END__"
    if start_marker not in output or end_marker not in output:
        return output.strip()

    start_index = output.index(start_marker) + len(start_marker)
    end_index = output.index(end_marker, start_index)
    return output[start_index:end_index].strip()


def _run_wsl_bash_script(script: str) -> subprocess.CompletedProcess[str]:
    script_path = Path(tempfile.gettempdir()) / (
        f"kimi_adapter_{int(time.time() * 1000)}.sh"
    )
    script_path.write_text(script, encoding="utf-8", newline="\n")
    wsl_script_path = _windows_path_to_wsl(script_path)
    try:
        return subprocess.run(
            ["wsl", "-e", "bash", wsl_script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_REMOTE_SCRIPT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError("remote Kimi bridge command timed out") from exc
    finally:
        script_path.unlink(missing_ok=True)


def _windows_path_to_wsl(path: Path) -> str:
    path_text = str(path)
    drive, remainder = path_text[0], path_text[2:]
    return f"/mnt/{drive.lower()}{remainder.replace(chr(92), '/')}"


def _normalize_bridge_segment(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return normalized or "unknown"


def _maybe_raise_forced_remote_writeback_failure(
    *,
    remote: str,
    session_id: str,
    request_id: str,
) -> None:
    failure_mode = os.getenv(_FORCE_WRITEBACK_FAILURE_ENV, "").strip().lower()
    if failure_mode == "":
        return

    message = (
        f"forced remote Kimi writeback failure: remote={remote} "
        f"session_id={session_id} request_id={request_id}"
    )
    if failure_mode == "timeout":
        raise TimeoutError(message)
    if failure_mode == "error":
        raise RuntimeError(message)
