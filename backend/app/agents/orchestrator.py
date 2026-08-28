"""
The orchestrator/executor. Runs the plan produced by planner.py step by
step, calling deterministic code and tools (never letting the LLM touch
money/quantities), logging every tool call, and stopping at the human
approval gate rather than auto-completing the workflow.

State machine for Workflow.status:
  pending -> in_progress -> awaiting_approval -> approved | rejected
                          -> failed  (budget/validation dead-ends)
                          -> done    (clarification-only runs)
"""
import datetime as dt
import json

from sqlalchemy.orm import Session

from app.models import Workflow, WorkflowStep, ToolLog, Quote, PurchaseOrder, Approval
from app.agents import parser, planner, supplier_tool, scoring, validator, po_generator


def _add_step(db: Session, workflow_id: int, order: int, name: str) -> WorkflowStep:
    step = WorkflowStep(workflow_id=workflow_id, step_order=order, step_name=name,
                         status="in_progress", started_at=dt.datetime.utcnow())
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


def _finish_step(db: Session, step: WorkflowStep, status: str, output: dict):
    step.status = status
    step.output_json = json.dumps(output, default=str)
    step.finished_at = dt.datetime.utcnow()
    db.commit()


def _log_tool(db: Session, workflow_id: int, tool_name: str, input_data, output_data,
              status="success", error=None):
    log = ToolLog(
        workflow_id=workflow_id,
        tool_name=tool_name,
        input_json=json.dumps(input_data, default=str),
        output_json=json.dumps(output_data, default=str),
        status=status,
        error=error,
    )
    db.add(log)
    db.commit()


