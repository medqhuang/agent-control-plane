from __future__ import annotations

import contextlib
import http.server
import socketserver
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_PACKAGES = ROOT / ".venv" / "Lib" / "site-packages"
if SITE_PACKAGES.exists():
    sys.path.insert(0, str(SITE_PACKAGES))

from playwright.sync_api import sync_playwright  # type: ignore


EDGE_PATHS = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]

OUTPUT_DIR = ROOT / "docs" / "images"
SHOWCASE_PATH = "/docs/showcase/index.html"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def find_edge_executable() -> str:
    for candidate in EDGE_PATHS:
        if candidate.exists():
            return str(candidate)
    raise RuntimeError("Microsoft Edge executable not found.")


def start_server() -> tuple[socketserver.TCPServer, str]:
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    server = ReusableTCPServer(("127.0.0.1", 0), QuietHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{port}"


def wait_for_showcase(page) -> None:
    page.wait_for_function("() => window.__showcaseReady === true")
    page.wait_for_timeout(250)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    edge_path = find_edge_executable()
    server, base_url = start_server()
    cwd_before = Path.cwd()
    try:
        os_chdir = getattr(Path, "cwd")
        del os_chdir  # silence lint-like checks for unused helper thought
        import os

        os.chdir(ROOT)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=edge_path,
                args=["--hide-scrollbars"],
            )
            context = browser.new_context(
                viewport={"width": 1560, "height": 1400},
                device_scale_factor=1.5,
                color_scheme="light",
            )
            page = context.new_page()

            captures = [
                (
                    "overview",
                    OUTPUT_DIR / "ui-overview.png",
                    "#capture-root",
                ),
                (
                    "reply",
                    OUTPUT_DIR / "ui-session-detail.png",
                    "#detail-panel",
                ),
                (
                    "approval",
                    OUTPUT_DIR / "ui-approval-flow.png",
                    "#interaction-column",
                ),
            ]

            for state_name, output_path, selector in captures:
                page.goto(f"{base_url}{SHOWCASE_PATH}?state={state_name}", wait_until="networkidle")
                wait_for_showcase(page)
                locator = page.locator(selector)
                locator.screenshot(path=str(output_path))

            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        import os

        os.chdir(cwd_before)

    generated = [
        str(OUTPUT_DIR / "ui-overview.png"),
        str(OUTPUT_DIR / "ui-session-detail.png"),
        str(OUTPUT_DIR / "ui-approval-flow.png"),
    ]
    print("\n".join(generated))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
