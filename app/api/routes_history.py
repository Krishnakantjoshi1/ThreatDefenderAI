from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.services import history_service, report_service

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
def history(limit: int = 50, min_score: int = 0):
    return {"items": history_service.list_history(limit, min_score)}


@router.get("/reports/history.pdf")
def history_report():
    records = history_service.list_history(limit=500)
    pdf = report_service.build_pdf(records)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="threatdefender-history.pdf"'},
    )


@router.get("/reports/scans/{scan_id}.pdf")
def scan_report(scan_id: int):
    record = history_service.get_item(scan_id)
    if not record:
        raise HTTPException(status_code=404, detail="Scan not found")
    pdf = report_service.build_pdf([record], title="ThreatDefender scan report")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="threatdefender-scan-{scan_id}.pdf"'},
    )


@router.get("/history/{scan_id}")
def history_item(scan_id: int):
    item = history_service.get_item(scan_id)
    if not item:
        raise HTTPException(status_code=404, detail="Scan not found")
    return item


@router.delete("/history/{scan_id}")
def history_delete(scan_id: int):
    if not history_service.delete_item(scan_id):
        raise HTTPException(status_code=404, detail="Scan not found")
    return {"deleted": scan_id}


@router.delete("/history")
def history_clear():
    return {"deleted": history_service.clear_all()}


@router.get("/stats")
def stats():
    return history_service.get_stats()


@router.get("/memory")
def memory(limit: int = 50):
    return {"items": history_service.get_memory(limit)}
