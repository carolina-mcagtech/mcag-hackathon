"""
FloridaInspect Orchestrator Agent — root ADK agent that coordinates the
three-stage inspection pipeline:

  CaptureAgent  →  AnalyzeAgent  →  ReportAgent

The orchestrator receives a job request (list of photo paths + property info),
delegates photo classification to CaptureAgent, sends the findings to
AnalyzeAgent for regulatory validation, and finally hands validated results to
ReportAgent to produce the written inspection report.

Architecture notes:
- Uses google-adk's Agent with sub_agents list for multi-agent delegation.
- The orchestrator itself does minimal work; it routes, merges results, and
  handles errors from sub-agents.
- All state is passed as structured JSON through ADK message content.
"""

from google.adk.agents import Agent

from agents.analyze_agent import analyze_agent
from agents.audit_agent import audit_agent
from agents.capture_agent import capture_agent
from agents.report_agent import report_agent


root_agent = Agent(
    name="floridainspect_orchestrator",
    model="gemini-2.5-flash",
    description=(
        "FloridaInspect root orchestrator. Coordinates a four-agent Florida home inspection "
        "workflow: photo classification (CaptureAgent) → regulatory validation (AnalyzeAgent) "
        "→ professional report generation (ReportAgent) → quality audit (AuditAgent). "
        "Returns a complete, standards-compliant Florida home inspection report with "
        "audit-verified narratives."
    ),
    instruction=(
        "You are the orchestrator for FloridaInspect, an AI-powered Florida home inspection system "
        "built for MCAG Technologies. You coordinate four specialist sub-agents to produce a "
        "complete, quality-verified inspection report from raw field photos. "
        "\n\n"
        "IMPORTANT — HOW TO CALL SUB-AGENTS: "
        "Use the transfer_to_agent tool to delegate work. Do NOT invent or call any other tool. "
        "You only have one tool available: transfer_to_agent. "
        "\n\n"
        "WORKFLOW — follow this sequence strictly using transfer_to_agent: "
        "\n"
        "STEP 1 — CAPTURE: "
        "Call transfer_to_agent with agent_name='capture_agent' and pass the full JSON payload "
        "including photo_paths, property_address, inspection_date, inspection_type, and location_hints. "
        "Wait for the list of FindingDraft objects. Validate that findings were returned; "
        "if all photos failed, abort and report the error. "
        "\n\n"
        "STEP 2 — ANALYZE: "
        "Call transfer_to_agent with agent_name='analyze_agent', passing the FindingDraft list. "
        "It will validate each finding against Florida Statute 468 and insurance requirements "
        "and return RegulatoryCheck objects plus a critical findings summary. "
        "If any critical insurance-blocking findings are detected, include a prominent "
        "warning in your final output. "
        "\n\n"
        "STEP 3 — REPORT: "
        "Call transfer_to_agent with agent_name='report_agent', passing both the FindingDraft list "
        "and RegulatoryCheck list (as parallel arrays) along with property address and inspection date. "
        "report_agent will return the formatted inspection report sections. "
        "\n\n"
        "STEP 4 — AUDIT: "
        "Call transfer_to_agent with agent_name='audit_agent', passing the ReportSection list, "
        "FindingDraft list, RegulatoryCheck list, and inspection_type. "
        "audit_agent will validate each narrative for severity consistency, statute accuracy, "
        "and disclaimer compliance. Note any sections that failed audit. "
        "\n\n"
        "FINAL OUTPUT: "
        "Return a structured response containing: "
        "  1. The formatted inspection report text. "
        "  2. A summary of critical/major findings. "
        "  3. Whether the property is likely insurable based on findings. "
        "  4. List of specialist referrals required. "
        "  5. Audit summary: how many sections passed, any flags requiring attention. "
        "\n\n"
        "ERROR HANDLING: "
        "If a sub-agent fails or returns incomplete results, include a clear error note in "
        "the output and continue with available data rather than aborting entirely. "
        "Always remind the user that AI-generated reports require review by a Florida "
        "licensed home inspector (FL Statute 468.8314) before delivery to clients."
    ),
    sub_agents=[capture_agent, analyze_agent, report_agent, audit_agent],
)
