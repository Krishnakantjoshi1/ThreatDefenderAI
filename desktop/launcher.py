"""Desktop launcher: starts the local engine, waits until it is healthy, opens the dashboard."""
import json
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402

from app import config  # noqa: E402

HOST = "127.0.0.1"
URL = f"http://{HOST}:{config.PORT}"


def wait_until_ready(timeout: float = 25.0) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(URL + "/api/health", timeout=1) as r:
                health = json.load(r)
                if (r.status == 200 and isinstance(health, dict) and
                        health.get("status") == "ok" and health.get("app") == config.APP_NAME):
                    return True
        except (OSError, ValueError):
            time.sleep(0.4)
    return False


def reports_available() -> bool:
    try:
        with urllib.request.urlopen(URL + "/openapi.json", timeout=2) as response:
            routes = json.load(response).get("paths", {})
            return ("/api/reports/history.pdf" in routes and
                    "/api/reports/scans/{scan_id}.pdf" in routes)
    except (OSError, ValueError):
        return False


def main() -> None:
    if wait_until_ready(timeout=1.0):
        if not reports_available():
            print(
                "\n  An older ThreatDefender server is already running and does not support PDF reports.\n"
                "  Close the window or terminal running it, then start ThreatDefender again.\n"
            )
            return
        print(f"\n  ThreatDefender AI is already running -> {URL}\n")
        webbrowser.open(URL)
        return

    server = uvicorn.Server(uvicorn.Config("app.main:app", host=HOST, port=config.PORT, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    if wait_until_ready():
        print(f"\n  ThreatDefender AI is running -> {URL}\n  Press Ctrl+C to stop.\n")
        webbrowser.open(URL)
    else:
        server.should_exit = True
        thread.join(timeout=3)
        print(f"The local server did not become healthy at {URL}. Check whether port {config.PORT} is available.")
        return
    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        server.should_exit = True


if __name__ == "__main__":
    main()
