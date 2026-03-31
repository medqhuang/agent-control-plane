"""Placeholder Kimi worker for the remote-agent foundation."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from uuid import uuid4

from remote_agent.relay.client import RelayReporter


def build_kimi_start_result(
    task: str,
    *,
    relay_reporter: RelayReporter | None = None,
) -> dict[str, object]:
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    session_id = f"kimi-{uuid4().hex[:12]}"
    reporter = relay_reporter or RelayReporter()
    return {
        "type": "kimi_start_result",
        "accepted": True,
        "provider": "kimi",
        "task": task,
        "session": {
            "session_id": session_id,
            "provider": "kimi",
            "state": "starting",
            "created_at": created_at,
        },
        "worker": {
            "status": "placeholder_started",
            "mode": "placeholder",
            "transport": "planned:kimi --wire",
            "entrypoint": "remote_agent.providers.kimi.worker:build_kimi_start_result",
            "next_step": "replace placeholder task acceptance with real kimi --wire process management",
        },
        "supervisor": {
            "status": "accepted",
            "entrypoint": "remote_agent.supervisor.runtime:SupervisorRuntime",
        },
        "relay": reporter.describe(),
    }
