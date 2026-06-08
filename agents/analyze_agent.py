"""
AnalyzeAgent — Second stage of the FloridaInspect pipeline.

Responsibilities:
- Receive FindingDraft objects from CaptureAgent.
- Call validate_regulation (RAG against fl_regulations.txt + ChromaDB) for each finding.
- Apply Florida-specific regulatory knowledge to produce RegulatoryCheck results.
- Flag findings that are insurance-blocking or require licensed specialist referral.

This agent embodies the regulatory expertise of a Florida-licensed home inspector:
it knows Florida Statute 468 Part XV, the Citizens 4-Point form requirements,
Wind Mitigation OIR-B1-1802 criteria, and common FL-specific deficiencies
(polybutylene pipe, Federal Pacific panels, Chinese drywall, sinkhole indicators).
"""

from google.adk.agents import Agent

from tools.classify_photo import FindingDraft
from tools.validate_regulation import RegulatoryCheck, validate_regulation


def _validate_findings_tool(findings: list[dict]) -> list[dict]:
    """ADK-callable wrapper around validate_regulation.

    Args:
        findings: List of FindingDraft dicts (as produced by CaptureAgent).

    Returns:
        List of RegulatoryCheck dicts with compliance verdicts and actions.
    """
    results: list[dict] = []
    for finding_dict in findings:
        # Skip error records from CaptureAgent
        if "error" in finding_dict:
            results.append({
                "finding_summary": finding_dict.get("observation", "Unknown"),
                "applicable_regulations": [],
                "compliant": None,
                "violation_description": "Photo could not be classified — skipped regulatory check.",
                "recommended_action": "Obtain a valid photo of this area for proper evaluation.",
                "insurance_impact": "none",
                "supporting_excerpts": [],
                "skipped": True,
            })
            continue

        try:
            finding = FindingDraft.model_validate(finding_dict)
            check = validate_regulation(finding)
            results.append(check.model_dump())
        except Exception as exc:
            results.append({
                "finding_summary": finding_dict.get("observation", "Unknown")[:200],
                "applicable_regulations": [],
                "compliant": None,
                "violation_description": None,
                "recommended_action": "Manual regulatory review required due to processing error.",
                "insurance_impact": "none",
                "supporting_excerpts": [],
                "error": str(exc),
            })
    return results


def _flag_critical_findings_tool(regulatory_checks: list[dict]) -> dict:
    """Identify insurance-blocking and safety-critical issues requiring immediate attention.

    Args:
        regulatory_checks: List of RegulatoryCheck dicts from _validate_findings_tool.

    Returns:
        Summary dict with lists of critical, major, and referral-required findings.
    """
    critical: list[dict] = []
    major: list[dict] = []
    referrals: list[str] = []

    referral_keywords = [
        "geotechnical engineer", "sinkhole", "mold remediator", "wdo", "pest control",
        "structural engineer", "licensed electrician", "licensed plumber",
    ]

    for check in regulatory_checks:
        if check.get("insurance_impact") == "critical":
            critical.append(check)
        elif check.get("insurance_impact") in ("major", "moderate"):
            major.append(check)

        action_lower = check.get("recommended_action", "").lower()
        for kw in referral_keywords:
            if kw in action_lower and kw not in referrals:
                referrals.append(kw.replace("licensed ", "").title())

    return {
        "critical_count": len(critical),
        "major_count": len(major),
        "critical_findings": critical,
        "major_findings": major,
        "specialist_referrals_required": list(set(referrals)),
        "insurance_eligible": len(critical) == 0,
    }


analyze_agent = Agent(
    name="analyze_agent",
    model="gemini-2.5-flash",
    description=(
        "Validates inspection findings against Florida home inspection regulations using RAG. "
        "Applies knowledge of Florida Statute 468, 4-Point inspection requirements, Wind Mitigation "
        "criteria, and common Florida-specific deficiencies (polybutylene pipe, Federal Pacific panels, "
        "Chinese drywall). Returns regulatory verdicts, violation descriptions, and recommended actions."
    ),
    instruction=(
        "You are the AnalyzeAgent for FloridaInspect, a Florida home inspection AI system. "
        "Your role is to validate each inspection finding against Florida building codes and "
        "insurance requirements. "
        "\n\n"
        "When given a list of FindingDraft observations from CaptureAgent: "
        "1. Call validate_findings_tool to check each finding against FL regulations. "
        "2. Call flag_critical_findings_tool to identify insurance-blocking issues. "
        "3. Prioritise findings by insurance impact: critical > moderate > minor > none. "
        "4. For any critical finding, clearly state the specific Florida statute or code violated. "
        "5. Return the complete list of RegulatoryCheck results plus the critical findings summary. "
        "\n\n"
        "Key Florida-specific rules to enforce: "
        "- Federal Pacific / Zinsco panels: non-insurable, must flag as critical. "
        "- Polybutylene supply piping: non-insurable, must flag as critical. "
        "- Aluminum branch wiring without COPALUM/AlumiConn: critical safety hazard. "
        "- Roof age 20+ years or active leaks: insurance-blocking. "
        "- HVAC/water heater 15+ years: flag for replacement budget. "
        "- Sinkhole indicators and mold: must refer to licensed specialists."
    ),
    tools=[_validate_findings_tool, _flag_critical_findings_tool],
)
