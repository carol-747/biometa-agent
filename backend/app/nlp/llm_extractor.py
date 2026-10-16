"""Optional LLM-based relationship extractor using Claude tool use.

Runs only when ANTHROPIC_API_KEY is set; the rule-based v2 extractor is the
default so the pipeline has no API dependency. The LLM is forced to return
structured output through a tool schema, and we keep only relations whose
microbe and metabolite surface strings actually occur in the sentence (so the
model cannot invent entities). Negated relations are dropped, matching v2.
"""

from __future__ import annotations

import json
import logging

from app.core.config import get_settings
from app.nlp.relationship_extractor import Relationship

logger = logging.getLogger(__name__)

REL_TYPES = ["produces", "consumes", "converts", "inhibits", "activates",
             "associates_with", "interacts", "regulates"]

TOOL = {
    "name": "record_relationships",
    "description": "Record every microbe-metabolite relationship explicitly asserted in the text.",
    "input_schema": {
        "type": "object",
        "properties": {
            "relationships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "microbe": {"type": "string", "description": "Exact microbe name as written in the text"},
                        "metabolite": {"type": "string", "description": "Exact metabolite name as written in the text"},
                        "relationship_type": {"type": "string", "enum": REL_TYPES},
                        "negated": {"type": "boolean", "description": "True if the text says this relationship does NOT hold"},
                        "evidence": {"type": "string", "description": "The clause supporting this"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["microbe", "metabolite", "relationship_type", "negated", "confidence"],
                },
            }
        },
        "required": ["relationships"],
    },
}

PROMPT = """Extract microbe-metabolite relationships from this biomedical text.

Rules:
- Only relationships the text explicitly asserts. Do not use outside knowledge.
- Use the exact surface spelling of each microbe and metabolite from the text.
- "X produces B from A" means X produces B AND X consumes A (substrate). Use `converts` only when the text says convert/transform/catalyze.
- If the text says a relationship does NOT hold (negation), set negated=true.
- A bare co-mention with no asserted relationship should be omitted.

Text:
{text}"""


def extract_relationships_llm(text: str, pmid: str | None = None, model: str | None = None) -> list[Relationship]:
    if not text:
        return []
    import anthropic

    settings = get_settings()
    if not settings.anthropic_api_key:
        raise RuntimeError("LLM extractor requires ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    resp = client.messages.create(
        model=model or "claude-sonnet-4-6",
        max_tokens=1500,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "record_relationships"},
        messages=[{"role": "user", "content": PROMPT.format(text=text)}],
    )
    data = next((b.input for b in resp.content if getattr(b, "type", None) == "tool_use"), None)
    if not data:
        return []

    low = text.lower()
    out: list[Relationship] = []
    for r in data.get("relationships", []):
        micro, met = r.get("microbe", ""), r.get("metabolite", "")
        if micro.lower() not in low or met.lower() not in low:  # reject hallucinated entities
            continue
        rtype = r.get("relationship_type")
        if rtype not in REL_TYPES:
            continue
        out.append(Relationship(
            microbe=micro, microbe_type="", metabolite=met, metabolite_class="",
            relationship_type=rtype, confidence=round(float(r.get("confidence", 0.7)), 3),
            evidence_sentence=(r.get("evidence") or text).strip(), article_pmid=pmid,
            extraction_method="llm", negated=bool(r.get("negated", False)),
        ))
    return [r for r in out if not r.negated]
