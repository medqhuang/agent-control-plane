"""Minimal in-memory server registry for relay multi-remote support."""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
import json
import os
from time import monotonic
from typing import Mapping
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import Request
from urllib.request import urlopen

_REGISTRY_ENV = "RELAY_SERVER_REGISTRY"
_REMOTE_DISCONNECT_AFTER_ENV = "RELAY_REMOTE_DISCONNECT_AFTER_SECONDS"
_REMOTE_HEALTHCHECK_TIMEOUT_ENV = "RELAY_REMOTE_HEALTHCHECK_TIMEOUT_SECONDS"
_REMOTE_STATUS_CACHE_SECONDS_ENV = "RELAY_REMOTE_STATUS_CACHE_SECONDS"

_DEFAULT_REMOTE_DISCONNECT_AFTER_SECONDS = 30.0
_DEFAULT_REMOTE_HEALTHCHECK_TIMEOUT_SECONDS = 0.75
_DEFAULT_REMOTE_STATUS_CACHE_SECONDS = 2.0


class ServerRegistry:
    """Tracks configured and observed remote-agent servers by remote_id."""

    def __init__(
        self,
        configured_servers: list[Mapping[str, object]] | None = None,
        *,
        disconnect_after_seconds: float = _DEFAULT_REMOTE_DISCONNECT_AFTER_SECONDS,
        healthcheck_timeout_seconds: float = _DEFAULT_REMOTE_HEALTHCHECK_TIMEOUT_SECONDS,
        status_cache_seconds: float = _DEFAULT_REMOTE_STATUS_CACHE_SECONDS,
    ) -> None:
        self._servers_by_remote_id: dict[str, dict[str, object]] = {}
        self._disconnect_after_seconds = max(disconnect_after_seconds, 0.0)
        self._healthcheck_timeout_seconds = max(healthcheck_timeout_seconds, 0.1)
        self._status_cache_seconds = max(status_cache_seconds, 0.0)
        for server in configured_servers or []:
            self._upsert_configured_server(server)

    @classmethod
    def from_env(cls) -> "ServerRegistry":
        disconnect_after_seconds = _read_env_float(
            _REMOTE_DISCONNECT_AFTER_ENV,
            _DEFAULT_REMOTE_DISCONNECT_AFTER_SECONDS,
        )
        healthcheck_timeout_seconds = _read_env_float(
            _REMOTE_HEALTHCHECK_TIMEOUT_ENV,
            _DEFAULT_REMOTE_HEALTHCHECK_TIMEOUT_SECONDS,
        )
        status_cache_seconds = _read_env_float(
            _REMOTE_STATUS_CACHE_SECONDS_ENV,
            _DEFAULT_REMOTE_STATUS_CACHE_SECONDS,
        )
        raw_value = os.environ.get(_REGISTRY_ENV, "").strip()
        if not raw_value:
            return cls(
                disconnect_after_seconds=disconnect_after_seconds,
                healthcheck_timeout_seconds=healthcheck_timeout_seconds,
                status_cache_seconds=status_cache_seconds,
            )

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
        return cls(
            normalized_servers,
            disconnect_after_seconds=disconnect_after_seconds,
            healthcheck_timeout_seconds=healthcheck_timeout_seconds,
            status_cache_seconds=status_cache_seconds,
        )

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
        normalized_remote_id = _normalize_remote_id(remote_id)
        if not normalized_remote_id:
            return ""

        server = self._servers_by_remote_id.get(normalized_remote_id)
        if server is None:
            return ""
        return _normalize_string(server.get("endpoint"))

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
            "_connection_checked_at_monotonic": 0.0,
            "_connection": "unreachable",
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
        connection = self._get_connection_status(server)
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
                "connection": connection,
            },
            "last_event_at": _normalize_string(server.get("last_event_at")),
            "last_event_seq": _normalize_int(server.get("last_event_seq")),
        }

    def _get_connection_status(self, server: Mapping[str, object]) -> str:
        checked_at = _normalize_float(server.get("_connection_checked_at_monotonic"))
        cached_connection = _normalize_connection(server.get("_connection"))
        now_monotonic = monotonic()
        if (
            cached_connection
            and checked_at > 0.0
            and (now_monotonic - checked_at) <= self._status_cache_seconds
        ):
            return cached_connection

        connection = self._probe_or_infer_connection(server)
        if isinstance(server, dict):
            server["_connection"] = connection
            server["_connection_checked_at_monotonic"] = now_monotonic
        return connection

    def _probe_or_infer_connection(self, server: Mapping[str, object]) -> str:
        endpoint = _normalize_string(server.get("endpoint"))
        status = server.get("status")
        event_seen = bool(status.get("event_seen", False)) if isinstance(status, Mapping) else False

        if endpoint:
            if _remote_healthcheck_ok(
                endpoint,
                timeout_seconds=self._healthcheck_timeout_seconds,
            ):
                return "connected"
            return "disconnected" if event_seen else "unreachable"

        if not event_seen:
            return "unreachable"

        last_event_at = _parse_timestamp(server.get("last_event_at"))
        if last_event_at is None:
            return "disconnected"

        age_seconds = (_utcnow() - last_event_at).total_seconds()
        if age_seconds <= self._disconnect_after_seconds:
            return "connected"
        return "disconnected"


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


def _normalize_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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


def _normalize_connection(value: object) -> str:
    normalized = _normalize_string(value).lower()
    if normalized in {"connected", "disconnected", "unreachable"}:
        return normalized
    return ""


def _parse_timestamp(value: object) -> datetime | None:
    normalized = _normalize_string(value)
    if not normalized:
        return None

    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _read_env_float(name: str, default: float) -> float:
    raw_value = os.environ.get(name, "").strip()
    if not raw_value:
        return default

    try:
        parsed = float(raw_value)
    except ValueError:
        return default

    return parsed if parsed >= 0 else default


def _remote_healthcheck_ok(endpoint: str, *, timeout_seconds: float) -> bool:
    healthz_url = endpoint.rstrip("/") + "/healthz"
    request = Request(
        healthz_url,
        method="GET",
        headers={"Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return 200 <= int(getattr(response, "status", 0)) < 300
    except (HTTPError, URLError, OSError, ValueError):
        return False


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
