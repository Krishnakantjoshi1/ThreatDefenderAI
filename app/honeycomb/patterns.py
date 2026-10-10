"""Plain-language names for dominant Honeycomb shapes (used as a scam category label)."""
from typing import Dict

CATEGORY_RULES = [
    ({"credential", "identity"}, "Credential phishing / bank impersonation"),
    ({"offer", "money"}, "Lottery / advance-fee scam"),
    ({"offer", "link"}, "Reward bait phishing"),
    ({"credential", "urgency"}, "Urgent credential phishing"),
    ({"conversation", "money"}, "Social-engineering payment scam"),
    ({"identity", "urgency"}, "Authority / account-alert impersonation"),
    ({"link"}, "Malicious link / file"),
    ({"credential"}, "Credential harvesting"),
    ({"money"}, "Payment fraud"),
    ({"offer"}, "Reward / offer bait"),
    ({"identity"}, "Impersonation"),
    ({"urgency"}, "Pressure tactics"),
    ({"conversation"}, "Social engineering"),
]


def category_from(scores: Dict[str, int], threshold: int = 40) -> str:
    active = {d for d, v in scores.items() if v >= threshold}
    if not active:
        return "None detected"
    for need, name in CATEGORY_RULES:
        if need <= active:
            return name
    return "Suspicious content"
