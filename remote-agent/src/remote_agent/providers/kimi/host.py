"""Hosted Kimi session runtime for remote-agent service mode."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from pathlib import Path
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


class SessionOperationError(RuntimeError):
    """Raised when a hosted session cannot perform the requested operation."""


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
        self.updated_at = self.started_at

        self.state = "starting"
        self.worker_status = "starting"
        self.last_error: str | None = None
        self.command: list[str] = []
        self.wire_info: dict[str, object] = {}
        self.lifecycle_events: list[dict[str, object]] = []
        self.raw_event_types: list[str] = []
        self.stderr_lines: list[str] = []
        self.transport_notes: list[str] = []
        self.relay_deliveries: list[dict[str, object]] = []
        self.approval_request: dict[str, object] | None = None
        self.prompt_result: dict[str, object] | None = None
        self.last_turn: dict[str, object] | None = None
        self.process: asyncio.subprocess.Process | None = None
        self.stderr_task: asyncio.Task[None] | None = None
        self.turn_count = 0
        self.pending_request_id = ""
        self.stopped_at: str | None = None

        self._turn_lock = asyncio.Lock()
        self._decision_future: asyncio.Future[dict[str, str]] | None = None
        self._decision_writeback_future: asyncio.Future[dict[str, object]] | None = None
        self._continuation_task: asyncio.Task[None] | None = None
        self._turn_progress_emitted = False
        self._closed = False

    async def start(self) -> dict[str, object]:
        try:
            await self._ensure_process_started()
        except Exception as exc:
            self.state = "failed"
            self.worker_status = "unavailable"
            self.last_error = str(exc)
            self.transport_notes.append(str(exc))
            return self._build_turn_result(
                action="start",
                message=self.task,
                accepted=False,
            )

        try:
            return await self._run_turn(message=self.task, action="start")
        except Exception as exc:
            self.last_error = str(exc)
            self.transport_notes.append(str(exc))
            await self._close_session(
                final_state="failed",
                worker_status="turn_failed",
                emit_finished_status="failed",
            )
            return self._build_turn_result(
                action="start",
                message=self.task,
                accepted=False,
            )

    async def reply(self, *, message: str) -> dict[str, object]:
        if self._closed:
            raise SessionOperationError(f"session {self.session_id} is already stopped")
        if self.state == "approval_pending":
            raise SessionOperationError(
                f"session {self.session_id} is waiting for approval; resolve approval first"
            )
        if self.state == "running":
            raise SessionOperationError(
                f"session {self.session_id} already has a turn in progress"
            )
        if self.state not in {"idle", "finished"}:
            raise SessionOperationError(
                f"session {self.session_id} is not ready for reply (state={self.state})"
            )

        try:
            return await self._run_turn(message=message, action="reply")
        except Exception as exc:
            self.last_error = str(exc)
            self.transport_notes.append(str(exc))
            await self._close_session(
                final_state="failed",
                worker_status="turn_failed",
                emit_finished_status="failed",
            )
            raise SessionOperationError(str(exc)) from exc

    async def submit_decision(
        self,
        *,
        request_id: str,
        decision: str,
        feedback: str = "",
    ) -> dict[str, object]:
        if request_id != self.pending_request_id or self._decision_future is None:
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

    async def stop(self) -> dict[str, object]:
        if self._closed:
            return {
                "type": "session_stop_result",
                "accepted": True,
                "session": self.snapshot(),
                "message": "session already stopped",
            }
        # Keep hosted-session state aligned with relay-side pending approval state.
        if self.state == "approval_pending":
            raise SessionOperationError(
                f"session {self.session_id} is waiting for approval; stop would leave relay approval state inconsistent"
            )
        if self.state == "running":
            raise SessionOperationError(
                f"session {self.session_id} has a turn in progress; wait for the turn to finish before stopping"
            )

        await self._close_session(
            final_state="stopped",
            worker_status="stopped",
            emit_finished_status=None,
        )
        return {
            "type": "session_stop_result",
            "accepted": True,
            "session": self.snapshot(),
            "message": "session stopped",
        }

    def snapshot(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "provider": "kimi",
            "title": self.task,
            "state": self.state,
            "created_at": self.started_at,
            "updated_at": self.updated_at,
            "stopped_at": self.stopped_at,
            "workdir": self.workdir,
            "turn_count": self.turn_count,
            "pending_request_id": self.pending_request_id,
            "last_turn": dict(self.last_turn or {}),
            "error": self.last_error,
        }

    def summary(self) -> dict[str, object]:
        last_turn = self.last_turn or {}
        return {
            "session_id": self.session_id,
            "provider": "kimi",
            "title": self.task,
            "state": self.state,
            "created_at": self.started_at,
            "updated_at": self.updated_at,
            "workdir": self.workdir,
            "turn_count": self.turn_count,
            "pending_request_id": self.pending_request_id,
            "last_turn_status": last_turn.get("status"),
            "last_turn_message": last_turn.get("message"),
        }

    def detail(self) -> dict[str, object]:
        return {
            "type": "session_watch_result",
            "session": self.snapshot(),
            "events": [dict(event) for event in self.lifecycle_events],
            "provider_observation": {
                "raw_event_types": list(self.raw_event_types),
                "approval_request": dict(self.approval_request or {}),
                "prompt_result": dict(self.prompt_result or {}),
                "stderr_tail": self.stderr_lines[-20:],
                "notes": list(self.transport_notes),
            },
            "relay": {
                **self.reporter.describe(),
                "delivery_count": len(self.relay_deliveries),
                "deliveries": list(self.relay_deliveries),
            },
        }

    async def _ensure_process_started(self) -> None:
        if self.process is not None:
            return

        kimi_executable = _resolve_kimi_bin(self.kimi_bin)
        self.wire_info = await _get_kimi_wire_info(kimi_executable)
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
        await _send_json_message(
            self.process,
            {
                "jsonrpc": "2.0",
                "id": init_id,
                "method": "initialize",
                "params": {
                    "protocol_version": str(self.wire_info.get("protocol_version", "1.8")),
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

        self.state = "idle"
        self.worker_status = "ready"
        self.updated_at = _utc_now()

    async def _run_turn(
        self,
        *,
        message: str,
        action: str,
    ) -> dict[str, object]:
        if self.process is None:
            raise KimiWorkerError("kimi --wire process is unavailable")

        async with self._turn_lock:
            if self._closed:
                raise SessionOperationError(f"session {self.session_id} is already stopped")
            if self.state == "approval_pending":
                raise SessionOperationError(
                    f"session {self.session_id} is waiting for approval; resolve approval first"
                )
            if self._continuation_task is not None and not self._continuation_task.done():
                raise SessionOperationError(
                    f"session {self.session_id} is still completing the previous turn"
                )

            self.turn_count += 1
            turn_index = self.turn_count
            turn_started_at = _utc_now()
            prompt_id = f"{self.session_id}-prompt-{turn_index}"
            self.prompt_result = {}
            self.approval_request = None
            self.pending_request_id = ""
            self.last_error = None
            self._decision_future = None
            self._decision_writeback_future = None
            self._turn_progress_emitted = False
            self.state = "running"
            self.worker_status = "turn_running"
            self.updated_at = turn_started_at
            self.last_turn = {
                "turn_index": turn_index,
                "action": action,
                "message": message,
                "status": "running",
                "started_at": turn_started_at,
                "completed_at": None,
                "approval_request": {},
                "prompt_result": {},
            }

            await _send_json_message(
                self.process,
                {
                    "jsonrpc": "2.0",
                    "id": prompt_id,
                    "method": "prompt",
                    "params": {
                        "user_input": message,
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
                        await self._handle_approval_request(
                            msg=msg,
                            prompt_id=prompt_id,
                            turn_index=turn_index,
                            action=action,
                            message=message,
                            turn_started_at=turn_started_at,
                        )
                        return self._build_turn_result(action=action, message=message)

                    self.transport_notes.append(
                        f"unhandled wire request type: {request_type or 'unknown'}"
                    )
                    continue

                if str(msg.get("id")) == prompt_id:
                    if "error" in msg:
                        raise KimiWorkerError(f"kimi --wire prompt failed: {msg['error']}")
                    self.prompt_result = dict(msg.get("result") or {})
                    await self._append_finished_event()
                    completed_at = _utc_now()
                    self.state = "idle"
                    self.worker_status = "turn_finished"
                    self.updated_at = completed_at
                    self.last_turn = {
                        "turn_index": turn_index,
                        "action": action,
                        "message": message,
                        "status": str(self.prompt_result.get("status", "finished")),
                        "started_at": turn_started_at,
                        "completed_at": completed_at,
                        "approval_request": {},
                        "prompt_result": dict(self.prompt_result),
                    }
                    return self._build_turn_result(action=action, message=message)

                self.transport_notes.append(
                    f"unrecognized wire message: {json.dumps(msg, ensure_ascii=False)}"
                )

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

        if not self._turn_progress_emitted and provider_event_type in {
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
            self._turn_progress_emitted = True
        self.updated_at = _utc_now()

    async def _handle_approval_request(
        self,
        *,
        msg: dict[str, object],
        prompt_id: str,
        turn_index: int,
        action: str,
        message: str,
        turn_started_at: str,
    ) -> None:
        self.approval_request = _normalize_approval_request(msg)
        self.pending_request_id = str(self.approval_request.get("request_id", ""))
        self._decision_future = asyncio.get_running_loop().create_future()
        self._decision_writeback_future = asyncio.get_running_loop().create_future()
        self.on_pending_approval(self.pending_request_id, self.session_id)
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
        self.updated_at = _utc_now()
        self.last_turn = {
            "turn_index": turn_index,
            "action": action,
            "message": message,
            "status": "approval_pending",
            "started_at": turn_started_at,
            "completed_at": None,
            "approval_request": dict(self.approval_request),
            "prompt_result": {},
        }
        self._continuation_task = asyncio.create_task(
            self._continue_after_approval(
                prompt_id=prompt_id,
                turn_index=turn_index,
                action=action,
                message=message,
                turn_started_at=turn_started_at,
            )
        )

    async def _continue_after_approval(
        self,
        *,
        prompt_id: str,
        turn_index: int,
        action: str,
        message: str,
        turn_started_at: str,
    ) -> None:
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
            self.pending_request_id = ""
            self.approval_request = None
            self.state = "running"
            self.worker_status = "decision_written"
            self.updated_at = _utc_now()
            if self._decision_writeback_future is not None:
                self._decision_writeback_future.set_result(
                    {
                        "status": "written",
                        "provider": "kimi",
                        "transport": "kimi --wire",
                        "session_id": self.session_id,
                        "request_id": decision_payload["request_id"],
                        "decision": decision_payload["decision"],
                        "responded_at": self.updated_at,
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
                    completed_at = _utc_now()
                    self.state = "idle"
                    self.worker_status = "turn_finished"
                    self.updated_at = completed_at
                    self.last_turn = {
                        "turn_index": turn_index,
                        "action": action,
                        "message": message,
                        "status": str(self.prompt_result.get("status", "finished")),
                        "started_at": turn_started_at,
                        "completed_at": completed_at,
                        "approval_request": {},
                        "prompt_result": dict(self.prompt_result),
                    }
                    return
        except Exception as exc:
            self.last_error = str(exc)
            self.transport_notes.append(str(exc))
            if (
                self._decision_writeback_future is not None
                and not self._decision_writeback_future.done()
            ):
                self._decision_writeback_future.set_exception(exc)
            await self._close_session(
                final_state="failed",
                worker_status="turn_failed",
                emit_finished_status="failed",
            )
        finally:
            self._continuation_task = None

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

    async def _close_session(
        self,
        *,
        final_state: str,
        worker_status: str,
        emit_finished_status: str | None,
    ) -> None:
        if self._closed:
            return
        self._closed = True

        if emit_finished_status is not None:
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
                    "status": emit_finished_status,
                },
            )

        if self.pending_request_id:
            self.on_approval_cleared(self.pending_request_id)
            self.pending_request_id = ""

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

        self.state = final_state
        self.worker_status = worker_status
        self.stopped_at = _utc_now() if final_state == "stopped" else self.stopped_at
        self.updated_at = _utc_now()
        self.on_session_terminal(self.session_id)

    def _build_turn_result(
        self,
        *,
        action: str,
        message: str,
        accepted: bool = True,
    ) -> dict[str, object]:
        return {
            "type": "kimi_start_result" if action == "start" else "session_reply_result",
            "accepted": accepted,
            "provider": "kimi",
            "action": action,
            "message": message,
            "session": self.snapshot(),
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
            "turn": dict(self.last_turn or {}),
            "events": [dict(event) for event in self.lifecycle_events],
            "provider_observation": {
                "raw_event_types": list(self.raw_event_types),
                "approval_request": dict(self.approval_request or {}),
                "prompt_result": dict(self.prompt_result or {}),
                "stderr_tail": self.stderr_lines[-20:],
                "notes": list(self.transport_notes),
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
