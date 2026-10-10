"""Behavioural combinations: signals that are weak alone but strong together."""
from typing import Dict, List

from app.detectors.url_detector import noisy_or

ACTIVE = 40  # a Honeycomb dimension at/above this value counts as "active"

_COMBOS = [
    ({"urgency", "credential"}, 0.55, "Pressure + request for secrets (classic phishing pattern)"),
    ({"offer", "credential"}, 0.5, "Reward bait + request for credentials"),
    ({"offer", "link"}, 0.4, "Reward bait + link"),
    ({"offer", "money"}, 0.5, "Prize + payment request (advance-fee fraud)"),
    ({"identity", "urgency"}, 0.35, "Impersonation + urgency"),
    ({"money", "urgency"}, 0.4, "Payment demand + urgency"),
    ({"credential", "link"}, 0.45, "Credential request + link"),
    ({"conversation", "money"}, 0.45, "Social-engineering conversation + money request"),
    ({"identity", "credential"}, 0.4, "Impersonation + credential request"),
]


def analyze_behavior(dimension_scores: Dict[str, int]) -> Dict:
    active = {d for d, v in dimension_scores.items() if v >= ACTIVE}
    behaviors: List[Dict] = []
    for need, weight, label in _COMBOS:
        if need <= active:
            behaviors.append({"code": "combo_" + "_".join(sorted(need)), "label": label,
                              "weight": weight, "dimension": sorted(need)[0], "evidence": " + ".join(sorted(need)),
                              "source": "behavior"})
    if len(active) >= 4:
        behaviors.append({"code": "multi_vector", "label": f"{len(active)} of 7 attack dimensions active at once",
                          "weight": 0.5, "dimension": "conversation", "evidence": ", ".join(sorted(active)),
                          "source": "behavior"})
    return {"score": int(round(100 * noisy_or([b["weight"] for b in behaviors]))), "behaviors": behaviors,
            "active_dimensions": sorted(active)}
