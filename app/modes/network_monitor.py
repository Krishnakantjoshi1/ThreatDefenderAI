"""Detects whether the internet is reachable.

Probes run in parallel and the result is cached, with an optional background refresher,
so a scan never waits on slow network timeouts.
"""
import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.database import repository as repo

_PROBES = [("1.1.1.1", 53), ("8.8.8.8", 53), ("9.9.9.9", 53)]
_TTL = 5.0
_lock = threading.Lock()
_state = {"ts": 0.0, "ok": False}
_started = False


def _one(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _probe(timeout: float = 1.0) -> bool:
    with ThreadPoolExecutor(max_workers=len(_PROBES)) as pool:
        futures = [pool.submit(_one, h, p, timeout) for h, p in _PROBES]
        for f in as_completed(futures):
            if f.result():
                return True
    return False


def _refresh() -> bool:
    ok = _probe()
    with _lock:
        _state.update(ts=time.monotonic(), ok=ok)
    return ok


def is_forced_offline() -> bool:
    return os.getenv("TD_FORCE_OFFLINE", "").lower() in ("1", "true", "yes") or repo.get_bool("force_offline")


def internet_available(use_cache: bool = True) -> bool:
    """True only if the internet is really reachable AND demo 'simulate offline' is off."""
    if is_forced_offline():
        return False
    with _lock:
        fresh = (time.monotonic() - _state["ts"]) < _TTL
        cached = _state["ok"]
    if use_cache and fresh:
        return cached
    return _refresh()


def start_background_monitor(interval: float = 3.0) -> None:
    """Keep the cache warm so API calls return instantly and Wi-Fi changes are noticed quickly."""
    global _started
    if _started:
        return
    _started = True

    def loop():
        while True:
            try:
                _refresh()
            except Exception:  # never let the monitor thread die
                pass
            time.sleep(interval)

    threading.Thread(target=loop, name="network-monitor", daemon=True).start()


def reset_cache() -> None:
    with _lock:
        _state.update(ts=0.0, ok=False)
