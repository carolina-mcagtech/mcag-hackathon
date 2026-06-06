"""
api.py — FastAPI HTTP interface for FloridaInspect Agent.
Deployed on Railway via Procfile / railway.json.

Endpoints:
    GET  /health       — liveness probe
    GET  /demo-result  — return cached AI demo report instantly (no pipeline run)
    POST /demo         — run the built-in 7-finding demo scenario
    POST /inspect      — run Analyze + Report agents on caller-supplied findings
"""

from __future__ import annotations

import base64
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from demo.run_demo import INSPECTION_DATE, MOCK_FINDINGS, PROPERTY_ADDRESS
from tools.classify_photo import FindingDraft, classify_photo_from_bytes
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


_DEMO_RESULT_PATH = Path(__file__).parent / "demo_report_output.json"


# ── GET /health ───────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "InspectIQ Agent"}


# ── GET /demo-result ──────────────────────────────────────────────────────────

@app.get("/demo-result")
def demo_result() -> dict[str, Any]:
    """Return the pre-generated AI demo report from disk without running the pipeline.

    Reads demo_report_output.json committed to the repo, so judges get real
    Gemini-generated output instantly instead of waiting ~3 minutes for the
    full pipeline to run.
    """
    if not _DEMO_RESULT_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Demo result not found. Run POST /demo first to generate it.",
        )
    return json.loads(_DEMO_RESULT_PATH.read_text(encoding="utf-8"))


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

class FlexFinding(BaseModel):
    """Flexible finding input — only severity is truly required.

    Accepts both the canonical FindingDraft field names and common shorthand
    alternatives so callers don't need to know the internal schema.

    Minimal example::

        {
          "system": "electrical",
          "observation": "Possible FPE Stab-Lok panel observed",
          "severity": "critical"
        }

    Full example (matches internal FindingDraft exactly)::

        {
          "system": "electrical",
          "location": "Main electrical panel — garage",
          "observation": "Federal Pacific Stab-Lok panel, 150-amp service.",
          "severity": "critical",
          "deficiency_suspected": true,
          "photo_description": "Federal Pacific electrical panel with double-tapped breakers.",
          "confidence": 0.97
        }

    Field aliases accepted:
        component  → system
        description → observation
    """

    # canonical fields
    system: Optional[str] = Field(default=None, description="roof | electrical | plumbing | hvac | structure | other")
    location: str = Field(default="Not specified", description="Where in the property this was observed")
    observation: Optional[str] = Field(default=None, description="Plain-language description of what was observed")
    severity: str = Field(default="major", description="critical | major | minor | informational")
    deficiency_suspected: bool = Field(default=True)
    photo_description: Optional[str] = Field(default=None)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)

    # shorthand aliases
    component: Optional[str] = Field(default=None, description="Alias for 'system'")
    description: Optional[str] = Field(default=None, description="Alias for 'observation'")

    def to_finding_draft(self) -> FindingDraft:
        system = self.system or self.component or "other"
        observation = self.observation or self.description or "No observation provided"
        return FindingDraft(
            system=system,
            location=self.location,
            observation=observation,
            severity=self.severity,
            deficiency_suspected=self.deficiency_suspected,
            photo_description=self.photo_description or observation[:80],
            confidence=self.confidence,
        )


class InspectRequest(BaseModel):
    findings: list[FlexFinding] = Field(description="One or more inspection findings")
    inspection_type: str = Field(default="4-point", description="4-point | wind-mit | full")
    property_address: Optional[str] = Field(default="Address not provided")
    inspection_date: Optional[str] = Field(default=None, description="ISO-8601 date, defaults to today")


@app.post("/inspect")
def inspect(body: InspectRequest) -> dict[str, Any]:
    """Run Analyze + Report agents on caller-supplied findings.

    Minimal call::

        curl -X POST /inspect -H "Content-Type: application/json" -d '{
          "findings": [
            {"system": "electrical", "observation": "Possible FPE Stab-Lok panel", "severity": "critical"},
            {"component": "roof",    "description": "Missing shingles on north slope", "severity": "major"}
          ],
          "inspection_type": "4-point"
        }'
    """
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")

    if not body.findings:
        raise HTTPException(status_code=422, detail="findings list must not be empty")

    finding_objects = [f.to_finding_draft() for f in body.findings]

    return _run_pipeline(
        findings=finding_objects,
        property_address=body.property_address or "Address not provided",
        inspection_date=body.inspection_date or datetime.date.today().isoformat(),
        inspection_type=body.inspection_type,
    )


# ── shared photo request models ───────────────────────────────────────────────

