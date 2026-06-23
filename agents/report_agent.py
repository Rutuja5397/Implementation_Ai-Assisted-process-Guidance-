"""
AGT-08: Report Generation Agent

Synthesises a structured fault report from the complete session transcript,
recorded measurements, and session metadata. Delegates to the existing
report_generator module for Claude API interaction, then returns the
structured report data without writing to the database (the Orchestrator
handles persistence).
"""

import json
import logging
import os
import re
from typing import Any

import anthropic

from agents.base_agent import BaseAgent, AgentError

logger = logging.getLogger(__name__)

AGENT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS  = 1500


class ReportGenerationAgent(BaseAgent):
    AGT_ID = "AGT-08"

    def _execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Input keys:
          crane_type:          str
          component:           str
          problem_description: str
          environment:         str | None
          recent_changes:      str | None
          error_messages:      str | None
          conversation_history: list[{role, content}]
          measurements:        list[dict]   (raw measurement records)
          current_hypothesis:  str | None
          lifecycle_state:     str

        Output:
          report_data:     dict  (structured report fields — NOT yet in DB)
          generation_ok:   bool
          error_message:   str | None
          tokens_used:     dict
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise AgentError(self.AGT_ID, "ANTHROPIC_API_KEY not set")

        crane_type          : str  = payload.get("crane_type", "Unknown Crane")
        component           : str  = payload.get("component", "Unknown Component")
        problem_description : str  = payload.get("problem_description", "")
        environment         : str  = payload.get("environment") or "Not specified"
        recent_changes      : str  = payload.get("recent_changes") or "None reported"
        error_messages      : str  = payload.get("error_messages") or "None reported"
        history             : list = payload.get("conversation_history", [])
        measurements        : list = payload.get("measurements", [])
        current_hypothesis  : str  = payload.get("current_hypothesis") or ""
        lifecycle_state     : str  = payload.get("lifecycle_state", "UNKNOWN")

        # Build conversation transcript
        transcript = ""
        for msg in history:
            role_label = "Engineer" if msg.get("role") == "user" else "AI Assistant"
            transcript += f"\n[{role_label}]: {msg.get('content', '')}\n"

        # Build measurements summary
        meas_list = _format_measurements(measurements)
        meas_summary_str = json.dumps(meas_list, indent=2) if meas_list else "No measurements recorded."

        prompt = f"""You are generating a formal crane maintenance troubleshooting report.

SESSION INFORMATION:
- Crane: {crane_type}
- Component: {component}
- Reported Problem: {problem_description}
- Environment: {environment}
- Recent Changes: {recent_changes}
- Error Messages: {error_messages}
- Lifecycle State at Report: {lifecycle_state}
- Working Hypothesis: {current_hypothesis or 'Not determined'}

MEASUREMENTS RECORDED:
{meas_summary_str}

TROUBLESHOOTING CONVERSATION:
{transcript}

Generate a structured fault report in the following JSON format
(respond ONLY with valid JSON, no other text):

{{
  "issue_summary": "One-sentence summary of the reported fault",
  "steps_taken": [
    "Step 1 description",
    "Step 2 description"
  ],
  "root_cause": "Identified root cause or 'Undetermined - further investigation required'",
  "diagnosis": "Full diagnostic narrative (2-4 sentences)",
  "recommendations": [
    "Recommendation 1",
    "Recommendation 2",
    "Recommendation 3"
  ],
  "severity": "low|medium|high|critical",
  "follow_up_required": true,
  "severity_justification": "Brief justification of severity rating"
}}

Severity guide:
- critical: Immediate safety risk, crane must not be operated
- high: Significant fault, operation should be suspended
- medium: Degraded operation, schedule repair within 48 hours
- low: Minor issue, schedule at next planned maintenance
"""

        client = anthropic.Anthropic(api_key=api_key)
        try:
            resp = client.messages.create(
                model=AGENT_MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            raise AgentError(self.AGT_ID, f"Anthropic API error: {exc}") from exc

        raw_text = resp.content[0].text.strip()
        tokens_used = {
            "input":  resp.usage.input_tokens,
            "output": resp.usage.output_tokens,
        }

        report_data, generation_ok, error_msg = _parse_report_json(
            raw_text, component, crane_type, current_hypothesis, meas_summary_str
        )

        return {
            "report_data":         report_data,
            "measurements_summary": meas_summary_str,
            "generation_ok":       generation_ok,
            "error_message":       error_msg,
            "tokens_used":         tokens_used,
        }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _format_measurements(measurements: list) -> list[dict]:
    """Convert raw measurement dicts to human-readable report entries."""
    result = []
    field_map = {
        "voltage":               ("voltage_V",               "V"),
        "current":               ("current_A",               "A"),
        "temperature":           ("temperature_C",           "°C"),
        "load":                  ("load_kg",                 "kg"),
        "brake_gap":             ("brake_gap_mm",            "mm"),
        "insulation_resistance": ("insulation_resistance_MOhm", "MΩ"),
        "vibration":             ("vibration_mm_s",          "mm/s"),
    }
    for m in measurements:
        entry: dict = {}
        for field, (label, unit) in field_map.items():
            val = m.get(field)
            if val is not None:
                entry[label] = val
        if m.get("notes"):
            entry["notes"] = m["notes"]
        if entry:
            result.append(entry)
    return result


def _parse_report_json(
    raw_text: str,
    component: str,
    crane_type: str,
    current_hypothesis: str,
    meas_summary_str: str,
) -> tuple[dict, bool, str | None]:
    """Parse Claude JSON response; return (report_data, ok, error_msg)."""
    text = raw_text

    # Strip markdown fences if present
    fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)

    try:
        data = json.loads(text)
        return data, True, None
    except json.JSONDecodeError as exc:
        logger.error(f"[AGT-08] Failed to parse report JSON: {exc}")
        fallback = {
            "issue_summary":          f"Fault investigation: {component} on {crane_type}",
            "steps_taken":            ["Session conducted; see conversation transcript"],
            "root_cause":             "Undetermined - review conversation for details",
            "diagnosis":              current_hypothesis or "No diagnosis recorded.",
            "recommendations":        ["Review conversation history", "Consult OEM documentation"],
            "severity":               "medium",
            "follow_up_required":     True,
            "severity_justification": "Default severity assigned due to parse failure.",
        }
        return fallback, False, str(exc)
