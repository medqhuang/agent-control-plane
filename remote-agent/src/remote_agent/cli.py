"""CLI entrypoint for the minimal remote-agent foundation."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

import uvicorn

from remote_agent.app import create_app
from remote_agent.output import print_json
from remote_agent.service_client import RemoteAgentServiceError
from remote_agent.service_client import default_service_base_url
from remote_agent.service_client import post_json
from remote_agent.supervisor import SupervisorRuntime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="remote-agent",
        description="Minimal remote-agent foundation CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser(
        "serve",
        help="start the remote-agent HTTP service",
    )
    serve_parser.add_argument(
        "--host",
        default=os.environ.get("REMOTE_AGENT_HOST", "127.0.0.1"),
    )
    serve_parser.add_argument(
        "--port",
        default=_get_env_int("REMOTE_AGENT_PORT", 8711),
        type=int,
    )
    serve_parser.add_argument(
        "--log-level",
        default=os.environ.get("REMOTE_AGENT_LOG_LEVEL", "info"),
        choices=["critical", "error", "warning", "info", "debug", "trace"],
    )
    serve_parser.set_defaults(handler=_handle_serve)

    kimi_parser = subparsers.add_parser(
        "kimi",
        help="Kimi provider commands",
    )
    kimi_subparsers = kimi_parser.add_subparsers(
        dest="kimi_command",
        required=True,
    )

    kimi_start_parser = kimi_subparsers.add_parser(
        "start",
        help="start a hosted Kimi task via the local remote-agent service",
    )
    kimi_start_parser.add_argument(
        "--task",
        required=True,
        help="task text for the hosted Kimi worker",
    )
    kimi_start_parser.add_argument(
        "--workdir",
        default=None,
        help="working directory for kimi --wire; defaults to the current directory",
    )
    kimi_start_parser.add_argument(
        "--timeout-seconds",
        default=_get_env_int("REMOTE_AGENT_KIMI_TIMEOUT_SECONDS", 90),
        type=int,
        help="maximum time to wait for a finish or approval checkpoint",
    )
    kimi_start_parser.add_argument(
        "--kimi-bin",
        default=os.environ.get("KIMI_BIN"),
        help="override the kimi executable path",
    )
    kimi_start_parser.add_argument(
        "--service-base-url",
        default=default_service_base_url(),
        help="base URL for the local remote-agent service",
    )
    kimi_start_parser.set_defaults(handler=_handle_kimi_start)
    return parser


def _get_env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _handle_serve(args: argparse.Namespace) -> int:
    runtime = SupervisorRuntime()
    print_json(
        {
            "type": "remote_agent_service_starting",
            "service": "remote-agent",
            "server": {
                "host": args.host,
                "port": args.port,
                "log_level": args.log_level,
            },
            "runtime": runtime.build_service_snapshot(
                host=args.host,
                port=args.port,
            ),
        }
    )
    uvicorn.run(
        create_app(runtime),
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )
    return 0


def _handle_kimi_start(args: argparse.Namespace) -> int:
    try:
        payload = post_json(
            path="/v1/kimi/start",
            payload={
                "task": args.task,
                "workdir": args.workdir,
                "timeout_seconds": args.timeout_seconds,
                "kimi_bin": args.kimi_bin,
            },
            base_url=args.service_base_url,
            timeout_seconds=max(float(args.timeout_seconds) + 5.0, 10.0),
        )
    except RemoteAgentServiceError as exc:
        print_json(
            {
                "type": "kimi_start_result",
                "accepted": False,
                "provider": "kimi",
                "task": args.task,
                "session": {
                    "provider": "kimi",
                    "state": "failed",
                    "created_at": None,
                    "workdir": args.workdir or os.getcwd(),
                },
                "worker": {
                    "status": "service_unavailable",
                    "mode": "hosted_wire",
                    "transport": "kimi --wire",
                    "timeout_seconds": args.timeout_seconds,
                    "error": str(exc),
                },
                "service": {
                    "base_url": args.service_base_url,
                    "entrypoint": "remote_agent.service_client:post_json",
                },
            }
        )
        return 1

    print_json(payload)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 1
    return int(handler(args))
