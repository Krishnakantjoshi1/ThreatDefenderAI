"""Scan orchestrator: parse -> detectors -> Honeycomb -> risk engine -> intelligence -> persist.

Detection is fully local. Online tools run only when the controller's effective mode allows it.
"""
import time
from typing import Dict, List, Optional

from app import config
from app.ai.explanation import quick_explanation
from app.database import repository as repo
from app.detectors.behavior_detector import analyze_behavior
from app.detectors.content_detector import analyze_page
from app.detectors.file_detector import analyze_file
from app.detectors.sender_detector import analyze_sender
from app.detectors.text_detector import analyze_text
from app.detectors.url_detector import analyze_url, noisy_or
from app.honeycomb.analyzer import build_honeycomb
from app.intelligence import threat_memory
from app.intelligence.scam_dna import scam_dna
from app.modes.controller import resolve_mode
from app.security.attack_chain import build_attack_chain
from app.security.evidence_fusion import fuse, top_reasons
from app.security.quarantine import quarantine_item
from app.security.risk_engine import compute_risk
from app.tools.tool_registry import run_online_tools
from app.utils.hashing import fingerprint, sha256_bytes
from app.utils.text_utils import mask_preview, normalize_text
from app.utils.url_utils import extract_urls, is_single_url, parse_url

_BREADTH = {0: 0, 1: 0, 2: 25, 3: 50, 4: 70, 5: 85}


def _pipeline(kind: str, text: str, url_list: List[str], sender: Optional[str], online: bool,
              extra_indicators: Optional[List[Dict]] = None, extra_components: Optional[Dict[str, int]] = None,
              text_for_analysis: Optional[str] = None, fp_source: str = "", preview_source: str = "",
              file_info: Optional[Dict] = None, data: Optional[bytes] = None, page_info: Optional[Dict] = None) -> Dict:
    t0 = time.perf_counter()
    mode = resolve_mode()

    url_results = [analyze_url(u) for u in url_list[:10]]
    text_res = analyze_text(text_for_analysis) if text_for_analysis else {"score": 0, "indicators": []}
    sender_res = analyze_sender(sender or "")

    # Online intelligence (skipped entirely in OFFLINE mode or when the caller wants the fast path)
    online_report = {"used": False, "mode": mode["effective"], "sent": [], "results": [], "indicators": [],
                     "note": "Fast local scan (online tools skipped)." if not online else ""}
    if online and url_results:
        online_report = run_online_tools(url_results, mode["effective"])

    url_inds = [i for u in url_results for i in u["indicators"]]
    all_inds = fuse(text_res["indicators"], url_inds, sender_res["indicators"],
                    online_report["indicators"], extra_indicators or [])

    honeycomb = build_honeycomb(all_inds, url_results)
    behavior = analyze_behavior(honeycomb["scores"])

    reg_domains = sorted({u["registered_domain"] for u in url_results if u["registered_domain"]})
    fp = fingerprint(fp_source or text or "")
    memory = threat_memory.lookup(fp, reg_domains)

    known_bad = any(u.get("known_bad") for u in url_results) or any(i["code"] == "known_bad_hash" for i in all_inds)
    hot = honeycomb["hot_count"]
    components = {
        "url": max([u["score"] for u in url_results], default=0),
        "text": text_res["score"],
        "sender": sender_res["score"],
        "behavior": behavior["score"],
        "honeycomb": _BREADTH.get(hot, 95),
        "memory": int(memory["prior_risk"] * 0.8) if memory["prior_risk"] >= 60 else 0,
        "intel": 97 if known_bad else 0,
        "online": int(round(100 * noisy_or([i["weight"] for i in online_report["indicators"]]))),
    }
    components.update(extra_components or {})
    risk = compute_risk(components)

    all_with_behavior = fuse(all_inds, behavior["behaviors"])
    category = honeycomb["category"] if risk["verdict"] != "SAFE" else "None detected"
    dna = scam_dna(honeycomb["scores"])
    chain = build_attack_chain(honeycomb["scores"], all_with_behavior, risk["score"]) if risk["verdict"] != "SAFE" else []

    result: Dict = {
        "kind": kind,
        "score": risk["score"], "verdict": risk["verdict"], "action": risk["action"],
        "category": category,
        "components": risk["components"],
        "reasons": top_reasons(all_with_behavior),
        "honeycomb": honeycomb,
        "behavior": behavior,
        "scam_dna": dna,
        "attack_chain": chain,
        "memory": memory,
        "urls": [{"url": u["url"][:200], "host": u["host"], "registered_domain": u["registered_domain"],
                  "score": u["score"], "trusted": u["trusted"], "known_bad": u["known_bad"],
                  "indicators": [i["label"] for i in u["indicators"]]} for u in url_results],
        "online": {k: online_report[k] for k in ("used", "mode", "sent", "results", "note")},
        "mode": {k: mode[k] for k in ("effective", "network", "fallback", "note", "preference")},
        "fingerprint": fp,
    }
    if file_info:
        result["file"] = file_info
    if page_info:
        result["page"] = page_info
    result["summary"] = _summary(result)
    result["quick_explanation"] = quick_explanation(result)

    # ---- persist (privacy: masked preview + fingerprint only) ----
    store_preview = repo.get_bool("store_preview")
    preview = mask_preview(preview_source or text) if store_preview else "[hidden by privacy setting]"
    stored = _redact(result) if not store_preview else result
    scan_id = repo.add_scan(kind, preview, fp, result["score"], result["verdict"], result["action"], category, stored)
    result["id"] = scan_id
    stored["id"] = scan_id
    repo.update_scan_result(scan_id, stored)

    threat_memory.remember(fp, category, result["score"], [i["code"] for i in all_with_behavior if i["weight"] > 0.06], reg_domains)

    result["quarantine"] = None
    if risk["verdict"] == "CRITICAL":
        name = (file_info or {}).get("filename") or (url_results[0]["host"] if url_results else "Suspicious message")
        reason = category + (" - " + result["reasons"][0]["label"] if result["reasons"] else "")
        q = quarantine_item(scan_id, "file" if file_info else kind, name, reason, result["score"],
                            (file_info or {}).get("sha256") or fp, data if file_info else None)
        result["quarantine"] = q

    result["latency_ms"] = int((time.perf_counter() - t0) * 1000)
    return result


