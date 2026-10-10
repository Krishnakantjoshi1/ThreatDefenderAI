"""Deterministic URL analysis. Pure Python, works fully offline.

Each indicator carries a weight in (0,1]; the URL score is a noisy-OR of the weights
so that several weak signals can add up while a single weak signal stays low.
"""
import re
from typing import Dict, List

from app.intelligence import threat_database as db
from app.utils.url_utils import parse_url

_LEET = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def noisy_or(weights: List[float]) -> float:
    p = 1.0
    for w in weights:
        p *= 1.0 - max(0.0, min(1.0, w))
    return 1.0 - p


def _edit_distance_le1(a: str, b: str) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    for i in range(len(long_)):
        if long_[:i] + long_[i + 1:] == short:
            return True
    return False


def _ind(code: str, label: str, weight: float, dimension: str = "link", evidence: str = "") -> Dict:
    return {"code": code, "label": label, "weight": weight, "dimension": dimension,
            "evidence": evidence, "source": "url"}


def analyze_url(url: str) -> Dict:
    p = parse_url(url)
    result = {"url": url, "host": p["host"], "registered_domain": p["registered_domain"],
              "score": 0, "indicators": [], "trusted": False, "known_bad": ""}
    if not p["valid"]:
        result["indicators"].append(_ind("unparsable", "URL could not be parsed", 0.2, evidence=url[:60]))
        result["score"] = 20
        return result

    host, reg = p["host"], p["registered_domain"]
    full_lower = (host + p["path"] + "?" + p["query"]).lower()
    ind: List[Dict] = []

    # --- known-bad lookup (offline threat database) ---
    bad_src = db.is_known_bad_domain(host, reg)
    if bad_src:
        result["known_bad"] = bad_src
        ind.append(_ind("known_bad", f"Listed in {bad_src}", 0.97, "link", host))

    # --- trusted domain: exact registered-domain match with a known legit brand/site ---
    trusted = reg in db.trusted_domains() or any(reg.endswith("." + t) or reg == t for t in db.patterns().get("trusted_domains", []))
    result["trusted"] = bool(trusted and not bad_src and not p["has_userinfo"])

    if p["is_ip"]:
        ind.append(_ind("ip_host", "Uses a raw IP address instead of a domain name", 0.55, evidence=host))
    if p["has_userinfo"]:
        ind.append(_ind("at_symbol", "URL contains '@' (hides the real destination)", 0.5, evidence=p["raw"][:60]))
    if p["scheme"] == "http" or (not p["had_scheme"] and not trusted):
        ind.append(_ind("no_https", "Page is not served over HTTPS", 0.12, evidence=p["scheme"] or "no scheme"))
    if reg in db.patterns().get("shorteners", []):
        ind.append(_ind("shortener", "Shortened link hides the real destination", 0.3, evidence=reg))
    if not result["trusted"]:
        if p["tld"] in db.patterns().get("suspicious_tlds", []):
            ind.append(_ind("bad_tld", f"Domain ends in '.{p['tld']}', often abused for scams", 0.3, evidence="." + p["tld"]))
        if "xn--" in host:
            ind.append(_ind("punycode", "Internationalised (punycode) domain - possible look-alike", 0.45, evidence=host))
        if len(p["subdomain"].split(".")) >= 3:
            ind.append(_ind("many_subdomains", "Unusually many subdomains", 0.3, evidence=p["subdomain"]))
        if host.count("-") >= 3:
            ind.append(_ind("many_hyphens", "Domain stuffed with hyphens", 0.3, evidence=host))
        elif host.count("-") == 2:
            ind.append(_ind("hyphens", "Domain contains multiple hyphens", 0.15, evidence=host))
        if sum(c.isdigit() for c in host) >= 4 and not p["is_ip"]:
            ind.append(_ind("digits", "Many digits inside the domain name", 0.15, evidence=host))
        if len(p["raw"]) > 100:
            ind.append(_ind("long_url", "Very long URL", 0.12, evidence=f"{len(p['raw'])} chars"))

        # keywords commonly used on credential-harvesting pages
        kws = [k for k in db.patterns().get("url_keywords", []) if k in full_lower]
        if kws:
            w = min(0.45, 0.14 * len(kws))
            ind.append(_ind("keywords", "Sensitive keywords in URL: " + ", ".join(kws[:5]), w, "credential", ", ".join(kws[:5])))

        # brand impersonation / look-alike
        tokens = [t for t in re.split(r"[-._0-9]+", host) if t]
        label = reg.split(".")[0] if reg else ""
        deleet = label.translate(_LEET)
        flagged = False
        for brand, legit in db.brands().items():
            if reg in legit or any(reg.endswith("." + d) for d in legit):
                continue
            if brand in tokens or (len(brand) >= 5 and brand in host):
                ind.append(_ind("brand_impersonation", f"Uses the '{brand}' brand name but is not an official {brand} domain", 0.7, "identity", host))
                flagged = True
                break
            if len(brand) >= 4 and label != brand and (deleet == brand or _edit_distance_le1(deleet, brand)):
                ind.append(_ind("lookalike", f"Domain looks like '{brand}' (typo-squatting)", 0.75, "identity", host))
                flagged = True
                break
        if not flagged and label != deleet and any(c.isdigit() for c in label) and any(c.isalpha() for c in label):
            ind.append(_ind("leet", "Digits replace letters in the domain (e.g. 0 for o)", 0.2, "identity", label))

    result["indicators"] = ind
    result["score"] = int(round(100 * noisy_or([i["weight"] for i in ind])))
    return result
