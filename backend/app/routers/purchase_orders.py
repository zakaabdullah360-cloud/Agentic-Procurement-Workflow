from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PurchaseOrder
from app.schemas import PurchaseOrderOut

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase-orders"])


@router.get("/{po_id}", response_model=PurchaseOrderOut)
def get_po(po_id: int, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).get(po_id)
    if not po:
        raise HTTPException(404, "purchase order not found")
    return po


@router.get("/{po_id}/download")
def download_po(po_id: int, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).get(po_id)
    if not po or not po.file_path:
        raise HTTPException(404, "purchase order file not found")
    return FileResponse(
        po.file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"PO_{po_id}.docx",
    )
