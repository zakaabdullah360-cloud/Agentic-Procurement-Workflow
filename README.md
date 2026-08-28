# Agentic Procurement Workflow — HackHorizon Problem Statement 2

A working prototype of an agentic AI system that turns a plain-English business
request into a structured, multi-step workflow, executes it through real
tools (supplier data lookup, PO document generation, an approval queue),
validates every stage deterministically, and stops at a mandatory human
approval gate before anything is "spent."

Covers both required use cases with the **same orchestrator**:

1. **Procurement** — "Create a purchase request for 50 laptops under PKR 10
   million, compare three suppliers, identify the best option, prepare the
   purchase order, and send it for approval."
2. **Vendor renewal** — "Our software vendor contract is expiring. Compare 3
   renewal/alternative options and recommend one within a $20,000 budget."

## Why 4 supplier data sources, not 1

Your `laptops_Dataset.csv` (and the 3 additional CSVs you supplied) contain
laptop **models and prices only** — none of the 4 files has a supplier/vendor
column. So there's no way to pull "3 supplier quotes" out of a single file.
Instead, each CSV is treated as **one supplier's catalog**:

| Supplier (in the app) | Source file | Native currency | Notes |
|---|---|---|---|
| AlphaTech Distributors | `supplier_alpha_pk.csv` (your original `laptops_Dataset.csv`) | PKR | used as-is |
| BravoLaptops Wholesale | `supplier_bravo_eu.csv` | EUR | converted to PKR at a fixed, disclosed rate (`EUR_TO_PKR` in `app/config.py`) — this is a config constant, not hidden in the scoring math |
| CharlieLaptop Traders | `supplier_charlie_in.csv` | INR (₹ symbol) | treated as PKR-equivalent for the demo — a real deployment would need a live FX feed, called out here rather than silently assumed |
| DeltaTech Systems | `supplier_delta_clean.csv` | PKR-equivalent | the only file with a real `rating` column, carried through to the UI |

For each supplier, the "quote" for a request is: **median price of laptops
in the realistic business-laptop price band** (filters out ultra-budget and
flagship gaming outliers) × quantity requested. Delivery lead time is
simulated per supplier (disclosed, not hidden) since none of the datasets
contain delivery data. This is documented, not invented as fact — see
`app/scripts/load_data.py` docstrings for exactly what's derived vs. real.

The vendor-renewal use case has **no dataset at all** (out of scope of what
you uploaded), so its 3 options are explicitly mocked in the same file —
matching the hackathon PDF's own suggestion to use "a realistic mock ... if
no real vendor API is available."

## Architecture

```
Natural language request
        │
        ▼
 parser.py            — regex-based intent extraction (item, qty, budget,
                         currency, # suppliers to compare). Optional Claude
                         API call first if ANTHROPIC_API_KEY is set, with
                         automatic fallback to the rule-based parser.
        │
        ▼
 planner.py            — deterministic ordered step list (DAG), branches to
                         a short "missing information" plan if required
                         fields weren't extracted.
        │
        ▼
 orchestrator.py        — executes the plan step-by-step, persists workflow
                         state (workflow_steps table), calls tools below,
                         and STOPS at the approval gate. Nothing here uses
                         an LLM for money/quantity decisions.
        │
        ├─▶ supplier_tool.py   (Tool 1: reads seeded supplier catalog rows)
        ├─▶ scoring.py         (deterministic budget filter + weighted rank)
        ├─▶ validator.py       (independent pre-PO and pre-approval checks)
        ├─▶ po_generator.py    (Tool 2: writes a real .docx Purchase Order)
        └─▶ Approval row       (Tool 3: approval queue — see approvals.py)
        │
        ▼
 Human approval (REST call from the frontend's Approve/Reject buttons)
        │
        ▼
 finalize_after_approval() — updates workflow status + final report
```

Every tool call is written to `tool_logs` with input, output, status and
timestamp — visible via `GET /api/workflows/{id}/logs`.

## Project structure

```
backend/
  app/
    main.py              FastAPI app, seeds the DB on startup
    config.py             scoring weights, FX constant, LLM toggle
    database.py            SQLAlchemy engine/session
    models.py               full schema (workflows, workflow_steps, tool_logs,
                            suppliers, quotes, purchase_orders, approvals)
    schemas.py              Pydantic request/response models
    agents/
      parser.py             Stage 1 — NL to structured request
      planner.py             Stage 2 — plan/DAG
      supplier_tool.py       Tool 1 — supplier data
      scoring.py              budget filter + weighted ranking + explanation
      validator.py             quote validation + PO validation
      po_generator.py          Tool 2 — .docx PO generation
      orchestrator.py           the state machine that runs everything
    routers/
      workflows.py            POST/GET workflow endpoints
      suppliers.py              GET /api/suppliers
      purchase_orders.py         GET + /download
      approvals.py                Tool 3 — approve/reject endpoints
    scripts/load_data.py         seeds suppliers table from the 4 CSVs + mocks
    data/                          your 4 CSVs, renamed by supplier
  requirements.txt
  .env.example
frontend/
  src/
    App.jsx                    top-level page, wires everything together
    api.js                      axios client
    components/
      ChatInput.jsx              request box + one-click example queries
      WorkflowTrace.jsx           live step-by-step status
      SupplierComparison.jsx       scored/ranked comparison table
      POPreview.jsx                 PO details + docx download
      ApprovalQueue.jsx              Approve / Reject buttons
  package.json / vite.config.js
```

## Setup (VS Code)

### 1. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows;  source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env           # optional — only needed if you want the Claude parser
uvicorn app.main:app --reload --port 8000
```
On first startup this automatically creates `workflow.db` (SQLite) and seeds
the `suppliers` table from the 4 CSVs. Visit `http://localhost:8000/docs`
to confirm it's up and browse the auto-generated API docs.

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`. The Vite dev server proxies `/api` calls to
the backend on port 8000 (see `vite.config.js`), so run both at once in two
VS Code terminal panes.

### 3. Try it
Click one of the three example-query chips (primary use case, vendor
renewal, or the deliberately incomplete request that demonstrates the
failure/clarification path), or type your own, and click **Run agent**.

## API reference

| Endpoint | Purpose |
|---|---|
| `POST /api/workflows` | Submit a request; runs the full pipeline synchronously up to the approval gate |
| `GET /api/workflows` | List all workflows |
| `GET /api/workflows/{id}` | Full detail: params, steps, quotes, PO, approval, report |
| `GET /api/workflows/{id}/steps` | Just the step trace |
| `GET /api/workflows/{id}/logs` | Tool call audit log |
| `GET /api/suppliers` | All seeded suppliers/vendors |
| `GET /api/purchase-orders/{id}` | PO detail |
| `GET /api/purchase-orders/{id}/download` | Download the generated `.docx` |
| `POST /api/approvals/{id}/approve` | Human approval — unblocks the workflow |
| `POST /api/approvals/{id}/reject` | Human rejection — finalizes as rejected |

## Test scenarios this handles

- **Happy path** — primary use case, all 3 suppliers within budget, best one ranked and PO generated.
- **All suppliers over budget** — try a very low budget (e.g. "under PKR 100,000") to see every supplier flagged and the workflow fail with a clear reason, no PO generated.
- **Missing fields** — "Buy some laptops please" stops at `flag_missing_information` and names exactly what's missing, rather than guessing.
- **PO/budget consistency** — `validator.validate_purchase_order` independently recomputes subtotal/total and would block approval if they ever drifted from unit_price × quantity.
- **Human rejection** — reject instead of approve; workflow finalizes as `rejected` with its own report, no silent auto-completion either way.

## Demo script (5–7 min)

1. **Primary use case** — paste the reference query, hit Run. Narrate: parse → plan → 3 real tool calls (point at the trace + `/logs` endpoint) → transparent scoring table → PO with download link → **it stops here** and asks a human.
2. **Approve it** — click Approve, show the final report updating live.
3. **Generalizability** — paste the vendor-renewal query. Same orchestrator, same trace shape, different domain — point out `PremiumSuite` gets flagged as over-budget by the identical filter logic.
4. **Resilience** — paste "Buy some laptops please" to show it doesn't hallucinate a plan when required fields are missing.
5. **Auditability** — open `/docs` or hit `/api/workflows/{id}/logs` to show every tool call is logged with real inputs/outputs and timestamps, not just "it worked."

## Honest limitations (say these to judges, don't hide them)

- Currency normalization (EUR/INR → PKR) uses a fixed constant, not a live FX API — disclosed in `config.py`, swappable for a real feed.
- Delivery lead times are simulated per supplier (no dataset has this field) — disclosed, not fabricated as real data.
- The rule-based parser is tuned for the two demo use cases' phrasing; arbitrary free text may need the optional Claude API path (`ANTHROPIC_API_KEY` in `.env`) for robust extraction.
