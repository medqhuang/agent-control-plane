"""Minimal in-memory approval store for relay approval tracking."""

from __future__ import annotations

from typing import Mapping

_APPROVALS_BY_ID: dict[str, dict[str, object]] = {}

_STATUS_BY_DECISION = {
    "approve": "approved",
    "reject": "rejected",
}

_TERMINAL_STATUSES = ("approved", "rejected")


class ApprovalLookupAmbiguousError(LookupError):
    """Raised when request_id-only lookup matches multiple remote approvals."""

    def __init__(self, request_id: str, remote_ids: list[str]) -> None:
        super().__init__(
            f"approval request_id {request_id} is ambiguous across multiple remotes"
        )
        self.request_id = request_id
        self.remote_ids = remote_ids


def list_approvals() -> list[dict[str, object]]:
    return [dict(approval) for approval in _APPROVALS_BY_ID.values()]


def get_approval(
    request_id: str,
    *,
    remote_id: str | None = None,
) -> dict[str, object] | None:
    approval = _resolve_approval(request_id, remote_id=remote_id)
    if approval is None:
        return None
    return dict(approval)


def get_status_for_decision(decision: str) -> str:
    return _STATUS_BY_DECISION[decision]


def is_terminal_status(status: str) -> bool:
    return status in _TERMINAL_STATUSES


def apply_decision(
    request_id: str,
    decision: str,
    *,
    remote_id: str | None = None,
) -> dict[str, object] | None:
    approval = _resolve_approval(request_id, remote_id=remote_id)
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
        remote_id=_remote_id_from_event(event),
        provider=str(event.get("provider", "")),
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
        remote_id=_remote_id_from_event(event),
        provider=str(event.get("provider", "")),
        kind=str(payload["kind"]),
        summary=str(payload["summary"]),
        source_seq=int(event["seq"]),
        updated_at=str(event["at"]),
    )


def _upsert_pending_approval(
    *,
    request_id: str,
    session_id: str,
    remote_id: str,
    provider: str,
    kind: str,
    summary: str,
    source_seq: int,
    updated_at: str,
) -> tuple[dict[str, object], bool]:
    approval_id = _approval_id(remote_id, request_id)
    approval = _APPROVALS_BY_ID.get(approval_id)
    if approval is None:
        approval = {
            "request_id": request_id,
            "session_id": session_id,
            "remote_id": remote_id,
            "remote": remote_id,
            "provider": provider,
            "status": "pending",
            "kind": kind,
            "summary": summary,
            "source_seq": source_seq,
            "updated_at": updated_at,
        }
        _APPROVALS_BY_ID[approval_id] = approval
        return dict(approval), True

    if approval["status"] != "pending":
        return dict(approval), False

    current_source_seq = int(approval.get("source_seq", 0))
    if source_seq <= current_source_seq:
        return dict(approval), False

    approval["session_id"] = session_id
    approval["remote_id"] = remote_id
    approval["remote"] = remote_id
    approval["provider"] = provider
    approval["kind"] = kind
    approval["summary"] = summary
    approval["status"] = "pending"
    approval["source_seq"] = source_seq
    approval["updated_at"] = updated_at
    return dict(approval), True


def _remote_id_from_event(event: Mapping[str, object]) -> str:
    remote_id = str(event.get("remote_id", "")).strip()
    if remote_id:
        return remote_id
    return str(event.get("remote", "")).strip()


def _approval_id(remote_id: str, request_id: str) -> str:
    return f"{remote_id}::{request_id}"


def _resolve_approval(
    request_id: str,
    *,
    remote_id: str | None = None,
) -> dict[str, object] | None:
    normalized_request_id = str(request_id).strip()
    normalized_remote_id = str(remote_id or "").strip()

    if normalized_remote_id:
        return _APPROVALS_BY_ID.get(_approval_id(normalized_remote_id, normalized_request_id))

    matches = [
        approval
        for approval in _APPROVALS_BY_ID.values()
        if str(approval.get("request_id", "")).strip() == normalized_request_id
    ]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    remote_ids = sorted(
        {
            str(approval.get("remote_id") or approval.get("remote") or "").strip()
            for approval in matches
        }
    )
    raise ApprovalLookupAmbiguousError(normalized_request_id, remote_ids)
