"""
Crane AI – Process Guidance Tool
Streamlit Frontend: Role-based multi-screen industrial troubleshooting UI

Screens:
  login          – auth (signup includes role selection)
  intake         – fault intake form (ME, SME)
  guidance       – AI diagnostic chat + escalation/SME actions (ME, SME)
  dashboard      – session history, role-filtered views (all roles)
  sme_inbox      – escalated sessions queue (SME)
  knowledge_gaps – knowledge gap management (KE, SME)
  admin          – user management + audit log (ADM)
"""

import json
import os
from datetime import datetime
from typing import Optional

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# ─── Config ──────────────────────────────────────────────────────────────────

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

CRANE_COMPONENTS = {
    "Demag EKKE 5t": [
        "Hoist Motor", "Hoist Brake", "Wire Rope", "Hook Block",
        "Trolley Motor", "Gearbox", "Limit Switch", "Control System", "Power Supply",
    ],
    "Liebherr Tower Crane": [
        "Hoist Motor", "Hoist Brake", "Wire Rope", "Hook Block",
        "Bridge Motor", "Trolley Motor", "Gearbox", "Limit Switch",
        "Control System", "Power Supply",
    ],
    "Generic Crane": [
        "Hoist Motor", "Hoist Brake", "Wire Rope", "Hook Block",
        "Trolley Motor", "Bridge Motor", "Gearbox", "Limit Switch",
        "Control System", "Power Supply",
    ],
}

SEVERITY_COLORS = {
    "critical": "#FF4444", "high": "#FF8C00", "medium": "#FFD700",
    "low": "#32CD32", None: "#888888",
}
SEVERITY_ICONS = {
    "critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", None: "⚪",
}

LIFECYCLE_LABELS = {
    "LOGGED":                    "Logged",
    "IN_PROGRESS":               "In Progress",
    "AWAITING_MEASUREMENT":      "Awaiting Measurement",
    "PROBABLE_CAUSE_IDENTIFIED": "Probable Cause",
    "UNRESOLVED":                "Unresolved",
    "ESCALATED":                 "Escalated",
    "SME_IN_REVIEW":             "SME Review",
    "KNOWLEDGE_GAP_FLAGGED":     "Knowledge Gap",
    "RESOLVED":                  "Resolved",
    "CLOSED_WITH_REPORT":        "Closed",
}
LIFECYCLE_BADGE_CLASS = {
    "LOGGED":                    "badge-state-logged",
    "IN_PROGRESS":               "badge-state-active",
    "AWAITING_MEASUREMENT":      "badge-state-waiting",
    "PROBABLE_CAUSE_IDENTIFIED": "badge-state-probable",
    "UNRESOLVED":                "badge-state-unresolved",
    "ESCALATED":                 "badge-state-escalated",
    "SME_IN_REVIEW":             "badge-state-sme",
    "KNOWLEDGE_GAP_FLAGGED":     "badge-state-gap",
    "RESOLVED":                  "badge-state-resolved",
    "CLOSED_WITH_REPORT":        "badge-state-closed",
}

ROLE_COLORS = {
    "ME":  "#3b82f6",   # blue
    "SME": "#8b5cf6",   # purple
    "KE":  "#10b981",   # green
    "SUP": "#f59e0b",   # amber
    "ADM": "#ef4444",   # red
}
ROLE_LABELS = {
    "ME":  "Maintenance Engineer",
    "SME": "Senior Engineer",
    "KE":  "Knowledge Engineer",
    "SUP": "Supervisor",
    "ADM": "Administrator",
}
# Roles available for self-selection during signup (ADM must be assigned by admin)
SIGNUP_ROLES = ["ME", "SME", "KE", "SUP"]

# ─── Page configuration ───────────────────────────────────────────────────────

