"""Minimal in-memory server registry for relay multi-remote support."""

from __future__ import annotations

import json
import os
from typing import Mapping

_REGISTRY_ENV = "RELAY_SERVER_REGISTRY"


class ServerRegistry:
    """Tracks configured and observed remote-agent servers by remote_id."""

    def __init__(self, configured_servers: list[Mapping[str, object]] | None = None) -> None:
        self._servers_by_remote_id: dict[str, dict[str, object]] = {}
        for server in configured_servers or []:
            self._upsert_configured_server(server)

    @classmethod
    def from_env(cls) -> "ServerRegistry":
        raw_value = os.environ.get(_REGISTRY_ENV, "").strip()
        if not raw_value:
            return cls()

        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{_REGISTRY_ENV} must be valid JSON") from exc

        if not isinstance(parsed, list):
            raise RuntimeError(f"{_REGISTRY_ENV} must decode to a list of server objects")

        normalized_servers: list[Mapping[str, object]] = []
        for item in parsed:
            if not isinstance(item, Mapping):
                raise RuntimeError(f"{_REGISTRY_ENV} items must be objects")
            normalized_servers.append(item)
        return cls(normalized_servers)

    def list_servers(self) -> list[dict[str, object]]:
        servers = sorted(
            self._servers_by_remote_id.values(),
            key=lambda item: (str(item.get("display_name", "")), str(item.get("remote_id", ""))),
        )
        return [self._public_server(server) for server in servers]

    def get_server(self, remote_id: str) -> dict[str, object] | None:
        normalized_remote_id = _normalize_remote_id(remote_id)
        if not normalized_remote_id:
            return None

        server = self._servers_by_remote_id.get(normalized_remote_id)
        if server is None:
            return None
        return self._public_server(server)

    def resolve_endpoint(self, remote_id: str) -> str:
        server = self.get_server(remote_id)
        if server is None:
            return ""
        return str(server.get("endpoint", ""))

    def observe_remote_event(self, event: Mapping[str, object]) -> dict[str, object]:
        remote_id = _remote_id_from_record(event)
        provider = _normalize_provider(event.get("provider"))
        endpoint = _endpoint_from_control(event.get("control"))
        updated_at = _normalize_string(event.get("at"))
        event_seq = _normalize_int(event.get("seq"))
        server = self._get_or_create_server(
            remote_id=remote_id,
            display_name=remote_id,
            endpoint=endpoint,
            providers=[provider] if provider else [],
            current_provider=provider,
            configured=False,
        )
        self._observe_server(
            server,
            endpoint=endpoint,
            provider=provider,
            updated_at=updated_at,
            event_seq=event_seq,
        )
        return self._public_server(server)

    def observe_approval_request(self, event: Mapping[str, object]) -> dict[str, object]:
        remote_id = _remote_id_from_record(event)
        provider = _normalize_provider(event.get("provider"))
        updated_at = _normalize_string(event.get("at"))
        event_seq = _normalize_int(event.get("seq"))
        server = self._get_or_create_server(
            remote_id=remote_id,
            display_name=remote_id,
            endpoint="",
            providers=[provider] if provider else [],
            current_provider=provider,
            configured=False,
        )
        self._observe_server(
            server,
            endpoint="",
            provider=provider,
            updated_at=updated_at,
            event_seq=event_seq,
        )
        return self._public_server(server)

    def enrich_session(self, session: Mapping[str, object]) -> dict[str, object]:
        enriched = dict(session)
        remote_id = _remote_id_from_record(session)
        if not remote_id:
            return enriched

        enriched["remote"] = remote_id
        enriched["remote_id"] = remote_id
        server = self.get_server(remote_id)
        if server is not None:
            enriched["server"] = server
        return enriched

    def enrich_approval(self, approval: Mapping[str, object]) -> dict[str, object]:
        enriched = dict(approval)
        remote_id = _remote_id_from_record(approval)
        if not remote_id:
            return enriched

        enriched["remote"] = remote_id
        enriched["remote_id"] = remote_id
        server = self.get_server(remote_id)
        if server is not None:
            enriched["server"] = server
        return enriched

    def _upsert_configured_server(self, raw_server: Mapping[str, object]) -> None:
        remote_id = _normalize_remote_id(raw_server.get("remote_id"))
        if not remote_id:
            raise RuntimeError("configured relay server entry must define non-empty remote_id")

        providers = _normalize_providers(raw_server.get("providers"))
        current_provider = _normalize_provider(raw_server.get("current_provider"))
        if not current_provider and providers:
            current_provider = providers[0]

        server = self._get_or_create_server(
            remote_id=remote_id,
            display_name=_normalize_string(raw_server.get("display_name")) or remote_id,
            endpoint=_normalize_endpoint(raw_server),
            providers=providers,
            current_provider=current_provider,
            configured=True,
        )
        server["status"]["configured"] = True
        server["status"]["writeback_ready"] = bool(server["endpoint"])

    def _get_or_create_server(
        self,
        *,
        remote_id: str,
        display_name: str,
        endpoint: str,
        providers: list[str],
        current_provider: str,
        configured: bool,
    ) -> dict[str, object]:
        server = self._servers_by_remote_id.get(remote_id)
        if server is not None:
            return server

        server = {
            "remote_id": remote_id,
            "display_name": display_name or remote_id,
            "endpoint": endpoint,
            "providers": list(providers),
            "current_provider": current_provider,
            "status": {
                "configured": configured,
                "event_seen": False,
                "writeback_ready": bool(endpoint),
            },
            "last_event_at": "",
            "last_event_seq": 0,
        }
        self._servers_by_remote_id[remote_id] = server
        return server

    def _observe_server(
        self,
        server: dict[str, object],
        *,
        endpoint: str,
        provider: str,
        updated_at: str,
        event_seq: int,
    ) -> None:
        if endpoint:
            server["endpoint"] = endpoint

        if provider:
            current_providers = list(server.get("providers", []))
            if provider not in current_providers:
                current_providers.append(provider)
                server["providers"] = current_providers
            server["current_provider"] = provider

        status = server["status"]
        if isinstance(status, dict):
            status["event_seen"] = True
            status["writeback_ready"] = bool(server.get("endpoint", ""))

        if updated_at:
            server["last_event_at"] = updated_at

        previous_seq = _normalize_int(server.get("last_event_seq"))
        if event_seq > previous_seq:
            server["last_event_seq"] = event_seq

    def _public_server(self, server: Mapping[str, object]) -> dict[str, object]:
        raw_status = server.get("status")
        status = dict(raw_status) if isinstance(raw_status, Mapping) else {}
        providers = _normalize_providers(server.get("providers"))
        return {
            "remote_id": _normalize_remote_id(server.get("remote_id")),
            "display_name": _normalize_string(server.get("display_name")),
            "endpoint": _normalize_string(server.get("endpoint")),
            "providers": providers,
            "current_provider": _normalize_provider(server.get("current_provider")),
            "status": {
                "configured": bool(status.get("configured", False)),
                "event_seen": bool(status.get("event_seen", False)),
                "writeback_ready": bool(status.get("writeback_ready", False)),
            },
            "last_event_at": _normalize_string(server.get("last_event_at")),
            "last_event_seq": _normalize_int(server.get("last_event_seq")),
        }


