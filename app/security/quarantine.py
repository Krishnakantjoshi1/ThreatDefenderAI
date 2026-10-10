"""Quarantine: suspicious items are isolated, never executed, never silently deleted."""
import os
import shutil
import uuid
from pathlib import Path
from typing import Dict, Optional

from app import config
from app.database import repository as repo
from app.utils.file_utils import safe_filename


def _inside_quarantine(path: Path) -> bool:
    try:
        path.resolve().relative_to(config.quarantine_dir().resolve())
        return True
    except ValueError:
        return False


def quarantine_item(scan_id: Optional[int], kind: str, name: str, reason: str, score: int,
                    sha256: str, data: Optional[bytes] = None) -> Dict:
    existing = repo.find_quarantined(sha256)
    if existing:
        return {"id": existing["id"], "new": False}
    path = ""
    if data is not None:
        target = config.quarantine_dir() / f"{uuid.uuid4().hex}.quarantined"
        target.write_bytes(data)  # stored inert: random name, no executable extension
        try:
            os.chmod(target, 0o600)
        except OSError:
            pass
        path = str(target)
    item_id = repo.add_quarantine(scan_id, kind, safe_filename(name) if kind == "file" else name[:120],
                                  reason[:300], score, sha256, path)
    return {"id": item_id, "new": True}


def restore_item(item_id: int) -> Dict:
    item = repo.get_quarantine(item_id)
    if not item or item["status"] != "quarantined":
        raise KeyError("Item not found or not in quarantine")
    restored_path = ""
    if item["path"] and Path(item["path"]).exists() and _inside_quarantine(Path(item["path"])):
        out_dir = config.quarantine_dir() / "restored"
        out_dir.mkdir(exist_ok=True)
        dest = out_dir / safe_filename(item["name"])
        if dest.exists():
            dest = out_dir / f"{uuid.uuid4().hex[:6]}_{safe_filename(item['name'])}"
        shutil.copy2(item["path"], dest)
        restored_path = str(dest)
    repo.set_quarantine_status(item_id, "restored", restored_path or item["path"])
    return {"id": item_id, "status": "restored", "path": restored_path}


def delete_item(item_id: int) -> Dict:
    item = repo.get_quarantine(item_id)
    if not item:
        raise KeyError("Item not found")
    p = Path(item["path"]) if item["path"] else None
    if p and p.exists() and _inside_quarantine(p):
        p.unlink()
    repo.set_quarantine_status(item_id, "deleted", "")
    return {"id": item_id, "status": "deleted"}
