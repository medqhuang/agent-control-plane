"""Minimal relay reporting client for remote-agent standard events."""

from __future__ import annotations

import json
import os
import socket
from dataclasses import dataclass
from dataclasses import field
from typing import Mapping
from urllib import error
from urllib import request

_REMOTE_AGENT_EVENTS_PATH = "/v1/remote-agent/events"


def _default_endpoint() -> str | None:
    return os.environ.get("REMOTE_AGENT_RELAY_ENDPOINT")


def _default_remote_name() -> str:
    return os.environ.get("REMOTE_AGENT_REMOTE_NAME") or socket.getfqdn()


def _default_timeout_seconds() -> float:
    raw_value = os.environ.get("REMOTE_AGENT_RELAY_TIMEOUT_SECONDS")
    if raw_value is None:
        return 5.0
    try:
        return float(raw_value)
    except ValueError:
        return 5.0


@dataclass(slots=True)
class RelayReporter:
    endpoint: str | None = field(default_factory=_default_endpoint)
    remote_name: str = field(default_factory=_default_remote_name)
    timeout_seconds: float = field(default_factory=_default_timeout_seconds)

    def describe(self) -> dict[str, object]:
        event_endpoint = self._event_endpoint()
        return {
            "status": "configured" if event_endpoint is not None else "not_configured",
            "endpoint": self.endpoint,
            "event_endpoint": event_endpoint,
            "remote_name": self.remote_name,
            "timeout_seconds": self.timeout_seconds,
            "entrypoint": "remote_agent.relay.client:RelayReporter",
            "next_step": "relay decision writeback is still pending",
        }

    def post_event(self, event: Mapping[str, object]) -> dict[str, object]:
        event_endpoint = self._event_endpoint()
        event_type = str(event.get("type", ""))
        payload = event.get("payload")
        request_id = ""
        if isinstance(payload, dict):
            request_id = str(payload.get("request_id", ""))

        if event_endpoint is None:
            return {
                "status": "not_configured",
                "accepted": False,
                "event_type": event_type,
                "session_id": str(event.get("session_id", "")),
                "request_id": request_id,
            }

        body = json.dumps(dict(event), ensure_ascii=False).encode("utf-8")
        relay_request = request.Request(
            event_endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        opener = request.build_opener(request.ProxyHandler({}))

        try:
            with opener.open(relay_request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8", errors="replace")
                parsed = json.loads(response_body) if response_body else {}
                return {
                    "status": "delivered",
                    "accepted": 200 <= response.status < 300,
                    "http_status": response.status,
                    "event_type": event_type,
                    "session_id": str(event.get("session_id", "")),
                    "request_id": request_id,
                    "applied": bool(parsed.get("applied", False)),
                }
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            return {
                "status": "http_error",
                "accepted": False,
                "http_status": exc.code,
                "event_type": event_type,
                "session_id": str(event.get("session_id", "")),
                "request_id": request_id,
                "detail": detail,
            }
        except error.URLError as exc:
            return {
                "status": "connection_error",
                "accepted": False,
                "event_type": event_type,
                "session_id": str(event.get("session_id", "")),
                "request_id": request_id,
                "detail": str(exc.reason),
            }

    def _event_endpoint(self) -> str | None:
        if self.endpoint is None:
            return None
        normalized = self.endpoint.rstrip("/")
        if normalized.endswith(_REMOTE_AGENT_EVENTS_PATH):
            return normalized
        return normalized + _REMOTE_AGENT_EVENTS_PATH
