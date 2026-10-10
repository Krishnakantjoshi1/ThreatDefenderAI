from fastapi import APIRouter

from app import config
from app.modes.controller import resolve_mode
from app.security import protection

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    return {"status": "ok", "app": config.APP_NAME, "version": config.APP_VERSION,
            "protection_enabled": protection.is_enabled(), "mode": resolve_mode()}
