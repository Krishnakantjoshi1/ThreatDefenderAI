import hashlib
import re


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8", errors="ignore"))


_URL = re.compile(r"(?i)(?:https?://|www\.)([^\s/<>\"']+)[^\s<>\"']*")
_DIGITS = re.compile(r"\d+")
_SPACES = re.compile(r"\s+")


def fingerprint(text: str) -> str:
    """Privacy-preserving fingerprint: URLs collapse to host, digits to '#', case folded.

    The original message cannot be recovered from this value.
    """
    t = _URL.sub(lambda m: " url:" + m.group(1).lower() + " ", text.lower())
    t = _DIGITS.sub("#", t)
    t = _SPACES.sub(" ", t).strip()
    return sha256_text(t)[:24]
