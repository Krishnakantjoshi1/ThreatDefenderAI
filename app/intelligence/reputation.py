"""Offline reputation facts about a domain: local lists + what Threat Memory has seen."""
from typing import Dict

from app.intelligence import threat_database as db


def local_reputation(host: str, reg_domain: str) -> Dict:
    src = db.is_known_bad_domain(host, reg_domain)
    return {"host": host, "known_bad": bool(src), "source": src or None,
            "trusted": reg_domain in db.trusted_domains()}
