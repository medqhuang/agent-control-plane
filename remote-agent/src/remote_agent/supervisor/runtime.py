"""Placeholder supervisor runtime for the remote-agent foundation."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from remote_agent import __version__
from remote_agent.providers.kimi.worker import build_kimi_start_result
from remote_agent.relay.client import RelayReporter


@dataclass(slots=True)
class SupervisorRuntime:
    relay_reporter: RelayReporter = field(default_factory=RelayReporter)

    def describe(self) -> dict[str, object]:
        return {
            "service": "remote-agent",
            "version": __version__,
            "supervisor": {
                "status": "placeholder",
                "entrypoint": "remote_agent.supervisor.runtime:SupervisorRuntime",
                "responsibility": "session lifecycle and provider worker orchestration",
            },
            "providers": {
                "kimi": {
                    "status": "enabled_placeholder",
                    "transport": "planned:kimi --wire",
                    "worker_entrypoint": "remote_agent.providers.kimi.worker:build_kimi_start_result",
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
            },
        }

    def start_kimi_task(self, *, task: str) -> dict[str, object]:
        return build_kimi_start_result(
            task=task,
            relay_reporter=self.relay_reporter,
        )
