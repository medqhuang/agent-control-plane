"""Minimal in-memory session store for relay session tracking."""

from __future__ import annotations

from typing import Mapping

# README.md defines the shared session status model for the relay core.
SESSION_STATUSES = (
    "running",
    "waiting_approval",
    "completed",
    "failed",
    "disconnected",
)


_SESSIONS_BY_ID: dict[str, dict[str, object]] = {}

_SESSION_STATUS_BY_APPROVAL_STATUS = {
    "pending": "waiting_approval",
    "approved": "running",
    "rejected": "failed",
}

_SESSION_STATUS_BY_REMOTE_EVENT_TYPE = {
    "session_started": "running",
    "session_continued": "running",
    "approval_request_observed": "waiting_approval",
}

_COMPLETED_REMOTE_STATUSES = {"finished", "completed"}


def list_sessions() -> list[dict[str, object]]:
    return [dict(session) for session in _SESSIONS_BY_ID.values()]


def get_session(session_id: str) -> dict[str, object] | None:
    session = _SESSIONS_BY_ID.get(session_id)
    if session is None:
        return None
    return dict(session)


def sync_session_status_from_approval(
    session_id: str,
    approval_status: str,
) -> dict[str, object] | None:
    session = _SESSIONS_BY_ID.get(session_id)
    if session is None:
        return None

    session["status"] = _SESSION_STATUS_BY_APPROVAL_STATUS[approval_status]
    return dict(session)


def upsert_session_from_approval_request(
    event: Mapping[str, object],
) -> dict[str, object]:
    session_id = str(event["session_id"])
    session = _SESSIONS_BY_ID.get(session_id)
    if session is None:
        session = {
            "id": session_id,
            "provider": str(event["provider"]),
            "remote": str(event["remote"]),
            "title": str(event["title"]),
            "status": "waiting_approval",
            "last_event_seq": int(event.get("seq", 0)),
            "last_event_type": str(event.get("type", "approval_request")),
            "updated_at": str(event.get("at", "")),
        }
        _SESSIONS_BY_ID[session_id] = session
    else:
        session["provider"] = str(event["provider"])
        session["remote"] = str(event["remote"])
        session["title"] = str(event["title"])

    session["status"] = _SESSION_STATUS_BY_APPROVAL_STATUS[str(event["status"])]
    if "seq" in event:
        session["last_event_seq"] = int(event["seq"])
    if "type" in event:
        session["last_event_type"] = str(event["type"])
    if "at" in event:
        session["updated_at"] = str(event["at"])
    return dict(session)


def upsert_session_from_remote_event(
    event: Mapping[str, object],
) -> tuple[dict[str, object], bool]:
    session_id = str(event["session_id"])
    event_seq = int(event["seq"])
    session = _SESSIONS_BY_ID.get(session_id)
    if session is None:
        session = {
            "id": session_id,
            "provider": str(event["provider"]),
            "remote": str(event["remote"]),
            "title": str(event["title"]),
            "status": _status_from_remote_event(event),
            "last_event_seq": event_seq,
            "last_event_type": str(event["type"]),
            "updated_at": str(event["at"]),
        }
        _SESSIONS_BY_ID[session_id] = session
        return dict(session), True

    previous_seq = int(session.get("last_event_seq", 0))
    if event_seq <= previous_seq:
        return dict(session), False

    session["provider"] = str(event["provider"])
    session["remote"] = str(event["remote"])
    session["title"] = str(event["title"])
    session["status"] = _status_from_remote_event(event)
    session["last_event_seq"] = event_seq
    session["last_event_type"] = str(event["type"])
    session["updated_at"] = str(event["at"])
    return dict(session), True


def _status_from_remote_event(event: Mapping[str, object]) -> str:
    event_type = str(event["type"])
    if event_type == "session_finished":
        payload = event.get("payload")
        status = ""
        if isinstance(payload, dict):
            status = str(payload.get("status", "")).strip().lower()
        if status in _COMPLETED_REMOTE_STATUSES:
            return "completed"
        return "failed"
    return _SESSION_STATUS_BY_REMOTE_EVENT_TYPE.get(event_type, "running")
