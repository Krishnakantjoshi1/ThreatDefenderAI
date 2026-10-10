from typing import Dict

from app.modes.controller import resolve_mode
from app.tools import url_reputation, threat_intelligence


def status() -> Dict:
    m = resolve_mode()
    return {
        "network": m["network"],
        "mode": m["effective"],
        "tools": {
            "domain_lookup": m["network"] == "connected" and m["effective"] != "offline",
            "safe_browsing": url_reputation.available() and m["network"] == "connected" and m["effective"] == "online",
            "feed_update": m["network"] == "connected",
        },
        "feed": threat_intelligence.feed_info(),
    }
