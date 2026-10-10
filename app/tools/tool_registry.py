"""Runs online tools ONLY when the effective mode allows it, and reports exactly what was sent."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Dict, List

from app import config
from app.tools import domain_lookup, url_reputation


def _ind(code, label, weight, evidence):
    return {"code": code, "label": label, "weight": weight, "dimension": "link",
            "evidence": evidence, "source": "online"}


def run_online_tools(url_results: List[Dict], mode: str) -> Dict:
    report: Dict = {"used": False, "mode": mode, "sent": [], "results": [], "indicators": [], "note": ""}
    if mode == "offline":
        report["note"] = "Offline: no data left this device."
        return report

    targets = [u for u in url_results if u.get("host") and not u.get("trusted") and not u.get("known_bad")]
    targets.sort(key=lambda u: -u["score"])
    targets = targets[:3]
    if not targets:
        report["note"] = "No unknown domains to check online."
        return report

    jobs = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for u in targets:
            jobs.append((u, "domain_lookup", pool.submit(domain_lookup.lookup, u["registered_domain"], u["host"])))
            report["sent"].append({"what": "domain name", "value": u["registered_domain"], "to": "DNS + rdap.org"})
            if mode == "online" and url_reputation.available():
                jobs.append((u, "safe_browsing", pool.submit(url_reputation.check, u["url"])))
                report["sent"].append({"what": "full URL", "value": u["url"][:80], "to": "Google Safe Browsing"})
        for u, name, fut in jobs:
            try:
                res = fut.result(timeout=config.ONLINE_TIMEOUT + 3)
            except (FutureTimeout, Exception) as exc:  # never let an online tool break a scan
                res = {"tool": name, "ok": False, "detail": f"failed ({type(exc).__name__})"}
            report["results"].append(res)
            if name == "domain_lookup" and res.get("ok"):
                age = res.get("age_days")
                if age is not None and age < 30:
                    report["indicators"].append(_ind("new_domain", f"Domain was registered only {age} days ago", 0.45, u["registered_domain"]))
                elif age is not None and age < 90:
                    report["indicators"].append(_ind("young_domain", f"Domain is young ({age} days old)", 0.2, u["registered_domain"]))
                if res.get("resolves") is False:
                    report["indicators"].append(_ind("no_dns", "Domain does not resolve in DNS", 0.1, u["host"]))
            if name == "safe_browsing" and res.get("ok") and res.get("malicious"):
                report["indicators"].append(_ind("safe_browsing", "Flagged as dangerous by Google Safe Browsing", 0.97, u["host"]))

    report["used"] = any(r.get("ok") for r in report["results"])
    if not report["used"]:
        report["note"] = "Online tools were unreachable; the verdict is based on local analysis only."
    else:
        report["note"] = "Online intelligence added to the local analysis."
    return report
