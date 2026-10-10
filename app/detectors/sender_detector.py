"""Sender (email address / phone number) heuristics."""
import re
from typing import Dict, List

from app.detectors.url_detector import analyze_url, noisy_or
from app.intelligence import threat_database as db

_FREE_MAIL = {"gmail.com", "yahoo.com", "yahoo.in", "outlook.com", "hotmail.com", "rediffmail.com", "proton.me", "protonmail.com", "mail.com"}
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def _ind(code, label, weight, dimension="identity", evidence=""):
    return {"code": code, "label": label, "weight": weight, "dimension": dimension,
            "evidence": evidence, "source": "sender"}


def analyze_sender(sender: str) -> Dict:
    sender = (sender or "").strip()
    ind: List[Dict] = []
    if not sender:
        return {"score": 0, "indicators": []}

    m = _EMAIL.search(sender)
    if m:
        domain = m.group(1).lower()
        local = sender[: m.start()].lower()
        if domain in _FREE_MAIL:
            for brand in db.brands():
                if brand in local or brand in sender.lower().split("<")[0]:
                    ind.append(_ind("free_mail_brand", f"Claims to be '{brand}' but uses a free email service ({domain})", 0.5, evidence=sender[:60]))
                    break
        else:
            url_result = analyze_url("https://" + domain)
            for i in url_result["indicators"]:
                if i["code"] in ("brand_impersonation", "lookalike", "known_bad", "punycode", "bad_tld"):
                    ind.append(_ind("sender_" + i["code"], "Sender domain: " + i["label"], i["weight"], "identity", domain))
    else:
        digits = re.sub(r"\D", "", sender)
        if sender.startswith("+") and not sender.startswith("+91") and len(digits) >= 8:
            ind.append(_ind("foreign_number", "Message from an international number", 0.15, "identity", sender[:20]))
        if digits and len(digits) == 10 and digits[0] in "6789" and not sender.startswith("+"):
            pass  # normal Indian mobile number, no signal

    return {"score": int(round(100 * noisy_or([i["weight"] for i in ind]))), "indicators": ind}
