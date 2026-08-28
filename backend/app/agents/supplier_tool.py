"""
Tool 1: Supplier Data Tool.
Reads supplier catalog rows already seeded in the DB (from the 4 CSVs for
procurement, or the 3 mocked options for vendor renewal) and returns a
per-supplier quote for the requested quantity. Simulates realistic
per-supplier "API latency" (small random jitter) purely for the
observability/audit-log demo - all numbers used for decisions remain
deterministic.
"""
import random
from sqlalchemy.orm import Session

from app.models import Supplier


def get_supplier_quotes(db: Session, structured: dict) -> list:
    category = "software_vendor" if structured["workflow_type"] == "vendor_renewal" else "laptop_supplier"
    n = structured.get("num_suppliers") or 3
    suppliers = (
        db.query(Supplier)
        .filter(Supplier.category == category)
        .order_by(Supplier.id)
        .limit(n)
        .all()
    )

    quantity = structured.get("quantity") or 1
    results = []
    for s in suppliers:
        total = round(s.unit_price * quantity, 2)
        simulated_latency_ms = random.randint(80, 420)  # cosmetic only, logged for realism
        results.append({
            "supplier_id": s.id,
            "supplier_name": s.name,
            "quantity": quantity,
            "unit_price": s.unit_price,
            "total_price": total,
            "currency": s.currency,
            "lead_time_days": s.lead_time_days,
            "warranty_years": s.warranty_years,
            "rating": s.rating,
            "simulated_latency_ms": simulated_latency_ms,
        })
    return results
