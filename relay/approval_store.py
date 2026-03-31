"""Minimal in-memory approval store for P1 relay development."""

_APPROVALS_BY_REQUEST_ID: dict[str, dict[str, str]] = {
    "approval_demo_1": {
        "request_id": "approval_demo_1",
        "session_id": "session_demo_1",
        "status": "pending",
        "kind": "command",
        "summary": "Approve the pending command for the demo session.",
    }
}

_STATUS_BY_DECISION = {
    "approve": "approved",
    "reject": "rejected",
}


def list_approvals() -> list[dict[str, str]]:
    return [dict(approval) for approval in _APPROVALS_BY_REQUEST_ID.values()]


def get_approval(request_id: str) -> dict[str, str] | None:
    approval = _APPROVALS_BY_REQUEST_ID.get(request_id)
    if approval is None:
        return None
    return dict(approval)


def apply_decision(request_id: str, decision: str) -> dict[str, str] | None:
    approval = _APPROVALS_BY_REQUEST_ID.get(request_id)
    if approval is None:
        return None

    approval["status"] = _STATUS_BY_DECISION[decision]
    return dict(approval)
