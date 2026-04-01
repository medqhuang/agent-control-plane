"""Minimal in-memory event log for P1 relay development."""

_EVENTS: list[dict[str, str | int]] = []
_NEXT_SEQ = 1


def get_next_event_seq() -> int:
    return _NEXT_SEQ


def append_approval_response_event(
    request_id: str,
    session_id: str,
    decision: str,
    approval_status: str,
    *,
    remote_id: str = "",
    seq: int | None = None,
) -> dict[str, str | int]:
    global _NEXT_SEQ

    event_seq = _NEXT_SEQ if seq is None else seq
    if event_seq != _NEXT_SEQ:
        raise ValueError("event seq out of sync")

    event = {
        "seq": event_seq,
        "type": "approval_response",
        "request_id": request_id,
        "session_id": session_id,
        "remote_id": remote_id,
        "decision": decision,
        "approval_status": approval_status,
    }
    _EVENTS.append(event)
    _NEXT_SEQ = event_seq + 1
    return dict(event)


def list_events() -> list[dict[str, str | int]]:
    return [dict(event) for event in _EVENTS]
