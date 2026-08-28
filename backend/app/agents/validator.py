"""
Independent validation checks, run twice: once over raw quotes (pre-PO),
once over the generated PO (pre-approval). Never silently continues on
failure - callers must inspect `ok` and act (retry/escalate).
"""


def validate_quotes(quotes: list, structured: dict) -> dict:
    errors = []
    if not quotes:
        errors.append("No supplier quotes were returned - supplier data tool "
                       "may have failed or no suppliers exist for this category.")
    for q in quotes:
        if q["unit_price"] <= 0:
            errors.append(f"{q['supplier_name']}: non-positive unit price.")
        if q["total_price"] != round(q["unit_price"] * q["quantity"], 2):
            errors.append(f"{q['supplier_name']}: total does not match unit_price x quantity.")
    within_budget_count = sum(1 for q in quotes if q.get("within_budget"))
    if within_budget_count == 0:
        errors.append("No supplier is within the stated budget.")
    return {"ok": len(errors) == 0, "errors": errors, "within_budget_count": within_budget_count}


def validate_purchase_order(po: dict, structured: dict) -> dict:
    errors = []
    required = ["item", "quantity", "unit_price", "subtotal", "total", "currency", "supplier_name"]
    for field in required:
        if not po.get(field) and po.get(field) != 0:
            errors.append(f"Missing required PO field: {field}")

    if po.get("quantity") != structured.get("quantity"):
        errors.append("PO quantity does not match the originally requested quantity.")

    expected_subtotal = round(po.get("unit_price", 0) * po.get("quantity", 0), 2)
    if round(po.get("subtotal", 0), 2) != expected_subtotal:
        errors.append("PO subtotal does not equal unit_price x quantity.")

    if round(po.get("total", 0), 2) != round(po.get("subtotal", 0), 2):
        errors.append("PO total does not equal subtotal (no tax/fees modeled - should match exactly).")

    budget = structured.get("budget")
    if budget is not None and po.get("total", 0) > budget:
        errors.append("PO total exceeds the stated budget - should never reach approval in this state.")

    return {"ok": len(errors) == 0, "errors": errors}
