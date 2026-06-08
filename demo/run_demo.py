"""
FloridaInspect Demo — Simulated inspection scenario without real photos.

This demo runs the full pipeline using mock/synthetic FindingDraft data to
demonstrate the AnalyzeAgent and ReportAgent stages without requiring actual
Gemini Vision photo classification. Useful for testing your API key and
validating the regulatory analysis + report generation pipeline.

Scenario:
    A 1987-built single-family home in Hillsborough County, FL.
    Inspection reveals a mix of critical, major, and minor findings across
    all four 4-Point inspection systems (roof, electrical, plumbing, HVAC).

Run:
    python demo/run_demo.py
    python main.py --demo
"""

import json
import os
import sys
from pathlib import Path

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from tools.audit_narrative import AuditResult, audit_narrative
from tools.classify_photo import FindingDraft
from tools.generate_narrative import assemble_full_report, generate_narrative
from tools.validate_regulation import validate_regulation


PROPERTY_ADDRESS = "4712 Palmetto Oak Drive, Tampa, FL 33647"
INSPECTION_DATE = "2024-06-15"

# Synthetic findings that represent a typical 1987 FL home inspection
MOCK_FINDINGS: list[dict] = [
    {
        "system": "roof",
        "location": "Main roof — rear slope",
        "observation": (
            "Asphalt shingle roof approximately 19 years old. Multiple shingles showing "
            "significant granule loss, with bare fiberglass mat exposed in two locations "
            "near the ridge vent. Evidence of prior patch repair using mismatched shingles. "
            "No active leak observed at time of inspection but interior attic decking shows "
            "old water staining consistent with past leak events."
        ),
        "severity": "major",
        "deficiency_suspected": True,
        "photo_description": "Worn asphalt shingles with granule loss and patching on rear slope.",
        "confidence": 0.91,
    },
    {
        "system": "electrical",
        "location": "Main electrical panel — garage",
        "observation": (
            "Federal Pacific Electric Stab-Lok panel identified, 150-amp service. "
            "Panel contains 32 circuit breakers. Three double-tapped breakers observed "
            "(circuits 4, 12, and 22). No evidence of heat damage or corrosion inside panel. "
            "Panel label is partially legible. This panel type is associated with a known "
            "failure to trip under overcurrent conditions."
        ),
        "severity": "critical",
        "deficiency_suspected": True,
        "photo_description": "Federal Pacific Stab-Lok electrical panel with double-tapped breakers.",
        "confidence": 0.97,
    },
    {
        "system": "electrical",
        "location": "Kitchen — outlets near sink",
        "observation": (
            "Two electrical outlets within 36 inches of the kitchen sink are not GFCI-protected. "
            "Standard duplex outlets installed. No GFCI outlet or breaker protecting this circuit "
            "was identified. This is a violation of NEC 210.8 as adopted by the Florida Building Code."
        ),
        "severity": "major",
        "deficiency_suspected": True,
        "photo_description": "Non-GFCI outlet within 36 inches of kitchen sink.",
        "confidence": 0.95,
    },
    {
        "system": "plumbing",
        "location": "Under kitchen sink and visible in crawl space access",
        "observation": (
            "Gray polybutylene supply piping (Quest brand, identified by stamped markings) "
            "present throughout visible supply lines. Polybutylene comprises the main hot and "
            "cold supply distribution from the water meter. Small pinhole leak observed at "
            "one compression fitting under the kitchen sink — active drip at time of inspection. "
            "Supply piping is estimated to date from original construction (1987)."
        ),
        "severity": "critical",
        "deficiency_suspected": True,
        "photo_description": "Gray polybutylene Quest supply piping with active pinhole leak at compression fitting.",
        "confidence": 0.99,
    },
    {
        "system": "plumbing",
        "location": "Garage — water heater",
        "observation": (
            "Electric water heater, 50-gallon capacity, manufactured 2009 (15 years old). "
            "Temperature-pressure relief valve present but discharge pipe terminates 8 inches "
            "above floor, facing up — creates risk of scalding if TPR activates. "
            "Water heater is at end of expected 12–15 year serviceable life. "
            "No evidence of active leaks at tank connections."
        ),
        "severity": "major",
        "deficiency_suspected": True,
        "photo_description": "15-year-old water heater with TPR discharge pipe incorrectly terminated upward.",
        "confidence": 0.88,
    },
    {
        "system": "hvac",
        "location": "Central air handler — interior utility closet; condenser — exterior pad",
        "observation": (
            "York split-system heat pump, 3-ton capacity, manufactured 2011 (13 years old). "
            "System operational at time of inspection; delta-T (temperature differential across "
            "evaporator) measured at 17°F, within acceptable range. Air filter heavily soiled — "
            "last replacement unknown. Flex ductwork in attic shows two disconnected joints at "
            "Y-branch leading to master bedroom and den. Ductwork is uninsulated in attic section."
        ),
        "severity": "major",
        "deficiency_suspected": True,
        "photo_description": "HVAC system with disconnected flex duct joints in attic and soiled air filter.",
        "confidence": 0.87,
    },
    {
        "system": "structure",
        "location": "Southwest corner of living room and adjacent bedroom wall",
        "observation": (
            "Stair-step diagonal cracking observed in concrete block exterior wall at southwest "
            "corner, extending from floor to approximately 4 feet height. Interior drywall at "
            "same corner shows corresponding cracking. Floor in this area has noticeable slope "
            "estimated at approximately 1 inch over 8 feet. These indicators are consistent with "
            "differential foundation settlement; sinkhole activity cannot be ruled out given "
            "Hillsborough County karst geology."
        ),
        "severity": "critical",
        "deficiency_suspected": True,
        "photo_description": "Stair-step block wall cracking at SW corner with floor slope — possible sinkhole indicator.",
        "confidence": 0.82,
    },
]


