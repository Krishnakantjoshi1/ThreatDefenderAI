from typing import Dict, List


def story_text(chain: List[Dict]) -> str:
    steps = [c["stage"] for c in chain if c["dimension"] != "impact"]
    if not steps:
        return "No attack sequence detected."
    return " -> ".join(steps) + (" -> Account takeover / financial loss" if any(c["dimension"] == "impact" for c in chain) else "")
