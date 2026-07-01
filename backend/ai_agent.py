"""
AI Agent: uses Claude (via Anthropic API) with RAG context to guide
crane maintenance engineers through structured troubleshooting.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional

import anthropic

from backend.rag_system import RAGSystem

logger = logging.getLogger(__name__)

# Singleton RAG system (initialised once per process)
_rag: Optional[RAGSystem] = None


def get_rag() -> RAGSystem:
    global _rag
    if _rag is None:
        _rag = RAGSystem()
        _rag.initialize()
    return _rag


# ─── System prompt builder ────────────────────────────────────────────────────

def build_system_prompt(
    crane_type: str,
    component: str,
    problem_description: str,
    environment: Optional[str],
    recent_changes: Optional[str],
    error_messages: Optional[str],
    rag_chunks: List[Dict[str, Any]],
    measurements: List[Dict[str, Any]],
    completed_steps: Optional[str],
    likely_causes: Optional[str],
) -> str:

    # Format RAG evidence
    rag_section = ""
    if rag_chunks:
        rag_section = "\n\n=== RETRIEVED TECHNICAL KNOWLEDGE ===\n"
        for i, chunk in enumerate(rag_chunks, 1):
            rag_section += (
                f"\n[Source {i}: {chunk['component']} – {chunk['source']}]\n"
                f"{chunk['content']}\n"
            )

    # Format measurements
    meas_section = ""
    if measurements:
        meas_section = "\n\n=== RECORDED MEASUREMENTS ===\n"
        for m in measurements:
            parts = []
            if m.get("voltage") is not None:
                parts.append(f"Voltage: {m['voltage']} V")
            if m.get("current") is not None:
                parts.append(f"Current: {m['current']} A")
            if m.get("temperature") is not None:
                parts.append(f"Temperature: {m['temperature']} °C")
            if m.get("load") is not None:
                parts.append(f"Load: {m['load']} kg")
            if m.get("brake_gap") is not None:
                parts.append(f"Brake Gap: {m['brake_gap']} mm")
            if m.get("insulation_resistance") is not None:
                parts.append(f"Insulation Resistance: {m['insulation_resistance']} MΩ")
            if m.get("vibration") is not None:
                parts.append(f"Vibration: {m['vibration']} mm/s RMS")
            if m.get("notes"):
                parts.append(f"Notes: {m['notes']}")
            if parts:
                meas_section += f"  • {', '.join(parts)}\n"

    # Format progress
    progress_section = ""
    if completed_steps:
        try:
            steps = json.loads(completed_steps)
            if steps:
                progress_section = "\n\n=== COMPLETED DIAGNOSTIC STEPS ===\n"
                for step in steps:
                    progress_section += f"  ✓ {step}\n"
        except (json.JSONDecodeError, TypeError):
            pass

    likely_section = ""
    if likely_causes:
        try:
            causes = json.loads(likely_causes)
            if causes:
                likely_section = "\n\n=== CURRENT WORKING HYPOTHESES ===\n"
                for cause in causes:
                    likely_section += f"  • {cause}\n"
        except (json.JSONDecodeError, TypeError):
            pass

    system_prompt = f"""You are an expert crane maintenance AI assistant integrated into an industrial troubleshooting system. Your role is to guide qualified engineers through systematic, evidence-based diagnosis of crane faults.

=== CURRENT SESSION CONTEXT (DO NOT RE-ASK THESE BASICS) ===
Crane:              {crane_type}
Component:          {component}
Reported Problem:   {problem_description}
Environment:        {environment or 'Not specified'}
Recent Changes:     {recent_changes or 'None reported'}
Error Messages:     {error_messages or 'None reported'}
{rag_section}
{meas_section}
{progress_section}
{likely_section}

=== YOUR BEHAVIOUR RULES ===

1. **DO NOT ask questions already answered above.** The engineer has provided the context above - respect their time.
2. **Start at the right diagnostic depth.** You know the crane, component, and problem - skip generic questions and ask targeted, specific diagnostic questions.
3. **Be systematic.** Follow a logical troubleshooting sequence: most likely causes first, safety checks before invasive tests.
4. **Interpret measurements immediately.** When the engineer provides voltage, current, temperature, etc., compare against the reference values in the retrieved knowledge and state whether they are normal, warning, or fault-level.
5. **Reference technical knowledge.** When you recommend a check, reference the relevant specification from the retrieved knowledge (e.g., "The hoist brake air gap should be 0.2–0.3 mm per the Demag specification").
6. **Prioritise safety.** Always flag safety-critical issues immediately. If you detect a situation where crane operation could be dangerous, state this clearly and recommend immediate shutdown.
7. **You MUST call the `submit_diagnostic_data` tool in every response.** Write your prose explanation first, then call the tool with the structured data. The tool captures the questions the engineer must answer — do NOT write questions in your prose.
8. **Guide toward diagnosis.** Explain the diagnostic logic clearly in prose (2–4 sentences). Each question in the tool call should serve a clear purpose.
9. **When sufficient data is collected**, synthesise a diagnosis and recommend the `generate_report` action to the engineer.
10. **Tone:** Professional, precise, technical. This is an industrial setting, not a general chatbot.

