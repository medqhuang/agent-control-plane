"""Remote Kimi smoke trigger for a real approval prompt."""

import argparse
import json
import time

from adapters.kimi import start_remote_kimi_approval_smoke


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Trigger a remote Kimi approval prompt and push it into relay.",
    )
    parser.add_argument("relay_base_url")
    parser.add_argument(
        "--remote-host",
        default="zhaojin.ustc.edu.cn",
    )
    parser.add_argument(
        "--session-suffix",
        default=str(int(time.time())),
    )
    parser.add_argument(
        "--command",
        default="pwd",
    )
    parser.add_argument(
        "--workdir",
        default="~/kimi-web/p2-smoke",
    )
    args = parser.parse_args()

    result = start_remote_kimi_approval_smoke(
        relay_base_url=args.relay_base_url,
        remote_host=args.remote_host,
        session_id=f"kimi_remote_{args.session_suffix}",
        command=args.command,
        workdir=args.workdir,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
