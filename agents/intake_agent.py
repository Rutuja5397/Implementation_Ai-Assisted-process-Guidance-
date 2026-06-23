"""
AGT-02: Intake Agent

Validates and structures fault intake form data into a clean context
snapshot that downstream agents can rely on without re-validating.
"""

from typing import Any
from agents.base_agent import BaseAgent, AgentError
from backend.rag_system import COMPONENT_FILE_MAP


class IntakeAgent(BaseAgent):
    AGT_ID = "AGT-02"

    REQUIRED_FIELDS = ("crane_type", "component", "problem_description")

    def _execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Input keys (all str):
          crane_type, component, problem_description,
          environment*, recent_changes*, error_messages*   (* optional)

        Output:
          valid: bool
          context_snapshot: str   (formatted text block for system prompt)
          component_key: str      (normalised, for ChromaDB filter)
          validation_errors: list[str]
        """
        errors = []

        for field in self.REQUIRED_FIELDS:
            val = payload.get(field, "")
            if not val or not str(val).strip():
                errors.append(f"Missing required field: {field}")

        if errors:
            return {"valid": False, "validation_errors": errors,
                    "context_snapshot": "", "component_key": ""}

        crane    = str(payload["crane_type"]).strip()
        component= str(payload["component"]).strip()
        problem  = str(payload["problem_description"]).strip()
        env      = str(payload.get("environment") or "Not specified").strip()
        changes  = str(payload.get("recent_changes") or "None reported").strip()
        errors_f = str(payload.get("error_messages") or "None reported").strip()

        # Normalise component key for ChromaDB lookup
        component_key = component if component in COMPONENT_FILE_MAP else component

        context_snapshot = (
            f"Crane Type:          {crane}\n"
            f"Affected Component:  {component}\n"
            f"Reported Problem:    {problem}\n"
            f"Environment:         {env}\n"
            f"Recent Changes:      {changes}\n"
            f"Error Codes/Warnings:{errors_f}"
        )

        return {
            "valid": True,
            "validation_errors": [],
            "context_snapshot": context_snapshot,
            "component_key": component_key,
            "structured": {
                "crane_type":           crane,
                "component":            component,
                "problem_description":  problem,
                "environment":          env,
                "recent_changes":       changes,
                "error_messages":       errors_f,
            },
        }
