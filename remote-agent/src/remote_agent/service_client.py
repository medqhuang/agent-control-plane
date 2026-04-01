"""HTTP client helpers for talking to the local remote-agent service."""

from __future__ import annotations

import json
import os
from urllib import error
from urllib import request


class RemoteAgentServiceError(RuntimeError):
    """Raised when the local remote-agent service cannot satisfy a request."""


def default_service_base_url() -> str:
    for env_name in ("REMOTE_AGENT_SERVICE_BASE_URL", "REMOTE_AGENT_CONTROL_BASE_URL"):
        configured = os.environ.get(env_name)
        if configured:
            return configured.rstrip("/")
    host = os.environ.get("REMOTE_AGENT_CONTROL_HOST", "127.0.0.1")
    port = os.environ.get("REMOTE_AGENT_PORT", "8711")
    return f"http://{host}:{port}"


def post_json(
    *,
    path: str,
    payload: dict[str, object],
    base_url: str | None = None,
    timeout_seconds: float = 10.0,
) -> dict[str, object]:
    normalized_base_url = (base_url or default_service_base_url()).rstrip("/")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    service_request = request.Request(
        normalized_base_url + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    opener = request.build_opener(request.ProxyHandler({}))
    try:
        with opener.open(service_request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(response_body) if response_body else {}
            if isinstance(parsed, dict):
                return parsed
            raise RemoteAgentServiceError(
                f"unexpected remote-agent response payload for {path}"
            )
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RemoteAgentServiceError(
            f"remote-agent service returned HTTP {exc.code} for {path}: {detail}"
        ) from exc
    except error.URLError as exc:
        raise RemoteAgentServiceError(
            f"remote-agent service is unavailable at {normalized_base_url}: {exc.reason}"
        ) from exc
