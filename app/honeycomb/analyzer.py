"""Honeycomb Threat Analysis: collapse all evidence into 7 explainable 0-100 dimensions."""
from typing import Dict, List

from app.detectors.url_detector import noisy_or
from app.honeycomb.dimensions import DIMENSIONS, META
from app.honeycomb.patterns import category_from


def build_honeycomb(indicators: List[Dict], url_results: List[Dict]) -> Dict:
    scores: Dict[str, int] = {}
    for dim in DIMENSIONS:
        ws = [i["weight"] for i in indicators if i["dimension"] == dim]
        if dim == "link" and url_results:
            worst = max(u["score"] for u in url_results)
            ws.append(worst / 100.0 * 0.95)  # the link dimension reflects the riskiest URL
        scores[dim] = int(round(100 * noisy_or(ws)))
    top = sorted(scores.items(), key=lambda kv: -kv[1])
    return {
        "scores": scores,
        "labels": {d: META[d]["label"] for d in DIMENSIONS},
        "category": category_from(scores),
        "dominant": [d for d, v in top if v >= 40][:3],
        "hot_count": sum(1 for v in scores.values() if v >= 60),
    }
