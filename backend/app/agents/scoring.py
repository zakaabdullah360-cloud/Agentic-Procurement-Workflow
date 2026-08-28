"""
Stages: filter_by_budget + score_and_rank_suppliers.
All arithmetic here is plain Python - no LLM involved, so results are
reproducible and auditable, per the hackathon's explainability requirement.
"""
from app.config import SCORE_WEIGHTS


def filter_by_budget(quotes: list, budget: float) -> list:
    """Marks each quote within_budget True/False. Does not drop anything -
    the caller decides how to handle over-budget quotes (flag, not silently
    discard, per the validation-layer requirement)."""
    if budget is None:
        for q in quotes:
            q["within_budget"] = True
        return quotes
    for q in quotes:
        q["within_budget"] = q["total_price"] <= budget
    return quotes


def score_and_rank(quotes: list) -> list:
    """
    Weighted scoring over quotes that are within budget:
      price     50% (lower total price -> higher score)
      delivery  30% (shorter lead time -> higher score)
      warranty  20% (longer warranty/term -> higher score)
    Each criterion is min-max normalized across the *within-budget* quotes
    being compared, so the score is always relative and explainable.
    """
    valid = [q for q in quotes if q.get("within_budget")]
    if not valid:
        return quotes

    prices = [q["total_price"] for q in valid]
    leads = [q["lead_time_days"] for q in valid]
    warranties = [q["warranty_years"] for q in valid]

    p_min, p_max = min(prices), max(prices)
    l_min, l_max = min(leads), max(leads)
    w_min, w_max = min(warranties), max(warranties)

    def norm_inverse(value, lo, hi):
        # lower is better (price, lead time) -> higher normalized score
        if hi == lo:
            return 1.0
        return (hi - value) / (hi - lo)

    def norm_direct(value, lo, hi):
        # higher is better (warranty) -> higher normalized score
        if hi == lo:
            return 1.0
        return (value - lo) / (hi - lo)

    for q in valid:
        price_score = norm_inverse(q["total_price"], p_min, p_max)
        delivery_score = norm_inverse(q["lead_time_days"], l_min, l_max)
        warranty_score = norm_direct(q["warranty_years"], w_min, w_max)

        total_score = (
            price_score * SCORE_WEIGHTS["price"]
            + delivery_score * SCORE_WEIGHTS["delivery"]
            + warranty_score * SCORE_WEIGHTS["warranty"]
        )
        q["score"] = round(total_score, 4)
        q["score_breakdown"] = {
            "price_score": round(price_score, 4),
            "delivery_score": round(delivery_score, 4),
            "warranty_score": round(warranty_score, 4),
            "weights": SCORE_WEIGHTS,
        }

    valid.sort(key=lambda q: q["score"], reverse=True)
    for i, q in enumerate(valid, start=1):
        q["rank"] = i

    # keep invalid (over-budget) quotes in the returned list, unranked
    invalid = [q for q in quotes if not q.get("within_budget")]
    for q in invalid:
        q["score"] = None
        q["rank"] = None
    return valid + invalid


def explain_selection(best: dict, runner_up: dict = None) -> str:
    lines = [
        f"{best['supplier_name']} was selected with a score of {best['score']:.2f}/1.00.",
        f"Total cost: {best['total_price']:,.2f} {best['currency']} "
        f"(unit price {best['unit_price']:,.2f} x {best['quantity']}), "
        f"within the stated budget.",
        f"Delivery/lead time: {best['lead_time_days']} days.",
        f"Warranty/term: {best['warranty_years']} year(s).",
    ]
    if runner_up:
        lines.append(
            f"Next best option was {runner_up['supplier_name']} "
            f"(score {runner_up['score']:.2f}), edged out mainly on "
            f"{'price' if best['score_breakdown']['price_score'] > runner_up['score_breakdown']['price_score'] else 'delivery/warranty'}."
        )
    return " ".join(lines)
