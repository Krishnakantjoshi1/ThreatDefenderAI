from typing import Dict

from app.modes.controller import resolve_mode
from app.security import protection


def status() -> Dict:
    return {"enabled": protection.is_enabled(), "mode": resolve_mode()}


def set_enabled(value: bool) -> Dict:
    protection.set_enabled(value)
    return status()
