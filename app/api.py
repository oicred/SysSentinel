"""
SysSentinel API
================
FastAPI web endpoint that exposes the multi-agent pipeline over HTTP.

Endpoints:
  GET  /          → health check + system info
  POST /resolve   → run the incident resolution pipeline
  GET  /resolve/examples → pre-built example alerts for demo

Deploy locally:
  uvicorn app.api:app --reload --port 8080

Deploy to Cloud Run:
  gcloud run deploy syssentinel --source . --region us-central1 --allow-unauthenticated
"""

import json
import sys
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Allow running from repo root OR from app/ directory
sys.path.insert(0, os.path.dirname(__file__))

from agents import (
    create_agent,
    check_disk_space,
    check_db_connections,
    get_process_list,
    search_incident_knowledge_base,
    get_run_mode,
    is_elastic_active,
)

# ─── App Setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SysSentinel",
    description=(
        "B2B IT Incident Resolution Orchestrator — "
        "Multi-agent system powered by Google ADK + Gemini 2.5 Flash. "
        "Built for the Google Cloud Rapid Agent Hackathon (Track 1: Build)."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ─── Request / Response Models ──────────────────────────────────────────────────

class ResolveRequest(BaseModel):
    alert: str
    context: Optional[str] = None  # Optional extra context (e.g. environment name)

    class Config:
        json_schema_extra = {
            "examples": [
                {"alert": "Database connection pool timeout in prod-db-01"},
                {"alert": "Disk space critical on prod-web-02", "context": "production"},
            ]
        }


class TriageResult(BaseModel):
    category: str
    severity: str
    target_server: str
    triage_summary: str


class RAGResult(BaseModel):
    source: str
    historical_matches: list


class DiagnosticResult(BaseModel):
    server: str
    diagnostic_summary: str
    top_processes: list
    action_plan: str
    recommended_patch_script: str


class ResolveResponse(BaseModel):
    alert: str
    run_mode: str
    elastic_mcp_active: bool
    triage: TriageResult
    knowledge_base: RAGResult
    diagnostics: DiagnosticResult
    resolution_time_ms: float


# ─── Helper: Run the pipeline ──────────────────────────────────────────────────

def _parse_json_or_wrap(raw: str, fallback_key: str = "response") -> dict:
    """Parse JSON from agent output, or wrap plain text in a dict."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {fallback_key: str(raw)}


def run_pipeline(alert: str, context: Optional[str] = None) -> dict:
    import time
    t0 = time.time()

    full_alert = f"{alert} [{context}]" if context else alert

    # ── Step 1: Triage ─────────────────────────────────────────────────────────
    triage_agent = create_agent(
        "triage_agent",
        (
            "You are an expert IT Support Triage Engineer. Analyze the incoming alert and respond "
            "with a JSON object containing exactly these keys: "
            "alert (string), category (string: Database|Compute|Infrastructure|Network|Security), "
            "severity (string: LOW|MEDIUM|HIGH|CRITICAL), target_server (string), "
            "triage_summary (string). "
            "Do not include any text outside the JSON object."
        )
    )
    triage_raw  = triage_agent.run(full_alert)
    triage_data = _parse_json_or_wrap(triage_raw, "triage_summary")
    triage_data.setdefault("alert", alert)
    triage_data.setdefault("category", "Infrastructure")
    triage_data.setdefault("severity", "HIGH")
    triage_data.setdefault("target_server", "unknown-server")
    triage_data.setdefault("triage_summary", triage_raw)

    # ── Step 2: RAG / Knowledge Base ───────────────────────────────────────────
    rag_agent = create_agent(
        "rag_agent",
        (
            "You are a Knowledge Base Assistant with access to historical IT incident tickets. "
            "Search for incidents similar to the query using the search_incident_knowledge_base tool. "
            "Return the JSON response from that tool directly."
        ),
        tools=[search_incident_knowledge_base]
    )
    rag_query  = f"{triage_data['category']} — {alert}"
    rag_raw    = rag_agent.run(rag_query)
    rag_data   = _parse_json_or_wrap(rag_raw, "response")
    rag_data.setdefault("source", get_run_mode())
    rag_data.setdefault("historical_matches", [])

    # ── Step 3: Diagnostics & Patch ────────────────────────────────────────────
    diag_agent = create_agent(
        "diagnostic_agent",
        (
            "You are a Senior Site Reliability Engineer. Use the diagnostic tools to inspect "
            "the target server. Then produce a JSON object with these keys: "
            "server (string), diagnostic_summary (string), top_processes (list), "
            "action_plan (string with numbered steps), recommended_patch_script (string with shell commands). "
            "Base your resolution on the historical ticket context provided. "
            "Do not include any text outside the JSON object."
        ),
        tools=[check_disk_space, check_db_connections, get_process_list]
    )
    server = triage_data.get("target_server", "prod-web-02")
    history_summary = json.dumps(rag_data.get("historical_matches", [])[:2])
    diag_prompt = (
        f"Server: {server}. Alert: {full_alert}. "
        f"Historical resolutions: {history_summary}"
    )
    diag_raw  = diag_agent.run(diag_prompt)
    diag_data = _parse_json_or_wrap(diag_raw, "action_plan")
    diag_data.setdefault("server", server)
    diag_data.setdefault("diagnostic_summary", "Diagnostics completed.")
    diag_data.setdefault("top_processes", [])
    diag_data.setdefault("action_plan", diag_raw)
    diag_data.setdefault("recommended_patch_script", "# Review server manually")

    elapsed_ms = round((time.time() - t0) * 1000, 1)

    return {
        "alert": alert,
        "run_mode": get_run_mode(),
        "elastic_mcp_active": is_elastic_active(),
        "triage": triage_data,
        "knowledge_base": rag_data,
        "diagnostics": diag_data,
        "resolution_time_ms": elapsed_ms,
    }


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["System"])
def health_check():
    """Health check endpoint. Returns system status and run mode."""
    return {
        "service": "SysSentinel",
        "version": "2.0.0",
        "status": "operational",
        "run_mode": get_run_mode(),
        "elastic_mcp_active": is_elastic_active(),
        "hackathon": "Google Cloud Rapid Agent Hackathon — Track 1: Build",
        "partner_track": "Elastic",
        "endpoints": {
            "resolve":  "POST /resolve",
            "examples": "GET  /resolve/examples",
            "docs":     "GET  /docs",
        }
    }


@app.post("/resolve", response_model=ResolveResponse, tags=["Agents"])
def resolve_incident(request: ResolveRequest):
    """
    Run the full multi-agent incident resolution pipeline.

    Pipeline:
      1. Triage Agent    — classifies severity, category, and target server
      2. RAG Agent       — searches Elastic knowledge base for similar past incidents
      3. Diagnostic Agent — runs server diagnostics and generates a patch script

    Returns a structured incident report with action plan and ready-to-run patch.
    """
    if not request.alert or not request.alert.strip():
        raise HTTPException(status_code=422, detail="alert field must not be empty")

    try:
        result = run_pipeline(request.alert.strip(), request.context)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")


@app.get("/resolve/examples", tags=["Agents"])
def list_examples():
    """Return pre-built example alerts you can POST to /resolve for a demo."""
    return {
        "examples": [
            {
                "description": "Database connection pool exhaustion (CRITICAL)",
                "payload": {"alert": "Database connection pool timeout in prod-db-01"}
            },
            {
                "description": "Web server disk space exhaustion (HIGH)",
                "payload": {"alert": "Disk space is critical on server prod-web-02",
                            "context": "production"}
            },
            {
                "description": "API gateway high CPU (HIGH)",
                "payload": {"alert": "CPU usage exceeds 90% on api-gateway-01",
                            "context": "production"}
            },
        ]
    }


# ─── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
