"""ASGI application for the remote-agent service."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from fastapi import HTTPException
from pydantic import BaseModel

from remote_agent import __version__
from remote_agent.supervisor import ApprovalNotPendingError
from remote_agent.supervisor import KimiWritebackError
from remote_agent.supervisor import SupervisorRuntime


class KimiStartRequest(BaseModel):
    task: str
    workdir: str | None = None
    timeout_seconds: int = 90
    kimi_bin: str | None = None


class ApprovalResponseRequest(BaseModel):
    request_id: str
    decision: Literal["approve", "reject"]
    feedback: str = ""


def create_app(runtime: SupervisorRuntime | None = None) -> FastAPI:
    runtime = runtime or SupervisorRuntime()
    app = FastAPI(
        title="Agent Control Plane Remote Agent",
        version=__version__,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "remote-agent",
        }

    @app.get("/v1/runtime")
    async def get_runtime() -> dict[str, object]:
        return runtime.describe()

    @app.post("/v1/kimi/start")
    async def post_kimi_start(payload: KimiStartRequest) -> dict[str, object]:
        return await runtime.start_kimi_task(
            task=payload.task,
            workdir=payload.workdir,
            timeout_seconds=payload.timeout_seconds,
            kimi_bin=payload.kimi_bin,
        )

    @app.post("/v1/approval-response")
    async def post_approval_response(
        payload: ApprovalResponseRequest,
    ) -> dict[str, object]:
        try:
            writeback = await runtime.apply_approval_response(
                request_id=payload.request_id,
                decision=payload.decision,
                feedback=payload.feedback,
            )
        except ApprovalNotPendingError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except KimiWritebackError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return {
            "request_id": payload.request_id,
            "decision": payload.decision,
            "provider_writeback": writeback,
        }

    return app
