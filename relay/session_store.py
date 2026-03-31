"""Minimal in-memory session store for P1 relay development."""

from typing import Mapping

# README.md defines the shared session status model for the relay core.
SESSION_STATUSES = (
    "running",
    "waiting_approval",
    "completed",
    "failed",
    "disconnected",
)


_SESSIONS_BY_ID: dict[str, dict[str, str]] = {
    "session_demo_1": {
        "id": "session_demo_1",
        "provider": "kimi",
        "remote": "demo-remote",
        "status": "waiting_approval",
        "title": "demo approval session",
    }
}

_SESSION_STATUS_BY_APPROVAL_STATUS = {
    "pending": "waiting_approval",
    "approved": "running",
    "rejected": "failed",
}


def list_sessions() -> list[dict[str, str]]:
    return [dict(session) for session in _SESSIONS_BY_ID.values()]


def get_session(session_id: str) -> dict[str, str] | None:
    session = _SESSIONS_BY_ID.get(session_id)
    if session is None:
        return None
    return dict(session)


def sync_session_status_from_approval(
    session_id: str,
    approval_status: str,
) -> dict[str, str] | None:
    session = _SESSIONS_BY_ID.get(session_id)
    if session is None:
        return None

    session["status"] = _SESSION_STATUS_BY_APPROVAL_STATUS[approval_status]
    return dict(session)


def upsert_session_from_approval_request(
    event: Mapping[str, object],
) -> dict[str, str]:
    session_id = str(event["session_id"])
    session = _SESSIONS_BY_ID.get(session_id)
    if session is None:
        session = {
            "id": session_id,
            "provider": str(event["provider"]),
            "remote": str(event["remote"]),
            "title": str(event["title"]),
            "status": "waiting_approval",
        }
        _SESSIONS_BY_ID[session_id] = session
    else:
        session["provider"] = str(event["provider"])
        session["remote"] = str(event["remote"])
        session["title"] = str(event["title"])

    session["status"] = _SESSION_STATUS_BY_APPROVAL_STATUS[str(event["status"])]
    return dict(session)
