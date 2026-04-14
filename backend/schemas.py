"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, field_validator


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


# ─── Sessions ────────────────────────────────────────────────────────────────

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
    status: str
    current_hypothesis: Optional[str]
    completed_steps: Optional[str]
    likely_causes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SessionSummary(BaseModel):
    id: int
    crane_type: str
    component: str
    problem_description: str
    status: str
    created_at: datetime
    has_report: bool

    class Config:
        from_attributes = True


# ─── Chat ────────────────────────────────────────────────────────────────────

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


# ─── Measurements ────────────────────────────────────────────────────────────

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


# ─── Reports ─────────────────────────────────────────────────────────────────

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
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Dashboard ───────────────────────────────────────────────────────────────

class DashboardEntry(BaseModel):
    session_id: int
    crane_type: str
    component: str
    problem_description: str
    status: str
    session_date: datetime
    has_report: bool
    report_id: Optional[int]
    severity: Optional[str]
    engineer_name: str


class SessionStateUpdate(BaseModel):
    current_hypothesis: Optional[str] = None
    completed_steps: Optional[str] = None
    likely_causes: Optional[str] = None
