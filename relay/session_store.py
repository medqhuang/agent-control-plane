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
    return [public_session(session) for session in _SESSIONS_BY_ID.values()]


def get_session(
    session_id: str,
    *,
    remote_id: str | None = None,
) -> dict[str, object] | None:
    if remote_id is not None:
        session = _SESSIONS_BY_ID.get(_session_key(remote_id, session_id))
        if session is None:
            return None
        return dict(session)

    matches = [
        session
        for session in _SESSIONS_BY_ID.values()
        if str(session.get("id", "")) == session_id
    ]
    if not matches:
        return None
    if len(matches) == 1:
        return dict(matches[0])
    raise LookupError(f"session {session_id} is ambiguous across multiple remotes")


def sync_session_status_from_approval(
    session_id: str,
    approval_status: str,
    *,
    remote_id: str | None = None,
) -> dict[str, object] | None:
    session = get_session(session_id, remote_id=remote_id)
    if session is None:
        return None

    session["status"] = _SESSION_STATUS_BY_APPROVAL_STATUS[approval_status]
    _SESSIONS_BY_ID[_session_key(str(session["remote_id"]), session_id)] = session
    return dict(session)


def upsert_session_from_approval_request(
    event: Mapping[str, object],
) -> dict[str, object]:
    session_id = str(event["session_id"])
    remote_id = _remote_id_from_event(event)
    key = _session_key(remote_id, session_id)
    session = _SESSIONS_BY_ID.get(key)
    if session is None:
        session = {
            "id": session_id,
            "remote_id": remote_id,
            "provider": str(event["provider"]),
            "remote": remote_id,
            "title": str(event["title"]),
            "status": "waiting_approval",
            "last_event_seq": int(event.get("seq", 0)),
            "last_event_type": str(event.get("type", "approval_request")),
            "updated_at": str(event.get("at", "")),
            "control": {},
        }
        _SESSIONS_BY_ID[key] = session
    else:
        session["remote_id"] = remote_id
        session["provider"] = str(event["provider"])
        session["remote"] = remote_id
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
    remote_id = _remote_id_from_event(event)
    key = _session_key(remote_id, session_id)
    event_seq = int(event["seq"])
    session = _SESSIONS_BY_ID.get(key)
    control = _normalize_control(event.get("control"))
    if session is None:
        session = {
            "id": session_id,
            "remote_id": remote_id,
            "provider": str(event["provider"]),
            "remote": remote_id,
            "title": str(event["title"]),
            "status": _status_from_remote_event(event),
            "last_event_seq": event_seq,
            "last_event_type": str(event["type"]),
            "updated_at": str(event["at"]),
            "control": control,
        }
        _SESSIONS_BY_ID[key] = session
        return dict(session), True

    previous_seq = int(session.get("last_event_seq", 0))
    if event_seq <= previous_seq:
        return dict(session), False

    session["remote_id"] = remote_id
    session["provider"] = str(event["provider"])
    session["remote"] = remote_id
    session["title"] = str(event["title"])
    session["status"] = _status_from_remote_event(event)
    session["last_event_seq"] = event_seq
    session["last_event_type"] = str(event["type"])
    session["updated_at"] = str(event["at"])
    if control:
        session["control"] = control
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


def _normalize_control(raw_control: object) -> dict[str, object]:
    if not isinstance(raw_control, Mapping):
        return {}
    return {
        key: value
        for key, value in raw_control.items()
        if isinstance(key, str)
    }


def public_session(session: Mapping[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in session.items()
        if key != "control"
    }


def _session_key(remote_id: str, session_id: str) -> str:
    return f"{remote_id}::{session_id}"


def _remote_id_from_event(event: Mapping[str, object]) -> str:
    remote_id = str(event.get("remote_id", "")).strip()
    if remote_id:
        return remote_id
    return str(event.get("remote", "")).strip()
