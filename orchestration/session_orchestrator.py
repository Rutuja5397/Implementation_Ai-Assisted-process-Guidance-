"""
AGT-01: Session Orchestrator

The central coordinator of the multi-agent pipeline. All three main
workflows delegate to specialised agents in sequence:

  handle_session_start()  →  IntakeAgent → RetrievalAgent → DiagnosticAgent → SafetyAgent
  handle_chat_turn()      →  RetrievalAgent → ParameterAgent → DiagnosticAgent → SafetyAgent
  handle_report_request() →  ReportGenerationAgent → KnowledgeFeedbackAgent

The Orchestrator:
  - wires agent input/output contracts together
  - does NOT access the database itself (caller is responsible for persistence)
  - propagates AgentError exceptions so callers can decide how to degrade gracefully
  - attaches agent metadata to every result for observability
"""

import json
import logging
from typing import Any, Optional

from agents.intake_agent              import IntakeAgent as IntakeProcessingAgent
from agents.retrieval_agent           import RetrievalAgent
from agents.parameter_agent           import ParameterInterpretationAgent
from agents.diagnostic_agent          import DiagnosticReasoningAgent
from agents.safety_agent              import SafetyGuardrailAgent
from agents.report_agent              import ReportGenerationAgent
from agents.knowledge_feedback_agent  import KnowledgeFeedbackAgent
from agents.procedure_agent           import ProcedureGuidanceAgent
from agents.base_agent                import AgentError

logger = logging.getLogger(__name__)

VERSION = "1.0.0"


