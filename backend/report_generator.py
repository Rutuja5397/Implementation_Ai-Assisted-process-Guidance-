"""
Report generator: uses AI to synthesise a structured fault report
from the full session history, measurements, and conversation.
"""

import json
import logging
import os
from typing import List, Dict, Any, Optional

import anthropic
from sqlalchemy.orm import Session

from backend import models

logger = logging.getLogger(__name__)


def generate_report(
    db_session: Session,
    session: models.TroubleshootingSession,
) -> models.Report:
    """
    Generate a structured troubleshooting report for a completed session.
    Calls Claude to synthesise findings, then stores in DB.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    # Collect session data
    messages = session.messages
    measurements = session.measurements

    # Build conversation transcript
    transcript = ""
    for msg in messages:
        role_label = "Engineer" if msg.role == "user" else "AI Assistant"
        transcript += f"\n[{role_label}]: {msg.content}\n"

    # Build measurements summary
    meas_list = []
    for m in measurements:
        entry = {}
        if m.voltage is not None:
            entry["voltage_V"] = m.voltage
        if m.current is not None:
            entry["current_A"] = m.current
        if m.temperature is not None:
            entry["temperature_C"] = m.temperature
        if m.load is not None:
            entry["load_kg"] = m.load
        if m.brake_gap is not None:
            entry["brake_gap_mm"] = m.brake_gap
        if m.insulation_resistance is not None:
            entry["insulation_resistance_MOhm"] = m.insulation_resistance
        if m.vibration is not None:
            entry["vibration_mm_s"] = m.vibration
        if m.notes:
            entry["notes"] = m.notes
        if entry:
            meas_list.append(entry)

    meas_summary_str = json.dumps(meas_list, indent=2) if meas_list else "No measurements recorded."

    # Prompt for report generation
    prompt = f"""You are generating a formal crane maintenance troubleshooting report.

SESSION INFORMATION:
- Crane: {session.crane_type}
- Component: {session.component}
- Reported Problem: {session.problem_description}
- Environment: {session.environment or 'Not specified'}
- Recent Changes: {session.recent_changes or 'None reported'}
- Error Messages: {session.error_messages or 'None reported'}

MEASUREMENTS RECORDED:
{meas_summary_str}

TROUBLESHOOTING CONVERSATION:
{transcript}

Generate a structured fault report in the following JSON format (respond ONLY with valid JSON, no other text):

{{
  "issue_summary": "One-sentence summary of the reported fault",
  "steps_taken": [
    "Step 1 description",
    "Step 2 description"
  ],
  "root_cause": "Identified root cause or 'Undetermined - further investigation required'",
  "diagnosis": "Full diagnostic narrative (2-4 sentences)",
  "recommendations": [
    "Recommendation 1",
    "Recommendation 2",
    "Recommendation 3"
  ],
  "severity": "low|medium|high|critical",
  "follow_up_required": true|false,
  "severity_justification": "Brief justification of severity rating"
}}

Severity guide:
- critical: Immediate safety risk, crane must not be operated
- high: Significant fault, operation should be suspended
- medium: Degraded operation, schedule repair within 48 hours
- low: Minor issue, schedule at next planned maintenance
"""

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text.strip()

    # Parse JSON response
    try:
        # Strip markdown code fences if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]

        report_data = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse report JSON: {e}")
        # Fallback report
        report_data = {
            "issue_summary": f"Fault investigation: {session.component} on {session.crane_type}",
            "steps_taken": ["Session conducted; see conversation transcript"],
            "root_cause": "Undetermined - review conversation for details",
            "diagnosis": session.current_hypothesis or "No diagnosis recorded.",
            "recommendations": ["Review conversation history", "Consult OEM documentation"],
            "severity": "medium",
            "follow_up_required": True,
        }

    # Create Report ORM object
    existing_report = db_session.query(models.Report).filter(
        models.Report.session_id == session.id
    ).first()

    if existing_report:
        # Update existing
        existing_report.issue_summary = report_data.get("issue_summary", "")
        existing_report.steps_taken = json.dumps(report_data.get("steps_taken", []))
        existing_report.measurements_summary = meas_summary_str
        existing_report.root_cause = report_data.get("root_cause")
        existing_report.diagnosis = report_data.get("diagnosis", "")
        existing_report.recommendations = json.dumps(report_data.get("recommendations", []))
        existing_report.severity = report_data.get("severity", "medium")
        existing_report.follow_up_required = report_data.get("follow_up_required", False)
        db_session.commit()
        db_session.refresh(existing_report)
        return existing_report
    else:
        db_report = models.Report(
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
            follow_up_required=report_data.get("follow_up_required", False),
        )
        db_session.add(db_report)

        # Mark session as completed
        session.status = "completed"
        db_session.commit()
        db_session.refresh(db_report)
        return db_report
