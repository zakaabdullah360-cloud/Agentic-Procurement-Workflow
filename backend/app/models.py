import datetime as dt

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


def now():
    return dt.datetime.utcnow()


class Supplier(Base):
    """
    A vendor/supplier catalog source. Populated once at seed time from the
    CSV datasets (procurement) or from a small hardcoded set (software
    vendor renewal use case) - same table, different `category`, which is
    what lets one orchestrator serve two business domains.
    """
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, default="laptop_supplier")
    source_file = Column(String, nullable=True)
    currency = Column(String, default="PKR")
    unit_price = Column(Float, nullable=False)       # representative unit price for demo item
    lead_time_days = Column(Integer, nullable=False)  # delivery time / activation time
    warranty_years = Column(Float, nullable=False)     # or contract term for renewal use case
    rating = Column(Float, nullable=True)
    catalog_size = Column(Integer, nullable=True)


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True)
    request_text = Column(Text, nullable=False)
    workflow_type = Column(String, nullable=False, default="procurement")
    status = Column(String, nullable=False, default="pending")
    # pending / in_progress / awaiting_approval / approved / rejected / failed / done
    failure_reason = Column(Text, nullable=True)
    extracted_params = Column(Text, nullable=True)   # JSON string
    final_report = Column(Text, nullable=True)        # JSON string
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    steps = relationship("WorkflowStep", back_populates="workflow", cascade="all, delete-orphan")
    logs = relationship("ToolLog", back_populates="workflow", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    step_name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    # pending / in_progress / done / failed / skipped
    output_json = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    workflow = relationship("Workflow", back_populates="steps")


class ToolLog(Base):
    __tablename__ = "tool_logs"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    input_json = Column(Text, nullable=True)
    output_json = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="success")  # success / error
    error = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=now)

    workflow = relationship("Workflow", back_populates="logs")


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    warranty_years = Column(Float, nullable=False)
    within_budget = Column(Boolean, default=True)
    score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    score_breakdown_json = Column(Text, nullable=True)

    workflow = relationship("Workflow", back_populates="quotes")
    supplier = relationship("Supplier")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    item = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    currency = Column(String, default="PKR")
    terms = Column(Text, nullable=True)
    file_path = Column(String, nullable=True)
    validated = Column(Boolean, default=False)
    validation_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)

    workflow = relationship("Workflow")
    supplier = relationship("Supplier")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending / approved / rejected
    approver = Column(String, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=now)
    decided_at = Column(DateTime, nullable=True)

    workflow = relationship("Workflow")
    purchase_order = relationship("PurchaseOrder")
