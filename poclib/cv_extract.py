"""Optional: extract structured attributes from academic CVs via the Claude API.

Enriches author attributes (career stage, prior funders, prestige signals) that
Dimensions does not capture, using tool-use for guaranteed-shape JSON output.
Used only in a demo cell; not part of the core GBQ pipeline.
"""
from anthropic import Anthropic

from . import config

EXTRACTION_MODEL = "claude-sonnet-4-6"

CV_SCHEMA = {
    "name": "academic_cv",
    "description": "Structured attributes extracted from an academic CV.",
    "input_schema": {
        "type": "object",
        "properties": {
            "full_name": {"type": "string"},
            "current_position": {"type": "string", "description": "e.g. Assistant Professor"},
            "career_stage": {
                "type": "string",
                "enum": ["graduate", "postdoc", "early_career", "mid_career", "senior", "emeritus", "unknown"],
            },
            "current_institution": {"type": "string"},
            "phd_year": {"type": "integer"},
            "phd_institution": {"type": "string"},
            "funders": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Funding agencies/foundations named as grant sources.",
            },
            "prestige_signals": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Named awards, fellowships, memberships (e.g. NAS, HHMI, Sloan).",
            },
        },
        "required": ["full_name", "career_stage"],
    },
}


def extract_cv(cv_text: str, model: str = EXTRACTION_MODEL) -> dict:
    """Return structured CV attributes as a dict using a single tool call."""
    client = Anthropic(api_key=config.require("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model=model,
        max_tokens=1500,
        tools=[CV_SCHEMA],
        tool_choice={"type": "tool", "name": "academic_cv"},
        messages=[
            {
                "role": "user",
                "content": (
                    "Extract structured attributes from this academic CV. "
                    "Use the academic_cv tool. Leave fields out if not stated.\n\n"
                    f"{cv_text}"
                ),
            }
        ],
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise RuntimeError("Model did not return a tool_use block.")
