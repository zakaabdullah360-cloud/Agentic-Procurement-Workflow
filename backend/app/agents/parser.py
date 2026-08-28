"""
Stage 1: Natural language -> structured request.

Rule-based extraction is the default and default-on path (works fully
offline, deterministic, always demoable). If ANTHROPIC_API_KEY is set,
`parse_with_llm` is tried first and the rule-based parser is used as a
fallback if the call fails or returns incomplete data - the pipeline never
depends on network access to run.
"""
import json
import re
from typing import Optional

from app.config import USE_LLM_PARSER, ANTHROPIC_API_KEY

NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


def _extract_quantity(text: str) -> Optional[int]:
    m = re.search(r"\b(\d{1,5})\s*(laptops?|units?|pcs|pieces?)\b", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d{1,5})\b", text)
    return int(m.group(1)) if m else None


def _extract_budget(text: str):
    """Returns (amount, currency) tuple, amount may be None."""
    t = text.lower()

    currency = "PKR"
    if "$" in text or "usd" in t:
        currency = "USD"
    elif "pkr" in t or "rs" in t or "rupees" in t:
        currency = "PKR"

    # "10 million", "PKR 10,000,000", "$20,000", "20k"
    m = re.search(r"(?:pkr|rs\.?|\$)?\s*([\d,]+(?:\.\d+)?)\s*million", t)
    if m:
        return float(m.group(1).replace(",", "")) * 1_000_000, currency

    m = re.search(r"(?:pkr|rs\.?|\$)?\s*([\d,]+(?:\.\d+)?)\s*k\b", t)
    if m:
        return float(m.group(1).replace(",", "")) * 1_000, currency

    m = re.search(r"(?:under|within|below|budget of)\s*(?:pkr|rs\.?|\$)?\s*([\d,]{4,})", t)
    if m:
        return float(m.group(1).replace(",", "")), currency

    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", text)
    if m:
        return float(m.group(1).replace(",", "")), "USD"

    return None, currency


def _extract_num_suppliers(text: str) -> int:
    m = re.search(r"compare\s+(\d+|\w+)\s+(?:suppliers|options|vendors|alternatives)", text, re.IGNORECASE)
    if m:
        token = m.group(1).lower()
        if token.isdigit():
            return int(token)
        return NUMBER_WORDS.get(token, 3)
    return 3


def _detect_workflow_type(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["vendor", "contract", "renewal", "subscription", "software"]):
        return "vendor_renewal"
    return "procurement"


def _detect_item(text: str, workflow_type: str) -> str:
    if workflow_type == "vendor_renewal":
        return "software vendor contract renewal"
    m = re.search(r"\b(\d+\s+)?([a-zA-Z][a-zA-Z\- ]{2,20}?)s?\b(?=\s+under|\s+within|\s*,|\s+for)", text)
    if "laptop" in text.lower():
        return "laptops"
    return "item"


def parse_rule_based(request_text: str) -> dict:
    workflow_type = _detect_workflow_type(request_text)
    budget, currency = _extract_budget(request_text)
    num_suppliers = _extract_num_suppliers(request_text)
    item = _detect_item(request_text, workflow_type)

    missing = []
    if workflow_type == "procurement":
        # only procurement has a meaningful item quantity; the generic digit
        # extractor would otherwise pick up "3" from "compare 3 options" on
        # vendor-renewal requests, which is a supplier count, not a quantity.
        quantity = _extract_quantity(request_text)
        if not quantity:
            missing.append("quantity")
        if not budget:
            missing.append("budget")
    else:
        quantity = 1  # one contract/subscription, not a unit count
        if not budget:
            missing.append("budget")

    return {
        "workflow_type": workflow_type,
        "item": item,
        "quantity": quantity,
        "budget": budget,
        "currency": currency,
        "num_suppliers": num_suppliers,
        "missing_fields": missing,
        "parser_used": "rule_based",
    }


def parse_with_llm(request_text: str) -> Optional[dict]:
    if not USE_LLM_PARSER:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        system = (
            "Extract structured procurement/vendor-renewal fields from a business "
            "request. Respond with ONLY a JSON object with keys: workflow_type "
            "('procurement' or 'vendor_renewal'), item (string), quantity (int or "
            "null), budget (number or null), currency (string), num_suppliers (int). "
            "No prose, no markdown fences."
        )
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=system,
            messages=[{"role": "user", "content": request_text}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        data = json.loads(text.strip().strip("`"))
        data["missing_fields"] = [
            k for k in ("quantity", "budget") if data.get(k) in (None, "")
        ]
        data["parser_used"] = "llm"
        return data
    except Exception:
        return None


def parse_request(request_text: str) -> dict:
    llm_result = parse_with_llm(request_text)
    if llm_result and not llm_result.get("missing_fields"):
        return llm_result
    return parse_rule_based(request_text)
