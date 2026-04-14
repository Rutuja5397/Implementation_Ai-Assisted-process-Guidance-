"""
FastAPI backend for the Crane AI Process Guidance Tool.
Provides REST endpoints for auth, sessions, chat, measurements,
report generation, and crane dashboard.
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

load_dotenv()

from backend import models, schemas
from backend.auth import (
    authenticate_user,
    create_access_token,
    create_user,
    get_current_user_from_token,
    get_user_by_username,
)
from backend.database import SessionLocal, get_db, init_db
from backend.ai_agent import generate_opening_message, get_ai_response
from backend.report_generator import generate_report as _generate_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Crane AI – Process Guidance Tool",
    description="AI-assisted industrial troubleshooting system for crane maintenance engineers",
    version="1.0.0",
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
    logger.info("Database initialised.")


# ─── Auth helpers ─────────────────────────────────────────────────────────────

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> models.User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    token = authorization.split(" ", 1)[1]
    user = get_current_user_from_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user


# ═══════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/auth/signup", response_model=schemas.Token)
def signup(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_username(db, user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    user = create_user(db, user_data)
    token = create_access_token({"sub": user.username})
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
    token = create_access_token({"sub": user.username})
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
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new troubleshooting session from intake form data."""
    session = models.TroubleshootingSession(
        user_id=current_user.id,
        crane_type=intake.crane_type,
        component=intake.component,
        problem_description=intake.problem_description,
        environment=intake.environment,
        recent_changes=intake.recent_changes,
        error_messages=intake.error_messages,
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Generate opening AI message
    session_data = {
        "crane_type": session.crane_type,
        "component": session.component,
        "problem_description": session.problem_description,
        "environment": session.environment,
        "recent_changes": session.recent_changes,
        "error_messages": session.error_messages,
        "completed_steps": session.completed_steps,
        "likely_causes": session.likely_causes,
    }

    try:
        ai_result = generate_opening_message(session_data)

        # Store opening message
        ai_msg = models.Message(
            session_id=session.id,
            role="assistant",
            content=ai_result["response_text"],
        )
        db.add(ai_msg)

        # Apply initial session update
        _apply_session_update(db, session, ai_result.get("session_update", {}))
        db.commit()

        return {
            "session_id": session.id,
            "opening_message": ai_result["response_text"],
            "retrieved_evidence": ai_result.get("retrieved_evidence", []),
        }
    except Exception as e:
        logger.error(f"AI opening message failed: {e}")
        # Still return session even if AI fails
        return {
            "session_id": session.id,
            "opening_message": (
                f"Session created for {intake.component} on {intake.crane_type}. "
                f"AI guidance is unavailable (check ANTHROPIC_API_KEY). "
                f"Please record your observations manually."
            ),
            "retrieved_evidence": [],
        }


@app.get("/sessions/{session_id}", response_model=schemas.SessionOut)
def get_session(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id, current_user.id)
    return schemas.SessionOut.model_validate(session)


@app.get("/sessions/{session_id}/messages", response_model=List[schemas.MessageOut])
def get_messages(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id, current_user.id)
    return [schemas.MessageOut.model_validate(m) for m in session.messages]


@app.get("/sessions/{session_id}/measurements", response_model=List[schemas.MeasurementOut])
def get_measurements(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id, current_user.id)
    return [schemas.MeasurementOut.model_validate(m) for m in session.measurements]


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
    """Send a user message and receive AI guidance response."""
    session = _get_session_or_404(db, session_id, current_user.id)

    if session.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is completed. Start a new session.",
        )

    # Store user message
    user_msg = models.Message(
        session_id=session.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Prepare conversation history (all messages except the one just added)
    history = [
        {"role": m.role, "content": m.content}
        for m in session.messages
        if m.id != user_msg.id
    ]

    # Prepare measurements list
    measurements = [
        {
            "voltage": m.voltage,
            "current": m.current,
            "temperature": m.temperature,
            "load": m.load,
            "brake_gap": m.brake_gap,
            "insulation_resistance": m.insulation_resistance,
            "vibration": m.vibration,
            "notes": m.notes,
        }
        for m in session.measurements
    ]

    session_data = {
        "crane_type": session.crane_type,
        "component": session.component,
        "problem_description": session.problem_description,
        "environment": session.environment,
        "recent_changes": session.recent_changes,
        "error_messages": session.error_messages,
        "completed_steps": session.completed_steps,
        "likely_causes": session.likely_causes,
    }

    try:
        ai_result = get_ai_response(
            session_data=session_data,
            conversation_history=history,
            new_user_message=request.message,
            measurements=measurements,
        )
    except Exception as e:
        logger.error(f"AI response failed: {e}")
        ai_result = {
            "response_text": f"AI service error: {str(e)}. Please check your API key configuration.",
            "session_update": {},
            "retrieved_evidence": [],
        }

    # Store AI response
    ai_msg = models.Message(
        session_id=session.id,
        role="assistant",
        content=ai_result["response_text"],
    )
    db.add(ai_msg)

    # Apply session state update
    _apply_session_update(db, session, ai_result.get("session_update", {}))
    db.commit()
    db.refresh(ai_msg)

    session_state = {
        "component": session.component,
        "status": session.status,
        "current_hypothesis": session.current_hypothesis,
        "completed_steps": _parse_json_list(session.completed_steps),
        "likely_causes": _parse_json_list(session.likely_causes),
    }

    return schemas.ChatResponse(
        message=schemas.MessageOut.model_validate(ai_msg),
        session_state=session_state,
        retrieved_evidence=ai_result.get("retrieved_evidence", []),
    )


# ═══════════════════════════════════════════════════════════════════
# MEASUREMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/sessions/{session_id}/measurements", response_model=schemas.MeasurementOut)
def add_measurement(
    session_id: int,
    measurement: schemas.MeasurementCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a new measurement for a session."""
    session = _get_session_or_404(db, session_id, current_user.id)

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
# REPORT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.post("/sessions/{session_id}/report", response_model=schemas.ReportOut)
def create_report(
    session_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate and store a final report for a completed session."""
    session = _get_session_or_404(db, session_id, current_user.id)

    if len(session.messages) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session must have at least one exchange before generating a report.",
        )

    try:
        report = _generate_report(db, session)
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}",
        )

    return schemas.ReportOut.model_validate(report)


