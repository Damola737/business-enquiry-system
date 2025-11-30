"""
Minimal FastAPI server exposing the customer support flows over HTTP.

Endpoints
- GET  /healthz                  → basic health check
- POST /process                  → run the end-to-end pipeline
- POST /kb/reload                → reload KB and rebuild index
- GET  /kb/search?q=...&domain=  → search KB docs

Run:
  uvicorn api.server:app --reload --port 8000

Requirements:
  pip install fastapi uvicorn pydantic
"""

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
import os
from pydantic import BaseModel

# Local imports
from mvp_pipeline import SimpleCustomerServicePipeline
from agents.research_agent import ResearchAgent


app = FastAPI(title="Customer Support Agent API", version="0.1.0")


# Lazily instantiate pipeline and research agent (shared for all requests)
_pipeline: Optional[SimpleCustomerServicePipeline] = None
_research: Optional[ResearchAgent] = None


def get_pipeline() -> SimpleCustomerServicePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = SimpleCustomerServicePipeline()
    return _pipeline


def get_research() -> ResearchAgent:
    global _research
    if _research is None:
        _research = ResearchAgent({}, knowledge_base_path="./knowledge_base")
    return _research


class ProcessRequest(BaseModel):
    message: str
    phone: str
    name: Optional[str] = None
    tenant_id: Optional[str] = None


class ProcessResponse(BaseModel):
    status: str
    enquiry_id: str
    agents_involved: List[str]
    processing_time_ms: int
    classification: Dict[str, Any]
    final_response: str
    escalation_summary: Optional[Dict[str, Any]] = None


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/")
async def root_ui():
    """Serve a minimal HTML UI for interacting with the agent."""
    ui_path = os.path.join(os.path.dirname(__file__), "ui.html")
    try:
        with open(ui_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except Exception:
        return HTMLResponse("<h1>Agent API</h1><p>Open <a href='/docs'>/docs</a> or POST to /process.</p>")

@app.get("/favicon.ico")
async def favicon():
    return PlainTextResponse("", status_code=204)


@app.post("/process", response_model=ProcessResponse)
async def process(req: ProcessRequest, request: Request):
    if not req.message or not req.phone:
        raise HTTPException(status_code=400, detail="'message' and 'phone' are required")

    # Resolve tenant_id from header, body, or default
    header_tenant = request.headers.get("X-Tenant-ID")
    tenant_id = req.tenant_id or header_tenant or "legacy-ng-telecom"

    pipeline = get_pipeline()
    result = pipeline.process(
        customer_message=req.message,
        customer_phone=req.phone,
        customer_name=req.name,
        tenant_id=tenant_id,
    )
    return {
        "status": result.get("status"),
        "enquiry_id": result.get("enquiry_id"),
        "agents_involved": result.get("agents_involved", []),
        "processing_time_ms": result.get("processing_time_ms", 0),
        "classification": result.get("classification", {}),
        "final_response": result.get("final_response", ""),
        "escalation_summary": result.get("escalation_summary"),
    }


class KBReloadResponse(BaseModel):
    documents: int
    terms: int
    kb_path: str
    timestamp: str


@app.post("/kb/reload", response_model=KBReloadResponse)
async def kb_reload():
    research = get_research()
    stats = research.reload_index()
    return stats


class KBSearchResponseItem(BaseModel):
    doc_id: str
    relevance_score: int
    title: str
    content: str
    category: str
    tags: List[str] = []


@app.get("/kb/search", response_model=List[KBSearchResponseItem])
async def kb_search(q: str, domain: Optional[str] = None, limit: int = 5):
    if not q:
        raise HTTPException(status_code=400, detail="Query 'q' is required")
    research = get_research()
    return research.search(q, limit=limit, domain=domain)