Begin your diagnostic sequence now based on the component and problem described above."""

    return system_prompt


# ─── Tool definition (structured output via tool_use) ────────────────────────

DIAGNOSTIC_TOOL = {
    "name": "submit_diagnostic_data",
    "description": (
        "Submit structured diagnostic data for this troubleshooting step. "
        "Call this ONCE per response with the questions for the engineer and the session state update."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "session_update": {
                "type": "object",
                "properties": {
                    "completed_steps": {"type": "array", "items": {"type": "string"}},
                    "likely_causes":   {"type": "array", "items": {"type": "string"}},
                    "current_hypothesis": {"type": "string"},
                },
                "required": ["completed_steps", "likely_causes", "current_hypothesis"],
            },
            "questions": {
                "type": "array",
                "description": "Structured questions for the engineer to answer via form widgets.",
                "items": {
                    "type": "object",
                    "properties": {
                        "text":    {"type": "string", "description": "The question text"},
                        "type":    {"type": "string", "enum": ["yesno", "number", "choice", "text"]},
                        "unit":    {"type": "string", "description": "Unit for number questions, e.g. V, A, mm"},
                        "options": {"type": "array", "items": {"type": "string"},
                                    "description": "Options list for choice questions"},
                    },
                    "required": ["text", "type"],
                },
            },
            "knowledge_confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "high=KB covers this step directly; medium=partial; low=not covered",
            },
            "confidence_reason": {
                "type": "string",
                "description": "If low confidence, describe what is missing from the knowledge base.",
            },
        },
        "required": ["session_update", "questions", "knowledge_confidence"],
    },
}


# ─── Main AI function ─────────────────────────────────────────────────────────

def get_ai_response(
    session_data: Dict[str, Any],
    conversation_history: List[Dict[str, str]],
    new_user_message: str,
    measurements: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Get AI response for a user message in a troubleshooting session.

    Returns:
        {
            "response_text": str,
            "session_update": dict,   # parsed from AI output
            "retrieved_evidence": list
        }
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    # Build search query from context + new message
    search_query = (
        f"{session_data['component']} {session_data['problem_description']} "
        f"{new_user_message}"
    )

    # Retrieve relevant knowledge
    rag = get_rag()
    evidence = rag.retrieve(
        query=search_query,
        component=session_data.get("component"),
        n_results=8,
    )

    # Build system prompt
    system_prompt = build_system_prompt(
        crane_type=session_data["crane_type"],
        component=session_data["component"],
        problem_description=session_data["problem_description"],
        environment=session_data.get("environment"),
        recent_changes=session_data.get("recent_changes"),
        error_messages=session_data.get("error_messages"),
        rag_chunks=evidence,
        measurements=measurements,
        completed_steps=session_data.get("completed_steps"),
        likely_causes=session_data.get("likely_causes"),
    )

    # Build messages list for Claude
    messages = []

    # Include existing conversation history
    for msg in conversation_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add new user message
    messages.append({"role": "user", "content": new_user_message})

    # Call Claude API
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        temperature=0.2,
        system=system_prompt,
        messages=messages,
        tools=[DIAGNOSTIC_TOOL],
        tool_choice={"type": "any"},
    )

    display_text, session_update, questions, confidence, confidence_reason = _parse_tool_response(response)

    return {
        "response_text": display_text,
        "session_update": session_update,
        "questions": questions,
        "knowledge_confidence": confidence,
        "confidence_reason": confidence_reason,
        "retrieved_evidence": evidence,
    }


def generate_opening_message(session_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate the first AI message after the intake form is submitted.
    The AI should NOT ask basic questions – it should jump into diagnostics.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    search_query = (
        f"{session_data['component']} {session_data['problem_description']} "
        f"diagnostic troubleshooting"
    )

    rag = get_rag()
    evidence = rag.retrieve(
        query=search_query,
        component=session_data.get("component"),
        n_results=8,
    )

    system_prompt = build_system_prompt(
        crane_type=session_data["crane_type"],
        component=session_data["component"],
        problem_description=session_data["problem_description"],
        environment=session_data.get("environment"),
        recent_changes=session_data.get("recent_changes"),
        error_messages=session_data.get("error_messages"),
        rag_chunks=evidence,
        measurements=[],
        completed_steps=None,
        likely_causes=None,
    )

    opening_request = (
        f"A new troubleshooting session has started. "
        f"The engineer has reported a problem with the {session_data['component']} "
        f"on a {session_data['crane_type']}: \"{session_data['problem_description']}\". "
        f"Begin the diagnostic sequence. Acknowledge what you know from the intake form, "
        f"summarise the likely fault categories for this component and problem, "
        f"then ask your FIRST targeted diagnostic question."
    )

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        temperature=0.2,
        system=system_prompt,
        messages=[{"role": "user", "content": opening_request}],
        tools=[DIAGNOSTIC_TOOL],
        tool_choice={"type": "any"},
    )

    display_text, session_update, questions, confidence, confidence_reason = _parse_tool_response(response)

    return {
        "response_text": display_text,
        "session_update": session_update,
        "questions": questions,
        "knowledge_confidence": confidence,
        "confidence_reason": confidence_reason,
        "retrieved_evidence": evidence,
    }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_tool_response(response):
    """Parse a Claude response that uses tool_use.
    Returns (display_text, session_update, questions, confidence, confidence_reason).
    """
    display_text = ""
    session_update = {}
    questions = []
    confidence = "high"
    confidence_reason = ""

    for block in response.content:
        if block.type == "text":
            display_text += block.text
        elif block.type == "tool_use" and block.name == "submit_diagnostic_data":
            data = block.input
            session_update    = data.get("session_update", {})
            questions         = data.get("questions", [])
            confidence        = data.get("knowledge_confidence", "high")
            confidence_reason = data.get("confidence_reason", "")

    return display_text.strip(), session_update, questions, confidence, confidence_reason
