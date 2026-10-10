"""Local threat database: shipped JSON seed data + optional downloaded feed (works offline)."""
import json
from functools import lru_cache
from typing import Dict, Set

from app import config
from app.utils.logger import get_logger

log = get_logger("threat_db")


def _read_json(name: str) -> Dict:
    path = config.threats_dir() / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        log.error("Could not load %s: %s", path, exc)
        return {}


@lru_cache(maxsize=1)
def patterns() -> Dict:
    return _read_json("phishing_patterns.json")


@lru_cache(maxsize=1)
def local_threats() -> Dict:
    return _read_json("local_threats.json")


@lru_cache(maxsize=1)
def scam_archetypes() -> list:
    return _read_json("scam_patterns.json").get("archetypes", [])


def brands() -> Dict[str, list]:
    return patterns().get("brands", {})


def trusted_domains() -> Set[str]:
    out = set(patterns().get("trusted_domains", []))
    for domains in brands().values():
        out.update(domains)
    return out


def feed_domains() -> Set[str]:
    """Domains from a downloaded feed (see tools/threat_intelligence.py). Re-read when file changes."""
    path = config.feed_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return set()
    return _load_feed(str(path), mtime)


@lru_cache(maxsize=4)
def _load_feed(path: str, mtime: float) -> Set[str]:  # mtime is part of the cache key
    from app.utils.url_utils import parse_url
    out: Set[str] = set()
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    host = parse_url(line)["host"]
                    if host:
                        out.add(host)
    except OSError:
        pass
    return out


def is_known_bad_domain(host: str, reg_domain: str) -> str:
    """Return the source name if host is a known-bad domain, else ''."""
    bad = {d.lower() for d in local_threats().get("bad_domains", [])}
    if host in bad or reg_domain in bad:
        return "local threat list"
    if host in local_threats().get("bad_ips", []):
        return "local threat list"
    feed = feed_domains()
    if host in feed or reg_domain in feed:
        return "downloaded threat feed"
    return ""


def is_known_bad_hash(sha256: str) -> bool:
    return sha256 in set(local_threats().get("bad_hashes", []))
