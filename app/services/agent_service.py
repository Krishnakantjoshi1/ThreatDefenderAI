"""AI agent service: asks local Phi-3 to explain an engine verdict (never to decide it)."""
from typing import Dict, Optional

from app.ai import ollama_client
from app.ai.explanation import explain
from app.database import repository as repo


def explain_scan(scan_id: int, content: Optional[str] = None, lang: str = "en", use_ai: bool = True) -> Dict:
    scan = repo.get_scan(scan_id)
    if not scan:
        raise KeyError("Scan not found")
    result = scan["result"]
    explanation = explain(result, content=content, lang=lang, use_ai=use_ai)
    repo.save_explanation(scan_id, explanation)
    return explanation


def ai_status() -> Dict:
    return ollama_client.status()
