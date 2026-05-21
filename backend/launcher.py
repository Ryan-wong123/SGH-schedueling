from __future__ import annotations

import argparse
import socket
import threading
import webbrowser

import uvicorn

from app.main import create_app


def _find_available_port(start: int = 8000, attempts: int = 50) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("Could not find an available local port.")


def _open_browser(url: str) -> None:
    webbrowser.open(url, new=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run GLF Assessment Scheduler.")
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser automatically.")
    args = parser.parse_args()

    port = _find_available_port()
    url = f"http://127.0.0.1:{port}"
    print("Starting GLF Assessment Scheduler")
    print(f"Open {url} if the browser does not open automatically.")
    print("Close this window when you are finished.")

    if not args.no_open:
        threading.Timer(1.5, _open_browser, args=(url,)).start()
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
