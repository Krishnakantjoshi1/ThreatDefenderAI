from app.database import repository as repo

VALID_MODES = ("offline", "online", "hybrid")


def get_preference() -> str:
    v = repo.get_setting("mode_preference")
    return v if v in ("auto", "manual") else "auto"


def get_manual_mode() -> str:
    v = repo.get_setting("manual_mode")
    return v if v in VALID_MODES else "hybrid"


def set_preference(pref: str, manual_mode: str = None) -> None:
    if pref not in ("auto", "manual"):
        raise ValueError("mode_preference must be 'auto' or 'manual'")
    repo.set_setting("mode_preference", pref)
    if manual_mode is not None:
        if manual_mode not in VALID_MODES:
            raise ValueError("manual_mode must be offline, online or hybrid")
        repo.set_setting("manual_mode", manual_mode)
