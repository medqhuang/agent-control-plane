"""CLI entrypoint for the minimal remote-agent foundation."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

import uvicorn

from remote_agent.app import create_app
from remote_agent.output import print_json
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
        help="start a placeholder Kimi task",
    )
    kimi_start_parser.add_argument(
        "--task",
        required=True,
        help="task text for the future Kimi worker",
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
        create_app(),
        host=args.host,
        port=args.port,
        log_level=args.log_level,
    )
    return 0


def _handle_kimi_start(args: argparse.Namespace) -> int:
    runtime = SupervisorRuntime()
    print_json(runtime.start_kimi_task(task=args.task))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 1
    return int(handler(args))
