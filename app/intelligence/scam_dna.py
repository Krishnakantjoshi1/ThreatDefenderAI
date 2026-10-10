"""Scam DNA: does this message *behave* like scams we know? (cosine similarity on the Honeycomb vector)"""
import math
from typing import Dict, List

from app.honeycomb.dimensions import DIMENSIONS
from app.intelligence import threat_database as db


def _cos(a: List[float], b: List[float]) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def scam_dna(scores: Dict[str, int], min_similarity: float = 0.80) -> Dict:
    vec = [scores.get(d, 0) / 100.0 for d in DIMENSIONS]
    strength = max(vec) if vec else 0
    matches = []
    for arch in db.scam_archetypes():
        ref = [arch["vector"].get(d, 0.0) for d in DIMENSIONS]
        matches.append({"name": arch["name"], "similarity": int(round(100 * _cos(vec, ref)))})
    matches.sort(key=lambda m: -m["similarity"])
    best = matches[0] if matches else None
    matched = bool(best and best["similarity"] >= int(min_similarity * 100) and strength >= 0.5)
    return {"fingerprint": {d: scores.get(d, 0) for d in DIMENSIONS},
            "match": best["name"] if matched else None,
            "similarity": best["similarity"] if matched else (best["similarity"] if best else 0),
            "top_matches": matches[:3], "is_known_pattern": matched}
