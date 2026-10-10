import base64
import binascii

from fastapi import APIRouter, HTTPException

from app import config
from app.api.schemas import ExplainRequest, FileScanRequest, PageScanRequest, ScanRequest
from app.services import agent_service, scan_service

router = APIRouter(prefix="/api", tags=["scan"])


@router.post("/scan")
def scan(req: ScanRequest):
    try:
        return scan_service.scan_input(req.content, req.kind, req.sender, req.online)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/scan/page")
def scan_page(req: PageScanRequest):
    try:
        return scan_service.scan_page(req.url, req.title or "", req.text or "", req.has_password_field,
                                      req.forms, req.hidden_iframes, req.online)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/scan/file")
def scan_file(req: FileScanRequest):
    if len(req.content_b64) > config.MAX_FILE_BYTES * 4 // 3 + 16:
        raise HTTPException(status_code=413, detail="File too large")
    try:
        data = base64.b64decode(req.content_b64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="content_b64 is not valid base64")
    try:
        return scan_service.scan_file(req.filename, data)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc))


@router.post("/explain")
def explain(req: ExplainRequest):
    try:
        return agent_service.explain_scan(req.scan_id, req.content, req.lang, req.use_ai)
    except KeyError:
        raise HTTPException(status_code=404, detail="Scan not found")


@router.get("/ai/status")
def ai_status():
    return agent_service.ai_status()
