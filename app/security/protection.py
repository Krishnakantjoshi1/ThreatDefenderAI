"""Protection controller: master on/off switch used by the browser extension."""
from app.database import repository as repo


def is_enabled() -> bool:
    return repo.get_bool("protection_enabled")


def set_enabled(value: bool) -> bool:
    repo.set_setting("protection_enabled", "true" if value else "false")
    return value
