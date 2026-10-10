import re
import unicodedata

_ZERO_WIDTH = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
_SPACES = re.compile(r"[ \t\r\f\v]+")
_LONG_DIGITS = re.compile(r"\d{4,}")


def normalize_text(text: str) -> str:
    """NFKC-normalise, strip zero-width characters (used to dodge keyword filters)."""
    text = unicodedata.normalize("NFKC", text or "")
    text = _ZERO_WIDTH.sub("", text)
    return _SPACES.sub(" ", text).strip()


def mask_preview(text: str, limit: int = 80) -> str:
    """Short, masked preview for history (long digit runs hidden)."""
    t = _LONG_DIGITS.sub("****", _SPACES.sub(" ", text or "").strip())
    return t[:limit] + ("..." if len(t) > limit else "")
