"""
AGT-04: Diagnostic Reasoning Agent

Core LLM-based reasoning agent. Generates targeted diagnostic questions,
interprets observations, updates hypotheses, and embeds structured
session_update JSON in every response.

Aware of the calling user's role so it can adjust response depth:
  ME  → step-by-step guidance, measurement instructions
  SME → deeper technical analysis, tolerance values, root cause reasoning
"""

import json
import logging
import os
import re
from typing import Any

import anthropic

from agents.base_agent import BaseAgent, AgentError

logger = logging.getLogger(__name__)

AGENT_MODEL   = "claude-sonnet-4-6"
MAX_TOKENS    = 1500
VERSION       = "2.0.0"


class DiagnosticReasoningAgent(BaseAgent):
    AGT_ID  = "AGT-04"
    VERSION = VERSION

    def _execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Input keys:
          context_snapshot:    str
          evidence_text:       str   (formatted evidence block)
          measurement_text:    str   (formatted measurement block from ParameterAgent)
          conversation_history:list[{role, content}]
          new_user_message:    str   (empty string for opening turn)
          session_state:       dict  {completed_steps, likely_causes, current_hypothesis}
          user_role:           str   (ME | SME)
          is_opening_turn:     bool

        Output:
          response_text:   str   (cleaned, markdown-safe)
          session_update:  dict  {completed_steps, likely_causes, current_hypothesis,
                                  probable_cause_flag, unresolved_flag, safety_concern_flag}
          tokens_used:     dict
        """
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise AgentError(self.AGT_ID, "ANTHROPIC_API_KEY not set")

        context_snapshot   : str  = payload.get("context_snapshot", "")
        evidence_text      : str  = payload.get("evidence_text", "")
        measurement_text   : str  = payload.get("measurement_text", "")
        history            : list = payload.get("conversation_history", [])
        new_message        : str  = payload.get("new_user_message", "")
        session_state      : dict = payload.get("session_state", {})
        user_role          : str  = payload.get("user_role", "ME")
        is_opening         : bool = payload.get("is_opening_turn", False)

        system_prompt = _build_system_prompt(
            context_snapshot, evidence_text, measurement_text,
            session_state, user_role,
        )

        messages = list(history)  # copy

        if is_opening:
            comp = _extract_field(context_snapshot, "Affected Component")
            crane= _extract_field(context_snapshot, "Crane Type")
            prob = _extract_field(context_snapshot, "Reported Problem")
            messages.append({"role": "user", "content": (
                f"A new troubleshooting session has started. "
                f"The engineer has reported a problem with the {comp} on a {crane}: "
                f"\"{prob}\". "
                f"Acknowledge what you know from the intake form, summarise the likely "
                f"fault categories for this component and problem, then ask your FIRST "
                f"targeted diagnostic question."
            )})
        else:
            if new_message:
                messages.append({"role": "user", "content": new_message})

        client = anthropic.Anthropic(api_key=api_key)
        try:
            resp = client.messages.create(
                model=AGENT_MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=messages,
            )
        except anthropic.APIError as exc:
            raise AgentError(self.AGT_ID, f"Anthropic API error: {exc}") from exc

        raw_text = resp.content[0].text
        session_update = _extract_session_update(raw_text)
        display_text   = _clean_response_text(raw_text)

        return {
            "response_text":  display_text,
            "raw_response":   raw_text,
            "session_update": session_update,
            "tokens_used":    {
                "input":  resp.usage.input_tokens,
                "output": resp.usage.output_tokens,
            },
        }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _build_system_prompt(
    context_snapshot: str,
    evidence_text: str,
    measurement_text: str,
    session_state: dict,
    user_role: str,
) -> str:
    # Role-specific depth instruction
    if user_role == "SME":
        role_instruction = (
            "You are communicating with a SENIOR MAINTENANCE ENGINEER / SUBJECT MATTER EXPERT. "
            "Provide deep technical analysis: reference tolerance values, failure modes, "
            "regulatory standards (EN, IEC), and component-level root cause reasoning. "
            "Do not over-explain basic procedures."
        )
    else:
        role_instruction = (
            "You are communicating with a MAINTENANCE ENGINEER. "
            "Provide clear, step-by-step guidance. "
            "Explain what each measurement tells you and why each check is needed. "
            "Reference specific values from the retrieved knowledge."
        )

    # Progress section
    steps  = session_state.get("completed_steps", [])
    causes = session_state.get("likely_causes", [])
    hypo   = session_state.get("current_hypothesis", "")

    progress = ""
    if steps:
        progress += "\n\n=== COMPLETED DIAGNOSTIC STEPS ===\n"
        progress += "".join(f"  ✓ {s}\n" for s in steps)
    if causes:
        progress += "\n=== CURRENT WORKING HYPOTHESES ===\n"
        progress += "".join(f"  • {c}\n" for c in causes)
    if hypo:
        progress += f"\n=== CURRENT HYPOTHESIS ===\n  {hypo}\n"

    return f"""You are an expert crane maintenance AI assistant in an industrial troubleshooting system.
Your role is to guide engineers through systematic, evidence-based fault diagnosis.

{role_instruction}

=== CURRENT SESSION CONTEXT (DO NOT RE-ASK THESE BASICS) ===
{context_snapshot}
{evidence_text}
{measurement_text}
{progress}

=== BEHAVIOUR RULES ===
1. Never ask questions already answered in the session context above.
2. Start at the right diagnostic depth — skip generic questions.
3. Be systematic: most-likely causes first, safety checks before invasive tests.
4. Interpret every measurement immediately against reference values.
5. Cite specifications from the retrieved technical knowledge.
6. Prioritise safety — flag critical conditions explicitly.
7. At the end of EVERY response, include this structured JSON block:

```json
{{
  "session_update": {{
    "completed_steps": ["step already done 1", "step already done 2"],
    "likely_causes": ["cause A", "cause B"],
    "current_hypothesis": "brief current theory",
    "probable_cause_flag": false,
    "unresolved_flag": false,
    "safety_concern_flag": false
  }}
}}
```

Set probable_cause_flag=true when you have sufficient evidence to name a root cause.
Set unresolved_flag=true after 8+ turns without identifying a probable cause.
Set safety_concern_flag=true when a safety-critical condition is suspected.

8. Guide toward diagnosis — each question must have a stated purpose.
9. When sufficient evidence is gathered, recommend generating the fault report.
10. Tone: professional, precise, industrial."""


def _extract_session_update(text: str) -> dict:
    try:
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            return data.get("session_update", {})
    except (json.JSONDecodeError, AttributeError):
        pass
    return {}


def _clean_response_text(text: str) -> str:
    cleaned = re.sub(r"```json\s*.*?```", "", text, flags=re.DOTALL)
    return cleaned.strip()


def _extract_field(snapshot: str, field_label: str) -> str:
    match = re.search(rf"{re.escape(field_label)}:\s*(.+)", snapshot)
    return match.group(1).strip() if match else ""
