"""All SQL lives here."""
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.database.database import connect, init_db

DEFAULT_SETTINGS = {
    "mode_preference": "auto",      # auto | manual
    "manual_mode": "hybrid",        # offline | online | hybrid
    "protection_enabled": "true",
    "store_preview": "true",
    "force_offline": "false",       # demo switch: pretend the internet is down
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------- settings ----------------
def get_setting(key: str) -> str:
    init_db()
    with connect() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else DEFAULT_SETTINGS.get(key, "")


def set_setting(key: str, value: str) -> None:
    init_db()
    with connect() as c:
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, str(value)))


def all_settings() -> Dict[str, str]:
    return {k: get_setting(k) for k in DEFAULT_SETTINGS}


def get_bool(key: str) -> bool:
    return get_setting(key).lower() == "true"


# ---------------- scans ----------------
def add_scan(kind: str, preview: str, fp: str, score: int, verdict: str, action: str,
             category: str, result: Dict[str, Any]) -> int:
    init_db()
    with connect() as c:
        cur = c.execute(
            "INSERT INTO scans(created_at,kind,preview,fingerprint,score,verdict,action,category,result_json) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (now(), kind, preview, fp, score, verdict, action, category, json.dumps(result)))
        return int(cur.lastrowid)


def update_scan_result(scan_id: int, result: Dict[str, Any]) -> None:
    with connect() as c:
        c.execute("UPDATE scans SET result_json=? WHERE id=?", (json.dumps(result), scan_id))


def save_explanation(scan_id: int, explanation: Dict[str, Any]) -> None:
    with connect() as c:
        c.execute("UPDATE scans SET explanation_json=? WHERE id=?", (json.dumps(explanation), scan_id))


def _scan_row(row) -> Dict[str, Any]:
    d = dict(row)
    d["result"] = json.loads(d.pop("result_json"))
    ex = d.pop("explanation_json")
    d["explanation"] = json.loads(ex) if ex else None
    return d


def get_scan(scan_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    with connect() as c:
        row = c.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
    return _scan_row(row) if row else None


def list_scans(limit: int = 50, min_score: int = 0) -> List[Dict[str, Any]]:
    init_db()
    with connect() as c:
        rows = c.execute("SELECT id,created_at,kind,preview,score,verdict,action,category FROM scans "
                         "WHERE score>=? ORDER BY id DESC LIMIT ?", (min_score, limit)).fetchall()
    return [dict(r) for r in rows]


def delete_scan(scan_id: int) -> bool:
    with connect() as c:
        return c.execute("DELETE FROM scans WHERE id=?", (scan_id,)).rowcount > 0


def clear_scans() -> int:
    init_db()
    with connect() as c:
        return c.execute("DELETE FROM scans").rowcount


def stats() -> Dict[str, Any]:
    init_db()
    with connect() as c:
        total = c.execute("SELECT COUNT(*) n FROM scans").fetchone()["n"]
        by_verdict = {r["verdict"]: r["n"] for r in c.execute("SELECT verdict, COUNT(*) n FROM scans GROUP BY verdict")}
        blocked = c.execute("SELECT COUNT(*) n FROM scans WHERE action='BLOCK'").fetchone()["n"]
        quarantined = c.execute("SELECT COUNT(*) n FROM quarantine WHERE status='quarantined'").fetchone()["n"]
        last = c.execute("SELECT id,created_at,kind,preview,score,verdict,category FROM scans "
                         "WHERE score>=30 ORDER BY id DESC LIMIT 1").fetchone()
    threats = total - by_verdict.get("SAFE", 0)
    return {"total_scans": total, "threats_detected": threats, "blocked": blocked,
            "suspicious": by_verdict.get("SUSPICIOUS", 0), "dangerous": by_verdict.get("DANGEROUS", 0),
            "critical": by_verdict.get("CRITICAL", 0), "safe": by_verdict.get("SAFE", 0),
            "quarantined": quarantined, "last_threat": dict(last) if last else None}


# ---------------- quarantine ----------------
def add_quarantine(scan_id: Optional[int], kind: str, name: str, reason: str, score: int,
                   sha256: str, path: str) -> int:
    init_db()
    with connect() as c:
        cur = c.execute("INSERT INTO quarantine(created_at,scan_id,kind,name,reason,score,sha256,path,status) "
                        "VALUES(?,?,?,?,?,?,?,?, 'quarantined')",
                        (now(), scan_id, kind, name, reason, score, sha256, path))
        return int(cur.lastrowid)


def find_quarantined(sha256: str) -> Optional[Dict[str, Any]]:
    init_db()
    with connect() as c:
        row = c.execute("SELECT * FROM quarantine WHERE sha256=? AND status='quarantined'", (sha256,)).fetchone()
    return dict(row) if row else None


def list_quarantine(include_all: bool = False) -> List[Dict[str, Any]]:
    init_db()
    q = "SELECT * FROM quarantine " + ("" if include_all else "WHERE status='quarantined' ") + "ORDER BY id DESC"
    with connect() as c:
        return [dict(r) for r in c.execute(q).fetchall()]


def get_quarantine(item_id: int) -> Optional[Dict[str, Any]]:
    init_db()
    with connect() as c:
        row = c.execute("SELECT * FROM quarantine WHERE id=?", (item_id,)).fetchone()
    return dict(row) if row else None


def set_quarantine_status(item_id: int, status: str, path: Optional[str] = None) -> None:
    with connect() as c:
        if path is None:
            c.execute("UPDATE quarantine SET status=? WHERE id=?", (status, item_id))
        else:
            c.execute("UPDATE quarantine SET status=?, path=? WHERE id=?", (status, path, item_id))


# ---------------- threat memory ----------------
def memory_get(fp: str) -> Optional[Dict[str, Any]]:
    init_db()
    with connect() as c:
        row = c.execute("SELECT * FROM memory WHERE fingerprint=?", (fp,)).fetchone()
    return dict(row) if row else None


def memory_upsert(fp: str, category: str, risk: int, indicators: List[str]) -> None:
    init_db()
    with connect() as c:
        c.execute(
            "INSERT INTO memory(fingerprint,category,risk,indicators_json,first_seen,last_seen,count) "
            "VALUES(?,?,?,?,?,?,1) ON CONFLICT(fingerprint) DO UPDATE SET "
            "last_seen=excluded.last_seen, count=count+1, risk=MAX(risk, excluded.risk), category=excluded.category",
            (fp, category, risk, json.dumps(indicators), now(), now()))


def memory_list(limit: int = 50) -> List[Dict[str, Any]]:
    init_db()
    with connect() as c:
        rows = c.execute("SELECT * FROM memory ORDER BY last_seen DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def memory_count() -> int:
    init_db()
    with connect() as c:
        return c.execute("SELECT COUNT(*) n FROM memory").fetchone()["n"]
