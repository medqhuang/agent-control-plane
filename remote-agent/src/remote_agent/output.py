"""Shared output helpers for CLI JSON responses."""

from __future__ import annotations

import json
import sys
from typing import Any


def print_json(payload: dict[str, Any]) -> None:
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    sys.stdout.flush()
