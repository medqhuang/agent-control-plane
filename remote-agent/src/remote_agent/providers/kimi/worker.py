"""Minimal Kimi worker backed by `kimi --wire`."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from remote_agent import __version__
from remote_agent.relay.client import RelayReporter

DEFAULT_PROTOCOL_VERSION = "1.8"
DEFAULT_TIMEOUT_SECONDS = 90
_KIMI_BIN_ENV = "KIMI_BIN"
_KIMI_BIN_CANDIDATES = (
    "kimi",
    str(Path.home() / ".local" / "bin" / "kimi"),
)


class KimiWorkerError(RuntimeError):
    """Raised when the Kimi wire worker cannot complete startup."""


def start_kimi_task(
    task: str,
    *,
    workdir: str | None = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    kimi_bin: str | None = None,
    relay_reporter: RelayReporter | None = None,
) -> dict[str, object]:
    return asyncio.run(
        _start_kimi_task(
            task=task,
            workdir=workdir,
            timeout_seconds=timeout_seconds,
            kimi_bin=kimi_bin,
            relay_reporter=relay_reporter,
        )
    )


async def _start_kimi_task(
    task: str,
    *,
    workdir: str | None,
    timeout_seconds: int,
    kimi_bin: str | None,
    relay_reporter: RelayReporter | None,
) -> dict[str, object]:
    reporter = relay_reporter or RelayReporter()
    started_at = _utc_now()
    session_id = f"kimi-{uuid4().hex[:12]}"
    resolved_workdir = str(Path(workdir or os.getcwd()).resolve())

    try:
        kimi_executable = _resolve_kimi_bin(kimi_bin)
        wire_info = await _get_kimi_wire_info(kimi_executable)
    except Exception as exc:
        return _build_error_result(
            task=task,
            started_at=started_at,
            session_id=session_id,
            reporter=reporter,
            workdir=resolved_workdir,
            timeout_seconds=timeout_seconds,
            message=str(exc),
        )

    command = [
        kimi_executable,
        "--wire",
        "--work-dir",
        resolved_workdir,
    ]
    raw_event_types: list[str] = []
    lifecycle_events: list[dict[str, object]] = []
    stderr_lines: list[str] = []
    approval_request: dict[str, object] | None = None
    prompt_result: dict[str, object] | None = None
    progress_emitted = False
    transport_notes: list[str] = []
    relay_deliveries: list[dict[str, object]] = []

    await _append_lifecycle_event(
        lifecycle_events=lifecycle_events,
        reporter=reporter,
        relay_deliveries=relay_deliveries,
        transport_notes=transport_notes,
        task=task,
        provider="kimi",
        session_id=session_id,
        event_type="session_started",
        payload={
            "provider": "kimi",
            "transport": "kimi --wire",
            "workdir": resolved_workdir,
        },
    )

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=resolved_workdir,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stderr_task = asyncio.create_task(_drain_stderr(process, stderr_lines))

    init_id = f"{session_id}-init"
    prompt_id = f"{session_id}-prompt"

    try:
        await _send_json_message(
            process,
            {
                "jsonrpc": "2.0",
                "id": init_id,
                "method": "initialize",
                "params": {
                    "protocol_version": wire_info["protocol_version"],
                    "client": {
                        "name": "remote-agent",
                        "version": __version__,
                    },
                    "capabilities": {
                        "supports_question": False,
                        "supports_plan_mode": False,
                    },
                },
            },
        )
        initialize_response = await _wait_for_response(
            process,
            target_id=init_id,
            timeout_seconds=timeout_seconds,
            raw_event_types=raw_event_types,
            transport_notes=transport_notes,
        )
        if "error" in initialize_response:
            raise KimiWorkerError(
                f"kimi --wire initialize failed: {initialize_response['error']}"
            )

        await _send_json_message(
            process,
            {
                "jsonrpc": "2.0",
                "id": prompt_id,
                "method": "prompt",
                "params": {
                    "user_input": task,
                },
            },
        )

        while True:
            msg = await _read_json_message(process, timeout_seconds)
            method = str(msg.get("method") or "")

            if method == "event":
                provider_event_type = _get_message_type(msg)
                if provider_event_type:
                    raw_event_types.append(provider_event_type)

                if not progress_emitted and provider_event_type in {
                    "StepBegin",
                    "StatusUpdate",
                    "ToolCall",
                    "ToolResult",
                    "ContentPart",
                }:
                    await _append_lifecycle_event(
                        lifecycle_events=lifecycle_events,
                        reporter=reporter,
                        relay_deliveries=relay_deliveries,
                        transport_notes=transport_notes,
                        task=task,
                        provider="kimi",
                        session_id=session_id,
                        event_type="session_continued",
                        payload={
                            "provider_event_type": provider_event_type,
                        },
                    )
                    progress_emitted = True
                continue

            if method == "request":
                request_type = _get_message_type(msg)
                if request_type:
                    raw_event_types.append(request_type)

                if request_type == "ApprovalRequest":
                    approval_request = _normalize_approval_request(msg)
                    await _append_lifecycle_event(
                        lifecycle_events=lifecycle_events,
                        reporter=reporter,
                        relay_deliveries=relay_deliveries,
                        transport_notes=transport_notes,
                        task=task,
                        provider="kimi",
                        session_id=session_id,
                        event_type="approval_request_observed",
                        payload=approval_request,
                    )
                    break
                transport_notes.append(
                    f"unhandled wire request type: {request_type or 'unknown'}"
                )
                continue

            if str(msg.get("id")) == prompt_id:
                if "error" in msg:
                    raise KimiWorkerError(f"kimi --wire prompt failed: {msg['error']}")

                prompt_result = dict(msg.get("result") or {})
                await _append_lifecycle_event(
                    lifecycle_events=lifecycle_events,
                    reporter=reporter,
                    relay_deliveries=relay_deliveries,
                    transport_notes=transport_notes,
                    task=task,
                    provider="kimi",
                    session_id=session_id,
                    event_type="session_finished",
                    payload={
                        "status": str(prompt_result.get("status", "finished")),
                    },
                )
                break

            if str(msg.get("id")) == init_id:
                # Duplicate initialize response can be ignored.
                continue

            transport_notes.append(
                f"unrecognized wire message: {json.dumps(msg, ensure_ascii=False)}"
            )
    except TimeoutError as exc:
        transport_notes.append(str(exc))
        return _build_runtime_result(
            task=task,
            session_id=session_id,
            started_at=started_at,
            reporter=reporter,
            workdir=resolved_workdir,
            timeout_seconds=timeout_seconds,
            wire_info=wire_info,
            command=command,
            lifecycle_events=lifecycle_events,
            raw_event_types=raw_event_types,
            stderr_lines=stderr_lines,
            approval_request=approval_request,
            prompt_result=prompt_result,
            state="timed_out",
            worker_status="timeout",
            transport_notes=transport_notes,
            relay_deliveries=relay_deliveries,
        )
    except Exception as exc:
        transport_notes.append(str(exc))
        return _build_runtime_result(
            task=task,
            session_id=session_id,
            started_at=started_at,
            reporter=reporter,
            workdir=resolved_workdir,
            timeout_seconds=timeout_seconds,
            wire_info=wire_info,
            command=command,
            lifecycle_events=lifecycle_events,
            raw_event_types=raw_event_types,
            stderr_lines=stderr_lines,
            approval_request=approval_request,
            prompt_result=prompt_result,
            state="failed",
            worker_status="wire_error",
            transport_notes=transport_notes,
            relay_deliveries=relay_deliveries,
        )
    finally:
        await _stop_process(process)
        if not stderr_task.done():
            stderr_task.cancel()
        try:
            await stderr_task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    final_state = "approval_pending" if approval_request is not None else "finished"
    worker_status = (
        "approval_request_observed" if approval_request is not None else "finished"
    )
    return _build_runtime_result(
        task=task,
        session_id=session_id,
        started_at=started_at,
        reporter=reporter,
        workdir=resolved_workdir,
        timeout_seconds=timeout_seconds,
        wire_info=wire_info,
        command=command,
        lifecycle_events=lifecycle_events,
        raw_event_types=raw_event_types,
        stderr_lines=stderr_lines,
        approval_request=approval_request,
        prompt_result=prompt_result,
        state=final_state,
        worker_status=worker_status,
        transport_notes=transport_notes,
        relay_deliveries=relay_deliveries,
    )


def _build_error_result(
    *,
    task: str,
    started_at: str,
    session_id: str,
    reporter: RelayReporter,
    workdir: str,
    timeout_seconds: int,
    message: str,
) -> dict[str, object]:
    return {
        "type": "kimi_start_result",
        "accepted": False,
        "provider": "kimi",
        "task": task,
        "session": {
            "session_id": session_id,
            "provider": "kimi",
            "state": "failed",
            "created_at": started_at,
            "workdir": workdir,
        },
        "worker": {
            "status": "unavailable",
            "mode": "kimi_wire_required",
            "transport": "kimi --wire",
            "timeout_seconds": timeout_seconds,
            "error": message,
        },
        "relay": {
            **reporter.describe(),
            "delivery_count": 0,
            "deliveries": [],
        },
    }


def _build_runtime_result(
    *,
    task: str,
    session_id: str,
    started_at: str,
    reporter: RelayReporter,
    workdir: str,
    timeout_seconds: int,
    wire_info: dict[str, object],
    command: Sequence[str],
    lifecycle_events: list[dict[str, object]],
    raw_event_types: list[str],
    stderr_lines: list[str],
    approval_request: dict[str, object] | None,
    prompt_result: dict[str, object] | None,
    state: str,
    worker_status: str,
    transport_notes: list[str],
    relay_deliveries: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "type": "kimi_start_result",
        "accepted": True,
        "provider": "kimi",
        "task": task,
        "session": {
            "session_id": session_id,
            "provider": "kimi",
            "state": state,
            "created_at": started_at,
            "workdir": workdir,
        },
        "worker": {
            "status": worker_status,
            "mode": "wire",
            "transport": "kimi --wire",
            "timeout_seconds": timeout_seconds,
            "entrypoint": "remote_agent.providers.kimi.worker:start_kimi_task",
        },
        "wire": {
            **wire_info,
            "command": list(command),
        },
        "events": lifecycle_events,
        "provider_observation": {
            "raw_event_types": raw_event_types,
            "event_type_counts": dict(Counter(raw_event_types)),
            "approval_request": approval_request,
            "prompt_result": prompt_result,
            "stderr_tail": stderr_lines[-20:],
            "notes": transport_notes,
        },
        "supervisor": {
            "status": "accepted",
            "entrypoint": "remote_agent.supervisor.runtime:SupervisorRuntime",
        },
        "relay": {
            **reporter.describe(),
            "delivery_count": len(relay_deliveries),
            "deliveries": relay_deliveries,
        },
    }


async def _append_lifecycle_event(
    *,
    lifecycle_events: list[dict[str, object]],
    reporter: RelayReporter,
    relay_deliveries: list[dict[str, object]],
    transport_notes: list[str],
    task: str,
    provider: str,
    session_id: str,
    event_type: str,
    payload: dict[str, object],
) -> None:
    event = _standard_event(
        seq=len(lifecycle_events) + 1,
        event_type=event_type,
        session_id=session_id,
        payload=payload,
    )
    lifecycle_events.append(event)
    delivery = await asyncio.to_thread(
        reporter.post_event,
        _build_relay_event(
            provider=provider,
            remote=reporter.remote_name,
            title=task,
            event=event,
            control=reporter.build_control_metadata(),
        ),
    )
    relay_deliveries.append(delivery)
    if str(delivery.get("status")) not in {"delivered", "not_configured"}:
        transport_notes.append(
            f"relay delivery failed for seq {event['seq']}: {delivery.get('detail', delivery.get('status'))}"
        )


def _build_relay_event(
    *,
    provider: str,
    remote: str,
    title: str,
    event: dict[str, object],
    control: dict[str, object],
) -> dict[str, object]:
    return {
        "type": str(event["type"]),
        "provider": provider,
        "session_id": str(event["session_id"]),
        "seq": int(event["seq"]),
        "at": str(event["at"]),
        "remote": remote,
        "title": title,
        "payload": _relay_payload_for_event(event),
        "control": dict(control),
    }


def _relay_payload_for_event(event: dict[str, object]) -> dict[str, object]:
    event_type = str(event["type"])
    payload = event.get("payload")
    normalized_payload = payload if isinstance(payload, dict) else {}

    if event_type == "approval_request_observed":
        summary = str(
            normalized_payload.get("description")
            or normalized_payload.get("action")
            or "Approval requested"
        )
        command = str(normalized_payload.get("command", ""))
        return {
            "request_id": str(normalized_payload.get("request_id", "")),
            "kind": "command" if command else "approval",
            "summary": summary,
        }

    if event_type == "session_finished":
        return {
            "status": str(normalized_payload.get("status", "finished")),
        }

    return {
        "status": "running",
    }


def _resolve_kimi_bin(kimi_bin: str | None) -> str:
    candidates = [value for value in (kimi_bin, os.environ.get(_KIMI_BIN_ENV)) if value]
    candidates.extend(_KIMI_BIN_CANDIDATES)
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        if Path(candidate).exists():
            return str(Path(candidate).resolve())
    raise KimiWorkerError(
        "kimi executable not found; expected `kimi --wire` to be available"
    )


async def _get_kimi_wire_info(kimi_bin: str) -> dict[str, object]:
    process = await asyncio.create_subprocess_exec(
        kimi_bin,
        "info",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        error_text = stderr.decode("utf-8", errors="replace").strip()
        raise KimiWorkerError(error_text or "`kimi info` failed")

    info_text = stdout.decode("utf-8", errors="replace")
    cli_version = ""
    protocol_version = DEFAULT_PROTOCOL_VERSION
    for line in info_text.splitlines():
        if line.startswith("kimi-cli version:"):
            cli_version = line.split(":", 1)[1].strip()
        if line.startswith("wire protocol:"):
            protocol_version = line.split(":", 1)[1].strip()
    return {
        "binary": kimi_bin,
        "cli_version": cli_version,
        "protocol_version": protocol_version,
    }


async def _send_json_message(
    process: asyncio.subprocess.Process,
    payload: dict[str, object],
) -> None:
    if process.stdin is None:
        raise KimiWorkerError("kimi --wire stdin is unavailable")
    process.stdin.write(json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n")
    await process.stdin.drain()


async def _wait_for_response(
    process: asyncio.subprocess.Process,
    *,
    target_id: str,
    timeout_seconds: int,
    raw_event_types: list[str],
    transport_notes: list[str],
) -> dict[str, object]:
    while True:
        msg = await _read_json_message(process, timeout_seconds)
        method = str(msg.get("method") or "")
        if method in {"event", "request"}:
            message_type = _get_message_type(msg)
            if message_type:
                raw_event_types.append(message_type)
            transport_notes.append(
                f"received {method} before response for {target_id}: {message_type or 'unknown'}"
            )
            continue
        if str(msg.get("id")) == target_id:
            return msg


async def _read_json_message(
    process: asyncio.subprocess.Process,
    timeout_seconds: int,
) -> dict[str, object]:
    if process.stdout is None:
        raise KimiWorkerError("kimi --wire stdout is unavailable")
    while True:
        try:
            line = await asyncio.wait_for(process.stdout.readline(), timeout=timeout_seconds)
        except asyncio.TimeoutError as exc:
            raise TimeoutError(
                f"kimi --wire did not produce a message within {timeout_seconds} seconds"
            ) from exc
        if not line:
            raise KimiWorkerError("kimi --wire closed stdout unexpectedly")
        text = line.decode("utf-8", errors="replace").strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise KimiWorkerError(f"invalid kimi --wire json line: {text}") from exc
        if not isinstance(parsed, dict):
            raise KimiWorkerError(f"unexpected kimi --wire message: {parsed!r}")
        return parsed


async def _drain_stderr(
    process: asyncio.subprocess.Process,
    sink: list[str],
) -> None:
    if process.stderr is None:
        return
    while True:
        line = await process.stderr.readline()
        if not line:
            break
        sink.append(line.decode("utf-8", errors="replace").rstrip())


async def _stop_process(process: asyncio.subprocess.Process) -> None:
    if process.returncode is not None:
        return
    process.terminate()
    try:
        await asyncio.wait_for(process.wait(), timeout=5)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()


def _get_message_type(msg: dict[str, object]) -> str | None:
    params = msg.get("params")
    if isinstance(params, dict):
        value = params.get("type")
        if isinstance(value, str):
            return value
    return None


def _normalize_approval_request(msg: dict[str, object]) -> dict[str, object]:
    params = msg.get("params")
    payload: dict[str, Any]
    if isinstance(params, dict):
        raw_payload = params.get("payload")
        payload = raw_payload if isinstance(raw_payload, dict) else {}
    else:
        payload = {}

    command = ""
    display = payload.get("display")
    if isinstance(display, list):
        for block in display:
            if isinstance(block, dict) and block.get("type") == "shell":
                maybe_command = block.get("command")
                if isinstance(maybe_command, str):
                    command = maybe_command
                    break

    return {
        "request_id": str(payload.get("id", msg.get("id", ""))),
        "tool_call_id": str(payload.get("tool_call_id", "")),
        "sender": str(payload.get("sender", "")),
        "action": str(payload.get("action", "")),
        "description": str(payload.get("description", "")),
        "command": command,
    }


def _standard_event(
    *,
    seq: int,
    event_type: str,
    session_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    return {
        "seq": seq,
        "type": event_type,
        "session_id": session_id,
        "at": _utc_now(),
        "payload": payload,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
