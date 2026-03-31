"""Minimal in-memory event log for P1 relay development."""

_EVENTS: list[dict[str, str | int]] = []
_NEXT_SEQ = 1


def append_approval_response_event(
    request_id: str,
    session_id: str,
    decision: str,
    approval_status: str,
) -> dict[str, str | int]:
    global _NEXT_SEQ

    event = {
        "seq": _NEXT_SEQ,
        "type": "approval_response",
        "request_id": request_id,
        "session_id": session_id,
        "decision": decision,
        "approval_status": approval_status,
    }
    _EVENTS.append(event)
    _NEXT_SEQ += 1
    return dict(event)


def list_events() -> list[dict[str, str | int]]:
    return [dict(event) for event in _EVENTS]
