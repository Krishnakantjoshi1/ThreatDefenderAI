"""Online domain facts: DNS resolution + registration age via RDAP (no API key needed)."""
import json
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Dict

from app import config


def lookup(reg_domain: str, host: str) -> Dict:
    out: Dict = {"tool": "domain_lookup", "domain": reg_domain, "ok": False, "age_days": None, "resolves": None, "detail": ""}
    try:
        socket.setdefaulttimeout(config.ONLINE_TIMEOUT)
        socket.getaddrinfo(host, None)
        out["resolves"] = True
    except OSError:
        out["resolves"] = False
    try:
        req = urllib.request.Request(f"https://rdap.org/domain/{reg_domain}",
                                     headers={"Accept": "application/rdap+json", "User-Agent": "ThreatDefenderAI/1.0"})
        with urllib.request.urlopen(req, timeout=config.ONLINE_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8", "ignore"))
        for ev in data.get("events", []):
            if ev.get("eventAction") == "registration":
                dt = datetime.fromisoformat(ev["eventDate"].replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                out["age_days"] = max(0, (datetime.now(timezone.utc) - dt).days)
                break
        out["ok"] = True
        out["detail"] = f"registered {out['age_days']} days ago" if out["age_days"] is not None else "no registration date published"
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        out["detail"] = f"RDAP unavailable ({type(exc).__name__})"
    return out
