"""Optional Google Safe Browsing lookup (only if SAFE_BROWSING_KEY is set)."""
import json
import urllib.error
import urllib.request
from typing import Dict

from app import config


def available() -> bool:
    return bool(config.SAFE_BROWSING_KEY)


def check(url: str) -> Dict:
    out = {"tool": "safe_browsing", "ok": False, "malicious": False, "detail": ""}
    if not available():
        out["detail"] = "not configured (no SAFE_BROWSING_KEY)"
        return out
    body = {
        "client": {"clientId": "threatdefender-ai", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
            "platformTypes": ["ANY_PLATFORM"], "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    try:
        req = urllib.request.Request(
            "https://safebrowsing.googleapis.com/v4/threatMatches:find?key=" + config.SAFE_BROWSING_KEY,
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=config.ONLINE_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        out["ok"] = True
        out["malicious"] = bool(data.get("matches"))
        out["detail"] = "flagged by Safe Browsing" if out["malicious"] else "not listed by Safe Browsing"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        out["detail"] = f"unavailable ({type(exc).__name__})"
    return out
