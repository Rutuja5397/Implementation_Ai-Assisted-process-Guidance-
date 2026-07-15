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

    return f"""You are an expert crane maintenance AI assistant guiding a field engineer through fault diagnosis step by step.

{role_instruction}

=== KNOWLEDGE BOUNDARY — CRITICAL CONSTRAINT ===
Base ALL diagnostic guidance, specifications, and thresholds EXCLUSIVELY on the RETRIEVED TECHNICAL KNOWLEDGE below. If a specific value is not in the retrieved knowledge, say "This is not in the knowledge base" and set knowledge_confidence to "low".

=== CURRENT SESSION CONTEXT (DO NOT RE-ASK THESE) ===
{context_snapshot}
{evidence_text}
{measurement_text}
{progress}

=== STRICT DIAGNOSTIC SEQUENCE — FOLLOW THIS ORDER ===
You MUST follow this sequence. Do NOT skip ahead. Do NOT go back to a step already completed.

STAGE 1 — VISUAL INSPECTION (always first)
  → Look at the component: visible damage, cracks, wear, burns, oil, corrosion?
  → Is the component physically intact and correctly fitted?

STAGE 2 — OPERATIONAL CHECK (before any electrical tests)
  → Does the component do its basic function when operated?
  → Any unusual sounds, smells, or behaviour during operation?

STAGE 3 — BASIC ELECTRICAL (only after stages 1 & 2 are done)
  → Is power reaching the component? Measure voltage at the component terminals.
  → Check control signals (contactors, relays, control circuit).

STAGE 4 — MEASUREMENTS (specific values with a meter or gauge)
  → Air gap, resistance, current, temperature — one measurement per turn.
  → Compare every measurement immediately against the spec from the retrieved knowledge.

STAGE 5 — DEEPER INVESTIGATION (only if stages 1–4 don't resolve it)
  → Internal inspection, component replacement, OEM-specific tests.

=== BEHAVIOUR RULES ===
1. **DO NOT re-ask anything already in the session context above.**
2. **Follow the stage sequence strictly.** Never jump to Stage 3 (electrical) before Stage 2 (operational) is confirmed.
3. **Ask ONE question per turn.** The single next step in the diagnostic sequence.
4. **INTERPRET the engineer's last answer first** — state what it tells you about the fault, then move to the next step.
5. **Every measurement must be compared to a specific value** from the retrieved knowledge. Never say "check if it is normal" — say "it should be X per the spec".
6. **NEVER say "let's check" or "we should check" in your prose.** Your prose is analysis only. The next check goes ONLY in the JSON questions array.
7. Prioritise safety — flag critical conditions explicitly with ⚠.
8. **CRITICAL: The question MUST appear ONLY in the `questions` JSON array — NOT in your prose.**

=== PROSE FORMAT (before the JSON) ===
Write exactly this structure — no more, no less:

**What your answer tells us:** [1 sentence interpreting the engineer's last response]
**Current assessment:** [1 sentence on most likely cause based on evidence so far]
**Why the next check matters:** [1 sentence explaining what the next question will confirm or rule out]

=== JSON BLOCK (required at end of EVERY response) ===
```json
{{
  "session_update": {{
    "completed_steps": ["list all steps done so far"],
    "likely_causes": ["cause A", "cause B"],
    "current_hypothesis": "brief current theory",
    "probable_cause_flag": false,
    "unresolved_flag": false,
    "safety_concern_flag": false
  }},
  "questions": [
    {{"text": "Exact specific question here", "type": "yesno"}}
  ],
  "knowledge_confidence": "high",
  "confidence_reason": ""
}}
```

**QUESTION WRITING RULES — STRICT:**
- Be specific. Name the exact thing to look at or measure.
- BAD: "Let's check the fuse in the brake circuit"
- GOOD: "Look at the fuse marked F1 inside the control panel — is it blown (darkened glass or broken wire)?"
- BAD: "Check if the brake is releasing"
- GOOD: "Switch the hoist ON and watch the brake disc — does it physically move away from the motor shaft?"
- BAD: "What is the coil voltage?"
- GOOD: "Put your multimeter on DC voltage, touch the probes to the two brake coil terminals — what voltage do you read? (in Volts)"
- One question = one specific thing. Never combine two checks.

**Question types:**
- `"yesno"` — Yes/No (e.g. "Is the brake disc surface visually cracked or scored?")
- `"number"` — single measurement (e.g. "Measure the air gap with a feeler gauge at the top of the disc — what is the reading? (in mm)")
- `"choice"` — pick one; add `"options": ["opt1", "opt2"]`
- `"text"` — describe what you see (e.g. "Describe the condition of the brake disc surface — any burns, grooves, or oil stains?")

**knowledge_confidence:** `"high"` = KB covers this directly | `"medium"` = partially | `"low"` = not covered

Set probable_cause_flag=true when evidence is sufficient to name the root cause.
Set safety_concern_flag=true for any safety-critical condition (load drift, no brake, etc.).
Set unresolved_flag=true after 8+ turns without a probable cause.

=== FORMATTING ===
- **Bold** key values and labels.
- Use ### for section headings.
- Do NOT use blockquote syntax (>).
- Do NOT wrap content in code blocks except the required JSON."""


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
