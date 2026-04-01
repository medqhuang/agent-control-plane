"""Minimal control client for relay -> remote-agent writeback."""

from __future__ import annotations

import json
import socket
from typing import Mapping
from urllib import error
from urllib import request

from relay.server_registry import resolve_server_endpoint


class RemoteAgentHttpError(RuntimeError):
    """Raised when remote-agent responds with a non-2xx HTTP status."""

    def __init__(
        self,
        message: str,
        *,
        http_status: int,
        detail: str,
        base_url: str,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.detail = detail
        self.base_url = base_url


def post_approval_response(
    *,
    session: Mapping[str, object],
    request_id: str,
    decision: str,
    feedback: str = "",
    timeout_seconds: float = 10.0,
) -> dict[str, object]:
    payload = {
        "request_id": request_id,
        "decision": decision,
        "feedback": feedback,
    }
    response = _request_remote_agent_json(
        session=session,
        path="/v1/approval-response",
        method="POST",
        payload=payload,
        timeout_seconds=timeout_seconds,
    )
    return {
        "status": "written",
        "base_url": response["base_url"],
        "http_status": response["http_status"],
        "result": response["result"],
    }


def get_session_detail(
    *,
    session: Mapping[str, object],
    timeout_seconds: float = 10.0,
) -> dict[str, object]:
    response = _request_remote_agent_json(
        session=session,
        path=f"/v1/sessions/{session['id']}",
        method="GET",
        timeout_seconds=timeout_seconds,
    )
    return {
        "status": "read",
        "base_url": response["base_url"],
        "http_status": response["http_status"],
        "result": response["result"],
    }


def _request_remote_agent_json(
    *,
    session: Mapping[str, object],
    path: str,
    method: str,
    payload: Mapping[str, object] | None = None,
    timeout_seconds: float = 10.0,
) -> dict[str, object]:
    base_url = _resolve_base_url(session)
    body: bytes | None = None
    if payload is not None:
        body = json.dumps(
            dict(payload),
            ensure_ascii=False,
        ).encode("utf-8")

    service_request = request.Request(
        base_url + path,
        data=body,
        headers={
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
        method=method,
    )
    opener = request.build_opener(request.ProxyHandler({}))

    try:
        with opener.open(service_request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(response_body) if response_body else {}
            if not isinstance(parsed, dict):
                raise RuntimeError("remote-agent returned a non-object response")
            return {
                "base_url": base_url,
                "http_status": response.status,
                "result": parsed,
            }
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RemoteAgentHttpError(
            f"remote-agent request failed with HTTP {exc.code}: {detail}",
            http_status=exc.code,
            detail=detail,
            base_url=base_url,
        ) from exc
    except error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, socket.timeout):
            raise TimeoutError(f"remote-agent request timed out via {base_url}") from exc
        raise RuntimeError(
            f"remote-agent connection failed via {base_url}: {reason}"
        ) from exc


def _resolve_base_url(session: Mapping[str, object]) -> str:
    control = session.get("control")
    base_url = ""
    if isinstance(control, Mapping):
        base_url = str(control.get("base_url", "")).rstrip("/")
    if not base_url:
        remote_id = str(session.get("remote_id") or session.get("remote") or "").strip()
        base_url = resolve_server_endpoint(remote_id).rstrip("/")
    if not base_url:
        raise RuntimeError("remote-agent control base_url is missing")
    return base_url