st.set_page_config(
    page_title="Crane AI – Process Guidance",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── CSS Styling ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3 {
        font-size: 1rem !important; font-weight: 700 !important;
        margin: 10px 0 4px 0 !important; line-height: 1.4 !important;
        color: #111827 !important;
    }
    [data-testid="stChatMessage"] h4,
    [data-testid="stChatMessage"] h5 {
        font-size: 0.95rem !important; font-weight: 600 !important;
        margin: 8px 0 4px 0 !important; color: #1e293b !important;
    }
    [data-testid="stChatMessage"] p {
        font-size: 0.95rem !important; line-height: 1.75 !important;
        margin-bottom: 8px !important; color: #111827 !important;
    }
    [data-testid="stChatMessage"] li {
        font-size: 0.95rem !important; line-height: 1.7 !important;
        color: #111827 !important; margin-bottom: 4px !important;
    }
    [data-testid="stChatMessage"] strong {
        color: #111827 !important; font-weight: 700 !important;
    }

    /* Assistant message bubble — light blue tint with left border */
    [data-testid="stChatMessage"]:nth-child(odd) {
        background: #f0f7ff !important;
        border-left: 3px solid #3b82f6 !important;
        border-radius: 8px !important;
        padding: 4px 8px !important;
        margin-bottom: 10px !important;
    }
    /* User message bubble — very light grey */
    [data-testid="stChatMessage"]:nth-child(even) {
        background: #f9fafb !important;
        border-left: 3px solid #d1d5db !important;
        border-radius: 8px !important;
        padding: 4px 8px !important;
        margin-bottom: 10px !important;
    }

    /* Question highlight box at the end of AI messages */
    .ai-question-box {
        background: #eff6ff; border: 1px solid #bfdbfe;
        border-left: 4px solid #2563eb; border-radius: 6px;
        padding: 10px 14px; margin-top: 10px;
    }
    .ai-question-box p {
        font-size: 0.96rem !important; font-weight: 600 !important;
        color: #1e3a8a !important; margin: 0 !important;
    }

    /* ── Cards ── */
    .card {
        background: white; border: 1px solid #e5e7eb; border-radius: 10px;
        padding: 20px; margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .section-header {
        font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.08em; color: #6b7280; margin-bottom: 10px;
        border-bottom: 1px solid #f3f4f6; padding-bottom: 6px;
    }

    /* ── Generic badges ── */
    .badge {
        display: inline-block; padding: 3px 10px; border-radius: 12px;
        font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
    }
    .badge-active       { background:#dbeafe; color:#1d4ed8; }
    .badge-completed    { background:#d1fae5; color:#065f46; }
    .badge-critical     { background:#fee2e2; color:#991b1b; }
    .badge-high         { background:#ffedd5; color:#9a3412; }
    .badge-medium       { background:#fef9c3; color:#854d0e; }
    .badge-low          { background:#d1fae5; color:#065f46; }

    /* ── Lifecycle state badges ── */
    .badge-state-logged      { background:#f3f4f6; color:#374151; }
    .badge-state-active      { background:#dbeafe; color:#1e40af; }
    .badge-state-waiting     { background:#fef9c3; color:#92400e; }
    .badge-state-probable    { background:#d1fae5; color:#065f46; }
    .badge-state-unresolved  { background:#fee2e2; color:#991b1b; }
    .badge-state-escalated   { background:#fde8ff; color:#6b21a8; }
    .badge-state-sme         { background:#ede9fe; color:#4c1d95; }
    .badge-state-gap         { background:#fff7ed; color:#9a3412; }
    .badge-state-resolved    { background:#dcfce7; color:#14532d; }
    .badge-state-closed      { background:#e5e7eb; color:#374151; }

    /* ── Role badges ── */
    .role-badge {
        display: inline-block; padding: 2px 9px; border-radius: 10px;
        font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.06em; color: white;
    }

    /* ── Evidence ── */
    .evidence-chunk {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-left: 3px solid #6366f1; border-radius: 4px;
        padding: 10px 12px; margin-bottom: 8px;
        font-size: 0.82rem; line-height: 1.6;
    }
    .evidence-meta { font-size: 0.7rem; color: #6b7280; margin-bottom: 6px; font-weight: 600; }

    /* ── Login ── */
    .login-logo { text-align:center; margin-bottom:32px; }
    .login-logo h1 { font-size:2rem; font-weight:800; color:#1a1f36; margin:8px 0 4px 0; }

    /* ── Report ── */
    .report-section {
        background:white; border:1px solid #e5e7eb; border-radius:8px;
        padding:20px; margin-bottom:16px;
    }
    .report-section h4 {
        color:#374151; margin:0 0 12px 0; font-size:0.9rem;
        font-weight:700; text-transform:uppercase; letter-spacing:0.05em;
    }

    /* ── SME / KE action panels ── */
    .action-panel {
        background:#faf5ff; border:1px solid #e9d5ff; border-radius:8px;
        padding:16px; margin-bottom:12px;
    }
    .action-panel-sme { background:#faf5ff; border-color:#c4b5fd; }
    .action-panel-ke  { background:#f0fdf4; border-color:#86efac; }
    .action-panel-gap {
        background:#fff7ed; border:1px solid #fed7aa;
        border-left:4px solid #f97316; border-radius:6px;
        padding:12px 16px; margin-bottom:10px;
    }

    /* ── Admin table ── */
    .admin-user-row {
        background:white; border:1px solid #e5e7eb; border-radius:6px;
        padding:12px 16px; margin-bottom:8px;
        display:flex; align-items:center; justify-content:space-between;
    }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 6px; font-weight: 600; font-size: 0.9rem; transition: all 0.2s;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        border: none; color: white; padding: 10px 24px;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════

def init_session_state():
    defaults = {
        "screen":                 "login",
        "token":                  None,
        "user":                   None,
        "current_session_id":     None,
        "messages":               [],
        "evidence":               [],
        "session_state_data":     {},
        "measurements_submitted": [],
        "pending_evidence":       [],
        "pending_questions":      [],
        "similar_matches":        [],
        "pending_intake":         {},
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


def _role() -> str:
    """Return current user's role. Defaults to 'ME' if role is missing/null."""
    user = st.session_state.get("user")
    if not user:
        return ""
    return user.get("role") or "ME"


def _has_role(*roles: str) -> bool:
    return _role() in roles


def _landing_screen_for_role(role: str) -> str:
    """Which screen to land on after login."""
    if role == "KE":
        return "knowledge_gaps"
    if role == "ADM":
        return "admin"
    if role == "SUP":
        return "dashboard"
    return "intake"   # ME, SME


# ═══════════════════════════════════════════════════════════════════
# API HELPERS
# ═══════════════════════════════════════════════════════════════════

def api(method: str, path: str, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    url = f"{BACKEND_URL}{path}"
    timeout = kwargs.pop("timeout", 120)
    return getattr(requests, method)(url, headers=headers, timeout=timeout, **kwargs)


def handle_api_error(resp: requests.Response, context: str = "") -> bool:
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        st.error(f"{context}: {detail}")
        return False
    return True


# ═══════════════════════════════════════════════════════════════════
# TOP NAVIGATION BAR
# ═══════════════════════════════════════════════════════════════════

def render_top_bar():
    user = st.session_state.user
    role = _role()

    col1, col2 = st.columns([6, 4])

    with col1:
        role_color = ROLE_COLORS.get(role, "#6b7280")
        role_label = ROLE_LABELS.get(role, role)
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:14px; padding: 6px 0;">
            <span style="font-size:2.6rem; line-height:1;">🏗️</span>
            <div>
                <div style="font-size:1.45rem; font-weight:800; color:#1a1f36; line-height:1.25;">
                    AI-Assisted Process Guidance
                </div>
                <div style="font-size:0.78rem; color:#6b7280; margin-top:2px;">
                    Industrial Crane Maintenance Troubleshooting System
                    &nbsp;&nbsp;
                    <span class="role-badge" style="background:{role_color};">{role}</span>
                    &nbsp;<span style="color:#9ca3af;">{role_label}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        if user:
            # Build nav buttons based on role
            nav_buttons = []
            if _has_role("ME"):
                nav_buttons.append(("📋 New Issue", "intake"))
            if not _has_role("ADM"):
                nav_buttons.append(("📊 Dashboard", "dashboard"))
            if _has_role("SME"):
                nav_buttons.append(("📥 SME Inbox", "sme_inbox"))
            if _has_role("KE", "SME"):
                nav_buttons.append(("🔍 Knowledge Gaps", "knowledge_gaps"))
            if _has_role("ADM"):
                nav_buttons.append(("⚙️ Admin", "admin"))

            # +2: one column for the notification bell, one for the user popover
            nav_cols = st.columns(len(nav_buttons) + 2)
            for i, (label, screen) in enumerate(nav_buttons):
                with nav_cols[i]:
                    if st.button(label, use_container_width=True):
                        _nav(screen)

            # Notification bell — shown to all logged-in users
            notif_count = 0
            try:
                nc_resp = api("get", "/notifications/unread-count")
                if nc_resp.status_code == 200:
                    notif_count = nc_resp.json().get("unread_count", 0)
            except Exception:
                pass

            bell_label = f"🔔 {notif_count}" if notif_count > 0 else "🔔"
            with nav_cols[-2] if len(nav_cols) > 1 else nav_cols[-1]:
                with st.popover(bell_label, use_container_width=True):
                    st.markdown("**Notifications**")
                    try:
                        notif_resp = api("get", "/notifications?unread_only=false")
                        if notif_resp.status_code == 200:
                            notifs = notif_resp.json()[:10]
                            if not notifs:
                                st.caption("No notifications.")
                            else:
                                for n in notifs:
                                    read_icon = "" if n.get("is_read") else "🔵 "
                                    st.markdown(
                                        f"{read_icon}{n['message']}  \n"
                                        f"<span style='font-size:0.72rem;color:#9ca3af;'>"
                                        f"{_format_date(n.get('created_at',''))}</span>",
                                        unsafe_allow_html=True,
                                    )
                                    if not n.get("is_read"):
                                        api("put", f"/notifications/{n['id']}/read")
                                    st.divider()
                        else:
                            st.caption("Could not load notifications.")
                    except Exception:
                        st.caption("Notification service unavailable.")

            with nav_cols[-1]:
                with st.popover(f"👤 {user['name']}", use_container_width=True):
                    role_color = ROLE_COLORS.get(role, "#6b7280")
                    st.markdown(f"""
                    <div style="padding:4px 0 10px 0;">
                        <div style="font-size:0.95rem; font-weight:700; color:#1a1f36;">{user['name']}</div>
                        <div style="font-size:0.78rem; color:#6b7280;">@{user['username']}</div>
                        <div style="margin-top:6px;">
                            <span class="role-badge" style="background:{role_color};">{role}</span>
                            <span style="font-size:0.78rem; color:#6b7280; margin-left:6px;">
                                {ROLE_LABELS.get(role, '')}
                            </span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.divider()
                    if st.button("🚪 Logout", use_container_width=True, type="primary"):
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        init_session_state()
                        st.rerun()

    st.divider()


def _nav(screen: str):
    """Navigate to a screen, resetting intake-specific state if needed."""
    if screen == "intake":
        st.session_state.current_session_id = None
        st.session_state.messages = []
        st.session_state.evidence = []
        st.session_state.measurements_submitted = []
    st.session_state.screen = screen
    st.rerun()


# ═══════════════════════════════════════════════════════════════════
# SCREEN 1: LOGIN / SIGNUP
# ═══════════════════════════════════════════════════════════════════

def screen_login():
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_center:
        st.markdown("""
        <div style="text-align:center; padding: 32px 0 24px 0;">
            <div style="font-size:3.5rem;">🏗️</div>
            <h1 style="font-size:1.9rem; font-weight:800; color:#1a1f36; margin:8px 0 4px 0;">
                Crane AI
            </h1>
            <p style="color:#6b7280; font-size:0.95rem; margin:0;">
                AI-Assisted Industrial Process Guidance Tool<br>
                <span style="font-size:0.82rem;">For Crane Maintenance Engineers</span>
            </p>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["🔐  Sign In", "✨  Create Account"])

        with tab_login:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("login_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Sign In →", use_container_width=True, type="primary")

                if submitted:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    else:
                        with st.spinner("Signing in..."):
                            resp = api("post", "/auth/login",
                                       json={"username": username, "password": password})
                        if handle_api_error(resp, "Login failed"):
                            data = resp.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.user  = data["user"]
                            role = data["user"].get("role", "ME")
                            st.session_state.screen = _landing_screen_for_role(role)
                            st.success(f"Welcome back, {data['user']['name']}!")
                            st.rerun()

        with tab_signup:
            st.markdown("<br>", unsafe_allow_html=True)

            # Role selector is OUTSIDE the form so it updates in real-time
            # (inside st.form, widgets don't rerun until Submit is clicked,
            #  causing the hint to always show "ME" regardless of selection)
            role_options = [f"{r} – {ROLE_LABELS[r]}" for r in SIGNUP_ROLES]
            role_selected = st.selectbox(
                "Role",
                options=role_options,
                key="signup_role_select",
                help="Select your role. Administrator accounts must be assigned by an existing admin.",
            )
            role_code = role_selected.split(" – ")[0]
            role_color = ROLE_COLORS.get(role_code, "#6b7280")
            st.markdown(
                f'<div style="font-size:0.78rem;color:#6b7280;margin-top:-6px;margin-bottom:12px;">'
                f'<span class="role-badge" style="background:{role_color};">{role_code}</span>'
                f'&nbsp; {_role_description(role_code)}</div>',
                unsafe_allow_html=True,
            )

            with st.form("signup_form", clear_on_submit=False):
                name         = st.text_input("Full Name", placeholder="e.g. Karl Müller")
                new_username = st.text_input("Username", placeholder="Choose a username")
                new_password = st.text_input("Password", type="password", placeholder="Choose a strong password")
                confirm_pw   = st.text_input("Confirm Password", type="password", placeholder="Repeat your password")

                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Create Account →", use_container_width=True, type="primary")

                if submitted:
                    # Read role from session_state (set by the selectbox outside the form)
                    selected_role = st.session_state.get("signup_role_select", role_options[0])
                    final_role_code = selected_role.split(" – ")[0]

                    if not all([name, new_username, new_password, confirm_pw]):
                        st.error("All fields are required.")
                    elif new_password != confirm_pw:
                        st.error("Passwords do not match.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        with st.spinner("Creating account..."):
                            resp = api("post", "/auth/signup",
                                       json={"name": name, "username": new_username,
                                             "password": new_password, "role": final_role_code})
                        if handle_api_error(resp, "Signup failed"):
                            data = resp.json()
                            st.session_state.token  = data["access_token"]
                            st.session_state.user   = data["user"]
                            confirmed_role = data["user"].get("role", "ME")
                            st.session_state.screen = _landing_screen_for_role(confirmed_role)
                            st.success(f"Account created! Welcome, {data['user']['name']} ({confirmed_role})!")
                            st.rerun()

        st.markdown("""
        <div style="text-align:center; color:#9ca3af; font-size:0.78rem; padding-top:32px;">
            Fraunhofer IESE · Master Thesis Prototype · 2025
        </div>
        """, unsafe_allow_html=True)


def _role_description(role: str) -> str:
    return {
        "ME":  "Performs day-to-day fault diagnosis, records measurements, generates reports.",
        "SME": "Senior expert who handles escalated cases, annotates diagnoses, validates root causes.",
        "KE":  "Knowledge Engineer who manages the knowledge base and resolves knowledge gaps.",
        "SUP": "Supervisor with read-only access to all sessions and cross-engineer reports.",
        "ADM": "System Administrator managing users, roles, and audit logs.",
    }.get(role, "")


# ═══════════════════════════════════════════════════════════════════
# SCREEN 2: ISSUE INTAKE FORM
# ═══════════════════════════════════════════════════════════════════

def screen_intake():
    render_top_bar()

    st.markdown("""
    <div style="margin-bottom:20px;">
        <h2 style="font-size:1.4rem; font-weight:700; color:#1a1f36; margin:0 0 4px 0;">
            📋 New Troubleshooting Session
        </h2>
        <p style="color:#6b7280; font-size:0.9rem; margin:0;">
            Provide issue details below. The AI will use this context to start targeted diagnostics immediately.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # crane_type must be outside the form so changing it reruns and updates the component list
    st.markdown('<div class="section-header">Crane & Component</div>', unsafe_allow_html=True)
    crane_type = st.selectbox(
        "Crane Type *",
        options=list(CRANE_COMPONENTS.keys()),
        help="Select the crane model being investigated",
    )
    components = CRANE_COMPONENTS.get(crane_type, [])

    with st.form("intake_form"):
        col1, col2 = st.columns(2)

        with col1:
            component  = st.selectbox(
                "Component *",
                options=components,
                help="Select the specific component with the issue",
            )

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<div class="section-header">Problem Description</div>', unsafe_allow_html=True)

            problem_description = st.text_area(
                "Describe the fault or observed behaviour *",
                placeholder=(
                    "e.g. Motor runs but load does not lift. "
                    "Heard a loud click when attempting to hoist 3t load. "
                    "Motor current was normal but no drum rotation."
                ),
                height=130,
                help="Describe exactly what you observe. Be as specific as possible.",
            )

        with col2:
            st.markdown('<div class="section-header">Optional Context</div>', unsafe_allow_html=True)

            environment = st.text_area(
                "Environmental Conditions",
                placeholder="e.g. Outdoor, ambient ~35°C, high dust from nearby grinding.",
                height=90,
            )
            recent_changes = st.text_area(
                "Recent Maintenance / Changes",
                placeholder="e.g. Brake disc replaced 2 weeks ago.",
                height=90,
            )
            error_messages = st.text_area(
                "Error Messages / Fault Codes",
                placeholder="e.g. PLC display shows E09 (motor thermal trip).",
                height=90,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
        with col_btn2:
            submitted = st.form_submit_button(
                "🚀 Start AI Diagnostics",
                use_container_width=True,
                type="primary",
            )

        if submitted:
            if not problem_description.strip():
                st.error("Problem description is required.")
            else:
                payload = {
                    "crane_type":          crane_type,
                    "component":           component,
                    "problem_description": problem_description.strip(),
                    "environment":         environment.strip() or None,
                    "recent_changes":      recent_changes.strip() or None,
                    "error_messages":      error_messages.strip() or None,
                }
                # Check for previously resolved similar sessions first
                with st.spinner("🔍 Checking for known solutions..."):
                    sim_resp = api("post", "/sessions/find-similar", json=payload)
                if sim_resp.status_code == 200:
                    matches = sim_resp.json().get("matches", [])
                    if matches:
                        st.session_state.similar_matches = matches
                        st.session_state.pending_intake = payload
                        st.session_state.screen = "similar_found"
                        st.rerun()
                        return

                # No match — create session and go straight to diagnosis
                with st.spinner("🤖 Creating session and loading AI context..."):
                    resp = api("post", "/sessions", json=payload)
                if handle_api_error(resp, "Failed to create session"):
                    data = resp.json()
                    session_id  = data["session_id"]
                    opening_msg = data.get("opening_message", "")
                    evidence    = data.get("retrieved_evidence", [])
                    st.session_state.current_session_id = session_id
                    st.session_state.messages = [{"role": "assistant", "content": opening_msg,
                                                   "confidence": data.get("knowledge_confidence", "high"),
                                                   "confidence_reason": data.get("confidence_reason", "")}]
                    st.session_state.evidence = evidence
                    st.session_state.session_state_data = {
                        "component":          component,
                        "crane_type":         crane_type,
                        "lifecycle_state":    data.get("lifecycle_state", "IN_PROGRESS"),
                        "completed_steps":    [],
                        "likely_causes":      [],
                        "current_hypothesis": None,
                    }
                    st.session_state.measurements_submitted = []
                    st.session_state.pending_questions = data.get("questions", [])
                    st.session_state.screen = "guidance"
                    st.rerun()


def screen_similar_found():
    """Show previously resolved similar sessions. Let user apply the known fix or start fresh."""
    render_top_bar()
    matches  = st.session_state.get("similar_matches", [])
    payload  = st.session_state.get("pending_intake", {})

    st.markdown("""
    <div style="background:#f0fdf4;border:1px solid #86efac;border-left:4px solid #16a34a;
                border-radius:8px;padding:16px 20px;margin-bottom:20px;">
        <h3 style="color:#15803d;margin:0 0 6px 0;font-size:1.1rem;">
            ✅ Known Fault Found
        </h3>
        <p style="color:#166534;margin:0;font-size:0.9rem;">
            A previous engineer already resolved the same fault on this component.
            Review the report below. If it matches your issue, apply it directly —
            no diagnostic steps needed. Otherwise start a fresh diagnosis.
        </p>
    </div>
    """, unsafe_allow_html=True)

    for i, match in enumerate(matches):
        sev   = match.get("severity", "medium")
        sev_color = SEVERITY_COLORS.get(sev, "#888")
        sev_icon  = SEVERITY_ICONS.get(sev, "⚪")

        with st.expander(
            f"Session #{match['session_id']} — {match['component']} — {match['crane_type']} "
            f"  ({match.get('created_at', '')})",
            expanded=(i == 0),
        ):
            st.markdown(
                f'<span style="background:{sev_color}22;color:{sev_color};border:1px solid {sev_color}55;'
                f'border-radius:10px;padding:2px 10px;font-size:0.78rem;font-weight:700;">'
                f'{sev_icon} {sev.upper()}</span>',
                unsafe_allow_html=True,
            )
            st.markdown("**Previous problem reported:**")
            st.info(match.get("problem_description", ""))

            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.markdown("**Root Cause**")
                st.markdown(match.get("root_cause") or "_Not recorded_")
                st.markdown("**Diagnosis**")
                st.markdown(match.get("diagnosis", ""))
            with col_r2:
                st.markdown("**Steps Taken**")
                steps = _parse_list(match.get("steps_taken", "[]"))
                for s in steps:
                    st.markdown(f"✓ {s}")
                st.markdown("**Recommendations**")
                recs = _parse_list(match.get("recommendations", "[]"))
                for r in recs:
                    st.markdown(f"• {r}")

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                if st.button(
                    "✅ This fixes my issue — Apply & Close",
                    key=f"apply_{match['session_id']}",
                    type="primary", use_container_width=True,
                ):
                    with st.spinner("Creating session and applying known fix..."):
                        # Create a minimal session
                        resp = api("post", "/sessions", json=payload)
                    if handle_api_error(resp, "Failed to create session"):
                        new_id = resp.json()["session_id"]
                        close_resp = api(
                            "post", f"/sessions/{new_id}/close-with-known-fix",
                            json={"reference_session_id": match["session_id"]},
                        )
                        if handle_api_error(close_resp, "Failed to apply fix"):
                            st.session_state.similar_matches = []
                            st.session_state.pending_intake  = {}
                            st.session_state.screen = "dashboard"
                            st.success("Known fix applied. Session closed with report.")
                            st.rerun()
            with c2:
                if st.button(
                    "🔍 My issue is different — Start new diagnosis",
                    key=f"fresh_{match['session_id']}",
                    use_container_width=True,
                ):
                    with st.spinner("🤖 Starting new diagnostic session..."):
                        resp = api("post", "/sessions", json=payload)
                    if handle_api_error(resp, "Failed to create session"):
                        data = resp.json()
                        st.session_state.current_session_id = data["session_id"]
                        st.session_state.messages = [{"role": "assistant",
                            "content": data.get("opening_message", ""),
                            "confidence": data.get("knowledge_confidence", "high"),
                            "confidence_reason": data.get("confidence_reason", "")}]
                        st.session_state.evidence  = data.get("retrieved_evidence", [])
                        st.session_state.session_state_data = {
                            "component":          payload["component"],
                            "crane_type":         payload["crane_type"],
                            "lifecycle_state":    data.get("lifecycle_state", "IN_PROGRESS"),
                            "completed_steps":    [], "likely_causes": [],
                            "current_hypothesis": None,
                        }
                        st.session_state.measurements_submitted = []
                        st.session_state.pending_questions = data.get("questions", [])
                        st.session_state.similar_matches   = []
                        st.session_state.pending_intake    = {}
                        st.session_state.screen = "guidance"
                        st.rerun()


def _render_assistant_message(content: str, confidence: str = "high", confidence_reason: str = ""):
    """Render an AI message with optional confidence badge and highlighted question."""
    paragraphs = [p.strip() for p in content.strip().split("\n\n") if p.strip()]
    if not paragraphs:
        st.markdown(content)
    else:
        question_paras = []
        body_paras = []
        for i, para in enumerate(paragraphs):
            if "?" in para and i >= len(paragraphs) - 2:
                question_paras.append(para)
            else:
                body_paras.append(para)
        if body_paras:
            st.markdown("\n\n".join(body_paras))
        if question_paras:
            q_text = "\n\n".join(question_paras)
            st.markdown(
                f'<div class="ai-question-box"><p>{q_text}</p></div>',
                unsafe_allow_html=True,
            )
        elif not body_paras:
            st.markdown(content)

    if confidence == "low":
        reason_text = f" — {confidence_reason}" if confidence_reason else ""
        st.markdown(
            f'<div style="margin-top:8px;background:#fff7ed;border:1px solid #fed7aa;'
            f'border-left:3px solid #f97316;border-radius:5px;padding:5px 10px;'
            f'font-size:0.78rem;color:#9a3412;">'
            f'⚠️ <b>Low knowledge base coverage</b>{reason_text}. '
            f'Consider flagging a knowledge gap if guidance is insufficient.</div>',
            unsafe_allow_html=True,
        )
    elif confidence == "medium":
        reason_text = f" — {confidence_reason}" if confidence_reason else ""
        st.markdown(
            f'<div style="margin-top:8px;background:#fefce8;border:1px solid #fde68a;'
            f'border-left:3px solid #eab308;border-radius:5px;padding:5px 10px;'
            f'font-size:0.78rem;color:#713f12;">'
            f'ℹ️ <b>Partial knowledge base coverage</b>{reason_text}. '
            f'Guidance may be incomplete.</div>',
            unsafe_allow_html=True,
        )


def _render_structured_input(session_id: int, is_closed: bool, lifecycle: str):
    """Render structured question widgets or fall back to plain text area."""
    questions = st.session_state.get("pending_questions", [])

    if is_closed or not _has_role("ME", "SME"):
        if is_closed:
            st.info("Session closed. View the generated report in the Dashboard.")
        return

    def _store_response(data: dict, sent_text: str):
        st.session_state.messages.append({"role": "user", "content": sent_text})
        st.session_state.messages.append({
            "role": "assistant",
            "content": data["message"]["content"],
            "confidence": data.get("knowledge_confidence", "high"),
            "confidence_reason": data.get("confidence_reason", ""),
        })
        st.session_state.evidence = data.get("retrieved_evidence", [])
        ss = data.get("session_state", {})
        st.session_state.session_state_data.update({
            "completed_steps":    ss.get("completed_steps", []),
            "likely_causes":      ss.get("likely_causes", []),
            "current_hypothesis": ss.get("current_hypothesis"),
            "lifecycle_state":    ss.get("lifecycle_state", lifecycle),
        })
        st.session_state.pending_questions = data.get("questions", [])

    if questions:
        st.markdown(
            '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'
            'padding:12px 16px;margin-bottom:6px;">'
            '<span style="font-size:0.78rem;font-weight:700;color:#475569;'
            'text-transform:uppercase;letter-spacing:0.05em;">Answer each question below</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        with st.form("structured_input_form", clear_on_submit=True):
            answers = {}
            for i, q in enumerate(questions):
                q_type = q.get("type", "text")
                q_text = q.get("text", "")
                st.markdown(
                    f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:6px;'
                    f'padding:10px 14px;margin-bottom:4px;">'
                    f'<span style="font-size:0.82rem;font-weight:600;color:#374151;">Q{i+1}. {q_text}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if q_type == "yesno":
                    answers[i] = st.radio(
                        f"q{i}", ["Yes", "No", "Not checked yet"],
                        key=f"sq_{i}", horizontal=True, label_visibility="collapsed",
                    )
                elif q_type == "number":
                    unit = q.get("unit", "")
                    answers[i] = st.text_input(
                        f"Value{' (' + unit + ')' if unit else ''}",
                        key=f"sq_{i}", placeholder=f"Enter value{' in ' + unit if unit else ''}",
                    )
                elif q_type == "choice":
                    options = q.get("options", ["—"])
                    answers[i] = st.selectbox(f"q{i}", options, key=f"sq_{i}", label_visibility="collapsed")
                else:
                    answers[i] = st.text_area(f"q{i}", key=f"sq_{i}", height=55, label_visibility="collapsed",
                                               placeholder="Type your observation...")

            extra = st.text_input(
                "Additional observation (optional)", key="sq_extra",
                placeholder="Any other finding not covered above...",
            )
            send_btn = st.form_submit_button("Send Answers →", type="primary")

        if send_btn:
            parts = []
            for i, q in enumerate(questions):
                ans = answers.get(i)
                if ans is not None and str(ans).strip() not in ("", "—"):
                    parts.append(f"{q['text']}: {ans}")
            if extra and extra.strip():
                parts.append(extra.strip())
            if parts:
                assembled = "\n".join(parts)
                with st.spinner("🤖 Analysing..."):
                    resp = api("post", f"/sessions/{session_id}/chat", json={"message": assembled})
                if handle_api_error(resp, "Chat failed"):
                    _store_response(resp.json(), assembled)
                    st.rerun()
            else:
                st.warning("Please answer at least one question before sending.")
    else:
        # Fallback: plain text area
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "Your response",
                placeholder=(
                    "Type your observations, measurements, or answers here...\n"
                    "e.g. 'Voltage on L1: 402V, L2: 398V, L3: 401V. Motor humming but not rotating.'"
                ),
                height=90, label_visibility="collapsed",
            )
            col_f1, col_f2 = st.columns([4, 1])
            with col_f2:
                send_btn = st.form_submit_button("Send →", use_container_width=True, type="primary")

        if send_btn and user_input.strip():
            with st.spinner("🤖 Analysing..."):
                resp = api("post", f"/sessions/{session_id}/chat", json={"message": user_input.strip()})
            if handle_api_error(resp, "Chat failed"):
                _store_response(resp.json(), user_input.strip())
                st.rerun()


# ═══════════════════════════════════════════════════════════════════
# SCREEN 3: AI GUIDANCE INTERFACE
# ═══════════════════════════════════════════════════════════════════

def screen_guidance():
    render_top_bar()

    session_id = st.session_state.current_session_id
    if not session_id:
        st.warning("No active session. Please start from the intake form.")
        st.session_state.screen = "intake"
        st.rerun()

    # Refresh session state from backend
    session_resp = api("get", f"/sessions/{session_id}")
    if session_resp.status_code == 200:
        sdata = session_resp.json()
        lifecycle = sdata.get("lifecycle_state", "IN_PROGRESS")
        st.session_state.session_state_data = {
            "component":          sdata["component"],
            "crane_type":         sdata["crane_type"],
            "lifecycle_state":    lifecycle,
            "completed_steps":    _parse_list(sdata.get("completed_steps")),
            "likely_causes":      _parse_list(sdata.get("likely_causes")),
            "current_hypothesis": sdata.get("current_hypothesis"),
            "escalation_reason":  sdata.get("escalation_reason"),
        }
    else:
        lifecycle = st.session_state.session_state_data.get("lifecycle_state", "IN_PROGRESS")

    ssd  = st.session_state.session_state_data
    role = _role()
    is_closed = lifecycle == "CLOSED_WITH_REPORT"

    # ── Knowledge-updated banner ──────────────────────────────────
    # Show when the session was previously in KNOWLEDGE_GAP_FLAGGED and is now
    # back to IN_PROGRESS — meaning a KE has resolved the gap.
    if lifecycle == "IN_PROGRESS" and _has_role("ME", "SME"):
        # Check if there is a resolved gap for this session
        try:
            gaps_resp = api("get", f"/knowledge-gaps?include_resolved=true")
            if gaps_resp.status_code == 200:
                session_gaps = [
                    g for g in gaps_resp.json()
                    if g.get("session_id") == session_id and g.get("status") == "resolved"
                ]
                if session_gaps:
                    latest_gap = session_gaps[0]
                    st.success(
                        f"✅ **Knowledge base updated!** A Knowledge Engineer has resolved the "
                        f"knowledge gap for **{latest_gap.get('component_key', '')}** "
                        f"(Gap #{latest_gap.get('id')}). "
                        f"You can now continue diagnosis — the AI has access to the updated knowledge."
                    )
        except Exception:
            pass

    # ── Header ───────────────────────────────────────────────────
    col_h1, col_h2, col_h3 = st.columns([3, 1, 1])
    with col_h1:
        lc_label = LIFECYCLE_LABELS.get(lifecycle, lifecycle)
        lc_class = LIFECYCLE_BADGE_CLASS.get(lifecycle, "badge-state-active")
        st.markdown(f"""
        <div style="margin-bottom:12px;">
            <h2 style="font-size:1.3rem; font-weight:700; color:#1a1f36; margin:0 0 4px 0;">
                🔍 Diagnostic Session #{session_id}
            </h2>
            <p style="color:#6b7280; font-size:0.85rem; margin:0;">
                <b>{ssd.get('crane_type','')}</b> · {ssd.get('component','')}
                &nbsp;&nbsp;
                <span class="badge {lc_class}">{lc_label}</span>
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_h2:
        # Generate report button — available if not closed
        if not is_closed and _has_role("ME", "SME"):
            if st.button("⚡ Generate Report", type="primary", use_container_width=True):
                with st.spinner("Generating report..."):
                    resp = api("post", f"/sessions/{session_id}/report")
                if handle_api_error(resp, "Report generation failed"):
                    st.success("Report generated!")
                    st.session_state.screen = "dashboard"
                    st.rerun()

    with col_h3:
        # Escalate button — only for ME when session is active and not escalated
        can_escalate = (
            role == "ME"
            and lifecycle in ("IN_PROGRESS", "AWAITING_MEASUREMENT", "UNRESOLVED",
                               "PROBABLE_CAUSE_IDENTIFIED")
        )
        if can_escalate:
            if st.button("🚨 Escalate", use_container_width=True):
                st.session_state._show_escalate_dialog = True
                st.rerun()

    # Escalation dialog
    if st.session_state.get("_show_escalate_dialog"):
        with st.container():
            st.markdown("""
            <div style="background:#faf5ff;border:1px solid #c4b5fd;border-radius:8px;
                         padding:16px;margin-bottom:16px;">
                <b style="color:#5b21b6;">Escalate to SME Review</b>
            </div>
            """, unsafe_allow_html=True)
            with st.form("escalate_form"):
                reason = st.text_area(
                    "Escalation reason *",
                    placeholder="Describe why this case requires senior engineer review...",
                    height=80,
                )
                ec1, ec2 = st.columns(2)
                with ec1:
                    if st.form_submit_button("🚨 Confirm Escalation", type="primary", use_container_width=True):
                        if not reason.strip():
                            st.error("Please provide a reason for escalation.")
                        else:
                            resp = api("post", f"/sessions/{session_id}/escalate",
                                       json={"reason": reason.strip()})
                            if handle_api_error(resp, "Escalation failed"):
                                st.success("Session escalated to SME review.")
                                st.session_state._show_escalate_dialog = False
                                st.rerun()
                with ec2:
                    if st.form_submit_button("Cancel", use_container_width=True):
                        st.session_state._show_escalate_dialog = False
                        st.rerun()

    # SME Actions bar — for SME on escalated/SME-review sessions
    if role == "SME" and lifecycle in ("ESCALATED", "SME_IN_REVIEW"):
        _render_sme_action_bar(session_id, lifecycle, ssd)

    # ── Layout ───────────────────────────────────────────────────
    chat_col, right_col = st.columns([3, 2])

    # ── LEFT: Chat ───────────────────────────────────────────────
    with chat_col:
        st.markdown('<div class="section-header">💬 AI-Guided Diagnostic Process</div>', unsafe_allow_html=True)

        # Diagnostic phase strip
        steps_done = len(ssd.get("completed_steps", []))
        if lifecycle in ("RESOLVED", "CLOSED_WITH_REPORT"):
            _phase = 3
        elif lifecycle == "PROBABLE_CAUSE_IDENTIFIED" or steps_done >= 4:
            _phase = 2
        elif steps_done >= 1:
            _phase = 1
        else:
            _phase = 0

        def _phase_pill(label, idx, active_idx):
            if idx < active_idx:
                bg, color, border = "#dcfce7", "#166534", "#86efac"
                prefix = "✓ "
            elif idx == active_idx:
                bg, color, border = "#eff6ff", "#1d4ed8", "#93c5fd"
                prefix = "● "
            else:
                bg, color, border = "#f9fafb", "#9ca3af", "#e5e7eb"
                prefix = ""
            return (
                f'<span style="background:{bg};color:{color};border:1px solid {border};'
                f'border-radius:12px;padding:2px 10px;font-size:0.75rem;font-weight:600;'
                f'white-space:nowrap;">{prefix}{label}</span>'
            )

        phases = ["Intake", "Investigation", "Root Cause", "Resolution"]
        pills = " &nbsp;→&nbsp; ".join(_phase_pill(p, i, _phase) for i, p in enumerate(phases))
        st.markdown(
            f'<div style="margin-bottom:10px;padding:6px 2px;">{pills}</div>',
            unsafe_allow_html=True,
        )

        for msg in st.session_state.messages:
            if msg["role"] == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    _render_assistant_message(
                        msg["content"],
                        msg.get("confidence", "high"),
                        msg.get("confidence_reason", ""),
                    )
            else:
                with st.chat_message("user", avatar="👷"):
                    st.markdown(msg["content"])

        st.markdown("<br>", unsafe_allow_html=True)

        _render_structured_input(session_id, is_closed, lifecycle)

    # ── RIGHT: Tabs ──────────────────────────────────────────────
    with right_col:
        tab_labels = ["📐 Measurements", "📚 Evidence", "📊 Session State"]
        if role == "SME":
            tab_labels.append("📝 Annotations")

        right_tabs = st.tabs(tab_labels)

        # Tab 1: Measurements
        with right_tabs[0]:
            _render_measurement_tab(session_id)

        # Tab 2: Evidence
        with right_tabs[1]:
            _render_evidence_tab()

        # Tab 3: Session State
        with right_tabs[2]:
            _render_session_state_tab(ssd)

        # Tab 4: Annotations (SME only)
        if role == "SME" and len(right_tabs) > 3:
            with right_tabs[3]:
                _render_annotations_tab(session_id)


def _render_sme_action_bar(session_id: int, lifecycle: str, ssd: dict):
    """SME action strip shown above chat when viewing escalated/in-review sessions."""
    st.markdown("""
    <div class="action-panel action-panel-sme">
        <b style="color:#5b21b6; font-size:0.85rem;">👨‍🔬 SME Actions</b>
        &nbsp;—&nbsp;
        <span style="font-size:0.82rem; color:#6b7280;">
            You are reviewing an escalated session
        </span>
    </div>
    """, unsafe_allow_html=True)

    reason = ssd.get("escalation_reason")
    if reason:
        st.info(f"**Escalation reason:** {reason}")

    # Show advisory if any AI message had low confidence
    low_conf_msgs = [
        m for m in st.session_state.get("messages", [])
        if m.get("role") == "assistant" and m.get("confidence") == "low"
    ]
    if low_conf_msgs:
        reasons = list({m.get("confidence_reason", "") for m in low_conf_msgs if m.get("confidence_reason")})
        reason_text = f": {reasons[0]}" if reasons else ""
        st.warning(
            f"⚠️ **Knowledge gap detected** — the AI reported low knowledge base coverage on "
            f"{len(low_conf_msgs)} message(s){reason_text}. "
            f"Review the highlighted messages below and consider clicking **Flag Knowledge Gap**."
        )

    ac1, ac2, ac3, ac4 = st.columns(4)

    with ac1:
        if lifecycle == "ESCALATED":
            if st.button("🔬 Open for Review", use_container_width=True, type="primary"):
                resp = api("post", f"/sessions/{session_id}/sme-review")
                if handle_api_error(resp, "Failed to start SME review"):
                    st.success("Session now in SME Review.")
                    st.rerun()

    with ac2:
        if lifecycle == "SME_IN_REVIEW":
            if st.button("✅ Mark Resolved", use_container_width=True):
                resp = api("post", f"/sessions/{session_id}/resolve")
                if handle_api_error(resp, "Failed to resolve"):
                    st.success("Session resolved.")
                    st.rerun()

    with ac3:
        if lifecycle == "SME_IN_REVIEW":
            if st.button("⚠️ Flag Knowledge Gap", use_container_width=True):
                resp = api("post", f"/sessions/{session_id}/flag-knowledge-gap")
                if handle_api_error(resp, "Failed to flag gap"):
                    st.success("Knowledge gap flagged.")
                    st.rerun()

    with ac4:
        st.markdown("")  # spacer


def _render_measurement_tab(session_id: int):
    st.markdown('<div class="section-header">Record Measurements</div>', unsafe_allow_html=True)

    with st.form("measurement_form", clear_on_submit=True):
        mcol1, mcol2 = st.columns(2)
        with mcol1:
            voltage    = st.number_input("Voltage (V)", min_value=0.0, max_value=1000.0,
                                          value=None, format="%.1f", placeholder="e.g. 400.0")
            temperature = st.number_input("Temperature (°C)", min_value=-50.0, max_value=300.0,
                                           value=None, format="%.1f", placeholder="e.g. 65.0")
            brake_gap  = st.number_input("Brake Gap (mm)", min_value=0.0, max_value=10.0,
                                          value=None, format="%.2f", placeholder="e.g. 0.25")
            insulation_res = st.number_input("Insulation Res. (MΩ)", min_value=0.0,
                                              value=None, format="%.2f", placeholder="e.g. 5.0")
        with mcol2:
            current   = st.number_input("Current (A)", min_value=0.0, max_value=2000.0,
                                         value=None, format="%.2f", placeholder="e.g. 12.5")
            load      = st.number_input("Load (kg)", min_value=0.0, max_value=100000.0,
                                         value=None, format="%.0f", placeholder="e.g. 2500")
            vibration = st.number_input("Vibration (mm/s RMS)", min_value=0.0, max_value=100.0,
                                         value=None, format="%.2f", placeholder="e.g. 2.1")
            notes     = st.text_input("Notes", placeholder="Any additional observations")

        save_meas = st.form_submit_button("💾 Save Measurements", use_container_width=True)

    if save_meas:
        payload = {
            k: v for k, v in {
                "voltage": voltage, "current": current, "temperature": temperature,
                "load": load, "brake_gap": brake_gap, "insulation_resistance": insulation_res,
                "vibration": vibration, "notes": notes or None,
            }.items() if v is not None
        }
        if payload:
            resp = api("post", f"/sessions/{session_id}/measurements", json=payload)
            if handle_api_error(resp, "Failed to save measurement"):
                st.session_state.measurements_submitted.append(payload)
                st.success("Measurement recorded!")
                st.rerun()
        else:
            st.warning("Enter at least one measurement value.")

    if st.session_state.measurements_submitted:
        st.markdown('<div class="section-header" style="margin-top:16px;">Recorded This Session</div>',
                    unsafe_allow_html=True)
        for i, m in enumerate(reversed(st.session_state.measurements_submitted[-5:])):
            parts = []
            if m.get("voltage"):              parts.append(f"**V:** {m['voltage']} V")
            if m.get("current"):              parts.append(f"**I:** {m['current']} A")
            if m.get("temperature"):          parts.append(f"**T:** {m['temperature']} °C")
            if m.get("load"):                 parts.append(f"**Load:** {m['load']} kg")
            if m.get("brake_gap"):            parts.append(f"**Gap:** {m['brake_gap']} mm")
            if m.get("insulation_resistance"): parts.append(f"**IR:** {m['insulation_resistance']} MΩ")
            if m.get("vibration"):            parts.append(f"**Vib:** {m['vibration']} mm/s")
            if m.get("notes"):                parts.append(f"*{m['notes']}*")
            st.markdown(f"**#{len(st.session_state.measurements_submitted)-i}** " + "  ·  ".join(parts))


def _render_evidence_tab():
    st.markdown('<div class="section-header">Retrieved Technical Knowledge</div>',
                unsafe_allow_html=True)
    evidence = st.session_state.evidence
    if evidence:
        for chunk in evidence:
            relevance        = chunk.get("relevance_score", 0)
            content_preview  = chunk["content"][:350] + ("..." if len(chunk["content"]) > 350 else "")
            st.markdown(f"""
            <div class="evidence-chunk">
                <div class="evidence-meta">
                    📄 {chunk.get('component','?')} · {chunk.get('source','?')}
                    &nbsp;&nbsp; Relevance: {relevance:.2f}
                </div>
                {content_preview.replace(chr(10), "<br>")}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown(
            '<p style="color:#9ca3af; font-size:0.85rem; text-align:center; padding:24px 0;">'
            'No evidence retrieved yet.<br>Start the diagnostic conversation.</p>',
            unsafe_allow_html=True
        )


def _render_session_state_tab(ssd: dict):
    st.markdown('<div class="section-header">Diagnostic Progress</div>', unsafe_allow_html=True)

    lifecycle = ssd.get("lifecycle_state", "IN_PROGRESS")
    lc_label  = LIFECYCLE_LABELS.get(lifecycle, lifecycle)
    lc_class  = LIFECYCLE_BADGE_CLASS.get(lifecycle, "badge-state-active")

    st.markdown(f"""
    <table style="width:100%; font-size:0.85rem; border-collapse:collapse;">
        <tr>
            <td style="color:#6b7280; padding:4px 8px 4px 0; width:45%;">Component</td>
            <td style="font-weight:600; color:#1e293b;">{ssd.get('component','–')}</td>
        </tr>
        <tr>
            <td style="color:#6b7280; padding:4px 8px 4px 0;">Lifecycle State</td>
            <td><span class="badge {lc_class}">{lc_label}</span></td>
        </tr>
    </table>
    """, unsafe_allow_html=True)

    hypothesis = ssd.get("current_hypothesis")
    if hypothesis:
        st.markdown('<div class="section-header" style="margin-top:14px;">Current Working Hypothesis</div>',
                    unsafe_allow_html=True)
        st.info(hypothesis)

    steps = ssd.get("completed_steps", [])
    if steps:
        st.markdown('<div class="section-header" style="margin-top:14px;">Completed Diagnostic Steps</div>',
                    unsafe_allow_html=True)
        for step in steps:
            st.markdown(f'<div style="color:#059669;font-size:0.87rem;padding:4px 0;">✓ {step}</div>',
                        unsafe_allow_html=True)

    causes = ssd.get("likely_causes", [])
    if causes:
        st.markdown('<div class="section-header" style="margin-top:14px;">Likely Causes</div>',
                    unsafe_allow_html=True)
        for cause in causes:
            st.markdown(f'<div style="color:#6b7280;font-size:0.87rem;padding:4px 0;">◈ {cause}</div>',
                        unsafe_allow_html=True)

    if not steps and not causes and not hypothesis:
        st.markdown(
            '<p style="color:#9ca3af; font-size:0.85rem; text-align:center; padding:24px 0;">'
            'Progress will appear here as the diagnosis develops.</p>',
            unsafe_allow_html=True
        )


def _render_annotations_tab(session_id: int):
    st.markdown('<div class="section-header">Expert Annotations</div>', unsafe_allow_html=True)

    ann_resp = api("get", f"/sessions/{session_id}/annotations")
    if ann_resp.status_code == 200:
        annotations = ann_resp.json()
        if annotations:
            for ann in annotations:
                ann_type = ann.get("annotation_type", "general")
                icon = {"root_cause": "🎯", "safety_note": "⚠️",
                        "procedure_note": "📋", "general": "💬"}.get(ann_type, "💬")
                st.markdown(f"""
                <div class="action-panel action-panel-sme" style="margin-bottom:8px;">
                    <div style="font-size:0.75rem;color:#7c3aed;font-weight:600;margin-bottom:4px;">
                        {icon} {ann_type.upper().replace("_"," ")}
                        &nbsp;·&nbsp;
                        <span style="font-weight:400;color:#6b7280;">{_format_date(ann.get('created_at',''))}</span>
                    </div>
                    <div style="font-size:0.87rem;color:#374151;">{ann.get('annotation_text','')}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(
                '<p style="color:#9ca3af;font-size:0.85rem;text-align:center;padding:12px 0;">'
                'No annotations yet.</p>', unsafe_allow_html=True
            )

    st.markdown('<div class="section-header" style="margin-top:12px;">Add Annotation</div>',
                unsafe_allow_html=True)
    with st.form("annotation_form", clear_on_submit=True):
        ann_type = st.selectbox(
            "Annotation type",
            options=["general", "root_cause", "safety_note", "procedure_note"],
            format_func=lambda x: {"general": "General Note",
                                    "root_cause": "Root Cause Finding",
                                    "safety_note": "Safety Note",
                                    "procedure_note": "Procedure Note"}[x],
        )
        ann_text = st.text_area("Annotation", height=80, placeholder="Enter your expert annotation...")
        if st.form_submit_button("Add Annotation", use_container_width=True):
            if ann_text.strip():
                resp = api("post", f"/sessions/{session_id}/annotations",
                           json={"annotation_text": ann_text.strip(), "annotation_type": ann_type})
                if handle_api_error(resp, "Failed to add annotation"):
                    st.success("Annotation added.")
                    st.rerun()
            else:
                st.warning("Please enter annotation text.")


# ═══════════════════════════════════════════════════════════════════
# SCREEN 4: CRANE DASHBOARD (role-aware)
# ═══════════════════════════════════════════════════════════════════

def screen_dashboard():
    render_top_bar()
    role = _role()

    st.markdown("""
    <div style="margin-bottom:8px;">
        <h2 style="font-size:1.4rem; font-weight:700; color:#1a1f36; margin:0 0 4px 0;">
            📊 Crane Dashboard
        </h2>
        <p style="color:#6b7280; font-size:0.9rem; margin:0;">
            Troubleshooting history, lifecycle states, and maintenance reports.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── View mode selector (role-gated) ──────────────────────────
    view_options = ["My Sessions"]
    if role in ("SME", "SUP", "ADM"):
        view_options += ["All Sessions"]
    if role in ("SME", "SUP"):
        view_options += ["Escalated / SME Review"]

    col_t, col_v = st.columns([3, 2])
    with col_v:
        st.markdown("<br>", unsafe_allow_html=True)
        view_mode = st.radio(
            "View",
            options=view_options,
            horizontal=True,
            label_visibility="collapsed",
        )

    filter_mode_map = {
        "My Sessions":            "own",
        "All Sessions":           "all",
        "Escalated / SME Review": "escalated",
    }
    filter_mode = filter_mode_map.get(view_mode, "own")

    if filter_mode == "all":
        st.info("👥 Showing sessions from all engineers.")
    elif filter_mode == "escalated":
        st.info("📥 Showing escalated sessions pending SME review.")

    # ── Stats ─────────────────────────────────────────────────────
    fm_for_stats = "own" if filter_mode == "own" else "all"
    stats_resp = api("get", "/dashboard/stats", params={"filter_mode": fm_for_stats})
    stats = stats_resp.json() if stats_resp.status_code == 200 else {}

    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.metric("Total Sessions", stats.get("total_sessions", 0))
    with mc2:
        st.metric("Closed with Report", stats.get("completed_sessions", 0))
    with mc3:
        st.metric("Reports Generated", stats.get("total_reports", 0))
    with mc4:
        follow_up = stats.get("follow_up_needed", 0)
        st.metric("Follow-up Required", follow_up,
                  delta=f"⚠️ {follow_up} pending" if follow_up else None,
                  delta_color="inverse")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────
    with st.expander("🔍 Filter Sessions", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            filter_crane = st.selectbox("Crane", options=["All"] + list(CRANE_COMPONENTS.keys()))
        with fc2:
            all_comps = sorted({c for comps in CRANE_COMPONENTS.values() for c in comps})
            filter_component = st.selectbox("Component", options=["All"] + all_comps)
        with fc3:
            filter_lc = st.selectbox(
                "Lifecycle State",
                options=["All"] + list(LIFECYCLE_LABELS.keys()),
                format_func=lambda x: x if x == "All" else LIFECYCLE_LABELS.get(x, x),
            )
        with fc4:
            filter_severity = st.selectbox("Severity", options=["All", "critical", "high", "medium", "low"])

    # ── Fetch entries ─────────────────────────────────────────────
    params: dict = {"filter_mode": filter_mode}
    if filter_crane != "All":
        params["crane_type"] = filter_crane
    if filter_component != "All":
        params["component"] = filter_component
    if filter_lc != "All":
        params["lifecycle_state"] = filter_lc

    dash_resp = api("get", "/dashboard", params=params)
    if dash_resp.status_code != 200:
        st.error("Failed to load dashboard data.")
        return

    entries = dash_resp.json()
    if filter_severity != "All":
        entries = [e for e in entries if e.get("severity") == filter_severity]

    # ── Charts ────────────────────────────────────────────────────
    if entries:
        ch1, ch2 = st.columns(2)
        with ch1:
            comp_counts = {}
            for e in entries:
                comp_counts[e["component"]] = comp_counts.get(e["component"], 0) + 1
            if comp_counts:
                df_comp = pd.DataFrame(list(comp_counts.items()), columns=["Component", "Count"]).sort_values("Count", ascending=False)
                fig = px.bar(df_comp, x="Count", y="Component", orientation="h",
                             title="Issues by Component", color="Count",
                             color_continuous_scale="Blues")
                fig.update_layout(height=280, margin=dict(l=0,r=0,t=40,b=0),
                                   showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)
        with ch2:
            lc_counts = {}
            for e in entries:
                lc = e.get("lifecycle_state", "UNKNOWN")
                label = LIFECYCLE_LABELS.get(lc, lc)
                lc_counts[label] = lc_counts.get(label, 0) + 1
            if lc_counts:
                df_lc = pd.DataFrame(list(lc_counts.items()), columns=["State", "Count"])
                fig2 = px.pie(df_lc, names="State", values="Count", title="Sessions by Lifecycle State")
                fig2.update_layout(height=280, margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    st.markdown(f'<div class="section-header">Sessions ({len(entries)} found)</div>',
                unsafe_allow_html=True)

    if not entries:
        st.info("No sessions found for the selected filters.")
        return

    for entry in entries:
        _render_dashboard_entry(entry, role, filter_mode)


def _render_dashboard_entry(entry: dict, role: str, filter_mode: str):
    lifecycle    = entry.get("lifecycle_state", "")
    lc_label     = LIFECYCLE_LABELS.get(lifecycle, lifecycle)
    lc_class     = LIFECYCLE_BADGE_CLASS.get(lifecycle, "badge-state-active")
    sev          = entry.get("severity")
    sev_icon     = SEVERITY_ICONS.get(sev, "⚪")
    has_report   = entry["has_report"]
    is_escalated = entry.get("escalated", False)

    esc_marker = " 🔔" if is_escalated and lifecycle not in ("RESOLVED", "CLOSED_WITH_REPORT") else ""

    with st.expander(
        f"{sev_icon}  #{entry['session_id']}  ·  {entry['crane_type']}  ·  "
        f"{entry['component']}  ·  {_format_date(entry['session_date'])}{esc_marker}",
        expanded=False,
    ):
        top_c1, top_c2 = st.columns([3, 1])
        with top_c1:
            st.markdown(f"**Problem:** {entry['problem_description']}")
            eng_role_color = ROLE_COLORS.get(entry.get("engineer_role","ME"), "#6b7280")
            st.markdown(
                f'👷 <b>{entry.get("engineer_name","Unknown")}</b>'
                f' &nbsp; <span class="role-badge" style="background:{eng_role_color};">'
                f'{entry.get("engineer_role","ME")}</span>'
                f' &nbsp;&nbsp; '
                f'<span class="badge {lc_class}">{lc_label}</span>',
                unsafe_allow_html=True,
            )
            if sev:
                st.markdown(
                    f'Severity: <span class="badge badge-{sev}">{sev.upper()}</span>',
                    unsafe_allow_html=True,
                )

        with top_c2:
            session_id = entry["session_id"]

            # Open/Resume session (ME and SME only)
            if role in ("ME", "SME"):
                if lifecycle != "CLOSED_WITH_REPORT":
                    btn_label = "▶ Resume" if session_id == st.session_state.current_session_id else "View / Resume"
                    if st.button(btn_label, key=f"resume_{session_id}", use_container_width=True,
                                 type="primary" if session_id == st.session_state.current_session_id else "secondary"):
                        st.session_state.current_session_id = session_id
                        msgs_resp = api("get", f"/sessions/{session_id}/messages")
                        if msgs_resp.status_code == 200:
                            st.session_state.messages = [
                                {"role": m["role"], "content": m["content"]}
                                for m in msgs_resp.json()
                            ]
                        meas_resp = api("get", f"/sessions/{session_id}/measurements")
                        if meas_resp.status_code == 200:
                            st.session_state.measurements_submitted = meas_resp.json()
                        st.session_state.pending_questions = []
                        st.session_state.screen = "guidance"
                        st.rerun()

            # SME-specific actions in dashboard
            if role == "SME" and lifecycle == "ESCALATED":
                if st.button("🔬 Open for Review", key=f"sme_open_{session_id}", use_container_width=True):
                    resp = api("post", f"/sessions/{session_id}/sme-review")
                    if handle_api_error(resp, "Failed"):
                        st.rerun()

            # Generate report button
            if not has_report and role in ("ME", "SME") and lifecycle not in ("CLOSED_WITH_REPORT", "LOGGED"):
                if st.button("⚡ Generate Report", key=f"gen_{session_id}", use_container_width=True):
                    with st.spinner("Generating..."):
                        resp = api("post", f"/sessions/{session_id}/report")
                    if handle_api_error(resp, "Report generation failed"):
                        st.success("Report generated!")
                        st.rerun()

        # Render report inline
        if has_report and entry.get("report_id"):
            st.markdown("---")
            st.markdown("**📄 Fault Report**")
            report_resp = api("get", f"/reports/{entry['report_id']}")
            if report_resp.status_code == 200:
                user_role = st.session_state.get("user", {}).get("role", "")
                _render_report(
                    report_resp.json(),
                    allow_close_followup=(user_role in ("ME", "SME")),
                )
        elif not has_report:
            st.caption("No report generated yet.")


def _render_report(r: dict, allow_close_followup: bool = False):
    st.markdown(f"""
    <div class="report-section">
        <h4>Diagnosis</h4>
        <p style="font-size:0.9rem; color:#374151; margin:0; line-height:1.6;">{r.get('diagnosis','–')}</p>
    </div>
    """, unsafe_allow_html=True)

    if r.get("root_cause"):
        st.markdown(f"""
        <div class="report-section">
            <h4>Root Cause</h4>
            <p style="font-size:0.9rem; color:#374151; margin:0; line-height:1.6;">{r.get('root_cause','–')}</p>
        </div>
        """, unsafe_allow_html=True)

    rep_col1, rep_col2 = st.columns(2)
    with rep_col1:
        steps = _parse_list(r.get("steps_taken"))
        if steps:
            st.markdown("**Steps Taken:**")
            for step in steps:
                st.markdown(f"✓ {step}")
    with rep_col2:
        recs = _parse_list(r.get("recommendations"))
        if recs:
            st.markdown("**Recommendations:**")
            for rec in recs:
                st.markdown(f"→ {rec}")

    if r.get("measurements_summary") and r["measurements_summary"] != "No measurements recorded.":
        with st.expander("📐 Measurements recorded"):
            try:
                meas = json.loads(r["measurements_summary"])
                if meas:
                    st.json(meas)
            except (json.JSONDecodeError, TypeError):
                st.text(r["measurements_summary"])

    if r.get("follow_up_required"):
        fu_status = r.get("follow_up_status") or "pending"
        report_id = r.get("id")

        if fu_status == "done":
            closed_at = r.get("follow_up_closed_at", "")
            if closed_at:
                try:
                    from datetime import datetime as _dt
                    closed_at = _dt.fromisoformat(closed_at[:19]).strftime("%d %b %Y %H:%M")
                except Exception:
                    pass
            note = r.get("follow_up_note") or ""
            st.success(
                f"✅ **Follow-up completed** — {closed_at}"
                + (f"\n\n_{note}_" if note else "")
            )
        else:
            st.warning("⚠️ **Follow-up required** — This case needs a verification check before the machine is returned to service.")
            if allow_close_followup and report_id:
                with st.expander("Mark follow-up as done"):
                    with st.form(key=f"followup_close_{report_id}"):
                        note = st.text_area(
                            "What was checked / confirmed?",
                            placeholder="e.g. Returned to service after replacing fuse and verifying motor runs without fault for 30 minutes.",
                        )
                        if st.form_submit_button("✅ Mark Follow-up Done", type="primary"):
                            if not note.strip():
                                st.error("Please describe what was done before closing the follow-up.")
                            else:
                                resp = api("put", f"/reports/{report_id}/follow-up/close", json={"note": note.strip()})
                                if resp.status_code == 200:
                                    st.success("Follow-up marked as done.")
                                    st.rerun()
                                else:
                                    st.error(f"Failed: {resp.text}")


# ═══════════════════════════════════════════════════════════════════
# SCREEN 5: SME INBOX
# ═══════════════════════════════════════════════════════════════════

def screen_sme_inbox():
    render_top_bar()

    st.markdown("""
    <div style="margin-bottom:16px;">
        <h2 style="font-size:1.4rem; font-weight:700; color:#1a1f36; margin:0 0 4px 0;">
            📥 SME Inbox — Escalated Sessions
        </h2>
        <p style="color:#6b7280; font-size:0.9rem; margin:0;">
            Sessions escalated by maintenance engineers awaiting your expert review.
        </p>
    </div>
    """, unsafe_allow_html=True)

    resp = api("get", "/dashboard", params={"filter_mode": "escalated"})
    if resp.status_code != 200:
        st.error("Failed to load escalated sessions.")
        return

    sessions = resp.json()

    # Also fetch SME_IN_REVIEW
    in_review  = [s for s in sessions if s.get("lifecycle_state") == "SME_IN_REVIEW"]
    escalated  = [s for s in sessions if s.get("lifecycle_state") == "ESCALATED"]

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("Awaiting Review", len(escalated))
    with col_m2:
        st.metric("In Your Review", len(in_review))
    with col_m3:
        st.metric("Total Queued", len(sessions))

    st.divider()

    if not sessions:
        st.success("✅ No escalated sessions pending — inbox clear.")
        return

    if escalated:
        st.markdown('<div class="section-header">🔔 Awaiting Pickup</div>', unsafe_allow_html=True)
        for entry in escalated:
            _render_sme_inbox_card(entry)

    if in_review:
        st.markdown('<div class="section-header" style="margin-top:20px;">🔬 Currently in Review</div>',
                    unsafe_allow_html=True)
        for entry in in_review:
            _render_sme_inbox_card(entry)


def _render_sme_inbox_card(entry: dict):
    lifecycle  = entry.get("lifecycle_state", "")
    lc_class   = LIFECYCLE_BADGE_CLASS.get(lifecycle, "badge-state-active")
    lc_label   = LIFECYCLE_LABELS.get(lifecycle, lifecycle)

    with st.container():
        st.markdown(f"""
        <div class="action-panel action-panel-sme">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <b style="font-size:0.95rem; color:#1e293b;">
                        #{entry['session_id']} — {entry['crane_type']} · {entry['component']}
                    </b>
                    <span class="badge {lc_class}" style="margin-left:10px;">{lc_label}</span>
                    <div style="color:#6b7280; font-size:0.83rem; margin-top:4px;">
                        👷 {entry.get('engineer_name','Unknown')} &nbsp;·&nbsp;
                        📅 {_format_date(entry['session_date'])}
                    </div>
                    <div style="color:#374151; font-size:0.87rem; margin-top:6px;">
                        <b>Problem:</b> {entry['problem_description']}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        session_id = entry["session_id"]
        btn_c1, btn_c2, btn_c3 = st.columns([1, 1, 4])
        with btn_c1:
            if lifecycle == "ESCALATED":
                if st.button("🔬 Open for Review", key=f"inbox_open_{session_id}",
                              use_container_width=True, type="primary"):
                    resp = api("post", f"/sessions/{session_id}/sme-review")
                    if handle_api_error(resp, "Failed"):
                        st.rerun()
        with btn_c2:
            if st.button("💬 Open Chat", key=f"inbox_chat_{session_id}", use_container_width=True):
                st.session_state.current_session_id = session_id
                msgs_resp = api("get", f"/sessions/{session_id}/messages")
                if msgs_resp.status_code == 200:
                    st.session_state.messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in msgs_resp.json()
                    ]
                meas_resp = api("get", f"/sessions/{session_id}/measurements")
                if meas_resp.status_code == 200:
                    st.session_state.measurements_submitted = meas_resp.json()
                st.session_state.screen = "guidance"
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# SCREEN 6: KNOWLEDGE GAPS
# ═══════════════════════════════════════════════════════════════════

def screen_knowledge_gaps():
    render_top_bar()

    st.markdown("""
    <div style="margin-bottom:16px;">
        <h2 style="font-size:1.4rem; font-weight:700; color:#1a1f36; margin:0 0 4px 0;">
            🔍 Knowledge Gap Management
        </h2>
        <p style="color:#6b7280; font-size:0.9rem; margin:0;">
            Cases where the knowledge base lacked sufficient content.
            Review, update the knowledge file, and resolve to let the engineer continue diagnosis.
        </p>
    </div>
    """, unsafe_allow_html=True)

    show_resolved = st.checkbox("Show resolved gaps", value=False)
    resp = api("get", f"/knowledge-gaps?include_resolved={'true' if show_resolved else 'false'}")
    if resp.status_code != 200:
        handle_api_error(resp, "Failed to load knowledge gaps")
        return

    gaps = resp.json()

    if not gaps:
        st.success("✅ No open knowledge gaps — the knowledge base covers all recorded cases.")
        return

    open_gaps = [g for g in gaps if g.get("status") != "resolved"]
    resolved_gaps = [g for g in gaps if g.get("status") == "resolved"]

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Open Gaps", len(open_gaps))
    col_m2.metric("Resolved", len(resolved_gaps))
    col_m3.metric("Total Shown", len(gaps))
    st.divider()

    gap_types = sorted({g.get("gap_type", "unknown") for g in gaps})
    filter_type = st.selectbox(
        "Filter by gap type",
        options=["All"] + gap_types,
        format_func=lambda x: x if x == "All" else x.replace("_", " ").title(),
    )
    if filter_type != "All":
        gaps = [g for g in gaps if g.get("gap_type") == filter_type]

    user_role = _role()
    is_ke = user_role == "KE"

    for gap in gaps:
        gap_id     = gap.get("id")
        gap_type   = gap.get("gap_type", "unknown")
        gap_status = gap.get("status", "open")
        session_id = gap.get("session_id")

        status_color = {"open": "#f97316", "in_review": "#8b5cf6", "resolved": "#10b981"}.get(gap_status, "#6b7280")
        status_bg    = {"open": "#fff7ed", "in_review": "#faf5ff", "resolved": "#f0fdf4"}.get(gap_status, "#f3f4f6")

        st.markdown(f"""
        <div class="action-panel-gap" style="border-left-color:{status_color}; background:{status_bg};">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <b style="color:#ea580c; font-size:0.9rem;">🔧 {gap.get('component_key','Unknown')}</b>
                    &nbsp;
                    <span style="font-size:0.75rem; background:#fff7ed; color:#9a3412;
                                  border:1px solid #fed7aa; border-radius:8px; padding:2px 8px;">
                        {gap_type.replace('_',' ').upper()}
                    </span>
                    &nbsp;
                    <span style="font-size:0.75rem; color:#6b7280;">
                        Gap #{gap_id} · Session #{session_id or '–'}
                        · {_format_date(gap.get('created_at',''))}
                    </span>
                </div>
                <span style="font-size:0.75rem; font-weight:700; color:{status_color}; text-transform:uppercase;">
                    {gap_status}
                </span>
            </div>
            <div style="margin-top:8px; font-size:0.86rem; color:#374151;">
                <b>Fault Pattern:</b> {gap.get('fault_pattern','–')}
            </div>
            <div style="margin-top:4px; font-size:0.85rem; color:#92400e;">
                <b>Suggested Action:</b> {gap.get('suggested_action','–')}
            </div>
            {_gap_detail_html(gap)}
        </div>
        """, unsafe_allow_html=True)

        btn_cols = st.columns([1, 1, 4]) if (is_ke and gap_status != "resolved") else st.columns([1, 5])

        with btn_cols[0]:
            if session_id and st.button("📂 View Session", key=f"gap_view_{gap_id}", use_container_width=True):
                st.session_state.current_session_id = session_id
                msgs_resp = api("get", f"/sessions/{session_id}/messages")
                if msgs_resp.status_code == 200:
                    st.session_state.messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in msgs_resp.json()
                    ]
                st.session_state.screen = "guidance"
                st.rerun()

        # KE-only: resolve button opens editor
        if is_ke and gap_status != "resolved":
            with btn_cols[1]:
                expand_key = f"ke_resolve_open_{gap_id}"
                if expand_key not in st.session_state:
                    st.session_state[expand_key] = False
                if st.button("✏️ Update & Resolve", key=f"ke_resolve_btn_{gap_id}", use_container_width=True):
                    st.session_state[expand_key] = not st.session_state[expand_key]

            if st.session_state.get(f"ke_resolve_open_{gap_id}", False):
                _render_ke_resolve_form(gap)

        st.markdown("<br>", unsafe_allow_html=True)


def _gap_detail_html(gap: dict) -> str:
    """Render extra structured details for a gap card."""
    parts = []
    if gap.get("missing_information"):
        parts.append(
            f'<div style="margin-top:4px;font-size:0.83rem;color:#374151;">'
            f'<b>Missing Information:</b> {gap["missing_information"]}</div>'
        )
    if gap.get("suggested_file_to_update"):
        parts.append(
            f'<div style="margin-top:4px;font-size:0.82rem;color:#6b7280;">'
            f'<b>File to Update:</b> <code>{gap["suggested_file_to_update"]}</code>'
            f'  ·  <b>Section:</b> {gap.get("suggested_section_or_node") or "—"}</div>'
        )
    if gap.get("confidence") is not None:
        pct = int((gap["confidence"] or 0) * 100)
        parts.append(
            f'<div style="margin-top:4px;font-size:0.8rem;color:#6b7280;">'
            f'<b>Gap Confidence:</b> {pct}%  ·  '
            f'<b>Detected by:</b> {gap.get("detected_by","–")}</div>'
        )
    if gap.get("resolution_note") and gap.get("status") == "resolved":
        parts.append(
            f'<div style="margin-top:6px;font-size:0.83rem;color:#065f46;background:#f0fdf4;'
            f'border-radius:4px;padding:6px 10px;">'
            f'<b>Resolution Note:</b> {gap["resolution_note"]}</div>'
        )
    return "".join(parts)


def _render_ke_resolve_form(gap: dict):
    """In-page knowledge editor form for Knowledge Engineers."""
    import os, pathlib

    gap_id      = gap.get("id")
    target_file = gap.get("suggested_file_to_update") or "general_procedures.txt"
    section     = gap.get("suggested_section_or_node") or ""

    st.markdown(f"""
    <div style="background:#f0fdf4; border:1px solid #86efac; border-radius:8px;
                padding:16px 18px; margin:8px 0 12px 0;">
        <div style="font-weight:700; color:#065f46; margin-bottom:6px; font-size:0.92rem;">
            ✏️ Knowledge Editor — Gap #{gap_id}
        </div>
        <div style="font-size:0.82rem; color:#374151; margin-bottom:4px;">
            Target file: <code>{target_file}</code>
            &nbsp; · &nbsp; Suggested section: <code>{section or '—'}</code>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Show current file content (read from filesystem via backend URL would require
    # a separate endpoint; here we read the file path from env for simplicity)
    kb_path_env = os.getenv("KNOWLEDGE_BASE_PATH", "./data/knowledge_base")

    # Try to find the actual file path (works when frontend runs on same machine)
    possible_paths = [
        pathlib.Path(kb_path_env) / target_file,
        pathlib.Path(__file__).resolve().parent.parent / "data" / "knowledge_base" / target_file,
    ]
    current_content_preview = ""
    for p in possible_paths:
        if p.exists():
            raw = p.read_text(encoding="utf-8")
            # Show only the relevant section if found
            if section and section in raw:
                idx = raw.index(section)
                current_content_preview = raw[idx: idx + 1200]
            else:
                current_content_preview = raw[:1200]
            current_content_preview += "\n\n[... truncated for display ...]" if len(raw) > 1200 else ""
            break

    if current_content_preview:
        with st.expander("📄 Current file content (preview)", expanded=False):
            st.code(current_content_preview, language="text")

    with st.form(key=f"ke_resolve_form_{gap_id}", clear_on_submit=False):
        st.markdown("**What information is missing and what should be added:**")
        content_to_add = st.text_area(
            "New content to add to the knowledge file",
            height=220,
            placeholder=(
                "Write the missing diagnostic steps, specifications, threshold values, "
                "or procedure that should be added to the knowledge base.\n\n"
                "Example:\n"
                "FAULT: Motor trips thermal relay repeatedly under rated load\n"
                "CAUSE: Relay setting above motor nameplate FLA\n"
                "FIX: Adjust thermal relay to 105% of motor nameplate FLA. "
                "Verify cooling air path is unobstructed. Check duty cycle vs. rated CDF."
            ),
            key=f"ke_content_{gap_id}",
        )

        append_section = st.text_input(
            "Insert under section (leave blank to append at end of file)",
            value=section,
            key=f"ke_section_{gap_id}",
            help="Exact section header from the knowledge file, e.g.  === COMMON FAILURE MODES ===",
        )

        resolution_note = st.text_area(
            "Resolution note (for audit trail)",
            height=80,
            placeholder="Briefly describe what was added and why (e.g. 'Added thermal relay procedure based on session #42 findings').",
            key=f"ke_note_{gap_id}",
        )

        submitted = st.form_submit_button(
            "💾 Save to Knowledge Base & Resolve Gap",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if not content_to_add.strip():
                st.error("Content to add cannot be empty.")
            elif not resolution_note.strip():
                st.error("Please provide a resolution note.")
            else:
                payload = {
                    "content_to_append": content_to_add.strip(),
                    "append_to_section": append_section.strip() or None,
                    "resolution_note":   resolution_note.strip(),
                }
                with st.spinner("Writing to knowledge base and re-indexing..."):
                    resp = api("put", f"/knowledge-gaps/{gap_id}/resolve", json=payload)
                if handle_api_error(resp, "Failed to resolve knowledge gap"):
                    st.session_state[f"ke_resolve_open_{gap_id}"] = False
                    st.success(
                        f"✅ Knowledge base updated! Gap #{gap_id} resolved. "
                        "The AI will use the new knowledge immediately. "
                        "The engineer has been notified to continue diagnosis."
                    )
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════
# SCREEN 7: ADMIN PANEL (ADM only)
# ═══════════════════════════════════════════════════════════════════

def screen_admin():
    render_top_bar()

    st.markdown("""
    <div style="margin-bottom:16px;">
        <h2 style="font-size:1.4rem; font-weight:700; color:#1a1f36; margin:0 0 4px 0;">
            ⚙️ Admin Panel
        </h2>
        <p style="color:#6b7280; font-size:0.9rem; margin:0;">
            User management, role assignment, and audit log.
        </p>
    </div>
    """, unsafe_allow_html=True)

    adm_tab1, adm_tab2 = st.tabs(["👥 User Management", "📋 Audit Log"])

    # ── Tab 1: Users ─────────────────────────────────────────────
    with adm_tab1:
        users_resp = api("get", "/admin/users")
        if users_resp.status_code != 200:
            handle_api_error(users_resp, "Failed to load users")
            return

        users = users_resp.json()
        st.markdown(f'<div class="section-header">All Users ({len(users)})</div>',
                    unsafe_allow_html=True)

        # Summary counts
        role_counts = {}
        for u in users:
            r = u.get("role", "ME")
            role_counts[r] = role_counts.get(r, 0) + 1

        cnt_cols = st.columns(len(ROLE_COLORS))
        for i, (r, color) in enumerate(ROLE_COLORS.items()):
            with cnt_cols[i]:
                st.markdown(
                    f'<div style="text-align:center; padding:8px; background:#f9fafb; '
                    f'border:1px solid #e5e7eb; border-radius:6px;">'
                    f'<div style="font-size:1.4rem;font-weight:800;color:{color};">'
                    f'{role_counts.get(r, 0)}</div>'
                    f'<div style="font-size:0.72rem;color:#6b7280;">{r}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)
        current_user_id = st.session_state.user.get("id") if st.session_state.user else None

        for user in users:
            uid          = user.get("id")
            is_active    = user.get("is_active", True)
            user_role    = user.get("role", "ME")
            role_color   = ROLE_COLORS.get(user_role, "#6b7280")
            active_badge = (
                '<span style="font-size:0.72rem;color:#065f46;background:#d1fae5;'
                'padding:2px 8px;border-radius:8px;font-weight:600;">ACTIVE</span>'
                if is_active else
                '<span style="font-size:0.72rem;color:#991b1b;background:#fee2e2;'
                'padding:2px 8px;border-radius:8px;font-weight:600;">INACTIVE</span>'
            )
            own_badge = " ← you" if uid == current_user_id else ""

            st.markdown(f"""
            <div style="background:white;border:1px solid #e5e7eb;border-radius:6px;
                         padding:12px 16px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <b style="color:#1e293b;">{user.get('name','')}</b>
                        <span style="color:#6b7280;font-size:0.82rem;margin-left:6px;">
                            @{user.get('username','')}{own_badge}
                        </span>
                        &nbsp;&nbsp;
                        <span class="role-badge" style="background:{role_color};">{user_role}</span>
                        &nbsp;
                        {active_badge}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Controls (only for other users)
            if uid != current_user_id:
                ctrl1, ctrl2, ctrl3 = st.columns([2, 1, 1])

                with ctrl1:
                    new_role = st.selectbox(
                        f"Role for {user.get('username','')}",
                        options=list(ROLE_LABELS.keys()),
                        index=list(ROLE_LABELS.keys()).index(user_role) if user_role in ROLE_LABELS else 0,
                        key=f"role_select_{uid}",
                        label_visibility="collapsed",
                        format_func=lambda x: f"{x} – {ROLE_LABELS[x]}",
                    )

                with ctrl2:
                    if st.button("💾 Assign Role", key=f"assign_{uid}", use_container_width=True):
                        if new_role != user_role:
                            resp = api("put", f"/admin/users/{uid}/role", json={"role": new_role})
                            if handle_api_error(resp, "Role update failed"):
                                st.success(f"Role updated to {new_role}.")
                                st.rerun()
                        else:
                            st.info("No change.")

                with ctrl3:
                    if is_active:
                        if st.button("🚫 Deactivate", key=f"deact_{uid}", use_container_width=True):
                            resp = api("put", f"/admin/users/{uid}/deactivate")
                            if handle_api_error(resp, "Deactivation failed"):
                                st.success("User deactivated.")
                                st.rerun()
                    else:
                        if st.button("✅ Activate", key=f"act_{uid}", use_container_width=True):
                            resp = api("put", f"/admin/users/{uid}/activate")
                            if handle_api_error(resp, "Activation failed"):
                                st.success("User activated.")
                                st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

    # ── Tab 2: Audit Log ─────────────────────────────────────────
    with adm_tab2:
        st.markdown('<div class="section-header">Recent Events</div>', unsafe_allow_html=True)

        ac1, ac2 = st.columns([2, 1])
        with ac1:
            event_filter = st.text_input("Filter by event type", placeholder="e.g. login, role_assign")
        with ac2:
            limit = st.number_input("Max entries", min_value=10, max_value=500, value=100, step=10)

        params = {"limit": limit}
        if event_filter.strip():
            params["event_type"] = event_filter.strip()

        audit_resp = api("get", "/admin/audit-log", params=params)
        if audit_resp.status_code != 200:
            handle_api_error(audit_resp, "Failed to load audit log")
            return

        entries = audit_resp.json()
        if not entries:
            st.info("No audit entries found.")
            return

        rows = []
        for e in entries:
            rows.append({
                "Time":          _format_date(e.get("created_at", "")),
                "Event":         e.get("event_type", ""),
                "Resource Type": e.get("resource_type", ""),
                "Resource ID":   e.get("resource_id", ""),
                "User ID":       e.get("user_id", ""),
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=500)


# ═══════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def _parse_list(value) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            result = json.loads(value)
            return result if isinstance(result, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _format_date(date_str: str) -> str:
    if not date_str:
        return "–"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y, %H:%M")
    except Exception:
        return date_str


# ═══════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ═══════════════════════════════════════════════════════════════════

def main():
    screen = st.session_state.get("screen", "login")

    if screen == "login":
        screen_login()
        return

    if not st.session_state.token:
        st.session_state.screen = "login"
        st.rerun()

    role = _role()

    if screen == "intake":
        if not _has_role("ME", "SME"):
            st.warning("Intake form is for Maintenance and Senior Engineers only.")
            _nav(_landing_screen_for_role(role))
        else:
            screen_intake()
    elif screen == "similar_found":
        screen_similar_found()
    elif screen == "guidance":
        screen_guidance()
    elif screen == "dashboard":
        screen_dashboard()
    elif screen == "sme_inbox":
        if not _has_role("SME"):
            st.warning("SME Inbox is for Senior Engineers only.")
            _nav(_landing_screen_for_role(role))
        else:
            screen_sme_inbox()
    elif screen == "knowledge_gaps":
        if not _has_role("KE", "SME"):
            st.warning("Knowledge Gaps is for Knowledge Engineers and SMEs only.")
            _nav(_landing_screen_for_role(role))
        else:
            screen_knowledge_gaps()
    elif screen == "admin":
        if not _has_role("ADM"):
            st.warning("Admin panel is for Administrators only.")
            _nav(_landing_screen_for_role(role))
        else:
            screen_admin()
    else:
        st.session_state.screen = "login"
        st.rerun()


if __name__ == "__main__":
    main()
