"""Placeholder relay reporting client."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RelayReporter:
    endpoint: str | None = None

    def describe(self) -> dict[str, object]:
        return {
            "status": "not_configured",
            "endpoint": self.endpoint,
            "entrypoint": "remote_agent.relay.client:RelayReporter",
            "next_step": "send session state and approval events to relay",
        }
