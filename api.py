"""
api.py — FastAPI HTTP interface for FloridaInspect Agent.
Deployed on Railway via Procfile / railway.json.

Endpoints:
    GET  /health   — liveness probe
    POST /demo     — run the built-in 7-finding demo scenario
    POST /inspect  — run Analyze + Report agents on caller-supplied findings
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from demo.run_demo import INSPECTION_DATE, MOCK_FINDINGS, PROPERTY_ADDRESS
from tools.classify_photo import FindingDraft
from tools.generate_narrative import assemble_full_report, generate_narrative
from tools.validate_regulation import validate_regulation

app = FastAPI(
    title="InspectIQ Agent",
    version="1.0.0",
    description="AI-powered Florida home inspection report generation",
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _run_pipeline(
    findings: list[FindingDraft],
    property_address: str,
    inspection_date: str,
    inspection_type: str = "4-point",
) -> dict[str, Any]:
    """Validate → narrate → assemble. Returns a serialisable report dict."""
    checks = [validate_regulation(f) for f in findings]
    sections = [generate_narrative(f, c) for f, c in zip(findings, checks)]
    report = assemble_full_report(
        sections=sections,
        property_address=property_address,
        inspection_date=inspection_date,
        inspector_license=(
            f"AI-ASSISTED REVIEW ({inspection_type.upper()}) "
            "— Requires licensed inspector sign-off"
        ),
    )
    return {"inspection_type": inspection_type, **report.model_dump()}


# ── GET /health ───────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "InspectIQ Agent"}


# ── POST /demo ────────────────────────────────────────────────────────────────

@app.post("/demo")
def demo() -> dict[str, Any]:
    """Run the built-in 7-finding Tampa demo scenario and return the full report."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")

    findings = [FindingDraft.model_validate(f) for f in MOCK_FINDINGS]
    return _run_pipeline(
        findings=findings,
        property_address=PROPERTY_ADDRESS,
        inspection_date=INSPECTION_DATE,
        inspection_type="4-point",
    )


# ── POST /inspect ─────────────────────────────────────────────────────────────

class InspectRequest(BaseModel):
    findings: list[dict[str, Any]] = Field(
        description="List of finding objects (FindingDraft schema)"
    )
    inspection_type: str = Field(
        default="4-point",
        description="Inspection type: 4-point | wind-mit | full",
    )
    property_address: Optional[str] = Field(
        default="Address not provided",
        description="Street address of the inspected property",
    )
    inspection_date: Optional[str] = Field(
        default=None,
        description="Inspection date ISO-8601 (defaults to today)",
    )


@app.post("/inspect")
def inspect(body: InspectRequest) -> dict[str, Any]:
    """Run Analyze + Report agents on caller-supplied findings."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")

    if not body.findings:
        raise HTTPException(status_code=422, detail="findings list must not be empty")

    try:
        finding_objects = [FindingDraft.model_validate(f) for f in body.findings]
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid finding data: {exc}") from exc

    return _run_pipeline(
        findings=finding_objects,
        property_address=body.property_address or "Address not provided",
        inspection_date=body.inspection_date or datetime.date.today().isoformat(),
        inspection_type=body.inspection_type,
    )