def _normalize_string(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_remote_id(value: object) -> str:
    return _normalize_string(value)


def _normalize_provider(value: object) -> str:
    return _normalize_string(value).lower()


def _normalize_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _normalize_providers(raw_value: object) -> list[str]:
    if isinstance(raw_value, str):
        provider = _normalize_provider(raw_value)
        return [provider] if provider else []

    if not isinstance(raw_value, list):
        return []

    normalized: list[str] = []
    for item in raw_value:
        provider = _normalize_provider(item)
        if provider and provider not in normalized:
            normalized.append(provider)
    return normalized


def _normalize_endpoint(raw_server: Mapping[str, object]) -> str:
    for key in ("endpoint", "base_url", "control_base_url"):
        endpoint = _normalize_string(raw_server.get(key))
        if endpoint:
            return endpoint.rstrip("/")
    return ""


def _endpoint_from_control(raw_control: object) -> str:
    if not isinstance(raw_control, Mapping):
        return ""
    endpoint = _normalize_string(raw_control.get("base_url"))
    if not endpoint:
        return ""
    return endpoint.rstrip("/")


def _remote_id_from_record(record: Mapping[str, object]) -> str:
    remote_id = _normalize_remote_id(record.get("remote_id"))
    if remote_id:
        return remote_id
    return _normalize_remote_id(record.get("remote"))


_REGISTRY = ServerRegistry.from_env()


def list_servers() -> list[dict[str, object]]:
    return _REGISTRY.list_servers()


def get_server(remote_id: str) -> dict[str, object] | None:
    return _REGISTRY.get_server(remote_id)


def resolve_server_endpoint(remote_id: str) -> str:
    return _REGISTRY.resolve_endpoint(remote_id)


def observe_remote_event(event: Mapping[str, object]) -> dict[str, object]:
    return _REGISTRY.observe_remote_event(event)


def observe_approval_request(event: Mapping[str, object]) -> dict[str, object]:
    return _REGISTRY.observe_approval_request(event)


def enrich_session(session: Mapping[str, object]) -> dict[str, object]:
    return _REGISTRY.enrich_session(session)


def enrich_approval(approval: Mapping[str, object]) -> dict[str, object]:
    return _REGISTRY.enrich_approval(approval)


__all__ = [
    "enrich_approval",
    "enrich_session",
    "get_server",
    "list_servers",
    "observe_approval_request",
    "observe_remote_event",
    "resolve_server_endpoint",
    "ServerRegistry",
]
