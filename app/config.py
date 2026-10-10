"""ThreatDefender AI - central configuration.

All paths are resolved at call time so tests can point TD_DATA_DIR at a temp folder.
Settings can be overridden with environment variables or a `.env` file.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Tiny .env loader (no external dependency)."""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

APP_NAME = "ThreatDefender AI"
APP_VERSION = "1.0.0"
HOST = os.getenv("TD_HOST", "127.0.0.1")
PORT = int(os.getenv("TD_PORT", "8000"))

# Local AI (Ollama). Must be a loopback address - see ai/ollama_client.py.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "90"))

# Optional online intelligence
SAFE_BROWSING_KEY = os.getenv("SAFE_BROWSING_KEY", "").strip()
ONLINE_TIMEOUT = float(os.getenv("TD_ONLINE_TIMEOUT", "4"))

# Limits
MAX_TEXT_CHARS = 20000
MAX_FILE_BYTES = 10 * 1024 * 1024

# Risk thresholds (0-100)
THRESHOLDS = {"SAFE": 0, "SUSPICIOUS": 30, "DANGEROUS": 60, "CRITICAL": 80}


def data_dir() -> Path:
    path = Path(os.getenv("TD_DATA_DIR", str(BASE_DIR / "data")))
    path.mkdir(parents=True, exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "threatdefender.db"


def quarantine_dir() -> Path:
    path = data_dir() / "quarantine"
    path.mkdir(parents=True, exist_ok=True)
    return path


def threats_dir() -> Path:
    """Shipped threat data (read-only, always inside the project)."""
    return BASE_DIR / "data" / "threats"


def feed_path() -> Path:
    return data_dir() / "threat_feed.txt"


def frontend_dir() -> Path:
    return BASE_DIR / "frontend"
