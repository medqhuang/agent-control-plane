"""Minimal relay ASGI entrypoint."""

from __future__ import annotations

from threading import Lock
from typing import Literal

from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel
from pydantic import Field

from relay.approval_store import ApprovalLookupAmbiguousError
from relay.approval_store import apply_decision
from relay.approval_store import get_approval
from relay.approval_store import get_status_for_decision
from relay.approval_store import is_terminal_status
from relay.approval_store import list_approvals
from relay.approval_store import upsert_pending_approval_from_remote_event
from relay.approval_store import upsert_pending_approval_request
from relay.event_log import append_approval_response_event
from relay.event_log import get_next_event_seq
from relay.remote_agent_client import post_approval_response as post_remote_agent_approval
from relay.server_registry import enrich_approval
from relay.server_registry import enrich_session
from relay.server_registry import list_servers
from relay.server_registry import observe_approval_request
from relay.server_registry import observe_remote_event
from relay.session_store import get_session
from relay.session_store import list_sessions
from relay.session_store import sync_session_status_from_approval
from relay.session_store import upsert_session_from_approval_request
from relay.session_store import upsert_session_from_remote_event


app = FastAPI(
    title="Agent Control Plane Relay",
    version="0.1.0",
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)

_APPROVAL_RESPONSE_LOCK = Lock()


class ApprovalResponseRequest(BaseModel):
    request_id: str
    remote_id: str = ""
    decision: Literal["approve", "reject"]
    feedback: str = ""


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


class RemoteAgentStandardEvent(BaseModel):
    type: Literal[
        "session_started",
        "session_continued",
        "approval_request_observed",
        "session_finished",
    ]
    provider: str
    session_id: str
    seq: int
    at: str
    remote: str
    title: str
    payload: dict[str, object] = Field(default_factory=dict)
    control: dict[str, object] = Field(default_factory=dict)


@app.get("/v1/snapshot")
def get_snapshot() -> dict[str, object]:
    return {
        "servers": list_servers(),
        "sessions": [enrich_session(session) for session in list_sessions()],
        "approvals": [enrich_approval(approval) for approval in list_approvals()],
    }


@app.get("/v1/servers")
def get_servers() -> dict[str, list[dict[str, object]]]:
    return {"servers": list_servers()}


@app.post("/v1/remote-agent/events")
def post_remote_agent_event(
    payload: RemoteAgentStandardEvent,
) -> dict[str, object]:
    normalized_event = payload.model_dump()
    observe_remote_event(normalized_event)
    session, session_applied = upsert_session_from_remote_event(normalized_event)
    approval = None
    approval_applied = False
    if normalized_event["type"] == "approval_request_observed":
        approval, approval_applied = upsert_pending_approval_from_remote_event(
            normalized_event
        )

    return {
        "session": enrich_session(session),
        "approval": enrich_approval(approval) if approval is not None else None,
        "event": normalized_event,
        "applied": session_applied or approval_applied,
        "session_applied": session_applied,
        "approval_applied": approval_applied,
    }


@app.post("/v1/kimi/approval-request")
def post_kimi_approval_request(
    payload: KimiApprovalRequestEvent,
) -> dict[str, object]:
    normalized_event = payload.model_dump()
    observe_approval_request(normalized_event)
    session = upsert_session_from_approval_request(normalized_event)
    approval = upsert_pending_approval_request(normalized_event)
    return {
        "session": enrich_session(session),
        "approval": enrich_approval(approval),
        "event": normalized_event,
    }


@app.post("/v1/approval-response")
def post_approval_response(
    payload: ApprovalResponseRequest,
) -> dict[str, object]:
    with _APPROVAL_RESPONSE_LOCK:
        target_remote_id = payload.remote_id.strip() or None
        try:
            approval = get_approval(payload.request_id, remote_id=target_remote_id)
        except ApprovalLookupAmbiguousError as exc:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "approval request_id is ambiguous across multiple remotes; provide remote_id",
                    "request_id": exc.request_id,
                    "remote_ids": exc.remote_ids,
                },
            ) from exc
        if approval is None:
            raise HTTPException(status_code=404, detail="approval request not found")

        target_status = get_status_for_decision(payload.decision)
        if is_terminal_status(approval["status"]):
            if approval["status"] == target_status:
                return {
                    "approval": enrich_approval(approval),
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
                    "remote_id": approval.get("remote_id", ""),
                    "current_status": approval["status"],
                    "attempted_decision": payload.decision,
                },
            )

        remote_id = str(approval.get("remote_id") or approval.get("remote") or "")
        session = get_session(approval["session_id"], remote_id=remote_id or None)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")

        event_seq = get_next_event_seq()
        try:
            provider_writeback = post_remote_agent_approval(
                session=session,
                request_id=approval["request_id"],
                decision=payload.decision,
                feedback=payload.feedback,
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

        approval = apply_decision(
            payload.request_id,
            payload.decision,
            remote_id=remote_id or None,
        )
        session = sync_session_status_from_approval(
            session_id=approval["session_id"],
            approval_status=approval["status"],
            remote_id=remote_id or None,
        )
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")

        event = append_approval_response_event(
            request_id=approval["request_id"],
            session_id=approval["session_id"],
            decision=payload.decision,
            approval_status=approval["status"],
            remote_id=remote_id,
            seq=event_seq,
        )
        return {
            "approval": enrich_approval(approval),
            "event": event,
            "idempotent": False,
            "provider_writeback": provider_writeback,
        }
