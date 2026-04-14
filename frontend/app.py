"""
Crane AI – Process Guidance Tool
Streamlit Frontend: 4-screen multi-page industrial troubleshooting UI
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
    "critical": "#FF4444",
    "high": "#FF8C00",
    "medium": "#FFD700",
    "low": "#32CD32",
    None: "#888888",
}

SEVERITY_ICONS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🟢",
    None: "⚪",
}

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
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}

    /* Top navigation bar */
    .top-bar {
        background: linear-gradient(135deg, #1a1f36 0%, #2d3561 100%);
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .top-bar h1 {
        margin: 0;
        font-size: 1.3rem;
        font-weight: 700;
        color: white;
    }
    .top-bar .subtitle {
        font-size: 0.75rem;
        color: #9ba4c7;
        margin: 0;
    }

    /* Chat message heading sizes — keep AI headings compact and readable */
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3 {
        font-size: 1rem !important;
        font-weight: 700 !important;
        margin: 10px 0 4px 0 !important;
        line-height: 1.4 !important;
        color: #1e293b !important;
    }
    [data-testid="stChatMessage"] h4,
    [data-testid="stChatMessage"] h5,
    [data-testid="stChatMessage"] h6 {
        font-size: 0.92rem !important;
        font-weight: 600 !important;
        margin: 8px 0 4px 0 !important;
        color: #374151 !important;
    }
    [data-testid="stChatMessage"] p {
        font-size: 0.92rem !important;
        line-height: 1.65 !important;
        margin-bottom: 6px !important;
    }
    [data-testid="stChatMessage"] li {
        font-size: 0.92rem !important;
        line-height: 1.6 !important;
    }
    [data-testid="stChatMessage"] table {
        font-size: 0.85rem !important;
    }

    /* Card containers */
    .card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    /* Section headers */
    .section-header {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6b7280;
        margin-bottom: 10px;
        border-bottom: 1px solid #f3f4f6;
        padding-bottom: 6px;
    }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
    }
    .badge-active { background: #dbeafe; color: #1d4ed8; }
    .badge-completed { background: #d1fae5; color: #065f46; }
    .badge-critical { background: #fee2e2; color: #991b1b; }
    .badge-high { background: #ffedd5; color: #9a3412; }
    .badge-medium { background: #fef9c3; color: #854d0e; }
    .badge-low { background: #d1fae5; color: #065f46; }

    /* Chat messages */
    .chat-msg-user {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 10px 10px 2px 10px;
        padding: 12px 16px;
        margin: 8px 0 8px 40px;
        font-size: 0.9rem;
        line-height: 1.6;
    }
    .chat-msg-ai {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-left: 4px solid #3b82f6;
        border-radius: 2px 10px 10px 10px;
        padding: 12px 16px;
        margin: 8px 40px 8px 0;
        font-size: 0.9rem;
        line-height: 1.7;
    }
    .chat-label {
        font-size: 0.72rem;
        font-weight: 600;
        color: #6b7280;
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .chat-label-user { color: #1d4ed8; }
    .chat-label-ai { color: #059669; }

    /* Evidence panel */
    .evidence-chunk {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 3px solid #6366f1;
        border-radius: 4px;
        padding: 10px 12px;
        margin-bottom: 8px;
        font-size: 0.82rem;
        line-height: 1.6;
    }
    .evidence-meta {
        font-size: 0.7rem;
        color: #6b7280;
        margin-bottom: 6px;
        font-weight: 600;
    }

    /* Measurement panel */
    .meas-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1e293b;
    }
    .meas-unit {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 2px;
    }

    /* Steps list */
    .step-completed {
        color: #059669;
        font-size: 0.87rem;
        padding: 4px 0;
    }
    .step-pending {
        color: #6b7280;
        font-size: 0.87rem;
        padding: 4px 0;
    }

    /* Login screen */
    .login-container {
        max-width: 420px;
        margin: 0 auto;
        padding-top: 40px;
    }
    .login-logo {
        text-align: center;
        margin-bottom: 32px;
    }
    .login-logo h1 {
        font-size: 2rem;
        font-weight: 800;
        color: #1a1f36;
        margin: 8px 0 4px 0;
    }
    .login-logo p {
        color: #6b7280;
        font-size: 0.9rem;
    }

    /* Metric cards */
    .metric-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1a1f36;
    }
    .metric-label {
        font-size: 0.78rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* Streamlit button overrides */
    .stButton > button {
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.9rem;
        transition: all 0.2s;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        border: none;
        color: white;
        padding: 10px 24px;
    }

    /* Report section */
    .report-section {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
    }
    .report-section h4 {
        color: #374151;
        margin: 0 0 12px 0;
        font-size: 0.9rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# SESSION STATE INITIALISATION
# ═══════════════════════════════════════════════════════════════════

def init_session_state():
    defaults = {
        "screen": "login",           # login | intake | guidance | dashboard
        "token": None,
        "user": None,
        "current_session_id": None,
        "messages": [],
        "evidence": [],
        "session_state_data": {},
        "measurements_submitted": [],
        "pending_evidence": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session_state()


# ═══════════════════════════════════════════════════════════════════
# API HELPERS
# ═══════════════════════════════════════════════════════════════════

def api(method: str, path: str, **kwargs) -> requests.Response:
    """Make an API call with auth header."""
    headers = kwargs.pop("headers", {})
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    url = f"{BACKEND_URL}{path}"
    return getattr(requests, method)(url, headers=headers, timeout=60, **kwargs)


def handle_api_error(resp: requests.Response, context: str = ""):
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
    col1, col2 = st.columns([6, 4])

    with col1:
        st.markdown("""
        <div style="display:flex; align-items:center; gap:14px; padding: 6px 0;">
            <span style="font-size:2.6rem; line-height:1;">🏗️</span>
            <div>
                <div style="font-size:1.45rem; font-weight:800; color:#1a1f36; line-height:1.25;">
                    AI-Assisted Process Guidance
                </div>
                <div style="font-size:0.78rem; color:#6b7280; margin-top:2px;">
                    Industrial Crane Maintenance Troubleshooting System
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        if user:
            nav_cols = st.columns([1, 1, 1])
            with nav_cols[0]:
                if st.button("📋 New Issue", use_container_width=True):
                    st.session_state.screen = "intake"
                    st.session_state.current_session_id = None
                    st.session_state.messages = []
                    st.session_state.evidence = []
                    st.rerun()
            with nav_cols[1]:
                if st.button("📊 Dashboard", use_container_width=True):
                    st.session_state.screen = "dashboard"
                    st.rerun()
            with nav_cols[2]:
                with st.popover(f"👤 {user['name']}", use_container_width=True):
                    st.markdown(
                        f"""
                        <div style="padding:4px 0 10px 0;">
                            <div style="font-size:0.95rem; font-weight:700;
                                        color:#1a1f36;">{user['name']}</div>
                            <div style="font-size:0.78rem; color:#6b7280;">
                                @{user['username']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.divider()
                    if st.button("🚪 Logout", use_container_width=True, type="primary"):
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        init_session_state()
                        st.rerun()

    st.divider()


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
                            st.session_state.user = data["user"]
                            st.session_state.screen = "intake"
                            st.success(f"Welcome back, {data['user']['name']}!")
                            st.rerun()

        with tab_signup:
            st.markdown("<br>", unsafe_allow_html=True)
            with st.form("signup_form", clear_on_submit=False):
                name = st.text_input("Full Name", placeholder="e.g. Karl Müller")
                new_username = st.text_input("Username", placeholder="Choose a username")
                new_password = st.text_input("Password", type="password",
                                              placeholder="Choose a strong password")
                confirm_password = st.text_input("Confirm Password", type="password",
                                                  placeholder="Repeat your password")
                st.markdown("<br>", unsafe_allow_html=True)
                submitted = st.form_submit_button("Create Account →", use_container_width=True, type="primary")

                if submitted:
                    if not all([name, new_username, new_password, confirm_password]):
                        st.error("All fields are required.")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match.")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        with st.spinner("Creating account..."):
                            resp = api("post", "/auth/signup",
                                       json={"name": name, "username": new_username,
                                             "password": new_password})
                        if handle_api_error(resp, "Signup failed"):
                            data = resp.json()
                            st.session_state.token = data["access_token"]
                            st.session_state.user = data["user"]
                            st.session_state.screen = "intake"
                            st.success(f"Account created! Welcome, {data['user']['name']}!")
                            st.rerun()

        st.markdown("""
        <div style="text-align:center; color:#9ca3af; font-size:0.78rem; padding-top:32px;">
            Fraunhofer IESE · Master Thesis Prototype · 2025
        </div>
        """, unsafe_allow_html=True)


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

    with st.form("intake_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="section-header">Crane & Component</div>', unsafe_allow_html=True)

            crane_type = st.selectbox(
                "Crane Type *",
                options=list(CRANE_COMPONENTS.keys()),
                help="Select the crane model being investigated",
            )

            components = CRANE_COMPONENTS.get(crane_type, [])
            component = st.selectbox(
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
                placeholder=(
                    "e.g. Outdoor installation, ambient ~35°C, high dust from nearby grinding. "
                    "Recent heavy rain, humidity ~95%."
                ),
                height=90,
                help="Temperature, dust, humidity, indoor/outdoor, special conditions",
            )

            recent_changes = st.text_area(
                "Recent Maintenance / Changes",
                placeholder=(
                    "e.g. Brake disc replaced 2 weeks ago. "
                    "Control panel fuse replaced yesterday. "
                    "No recent maintenance recorded."
                ),
                height=90,
                help="Any recent repairs, replacements, or modifications",
            )

            error_messages = st.text_area(
                "Error Messages / Fault Codes",
                placeholder=(
                    "e.g. PLC display shows E09 (motor thermal trip). "
                    "Overload relay L1 indicator lit. "
                    "No error codes visible."
                ),
                height=90,
                help="Any error codes, warning lights, or diagnostic messages shown",
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
                with st.spinner("🤖 Creating session and loading AI context..."):
                    payload = {
                        "crane_type": crane_type,
                        "component": component,
                        "problem_description": problem_description.strip(),
                        "environment": environment.strip() or None,
                        "recent_changes": recent_changes.strip() or None,
                        "error_messages": error_messages.strip() or None,
                    }
                    resp = api("post", "/sessions", json=payload)

                if handle_api_error(resp, "Failed to create session"):
                    data = resp.json()
                    session_id = data["session_id"]
                    opening_msg = data.get("opening_message", "")
                    evidence = data.get("retrieved_evidence", [])

                    # Initialise guidance screen state
                    st.session_state.current_session_id = session_id
                    st.session_state.messages = [
                        {"role": "assistant", "content": opening_msg}
                    ]
                    st.session_state.evidence = evidence
                    st.session_state.session_state_data = {
                        "component": component,
                        "crane_type": crane_type,
                        "status": "active",
                        "completed_steps": [],
                        "likely_causes": [],
                        "current_hypothesis": None,
                    }
                    st.session_state.measurements_submitted = []
                    st.session_state.screen = "guidance"
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
        completed_steps = _parse_list(sdata.get("completed_steps"))
        likely_causes = _parse_list(sdata.get("likely_causes"))
        current_hypothesis = sdata.get("current_hypothesis")
        st.session_state.session_state_data = {
            "component": sdata["component"],
            "crane_type": sdata["crane_type"],
            "status": sdata["status"],
            "completed_steps": completed_steps,
            "likely_causes": likely_causes,
            "current_hypothesis": current_hypothesis,
        }

    ssd = st.session_state.session_state_data

    # Header
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"""
        <div style="margin-bottom:12px;">
            <h2 style="font-size:1.3rem; font-weight:700; color:#1a1f36; margin:0 0 4px 0;">
                🔍 Diagnostic Session #{session_id}
            </h2>
            <p style="color:#6b7280; font-size:0.85rem; margin:0;">
                <b>{ssd.get('crane_type','')}</b> · {ssd.get('component','')}
                &nbsp;&nbsp;
                <span class="badge badge-{'active' if ssd.get('status')=='active' else 'completed'}">
                    {ssd.get('status','active').upper()}
                </span>
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_h2:
        if st.button("⚡ Generate Report", type="primary", use_container_width=True):
            with st.spinner("Generating report..."):
                resp = api("post", f"/sessions/{session_id}/report")
            if handle_api_error(resp, "Report generation failed"):
                report_data = resp.json()
                st.session_state.pending_report = report_data
                st.success("Report generated! View it in the Dashboard.")
                st.session_state.screen = "dashboard"
                st.rerun()

    # ── Three-column layout ──────────────────────────────────────
    chat_col, right_col = st.columns([3, 2])

    # ── LEFT: Chat panel ─────────────────────────────────────────
    with chat_col:
        st.markdown('<div class="section-header">💬 Diagnostic Chat</div>', unsafe_allow_html=True)

        # Chat display — use native st.chat_message so markdown renders properly
        for msg in st.session_state.messages:
            if msg["role"] == "assistant":
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("user", avatar="👷"):
                    st.markdown(msg["content"])

        st.markdown("<br>", unsafe_allow_html=True)

        # Chat input
        with st.form("chat_form", clear_on_submit=True):
            user_input = st.text_area(
                "Your response",
                placeholder=(
                    "Type your observations, measurements, or answers here...\n"
                    "e.g. 'Voltage on L1: 402V, L2: 398V, L3: 401V. "
                    "Motor humming but not rotating. Brake appears to be engaged.'"
                ),
                height=90,
                label_visibility="collapsed",
            )
            col_f1, col_f2 = st.columns([4, 1])
            with col_f2:
                send_btn = st.form_submit_button("Send →", use_container_width=True, type="primary")

        if send_btn and user_input.strip():
            with st.spinner("🤖 Analysing..."):
                resp = api(
                    "post",
                    f"/sessions/{session_id}/chat",
                    json={"message": user_input.strip()},
                )
            if handle_api_error(resp, "Chat failed"):
                data = resp.json()
                st.session_state.messages.append({"role": "user", "content": user_input.strip()})
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": data["message"]["content"],
                })
                st.session_state.evidence = data.get("retrieved_evidence", [])
                # Update session state
                ss = data.get("session_state", {})
                st.session_state.session_state_data.update({
                    "completed_steps": ss.get("completed_steps", []),
                    "likely_causes": ss.get("likely_causes", []),
                    "current_hypothesis": ss.get("current_hypothesis"),
                    "status": ss.get("status", "active"),
                })
                st.rerun()

    # ── RIGHT: Panels ────────────────────────────────────────────
    with right_col:
        right_tab1, right_tab2, right_tab3 = st.tabs(["📐 Measurements", "📚 Evidence", "📊 Session State"])

        # ── Tab 1: Measurement Input ──────────────────────────────
        with right_tab1:
            st.markdown('<div class="section-header">Record Measurements</div>', unsafe_allow_html=True)

            with st.form("measurement_form", clear_on_submit=True):
                mcol1, mcol2 = st.columns(2)
                with mcol1:
                    voltage = st.number_input("Voltage (V)", min_value=0.0, max_value=1000.0,
                                               value=None, format="%.1f", placeholder="e.g. 400.0")
                    temperature = st.number_input("Temperature (°C)", min_value=-50.0, max_value=300.0,
                                                   value=None, format="%.1f", placeholder="e.g. 65.0")
                    brake_gap = st.number_input("Brake Gap (mm)", min_value=0.0, max_value=10.0,
                                                 value=None, format="%.2f", placeholder="e.g. 0.25")
                    insulation_res = st.number_input("Insulation Res. (MΩ)", min_value=0.0,
                                                      value=None, format="%.2f", placeholder="e.g. 5.0")

                with mcol2:
                    current = st.number_input("Current (A)", min_value=0.0, max_value=2000.0,
                                               value=None, format="%.2f", placeholder="e.g. 12.5")
                    load = st.number_input("Load (kg)", min_value=0.0, max_value=100000.0,
                                            value=None, format="%.0f", placeholder="e.g. 2500")
                    vibration = st.number_input("Vibration (mm/s RMS)", min_value=0.0, max_value=100.0,
                                                 value=None, format="%.2f", placeholder="e.g. 2.1")
                    notes = st.text_input("Notes", placeholder="Any additional observations")

                save_meas = st.form_submit_button("💾 Save Measurements", use_container_width=True)

            if save_meas:
                payload = {
                    k: v for k, v in {
                        "voltage": voltage,
                        "current": current,
                        "temperature": temperature,
                        "load": load,
                        "brake_gap": brake_gap,
                        "insulation_resistance": insulation_res,
                        "vibration": vibration,
                        "notes": notes or None,
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

            # Show recorded measurements
            if st.session_state.measurements_submitted:
                st.markdown('<div class="section-header" style="margin-top:16px;">Recorded This Session</div>',
                            unsafe_allow_html=True)
                for i, m in enumerate(reversed(st.session_state.measurements_submitted[-5:])):
                    parts = []
                    if m.get("voltage"): parts.append(f"**V:** {m['voltage']} V")
                    if m.get("current"): parts.append(f"**I:** {m['current']} A")
                    if m.get("temperature"): parts.append(f"**T:** {m['temperature']} °C")
                    if m.get("load"): parts.append(f"**Load:** {m['load']} kg")
                    if m.get("brake_gap"): parts.append(f"**Gap:** {m['brake_gap']} mm")
                    if m.get("insulation_resistance"): parts.append(f"**IR:** {m['insulation_resistance']} MΩ")
                    if m.get("vibration"): parts.append(f"**Vib:** {m['vibration']} mm/s")
                    if m.get("notes"): parts.append(f"*{m['notes']}*")
                    st.markdown(f"**#{len(st.session_state.measurements_submitted)-i}** " + "  ·  ".join(parts))

        # ── Tab 2: Retrieved Evidence ─────────────────────────────
        with right_tab2:
            st.markdown('<div class="section-header">Retrieved Technical Knowledge</div>',
                        unsafe_allow_html=True)

            evidence = st.session_state.evidence
            if evidence:
                for chunk in evidence:
                    relevance = chunk.get("relevance_score", 0)
                    relevance_bar = "█" * int(relevance * 10) + "░" * (10 - int(relevance * 10))
                    content_preview = chunk["content"][:350] + ("..." if len(chunk["content"]) > 350 else "")

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
                    '<p style="color:#9ca3af; font-size:0.85rem; text-align:center; '
                    'padding:24px 0;">No evidence retrieved yet.<br>Start the diagnostic conversation.</p>',
                    unsafe_allow_html=True
                )

        # ── Tab 3: Session State ──────────────────────────────────
        with right_tab3:
            st.markdown('<div class="section-header">Diagnostic Progress</div>', unsafe_allow_html=True)

            ssd = st.session_state.session_state_data

            # Component & status
            st.markdown(f"""
            <table style="width:100%; font-size:0.85rem; border-collapse:collapse;">
                <tr>
                    <td style="color:#6b7280; padding:4px 8px 4px 0; width:45%;">Component</td>
                    <td style="font-weight:600; color:#1e293b;">{ssd.get('component','–')}</td>
                </tr>
                <tr>
                    <td style="color:#6b7280; padding:4px 8px 4px 0;">Session Status</td>
                    <td>
                        <span class="badge badge-{'active' if ssd.get('status')=='active' else 'completed'}">
                            {ssd.get('status','active')}
                        </span>
                    </td>
                </tr>
            </table>
            """, unsafe_allow_html=True)

            # Current hypothesis
            hypothesis = ssd.get("current_hypothesis")
            if hypothesis:
                st.markdown("""
                <div class="section-header" style="margin-top:14px;">Current Working Hypothesis</div>
                """, unsafe_allow_html=True)
                st.info(hypothesis)

            # Completed steps
            steps = ssd.get("completed_steps", [])
            if steps:
                st.markdown("""
                <div class="section-header" style="margin-top:14px;">Completed Diagnostic Steps</div>
                """, unsafe_allow_html=True)
                for step in steps:
                    st.markdown(f'<div class="step-completed">✓ {step}</div>', unsafe_allow_html=True)

            # Likely causes
            causes = ssd.get("likely_causes", [])
            if causes:
                st.markdown("""
                <div class="section-header" style="margin-top:14px;">Likely Causes (Working List)</div>
                """, unsafe_allow_html=True)
                for cause in causes:
                    st.markdown(f'<div class="step-pending">◈ {cause}</div>', unsafe_allow_html=True)

            if not steps and not causes and not hypothesis:
                st.markdown(
                    '<p style="color:#9ca3af; font-size:0.85rem; text-align:center; padding:24px 0;">'
                    'Progress will appear here as the diagnosis develops.</p>',
                    unsafe_allow_html=True
                )


# ═══════════════════════════════════════════════════════════════════
# SCREEN 4: CRANE DASHBOARD
# ═══════════════════════════════════════════════════════════════════

def screen_dashboard():
    render_top_bar()

    # ── Title + view toggle ──────────────────────────────────────
    title_col, toggle_col = st.columns([3, 2])
    with title_col:
        st.markdown("""
        <div style="margin-bottom:8px;">
            <h2 style="font-size:1.4rem; font-weight:700; color:#1a1f36; margin:0 0 4px 0;">
                📊 Crane Dashboard
            </h2>
            <p style="color:#6b7280; font-size:0.9rem; margin:0;">
                View troubleshooting history, reports, and maintenance trends.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with toggle_col:
        st.markdown("<br>", unsafe_allow_html=True)
        view_mode = st.radio(
            "View",
            options=["My Sessions", "All Engineers"],
            horizontal=True,
            label_visibility="collapsed",
        )
    all_engineers = (view_mode == "All Engineers")

    if all_engineers:
        st.info("👥 Showing sessions from all engineers — read-only view for knowledge reuse.")

    # ── Fetch stats ──────────────────────────────────────────────
    stats_resp = api("get", "/dashboard/stats", params={"all_engineers": str(all_engineers).lower()})
    stats = {}
    if stats_resp.status_code == 200:
        stats = stats_resp.json()

    # ── Summary metric cards ──────────────────────────────────────
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.metric("Total Sessions", stats.get("total_sessions", 0))
    with mc2:
        st.metric("Completed", stats.get("completed_sessions", 0))
    with mc3:
        st.metric("Reports Generated", stats.get("total_reports", 0))
    with mc4:
        follow_up = stats.get("follow_up_needed", 0)
        st.metric("Follow-up Required", follow_up,
                  delta=f"⚠️ {follow_up} pending" if follow_up else None,
                  delta_color="inverse")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Filters ──────────────────────────────────────────────────
    with st.expander("🔍 Filter Sessions", expanded=True):
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
        with filter_col1:
            filter_crane = st.selectbox(
                "Filter by Crane",
                options=["All"] + list(CRANE_COMPONENTS.keys()),
            )
        with filter_col2:
            all_components = list({c for comps in CRANE_COMPONENTS.values() for c in comps})
            filter_component = st.selectbox(
                "Filter by Component",
                options=["All"] + sorted(all_components),
            )
        with filter_col3:
            filter_status = st.selectbox(
                "Filter by Status",
                options=["All", "active", "completed", "abandoned"],
            )
        with filter_col4:
            filter_severity = st.selectbox(
                "Filter by Severity",
                options=["All", "critical", "high", "medium", "low"],
            )

    # ── Fetch dashboard data ──────────────────────────────────────
    params = {"all_engineers": str(all_engineers).lower()}
    if filter_crane != "All":
        params["crane_type"] = filter_crane
    if filter_component != "All":
        params["component"] = filter_component

    dash_resp = api("get", "/dashboard", params=params)

    if dash_resp.status_code != 200:
        st.error("Failed to load dashboard data.")
        return

    entries = dash_resp.json()

    # Client-side filters
    if filter_status != "All":
        entries = [e for e in entries if e["status"] == filter_status]
    if filter_severity != "All":
        entries = [e for e in entries if e.get("severity") == filter_severity]

    # ── Charts ───────────────────────────────────────────────────
    if entries:
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            comp_counts = {}
            for e in entries:
                comp_counts[e["component"]] = comp_counts.get(e["component"], 0) + 1
            if comp_counts:
                df_comp = pd.DataFrame(
                    list(comp_counts.items()), columns=["Component", "Count"]
                ).sort_values("Count", ascending=False)
                fig = px.bar(
                    df_comp, x="Count", y="Component", orientation="h",
                    title="Issues by Component",
                    color="Count",
                    color_continuous_scale="Blues",
                )
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0),
                                   showlegend=False, coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)

        with chart_col2:
            sev_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "no report": 0}
            for e in entries:
                sev = e.get("severity") or ("no report" if not e["has_report"] else "no report")
                sev_counts[sev] = sev_counts.get(sev, 0) + 1
            sev_counts = {k: v for k, v in sev_counts.items() if v > 0}
            if sev_counts:
                df_sev = pd.DataFrame(
                    list(sev_counts.items()), columns=["Severity", "Count"]
                )
                color_map = {
                    "critical": "#ef4444", "high": "#f97316",
                    "medium": "#eab308", "low": "#22c55e", "no report": "#94a3b8"
                }
                fig2 = px.pie(
                    df_sev, names="Severity", values="Count",
                    title="Issues by Severity",
                    color="Severity",
                    color_discrete_map=color_map,
                )
                fig2.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0))
                st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Session / Report table ────────────────────────────────────
    st.markdown(f'<div class="section-header">Sessions ({len(entries)} found)</div>',
                unsafe_allow_html=True)

    if not entries:
        st.info("No sessions found. Use 'New Issue' to start your first troubleshooting session.")
        return

    for entry in entries:
        sev = entry.get("severity")
        sev_icon = SEVERITY_ICONS.get(sev, "⚪")
        has_report = entry["has_report"]
        status = entry["status"]

        with st.expander(
            f"{sev_icon}  #{entry['session_id']}  ·  {entry['crane_type']}  ·  "
            f"{entry['component']}  ·  {_format_date(entry['session_date'])}",
            expanded=False,
        ):
            if all_engineers:
                # ── All Engineers view: show report only, no chat access ──
                st.markdown(f"**Problem:** {entry['problem_description']}")
                meta_cols = st.columns(3)
                with meta_cols[0]:
                    st.markdown(f"👷 **Engineer:** {entry['engineer_name']}")
                with meta_cols[1]:
                    status_badge = "badge-active" if status == "active" else "badge-completed"
                    st.markdown(
                        f'Status: <span class="badge {status_badge}">{status}</span>',
                        unsafe_allow_html=True,
                    )
                with meta_cols[2]:
                    if sev:
                        sev_badge = f"badge-{sev}"
                        st.markdown(
                            f'Severity: <span class="badge {sev_badge}">{sev.upper()}</span>',
                            unsafe_allow_html=True,
                        )

                if has_report and entry.get("report_id"):
                    st.markdown("---")
                    st.markdown("**📄 Fault Report**")
                    report_resp = api("get", f"/reports/{entry['report_id']}")
                    if report_resp.status_code == 200:
                        _render_report(report_resp.json())
                else:
                    st.caption("No report generated for this session yet.")

            else:
                # ── My Sessions view: full access with resume + generate ──
                dcol1, dcol2 = st.columns([2, 1])

                with dcol1:
                    st.markdown(f"**Problem:** {entry['problem_description']}")
                    st.markdown(f"**Engineer:** {entry['engineer_name']}")

                    status_badge = "badge-active" if status == "active" else "badge-completed"
                    st.markdown(
                        f'Status: <span class="badge {status_badge}">{status}</span>',
                        unsafe_allow_html=True,
                    )
                    if sev:
                        sev_badge = f"badge-{sev}"
                        st.markdown(
                            f'Severity: <span class="badge {sev_badge}">{sev.upper()}</span>',
                            unsafe_allow_html=True,
                        )

                with dcol2:
                    if entry["session_id"] == st.session_state.current_session_id:
                        if st.button("▶ Resume Session", key=f"resume_{entry['session_id']}",
                                     use_container_width=True, type="primary"):
                            st.session_state.screen = "guidance"
                            msgs_resp = api("get", f"/sessions/{entry['session_id']}/messages")
                            if msgs_resp.status_code == 200:
                                st.session_state.messages = [
                                    {"role": m["role"], "content": m["content"]}
                                    for m in msgs_resp.json()
                                ]
                            st.rerun()
                    else:
                        if st.button("View / Resume", key=f"view_{entry['session_id']}",
                                     use_container_width=True):
                            st.session_state.current_session_id = entry["session_id"]
                            msgs_resp = api("get", f"/sessions/{entry['session_id']}/messages")
                            if msgs_resp.status_code == 200:
                                st.session_state.messages = [
                                    {"role": m["role"], "content": m["content"]}
                                    for m in msgs_resp.json()
                                ]
                            meas_resp = api("get", f"/sessions/{entry['session_id']}/measurements")
                            if meas_resp.status_code == 200:
                                st.session_state.measurements_submitted = meas_resp.json()
                            st.session_state.screen = "guidance"
                            st.rerun()

                if has_report and entry.get("report_id"):
                    st.markdown("---")
                    st.markdown("**📄 Fault Report**")
                    report_resp = api("get", f"/reports/{entry['report_id']}")
                    if report_resp.status_code == 200:
                        _render_report(report_resp.json())

                if not has_report and status in ("active", "completed"):
                    st.markdown("---")
                    if st.button(
                        "⚡ Generate Report",
                        key=f"gen_report_{entry['session_id']}",
                        use_container_width=True,
                    ):
                        with st.spinner("Generating report..."):
                            resp = api("post", f"/sessions/{entry['session_id']}/report")
                        if handle_api_error(resp, "Report generation failed"):
                            st.success("Report generated!")
                            st.rerun()


def _render_report(r: dict):
    """Render a report inline in the dashboard."""
    # Diagnosis
    st.markdown(f"""
    <div class="report-section">
        <h4>Diagnosis</h4>
        <p style="font-size:0.9rem; color:#374151; margin:0; line-height:1.6;">{r.get('diagnosis','–')}</p>
    </div>
    """, unsafe_allow_html=True)

    # Root cause
    if r.get("root_cause"):
        st.markdown(f"""
        <div class="report-section">
            <h4>Root Cause</h4>
            <p style="font-size:0.9rem; color:#374151; margin:0; line-height:1.6;">{r.get('root_cause','–')}</p>
        </div>
        """, unsafe_allow_html=True)

    rep_col1, rep_col2 = st.columns(2)

    with rep_col1:
        # Steps taken
        steps = _parse_list(r.get("steps_taken"))
        if steps:
            st.markdown("**Steps Taken:**")
            for step in steps:
                st.markdown(f"✓ {step}")

    with rep_col2:
        # Recommendations
        recs = _parse_list(r.get("recommendations"))
        if recs:
            st.markdown("**Recommendations:**")
            for rec in recs:
                st.markdown(f"→ {rec}")

    # Measurements
    if r.get("measurements_summary") and r["measurements_summary"] != "No measurements recorded.":
        with st.expander("📐 Measurements recorded"):
            try:
                meas = json.loads(r["measurements_summary"])
                if meas:
                    st.json(meas)
            except (json.JSONDecodeError, TypeError):
                st.text(r["measurements_summary"])

    # Follow-up
    if r.get("follow_up_required"):
        st.warning("⚠️ Follow-up action required before returning crane to service.")


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
    elif screen == "intake":
        if not st.session_state.token:
            st.session_state.screen = "login"
            st.rerun()
        screen_intake()
    elif screen == "guidance":
        if not st.session_state.token:
            st.session_state.screen = "login"
            st.rerun()
        screen_guidance()
    elif screen == "dashboard":
        if not st.session_state.token:
            st.session_state.screen = "login"
            st.rerun()
        screen_dashboard()
    else:
        st.session_state.screen = "login"
        st.rerun()


if __name__ == "__main__":
    main()
