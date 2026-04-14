"""
SQLAlchemy ORM models for the Crane AI database.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime,
    ForeignKey, Enum, Boolean
)
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class SessionStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("TroubleshootingSession", back_populates="user")
    reports = relationship("Report", back_populates="user")


class TroubleshootingSession(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Intake form fields
    crane_type = Column(String(100), nullable=False)
    component = Column(String(100), nullable=False)
    problem_description = Column(Text, nullable=False)
    environment = Column(Text, nullable=True)
    recent_changes = Column(Text, nullable=True)
    error_messages = Column(Text, nullable=True)

    # Session state
    status = Column(String(20), default=SessionStatus.active)
    current_hypothesis = Column(Text, nullable=True)
    completed_steps = Column(Text, nullable=True)   # JSON list of steps
    likely_causes = Column(Text, nullable=True)     # JSON list

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="sessions")
    messages = relationship(
        "Message", back_populates="session",
        order_by="Message.created_at", cascade="all, delete-orphan"
    )
    measurements = relationship(
        "Measurement", back_populates="session",
        order_by="Measurement.created_at", cascade="all, delete-orphan"
    )
    report = relationship("Report", back_populates="session", uselist=False)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    role = Column(String(10), nullable=False)   # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TroubleshootingSession", back_populates="messages")


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)

    voltage = Column(Float, nullable=True)        # Volts
    current = Column(Float, nullable=True)        # Amps
    temperature = Column(Float, nullable=True)    # Celsius
    load = Column(Float, nullable=True)           # kg or %
    brake_gap = Column(Float, nullable=True)      # mm
    insulation_resistance = Column(Float, nullable=True)  # MΩ
    vibration = Column(Float, nullable=True)      # mm/s RMS
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TroubleshootingSession", back_populates="measurements")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    crane_type = Column(String(100), nullable=False)
    component = Column(String(100), nullable=False)

    issue_summary = Column(Text, nullable=False)
    steps_taken = Column(Text, nullable=False)         # JSON list
    measurements_summary = Column(Text, nullable=True) # JSON object
    root_cause = Column(Text, nullable=True)
    diagnosis = Column(Text, nullable=False)
    recommendations = Column(Text, nullable=False)     # JSON list
    severity = Column(String(20), nullable=True)       # low/medium/high/critical
    follow_up_required = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("TroubleshootingSession", back_populates="report")
    user = relationship("User", back_populates="reports")
