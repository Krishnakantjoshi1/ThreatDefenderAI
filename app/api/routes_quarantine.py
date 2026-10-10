from fastapi import APIRouter, HTTPException

from app.services import quarantine_service

router = APIRouter(prefix="/api", tags=["quarantine"])


@router.get("/quarantine")
def list_quarantine():
    return {"items": quarantine_service.list_items()}


@router.post("/quarantine/{item_id}/restore")
def restore(item_id: int):
    try:
        return quarantine_service.restore(item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/quarantine/{item_id}")
def delete(item_id: int):
    try:
        return quarantine_service.delete(item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
