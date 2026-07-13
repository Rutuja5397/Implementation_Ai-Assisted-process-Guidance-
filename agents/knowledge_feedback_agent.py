"""
AGT-09: Knowledge Feedback Agent

Analyses a completed troubleshooting session to detect knowledge gaps —
cases where the knowledge base had insufficient content to support the
diagnostic process. Also extracts reusable fault patterns from resolved
sessions for future knowledge base enrichment.

This agent is non-blocking: if it detects a gap it returns a structured
record that the Orchestrator stores in the knowledge_gaps table.

V3 enhancement: produces a fully structured gap object including
  suggested_file_to_update, suggested_section_or_node, missing_information,
  detected_by, confidence, and evidence_checked list.
"""

import json
import re
from typing import Any

from agents.base_agent import BaseAgent


# ─── Gap detection heuristics ────────────────────────────────────────────────

# Phrases in the AI conversation that suggest knowledge base coverage was poor
GAP_INDICATOR_PATTERNS = [
    r"not found in the knowledge base",
    r"no procedure found",
    r"consult the manufacturer",
    r"refer to.*OEM",
    r"knowledge base does not contain",
    r"I don't have specific.*information",
    r"no specific.*data.*available",
    r"recommend.*consulting.*documentation",
    r"unable to find.*specifications",
    r"no reference.*values.*found",
]

# Phrases that indicate a session was rich in knowledge
COVERAGE_POSITIVE_PATTERNS = [
    r"according to.*specification",
    r"per.*EN\s*\d+",
    r"per.*IEC\s*\d+",
    r"the.*manual.*states",
    r"reference value",
    r"within.*normal range",
    r"tolerance",
]

GAP_TYPES = {
    "no_procedure":              "No procedure steps found for this component/fault type.",
    "no_specs":                  "No technical specifications or reference values available.",
    "unresolved":                "Session ended without identifying a probable cause.",
    "low_coverage":              "General low knowledge base coverage detected for this scenario.",
    "missing_manual_info":       "Manual information for this fault mode is absent.",
    "missing_troubleshooting_step": "A specific troubleshooting step is missing from the knowledge base.",
    "outdated_knowledge":        "Knowledge base content appears outdated for this component.",
    "missing_threshold":         "Measurement thresholds or tolerance values are missing.",
    "unknown_fault":             "Fault pattern is completely unknown to the knowledge base.",
}

# Component → knowledge file mapping (mirrors rag_system.COMPONENT_FILE_MAP)
COMPONENT_FILE_MAP = {
    "hoist motor":              "hoist_motor.txt",
    "hoist brake":              "hoist_brake.txt",
    "wire rope":                "wire_rope.txt",
    "hook block":               "hook_block.txt",
    "trolley motor":            "trolley_bridge_motor.txt",
    "bridge motor":             "trolley_bridge_motor.txt",
    "gearbox":                  "gearbox.txt",
    "limit switch":             "limit_switch.txt",
    "control system":           "control_system.txt",
    "power supply":             "power_supply.txt",
}

# Section headers that map to gap types — used to suggest where to add content
SECTION_FOR_GAP_TYPE = {
    "no_procedure":              "=== DIAGNOSTIC PROCEDURE ===",
    "missing_troubleshooting_step": "=== DIAGNOSTIC PROCEDURE ===",
    "no_specs":                  "=== SPECIFICATIONS AND THRESHOLDS ===",
    "missing_threshold":         "=== SPECIFICATIONS AND THRESHOLDS ===",
    "unresolved":                "=== COMMON FAILURE MODES ===",
    "unknown_fault":             "=== COMMON FAILURE MODES ===",
    "missing_manual_info":       "=== OVERVIEW ===",
    "outdated_knowledge":        "=== OVERVIEW ===",
    "low_coverage":              "=== COMMON FAILURE MODES ===",
}


