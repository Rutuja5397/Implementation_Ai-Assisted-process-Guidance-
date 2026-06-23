"""
AGT-07: Safety / Guardrail Agent

Evaluates every AI-generated response before delivery.
Detects safety-critical conditions and prepends a structured warning block.
Cannot be disabled or bypassed for active sessions.
"""

import re
from typing import Any
from agents.base_agent import BaseAgent


# ─── Safety rule definitions ──────────────────────────────────────────────────
# Each rule: (regex_pattern, safety_level, message)
# safety_level: "advisory" | "warning" | "critical"

SAFETY_RULES = [
    # Brake failure + load combination → critical
    (r"brake.{0,40}(fail|not hold|slip|worn|stuck|release)",
     "critical",
     "Brake system deficiency detected. Do NOT operate the crane under load. "
     "Engage manual brake, lower the load safely if present, and suspend operations "
     "until the brake has been inspected and repaired by a qualified technician."),

    # Wire rope structural failures
    (r"(wire rope|rope).{0,40}(broken strand|kink|bird cage|deform|replace)",
     "critical",
     "Wire rope condition issue identified. The crane must NOT be used for lifting "
     "until the rope has been inspected per EN 12385 criteria and replaced if defective."),

    # Insulation / electrical isolation failures
    (r"insulation.{0,40}(fail|below|low|leakage|fault)",
     "warning",
     "Electrical insulation deficiency detected. Risk of electric shock to personnel. "
     "Isolate power supply before any further electrical work. "
     "Test insulation resistance per IEC 60204 before returning to service."),

    # Overload / overheating
    (r"(overload|over.?load|exceed.{0,20}rated|over.?heat|temperature.{0,20}critical)",
     "warning",
     "Overload or overheating condition indicated. Stop the operation immediately. "
     "Allow the crane to cool before resuming. Do not exceed rated load capacity."),

    # Structural / hook defects
    (r"(hook.{0,20}(crack|deform|bend|twist|damage)|block.{0,20}(fail|damage))",
     "critical",
     "Hook or lifting block defect suspected. Remove the crane from service immediately. "
     "Inspect hook per EN 1677 criteria. Replace if deformation exceeds 5% of throat opening."),

    # Gearbox failure
    (r"gearbox.{0,40}(seiz|fail|broken|shatter|crack)",
     "warning",
     "Gearbox mechanical failure suspected. Stop crane operation. "
     "Do not attempt to force movement. Isolate the drive before inspection."),

    # Generic safety-critical language catch-all
    (r"(immediate shutdown|stop operations|cease lifting|do not operate|danger to personnel)",
     "warning",
     "Safety-critical condition referenced in the diagnostic response. "
     "Follow all shutdown and isolation procedures before continuing inspection."),
]

LEVEL_ORDER = {"none": 0, "advisory": 1, "warning": 2, "critical": 3}


class SafetyGuardrailAgent(BaseAgent):
    AGT_ID = "AGT-07"

    def _execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Input keys:
          response_text:  str   (AI-generated diagnostic response)
          has_critical_measurements: bool  (from ParameterAgent)
          component_key:  str

        Output:
          approved:          bool
          safety_flag:       bool
          safety_level:      str   (none|advisory|warning|critical)
          safety_message:    str | None
          modified_response: str   (original with prepended alert block if flagged)
        """
        text: str        = payload.get("response_text", "")
        meas_critical    = payload.get("has_critical_measurements", False)
        component        = payload.get("component_key", "")

        triggered_level   = "none"
        triggered_messages= []

        # Check static safety rules
        for pattern, level, message in SAFETY_RULES:
            if re.search(pattern, text, re.IGNORECASE):
                if LEVEL_ORDER[level] >= LEVEL_ORDER[triggered_level]:
                    triggered_level = level
                triggered_messages.append(message)

        # If parameter agent flagged critical values, escalate to at least warning
        if meas_critical and LEVEL_ORDER["warning"] > LEVEL_ORDER[triggered_level]:
            triggered_level = "warning"
            triggered_messages.append(
                "One or more recorded measurements are outside safe operating limits. "
                "Review the measurement annotations above before proceeding."
            )

        safety_flag = triggered_level != "none"

        if not safety_flag:
            return {
                "approved":          True,
                "safety_flag":       False,
                "safety_level":      "none",
                "safety_message":    None,
                "modified_response": text,
            }

        # Deduplicate messages
        seen = set()
        unique_msgs = []
        for m in triggered_messages:
            if m not in seen:
                seen.add(m)
                unique_msgs.append(m)

        combined_message = " ".join(unique_msgs)

        if triggered_level == "critical":
            alert_header = "🚨 SAFETY CRITICAL — IMMEDIATE ACTION REQUIRED"
            border       = "=" * 60
        else:
            alert_header = "⚠️  SAFETY WARNING"
            border       = "-" * 60

        alert_block = (
            f"\n{border}\n"
            f"{alert_header}\n"
            f"{border}\n"
            f"{combined_message}\n"
            f"{border}\n\n"
        )

        modified_response = alert_block + text

        return {
            "approved":          True,   # always deliver (with alert)
            "safety_flag":       True,
            "safety_level":      triggered_level,
            "safety_message":    combined_message,
            "modified_response": modified_response,
        }
