"""Download a public phishing feed ONCE while online; it is then used offline for lookups."""
import urllib.error
import urllib.request
from typing import Dict

from app import config

FEED_URL = "https://openphish.com/feed.txt"


def update_feed() -> Dict:
    try:
        req = urllib.request.Request(FEED_URL, headers={"User-Agent": "ThreatDefenderAI/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read(5_000_000).decode("utf-8", "ignore")
        lines = [l.strip() for l in raw.splitlines() if l.strip().startswith(("http://", "https://"))]
        if not lines:
            return {"ok": False, "detail": "Feed returned no usable entries"}
        config.feed_path().write_text("\n".join(lines), encoding="utf-8")
        return {"ok": True, "entries": len(lines), "detail": f"Saved {len(lines)} known phishing URLs for offline use"}
    except (urllib.error.URLError, OSError) as exc:
        return {"ok": False, "detail": f"Could not download feed ({type(exc).__name__}). Needs internet."}


def feed_info() -> Dict:
    p = config.feed_path()
    if not p.exists():
        return {"present": False, "entries": 0}
    return {"present": True, "entries": sum(1 for _ in p.open(encoding="utf-8", errors="ignore"))}
