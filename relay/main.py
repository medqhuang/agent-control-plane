"""Minimal ASGI entrypoint for the relay service.

P0 only fixes the runtime stack and import path. P1 will add routes,
stores, and provider-facing integration points.
"""

from typing import Literal

from adapters.kimi import write_approval_response_to_kimi
from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel

from relay.approval_store import apply_decision
from relay.approval_store import get_approval
from relay.approval_store import get_status_for_decision
from relay.approval_store import is_terminal_status
from relay.approval_store import list_approvals
from relay.approval_store import upsert_pending_approval_request
from relay.event_log import append_approval_response_event
from relay.event_log import get_next_event_seq
from relay.session_store import get_session
from relay.session_store import list_sessions
from relay.session_store import sync_session_status_from_approval
from relay.session_store import upsert_session_from_approval_request


app = FastAPI(
    title="Agent Control Plane Relay",
    version="0.1.0",
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)


class ApprovalResponseRequest(BaseModel):
    request_id: str
    decision: Literal["approve", "reject"]


class KimiApprovalRequestEvent(BaseModel):
    type: Literal["approval_request"]
    provider: Literal["kimi"]
    session_id: str
    request_id: str
    seq: int
    remote: str
    title: str
    kind: str
    status: Literal["pending"]
    summary: str


@app.get("/v1/snapshot")
def get_snapshot() -> dict[str, list[dict[str, str]]]:
    return {
        "sessions": list_sessions(),
        "approvals": list_approvals(),
    }


@app.post("/v1/kimi/approval-request")
def post_kimi_approval_request(
    payload: KimiApprovalRequestEvent,
) -> dict[str, object]:
    normalized_event = payload.model_dump()
    session = upsert_session_from_approval_request(normalized_event)
    approval = upsert_pending_approval_request(normalized_event)
    return {
        "session": session,
        "approval": approval,
        "event": normalized_event,
    }


@app.post("/v1/approval-response")
def post_approval_response(
    payload: ApprovalResponseRequest,
) -> dict[str, object]:
    approval = get_approval(payload.request_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval request not found")

    target_status = get_status_for_decision(payload.decision)
    if is_terminal_status(approval["status"]):
        if approval["status"] == target_status:
            return {
                "approval": approval,
                "event": None,
                "idempotent": True,
                "message": "decision already applied",
                "provider_writeback": None,
            }

        raise HTTPException(
            status_code=409,
            detail={
                "message": "approval request already finalized with a different decision",
                "request_id": approval["request_id"],
                "current_status": approval["status"],
                "attempted_decision": payload.decision,
            },
        )

    session = get_session(approval["session_id"])
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    if session["provider"] != "kimi":
        raise HTTPException(status_code=501, detail="provider writeback not implemented")

    event_seq = get_next_event_seq()
    try:
        provider_writeback = write_approval_response_to_kimi(
            session_id=approval["session_id"],
            request_id=approval["request_id"],
            decision=payload.decision,
            source_seq=event_seq,
            remote=session["remote"],
        )
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "message": "provider writeback timed out",
                "provider": session["provider"],
                "remote": session["remote"],
                "session_id": approval["session_id"],
                "request_id": approval["request_id"],
                "decision": payload.decision,
                "source_seq": event_seq,
                "reason": str(exc),
            },
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "provider writeback failed",
                "provider": session["provider"],
                "remote": session["remote"],
                "session_id": approval["session_id"],
                "request_id": approval["request_id"],
                "decision": payload.decision,
                "source_seq": event_seq,
                "reason": str(exc),
            },
        ) from exc

    approval = apply_decision(payload.request_id, payload.decision)
    session = sync_session_status_from_approval(
        session_id=approval["session_id"],
        approval_status=approval["status"],
    )
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    event = append_approval_response_event(
        request_id=approval["request_id"],
        session_id=approval["session_id"],
        decision=payload.decision,
        approval_status=approval["status"],
        seq=event_seq,
    )
    return {
        "approval": approval,
        "event": event,
        "idempotent": False,
        "provider_writeback": provider_writeback,
    }
