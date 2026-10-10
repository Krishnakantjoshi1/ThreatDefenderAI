from typing import Dict, List

from app.database import repository as repo
from app.security import quarantine


def list_items() -> List[Dict]:
    items = repo.list_quarantine()
    for i in items:
        i.pop("path", None)  # internal storage path is not exposed to the UI
    return items


def restore(item_id: int) -> Dict:
    return quarantine.restore_item(item_id)


def delete(item_id: int) -> Dict:
    return quarantine.delete_item(item_id)
