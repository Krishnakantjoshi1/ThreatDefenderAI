"""Explanations: instant rule-based text always available; Phi-3 (Ollama) upgrades it when running."""
import re
import time
from typing import Dict, Optional

from app.ai import ollama_client
from app.ai.attack_story import story_text
from app.ai.prompt_builder import SYSTEM, build_prompt

_GOALS = {
    "credential": "steal your OTP, PIN, password or login details",
    "money": "trick you into sending money",
    "offer": "lure you with a fake reward so you lower your guard",
    "identity": "pose as a trusted bank, brand or authority",
    "link": "get you to open a dangerous link or file",
    "urgency": "rush you so you act before thinking",
    "conversation": "manipulate you through a convincing conversation",
}

_ACTIONS = {
    "SAFE": "No action needed. Stay alert and use official apps/websites for anything involving money.",
    "SUSPICIOUS": "Do not click links or share any details yet. Verify through the official app, website or a number you already trust.",
    "DANGEROUS": "Do not click, reply or share anything. Block the sender. If you already shared details, call your bank immediately.",
    "CRITICAL": "Do NOT click, reply or share any OTP/PIN. Block and report it: call 1930 or visit cybercrime.gov.in. If you already responded, contact your bank right now.",
}
_ACTIONS_HI = {
    "SAFE": "Koi action zaroori nahi. Phir bhi paise ke maamle mein official app ya website hi use karein.",
    "SUSPICIOUS": "Abhi link par click na karein aur koi detail share na karein. Official app ya trusted number se verify karein.",
    "DANGEROUS": "Click ya reply na karein, kuch share na karein. Sender ko block karein. Agar details de di hain to turant bank ko call karein.",
    "CRITICAL": "Click ya reply bilkul na karein, OTP/PIN kabhi share na karein. 1930 par call karein ya cybercrime.gov.in par report karein.",
}


def quick_explanation(result: Dict, lang: str = "en") -> Dict:
    """Deterministic explanation (no AI). Instant."""
    reasons = [r["label"] for r in result.get("reasons", [])[:3]]
    verdict = result.get("verdict", "SAFE")
    dominant = result.get("honeycomb", {}).get("dominant", [])
    category = result.get("honeycomb", {}).get("category", "")
    if verdict == "SAFE":
        why = "No meaningful scam or phishing signals were found."
    elif lang == "hinglish":
        why = f"Ye {category.lower()} jaisa lagta hai kyunki: " + "; ".join(reasons) + "."
    else:
        why = f"This looks like {category.lower()} because: " + "; ".join(reasons) + "."
    goal = ("The attacker wants to " + " and ".join(_GOALS[d] for d in dominant[:2]) + ".") if dominant and verdict != "SAFE" else ""
    actions = _ACTIONS_HI if lang == "hinglish" else _ACTIONS
    return {"why": why, "goal": goal, "story": story_text(result.get("attack_chain", [])),
            "action": actions[verdict], "source": "rule-based", "model": None, "latency_ms": 0}


_SECTION = re.compile(r"(?is)\b(WHY|GOAL|STORY|ACTION)\s*:\s*(.*?)(?=\b(?:WHY|GOAL|STORY|ACTION)\s*:|\Z)")


def parse_sections(text: str) -> Dict[str, str]:
    found = {k.lower(): re.sub(r"\s+", " ", v).strip() for k, v in _SECTION.findall(text)}
    return found


def explain(result: Dict, content: Optional[str] = None, lang: str = "en", use_ai: bool = True) -> Dict:
    base = quick_explanation(result, lang)
    if not use_ai:
        return base
    t0 = time.perf_counter()
    text = ollama_client.generate(build_prompt(result, content, lang), system=SYSTEM)
    ms = int((time.perf_counter() - t0) * 1000)
    if not text:
        base["note"] = "Local AI (Phi-3) not available - showing the built-in explanation."
        return base
    parsed = parse_sections(text)
    if not parsed.get("why"):
        parsed = {"why": re.sub(r"\s+", " ", text).strip()[:600]}
    return {
        "why": parsed.get("why") or base["why"],
        "goal": parsed.get("goal") or base["goal"],
        "story": parsed.get("story") or base["story"],
        "action": parsed.get("action") or base["action"],
        "source": "phi3", "model": ollama_client.config.OLLAMA_MODEL, "latency_ms": ms,
    }
