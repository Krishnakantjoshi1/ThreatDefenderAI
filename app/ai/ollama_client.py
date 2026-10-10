"""Minimal Ollama client (stdlib only). PRIVACY: refuses any non-loopback Ollama address,
so message content can never be sent to a remote AI by accident."""
import json
import urllib.error
import urllib.request
from typing import Dict, Optional
from urllib.parse import urlsplit

from app import config
from app.utils.logger import get_logger

log = get_logger("ollama")
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def _base() -> Optional[str]:
    host = urlsplit(config.OLLAMA_URL).hostname or ""
    if host not in _LOOPBACK:
        log.warning("OLLAMA_URL %s is not a loopback address - local AI disabled for privacy.", config.OLLAMA_URL)
        return None
    return config.OLLAMA_URL.rstrip("/")


def status() -> Dict:
    out = {"running": False, "model": config.OLLAMA_MODEL, "model_ready": False, "models": [], "detail": ""}
    base = _base()
    if not base:
        out["detail"] = "OLLAMA_URL must point to this computer (127.0.0.1)"
        return out
    try:
        with urllib.request.urlopen(base + "/api/tags", timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
        names = [m.get("name", "") for m in data.get("models", [])]
        out.update(running=True, models=names)
        out["model_ready"] = any(n == config.OLLAMA_MODEL or n.startswith(config.OLLAMA_MODEL + ":") for n in names)
        out["detail"] = "ready" if out["model_ready"] else f"Ollama is running but model '{config.OLLAMA_MODEL}' is missing. Run: ollama pull {config.OLLAMA_MODEL}"
    except (urllib.error.URLError, OSError, ValueError):
        out["detail"] = "Ollama is not running (start it, or the app uses the built-in rule-based explainer)"
    return out


def generate(prompt: str, system: str = "", max_tokens: int = 320) -> Optional[str]:
    """Return generated text, or None on ANY failure (callers must have a fallback)."""
    base = _base()
    if not base:
        return None
    body = {"model": config.OLLAMA_MODEL, "prompt": prompt, "system": system, "stream": False,
            "options": {"temperature": 0.2, "num_predict": max_tokens}}
    try:
        req = urllib.request.Request(base + "/api/generate", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=config.OLLAMA_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        text = (data.get("response") or "").strip()
        return text or None
    except (urllib.error.URLError, OSError, ValueError) as exc:
        log.info("Ollama generate failed: %s", exc)
        return None
