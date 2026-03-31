"""Minimal in-memory approval store for relay approval tracking."""

from __future__ import annotations

from typing import Mapping

_APPROVALS_BY_REQUEST_ID: dict[str, dict[str, object]] = {}

_STATUS_BY_DECISION = {
    "approve": "approved",
    "reject": "rejected",
}

_TERMINAL_STATUSES = ("approved", "rejected")


def list_approvals() -> list[dict[str, object]]:
    return [dict(approval) for approval in _APPROVALS_BY_REQUEST_ID.values()]


def get_approval(request_id: str) -> dict[str, object] | None:
    approval = _APPROVALS_BY_REQUEST_ID.get(request_id)
    if approval is None:
        return None
    return dict(approval)


def get_status_for_decision(decision: str) -> str:
    return _STATUS_BY_DECISION[decision]


def is_terminal_status(status: str) -> bool:
    return status in _TERMINAL_STATUSES


def apply_decision(request_id: str, decision: str) -> dict[str, object] | None:
    approval = _APPROVALS_BY_REQUEST_ID.get(request_id)
    if approval is None:
        return None

    approval["status"] = get_status_for_decision(decision)
    return dict(approval)


def upsert_pending_approval_request(
    event: Mapping[str, object],
) -> dict[str, object]:
    approval, _ = _upsert_pending_approval(
        request_id=str(event["request_id"]),
        session_id=str(event["session_id"]),
        kind=str(event["kind"]),
        summary=str(event["summary"]),
        source_seq=int(event.get("seq", 0)),
        updated_at=str(event.get("at", "")),
    )
    return approval


def upsert_pending_approval_from_remote_event(
    event: Mapping[str, object],
) -> tuple[dict[str, object], bool]:
    payload = event.get("payload")
    if not isinstance(payload, dict):
        raise KeyError("remote approval event payload must be an object")

    return _upsert_pending_approval(
        request_id=str(payload["request_id"]),
        session_id=str(event["session_id"]),
        kind=str(payload["kind"]),
        summary=str(payload["summary"]),
        source_seq=int(event["seq"]),
        updated_at=str(event["at"]),
    )


def _upsert_pending_approval(
    *,
    request_id: str,
    session_id: str,
    kind: str,
    summary: str,
    source_seq: int,
    updated_at: str,
) -> tuple[dict[str, object], bool]:
    approval = _APPROVALS_BY_REQUEST_ID.get(request_id)
    if approval is None:
        approval = {
            "request_id": request_id,
            "session_id": session_id,
            "status": "pending",
            "kind": kind,
            "summary": summary,
            "source_seq": source_seq,
            "updated_at": updated_at,
        }
        _APPROVALS_BY_REQUEST_ID[request_id] = approval
        return dict(approval), True

    if approval["status"] != "pending":
        return dict(approval), False

    current_source_seq = int(approval.get("source_seq", 0))
    if source_seq <= current_source_seq:
        return dict(approval), False

    approval["session_id"] = session_id
    approval["kind"] = kind
    approval["summary"] = summary
    approval["status"] = "pending"
    approval["source_seq"] = source_seq
    approval["updated_at"] = updated_at
    return dict(approval), True
