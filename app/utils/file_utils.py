import re
from pathlib import Path

_SAFE = re.compile(r"[^A-Za-z0-9._ -]")


def safe_filename(name: str) -> str:
    """Strip any path components / unsafe characters (blocks path traversal)."""
    base = Path(str(name).replace("\\", "/")).name
    base = _SAFE.sub("_", base).strip(" .")
    return base[:120] or "unnamed_file"