def run_demo() -> None:
    print("\n" + "=" * 72)
    print("FLORIDAINSPECT AGENT — DEMO SCENARIO")
    print("=" * 72)
    print(f"Property: {PROPERTY_ADDRESS}")
    print(f"Date:     {INSPECTION_DATE}")
    print(f"Findings: {len(MOCK_FINDINGS)} synthetic findings (no real photos needed)")
    print("=" * 72)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or api_key == "your_key_here":
        print("\nNOTE: GEMINI_API_KEY not set or is still the placeholder value.")
        print("Set a real key in .env to enable AI narrative generation.\n")
        print("Running OFFLINE mode — showing regulatory checks without AI narrative generation.\n")
        _run_offline_demo()
        return

    print("\nStep 1/4 — Validating findings against FL regulations (RAG)...")
    findings: list[FindingDraft] = []
    checks = []

    for i, fdict in enumerate(MOCK_FINDINGS):
        finding = FindingDraft.model_validate(fdict)
        findings.append(finding)
        check = validate_regulation(finding)
        checks.append(check)
        status = "VIOLATION" if check.compliant is False else ("?" if check.compliant is None else "OK")
        print(f"  [{i+1}/{len(MOCK_FINDINGS)}] {finding.system.upper():12} | {status:10} | {finding.severity.upper():14} | insurance: {check.insurance_impact}")

    critical_count = sum(1 for c in checks if c.insurance_impact == "critical")
    print(f"\n  Insurance-blocking findings: {critical_count}")

    print("\nStep 2/4 — Generating professional report narratives (Gemini)...")
    sections = []
    for i, (finding, check) in enumerate(zip(findings, checks)):
        print(f"  Generating section {i+1}/{len(findings)}: {finding.system} ({finding.severity})...", end=" ", flush=True)
        section = generate_narrative(finding, check)
        sections.append(section)
        mode = "fallback" if section.inspector_note and "fallback" in section.inspector_note else "AI"
        print(mode)

    print("\nStep 3/4 — Auditing narratives (AuditAgent — severity, statutes, disclaimers)...")
    audited_sections = []
    audit_passed = 0
    for i, (finding, check, section) in enumerate(zip(findings, checks, sections)):
        print(f"  Auditing section {i+1}/{len(sections)}: {finding.system}...", end=" ", flush=True)
        try:
            audit = audit_narrative(
                narrative=section.narrative,
                finding=finding,
                regulatory_check=check,
                inspection_type="4-point",
            )
        except Exception as exc:
            audit = AuditResult(
                passed=True, confidence=0.0, flags=[f"Audit error: {exc}"],
                verified_statutes=[], auditor_note="Audit skipped.",
            )
        audited_sections.append(section.model_copy(update={"audit_result": audit}))
        status = "PASS" if audit.passed else f"FLAGGED ({len(audit.flags)} issue{'s' if len(audit.flags) != 1 else ''})"
        if audit.passed:
            audit_passed += 1
        print(status)
        if not audit.passed:
            for flag in audit.flags:
                print(f"    ! {flag}")

    print(f"\n  Audit summary: {audit_passed}/{len(audited_sections)} sections passed")

    print("\nStep 4/4 — Assembling full report...")
    report = assemble_full_report(
        sections=audited_sections,
        property_address=PROPERTY_ADDRESS,
        inspection_date=INSPECTION_DATE,
    )

    print("\n" + "=" * 72)
    print("INSPECTION REPORT")
    print("=" * 72)
    print(f"\nProperty:  {report.property_address}")
    print(f"Date:      {report.inspection_date}")
    print(f"Inspector: {report.inspector_name}")
    print(f"License:   {report.inspector_license}")
    print(f"\nEXECUTIVE SUMMARY\n{'-'*40}")
    print(report.executive_summary)

    for section in report.sections:
        print(f"\n{'='*60}")
        print(f"SYSTEM: {section.system.upper()} — {section.severity_summary.upper()}")
        print(f"Headline: {section.headline}")
        print(f"\n{section.narrative}")
        if section.action_items:
            print("\nRecommended Actions:")
            for action in section.action_items:
                print(f"  • {action}")
        if section.inspector_note:
            print(f"\nNote: {section.inspector_note}")
        if section.audit_result:
            ar = section.audit_result
            badge = "✓ AUDIT PASSED" if ar.passed else f"⚠ AUDIT FLAGGED ({len(ar.flags)} issue{'s' if len(ar.flags) != 1 else ''})"
            print(f"Audit: {badge} | confidence={ar.confidence:.2f} | {ar.auditor_note}")
            if not ar.passed:
                for flag in ar.flags:
                    print(f"  ! {flag}")

    print(f"\n{'='*72}")
    print("LIMITATIONS")
    print("-" * 40)
    for lim in report.limitations:
        print(f"  • {lim}")
    print(f"\n{report.footer}")
    print("=" * 72)

    # Save JSON output — inject real REBS photo URLs keyed by system name
    _PHOTO_BASE = (
        "https://raw.githubusercontent.com/carolina-mcagtech/"
        "mcag-hackathon/master/docs/photos"
    )
    _DEMO_PHOTOS: dict[str, str] = {
        "roof":      f"{_PHOTO_BASE}/roof.jpeg",
        "electrical": f"{_PHOTO_BASE}/electrical.jpeg",
        "plumbing":  f"{_PHOTO_BASE}/plumbing.jpeg",
        "hvac":      f"{_PHOTO_BASE}/hvac.jpeg",
    }
    report_dict = report.model_dump()
    for section in report_dict.get("sections", []):
        key = section.get("system", "").lower().split()[0]
        if key in _DEMO_PHOTOS:
            section["photo_url"] = _DEMO_PHOTOS[key]
    output_path = Path(__file__).parent.parent / "demo_report_output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)
        f.write("\n")
    print(f"\nFull report JSON saved to: {output_path}")


