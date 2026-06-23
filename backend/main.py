"""
FastAPI backend — AI-Assisted Process Guidance Tool (Version 2).
Role-based access control, fault lifecycle management, escalation,
expert annotations, knowledge gap tracking, and admin endpoints.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

load_dotenv()

from backend import models, schemas
from backend.auth import (
    authenticate_user,
    build_token_payload,
    create_access_token,
    create_user,
    get_user_by_username,
)
from backend.database import get_db, init_db
from orchestration.session_orchestrator import SessionOrchestrator
from access_control.rbac import get_current_user, require_permission, require_role
from access_control.permissions import (
    P_SESSION_CREATE, P_SESSION_READ_OWN, P_SESSION_READ_ALL,
    P_SESSION_READ_ESCALATED, P_SESSION_CHAT_OWN, P_SESSION_CHAT_ESCALATED,
    P_SESSION_MEASURE, P_SESSION_ESCALATE,
    P_SESSION_ANNOTATE, P_SESSION_VALIDATE_CAUSE, P_SESSION_FLAG_GAP,
    P_REPORT_CREATE, P_REPORT_READ_ANY, P_FOLLOW_UP_CLOSE,
    P_DASHBOARD_OWN, P_DASHBOARD_ALL, P_DASHBOARD_STATS,
    P_CRANE_HISTORY,
    P_KNOWLEDGE_GAP_READ, P_KNOWLEDGE_GAP_RESOLVE,
    P_USER_READ, P_USER_CREATE, P_USER_DEACTIVATE, P_ROLE_ASSIGN,
    P_AUDIT_LOG_READ,
    has_permission,
)
from access_control.roles import Role

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Fault lifecycle transition rules ────────────────────────────────────────

ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "LOGGED":                    ["IN_PROGRESS"],
    "IN_PROGRESS":               ["AWAITING_MEASUREMENT", "PROBABLE_CAUSE_IDENTIFIED", "UNRESOLVED", "ESCALATED"],
    "AWAITING_MEASUREMENT":      ["IN_PROGRESS"],
    "PROBABLE_CAUSE_IDENTIFIED": ["RESOLVED", "UNRESOLVED"],
    "UNRESOLVED":                ["ESCALATED", "IN_PROGRESS"],
    "ESCALATED":                 ["SME_IN_REVIEW"],
    "SME_IN_REVIEW":             ["RESOLVED", "KNOWLEDGE_GAP_FLAGGED"],
    "KNOWLEDGE_GAP_FLAGGED":     ["SME_IN_REVIEW", "IN_PROGRESS"],   # IN_PROGRESS: KE resolved gap
    "RESOLVED":                  ["CLOSED_WITH_REPORT"],
    "CLOSED_WITH_REPORT":        [],
}

TRANSITION_ALLOWED_ROLES: dict[tuple, list[str]] = {
    ("LOGGED",                    "IN_PROGRESS"):               ["ME", "SME"],
    ("IN_PROGRESS",               "AWAITING_MEASUREMENT"):      ["ME", "SME"],
    ("IN_PROGRESS",               "PROBABLE_CAUSE_IDENTIFIED"): ["ME", "SME"],
    ("IN_PROGRESS",               "UNRESOLVED"):                ["ME", "SME"],
    ("IN_PROGRESS",               "ESCALATED"):                 ["ME"],
    ("AWAITING_MEASUREMENT",      "IN_PROGRESS"):               ["ME", "SME"],
    ("PROBABLE_CAUSE_IDENTIFIED", "RESOLVED"):                  ["ME", "SME"],
    ("PROBABLE_CAUSE_IDENTIFIED", "UNRESOLVED"):                ["ME", "SME"],
    ("UNRESOLVED",                "ESCALATED"):                 ["ME"],
    ("UNRESOLVED",                "IN_PROGRESS"):               ["ME", "SME"],
    ("ESCALATED",                 "SME_IN_REVIEW"):             ["SME"],
    ("SME_IN_REVIEW",             "RESOLVED"):                  ["SME"],
    ("SME_IN_REVIEW",             "KNOWLEDGE_GAP_FLAGGED"):     ["SME"],
    ("KNOWLEDGE_GAP_FLAGGED",     "SME_IN_REVIEW"):             ["SME", "KE"],
    ("KNOWLEDGE_GAP_FLAGGED",     "IN_PROGRESS"):               ["KE"],   # KE resolved gap → ME continues
    ("RESOLVED",                  "CLOSED_WITH_REPORT"):        ["ME", "SME"],
}


# ─── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI-Assisted Process Guidance Tool",
    description=(
        "Multi-agent, role-based AI guidance system for crane maintenance engineers. "
        "Supports fault intake, RAG-grounded diagnostics, escalation, and report generation."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialised (V2 schema).")
    # Pre-initialise RAG so the first user request is not delayed by indexing
    try:
        from backend.ai_agent import get_rag
        get_rag()
        logger.info("RAG system initialised and ready.")
    except Exception as e:
        logger.warning(f"RAG pre-init failed (will retry on first request): {e}")


# ═══════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/auth/signup", response_model=schemas.Token)
def signup(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    user = create_user(db, user_data)
    token = create_access_token(build_token_payload(user))
    _write_audit(db, user.id, "signup", "user", str(user.id))
    return schemas.Token(
        access_token=token,
        token_type="bearer",
        user=schemas.UserOut.model_validate(user),
    )


@app.post("/auth/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    token = create_access_token(build_token_payload(user))
    _write_audit(db, user.id, "login", "user", str(user.id))
    return schemas.Token(
        access_token=token,
        token_type="bearer",
        user=schemas.UserOut.model_validate(user),
    )


@app.get("/auth/me", response_model=schemas.UserOut)
def get_me(current_user: models.User = Depends(get_current_user)):
    return schemas.UserOut.model_validate(current_user)


# ═══════════════════════════════════════════════════════════════════
# SESSION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/sessions", response_model=dict)
def create_session(
    intake: schemas.SessionCreate,
    current_user: models.User = Depends(require_permission(P_SESSION_CREATE)),
    db: Session = Depends(get_db),
):
    """Create a new troubleshooting session (ME and SME only)."""
    session = models.TroubleshootingSession(
        user_id=current_user.id,
        crane_type=intake.crane_type,
        component=intake.component,
        problem_description=intake.problem_description,
        environment=intake.environment,
        recent_changes=intake.recent_changes,
        error_messages=intake.error_messages,
        lifecycle_state=models.FaultLifecycleState.LOGGED,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Record LOGGED → IN_PROGRESS transition
    _record_transition(db, session, "LOGGED", "IN_PROGRESS", current_user, "Session started")
    session.lifecycle_state = models.FaultLifecycleState.IN_PROGRESS
    db.commit()

    # Generate opening AI message via orchestrator
    orchestrator = SessionOrchestrator()
    intake_form = {
        "crane_type":           intake.crane_type,
        "component":            intake.component,
        "problem_description":  intake.problem_description,
        "environment":          intake.environment,
        "recent_changes":       intake.recent_changes,
        "error_messages":       intake.error_messages,
    }
    try:
        ai_result = orchestrator.handle_session_start(
            intake_form=intake_form,
            user_role=current_user.role,
        )
        db.add(models.Message(
            session_id=session.id, role="assistant",
            content=ai_result["response_text"],
        ))
        _apply_session_update(db, session, ai_result.get("session_update", {}))
        # Store agent metadata on session
        if ai_result.get("agent_metadata"):
            session.agent_metadata = json.dumps(ai_result["agent_metadata"])
        db.commit()
        opening_message = ai_result["response_text"]
        evidence = ai_result.get("retrieved_evidence", [])
    except Exception as e:
        logger.error(f"AI opening message failed: {e}")
        opening_message = (
            f"Session created for {intake.component} on {intake.crane_type}. "
            "AI guidance unavailable — check ANTHROPIC_API_KEY."
        )
        evidence = []

    _write_audit(db, current_user.id, "session_create", "session", str(session.id))
    return {
        "session_id": session.id,
        "lifecycle_state": session.lifecycle_state,
        "opening_message": opening_message,
        "retrieved_evidence": evidence,
        "questions": ai_result.get("questions", []) if isinstance(ai_result, dict) else [],
        "knowledge_confidence": ai_result.get("knowledge_confidence", "high") if isinstance(ai_result, dict) else "high",
        "confidence_reason": ai_result.get("confidence_reason", "") if isinstance(ai_result, dict) else "",
    }


@app.get("/sessions/{session_id}", response_model=schemas.SessionOut)
def get_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id)
    _assert_session_readable(session, current_user)
    return schemas.SessionOut.model_validate(session)


@app.get("/sessions/{session_id}/messages", response_model=List[schemas.MessageOut])
def get_messages(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id)
    _assert_session_readable(session, current_user)
    return [schemas.MessageOut.model_validate(m) for m in session.messages]


@app.get("/sessions/{session_id}/measurements", response_model=List[schemas.MeasurementOut])
def get_measurements(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id)
    _assert_session_readable(session, current_user)
    return [schemas.MeasurementOut.model_validate(m) for m in session.measurements]


@app.get("/sessions/{session_id}/annotations", response_model=List[schemas.ExpertAnnotationOut])
def get_annotations(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id)
    _assert_session_readable(session, current_user)
    return [schemas.ExpertAnnotationOut.model_validate(a) for a in session.expert_annotations]


@app.get("/sessions/{session_id}/transitions", response_model=List[schemas.StateTransitionOut])
def get_transitions(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id)
    _assert_session_readable(session, current_user)
    return [schemas.StateTransitionOut.model_validate(t) for t in session.state_transitions]


# ═══════════════════════════════════════════════════════════════════
# CHAT ENDPOINT
# ═══════════════════════════════════════════════════════════════════

@app.post("/sessions/{session_id}/chat", response_model=schemas.ChatResponse)
def chat(
    session_id: int,
    request: schemas.ChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a message and receive AI guidance. Allowed for session owner (ME) and SME on escalated."""
    session = _get_session_or_404(db, session_id)
    _assert_chat_permitted(session, current_user)

    if session.lifecycle_state == models.FaultLifecycleState.CLOSED_WITH_REPORT:
        raise HTTPException(400, "Session is closed. Start a new session.")

    # Store user message
    user_msg = models.Message(session_id=session.id, role="user", content=request.message)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Build conversation history (all messages except the one just added)
    history = [
        {"role": m.role, "content": m.content}
        for m in session.messages if m.id != user_msg.id
    ]
    measurements = _build_measurements_list(session)
    session_data = _build_session_data(session)

    orchestrator = SessionOrchestrator()
    try:
        ai_result = orchestrator.handle_chat_turn(
            session_data=session_data,
            conversation_history=history,
            new_user_message=request.message,
            measurements=measurements,
            user_role=current_user.role,
        )
    except Exception as e:
        logger.error(f"AI response error: {e}")
        ai_result = {
            "response_text": f"AI service error: {e}. Check ANTHROPIC_API_KEY.",
            "session_update": {},
            "retrieved_evidence": [],
        }

    ai_msg = models.Message(
        session_id=session.id, role="assistant",
        content=ai_result["response_text"],
    )
    db.add(ai_msg)
    _apply_session_update(db, session, ai_result.get("session_update", {}))
    db.commit()
    db.refresh(ai_msg)

    return schemas.ChatResponse(
        message=schemas.MessageOut.model_validate(ai_msg),
        session_state={
            "component": session.component,
            "lifecycle_state": session.lifecycle_state,
            "current_hypothesis": session.current_hypothesis,
            "completed_steps": _parse_json_list(session.completed_steps),
            "likely_causes": _parse_json_list(session.likely_causes),
        },
        retrieved_evidence=ai_result.get("retrieved_evidence", []),
        questions=ai_result.get("questions", []),
        knowledge_confidence=ai_result.get("knowledge_confidence", "high"),
        confidence_reason=ai_result.get("confidence_reason", ""),
    )


