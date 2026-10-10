"""Risk Engine. THE SECURITY ENGINE DECIDES; THE AI ONLY EXPLAINS.

final = 100 * (1 - PRODUCT(1 - weight_i * score_i/100))   over all evidence components
Several independent signals reinforce each other, one weak signal alone stays low.
"""
from typing import Dict, List

from app import config

# How much each evidence source is trusted (0-1)
WEIGHTS = {
    "url": 0.90, "text": 0.90, "content": 0.90, "file": 0.95, "sender": 0.60,
    "behavior": 0.80, "honeycomb": 0.55, "memory": 0.70, "intel": 1.00, "online": 0.90,
}


def verdict_for(score: int) -> str:
    t = config.THRESHOLDS
    if score >= t["CRITICAL"]:
        return "CRITICAL"
    if score >= t["DANGEROUS"]:
        return "DANGEROUS"
    if score >= t["SUSPICIOUS"]:
        return "SUSPICIOUS"
    return "SAFE"


def action_for(verdict: str) -> str:
    return {"SAFE": "ALLOW", "SUSPICIOUS": "WARN", "DANGEROUS": "BLOCK", "CRITICAL": "BLOCK"}[verdict]


def compute_risk(component_scores: Dict[str, int]) -> Dict:
    comps: List[Dict] = []
    p = 1.0
    for name, score in component_scores.items():
        if score is None or score <= 0:
            continue
        w = WEIGHTS.get(name, 0.5)
        p *= 1.0 - w * min(100, score) / 100.0
        comps.append({"name": name, "score": int(score), "weight": w})
    final = int(round(100 * (1.0 - p)))
    final = max(0, min(100, final))
    verdict = verdict_for(final)
    comps.sort(key=lambda c: -c["score"])
    return {"score": final, "verdict": verdict, "action": action_for(verdict), "components": comps}
