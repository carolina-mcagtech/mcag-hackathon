# FloridaInspect Agent

AI-powered Florida home inspection system built with Google ADK and Gemini API.
Developed for the MCAG Technologies hackathon.

## Overview

FloridaInspect Agent is a multi-agent system that automates the analysis and
reporting stages of a Florida residential home inspection. It processes field
photos, validates findings against Florida regulations, and generates
professional inspection reports.

```
Inspector Photos → CaptureAgent → AnalyzeAgent → ReportAgent → Full Report
                  (Gemini Vision) (RAG + Rules)  (Gemini Pro)
```

### Pipeline

| Agent | Model | Responsibility |
|-------|-------|----------------|
| **CaptureAgent** | Gemini 1.5 Flash | Classifies inspection photos → `FindingDraft` |
| **AnalyzeAgent** | Gemini 1.5 Pro | RAG validation against FL Statute 468 → `RegulatoryCheck` |
| **ReportAgent** | Gemini 1.5 Pro | Generates professional report narrative → `FullReport` |

### Regulatory Coverage

- Florida Statute 468 Part XV — Home Inspector licensing and standards
- Citizens 4-Point Inspection (roof, electrical, plumbing, HVAC)
- Wind Mitigation OIR-B1-1802 criteria
- Florida Building Code (FBC) 8th Edition
- NEC 2020 (as adopted in Florida)

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- A [Gemini API key](https://aistudio.google.com/app/apikey)

### 2. Install

```bash
git clone <repo-url>
cd mcag-hackathon

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=<your-key>
```

### 4. Run the demo (no photos required)

```bash
python demo/run_demo.py
# or
python main.py --demo
```

### 5. Run a real inspection

```bash
python main.py \
  --photos roof.jpg panel.jpg bathroom.jpg hvac.jpg \
  --address "123 Main St, Tampa FL 33601" \
  --date 2024-06-15
```

### 6. Launch ADK Web UI (interactive)

```bash
python main.py --adk-web
# Open http://localhost:8000
```

---

## Project Structure

```
mcag-hackathon/
├── main.py                     # CLI entry point
├── orchestrator/
│   └── agent.py                # Root ADK agent — coordinates sub-agents
├── agents/
│   ├── capture_agent.py        # Gemini Vision photo classifier
│   ├── analyze_agent.py        # FL regulation validator (RAG)
│   └── report_agent.py         # Professional report generator
├── tools/
│   ├── classify_photo.py       # Gemini Vision → FindingDraft
│   ├── validate_regulation.py  # ChromaDB RAG → RegulatoryCheck
│   └── generate_narrative.py   # Gemini Pro → ReportSection / FullReport
├── data/
│   └── fl_regulations.txt      # FL Statute 468, 4-Point, Wind Mit. reference
└── demo/
    └── run_demo.py             # Demo with synthetic findings (no photos needed)
```

---

## Key Data Models

```python
# Output of CaptureAgent
FindingDraft(
    system="electrical",
    location="Main panel — garage",
    observation="Federal Pacific Stab-Lok panel identified...",
    severity="critical",          # critical | major | minor | informational
    deficiency_suspected=True,
    confidence=0.97,
)

# Output of AnalyzeAgent
RegulatoryCheck(
    applicable_regulations=["FL Statute 468.8319(b)", "Citizens 4-Point HO-800"],
    compliant=False,
    violation_description="High-risk panel — insurance non-eligible",
    recommended_action="Replace panel with a listed UL-approved panel.",
    insurance_impact="critical",  # critical | moderate | minor | none
)

# Output of ReportAgent
ReportSection(
    system="Electrical",
    headline="Critical safety hazard — Federal Pacific panel requires immediate replacement",
    narrative="...",              # 2-4 professional paragraphs
    action_items=["Replace panel...", "Have a licensed electrician..."],
    severity_summary="critical",  # critical | poor | fair | satisfactory
)
```

---

## Florida Regulatory Reference

The system's RAG knowledge base (`data/fl_regulations.txt`) covers:

- **FL Statute 468.8311–8326** — Definitions, licensing, inspection scope, report requirements
- **4-Point Inspection** — Roof, electrical, plumbing, HVAC criteria per Citizens HO-800
- **Wind Mitigation OIR-B1-1802** — Roof deck attachment, roof-to-wall connections, opening protection
- **FL-specific deficiencies** — Polybutylene pipe, Federal Pacific panels, Chinese drywall, sinkhole indicators

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GEMINI_API_KEY` | **Required.** Your Gemini API key from Google AI Studio |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID (required only for Vertex AI mode) |
| `GOOGLE_CLOUD_LOCATION` | GCP region (required only for Vertex AI mode) |
| `GOOGLE_GENAI_USE_VERTEXAI` | Set `TRUE` to use Vertex AI instead of Gemini API |

---

## License

MIT — MCAG Technologies, 2024
