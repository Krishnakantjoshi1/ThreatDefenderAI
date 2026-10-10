"""URL extraction and parsing without external dependencies."""
import ipaddress
import re
from typing import Dict, List
from urllib.parse import urlsplit

_TLDS = (
    "com|in|net|org|info|biz|xyz|top|click|link|online|site|shop|store|live|icu|buzz|"
    "club|vip|work|support|tk|ml|ga|cf|gq|cc|co|me|io|app|dev|page|cfd|sbs|rest|"
    "monster|zip|mov|ru|cn|pw|ws|ly|gy|gd|gl|ee|sh|to|tv"
)
URL_RE = re.compile(
    r"(?i)\b(?:https?://[^\s<>\"'`]+|www\.[^\s<>\"'`]+|"
    r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+(?:" + _TLDS + r")(?:/[^\s<>\"'`]*)?(?![a-z0-9.-]))"
)
_TRAIL = ".,;:!?)]}>'\""

# Common two-part public suffixes (enough for India-focused demo; not a full PSL)
_SECOND_LEVEL = {
    "co.in", "org.in", "gov.in", "ac.in", "net.in", "nic.in", "edu.in", "res.in", "firm.in",
    "co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "net.au", "org.au", "com.br",
    "co.jp", "co.nz", "co.za", "com.sg", "com.cn", "com.pk", "com.bd",
}


def extract_urls(text: str) -> List[str]:
    seen, out = set(), []
    for m in URL_RE.finditer(text or ""):
        url = m.group(0).rstrip(_TRAIL)
        # skip things like "e.g" or file names accidentally matched without path
        if url.lower() not in seen and len(url) >= 4:
            seen.add(url.lower())
            out.append(url)
    return out


def is_single_url(text: str) -> bool:
    t = (text or "").strip()
    if not t or any(c.isspace() for c in t):
        return False
    m = URL_RE.fullmatch(t.rstrip(_TRAIL))
    return bool(m)


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def registered_domain(host: str) -> str:
    host = host.lower().strip(".")
    if _is_ip(host):
        return host
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if ".".join(parts[-2:]) in _SECOND_LEVEL and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def parse_url(url: str) -> Dict:
    """Return a dict of URL parts. Never raises; unparsable input gives empty host."""
    raw = (url or "").strip()
    had_scheme = bool(re.match(r"(?i)^[a-z][a-z0-9+.-]*://", raw))
    candidate = raw if had_scheme else "http://" + raw
    try:
        parts = urlsplit(candidate)
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        return {"raw": raw, "scheme": "", "host": "", "had_scheme": had_scheme, "valid": False,
                "path": "", "query": "", "registered_domain": "", "subdomain": "", "tld": "",
                "is_ip": False, "has_userinfo": False, "port": None}
    reg = registered_domain(host) if host else ""
    sub = host[: -len(reg)].rstrip(".") if reg and host.endswith(reg) else ""
    return {
        "raw": raw,
        "scheme": parts.scheme.lower() if had_scheme else "",
        "host": host,
        "port": port,
        "path": parts.path or "",
        "query": parts.query or "",
        "had_scheme": had_scheme,
        "valid": bool(host),
        "registered_domain": reg,
        "subdomain": sub,
        "tld": host.rsplit(".", 1)[-1] if "." in host else "",
        "is_ip": _is_ip(host),
        "has_userinfo": "@" in (parts.netloc or ""),
    }
