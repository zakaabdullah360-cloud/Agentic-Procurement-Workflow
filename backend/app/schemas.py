import datetime as dt
from typing import Optional, List, Any

from pydantic import BaseModel


class WorkflowCreateRequest(BaseModel):
    request_text: str


class WorkflowSummary(BaseModel):
    id: int
    request_text: str
    workflow_type: str
    status: str
    failure_reason: Optional[str] = None
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        from_attributes = True


class WorkflowStepOut(BaseModel):
    id: int
    step_order: int
    step_name: str
    status: str
    output_json: Optional[str] = None
    started_at: Optional[dt.datetime] = None
    finished_at: Optional[dt.datetime] = None

    class Config:
        from_attributes = True


class ToolLogOut(BaseModel):
    id: int
    tool_name: str
    input_json: Optional[str] = None
    output_json: Optional[str] = None
    status: str
    error: Optional[str] = None
    timestamp: dt.datetime

    class Config:
        from_attributes = True


class SupplierOut(BaseModel):
    id: int
    name: str
    category: str
    currency: str
    unit_price: float
    lead_time_days: int
    warranty_years: float
    rating: Optional[float] = None

    class Config:
        from_attributes = True


class QuoteOut(BaseModel):
    id: int
    supplier: SupplierOut
    quantity: int
    unit_price: float
    total_price: float
    lead_time_days: int
    warranty_years: float
    within_budget: bool
    score: Optional[float] = None
    rank: Optional[int] = None
    score_breakdown_json: Optional[str] = None

    class Config:
        from_attributes = True


class PurchaseOrderOut(BaseModel):
    id: int
    item: str
    quantity: int
    unit_price: float
    subtotal: float
    total: float
    currency: str
    terms: Optional[str] = None
    validated: bool
    validation_notes: Optional[str] = None
    file_path: Optional[str] = None

    class Config:
        from_attributes = True


class ApprovalOut(BaseModel):
    id: int
    status: str
    approver: Optional[str] = None
    comment: Optional[str] = None
    created_at: dt.datetime
    decided_at: Optional[dt.datetime] = None

    class Config:
        from_attributes = True


class ApprovalDecisionRequest(BaseModel):
    approver: str = "Demo Manager"
    comment: Optional[str] = None


class WorkflowDetailOut(BaseModel):
    workflow: WorkflowSummary
    extracted_params: Optional[dict] = None
    steps: List[WorkflowStepOut]
    quotes: List[QuoteOut]
    purchase_order: Optional[PurchaseOrderOut] = None
    approval: Optional[ApprovalOut] = None
    final_report: Optional[Any] = None
