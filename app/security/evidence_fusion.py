"""Merge indicators from every detector into one ranked, de-duplicated evidence list."""
from typing import Dict, List


def fuse(*groups: List[Dict]) -> List[Dict]:
    seen, out = set(), []
    for g in groups:
        for i in g or []:
            key = (i["code"], i.get("evidence", ""))
            if key in seen:
                continue
            seen.add(key)
            out.append(i)
    # context-only (<=0.05) signals are kept for transparency but sorted last
    out.sort(key=lambda i: -i["weight"])
    return out


def top_reasons(indicators: List[Dict], limit: int = 8) -> List[Dict]:
    """Reasons shown to the user: drop context-only signals."""
    return [{"label": i["label"], "dimension": i["dimension"], "weight": round(i["weight"], 2),
             "evidence": i.get("evidence", ""), "source": i.get("source", "")}
            for i in indicators if i["weight"] > 0.06][:limit]
