"""
SQLAlchemy ORM models for the Crane AI Process Guidance Tool (Version 2).
Extended with: user roles, fault lifecycle states, escalation records,
expert annotations, state transition history, knowledge gaps, and audit log.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime,
    ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


# ─── Enumerations ─────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ME  = "ME"   # Maintenance Engineer
    SME = "SME"  # Senior Maintenance Engineer / Subject Matter Expert
    KE  = "KE"   # Knowledge Engineer
    SUP = "SUP"  # Supervisor / Maintenance Manager
    ADM = "ADM"  # System Administrator


class FaultLifecycleState(str, enum.Enum):
    LOGGED                   = "LOGGED"
    IN_PROGRESS              = "IN_PROGRESS"
    AWAITING_MEASUREMENT     = "AWAITING_MEASUREMENT"
    PROBABLE_CAUSE_IDENTIFIED= "PROBABLE_CAUSE_IDENTIFIED"
    UNRESOLVED               = "UNRESOLVED"
    ESCALATED                = "ESCALATED"
    SME_IN_REVIEW            = "SME_IN_REVIEW"
    KNOWLEDGE_GAP_FLAGGED    = "KNOWLEDGE_GAP_FLAGGED"
    RESOLVED                 = "RESOLVED"
    CLOSED_WITH_REPORT       = "CLOSED_WITH_REPORT"


# ─── Core tables ──────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    username        = Column(String(50), unique=True, nullable=False, index=True)
    name            = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role            = Column(String(10), nullable=False, default=UserRole.ME)
    is_active       = Column(Boolean, default=True, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)
    last_login_at   = Column(DateTime, nullable=True)

    # relationships
    sessions            = relationship(
        "TroubleshootingSession",
        back_populates="user",
        foreign_keys="TroubleshootingSession.user_id",
    )
    escalated_sessions  = relationship(
        "TroubleshootingSession",
        back_populates="escalated_to_user",
        foreign_keys="TroubleshootingSession.escalated_to",
    )
    reports             = relationship("Report", back_populates="user",
                                        foreign_keys="Report.user_id")
    expert_annotations  = relationship("ExpertAnnotation", back_populates="author")
    state_transitions   = relationship("StateTransition", back_populates="actor")
    audit_log_entries   = relationship("AuditLogEntry", back_populates="actor")


class TroubleshootingSession(Base):
    __tablename__ = "sessions"

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Intake form fields
    crane_type          = Column(String(100), nullable=False)
    component           = Column(String(100), nullable=False)
    problem_description = Column(Text, nullable=False)
    environment         = Column(Text, nullable=True)
    recent_changes      = Column(Text, nullable=True)
    error_messages      = Column(Text, nullable=True)

    # Lifecycle state (replaces old "status" string)
    lifecycle_state = Column(
        String(30),
        nullable=False,
        default=FaultLifecycleState.LOGGED,
    )

    # AI-maintained diagnostic state
    current_hypothesis = Column(Text, nullable=True)
    completed_steps    = Column(Text, nullable=True)   # JSON list
    likely_causes      = Column(Text, nullable=True)   # JSON list

    # Escalation fields
    escalated_to   = Column(Integer, ForeignKey("users.id"), nullable=True)
    escalation_reason = Column(Text, nullable=True)
    escalated_at   = Column(DateTime, nullable=True)

    # Metadata
    agent_metadata = Column(Text, nullable=True)   # JSON: agent versions used
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    user               = relationship(
        "User", back_populates="sessions",
        foreign_keys=[user_id],
    )
    escalated_to_user  = relationship(
        "User", back_populates="escalated_sessions",
        foreign_keys=[escalated_to],
    )
    messages           = relationship(
        "Message", back_populates="session",
        order_by="Message.created_at", cascade="all, delete-orphan",
    )
    measurements       = relationship(
        "Measurement", back_populates="session",
        order_by="Measurement.created_at", cascade="all, delete-orphan",
    )
    report             = relationship("Report", back_populates="session", uselist=False)
    expert_annotations = relationship(
        "ExpertAnnotation", back_populates="session",
        order_by="ExpertAnnotation.created_at", cascade="all, delete-orphan",
    )
    state_transitions  = relationship(
        "StateTransition", back_populates="session",
        order_by="StateTransition.transitioned_at", cascade="all, delete-orphan",
    )
    knowledge_gap      = relationship(
        "KnowledgeGap", back_populates="session", uselist=False,
    )

    # ── Convenience property: backwards-compat "status" for V1 code ──────────
    @property
    def status(self) -> str:
        """Map lifecycle_state to the legacy status string used by V1 frontend."""
        if self.lifecycle_state == FaultLifecycleState.CLOSED_WITH_REPORT:
            return "completed"
        return "active"


class Message(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role       = Column(String(10), nullable=False)   # "user" or "assistant"
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TroubleshootingSession", back_populates="messages")


class Measurement(Base):
    __tablename__ = "measurements"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)

    voltage              = Column(Float, nullable=True)   # Volts
    current              = Column(Float, nullable=True)   # Amps
    temperature          = Column(Float, nullable=True)   # Celsius
    load                 = Column(Float, nullable=True)   # kg
    brake_gap            = Column(Float, nullable=True)   # mm
    insulation_resistance= Column(Float, nullable=True)   # MΩ
    vibration            = Column(Float, nullable=True)   # mm/s RMS
    notes                = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TroubleshootingSession", back_populates="measurements")


class Report(Base):
    __tablename__ = "reports"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)

    crane_type   = Column(String(100), nullable=False)
    component    = Column(String(100), nullable=False)

    issue_summary       = Column(Text, nullable=False)
    steps_taken         = Column(Text, nullable=False)          # JSON list
    measurements_summary= Column(Text, nullable=True)           # JSON object
    root_cause          = Column(Text, nullable=True)
    diagnosis           = Column(Text, nullable=False)
    recommendations     = Column(Text, nullable=False)          # JSON list
    severity            = Column(String(20), nullable=True)     # critical/high/medium/low
    follow_up_required  = Column(Boolean, default=False)
    # Follow-up tracking: populated only when follow_up_required=True
    follow_up_status    = Column(String(20), nullable=True)          # pending | done
    follow_up_closed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    follow_up_closed_at = Column(DateTime, nullable=True)
    follow_up_note      = Column(Text, nullable=True)

    agent_version       = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    session          = relationship("TroubleshootingSession", back_populates="report")
    user             = relationship("User", back_populates="reports",
                                   foreign_keys=[user_id])
    follow_up_closer = relationship("User", foreign_keys=[follow_up_closed_by])


# ─── New V2 tables ────────────────────────────────────────────────────────────

class ExpertAnnotation(Base):
    """SME annotations added during expert review of escalated sessions."""
    __tablename__ = "expert_annotations"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)

    annotation_text = Column(Text, nullable=False)
    # Types: expert_note | cause_validation | procedure_correction
    annotation_type = Column(String(30), nullable=False, default="expert_note")

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TroubleshootingSession", back_populates="expert_annotations")
    author  = relationship("User", back_populates="expert_annotations")


class StateTransition(Base):
    """Audit trail of every fault lifecycle state change."""
    __tablename__ = "state_transitions"

    id             = Column(Integer, primary_key=True, index=True)
    session_id     = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=False)

    previous_state = Column(String(30), nullable=False)
    new_state      = Column(String(30), nullable=False)
    reason         = Column(Text, nullable=True)

    transitioned_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TroubleshootingSession", back_populates="state_transitions")
    actor   = relationship("User", back_populates="state_transitions")


class KnowledgeGap(Base):
    """Records identified gaps in the knowledge base, flagged by SMEs or auto-detected."""
    __tablename__ = "knowledge_gaps"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)

    component_key       = Column(String(100), nullable=False)
    fault_pattern       = Column(Text, nullable=False)
    # gap_type: missing_manual_info | missing_troubleshooting_step | outdated_knowledge |
    #           missing_threshold | unknown_fault | no_procedure | no_specs |
    #           unresolved | low_coverage | no_matching_content
    gap_type            = Column(String(50), nullable=False, default="no_matching_content")
    suggested_action    = Column(Text, nullable=True)
    # status: open | in_review | resolved
    status              = Column(String(20), nullable=False, default="open")
    resolved_by         = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at  = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # ── Structured gap fields (V3) ────────────────────────────────────────────
    detected_by               = Column(String(40),  nullable=True, default="system")
    missing_information       = Column(Text,         nullable=True)
    affected_asset_type       = Column(String(100),  nullable=True)
    suggested_file_to_update  = Column(String(200),  nullable=True)
    suggested_section_or_node = Column(String(200),  nullable=True)
    evidence_checked          = Column(Text,         nullable=True)   # JSON list
    confidence                = Column(Float,        nullable=True, default=0.0)
    resolution_note           = Column(Text,         nullable=True)
    knowledge_content_added   = Column(Text,         nullable=True)

    session = relationship("TroubleshootingSession", back_populates="knowledge_gap")


class Notification(Base):
    """In-app notifications sent when a knowledge gap is resolved."""
    __tablename__ = "notifications"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    gap_id     = Column(Integer, ForeignKey("knowledge_gaps.id"), nullable=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=True)
    message    = Column(Text, nullable=False)
    is_read    = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])


class AuditLogEntry(Base):
    """System-wide audit trail for security-relevant and operational events."""
    __tablename__ = "audit_log"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=True)

    event_type    = Column(String(50), nullable=False)   # login, session_create, etc.
    resource_type = Column(String(50), nullable=True)    # session, report, user
    resource_id   = Column(String(50), nullable=True)
    details       = Column(Text, nullable=True)          # JSON blob

    created_at    = Column(DateTime, default=datetime.utcnow)

    actor = relationship("User", back_populates="audit_log_entries")