# ═══════════════════════════════════════════════════════════════════
# KNOWN FAULT / SIMILAR SESSION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/sessions/find-similar", response_model=dict)
def find_similar_sessions(
    intake: schemas.SessionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return up to 3 previously resolved sessions with same component + crane type."""
    from sqlalchemy import and_
    matches = (
        db.query(models.TroubleshootingSession)
        .filter(
            and_(
                models.TroubleshootingSession.component == intake.component,
                models.TroubleshootingSession.crane_type == intake.crane_type,
                models.TroubleshootingSession.lifecycle_state
                    == models.FaultLifecycleState.CLOSED_WITH_REPORT,
            )
        )
        .order_by(models.TroubleshootingSession.updated_at.desc())
        .limit(3)
        .all()
    )
    results = []
    for s in matches:
        if s.report:
            r = s.report
            results.append({
                "session_id":          s.id,
                "component":           s.component,
                "crane_type":          s.crane_type,
                "problem_description": s.problem_description,
                "report_id":           r.id,
                "issue_summary":       r.issue_summary,
                "root_cause":          r.root_cause or "",
                "diagnosis":           r.diagnosis,
                "steps_taken":         r.steps_taken,
                "recommendations":     r.recommendations,
                "severity":            r.severity or "medium",
                "created_at":          r.created_at.strftime("%Y-%m-%d") if r.created_at else "",
            })
    return {"matches": results}


@app.post("/sessions/{session_id}/close-with-known-fix", response_model=dict)
def close_with_known_fix(
    session_id: int,
    payload: dict,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Close a session immediately by re-using a known fault report from a previous session."""
    session = _get_session_or_404(db, session_id)
    ref_session_id = payload.get("reference_session_id")

    # Store a single message recording this known-fix closure
    note = (
        f"Issue matched a previously resolved fault (Session #{ref_session_id}). "
        f"Fault report applied directly — no diagnostic steps required."
    )
    db.add(models.Message(session_id=session.id, role="assistant", content=note))

    # Copy report fields from the reference session's report
    ref_session = db.query(models.TroubleshootingSession).filter_by(id=ref_session_id).first()
    if ref_session and ref_session.report:
        r = ref_session.report
        report = models.Report(
            session_id=session.id,
            user_id=current_user.id,
            crane_type=session.crane_type,
            component=session.component,
            issue_summary=r.issue_summary + f" [Applied from Session #{ref_session_id}]",
            steps_taken=r.steps_taken,
            root_cause=r.root_cause,
            diagnosis=r.diagnosis,
            recommendations=r.recommendations,
            severity=r.severity,
        )
        db.add(report)

    session.lifecycle_state = models.FaultLifecycleState.CLOSED_WITH_REPORT
    _record_transition(db, session, "IN_PROGRESS", "CLOSED_WITH_REPORT",
                       current_user, f"Known fix applied from session #{ref_session_id}")
    db.commit()
    _write_audit(db, current_user.id, "known_fix_applied", "session", str(session_id))
    return {"status": "closed", "session_id": session_id}


# ═══════════════════════════════════════════════════════════════════
# MEASUREMENT ENDPOINT
# ═══════════════════════════════════════════════════════════════════

@app.post("/sessions/{session_id}/measurements", response_model=schemas.MeasurementOut)
def add_measurement(
    session_id: int,
    measurement: schemas.MeasurementCreate,
    current_user: models.User = Depends(require_permission(P_SESSION_MEASURE)),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id)
    _assert_chat_permitted(session, current_user)

    db_meas = models.Measurement(
        session_id=session.id,
        voltage=measurement.voltage,
        current=measurement.current,
        temperature=measurement.temperature,
        load=measurement.load,
        brake_gap=measurement.brake_gap,
        insulation_resistance=measurement.insulation_resistance,
        vibration=measurement.vibration,
        notes=measurement.notes,
    )
    db.add(db_meas)
    db.commit()
    db.refresh(db_meas)
    return schemas.MeasurementOut.model_validate(db_meas)


# ═══════════════════════════════════════════════════════════════════
# ESCALATION ENDPOINT
# ═══════════════════════════════════════════════════════════════════

@app.post("/sessions/{session_id}/escalate")
def escalate_session(
    session_id: int,
    body: schemas.EscalateRequest,
    current_user: models.User = Depends(require_permission(P_SESSION_ESCALATE)),
    db: Session = Depends(get_db),
):
    """Maintenance Engineer escalates a session to SME review."""
    session = _get_session_or_404(db, session_id)

    if session.user_id != current_user.id:
        raise HTTPException(403, "You can only escalate your own sessions.")

    if session.lifecycle_state not in (
        models.FaultLifecycleState.IN_PROGRESS,
        models.FaultLifecycleState.AWAITING_MEASUREMENT,
        models.FaultLifecycleState.UNRESOLVED,
        models.FaultLifecycleState.PROBABLE_CAUSE_IDENTIFIED,
    ):
        raise HTTPException(400, f"Cannot escalate from state '{session.lifecycle_state}'.")

    prev = session.lifecycle_state
    session.lifecycle_state    = models.FaultLifecycleState.ESCALATED
    session.escalation_reason  = body.reason
    session.escalated_at       = datetime.utcnow()
    _record_transition(db, session, prev, "ESCALATED", current_user, body.reason)
    db.commit()

    _write_audit(db, current_user.id, "session_escalate", "session", str(session.id),
                 {"reason": body.reason})
    return {"session_id": session.id, "lifecycle_state": session.lifecycle_state}


@app.post("/sessions/{session_id}/sme-review")
def start_sme_review(
    session_id: int,
    current_user: models.User = Depends(require_role("SME")),
    db: Session = Depends(get_db),
):
    """SME opens an escalated session for review."""
    session = _get_session_or_404(db, session_id)

    if session.lifecycle_state != models.FaultLifecycleState.ESCALATED:
        raise HTTPException(400, f"Session is not in ESCALATED state (current: {session.lifecycle_state}).")

    session.lifecycle_state = models.FaultLifecycleState.SME_IN_REVIEW
    session.escalated_to    = current_user.id
    _record_transition(db, session, "ESCALATED", "SME_IN_REVIEW", current_user, "SME opened for review")
    db.commit()

    _write_audit(db, current_user.id, "sme_review_start", "session", str(session.id))
    return {"session_id": session.id, "lifecycle_state": session.lifecycle_state}


@app.post("/sessions/{session_id}/resolve")
def resolve_session(
    session_id: int,
    current_user: models.User = Depends(require_role("SME")),
    db: Session = Depends(get_db),
):
    """SME marks a session as resolved after expert review."""
    session = _get_session_or_404(db, session_id)

    if session.lifecycle_state not in (
        models.FaultLifecycleState.SME_IN_REVIEW,
        models.FaultLifecycleState.PROBABLE_CAUSE_IDENTIFIED,
    ):
        raise HTTPException(400, f"Cannot resolve from state '{session.lifecycle_state}'.")

    prev = session.lifecycle_state
    session.lifecycle_state = models.FaultLifecycleState.RESOLVED
    _record_transition(db, session, prev, "RESOLVED", current_user, "Root cause confirmed by SME")
    db.commit()

    _write_audit(db, current_user.id, "session_resolve", "session", str(session.id))
    return {"session_id": session.id, "lifecycle_state": session.lifecycle_state}


# ═══════════════════════════════════════════════════════════════════
# EXPERT ANNOTATION ENDPOINT
# ═══════════════════════════════════════════════════════════════════

@app.post("/sessions/{session_id}/annotations", response_model=schemas.ExpertAnnotationOut)
def add_expert_annotation(
    session_id: int,
    body: schemas.ExpertAnnotationCreate,
    current_user: models.User = Depends(require_permission(P_SESSION_ANNOTATE)),
    db: Session = Depends(get_db),
):
    """SME adds a structured expert annotation to a session."""
    session = _get_session_or_404(db, session_id)

    annotation = models.ExpertAnnotation(
        session_id=session.id,
        user_id=current_user.id,
        annotation_text=body.annotation_text,
        annotation_type=body.annotation_type,
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    _write_audit(db, current_user.id, "expert_annotation", "session", str(session.id))
    return schemas.ExpertAnnotationOut.model_validate(annotation)


# ═══════════════════════════════════════════════════════════════════
# KNOWLEDGE GAP ENDPOINT
# ═══════════════════════════════════════════════════════════════════

@app.post("/sessions/{session_id}/flag-knowledge-gap")
def flag_knowledge_gap(
    session_id: int,
    current_user: models.User = Depends(require_permission(P_SESSION_FLAG_GAP)),
    db: Session = Depends(get_db),
):
    """SME flags the session as a knowledge gap case for KE review."""
    session = _get_session_or_404(db, session_id)

    if session.lifecycle_state not in (
        models.FaultLifecycleState.SME_IN_REVIEW,
        models.FaultLifecycleState.UNRESOLVED,
    ):
        raise HTTPException(400, f"Cannot flag knowledge gap from state '{session.lifecycle_state}'.")

    prev = session.lifecycle_state
    session.lifecycle_state = models.FaultLifecycleState.KNOWLEDGE_GAP_FLAGGED
    _record_transition(db, session, prev, "KNOWLEDGE_GAP_FLAGGED", current_user,
                       "Knowledge gap identified by SME")

    # Create the knowledge gap record
    gap = models.KnowledgeGap(
        session_id=session.id,
        component_key=session.component,
        fault_pattern=session.problem_description[:200],
        gap_type="no_matching_content",
        suggested_action="Review knowledge base for this component and fault pattern.",
        status="open",
    )
    db.add(gap)
    db.commit()

    _write_audit(db, current_user.id, "knowledge_gap_flagged", "session", str(session.id))
    return {
        "session_id": session.id,
        "lifecycle_state": session.lifecycle_state,
        "knowledge_gap_id": gap.id,
    }


@app.get("/procedure")
def get_procedure(
    component: str,
    procedure_type: str = "inspection",
    current_user: models.User = Depends(get_current_user),
):
    """
    Return structured step-by-step procedure for a component (AGT-06).
    Available to all authenticated users.
    """
    orchestrator = SessionOrchestrator()
    result = orchestrator.get_procedure(
        component_key=component,
        procedure_type=procedure_type,
    )
    return result


@app.get("/knowledge-gaps", response_model=List[schemas.KnowledgeGapOut])
def get_knowledge_gaps(
    include_resolved: bool = False,
    current_user: models.User = Depends(require_permission(P_KNOWLEDGE_GAP_READ)),
    db: Session = Depends(get_db),
):
    """KE and SME: view knowledge gap records (open by default)."""
    query = db.query(models.KnowledgeGap)
    if not include_resolved:
        query = query.filter(models.KnowledgeGap.status != "resolved")
    gaps = query.order_by(models.KnowledgeGap.created_at.desc()).all()
    return [schemas.KnowledgeGapOut.model_validate(g) for g in gaps]


@app.put("/knowledge-gaps/{gap_id}/resolve", response_model=schemas.KnowledgeGapOut)
def resolve_knowledge_gap(
    gap_id: int,
    body: schemas.KnowledgeGapResolveRequest,
    current_user: models.User = Depends(require_permission(P_KNOWLEDGE_GAP_RESOLVE)),
    db: Session = Depends(get_db),
):
    """
    KE resolves a knowledge gap by:
      1. Writing new content to the identified knowledge base file.
      2. Re-indexing ChromaDB so the AI immediately uses the new knowledge.
      3. Transitioning the related session from KNOWLEDGE_GAP_FLAGGED → IN_PROGRESS.
      4. Notifying the session's ME and escalating SME.
    """
    gap = db.query(models.KnowledgeGap).filter(models.KnowledgeGap.id == gap_id).first()
    if not gap:
        raise HTTPException(404, "Knowledge gap not found")
    if gap.status == "resolved":
        raise HTTPException(400, "Knowledge gap is already resolved")

    # ── 1. Locate and update the knowledge base file ──────────────────────────
    kb_path = Path(os.getenv("KNOWLEDGE_BASE_PATH", "./data/knowledge_base"))
    target_file = gap.suggested_file_to_update or "general_procedures.txt"
    target_path = kb_path / target_file

    if not target_path.exists():
        raise HTTPException(
            400,
            f"Knowledge file '{target_file}' not found at {kb_path}. "
            "Please ensure the file exists before resolving."
        )

    new_content = body.content_to_append.strip()
    section_header = body.append_to_section or gap.suggested_section_or_node or ""

    try:
        existing = target_path.read_text(encoding="utf-8")

        if section_header and section_header in existing:
            # Insert content immediately after the section header line
            lines = existing.splitlines()
            insert_at = -1
            for i, line in enumerate(lines):
                if section_header.strip() in line:
                    insert_at = i + 1
                    break
            if insert_at >= 0:
                # Find next section header to insert before it
                end_at = len(lines)
                for j in range(insert_at, len(lines)):
                    if lines[j].startswith("===") and j > insert_at:
                        end_at = j
                        break
                insert_block = (
                    f"\n\n--- ADDED BY KE ({current_user.name}, "
                    f"{datetime.utcnow().strftime('%Y-%m-%d')}) ---\n"
                    f"{new_content}\n"
                    f"--- END ADDITION ---"
                )
                lines.insert(end_at, insert_block)
                updated_text = "\n".join(lines)
            else:
                updated_text = existing + f"\n\n{_ke_block(current_user.name, new_content)}"
        else:
            # Append to end of file
            updated_text = existing + f"\n\n{_ke_block(current_user.name, new_content)}"

        target_path.write_text(updated_text, encoding="utf-8")
        logger.info(f"[KnowledgeGap #{gap_id}] Wrote to {target_path}")

    except OSError as exc:
        raise HTTPException(500, f"Failed to write knowledge file: {exc}")

    # ── 2. Re-index ChromaDB ──────────────────────────────────────────────────
    try:
        from backend.rag_system import RAGSystem
        rag = RAGSystem()
        rag.reinitialize()
        logger.info(f"[KnowledgeGap #{gap_id}] ChromaDB re-indexed after file update.")
    except Exception as exc:
        logger.error(f"[KnowledgeGap #{gap_id}] RAG re-index failed: {exc}")
        # Non-fatal: file was written; RAG will re-index on next backend restart

    # ── 3. Update gap record ──────────────────────────────────────────────────
    gap.status                  = "resolved"
    gap.resolved_by             = current_user.id
    gap.resolved_at             = datetime.utcnow()
    gap.resolution_note         = body.resolution_note
    gap.knowledge_content_added = new_content
    db.commit()

    # ── 4. Transition session KNOWLEDGE_GAP_FLAGGED → IN_PROGRESS ───────────
    session = None
    if gap.session_id:
        session = db.query(models.TroubleshootingSession).filter(
            models.TroubleshootingSession.id == gap.session_id
        ).first()
        if session and session.lifecycle_state == models.FaultLifecycleState.KNOWLEDGE_GAP_FLAGGED:
            prev = session.lifecycle_state
            session.lifecycle_state = models.FaultLifecycleState.IN_PROGRESS
            _record_transition(
                db, session, str(prev), "IN_PROGRESS", current_user,
                f"Knowledge gap #{gap_id} resolved by KE — diagnosis can continue"
            )
            db.commit()
            logger.info(f"[KnowledgeGap #{gap_id}] Session #{gap.session_id} transitioned to IN_PROGRESS")

    # ── 5. Notify relevant users ──────────────────────────────────────────────
    notified_user_ids: set = set()

    def _notify(user_id: int, msg: str):
        if user_id and user_id not in notified_user_ids:
            notified_user_ids.add(user_id)
            db.add(models.Notification(
                user_id=user_id,
                gap_id=gap.id,
                session_id=gap.session_id,
                message=msg,
            ))

    component   = gap.component_key
    gap_type_lbl = (gap.gap_type or "").replace("_", " ").title()
    notify_msg  = (
        f"Knowledge Gap #{gap.id} resolved for {component} ({gap_type_lbl}). "
        f"The knowledge base has been updated — you can now continue diagnosis on Session #{gap.session_id}."
    )

    if session:
        # Notify the ME who owns the session
        _notify(session.user_id, notify_msg)
        # Notify the SME who escalated (if any)
        if session.escalated_to:
            _notify(session.escalated_to, notify_msg)

    db.commit()

    _write_audit(db, current_user.id, "knowledge_gap_resolve", "knowledge_gap", str(gap_id), {
        "file_updated": target_file,
        "session_id":   gap.session_id,
    })

    db.refresh(gap)
    return schemas.KnowledgeGapOut.model_validate(gap)


# ─── Notification endpoints ───────────────────────────────────────────────────

@app.get("/notifications", response_model=List[schemas.NotificationOut])
def get_notifications(
    unread_only: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return in-app notifications for the current user."""
    query = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id
    )
    if unread_only:
        query = query.filter(models.Notification.is_read == False)  # noqa: E712
    return [
        schemas.NotificationOut.model_validate(n)
        for n in query.order_by(models.Notification.created_at.desc()).limit(50).all()
    ]


@app.get("/notifications/unread-count")
def get_unread_count(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    count = db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False,  # noqa: E712
    ).count()
    return {"unread_count": count}


@app.put("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(404, "Notification not found")
    notif.is_read = True
    db.commit()
    return {"id": notification_id, "is_read": True}


@app.put("/notifications/read-all")
def mark_all_notifications_read(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == False,  # noqa: E712
    ).update({"is_read": True})
    db.commit()
    return {"marked_read": True}


# ═══════════════════════════════════════════════════════════════════
# REPORT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/sessions/{session_id}/report", response_model=schemas.ReportOut)
def create_report(
    session_id: int,
    current_user: models.User = Depends(require_permission(P_REPORT_CREATE)),
    db: Session = Depends(get_db),
):
    """Generate and store a fault report for a session."""
    session = _get_session_or_404(db, session_id)

    # ME can only report own sessions; SME can report escalated sessions too
    if current_user.role == Role.ME and session.user_id != current_user.id:
        raise HTTPException(403, "You can only generate reports for your own sessions.")

    if len(session.messages) < 2:
        raise HTTPException(400, "Session must have at least one exchange before generating a report.")

    # Build full history and measurements
    history      = [{"role": m.role, "content": m.content} for m in session.messages]
    measurements = _build_measurements_list(session)
    session_data = _build_session_data(session)
    session_resolved = session.lifecycle_state in (
        models.FaultLifecycleState.PROBABLE_CAUSE_IDENTIFIED,
        models.FaultLifecycleState.RESOLVED,
        models.FaultLifecycleState.SME_IN_REVIEW,
    )

    orchestrator = SessionOrchestrator()
    try:
        orch_result = orchestrator.handle_report_request(
            session_data=session_data,
            conversation_history=history,
            measurements=measurements,
            lifecycle_state=str(session.lifecycle_state),
            session_resolved=session_resolved,
        )
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(500, f"Report generation failed: {e}")

    if not orch_result.get("generation_ok"):
        logger.warning(f"[AGT-08] Report generation degraded for session {session_id}")

    report_data       = orch_result["report_data"]
    meas_summary_str  = orch_result.get("measurements_summary", "")

    # Persist report
    existing_report = db.query(models.Report).filter(
        models.Report.session_id == session.id
    ).first()

    if existing_report:
        existing_report.issue_summary         = report_data.get("issue_summary", "")
        existing_report.steps_taken           = json.dumps(report_data.get("steps_taken", []))
        existing_report.measurements_summary  = meas_summary_str
        existing_report.root_cause            = report_data.get("root_cause")
        existing_report.diagnosis             = report_data.get("diagnosis", "")
        existing_report.recommendations       = json.dumps(report_data.get("recommendations", []))
        existing_report.severity              = report_data.get("severity", "medium")
        fu_required = report_data.get("follow_up_required", False)
        existing_report.follow_up_required    = fu_required
        if fu_required and not existing_report.follow_up_status:
            existing_report.follow_up_status  = "pending"
        db.commit()
        db.refresh(existing_report)
        report = existing_report
    else:
        fu_required = report_data.get("follow_up_required", False)
        report = models.Report(
            session_id=session.id,
            user_id=session.user_id,
            crane_type=session.crane_type,
            component=session.component,
            issue_summary=report_data.get("issue_summary", ""),
            steps_taken=json.dumps(report_data.get("steps_taken", [])),
            measurements_summary=meas_summary_str,
            root_cause=report_data.get("root_cause"),
            diagnosis=report_data.get("diagnosis", ""),
            recommendations=json.dumps(report_data.get("recommendations", [])),
            severity=report_data.get("severity", "medium"),
            follow_up_required=fu_required,
            follow_up_status="pending" if fu_required else None,
        )
        db.add(report)
        db.commit()
        db.refresh(report)

    # Auto-create knowledge gap record if feedback agent flagged one
    if orch_result.get("gap_detected") and orch_result.get("gap_record"):
        gr = orch_result["gap_record"]
        import json as _json
        ev_raw = gr.get("evidence_checked", [])
        gap = models.KnowledgeGap(
            session_id=session.id,
            component_key=gr.get("component_key", session.component),
            fault_pattern=(gr.get("fault_pattern") or "")[:200],
            gap_type=gr.get("gap_type", "low_coverage"),
            suggested_action=gr.get("suggested_action", ""),
            status="open",
            # V3 structured fields
            detected_by=gr.get("detected_by", "diagnostic_agent"),
            missing_information=gr.get("missing_information"),
            affected_asset_type=gr.get("affected_asset_type", session.component),
            suggested_file_to_update=gr.get("suggested_file_to_update"),
            suggested_section_or_node=gr.get("suggested_section_or_node"),
            evidence_checked=_json.dumps(ev_raw) if ev_raw else None,
            confidence=gr.get("confidence", 0.0),
        )
        db.add(gap)

    # Transition lifecycle state
    prev = session.lifecycle_state
    session.lifecycle_state = models.FaultLifecycleState.CLOSED_WITH_REPORT
    _record_transition(db, session, prev, "CLOSED_WITH_REPORT", current_user, "Report generated")
    db.commit()

    _write_audit(db, current_user.id, "report_generate", "report", str(report.id))
    return schemas.ReportOut.model_validate(report)


@app.get("/reports/{report_id}", response_model=schemas.ReportOut)
def get_report(
    report_id: int,
    current_user: models.User = Depends(require_permission(P_REPORT_READ_ANY)),
    db: Session = Depends(get_db),
):
    """Any authenticated user can read any generated report (knowledge sharing)."""
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    return schemas.ReportOut.model_validate(report)


@app.put("/reports/{report_id}/follow-up/close", response_model=schemas.ReportOut)
def close_follow_up(
    report_id: int,
    body: schemas.FollowUpCloseRequest,
    current_user: models.User = Depends(require_permission(P_FOLLOW_UP_CLOSE)),
    db: Session = Depends(get_db),
):
    """Mark a follow-up as done. Allowed for ME and SME."""
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if not report.follow_up_required:
        raise HTTPException(400, "This report does not have a follow-up requirement")
    if report.follow_up_status == "done":
        raise HTTPException(400, "Follow-up already marked as done")

    report.follow_up_status    = "done"
    report.follow_up_closed_by = current_user.id
    report.follow_up_closed_at = datetime.utcnow()
    report.follow_up_note      = body.note

    db.commit()
    db.refresh(report)

    _write_audit(
        db, current_user.id, "follow_up_closed", "report", str(report_id),
        {"note": body.note},
    )
    return schemas.ReportOut.model_validate(report)


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/dashboard", response_model=List[schemas.DashboardEntry])
def get_dashboard(
    crane_type: Optional[str] = None,
    component: Optional[str] = None,
    lifecycle_state: Optional[str] = None,
    filter_mode: str = "own",   # own | all | escalated
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return sessions for the dashboard.
    filter_mode=own     → own sessions (ME, SME)
    filter_mode=all     → all sessions (SME, SUP, ADM)
    filter_mode=escalated → escalated/SME_in_review (SME, SUP)
    """
    query = db.query(models.TroubleshootingSession)

    if filter_mode == "own":
        if not has_permission(current_user.role, P_DASHBOARD_OWN):
            raise HTTPException(403, "No permission for own dashboard")
        query = query.filter(models.TroubleshootingSession.user_id == current_user.id)

    elif filter_mode == "all":
        if not has_permission(current_user.role, P_DASHBOARD_ALL):
            raise HTTPException(403, "No permission for all-engineers dashboard")

    elif filter_mode == "escalated":
        if not has_permission(current_user.role, "dashboard.escalated"):
            raise HTTPException(403, "No permission for escalated sessions view")
        query = query.filter(
            models.TroubleshootingSession.lifecycle_state.in_(
                ["ESCALATED", "SME_IN_REVIEW"]
            )
        )
    else:
        raise HTTPException(400, f"Unknown filter_mode: {filter_mode}")

    if crane_type:
        query = query.filter(models.TroubleshootingSession.crane_type == crane_type)
    if component:
        query = query.filter(models.TroubleshootingSession.component == component)
    if lifecycle_state:
        query = query.filter(models.TroubleshootingSession.lifecycle_state == lifecycle_state)

    sessions = query.order_by(models.TroubleshootingSession.created_at.desc()).all()
    user_map = {u.id: u for u in db.query(models.User).all()}

    results = []
    for s in sessions:
        engineer = user_map.get(s.user_id)
        report   = s.report
        results.append(schemas.DashboardEntry(
            session_id=s.id,
            crane_type=s.crane_type,
            component=s.component,
            problem_description=s.problem_description,
            lifecycle_state=s.lifecycle_state,
            session_date=s.created_at,
            has_report=report is not None,
            report_id=report.id if report else None,
            severity=report.severity if report else None,
            engineer_name=engineer.name if engineer else "Unknown",
            engineer_role=engineer.role if engineer else "ME",
            escalated=s.lifecycle_state in ("ESCALATED", "SME_IN_REVIEW"),
        ))
    return results


@app.get("/dashboard/cranes", response_model=List[str])
def get_all_cranes(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return distinct crane types visible to the current user."""
    query = db.query(models.TroubleshootingSession.crane_type).distinct()
    if current_user.role == Role.ME:
        query = query.filter(models.TroubleshootingSession.user_id == current_user.id)
    return [r[0] for r in query.all()]


@app.get("/dashboard/crane-history")
def get_crane_history(
    crane_type: str,
    current_user: models.User = Depends(require_permission(P_CRANE_HISTORY)),
    db: Session = Depends(get_db),
):
    """All completed sessions + reports for a given crane (cross-engineer)."""
    sessions = (
        db.query(models.TroubleshootingSession)
        .filter(
            models.TroubleshootingSession.crane_type == crane_type,
            models.TroubleshootingSession.lifecycle_state ==
            models.FaultLifecycleState.CLOSED_WITH_REPORT,
        )
        .order_by(models.TroubleshootingSession.created_at.desc())
        .all()
    )
    user_map = {u.id: u for u in db.query(models.User).all()}
    results = []
    for s in sessions:
        engineer = user_map.get(s.user_id)
        r = s.report
        results.append({
            "session_id":          s.id,
            "component":           s.component,
            "problem_description": s.problem_description,
            "session_date":        s.created_at.isoformat(),
            "engineer_name":       engineer.name if engineer else "Unknown",
            "engineer_role":       engineer.role if engineer else "ME",
            "report":              {
                "id":               r.id,
                "issue_summary":    r.issue_summary,
                "root_cause":       r.root_cause,
                "severity":         r.severity,
                "follow_up_required": r.follow_up_required,
                "recommendations":  _parse_json_list(r.recommendations),
                "diagnosis":        r.diagnosis,
            } if r else None,
        })
    return results


@app.get("/dashboard/stats")
def get_stats(
    filter_mode: str = "own",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Summary statistics for the dashboard."""
    session_q = db.query(models.TroubleshootingSession)
    report_q  = db.query(models.Report)

    if filter_mode == "own":
        session_q = session_q.filter(models.TroubleshootingSession.user_id == current_user.id)
        report_q  = report_q.filter(models.Report.user_id == current_user.id)
    elif filter_mode in ("all", "escalated"):
        if not has_permission(current_user.role, P_DASHBOARD_ALL):
            raise HTTPException(403, "No permission for cross-engineer stats")
        if filter_mode == "escalated":
            session_q = session_q.filter(
                models.TroubleshootingSession.lifecycle_state.in_(["ESCALATED", "SME_IN_REVIEW"])
            )

    total_sessions    = session_q.count()
    completed_sessions = session_q.filter(
        models.TroubleshootingSession.lifecycle_state ==
        models.FaultLifecycleState.CLOSED_WITH_REPORT
    ).count()
    total_reports    = report_q.count()
    follow_up_needed = report_q.filter(
        models.Report.follow_up_required == True,
        models.Report.follow_up_status == "pending",
    ).count()

    component_counts: dict = {}
    for row in session_q.with_entities(models.TroubleshootingSession.component).all():
        component_counts[row[0]] = component_counts.get(row[0], 0) + 1

    severity_counts: dict = {}
    for row in report_q.with_entities(models.Report.severity).all():
        if row[0]:
            severity_counts[row[0]] = severity_counts.get(row[0], 0) + 1

    return {
        "total_sessions":      total_sessions,
        "completed_sessions":  completed_sessions,
        "total_reports":       total_reports,
        "follow_up_needed":    follow_up_needed,
        "component_breakdown": component_counts,
        "severity_breakdown":  severity_counts,
    }


# ═══════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS (ADM only)
# ═══════════════════════════════════════════════════════════════════

@app.get("/admin/users", response_model=List[schemas.UserAdminOut])
def list_users(
    current_user: models.User = Depends(require_permission(P_USER_READ)),
    db: Session = Depends(get_db),
):
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [schemas.UserAdminOut.model_validate(u) for u in users]


@app.put("/admin/users/{user_id}/role")
def update_user_role(
    user_id: int,
    body: schemas.RoleUpdate,
    current_user: models.User = Depends(require_permission(P_ROLE_ASSIGN)),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    old_role = user.role
    user.role = body.role
    db.commit()
    _write_audit(db, current_user.id, "role_assign", "user", str(user_id),
                 {"old_role": old_role, "new_role": body.role})
    return {"user_id": user_id, "role": user.role}


@app.put("/admin/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    current_user: models.User = Depends(require_permission(P_USER_DEACTIVATE)),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(400, "Cannot deactivate your own account.")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = False
    db.commit()
    _write_audit(db, current_user.id, "user_deactivate", "user", str(user_id))
    return {"user_id": user_id, "is_active": False}


@app.put("/admin/users/{user_id}/activate")
def activate_user(
    user_id: int,
    current_user: models.User = Depends(require_permission(P_USER_DEACTIVATE)),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = True
    db.commit()
    _write_audit(db, current_user.id, "user_activate", "user", str(user_id))
    return {"user_id": user_id, "is_active": True}


@app.get("/admin/audit-log", response_model=List[schemas.AuditLogOut])
def get_audit_log(
    event_type: Optional[str] = None,
    limit: int = 200,
    current_user: models.User = Depends(require_permission(P_AUDIT_LOG_READ)),
    db: Session = Depends(get_db),
):
    query = db.query(models.AuditLogEntry).order_by(models.AuditLogEntry.created_at.desc())
    if event_type:
        query = query.filter(models.AuditLogEntry.event_type == event_type)
    entries = query.limit(limit).all()
    return [schemas.AuditLogOut.model_validate(e) for e in entries]


# ═══════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok", "service": "AI-Assisted Process Guidance Tool", "version": "2.0.0"}


# ═══════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════

def _get_session_or_404(db: Session, session_id: int) -> models.TroubleshootingSession:
    session = db.query(models.TroubleshootingSession).filter(
        models.TroubleshootingSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(404, "Session not found")
    return session


def _assert_session_readable(session: models.TroubleshootingSession, user: models.User):
    """Raise 403 if the user cannot read this session."""
    if session.user_id == user.id:
        return   # own session — always readable
    if has_permission(user.role, P_SESSION_READ_ALL):
        return   # SUP / ADM see everything
    if has_permission(user.role, P_SESSION_READ_ESCALATED):
        if session.lifecycle_state in ("ESCALATED", "SME_IN_REVIEW"):
            return   # SME can see escalated sessions
    raise HTTPException(403, "Access denied to this session")


def _assert_chat_permitted(session: models.TroubleshootingSession, user: models.User):
    """Raise 403 if the user cannot chat in this session."""
    if session.user_id == user.id and has_permission(user.role, P_SESSION_CHAT_OWN):
        return
    if (
        has_permission(user.role, P_SESSION_CHAT_ESCALATED)
        and session.lifecycle_state in ("ESCALATED", "SME_IN_REVIEW")
    ):
        return
    raise HTTPException(403, "You do not have permission to chat in this session")


def _record_transition(
    db: Session,
    session: models.TroubleshootingSession,
    prev_state: str,
    new_state: str,
    actor: models.User,
    reason: Optional[str] = None,
):
    transition = models.StateTransition(
        session_id=session.id,
        user_id=actor.id,
        previous_state=prev_state,
        new_state=new_state,
        reason=reason,
    )
    db.add(transition)


def _write_audit(
    db: Session,
    user_id: int,
    event_type: str,
    resource_type: str,
    resource_id: str,
    details: Optional[dict] = None,
):
    entry = models.AuditLogEntry(
        user_id=user_id,
        event_type=event_type,
        resource_type=resource_type,
        resource_id=resource_id,
        details=json.dumps(details) if details else None,
    )
    db.add(entry)
    try:
        db.commit()
    except Exception:
        db.rollback()


def _apply_session_update(
    db: Session,
    session: models.TroubleshootingSession,
    update: dict,
):
    if not update:
        return
    if "completed_steps" in update:
        steps = update["completed_steps"]
        if isinstance(steps, list):
            session.completed_steps = json.dumps(steps)
    if "likely_causes" in update:
        causes = update["likely_causes"]
        if isinstance(causes, list):
            session.likely_causes = json.dumps(causes)
    if "current_hypothesis" in update:
        session.current_hypothesis = str(update["current_hypothesis"])


def _build_session_data(session: models.TroubleshootingSession) -> dict:
    return {
        "crane_type":           session.crane_type,
        "component":            session.component,
        "problem_description":  session.problem_description,
        "environment":          session.environment,
        "recent_changes":       session.recent_changes,
        "error_messages":       session.error_messages,
        "completed_steps":      session.completed_steps,
        "likely_causes":        session.likely_causes,
    }


def _ke_block(ke_name: str, content: str) -> str:
    """Wrap KE-added content in a labelled block for auditability in the .txt file."""
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    return (
        f"\n\n=== KNOWLEDGE UPDATE ({date_str} — added by KE: {ke_name}) ===\n"
        f"{content}\n"
        f"=== END UPDATE ===\n"
    )


def _build_measurements_list(session: models.TroubleshootingSession) -> list:
    return [
        {
            "voltage":              m.voltage,
            "current":              m.current,
            "temperature":          m.temperature,
            "load":                 m.load,
            "brake_gap":            m.brake_gap,
            "insulation_resistance":m.insulation_resistance,
            "vibration":            m.vibration,
            "notes":                m.notes,
        }
        for m in session.measurements
    ]


def _parse_json_list(value: Optional[str]) -> list:
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []
