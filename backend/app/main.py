from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import workflows, suppliers, approvals, purchase_orders
from app.scripts.load_data import run as seed_suppliers

app = FastAPI(
    title="Agentic Procurement Workflow API",
    description="HackHorizon Problem Statement 2 prototype - "
                 "Agentic AI for Autonomous Business Workflow Execution",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a local hackathon demo; restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workflows.router)
app.include_router(suppliers.router)
app.include_router(approvals.router)
app.include_router(purchase_orders.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_suppliers()


@app.get("/")
def root():
    return {
        "service": "agentic-procurement-workflow",
        "status": "ok",
        "docs": "/docs",
    }