class SessionOrchestrator:
    """
    AGT-01: Session Orchestrator.
    Instantiated once per request (stateless across calls).
    """

    def __init__(self):
        self._intake     = IntakeProcessingAgent()
        self._retrieval  = RetrievalAgent()
        self._parameter  = ParameterInterpretationAgent()
        self._diagnostic = DiagnosticReasoningAgent()
        self._safety     = SafetyGuardrailAgent()
        self._report     = ReportGenerationAgent()
        self._feedback   = KnowledgeFeedbackAgent()
        self._procedure  = ProcedureGuidanceAgent()

    # ─── Public Pipelines ────────────────────────────────────────────────────

    def handle_session_start(
        self,
        intake_form: dict[str, Any],
        user_role:   str = "ME",
    ) -> dict[str, Any]:
        """
        Pipeline: intake → retrieval → diagnostic (opening turn) → safety

        Parameters
        ----------
        intake_form : raw form fields (crane_type, component, problem_description, ...)
        user_role   : "ME" | "SME"

        Returns
        -------
        {
          response_text:         str,
          session_update:        dict,
          retrieved_evidence:    list,
          knowledge_gap_indicator: bool,
          component_key:         str,
          context_snapshot:      str,
          safety_flag:           bool,
          safety_level:          str,
          safety_message:        str | None,
          agent_metadata:        dict,
          tokens_used:           dict,
        }
        """
        metadata: dict[str, Any] = {}

        # ── AGT-02: Intake ────────────────────────────────────────────────
        intake_result = self._intake.run(intake_form)
        metadata["AGT-02"] = {"valid": intake_result.get("valid")}

        if not intake_result.get("valid"):
            return _error_response(
                f"Intake validation failed: {intake_result.get('errors')}",
                metadata,
            )

        component_key    : str  = intake_result["component_key"]
        context_snapshot : str  = intake_result["context_snapshot"]

        # ── AGT-03: Retrieval ─────────────────────────────────────────────
        query_terms = (
            f"{component_key} {intake_form.get('problem_description', '')} "
            "diagnostic troubleshooting fault"
        )
        retrieval_result = self._retrieval.run({
            "component_key": component_key,
            "query_terms":   query_terms,
        })
        chunks   = retrieval_result.get("evidence_chunks", [])
        kb_gap   = retrieval_result.get("knowledge_gap_indicator", False)
        metadata["AGT-03"] = retrieval_result.get("retrieval_metadata", {})

        evidence_text = _format_evidence_text(chunks)

        # ── AGT-04: Diagnostic (opening turn) ─────────────────────────────
        try:
            diag_result = self._diagnostic.run({
                "context_snapshot":     context_snapshot,
                "evidence_text":        evidence_text,
                "measurement_text":     "",
                "conversation_history": [],
                "new_user_message":     "",
                "session_state":        {},
                "user_role":            user_role,
                "is_opening_turn":      True,
            })
        except AgentError as exc:
            logger.error(f"[AGT-01] DiagnosticAgent failed on session start: {exc}")
            return _error_response(str(exc), metadata)

        metadata["AGT-04"] = {"tokens": diag_result.get("tokens_used", {})}

        # ── AGT-07: Safety ────────────────────────────────────────────────
        safety_result = self._safety.run({
            "response_text":             diag_result["response_text"],
            "has_critical_measurements": False,
            "component_key":             component_key,
        })
        metadata["AGT-07"] = {
            "safety_flag":  safety_result["safety_flag"],
            "safety_level": safety_result["safety_level"],
        }

        return {
            "response_text":          safety_result["modified_response"],
            "session_update":         diag_result.get("session_update", {}),
            "retrieved_evidence":     chunks,
            "knowledge_gap_indicator": kb_gap,
            "component_key":          component_key,
            "context_snapshot":       context_snapshot,
            "safety_flag":            safety_result["safety_flag"],
            "safety_level":           safety_result["safety_level"],
            "safety_message":         safety_result.get("safety_message"),
            "agent_metadata":         metadata,
            "tokens_used":            diag_result.get("tokens_used", {}),
        }

    # ─────────────────────────────────────────────────────────────────────────

    def handle_chat_turn(
        self,
        session_data:         dict[str, Any],
        conversation_history: list[dict],
        new_user_message:     str,
        measurements:         list[dict],
        user_role:            str = "ME",
    ) -> dict[str, Any]:
        """
        Pipeline: retrieval → parameter → diagnostic → safety

        Parameters
        ----------
        session_data         : {crane_type, component, problem_description,
                                environment, recent_changes, error_messages,
                                completed_steps (JSON str), likely_causes (JSON str),
                                current_hypothesis (str)}
        conversation_history : list of {role, content}
        new_user_message     : latest engineer message
        measurements         : raw measurement rows from DB
        user_role            : "ME" | "SME"

        Returns
        -------
        {
          response_text:       str,
          session_update:      dict,
          retrieved_evidence:  list,
          has_critical:        bool,
          annotated_measurements: list,
          safety_flag:         bool,
          safety_level:        str,
          safety_message:      str | None,
          agent_metadata:      dict,
          tokens_used:         dict,
        }
        """
        metadata: dict[str, Any] = {}
        component_key = session_data.get("component", "")

        # Build intake context snapshot for the system prompt
        context_snapshot = _build_context_snapshot(session_data)

        # ── AGT-03: Retrieval ─────────────────────────────────────────────
        query_terms = (
            f"{component_key} "
            f"{session_data.get('problem_description', '')} "
            f"{new_user_message}"
        )
        retrieval_result = self._retrieval.run({
            "component_key": component_key,
            "query_terms":   query_terms,
        })
        chunks = retrieval_result.get("evidence_chunks", [])
        metadata["AGT-03"] = retrieval_result.get("retrieval_metadata", {})
        evidence_text = _format_evidence_text(chunks)

        # ── AGT-05: Parameter Interpretation ─────────────────────────────
        param_result = self._parameter.run({
            "component_key": component_key,
            "measurements":  measurements,
        })
        has_critical  = param_result.get("has_critical", False)
        measurement_text = param_result.get("summary_text", "")
        metadata["AGT-05"] = {"has_critical": has_critical}

        # ── AGT-04: Diagnostic ────────────────────────────────────────────
        session_state = {
            "completed_steps":  _parse_json_list(session_data.get("completed_steps")),
            "likely_causes":    _parse_json_list(session_data.get("likely_causes")),
            "current_hypothesis": session_data.get("current_hypothesis") or "",
        }
        try:
            diag_result = self._diagnostic.run({
                "context_snapshot":     context_snapshot,
                "evidence_text":        evidence_text,
                "measurement_text":     measurement_text,
                "conversation_history": conversation_history,
                "new_user_message":     new_user_message,
                "session_state":        session_state,
                "user_role":            user_role,
                "is_opening_turn":      False,
            })
        except AgentError as exc:
            logger.error(f"[AGT-01] DiagnosticAgent failed on chat turn: {exc}")
            return _error_response(str(exc), metadata)

        metadata["AGT-04"] = {"tokens": diag_result.get("tokens_used", {})}

        # ── AGT-07: Safety ────────────────────────────────────────────────
        safety_result = self._safety.run({
            "response_text":             diag_result["response_text"],
            "has_critical_measurements": has_critical,
            "component_key":             component_key,
        })
        metadata["AGT-07"] = {
            "safety_flag":  safety_result["safety_flag"],
            "safety_level": safety_result["safety_level"],
        }

        return {
            "response_text":           safety_result["modified_response"],
            "session_update":          diag_result.get("session_update", {}),
            "retrieved_evidence":      chunks,
            "has_critical":            has_critical,
            "annotated_measurements":  param_result.get("annotated_measurements", []),
            "safety_flag":             safety_result["safety_flag"],
            "safety_level":            safety_result["safety_level"],
            "safety_message":          safety_result.get("safety_message"),
            "agent_metadata":          metadata,
            "tokens_used":             diag_result.get("tokens_used", {}),
        }

    # ─────────────────────────────────────────────────────────────────────────

    def handle_report_request(
        self,
        session_data:         dict[str, Any],
        conversation_history: list[dict],
        measurements:         list[dict],
        lifecycle_state:      str,
        session_resolved:     bool = False,
    ) -> dict[str, Any]:
        """
        Pipeline: ReportGenerationAgent → KnowledgeFeedbackAgent

        Parameters
        ----------
        session_data         : session fields dict
        conversation_history : full message list {role, content}
        measurements         : raw measurement rows from DB
        lifecycle_state      : current FaultLifecycleState value
        session_resolved     : True if PROBABLE_CAUSE_IDENTIFIED or RESOLVED

        Returns
        -------
        {
          report_data:       dict   (structured report — Orchestrator caller persists)
          measurements_summary: str
          generation_ok:     bool
          gap_detected:      bool
          gap_record:        dict | None
          agent_metadata:    dict,
          tokens_used:       dict,
        }
        """
        metadata: dict[str, Any] = {}
        component_key = session_data.get("component", "")

        # ── AGT-08: Report Generation ─────────────────────────────────────
        try:
            report_result = self._report.run({
                "crane_type":           session_data.get("crane_type", ""),
                "component":            component_key,
                "problem_description":  session_data.get("problem_description", ""),
                "environment":          session_data.get("environment"),
                "recent_changes":       session_data.get("recent_changes"),
                "error_messages":       session_data.get("error_messages"),
                "conversation_history": conversation_history,
                "measurements":         measurements,
                "current_hypothesis":   session_data.get("current_hypothesis"),
                "lifecycle_state":      lifecycle_state,
            })
        except AgentError as exc:
            logger.error(f"[AGT-01] ReportAgent failed: {exc}")
            return _error_response(str(exc), metadata)

        metadata["AGT-08"] = {
            "generation_ok": report_result.get("generation_ok"),
            "tokens":        report_result.get("tokens_used", {}),
        }

        # ── AGT-09: Knowledge Feedback ────────────────────────────────────
        steps = _parse_json_list(session_data.get("completed_steps"))
        feedback_result = self._feedback.run({
            "component_key":          component_key,
            "problem_description":    session_data.get("problem_description", ""),
            "conversation_history":   conversation_history,
            "lifecycle_state":        lifecycle_state,
            "knowledge_gap_indicator": False,
            "retrieval_chunk_count":  0,
            "retrieved_evidence":     [],   # full evidence list not replayed at report time
            "session_resolved":       session_resolved,
            "current_hypothesis":     session_data.get("current_hypothesis"),
            "completed_steps_count":  len(steps),
        })
        metadata["AGT-09"] = {
            "gap_detected":   feedback_result.get("gap_detected"),
            "gap_type":       feedback_result.get("gap_type"),
            "coverage_score": feedback_result.get("coverage_score"),
        }

        gap_record = None
        if feedback_result.get("gap_detected"):
            gap_record = {
                "component_key":              component_key,
                "fault_pattern":              feedback_result.get("fault_pattern") or session_data.get("problem_description", "")[:200],
                "gap_type":                   feedback_result.get("gap_type"),
                "suggested_action":           feedback_result.get("suggested_action"),
                # V3 structured fields
                "detected_by":                feedback_result.get("detected_by", "diagnostic_agent"),
                "missing_information":        feedback_result.get("missing_information"),
                "affected_asset_type":        feedback_result.get("affected_asset_type", component_key),
                "suggested_file_to_update":   feedback_result.get("suggested_file_to_update"),
                "suggested_section_or_node":  feedback_result.get("suggested_section_or_node"),
                "evidence_checked":           feedback_result.get("evidence_checked", []),
                "confidence":                 feedback_result.get("confidence", 0.0),
            }

        return {
            "report_data":         report_result.get("report_data", {}),
            "measurements_summary": report_result.get("measurements_summary", ""),
            "generation_ok":       report_result.get("generation_ok", False),
            "gap_detected":        feedback_result.get("gap_detected", False),
            "gap_record":          gap_record,
            "agent_metadata":      metadata,
            "tokens_used":         report_result.get("tokens_used", {}),
        }

    # ─────────────────────────────────────────────────────────────────────────

    def get_procedure(
        self,
        component_key:   str,
        procedure_type:  str,
    ) -> dict[str, Any]:
        """
        Thin wrapper: delegates directly to ProcedureGuidanceAgent (AGT-06).
        Used by the optional /procedure endpoint.
        """
        return self._procedure.run({
            "component_key":  component_key,
            "procedure_type": procedure_type,
        })


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _format_evidence_text(chunks: list[dict]) -> str:
    if not chunks:
        return ""
    lines = ["\n=== RETRIEVED TECHNICAL KNOWLEDGE ==="]
    for i, chunk in enumerate(chunks, 1):
        lines.append(
            f"\n[Source {i}: {chunk.get('component', 'Unknown')} — {chunk.get('source', '')}]\n"
            f"{chunk.get('content', '')}"
        )
    return "\n".join(lines)


def _build_context_snapshot(session_data: dict) -> str:
    """Rebuild context_snapshot from session_data dict (used in chat turns)."""
    return (
        f"Crane Type: {session_data.get('crane_type', 'Unknown')}\n"
        f"Affected Component: {session_data.get('component', 'Unknown')}\n"
        f"Reported Problem: {session_data.get('problem_description', '')}\n"
        f"Environment: {session_data.get('environment') or 'Not specified'}\n"
        f"Recent Changes: {session_data.get('recent_changes') or 'None reported'}\n"
        f"Error Messages: {session_data.get('error_messages') or 'None reported'}"
    )


def _parse_json_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            result = json.loads(value)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, TypeError):
            pass
    return []


def _error_response(message: str, metadata: dict) -> dict:
    return {
        "response_text":          f"AI service error: {message}",
        "session_update":         {},
        "retrieved_evidence":     [],
        "knowledge_gap_indicator": False,
        "component_key":          "",
        "context_snapshot":       "",
        "safety_flag":            False,
        "safety_level":           "none",
        "safety_message":         None,
        "report_data":            {},
        "generation_ok":          False,
        "gap_detected":           False,
        "gap_record":             None,
        "agent_metadata":         {**metadata, "error": message},
        "tokens_used":            {},
    }
