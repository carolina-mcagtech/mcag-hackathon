"""
CaptureAgent — First stage of the FloridaInspect pipeline.

Responsibilities:
- Accept a list of inspection photo paths from the orchestrator.
- Call the classify_photo tool (Gemini Vision) for each photo.
- Return a list of FindingDraft objects for downstream processing.

In a real Florida home inspection workflow the inspector photographs each
system (roof, electrical panel, plumbing, HVAC) and this agent transforms
those raw images into structured data that AnalyzeAgent can validate against
Florida Statute 468 and insurance requirements.
"""

from google.adk.agents import Agent

from tools.classify_photo import FindingDraft, classify_photo


def _classify_photos_tool(photo_paths: list[str], location_hints: list[str] | None = None) -> list[dict]:
    """ADK-callable wrapper around classify_photo.

    Args:
        photo_paths: List of file system paths to inspection photos.
        location_hints: Optional parallel list of location strings (e.g. 'attic', 'main panel').

    Returns:
        List of FindingDraft dicts serialised for ADK message passing.
    """
    findings: list[dict] = []
    for i, path in enumerate(photo_paths):
        hint = location_hints[i] if location_hints and i < len(location_hints) else None
        try:
            draft = classify_photo(image_path=path, location_hint=hint)
            findings.append(draft.model_dump())
        except FileNotFoundError:
            findings.append({
                "system": "other",
                "location": hint or "unknown",
                "observation": f"Photo file not found: {path}",
                "severity": "informational",
                "deficiency_suspected": False,
                "photo_description": "Missing photo",
                "confidence": 0.0,
                "error": f"FileNotFoundError: {path}",
            })
        except Exception as exc:
            findings.append({
                "system": "other",
                "location": hint or "unknown",
                "observation": f"Classification failed: {exc}",
                "severity": "informational",
                "deficiency_suspected": False,
                "photo_description": "Classification error",
                "confidence": 0.0,
                "error": str(exc),
            })
    return findings


capture_agent = Agent(
    name="capture_agent",
    model="gemini-1.5-flash",
    description=(
        "Processes inspection photos using Gemini Vision. Accepts a list of photo paths "
        "and returns structured FindingDraft observations for each image. This is the "
        "first stage in the FloridaInspect pipeline, transforming raw field photos into "
        "structured data aligned with Florida Statute 468 inspection categories."
    ),
    instruction=(
        "You are the CaptureAgent for FloridaInspect, a Florida home inspection AI system. "
        "Your role is to analyse inspection photos and classify what you observe. "
        "When given a list of photo paths, call the classify_photos_tool for all photos. "
        "For each photo, identify the inspection system (roof, electrical, plumbing, hvac, structure), "
        "describe what is visible, assess severity, and flag suspected deficiencies. "
        "Return all findings as a structured list for the AnalyzeAgent to validate. "
        "If a photo path is invalid or a classification fails, include an error record so "
        "no findings are silently dropped."
    ),
    tools=[_classify_photos_tool],
)
