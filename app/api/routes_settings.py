from fastapi import APIRouter, HTTPException

from app.api.schemas import SettingsUpdate
from app.database import repository as repo
from app.modes import mode_state, network_monitor
from app.modes.controller import resolve_mode
from app.tools import online_health, threat_intelligence

router = APIRouter(prefix="/api", tags=["settings"])


def _b(v: bool) -> str:
    return "true" if v else "false"


@router.get("/settings")
def get_settings():
    return {"settings": repo.all_settings(), "mode": resolve_mode()}


@router.post("/settings")
def update_settings(req: SettingsUpdate):
    try:
        if req.mode_preference is not None or req.manual_mode is not None:
            mode_state.set_preference(req.mode_preference or mode_state.get_preference(), req.manual_mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if req.force_offline is not None:
        repo.set_setting("force_offline", _b(req.force_offline))
    if req.store_preview is not None:
        repo.set_setting("store_preview", _b(req.store_preview))
    if req.protection_enabled is not None:
        repo.set_setting("protection_enabled", _b(req.protection_enabled))
    network_monitor.reset_cache()
    return {"settings": repo.all_settings(), "mode": resolve_mode()}


@router.get("/mode")
def get_mode():
    return resolve_mode()


@router.get("/intel/status")
def intel_status():
    return online_health.status()


@router.post("/intel/update")
def intel_update():
    if not resolve_mode()["network"] == "connected":
        return {"ok": False, "detail": "No internet connection. Local protection keeps working; try again when online."}
    return threat_intelligence.update_feed()
