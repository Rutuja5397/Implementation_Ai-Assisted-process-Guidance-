"""
AGT-06: Procedure Guidance Agent

Retrieves structured step-by-step procedures from the knowledge base
for a given component and procedure type (inspection, adjustment, test,
replacement). Returns numbered steps ready for direct display.
"""

from typing import Any, Optional
from agents.base_agent import BaseAgent
from agents.retrieval_agent import _get_rag


# Keywords used to match procedure sections in retrieved chunks
PROCEDURE_KEYWORDS: dict[str, list[str]] = {
    "inspection": [
        "inspection procedure", "visual inspection", "inspect", "check for",
        "examine", "maintenance check",
    ],
    "adjustment": [
        "adjustment procedure", "adjust", "setting", "calibrate", "set gap",
        "alignment", "brake adjustment",
    ],
    "test": [
        "test procedure", "testing", "measure", "resistance test", "load test",
        "function test", "insulation test",
    ],
    "replacement": [
        "replacement", "replace", "install new", "removal procedure",
        "disassembly", "assembly",
    ],
}


class ProcedureGuidanceAgent(BaseAgent):
    AGT_ID = "AGT-06"

    def _execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Input keys:
          component_key:    str
          procedure_type:   str  (inspection|adjustment|test|replacement)

        Output:
          procedure_found:  bool
          procedure_title:  str
          steps:            list[str]
          source:           str
          notes:            str | None
        """
        component     : str = payload.get("component_key", "")
        procedure_type: str = payload.get("procedure_type", "inspection").lower()

        keywords = PROCEDURE_KEYWORDS.get(procedure_type, PROCEDURE_KEYWORDS["inspection"])
        query = f"{component} {procedure_type} procedure " + " ".join(keywords[:2])

        rag = _get_rag()
        chunks = rag.retrieve(query=query, component=component, n_results=3)

        if not chunks:
            return {
                "procedure_found": False,
                "procedure_title": f"{procedure_type.title()} procedure not found",
                "steps": [
                    "No procedure found in the knowledge base for this component "
                    "and procedure type. Consult the manufacturer's documentation."
                ],
                "source": "knowledge_base (no match)",
                "notes": "Consider flagging this as a knowledge gap.",
            }

        # Use the most relevant chunk
        best = chunks[0]
        raw  = best["content"]
        source = best.get("source", "knowledge_base")

        steps = _extract_steps(raw)
        title = f"{component} — {procedure_type.title()} Procedure"

        return {
            "procedure_found": True,
            "procedure_title": title,
            "steps":           steps,
            "source":          source,
            "notes":           None,
        }


def _extract_steps(text: str) -> list[str]:
    """
    Extract numbered or bulleted steps from a raw knowledge chunk.
    Falls back to splitting on sentences if no structure is found.
    """
    import re
    lines = text.split("\n")
    steps = []

    # Try numbered steps first: "1.", "1)", "Step 1"
    for line in lines:
        line = line.strip()
        if re.match(r"^(\d+[\.\)]|Step\s+\d+)", line, re.IGNORECASE):
            cleaned = re.sub(r"^(\d+[\.\)]|Step\s+\d+\.?\s*)", "", line, flags=re.IGNORECASE).strip()
            if cleaned:
                steps.append(cleaned)

    if steps:
        return steps

    # Try bullet points: "- ", "• ", "* "
    for line in lines:
        line = line.strip()
        if re.match(r"^[-•*]\s+", line):
            cleaned = re.sub(r"^[-•*]\s+", "", line).strip()
            if len(cleaned) > 10:
                steps.append(cleaned)

    if steps:
        return steps

    # Fallback: split into meaningful sentences
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 20][:8]
