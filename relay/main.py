"""Minimal ASGI entrypoint for the relay service.

P0 only fixes the runtime stack and import path. P1 will add routes,
stores, and provider-facing integration points.
"""

from typing import Literal

from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel

from relay.approval_store import apply_decision
from relay.approval_store import list_approvals
from relay.event_log import append_approval_response_event
from relay.session_store import list_sessions


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


@app.get("/v1/snapshot")
def get_snapshot() -> dict[str, list[dict[str, str]]]:
    return {
        "sessions": list_sessions(),
        "approvals": list_approvals(),
    }


@app.post("/v1/approval-response")
def post_approval_response(
    payload: ApprovalResponseRequest,
) -> dict[str, dict[str, str | int]]:
    approval = apply_decision(payload.request_id, payload.decision)
    if approval is None:
        raise HTTPException(status_code=404, detail="approval request not found")

    event = append_approval_response_event(
        request_id=approval["request_id"],
        session_id=approval["session_id"],
        decision=payload.decision,
        approval_status=approval["status"],
    )
    return {
        "approval": approval,
        "event": event,
    }
