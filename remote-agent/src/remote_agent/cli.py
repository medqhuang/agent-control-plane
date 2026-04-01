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
from remote_agent.service_client import get_json
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

    sessions_parser = subparsers.add_parser(
        "sessions",
        help="list hosted sessions from the local remote-agent service",
    )
    _add_service_base_url_argument(sessions_parser)
    sessions_parser.set_defaults(handler=_handle_sessions)

    watch_parser = subparsers.add_parser(
        "watch",
        help="show the latest hosted session state",
    )
    watch_parser.add_argument("session_id")
    _add_service_base_url_argument(watch_parser)
    watch_parser.set_defaults(handler=_handle_watch)

    reply_parser = subparsers.add_parser(
        "reply",
        help="send a follow-up message to a hosted session",
    )
    reply_parser.add_argument("session_id")
    reply_parser.add_argument(
        "--message",
        required=True,
        help="message to send to the hosted session",
    )
    _add_service_base_url_argument(reply_parser)
    reply_parser.set_defaults(handler=_handle_reply)

    stop_parser = subparsers.add_parser(
        "stop",
        help="stop a hosted session",
    )
    stop_parser.add_argument("session_id")
    _add_service_base_url_argument(stop_parser)
    stop_parser.set_defaults(handler=_handle_stop)

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
    _add_service_base_url_argument(kimi_start_parser)
    kimi_start_parser.set_defaults(handler=_handle_kimi_start)
    return parser


def _add_service_base_url_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--service-base-url",
        default=default_service_base_url(),
        help="base URL for the local remote-agent service",
    )


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


def _handle_sessions(args: argparse.Namespace) -> int:
    return _print_service_result(
        lambda: get_json(
            path="/v1/sessions",
            base_url=args.service_base_url,
        ),
        service_base_url=args.service_base_url,
    )


def _handle_watch(args: argparse.Namespace) -> int:
    return _print_service_result(
        lambda: get_json(
            path=f"/v1/sessions/{args.session_id}",
            base_url=args.service_base_url,
        ),
        service_base_url=args.service_base_url,
    )


def _handle_reply(args: argparse.Namespace) -> int:
    return _print_service_result(
        lambda: post_json(
            path=f"/v1/sessions/{args.session_id}/reply",
            payload={
                "message": args.message,
            },
            base_url=args.service_base_url,
            timeout_seconds=max(
                float(_get_env_int("REMOTE_AGENT_KIMI_TIMEOUT_SECONDS", 90)) + 5.0,
                10.0,
            ),
        ),
        service_base_url=args.service_base_url,
    )


def _handle_stop(args: argparse.Namespace) -> int:
    return _print_service_result(
        lambda: post_json(
            path=f"/v1/sessions/{args.session_id}/stop",
            payload={},
            base_url=args.service_base_url,
        ),
        service_base_url=args.service_base_url,
    )


def _handle_kimi_start(args: argparse.Namespace) -> int:
    # In service mode, the remote-agent daemon has its own cwd. When the user
    # omits --workdir, preserve the CLI invocation cwd explicitly so hosted
    # sessions match the documented "cd <dir> && remote-agent kimi start ..."
    # flow.
    workdir = args.workdir if args.workdir is not None else os.getcwd()
    return _print_service_result(
        lambda: post_json(
            path="/v1/kimi/start",
            payload={
                "task": args.task,
                "workdir": workdir,
                "timeout_seconds": args.timeout_seconds,
                "kimi_bin": args.kimi_bin,
            },
            base_url=args.service_base_url,
            timeout_seconds=max(float(args.timeout_seconds) + 5.0, 10.0),
        ),
        task=args.task,
        workdir=workdir,
        timeout_seconds=args.timeout_seconds,
        service_base_url=args.service_base_url,
    )


def _print_service_result(
    request_fn,
    *,
    task: str | None = None,
    workdir: str | None = None,
    timeout_seconds: int | None = None,
    service_base_url: str | None = None,
) -> int:
    try:
        payload = request_fn()
    except RemoteAgentServiceError as exc:
        print_json(
            {
                "type": "remote_agent_service_error",
                "accepted": False,
                "task": task,
                "session": {
                    "state": "failed",
                    "workdir": workdir or os.getcwd(),
                },
                "worker": {
                    "status": "service_unavailable",
                    "transport": "kimi --wire",
                    "timeout_seconds": timeout_seconds,
                    "error": str(exc),
                },
                "service": {
                    "base_url": service_base_url or default_service_base_url(),
                    "entrypoint": "remote_agent.service_client:_request_json",
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