def run_workflow(db: Session, workflow: Workflow):
    """Executes everything up to (and including) submitting for approval.
    Returns nothing - all state is persisted on `workflow` and its children."""
    workflow.status = "in_progress"
    db.commit()
    order = 0

    # --- Step: parse_request ---
    order += 1
    step = _add_step(db, workflow.id, order, "parse_request")
    try:
        structured = parser.parse_request(workflow.request_text)
        workflow.workflow_type = structured["workflow_type"]
        workflow.extracted_params = json.dumps(structured)
        _log_tool(db, workflow.id, "nl_parser", {"text": workflow.request_text}, structured)
        _finish_step(db, step, "done", structured)
        db.commit()
    except Exception as e:
        _finish_step(db, step, "failed", {"error": str(e)})
        workflow.status = "failed"
        workflow.failure_reason = f"Parsing failed: {e}"
        db.commit()
        return

    # --- Step: plan_workflow ---
    order += 1
    step = _add_step(db, workflow.id, order, "plan_workflow")
    plan = planner.plan_workflow(structured)
    _finish_step(db, step, "done", {"plan": plan})

    # --- Branch: missing information ---
    if structured.get("missing_fields"):
        order += 1
        step = _add_step(db, workflow.id, order, "flag_missing_information")
        msg = f"Cannot proceed - missing required field(s): {', '.join(structured['missing_fields'])}."
        _finish_step(db, step, "failed", {"message": msg})
        workflow.status = "failed"
        workflow.failure_reason = msg
        workflow.final_report = json.dumps({
            "summary": msg,
            "extracted_params": structured,
            "status": "failed",
        })
        db.commit()
        return

    # --- Step: retrieve_supplier_quotes ---
    order += 1
    step = _add_step(db, workflow.id, order, "retrieve_supplier_quotes")
    try:
        quotes = supplier_tool.get_supplier_quotes(db, structured)
        _log_tool(db, workflow.id, "supplier_data_tool", structured, quotes)
        _finish_step(db, step, "done", {"quotes": quotes})
    except Exception as e:
        _finish_step(db, step, "failed", {"error": str(e)})
        _log_tool(db, workflow.id, "supplier_data_tool", structured, None, status="error", error=str(e))
        workflow.status = "failed"
        workflow.failure_reason = f"Supplier data tool failed: {e}"
        db.commit()
        return

    # --- Step: validate_quotes ---
    order += 1
    step = _add_step(db, workflow.id, order, "validate_quotes")
    quote_validation = validator.validate_quotes(quotes, structured)
    _finish_step(db, step, "done" if quote_validation["ok"] else "failed", quote_validation)
    if not quote_validation["ok"] and not quotes:
        workflow.status = "failed"
        workflow.failure_reason = "; ".join(quote_validation["errors"])
        db.commit()
        return

    # --- Step: filter_by_budget ---
    order += 1
    step = _add_step(db, workflow.id, order, "filter_by_budget")
    quotes = scoring.filter_by_budget(quotes, structured.get("budget"))
    within_budget = [q for q in quotes if q["within_budget"]]
    _finish_step(db, step, "done", {
        "budget": structured.get("budget"),
        "within_budget_count": len(within_budget),
        "flagged_over_budget": [q["supplier_name"] for q in quotes if not q["within_budget"]],
    })

    if not within_budget:
        workflow.status = "failed"
        workflow.failure_reason = "No supplier is within the stated budget."
        workflow.final_report = json.dumps({
            "summary": "All supplier quotes exceeded the budget. No purchase order was generated.",
            "quotes": quotes,
            "status": "failed",
        })
        for q in quotes:
            db.add(_quote_row(workflow.id, q))
        db.commit()
        return

    # --- Step: score_and_rank_suppliers ---
    order += 1
    step = _add_step(db, workflow.id, order, "score_and_rank_suppliers")
    ranked = scoring.score_and_rank(quotes)
    _finish_step(db, step, "done", {"ranked": ranked})
    for q in ranked:
        db.add(_quote_row(workflow.id, q))
    db.commit()

    # --- Step: select_best_supplier ---
    order += 1
    step = _add_step(db, workflow.id, order, "select_best_supplier")
    valid_ranked = [q for q in ranked if q.get("within_budget")]
    best = valid_ranked[0]
    runner_up = valid_ranked[1] if len(valid_ranked) > 1 else None
    explanation = scoring.explain_selection(best, runner_up)
    _finish_step(db, step, "done", {"selected": best["supplier_name"], "explanation": explanation})

    # --- Step: generate_purchase_order ---
    order += 1
    step = _add_step(db, workflow.id, order, "generate_purchase_order")
    po_dict = po_generator.build_po_dict(workflow.id, structured, best)
    try:
        file_path = po_generator.generate_po_document(po_dict)
        _log_tool(db, workflow.id, "po_generator", po_dict, {"file_path": file_path})
        _finish_step(db, step, "done", {"po": po_dict, "file_path": file_path})
    except Exception as e:
        _finish_step(db, step, "failed", {"error": str(e)})
        _log_tool(db, workflow.id, "po_generator", po_dict, None, status="error", error=str(e))
        workflow.status = "failed"
        workflow.failure_reason = f"PO generation failed: {e}"
        db.commit()
        return

    # --- Step: validate_purchase_order ---
    order += 1
    step = _add_step(db, workflow.id, order, "validate_purchase_order")
    po_validation = validator.validate_purchase_order(po_dict, structured)
    _finish_step(db, step, "done" if po_validation["ok"] else "failed", po_validation)
    if not po_validation["ok"]:
        workflow.status = "failed"
        workflow.failure_reason = "PO validation failed: " + "; ".join(po_validation["errors"])
        db.commit()
        return

    po_row = PurchaseOrder(
        workflow_id=workflow.id,
        supplier_id=po_dict["supplier_id"],
        item=po_dict["item"],
        quantity=po_dict["quantity"],
        unit_price=po_dict["unit_price"],
        subtotal=po_dict["subtotal"],
        total=po_dict["total"],
        currency=po_dict["currency"],
        terms=po_dict["terms"],
        file_path=file_path,
        validated=True,
        validation_notes="All checks passed.",
    )
    db.add(po_row)
    db.commit()
    db.refresh(po_row)

    # --- Step: submit_for_approval ---
    order += 1
    step = _add_step(db, workflow.id, order, "submit_for_approval")
    approval = Approval(workflow_id=workflow.id, purchase_order_id=po_row.id, status="pending")
    db.add(approval)
    _log_tool(db, workflow.id, "approval_queue_tool",
              {"po_id": po_row.id}, {"status": "pending_approval"})
    _finish_step(db, step, "done", {"approval_status": "pending"})

    # --- Step: await_human_decision ---
    order += 1
    step = _add_step(db, workflow.id, order, "await_human_decision")
    step.status = "pending"  # not started yet - waits for human action via API
    db.add(step)

    workflow.status = "awaiting_approval"
    workflow.final_report = json.dumps({
        "summary": explanation,
        "selected_supplier": best["supplier_name"],
        "runner_up": runner_up["supplier_name"] if runner_up else None,
        "quotes": ranked,
        "purchase_order": po_dict,
        "status": "awaiting_approval",
    })
    db.commit()


def _quote_row(workflow_id: int, q: dict) -> Quote:
    return Quote(
        workflow_id=workflow_id,
        supplier_id=q["supplier_id"],
        quantity=q["quantity"],
        unit_price=q["unit_price"],
        total_price=q["total_price"],
        lead_time_days=q["lead_time_days"],
        warranty_years=q["warranty_years"],
        within_budget=q["within_budget"],
        score=q.get("score"),
        rank=q.get("rank"),
        score_breakdown_json=json.dumps(q.get("score_breakdown")) if q.get("score_breakdown") else None,
    )


def finalize_after_approval(db: Session, workflow: Workflow, approval: Approval):
    """Called after a human approves/rejects. Updates the final await_human_decision
    step and the workflow's final report - the last leg of the state machine."""
    step = (
        db.query(WorkflowStep)
        .filter(WorkflowStep.workflow_id == workflow.id, WorkflowStep.step_name == "await_human_decision")
        .first()
    )
    if step:
        step.status = "done"
        step.finished_at = dt.datetime.utcnow()
        step.output_json = json.dumps({"decision": approval.status, "approver": approval.approver})
        db.add(step)

    report = json.loads(workflow.final_report) if workflow.final_report else {}
    report["approval_decision"] = approval.status
    report["approver"] = approval.approver
    report["comment"] = approval.comment
    report["status"] = "approved" if approval.status == "approved" else "rejected"

    workflow.status = report["status"]
    workflow.final_report = json.dumps(report)
    db.commit()