class KnowledgeFeedbackAgent(BaseAgent):
    AGT_ID = "AGT-09"

    def _execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Input keys:
          component_key:         str
          problem_description:   str
          conversation_history:  list[{role, content}]   (full transcript)
          lifecycle_state:       str
          knowledge_gap_indicator: bool  (from RetrievalAgent at session open)
          retrieval_chunk_count: int     (how many chunks were found at open)
          retrieved_evidence:    list[dict]  (evidence chunks used in session)
          session_resolved:      bool    (True if PROBABLE_CAUSE_IDENTIFIED or RESOLVED)
          current_hypothesis:    str | None
          completed_steps_count: int

        Output:
          gap_detected:               bool
          gap_type:                   str | None
          gap_description:            str | None
          suggested_action:           str | None
          fault_pattern:              str | None
          coverage_score:             float
          detected_by:                str
          missing_information:        str | None
          affected_asset_type:        str | None
          suggested_file_to_update:   str | None
          suggested_section_or_node:  str | None
          evidence_checked:           list[str]
          confidence:                 float
        """
        component          : str  = payload.get("component_key", "")
        problem            : str  = payload.get("problem_description", "")
        history            : list = payload.get("conversation_history", [])
        lifecycle_state    : str  = payload.get("lifecycle_state", "")
        kb_gap_flag        : bool = payload.get("knowledge_gap_indicator", False)
        chunk_count = payload.get("retrieval_chunk_count")  # None = not measured at report time
        evidence           : list = payload.get("retrieved_evidence", [])
        resolved           : bool = payload.get("session_resolved", False)
        hypothesis         : str  = payload.get("current_hypothesis") or ""
        steps_count        : int  = payload.get("completed_steps_count", 0)

        # Concatenate AI-generated messages for pattern matching
        ai_text = " ".join(
            m.get("content", "")
            for m in history
            if m.get("role") == "assistant"
        )

        gap_indicators = _count_pattern_matches(ai_text, GAP_INDICATOR_PATTERNS)
        coverage_positives = _count_pattern_matches(ai_text, COVERAGE_POSITIVE_PATTERNS)

        # Coverage score: ratio of positive signals vs total diagnostic turns
        ai_turn_count = max(1, sum(1 for m in history if m.get("role") == "assistant"))
        coverage_score = min(1.0, coverage_positives / (ai_turn_count + gap_indicators + 1))

        # ── Determine gap type ────────────────────────────────────────────────
        gap_type      = None
        gap_desc      = None
        suggested_act = None
        missing_info  = None
        confidence    = 0.0

        if lifecycle_state in ("UNRESOLVED", "ESCALATED") and steps_count < 3:
            gap_type     = "unresolved"
            gap_desc     = GAP_TYPES["unresolved"]
            missing_info = (
                f"No root cause identified for '{component}' — '{problem[:120]}'. "
                "The knowledge base may be missing this fault pattern or similar case studies."
            )
            suggested_act = (
                f"Add troubleshooting content for '{component}' — '{problem[:100]}'. "
                "Consider adding a case study from this session to the knowledge base."
            )
            confidence = 0.85

        elif kb_gap_flag or (chunk_count is not None and chunk_count == 0):
            gap_type     = "no_specs"
            gap_desc     = GAP_TYPES["no_specs"]
            missing_info = (
                f"No knowledge base content found for component '{component}'. "
                "Technical specifications, operating thresholds, and diagnostic procedures "
                "are completely missing."
            )
            suggested_act = (
                f"Create a new knowledge file for '{component}' with technical specifications, "
                "operating limits, and step-by-step diagnostic procedures."
            )
            confidence = 0.95

        elif gap_indicators >= 2:
            gap_type     = "no_procedure"
            gap_desc     = GAP_TYPES["no_procedure"]
            missing_info = (
                f"The AI was unable to provide step-by-step diagnostic guidance for "
                f"'{component}' / '{problem[:100]}'. Procedure content is absent."
            )
            suggested_act = (
                f"Expand knowledge base entries for '{component}' with detailed "
                "step-by-step diagnostic procedures for this fault pattern."
            )
            confidence = 0.75

        elif coverage_score < 0.25:
            gap_type     = "low_coverage"
            gap_desc     = GAP_TYPES["low_coverage"]
            missing_info = (
                f"General knowledge coverage for '{component}' appears insufficient. "
                "The AI referenced few specification values or manual sections."
            )
            suggested_act = (
                f"Review and enrich knowledge base content for '{component}'. "
                "Coverage appears insufficient based on AI responses in this session."
            )
            confidence = 0.55

        gap_detected = gap_type is not None

        # ── Derive file and section to update ────────────────────────────────
        component_lower = component.lower()
        suggested_file = COMPONENT_FILE_MAP.get(component_lower)
        if not suggested_file:
            # Fuzzy: find best partial match
            for key, fname in COMPONENT_FILE_MAP.items():
                if key in component_lower or component_lower in key:
                    suggested_file = fname
                    break
            else:
                suggested_file = "general_procedures.txt"

        suggested_section = SECTION_FOR_GAP_TYPE.get(gap_type or "", "=== COMMON FAILURE MODES ===")

        # ── Build evidence_checked list ───────────────────────────────────────
        evidence_ids = [
            e.get("source", e.get("id", ""))
            for e in evidence
            if e.get("source") or e.get("id")
        ]
        # Deduplicate preserving order
        seen: set = set()
        unique_evidence: list = []
        for eid in evidence_ids:
            if eid not in seen:
                seen.add(eid)
                unique_evidence.append(eid)

        # ── Build fault pattern description for KB enrichment ─────────────────
        fault_pattern = None
        if resolved and hypothesis:
            fault_pattern = (
                f"Component: {component} | "
                f"Problem: {problem[:100]} | "
                f"Root cause: {hypothesis[:150]}"
            )

        return {
            "gap_detected":               gap_detected,
            "gap_type":                   gap_type,
            "gap_description":            gap_desc,
            "suggested_action":           suggested_act,
            "fault_pattern":              fault_pattern,
            "coverage_score":             round(coverage_score, 3),
            # V3 structured fields
            "detected_by":                "diagnostic_agent",
            "missing_information":        missing_info,
            "affected_asset_type":        component,
            "suggested_file_to_update":   suggested_file,
            "suggested_section_or_node":  suggested_section,
            "evidence_checked":           unique_evidence,
            "confidence":                 round(confidence, 2),
        }


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _count_pattern_matches(text: str, patterns: list[str]) -> int:
    count = 0
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            count += 1
    return count
