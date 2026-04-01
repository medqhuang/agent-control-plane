"""Minimal supervisor runtime for the remote-agent foundation."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from remote_agent import __version__
from remote_agent.providers.kimi.host import ApprovalNotPendingError
from remote_agent.providers.kimi.host import HostedKimiSession
from remote_agent.providers.kimi.host import KimiWritebackError
from remote_agent.relay.client import RelayReporter


@dataclass(slots=True)
class SupervisorRuntime:
    relay_reporter: RelayReporter = field(default_factory=RelayReporter)
    sessions_by_id: dict[str, HostedKimiSession] = field(default_factory=dict)
    session_id_by_request_id: dict[str, str] = field(default_factory=dict)

    def describe(self) -> dict[str, object]:
        return {
            "service": "remote-agent",
            "version": __version__,
            "supervisor": {
                "status": "hosted",
                "entrypoint": "remote_agent.supervisor.runtime:SupervisorRuntime",
                "responsibility": "session lifecycle and provider worker orchestration",
                "active_session_count": len(self.sessions_by_id),
                "pending_approval_count": len(self.session_id_by_request_id),
            },
            "providers": {
                "kimi": {
                    "status": "enabled",
                    "transport": "kimi --wire",
                    "worker_entrypoint": "remote_agent.providers.kimi.host:HostedKimiSession",
                }
            },
            "relay": self.relay_reporter.describe(),
        }

    def build_service_snapshot(
        self,
        *,
        host: str,
        port: int,
    ) -> dict[str, object]:
        return {
            **self.describe(),
            "server": {
                "host": host,
                "port": port,
                "health_endpoint": "/healthz",
                "runtime_endpoint": "/v1/runtime",
                "start_endpoint": "/v1/kimi/start",
                "approval_endpoint": "/v1/approval-response",
            },
        }

    async def start_kimi_task(
        self,
        *,
        task: str,
        workdir: str | None = None,
        timeout_seconds: int = 90,
        kimi_bin: str | None = None,
    ) -> dict[str, object]:
        session = HostedKimiSession(
            task=task,
            workdir=workdir,
            timeout_seconds=timeout_seconds,
            kimi_bin=kimi_bin,
            reporter=self.relay_reporter,
            on_pending_approval=self._register_pending_approval,
            on_approval_cleared=self._clear_pending_approval,
            on_session_terminal=self._drop_session,
        )
        self.sessions_by_id[session.session_id] = session
        result = await session.start()
        if str(result.get("session", {}).get("state")) != "approval_pending":
            self._drop_session(session.session_id)
        return result

    async def apply_approval_response(
        self,
        *,
        request_id: str,
        decision: str,
        feedback: str = "",
    ) -> dict[str, object]:
        session_id = self.session_id_by_request_id.get(request_id)
        if session_id is None:
            raise ApprovalNotPendingError(f"approval request {request_id} is not pending")

        session = self.sessions_by_id.get(session_id)
        if session is None:
            self._clear_pending_approval(request_id)
            raise ApprovalNotPendingError(
                f"session {session_id} is unavailable for approval request {request_id}"
            )

        return await session.submit_decision(
            request_id=request_id,
            decision=decision,
            feedback=feedback,
        )

    def _register_pending_approval(self, request_id: str, session_id: str) -> None:
        self.session_id_by_request_id[request_id] = session_id

    def _clear_pending_approval(self, request_id: str) -> None:
        self.session_id_by_request_id.pop(request_id, None)

    def _drop_session(self, session_id: str) -> None:
        self.sessions_by_id.pop(session_id, None)
        stale_request_ids = [
            request_id
            for request_id, mapped_session_id in self.session_id_by_request_id.items()
            if mapped_session_id == session_id
        ]
        for request_id in stale_request_ids:
            self.session_id_by_request_id.pop(request_id, None)


__all__ = [
    "ApprovalNotPendingError",
    "KimiWritebackError",
    "SupervisorRuntime",
]