def _summary(r: Dict) -> str:
    if r["verdict"] == "SAFE":
        return "No meaningful threat indicators found."
    top = r["reasons"][0]["label"] if r["reasons"] else r["category"]
    return f"{r['category']}: {top}"


def _redact(result: Dict) -> Dict:
    import copy
    r = copy.deepcopy(result)
    for reason in r.get("reasons", []):
        reason["evidence"] = ""
    for u in r.get("urls", []):
        u["url"] = u["host"]
    return r


# ---------------------------------------------------------------- public API
def scan_input(content: str, kind: Optional[str] = None, sender: Optional[str] = None, online: bool = True) -> Dict:
    text = normalize_text(content)[: config.MAX_TEXT_CHARS]
    if not text:
        raise ValueError("Nothing to scan: content is empty")
    kind = (kind or "auto").lower()
    if kind == "auto":
        kind = "url" if is_single_url(text) else "text"
    if kind not in ("url", "text"):
        raise ValueError("kind must be 'auto', 'url' or 'text'")

    if kind == "url":
        urls = [text]
        return _pipeline("url", text, urls, sender, online, fp_source=_canon_url(text), preview_source=text)
    urls = extract_urls(text)
    return _pipeline("text", text, urls, sender, online, text_for_analysis=text)


def _canon_url(u: str) -> str:
    p = parse_url(u)
    return f"{p['host']}{p['path']}".lower()


def scan_file(filename: str, data: bytes, online: bool = False) -> Dict:
    if len(data) > config.MAX_FILE_BYTES:
        raise ValueError(f"File too large (limit {config.MAX_FILE_BYTES // (1024 * 1024)} MB)")
    fr = analyze_file(filename, data)
    inner_text = fr["text_preview"]
    urls = extract_urls(inner_text) if inner_text else []
    info = {"filename": fr["filename"], "extension": fr["extension"], "size": fr["size"], "sha256": fr["sha256"]}
    return _pipeline("file", fr["filename"], urls, None, online, extra_indicators=fr["indicators"],
                     extra_components={"file": fr["score"]}, text_for_analysis=inner_text or None,
                     fp_source=fr["sha256"], preview_source=fr["filename"], file_info=info, data=data)


def scan_page(url: str, title: str = "", text: str = "", has_password_field: bool = False,
              forms: Optional[List[Dict]] = None, hidden_iframes: int = 0, online: bool = False) -> Dict:
    ur = analyze_url(url)
    suspicious = ur["score"] >= 30
    content_res = analyze_page(url, has_password_field, forms or [], hidden_iframes, suspicious, ur["trusted"])
    # Page text is only analysed when the page looks like a data-collection page or the URL is already suspicious,
    # so ordinary articles about scams are not flagged.
    analyse_text = (has_password_field or suspicious) and not ur["trusted"]
    body = normalize_text(text)[:4000] if analyse_text else ""
    info = {"url": url[:200], "title": (title or "")[:120], "has_password_field": bool(has_password_field)}
    return _pipeline("page", body, [url], None, online, extra_indicators=content_res["indicators"],
                     extra_components={"content": content_res["score"]},
                     text_for_analysis=body or None, fp_source=_canon_url(url), preview_source=url, page_info=info)
