import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Approval, Workflow
from app.schemas import ApprovalOut, ApprovalDecisionRequest
from app.agents.orchestrator import finalize_after_approval

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalOut])
def list_pending_approvals(db: Session = Depends(get_db)):
    return db.query(Approval).filter(Approval.status == "pending").order_by(Approval.id).all()


@router.post("/{approval_id}/approve", response_model=ApprovalOut)
def approve(approval_id: int, payload: ApprovalDecisionRequest, db: Session = Depends(get_db)):
    return _decide(db, approval_id, "approved", payload)


@router.post("/{approval_id}/reject", response_model=ApprovalOut)
def reject(approval_id: int, payload: ApprovalDecisionRequest, db: Session = Depends(get_db)):
    return _decide(db, approval_id, "rejected", payload)


def _decide(db: Session, approval_id: int, decision: str, payload: ApprovalDecisionRequest):
    approval = db.query(Approval).get(approval_id)
    if not approval:
        raise HTTPException(404, "approval not found")
    if approval.status != "pending":
        raise HTTPException(400, f"approval already {approval.status}")

    approval.status = decision
    approval.approver = payload.approver
    approval.comment = payload.comment
    approval.decided_at = dt.datetime.utcnow()
    db.commit()
    db.refresh(approval)

    workflow = db.query(Workflow).get(approval.workflow_id)
    finalize_after_approval(db, workflow, approval)

    return approval
