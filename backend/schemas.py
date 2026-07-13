"""
Pydantic v2 schemas for request/response validation.
Version 2: adds role to auth schemas, lifecycle state to session schemas,
and new schemas for escalation, expert annotations, knowledge gaps, audit log.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


# ─── Auth ─────────────────────────────────────────────────────────────────────

VALID_ROLES = {"ME", "SME", "KE", "SUP", "ADM"}

class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    role: str = "ME"

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    name: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut

# Admin: update a user's role
class RoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"role must be one of {sorted(VALID_ROLES)}")
        return v

# Admin: list of all users
class UserAdminOut(BaseModel):
    id: int
    username: str
    name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Sessions ─────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    crane_type: str
    component: str
    problem_description: str
    environment: Optional[str] = None
    recent_changes: Optional[str] = None
    error_messages: Optional[str] = None

class SessionOut(BaseModel):
    id: int
    user_id: int
    crane_type: str
    component: str
    problem_description: str
    environment: Optional[str]
    recent_changes: Optional[str]
    error_messages: Optional[str]
    lifecycle_state: str
    current_hypothesis: Optional[str]
    completed_steps: Optional[str]
    likely_causes: Optional[str]
    escalated_to: Optional[int]
    escalation_reason: Optional[str]
    escalated_at: Optional[datetime]
    agent_metadata: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SessionSummary(BaseModel):
    id: int
    crane_type: str
    component: str
    problem_description: str
    lifecycle_state: str
    created_at: datetime
    has_report: bool

    class Config:
        from_attributes = True


# ─── Chat ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str

class MessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    message: MessageOut
    session_state: dict
    retrieved_evidence: List[dict]
    questions: List[dict] = []
    knowledge_confidence: str = "high"
    confidence_reason: str = ""


# ─── Measurements ─────────────────────────────────────────────────────────────

class MeasurementCreate(BaseModel):
    voltage: Optional[float] = None
    current: Optional[float] = None
    temperature: Optional[float] = None
    load: Optional[float] = None
    brake_gap: Optional[float] = None
    insulation_resistance: Optional[float] = None
    vibration: Optional[float] = None
    notes: Optional[str] = None

class MeasurementOut(BaseModel):
    id: int
    session_id: int
    voltage: Optional[float]
    current: Optional[float]
    temperature: Optional[float]
    load: Optional[float]
    brake_gap: Optional[float]
    insulation_resistance: Optional[float]
    vibration: Optional[float]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Reports ──────────────────────────────────────────────────────────────────

class ReportOut(BaseModel):
    id: int
    session_id: int
    user_id: int
    crane_type: str
    component: str
    issue_summary: str
    steps_taken: str
    measurements_summary: Optional[str]
    root_cause: Optional[str]
    diagnosis: str
    recommendations: str
    severity: Optional[str]
    follow_up_required: bool
    follow_up_status: Optional[str] = None       # pending | done | None (not required)
    follow_up_closed_by: Optional[int] = None
    follow_up_closed_at: Optional[datetime] = None
    follow_up_note: Optional[str] = None
    agent_version: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ReportSummary(BaseModel):
    id: int
    session_id: int
    crane_type: str
    component: str
    issue_summary: str
    severity: Optional[str]
    follow_up_required: bool
    follow_up_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FollowUpCloseRequest(BaseModel):
    """Body sent when marking a follow-up as done."""
    note: str


# ─── Escalation ───────────────────────────────────────────────────────────────

class EscalateRequest(BaseModel):
    reason: str


# ─── Expert Annotations ───────────────────────────────────────────────────────

VALID_ANNOTATION_TYPES = {
    "expert_note", "cause_validation", "procedure_correction",
    "general", "root_cause", "safety_note", "procedure_note",
}

class ExpertAnnotationCreate(BaseModel):
    annotation_text: str
    annotation_type: str = "expert_note"

    @field_validator("annotation_type")
    @classmethod
    def type_must_be_valid(cls, v: str) -> str:
        if v not in VALID_ANNOTATION_TYPES:
            raise ValueError(f"annotation_type must be one of {sorted(VALID_ANNOTATION_TYPES)}")
        return v

class ExpertAnnotationOut(BaseModel):
    id: int
    session_id: int
    user_id: int
    annotation_text: str
    annotation_type: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Knowledge Gaps ───────────────────────────────────────────────────────────

class KnowledgeGapOut(BaseModel):
    id: int
    session_id: Optional[int]
    component_key: str
    fault_pattern: str
    gap_type: str
    suggested_action: Optional[str]
    status: str
    created_at: datetime
    resolved_at: Optional[datetime]
    # V3 structured fields
    detected_by: Optional[str]
    missing_information: Optional[str]
    affected_asset_type: Optional[str]
    suggested_file_to_update: Optional[str]
    suggested_section_or_node: Optional[str]
    evidence_checked: Optional[str]
    confidence: Optional[float]
    resolution_note: Optional[str]
    knowledge_content_added: Optional[str]

    class Config:
        from_attributes = True


class KnowledgeGapResolveRequest(BaseModel):
    """Body sent by KE when resolving a gap and updating the knowledge file."""
    resolution_note: str
    content_to_append: str        # new text to add to the knowledge base file
    append_to_section: Optional[str] = None   # optional section header to append under


# ─── Notifications ─────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: int
    user_id: int
    gap_id: Optional[int]
    session_id: Optional[int]
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── State Transitions ────────────────────────────────────────────────────────

class StateTransitionOut(BaseModel):
    id: int
    session_id: int
    user_id: int
    previous_state: str
    new_state: str
    reason: Optional[str]
    transitioned_at: datetime

    class Config:
        from_attributes = True


# ─── Dashboard ────────────────────────────────────────────────────────────────

class DashboardEntry(BaseModel):
    session_id: int
    crane_type: str
    component: str
    problem_description: str
    lifecycle_state: str
    session_date: datetime
    has_report: bool
    report_id: Optional[int]
    severity: Optional[str]
    engineer_name: str
    engineer_role: str
    escalated: bool


class SessionStateUpdate(BaseModel):
    current_hypothesis: Optional[str] = None
    completed_steps: Optional[str] = None
    likely_causes: Optional[str] = None


# ─── Audit Log ────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    event_type: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
