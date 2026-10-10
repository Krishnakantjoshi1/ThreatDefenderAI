"""Attack Chain: the attacker's likely sequence, derived from Honeycomb evidence (deterministic)."""
from typing import Dict, List

_STAGES = [
    ("offer", "Bait", "A tempting offer or reward grabs your attention"),
    ("conversation", "Trust", "A social-engineering conversation builds trust or demands secrecy"),
    ("identity", "Impersonation", "The sender pretends to be a bank, brand or authority you trust"),
    ("urgency", "Pressure", "Fear and urgency push you to act before you think"),
    ("link", "Delivery", "You are sent to a dangerous link, page or file"),
    ("credential", "Credential theft", "A fake login or OTP request steals your secrets"),
    ("money", "Cash-out", "Your money is moved out or you are tricked into paying"),
]


def build_attack_chain(honeycomb_scores: Dict[str, int], indicators: List[Dict], risk_score: int,
                       threshold: int = 40) -> List[Dict]:
    chain: List[Dict] = []
    for dim, title, default_detail in _STAGES:
        strength = honeycomb_scores.get(dim, 0)
        if strength < threshold:
            continue
        ev = [i for i in indicators if i["dimension"] == dim and i["weight"] > 0.06]
        ev.sort(key=lambda i: -i["weight"])
        detail = ev[0]["label"] if ev else default_detail
        chain.append({"stage": title, "dimension": dim, "strength": strength,
                      "explanation": default_detail, "evidence": detail})
    if chain and risk_score >= 60:
        chain.append({"stage": "Impact", "dimension": "impact", "strength": risk_score,
                      "explanation": "If you follow every step: stolen account, drained money, identity misuse",
                      "evidence": "Predicted outcome"})
    return chain