@app.get("/reports/{report_id}", response_model=schemas.ReportOut)
def get_report(
    report_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    # All authenticated engineers can read any report (knowledge sharing)
    return schemas.ReportOut.model_validate(report)


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.get("/dashboard", response_model=List[schemas.DashboardEntry])
def get_dashboard(
    crane_type: Optional[str] = None,
    component: Optional[str] = None,
    all_engineers: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return sessions with optional filters. all_engineers=true returns all users' sessions."""
    query = db.query(models.TroubleshootingSession)

    if not all_engineers:
        query = query.filter(models.TroubleshootingSession.user_id == current_user.id)

    if crane_type:
        query = query.filter(models.TroubleshootingSession.crane_type == crane_type)
    if component:
        query = query.filter(models.TroubleshootingSession.component == component)

    sessions = query.order_by(models.TroubleshootingSession.created_at.desc()).all()

    # Pre-fetch all users to avoid N+1 queries
    user_map = {u.id: u for u in db.query(models.User).all()}

    results = []
    for s in sessions:
        report = s.report
        engineer = user_map.get(s.user_id)
        results.append(
            schemas.DashboardEntry(
                session_id=s.id,
                crane_type=s.crane_type,
                component=s.component,
                problem_description=s.problem_description,
                status=s.status,
                session_date=s.created_at,
                has_report=report is not None,
                report_id=report.id if report else None,
                severity=report.severity if report else None,
                engineer_name=engineer.name if engineer else "Unknown",
            )
        )

    return results


@app.get("/dashboard/cranes", response_model=List[str])
def get_user_cranes(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return distinct crane types from user's sessions."""
    rows = (
        db.query(models.TroubleshootingSession.crane_type)
        .filter(models.TroubleshootingSession.user_id == current_user.id)
        .distinct()
        .all()
    )
    return [r[0] for r in rows]


@app.get("/dashboard/stats")
def get_stats(
    all_engineers: bool = False,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return summary statistics. all_engineers=true returns stats across all users."""
    session_q = db.query(models.TroubleshootingSession)
    report_q = db.query(models.Report)

    if not all_engineers:
        session_q = session_q.filter(models.TroubleshootingSession.user_id == current_user.id)
        report_q = report_q.filter(models.Report.user_id == current_user.id)

    total_sessions = session_q.count()
    completed_sessions = session_q.filter(
        models.TroubleshootingSession.status == "completed"
    ).count()
    total_reports = report_q.count()
    follow_up_needed = report_q.filter(models.Report.follow_up_required == True).count()

    component_rows = session_q.with_entities(models.TroubleshootingSession.component).all()
    component_counts: dict = {}
    for row in component_rows:
        component_counts[row[0]] = component_counts.get(row[0], 0) + 1

    return {
        "total_sessions": total_sessions,
        "completed_sessions": completed_sessions,
        "total_reports": total_reports,
        "follow_up_needed": follow_up_needed,
        "component_breakdown": component_counts,
    }


# ═══════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════

@app.get("/health")
def health():
    return {"status": "ok", "service": "Crane AI Backend"}


# ═══════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════

def _get_session_or_404(
    db: Session,
    session_id: int,
    user_id: int,
) -> models.TroubleshootingSession:
    session = db.query(models.TroubleshootingSession).filter(
        models.TroubleshootingSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return session


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


def _parse_json_list(value: Optional[str]) -> list:
    if not value:
        return []
    try:
        result = json.loads(value)
        return result if isinstance(result, list) else []
    except (json.JSONDecodeError, TypeError):
        return []
