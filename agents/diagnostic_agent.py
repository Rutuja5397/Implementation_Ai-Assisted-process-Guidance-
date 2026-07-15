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
MAX_TOKENS    = 2500
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
        session_update, questions, confidence, confidence_reason = _extract_structured_data(raw_text)
        display_text = _clean_response_text(raw_text)

        return {
            "response_text":        display_text,
            "raw_response":         raw_text,
            "session_update":       session_update,
            "questions":            questions,
            "knowledge_confidence": confidence,
            "confidence_reason":    confidence_reason,
            "tokens_used":          {
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
            "Provide technical analysis with reference values and root cause reasoning. "
            "Do not over-explain basic procedures."
        )
    else:
        role_instruction = (
            "You are communicating with a MAINTENANCE ENGINEER on the shop floor. "
            "Use PLAIN, SIMPLE language. Avoid jargon. "
            "Questions must be short, direct, and easy to understand — "
            "as if you are talking to a colleague standing next to the crane. "
            "Tell them exactly what to look at or measure, in one simple sentence."
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

=== KNOWLEDGE BOUNDARY — CRITICAL CONSTRAINT ===
Base ALL diagnostic guidance, specifications, thresholds, and procedures EXCLUSIVELY on the content in the RETRIEVED TECHNICAL KNOWLEDGE section. If the retrieved knowledge does not cover a specific check or value, state: "This information is not in the knowledge base" and set knowledge_confidence to "low".

=== CURRENT SESSION CONTEXT (DO NOT RE-ASK THESE BASICS) ===
{context_snapshot}
{evidence_text}
{measurement_text}
{progress}

=== BEHAVIOUR RULES ===
1. **DO NOT re-ask anything already in the session context above.**
2. **Progress simple to complex:** visual inspection → operational status → basic electrical → measurements → invasive tests. Never jump straight to voltage readings if a simpler check can rule out the cause.
3. **Ask ONE question per turn.** Pick the single most important next diagnostic step. Do NOT list multiple questions.
4. Be systematic: most-likely causes first, safety checks before invasive tests.
5. Interpret every measurement immediately against reference values from the retrieved knowledge.
6. Cite specifications from the retrieved technical knowledge (e.g. "per the Demag spec, brake air gap should be 0.2–0.3 mm").
7. Prioritise safety — flag critical conditions explicitly.
8. **CRITICAL: Do NOT write the question anywhere in your prose.** The question MUST appear ONLY in the `questions` array in the JSON block below.
9. At the end of EVERY response, include this structured JSON block:

```json
{{
  "session_update": {{
    "completed_steps": ["step already done 1"],
    "likely_causes": ["cause A"],
    "current_hypothesis": "brief current theory",
    "probable_cause_flag": false,
    "unresolved_flag": false,
    "safety_concern_flag": false
  }},
  "questions": [
    {{"text": "Is the main isolator confirmed ON?", "type": "yesno"}}
  ],
  "knowledge_confidence": "high",
  "confidence_reason": ""
}}
```

**The `questions` array must contain exactly ONE question.** Choose the question that will most efficiently narrow down the fault.

**QUESTION WRITING RULES:**
- Write questions in plain, everyday English — short and direct.
- Bad example: "Can you confirm the electromagnetic coil de-energisation sequence is functioning correctly?"
- Good example: "Does the brake release when the hoist is switched on?"
- Bad example: "What is the measured insulation resistance between phase conductors?"
- Good example: "Use a multimeter on the motor terminals — what voltage do you read? (in Volts)"
- One question = one thing to check. Never combine two checks in one question.

**Question types:**
- `"yesno"` — Yes/No questions (e.g. "Is the brake disc visually worn or cracked?")
- `"number"` — a single measurement (e.g. "What is the brake air gap? (in mm)")
- `"choice"` — pick one from a list; add `"options": ["opt1", "opt2"]` to the object
- `"text"` — describe what you see (e.g. "Describe any unusual sounds or smells from the brake")

**`knowledge_confidence` values:**
- `"high"` — retrieved knowledge directly covers this step
- `"medium"` — retrieved knowledge is partially relevant
- `"low"` — retrieved knowledge does not cover this fault; set `confidence_reason` to a short phrase

Set probable_cause_flag=true when you have sufficient evidence to name a root cause.
Set unresolved_flag=true after 8+ turns without identifying a probable cause.
Set safety_concern_flag=true when a safety-critical condition is suspected.

10. Your prose explanation (before the JSON) should be 2–3 short sentences: what you suspect, what to check, and what the answer will tell you. Keep it simple and clear.
11. When sufficient evidence is gathered, recommend generating the fault report.
12. Tone: clear, calm, practical. Like a knowledgeable colleague guiding a field engineer.

=== FORMATTING RULES ===
- Use **bold** for key values, labels, and emphasis.
- Use ### headings for section titles (e.g. ### Step 1 — Check Voltage).
- Use numbered lists for sequential steps, bullet lists for options or findings.
- Use markdown tables for comparisons (fault categories, measurement summaries, findings).
- Do NOT use blockquote syntax (lines starting with >). It renders poorly in this interface.
- Do NOT wrap content in code blocks except for the required JSON block at the end."""


def _extract_structured_data(text: str) -> tuple[dict, list, str, str]:
    """Returns (session_update, questions, knowledge_confidence, confidence_reason)."""
    try:
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            return (
                data.get("session_update", {}),
                data.get("questions", []),
                data.get("knowledge_confidence", "high"),
                data.get("confidence_reason", ""),
            )
    except (json.JSONDecodeError, AttributeError):
        pass
    return {}, [], "high", ""


def _clean_response_text(text: str) -> str:
    cleaned = re.sub(r"```json\s*.*?```", "", text, flags=re.DOTALL)
    return cleaned.strip()


def _extract_field(snapshot: str, field_label: str) -> str:
    match = re.search(rf"{re.escape(field_label)}:\s*(.+)", snapshot)
    return match.group(1).strip() if match else ""
