"""
Stage 2: turn the structured request into an explicit ordered plan.
Deterministic (not LLM) - the plan shape depends only on workflow_type and
whether required fields are present, so it's reproducible and inspectable.
"""

BASE_PLAN = [
    "parse_request",
    "plan_workflow",
    "retrieve_supplier_quotes",
    "validate_quotes",
    "filter_by_budget",
    "score_and_rank_suppliers",
    "select_best_supplier",
    "generate_purchase_order",
    "validate_purchase_order",
    "submit_for_approval",
    "await_human_decision",
    "finalize_report",
]

CLARIFICATION_PLAN = [
    "parse_request",
    "plan_workflow",
    "flag_missing_information",
    "finalize_report",
]


def plan_workflow(structured: dict) -> list:
    if structured.get("missing_fields"):
        return list(CLARIFICATION_PLAN)
    return list(BASE_PLAN)
