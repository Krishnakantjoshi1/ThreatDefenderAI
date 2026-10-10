from typing import Dict, List, Optional

from app.database import repository as repo


def list_history(limit: int = 50, min_score: int = 0) -> List[Dict]:
    return repo.list_scans(max(1, min(limit, 500)), max(0, min_score))


def get_item(scan_id: int) -> Optional[Dict]:
    return repo.get_scan(scan_id)


def delete_item(scan_id: int) -> bool:
    return repo.delete_scan(scan_id)


def clear_all() -> int:
    return repo.clear_scans()


def get_stats() -> Dict:
    s = repo.stats()
    s["memory_entries"] = repo.memory_count()
    return s


def get_memory(limit: int = 50) -> List[Dict]:
    return repo.memory_list(limit)
