"""Threat Memory: remembers fingerprints, categories and risk - never the raw message."""
import hashlib
from typing import Dict, List

from app.database import repository as repo


def domain_fingerprint(reg_domain: str) -> str:
    return hashlib.sha256(("domain:" + reg_domain.lower()).encode()).hexdigest()[:24]


def lookup(fp: str, reg_domains: List[str]) -> Dict:
    """What do we already know about this message / these domains?"""
    msg = repo.memory_get(fp)
    doms = []
    for d in reg_domains:
        row = repo.memory_get(domain_fingerprint(d))
        if row:
            doms.append({"domain": d, "seen": row["count"], "risk": row["risk"]})
    prior_risk = max([msg["risk"]] if msg else [0])
    for d in doms:
        prior_risk = max(prior_risk, d["risk"])
    return {"seen_before": bool(msg), "times_seen": msg["count"] if msg else 0,
            "prior_category": msg["category"] if msg else None, "prior_risk": prior_risk,
            "known_domains": doms}


def remember(fp: str, category: str, risk: int, indicator_codes: List[str], reg_domains: List[str]) -> None:
    """Only store things that were actually suspicious (risk >= 30)."""
    if risk < 30:
        return
    repo.memory_upsert(fp, category, risk, indicator_codes[:15])
    for d in reg_domains:
        repo.memory_upsert(domain_fingerprint(d), "domain", risk, [])