class PhotoBase64Request(BaseModel):
    image_base64: str = Field(description="Base64-encoded image bytes (JPEG, PNG, or WEBP)")
    inspection_type: str = Field(default="4-point", description="4-point | wind-mit | full")
    mime_type: str = Field(default="image/jpeg", description="MIME type of the image")
    location_hint: Optional[str] = Field(default=None, description="Location context, e.g. 'attic'")
    system_hint: Optional[str] = Field(default=None, description="System context, e.g. 'electrical'")
    property_address: Optional[str] = Field(default="Address not provided")
    inspection_date: Optional[str] = Field(default=None, description="ISO-8601 date, defaults to today")


class PhotoUrlRequest(BaseModel):
    image_url: str = Field(description="Publicly accessible URL of the inspection photo")
    inspection_type: str = Field(default="4-point", description="4-point | wind-mit | full")
    location_hint: Optional[str] = Field(default=None)
    system_hint: Optional[str] = Field(default=None)
    property_address: Optional[str] = Field(default="Address not provided")
    inspection_date: Optional[str] = Field(default=None)


def _decode_base64_image(image_base64: str) -> bytes:
    """Decode a base64 string to bytes, stripping data-URI prefix if present."""
    data = image_base64
    if "," in data:
        data = data.split(",", 1)[1]
    try:
        return base64.b64decode(data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid base64 image data: {exc}") from exc


def _download_image(url: str) -> tuple[bytes, str]:
    """Download an image from a URL and return (bytes, mime_type)."""
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to download image (HTTP {exc.response.status_code}): {url}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to download image: {exc}") from exc

    content_type = resp.headers.get("content-type", "image/jpeg").split(";")[0].strip()
    return resp.content, content_type


# ── POST /capture ─────────────────────────────────────────────────────────────

@app.post("/capture")
def capture(body: PhotoBase64Request) -> dict[str, Any]:
    """Classify a single inspection photo using Gemini Vision.

    Accepts a base64-encoded image and returns a structured FindingDraft
    describing the observed condition, severity, and confidence.

    Example::

        curl -X POST /capture -H "Content-Type: application/json" -d '{
          "image_base64": "<base64-string>",
          "inspection_type": "4-point",
          "location_hint": "main electrical panel"
        }'
    """
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")

    image_bytes = _decode_base64_image(body.image_base64)

    try:
        finding = classify_photo_from_bytes(
            image_bytes=image_bytes,
            mime_type=body.mime_type,
            system_hint=body.system_hint,
            location_hint=body.location_hint,
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        status = 429 if "rate limit" in str(exc).lower() else 502
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return finding.model_dump()


# ── POST /capture-url ─────────────────────────────────────────────────────────

@app.post("/capture-url")
def capture_url(body: PhotoUrlRequest) -> dict[str, Any]:
    """Classify an inspection photo supplied as a URL using Gemini Vision.

    Downloads the image then runs the same Capture Agent logic as POST /capture.
    Useful for quick testing without base64 encoding.

    Example::

        curl -X POST /capture-url -H "Content-Type: application/json" -d '{
          "image_url": "https://example.com/roof.jpg",
          "inspection_type": "4-point"
        }'
    """
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")

    image_bytes, mime_type = _download_image(body.image_url)

    try:
        finding = classify_photo_from_bytes(
            image_bytes=image_bytes,
            mime_type=mime_type,
            system_hint=body.system_hint,
            location_hint=body.location_hint,
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        status = 429 if "rate limit" in str(exc).lower() else 502
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return finding.model_dump()


# ── POST /pipeline ────────────────────────────────────────────────────────────

@app.post("/pipeline")
def pipeline(body: PhotoBase64Request) -> dict[str, Any]:
    """Run the full Capture → Analyze → Report pipeline on a single photo.

    1. Capture Agent: classifies the photo with Gemini Vision → FindingDraft
    2. Analyze Agent: validates the finding against FL regulations → RegulatoryCheck
    3. Report Agent: generates a professional narrative → FullReport

    Returns the complete FullReport JSON.

    Example::

        curl -X POST /pipeline -H "Content-Type: application/json" -d '{
          "image_base64": "<base64-string>",
          "inspection_type": "4-point",
          "property_address": "123 Main St, Tampa, FL 33601"
        }'
    """
    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")

    image_bytes = _decode_base64_image(body.image_base64)

    try:
        finding = classify_photo_from_bytes(
            image_bytes=image_bytes,
            mime_type=body.mime_type,
            system_hint=body.system_hint,
            location_hint=body.location_hint,
        )
    except EnvironmentError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except RuntimeError as exc:
        status = 429 if "rate limit" in str(exc).lower() else 502
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return _run_pipeline(
        findings=[finding],
        property_address=body.property_address or "Address not provided",
        inspection_date=body.inspection_date or datetime.date.today().isoformat(),
        inspection_type=body.inspection_type,
    )
