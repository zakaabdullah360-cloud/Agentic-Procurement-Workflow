import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Workflow, WorkflowStep, ToolLog, Quote, PurchaseOrder, Approval
from app.schemas import WorkflowCreateRequest, WorkflowSummary, WorkflowStepOut, ToolLogOut, WorkflowDetailOut
from app.agents.orchestrator import run_workflow

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowDetailOut)
def create_workflow(payload: WorkflowCreateRequest, db: Session = Depends(get_db)):
    wf = Workflow(request_text=payload.request_text, status="pending")
    db.add(wf)
    db.commit()
    db.refresh(wf)

    run_workflow(db, wf)  # synchronous for demo simplicity/predictability
    db.refresh(wf)

    return _to_detail(db, wf)


@router.get("", response_model=list[WorkflowSummary])
def list_workflows(db: Session = Depends(get_db)):
    return db.query(Workflow).order_by(Workflow.id.desc()).all()


@router.get("/{workflow_id}", response_model=WorkflowDetailOut)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    wf = db.query(Workflow).get(workflow_id)
    if not wf:
        raise HTTPException(404, "workflow not found")
    return _to_detail(db, wf)


@router.get("/{workflow_id}/steps", response_model=list[WorkflowStepOut])
def get_steps(workflow_id: int, db: Session = Depends(get_db)):
    return (
        db.query(WorkflowStep)
        .filter(WorkflowStep.workflow_id == workflow_id)
        .order_by(WorkflowStep.step_order)
        .all()
    )


@router.get("/{workflow_id}/logs", response_model=list[ToolLogOut])
def get_logs(workflow_id: int, db: Session = Depends(get_db)):
    return (
        db.query(ToolLog)
        .filter(ToolLog.workflow_id == workflow_id)
        .order_by(ToolLog.id)
        .all()
    )


def _to_detail(db: Session, wf: Workflow) -> dict:
    steps = (
        db.query(WorkflowStep)
        .filter(WorkflowStep.workflow_id == wf.id)
        .order_by(WorkflowStep.step_order)
        .all()
    )
    quotes = (
        db.query(Quote)
        .filter(Quote.workflow_id == wf.id)
        .order_by(Quote.rank.is_(None), Quote.rank)
        .all()
    )
    po = db.query(PurchaseOrder).filter(PurchaseOrder.workflow_id == wf.id).first()
    approval = db.query(Approval).filter(Approval.workflow_id == wf.id).first()

    return {
        "workflow": wf,
        "extracted_params": json.loads(wf.extracted_params) if wf.extracted_params else None,
        "steps": steps,
        "quotes": quotes,
        "purchase_order": po,
        "approval": approval,
        "final_report": json.loads(wf.final_report) if wf.final_report else None,
    }
