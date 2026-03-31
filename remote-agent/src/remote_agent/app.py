"""ASGI application for the minimal remote-agent service."""

from fastapi import FastAPI

from remote_agent import __version__
from remote_agent.supervisor import SupervisorRuntime


def create_app() -> FastAPI:
    runtime = SupervisorRuntime()
    app = FastAPI(
        title="Agent Control Plane Remote Agent",
        version=__version__,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "remote-agent",
        }

    @app.get("/v1/runtime")
    def get_runtime() -> dict[str, object]:
        return runtime.describe()

    return app
