"""Local demo command for pushing one Kimi approval request into relay."""

import argparse
import json
import time

from adapters.kimi import build_demo_kimi_approval_event
from adapters.kimi import push_kimi_event_to_relay


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("relay_base_url")
    parser.add_argument("--suffix", default=None)
    parser.add_argument("--seq", type=int, default=1)
    args = parser.parse_args()

    suffix = args.suffix or str(int(time.time() * 1000))
    raw_event = build_demo_kimi_approval_event(suffix, seq=args.seq)
    response = push_kimi_event_to_relay(args.relay_base_url, raw_event)
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
