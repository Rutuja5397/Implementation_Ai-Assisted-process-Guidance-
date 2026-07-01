"""
AGT-04: Diagnostic Reasoning Agent

Core LLM-based reasoning agent. Generates targeted diagnostic questions,
interprets observations, updates hypotheses, and uses tool_use to guarantee
structured output (questions, session_update, knowledge_confidence) every turn.
"""

import json
import logging
import os
from typing import Any

import anthropic

from agents.base_agent import BaseAgent, AgentError

logger = logging.getLogger(__name__)

AGENT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS  = 2500
VERSION     = "2.0.0"

# ─── Tool definition ──────────────────────────────────────────────────────────

DIAGNOSTIC_TOOL = {
    "name": "submit_diagnostic_data",
    "description": (
        "Submit structured diagnostic data for this troubleshooting step. "
        "Call this ONCE per response with the questions for the engineer to answer "
        "and the current session state."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "session_update": {
                "type": "object",
                "properties": {
                    "completed_steps":      {"type": "array", "items": {"type": "string"}},
                    "likely_causes":        {"type": "array", "items": {"type": "string"}},
                    "current_hypothesis":   {"type": "string"},
                    "probable_cause_flag":  {"type": "boolean"},
                    "unresolved_flag":      {"type": "boolean"},
                    "safety_concern_flag":  {"type": "boolean"},
                },
                "required": ["completed_steps", "likely_causes", "current_hypothesis"],
            },
            "questions": {
                "type": "array",
                "description": "Structured questions for the engineer to answer via form widgets.",
                "items": {
                    "type": "object",
                    "properties": {
                        "text":    {"type": "string"},
                        "type":    {"type": "string", "enum": ["yesno", "number", "choice", "text"]},
                        "unit":    {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["text", "type"],
                },
            },
            "knowledge_confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
            },
            "confidence_reason": {
                "type": "string",
            },
        },
        "required": ["session_update", "questions", "knowledge_confidence"],
    },
}


class DiagnosticReasoningAgent(BaseAgent):
    AGT_ID  = "AGT-04"
    VERSION = VERSION

    def _execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise AgentError(self.AGT_ID, "ANTHROPIC_API_KEY not set")

        context_snapshot : str  = payload.get("context_snapshot", "")
        evidence_text    : str  = payload.get("evidence_text", "")
        measurement_text : str  = payload.get("measurement_text", "")
        history          : list = payload.get("conversation_history", [])
        new_message      : str  = payload.get("new_user_message", "")
        session_state    : dict = payload.get("session_state", {})
        user_role        : str  = payload.get("user_role", "ME")
        is_opening       : bool = payload.get("is_opening_turn", False)

        system_prompt = _build_system_prompt(
            context_snapshot, evidence_text, measurement_text,
            session_state, user_role,
        )

        messages = list(history)

        if is_opening:
            comp  = _extract_field(context_snapshot, "Affected Component")
            crane = _extract_field(context_snapshot, "Crane Type")
            prob  = _extract_field(context_snapshot, "Reported Problem")
            messages.append({"role": "user", "content": (
                f"A new troubleshooting session has started. "
                f"The engineer has reported a problem with the {comp} on a {crane}: "
                f"\"{prob}\". "
                f"Acknowledge what you know from the intake form, summarise the likely "
                f"fault categories, then ask your first targeted diagnostic questions."
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
                tools=[DIAGNOSTIC_TOOL],
                tool_choice={"type": "auto"},
            )
        except anthropic.APIError as exc:
            raise AgentError(self.AGT_ID, f"Anthropic API error: {exc}") from exc

        display_text, session_update, questions, confidence, confidence_reason = _parse_tool_response(resp)

        return {
            "response_text":        display_text,
            "session_update":       session_update,
            "questions":            questions,
            "knowledge_confidence": confidence,
            "confidence_reason":    confidence_reason,
            "tokens_used": {
                "input":  resp.usage.input_tokens,
                "output": resp.usage.output_tokens,
            },
        }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_tool_response(response):
    """Extract prose text and structured data from a Claude response.
    Works whether Claude used the tool or not — falls back to regex parsing.
    """
    import re as _re

    display_text      = ""
    session_update    = {}
    questions         = []
    confidence        = "high"
    confidence_reason = ""
    tool_called       = False

    for block in response.content:
        if block.type == "text":
            display_text += block.text
        elif block.type == "tool_use" and block.name == "submit_diagnostic_data":
            tool_called       = True
            data              = block.input
            session_update    = data.get("session_update", {})
            questions         = data.get("questions", [])
            confidence        = data.get("knowledge_confidence", "high")
            confidence_reason = data.get("confidence_reason", "")

    # Fallback: if Claude didn't call the tool, try regex on the text
    if not tool_called and display_text:
        match = _re.search(r"```json\s*(.*?)\s*```", display_text, _re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                session_update = data.get("session_update", {})
            except (json.JSONDecodeError, AttributeError):
                pass
        # Clean JSON block from display text
        display_text = _re.sub(r"```json\s*.*?```", "", display_text, flags=_re.DOTALL)

    return display_text.strip(), session_update, questions, confidence, confidence_reason


def _build_system_prompt(
    context_snapshot: str,
    evidence_text: str,
    measurement_text: str,
    session_state: dict,
    user_role: str,
) -> str:
    if user_role == "SME":
        role_instruction = (
            "You are communicating with a SENIOR MAINTENANCE ENGINEER. "
            "Provide deep technical analysis: reference tolerance values, failure modes, "
            "regulatory standards (EN, IEC), and component-level root cause reasoning."
        )
    else:
        role_instruction = (
            "You are communicating with a MAINTENANCE ENGINEER. "
            "Provide clear, step-by-step guidance. "
            "Explain what each measurement tells you and why each check is needed. "
            "Reference specific values from the retrieved knowledge."
        )

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

=== CURRENT SESSION CONTEXT (DO NOT RE-ASK THESE) ===
{context_snapshot}
{evidence_text}
{measurement_text}
{progress}

=== BEHAVIOUR RULES ===
1. Never ask questions already answered in the session context above.
2. Start at the right diagnostic depth — skip generic questions.
3. Be systematic: most-likely causes first, safety checks before invasive tests.
4. Interpret every measurement immediately against reference values from the knowledge.
5. Cite specifications from the retrieved technical knowledge when relevant.
6. Prioritise safety — flag critical conditions explicitly in your prose.
7. You MUST call the submit_diagnostic_data tool in EVERY response. Write your prose explanation first, then call the tool.
8. Do NOT write questions in your prose — all questions go in the tool call questions array.
9. Keep prose to 2–4 sentences: explain the diagnostic reasoning and what the answers will reveal.
10. When sufficient evidence is gathered, recommend generating the fault report.
11. Tone: professional, precise, industrial.

Question types for the tool:
- yesno: Yes/No checks (rendered as radio buttons)
- number: measurements with a unit (rendered as number input)
- choice: fixed options (rendered as dropdown, include options array)
- text: open observations (rendered as text area)"""


def _extract_field(snapshot: str, field_label: str) -> str:
    import re
    match = re.search(rf"{re.escape(field_label)}:\s*(.+)", snapshot)
    return match.group(1).strip() if match else ""
