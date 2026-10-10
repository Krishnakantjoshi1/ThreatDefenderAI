"""Web-page content signals (sent by the browser extension)."""
from typing import Dict, List

from app.detectors.url_detector import noisy_or
from app.utils.url_utils import parse_url, registered_domain


def _ind(code, label, weight, dimension="credential", evidence=""):
    return {"code": code, "label": label, "weight": weight, "dimension": dimension,
            "evidence": evidence, "source": "content"}


def analyze_page(page_url: str, has_password_field: bool, forms: List[Dict], hidden_iframes: int,
                 url_is_suspicious: bool, url_is_trusted: bool) -> Dict:
    ind: List[Dict] = []
    page_reg = parse_url(page_url)["registered_domain"]

    if has_password_field and not url_is_trusted:
        w = 0.35 if url_is_suspicious else 0.08
        ind.append(_ind("password_form", "Page asks for a password", w, "credential", "password field"))
    if has_password_field and parse_url(page_url)["scheme"] == "http":
        ind.append(_ind("password_over_http", "Password requested over an unencrypted (HTTP) connection", 0.45, "credential", "http"))

    for f in forms or []:
        action = str((f or {}).get("action", "") or "")
        if not action.startswith(("http://", "https://")):
            continue
        action_reg = registered_domain(parse_url(action)["host"])
        if action_reg and page_reg and action_reg != page_reg:
            w = 0.6 if has_password_field else 0.25
            ind.append(_ind("form_cross_domain", "Form sends your input to a different website", w, "credential", action_reg))
            break

    if hidden_iframes and hidden_iframes >= 1 and not url_is_trusted:
        ind.append(_ind("hidden_iframe", "Hidden iframe(s) on the page", 0.25, "link", f"{hidden_iframes} hidden"))

    return {"score": int(round(100 * noisy_or([i["weight"] for i in ind]))), "indicators": ind}
