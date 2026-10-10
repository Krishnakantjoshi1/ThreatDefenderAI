from fastapi import APIRouter

from app.api.schemas import ProtectionUpdate
from app.services import protection_service

router = APIRouter(prefix="/api", tags=["protection"])


@router.get("/protection")
def get_protection():
    return protection_service.status()


@router.post("/protection")
def set_protection(req: ProtectionUpdate):
    return protection_service.set_enabled(req.enabled)
