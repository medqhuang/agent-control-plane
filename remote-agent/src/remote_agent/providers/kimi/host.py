"""Hosted Kimi session runtime for remote-agent service mode."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from remote_agent import __version__
from remote_agent.providers.kimi.worker import DEFAULT_TIMEOUT_SECONDS
from remote_agent.providers.kimi.worker import KimiWorkerError
from remote_agent.providers.kimi.worker import _append_lifecycle_event
from remote_agent.providers.kimi.worker import _drain_stderr
from remote_agent.providers.kimi.worker import _get_kimi_wire_info
from remote_agent.providers.kimi.worker import _get_message_type
from remote_agent.providers.kimi.worker import _normalize_approval_request
from remote_agent.providers.kimi.worker import _read_json_message
from remote_agent.providers.kimi.worker import _resolve_kimi_bin
from remote_agent.providers.kimi.worker import _send_json_message
from remote_agent.providers.kimi.worker import _stop_process
from remote_agent.providers.kimi.worker import _utc_now
from remote_agent.relay.client import RelayReporter


class ApprovalNotPendingError(LookupError):
    """Raised when a decision targets an unknown or inactive approval request."""


class KimiWritebackError(RuntimeError):
    """Raised when remote-agent cannot write a decision back to Kimi."""


class HostedKimiSession:
    """Owns one hosted `kimi --wire` process inside remote-agent serve."""

    def __init__(
        self,
        *,
        task: str,
        reporter: RelayReporter,
        on_pending_approval: Callable[[str, str], None],
        on_approval_cleared: Callable[[str], None],
        on_session_terminal: Callable[[str], None],
        workdir: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        kimi_bin: str | None = None,
    ) -> None:
        self.task = task
        self.reporter = reporter
        self.on_pending_approval = on_pending_approval
        self.on_approval_cleared = on_approval_cleared
        self.on_session_terminal = on_session_terminal
        self.timeout_seconds = timeout_seconds
        self.kimi_bin = kimi_bin
        self.session_id = f"kimi-{uuid4().hex[:12]}"
        self.workdir = str(Path(workdir or os.getcwd()).resolve())
        self.started_at = _utc_now()

        self.state = "starting"
        self.worker_status = "starting"
        self.command: list[str] = []
        self.wire_info: dict[str, object] = {}
        self.lifecycle_events: list[dict[str, object]] = []
        self.raw_event_types: list[str] = []
        self.stderr_lines: list[str] = []
        self.transport_notes: list[str] = []
        self.relay_deliveries: list[dict[str, object]] = []
        self.approval_request: dict[str, object] | None = None
        self.prompt_result: dict[str, object] | None = None
        self.process: asyncio.subprocess.Process | None = None
        self.stderr_task: asyncio.Task[None] | None = None
        self.progress_emitted = False
        self._decision_future: asyncio.Future[dict[str, str]] | None = None
        self._decision_writeback_future: asyncio.Future[dict[str, object]] | None = None
        self._continuation_task: asyncio.Task[None] | None = None
        self._pending_request_id = ""
        self._finalized = False

    async def start(self) -> dict[str, object]:
        try:
            kimi_executable = _resolve_kimi_bin(self.kimi_bin)
            self.wire_info = await _get_kimi_wire_info(kimi_executable)
        except Exception as exc:
            self.state = "failed"
            self.worker_status = "unavailable"
            self.transport_notes.append(str(exc))
            return self._build_result(accepted=False)

        self.command = [
            str(self.wire_info["binary"]),
            "--wire",
            "--work-dir",
            self.workdir,
        ]
        await _append_lifecycle_event(
            lifecycle_events=self.lifecycle_events,
            reporter=self.reporter,
            relay_deliveries=self.relay_deliveries,
            transport_notes=self.transport_notes,
            task=self.task,
            provider="kimi",
            session_id=self.session_id,
            event_type="session_started",
            payload={
                "provider": "kimi",
                "transport": "kimi --wire",
                "workdir": self.workdir,
            },
        )

        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            cwd=self.workdir,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self.stderr_task = asyncio.create_task(_drain_stderr(self.process, self.stderr_lines))

        init_id = f"{self.session_id}-init"
        prompt_id = f"{self.session_id}-prompt"

        try:
            await _send_json_message(
                self.process,
                {
                    "jsonrpc": "2.0",
                    "id": init_id,
                    "method": "initialize",
                    "params": {
                        "protocol_version": str(
                            self.wire_info.get("protocol_version", "1.8")
                        ),
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
            initialize_response = await self._wait_for_response(init_id)
            if "error" in initialize_response:
                raise KimiWorkerError(
                    f"kimi --wire initialize failed: {initialize_response['error']}"
                )

            await _send_json_message(
                self.process,
                {
                    "jsonrpc": "2.0",
                    "id": prompt_id,
                    "method": "prompt",
                    "params": {
                        "user_input": self.task,
                    },
                },
            )

            while True:
                msg = await _read_json_message(self.process, self.timeout_seconds)
                method = str(msg.get("method") or "")

                if method == "event":
                    await self._handle_event_message(msg)
                    continue

                if method == "request":
                    request_type = _get_message_type(msg)
                    if request_type:
                        self.raw_event_types.append(request_type)

                    if request_type == "ApprovalRequest":
                        await self._handle_approval_request(msg)
                        self._continuation_task = asyncio.create_task(
                            self._continue_after_approval(prompt_id)
                        )
                        return self._build_result()

                    self.transport_notes.append(
                        f"unhandled wire request type: {request_type or 'unknown'}"
                    )
                    continue

                if str(msg.get("id")) == prompt_id:
                    if "error" in msg:
                        raise KimiWorkerError(f"kimi --wire prompt failed: {msg['error']}")
                    self.prompt_result = dict(msg.get("result") or {})
                    await self._append_finished_event()
                    await self._finalize()
                    self.state = "finished"
                    self.worker_status = "finished"
                    return self._build_result()

                if str(msg.get("id")) == init_id:
                    continue

                self.transport_notes.append(
                    f"unrecognized wire message: {json.dumps(msg, ensure_ascii=False)}"
                )
        except TimeoutError as exc:
            self.state = "timed_out"
            self.worker_status = "timeout"
            self.transport_notes.append(str(exc))
            await self._finalize()
            return self._build_result()
        except Exception as exc:
            self.state = "failed"
            self.worker_status = "wire_error"
            self.transport_notes.append(str(exc))
            await self._finalize()
            return self._build_result()

    async def submit_decision(
        self,
        *,
        request_id: str,
        decision: str,
        feedback: str = "",
    ) -> dict[str, object]:
        if request_id != self._pending_request_id or self._decision_future is None:
            raise ApprovalNotPendingError(f"approval request {request_id} is not pending")
        if self._decision_future.done():
            raise KimiWritebackError(f"approval request {request_id} already has a decision")
        if self._decision_writeback_future is None:
            raise KimiWritebackError("decision writeback future is missing")

        self._decision_future.set_result(
            {
                "request_id": request_id,
                "decision": decision,
                "feedback": feedback,
            }
        )
        try:
            return await self._decision_writeback_future
        except Exception as exc:
            raise KimiWritebackError(str(exc)) from exc

    async def _wait_for_response(self, target_id: str) -> dict[str, object]:
        if self.process is None:
            raise KimiWorkerError("kimi --wire process is unavailable")
        while True:
            msg = await _read_json_message(self.process, self.timeout_seconds)
            method = str(msg.get("method") or "")
            if method in {"event", "request"}:
                message_type = _get_message_type(msg)
                if message_type:
                    self.raw_event_types.append(message_type)
                self.transport_notes.append(
                    f"received {method} before response for {target_id}: {message_type or 'unknown'}"
                )
                continue
            if str(msg.get("id")) == target_id:
                return msg

    async def _handle_event_message(self, msg: dict[str, object]) -> None:
        provider_event_type = _get_message_type(msg)
        if provider_event_type:
            self.raw_event_types.append(provider_event_type)

        if not self.progress_emitted and provider_event_type in {
            "StepBegin",
            "StatusUpdate",
            "ToolCall",
            "ToolResult",
            "ContentPart",
        }:
            await _append_lifecycle_event(
                lifecycle_events=self.lifecycle_events,
                reporter=self.reporter,
                relay_deliveries=self.relay_deliveries,
                transport_notes=self.transport_notes,
                task=self.task,
                provider="kimi",
                session_id=self.session_id,
                event_type="session_continued",
                payload={
                    "provider_event_type": provider_event_type,
                },
            )
            self.progress_emitted = True

    async def _handle_approval_request(self, msg: dict[str, object]) -> None:
        self.approval_request = _normalize_approval_request(msg)
        self._pending_request_id = str(self.approval_request.get("request_id", ""))
        self._decision_future = asyncio.get_running_loop().create_future()
        self._decision_writeback_future = asyncio.get_running_loop().create_future()
        self.on_pending_approval(self._pending_request_id, self.session_id)
        await _append_lifecycle_event(
            lifecycle_events=self.lifecycle_events,
            reporter=self.reporter,
            relay_deliveries=self.relay_deliveries,
            transport_notes=self.transport_notes,
            task=self.task,
            provider="kimi",
            session_id=self.session_id,
            event_type="approval_request_observed",
            payload=self.approval_request,
        )
        self.state = "approval_pending"
        self.worker_status = "approval_request_observed"

    async def _continue_after_approval(self, prompt_id: str) -> None:
        try:
            if self.process is None:
                raise KimiWorkerError("kimi --wire process is unavailable")
            if self._decision_future is None:
                raise KimiWorkerError("approval decision future is unavailable")

            decision_payload = await self._decision_future
            await _send_json_message(
                self.process,
                {
                    "jsonrpc": "2.0",
                    "id": decision_payload["request_id"],
                    "result": {
                        "request_id": decision_payload["request_id"],
                        "response": _kimi_response_for_decision(
                            decision_payload["decision"]
                        ),
                        "feedback": decision_payload["feedback"],
                    },
                },
            )
            self.on_approval_cleared(decision_payload["request_id"])
            self._pending_request_id = ""
            self.state = "running"
            self.worker_status = "decision_written"
            if self._decision_writeback_future is not None:
                self._decision_writeback_future.set_result(
                    {
                        "status": "written",
                        "provider": "kimi",
                        "transport": "kimi --wire",
                        "session_id": self.session_id,
                        "request_id": decision_payload["request_id"],
                        "decision": decision_payload["decision"],
                        "responded_at": _utc_now(),
                    }
                )

            while True:
                msg = await _read_json_message(self.process, self.timeout_seconds)
                method = str(msg.get("method") or "")

                if method == "event":
                    await self._handle_event_message(msg)
                    continue

                if method == "request":
                    request_type = _get_message_type(msg)
                    if request_type:
                        self.raw_event_types.append(request_type)
                    self.transport_notes.append(
                        f"unexpected wire request after decision writeback: {request_type or 'unknown'}"
                    )
                    continue

                if str(msg.get("id")) == prompt_id:
                    if "error" in msg:
                        raise KimiWorkerError(f"kimi --wire prompt failed: {msg['error']}")
                    self.prompt_result = dict(msg.get("result") or {})
                    await self._append_finished_event()
                    self.state = "finished"
                    self.worker_status = "finished"
                    return
        except Exception as exc:
            self.transport_notes.append(str(exc))
            self.state = "failed"
            self.worker_status = "writeback_failed"
            if self._decision_writeback_future is not None and not self._decision_writeback_future.done():
                self._decision_writeback_future.set_exception(exc)
        finally:
            await self._finalize()

    async def _append_finished_event(self) -> None:
        await _append_lifecycle_event(
            lifecycle_events=self.lifecycle_events,
            reporter=self.reporter,
            relay_deliveries=self.relay_deliveries,
            transport_notes=self.transport_notes,
            task=self.task,
            provider="kimi",
            session_id=self.session_id,
            event_type="session_finished",
            payload={
                "status": str((self.prompt_result or {}).get("status", "finished")),
            },
        )

    async def _finalize(self) -> None:
        if self._finalized:
            return
        self._finalized = True

        if self._pending_request_id:
            self.on_approval_cleared(self._pending_request_id)
            self._pending_request_id = ""

        if self.process is not None:
            await _stop_process(self.process)

        if self.stderr_task is not None:
            if not self.stderr_task.done():
                self.stderr_task.cancel()
            try:
                await self.stderr_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass

        self.on_session_terminal(self.session_id)

    def _build_result(self, *, accepted: bool = True) -> dict[str, object]:
        return {
            "type": "kimi_start_result",
            "accepted": accepted,
            "provider": "kimi",
            "task": self.task,
            "session": {
                "session_id": self.session_id,
                "provider": "kimi",
                "state": self.state,
                "created_at": self.started_at,
                "workdir": self.workdir,
            },
            "worker": {
                "status": self.worker_status,
                "mode": "hosted_wire",
                "transport": "kimi --wire",
                "timeout_seconds": self.timeout_seconds,
                "entrypoint": "remote_agent.providers.kimi.host:HostedKimiSession",
            },
            "wire": {
                **self.wire_info,
                "command": list(self.command),
            },
            "events": [dict(event) for event in self.lifecycle_events],
            "provider_observation": {
                "raw_event_types": list(self.raw_event_types),
                "approval_request": dict(self.approval_request or {}),
                "prompt_result": dict(self.prompt_result or {}),
                "stderr_tail": self.stderr_lines[-20:],
                "notes": list(self.transport_notes),
            },
            "supervisor": {
                "status": "hosted",
                "entrypoint": "remote_agent.supervisor.runtime:SupervisorRuntime",
            },
            "relay": {
                **self.reporter.describe(),
                "delivery_count": len(self.relay_deliveries),
                "deliveries": list(self.relay_deliveries),
            },
        }


def _kimi_response_for_decision(decision: str) -> str:
    if decision == "approve":
        return "approve"
    if decision == "reject":
        return "reject"
    raise ValueError(f"unsupported approval decision: {decision}")
