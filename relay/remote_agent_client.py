"""Minimal control client for relay -> remote-agent writeback."""

from __future__ import annotations

import json
import socket
from typing import Mapping
from urllib import error
from urllib import request


def post_approval_response(
    *,
    session: Mapping[str, object],
    request_id: str,
    decision: str,
    feedback: str = "",
    timeout_seconds: float = 10.0,
) -> dict[str, object]:
    control = session.get("control")
    if not isinstance(control, Mapping):
        raise RuntimeError("remote-agent control metadata is missing")

    base_url = str(control.get("base_url", "")).rstrip("/")
    if not base_url:
        raise RuntimeError("remote-agent control base_url is missing")

    payload = json.dumps(
        {
            "request_id": request_id,
            "decision": decision,
            "feedback": feedback,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    service_request = request.Request(
        base_url + "/v1/approval-response",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    opener = request.build_opener(request.ProxyHandler({}))

    try:
        with opener.open(service_request, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(response_body) if response_body else {}
            if not isinstance(parsed, dict):
                raise RuntimeError("remote-agent returned a non-object response")
            return {
                "status": "written",
                "base_url": base_url,
                "http_status": response.status,
                "result": parsed,
            }
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"remote-agent writeback failed with HTTP {exc.code}: {detail}"
        ) from exc
    except error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, socket.timeout):
            raise TimeoutError(f"remote-agent writeback timed out via {base_url}") from exc
        raise RuntimeError(
            f"remote-agent writeback connection failed via {base_url}: {reason}"
        ) from exc