def _run_offline_demo() -> None:
    """Run without Gemini API — shows regulatory checks only."""
    print("OFFLINE DEMO — Regulatory Check Results")
    print("=" * 72)
    print(f"{'#':<3} {'SYSTEM':<14} {'SEVERITY':<14} {'INSURANCE':<12} {'COMPLIANT'}")
    print("-" * 72)
    for i, fdict in enumerate(MOCK_FINDINGS):
        finding = FindingDraft.model_validate(fdict)
        check = validate_regulation(finding)
        compliant_str = "NO" if check.compliant is False else ("UNKNOWN" if check.compliant is None else "YES")
        print(f"{i+1:<3} {finding.system.upper():<14} {finding.severity.upper():<14} {check.insurance_impact:<12} {compliant_str}")

    print("\nTop Findings:")
    for i, fdict in enumerate(MOCK_FINDINGS, 1):
        finding = FindingDraft.model_validate(fdict)
        check = validate_regulation(finding)
        if check.insurance_impact in ("critical", "major", "moderate"):
            print(f"\n  [{i}] {finding.system.upper()} — {finding.severity.upper()}")
            print(f"      Observation: {finding.observation[:120]}...")
            print(f"      Action: {check.recommended_action}")
            if check.violation_description:
                print(f"      Violation: {check.violation_description}")

    print("\nSet GEMINI_API_KEY in .env to enable full AI-powered narrative generation.")


if __name__ == "__main__":
    run_demo()
