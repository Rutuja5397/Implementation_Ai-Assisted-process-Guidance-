"""
Crane AI – User Registry
Standalone Streamlit page that shows a live table of all registered users.
Reads directly from the SQLite database — no login required.

Run:
    streamlit run frontend/users_table.py --server.port 8503
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ─── Config ──────────────────────────────────────────────────────────────────

# Resolve DB path relative to this file's location (frontend/ → project root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_env_url = os.getenv("DATABASE_URL", "")
if _env_url:
    DB_PATH = _env_url.replace("sqlite:///", "")
    if not os.path.isabs(DB_PATH):
        DB_PATH = str(_PROJECT_ROOT / DB_PATH.lstrip("./"))
else:
    DB_PATH = str(_PROJECT_ROOT / "crane_ai.db")

ROLE_COLORS = {
    "ME":  "#3b82f6",
    "SME": "#8b5cf6",
    "KE":  "#10b981",
    "SUP": "#f59e0b",
    "ADM": "#ef4444",
}
ROLE_LABELS = {
    "ME":  "Maintenance Engineer",
    "SME": "Senior Engineer",
    "KE":  "Knowledge Engineer",
    "SUP": "Supervisor",
    "ADM": "Administrator",
}

# ─── Page setup ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Crane AI – User Registry",
    page_icon="👥",
    layout="wide",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .stat-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
    }
    .stat-num  { font-size: 2rem; font-weight: 800; line-height: 1.2; }
    .stat-lbl  { font-size: 0.75rem; color: #6b7280; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)


# ─── DB helpers ──────────────────────────────────────────────────────────────

def load_users() -> pd.DataFrame:
    """Load all users directly from SQLite."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            """
            SELECT
                id,
                name,
                username,
                role,
                is_active,
                created_at,
                last_login_at
            FROM users
            ORDER BY id ASC
            """,
            conn,
        )
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()


def fmt_dt(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    try:
        dt = datetime.fromisoformat(str(val))
        return dt.strftime("%d %b %Y  %H:%M")
    except Exception:
        return str(val)


# ─── Header ──────────────────────────────────────────────────────────────────

st.markdown("""
<div style="display:flex; align-items:center; gap:14px; padding:12px 0 24px 0;">
    <span style="font-size:2.8rem; line-height:1;">🏗️</span>
    <div>
        <div style="font-size:1.5rem; font-weight:800; color:#1a1f36;">
            Crane AI — User Registry
        </div>
        <div style="font-size:0.85rem; color:#6b7280; margin-top:2px;">
            All registered users · Live view from database
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── Load data ───────────────────────────────────────────────────────────────

df = load_users()

if df.empty:
    st.warning(f"No users found or database not accessible at `{DB_PATH}`.")
    st.stop()

total = len(df)
active_count = int(df["is_active"].sum()) if "is_active" in df.columns else total

# ─── Summary stats ───────────────────────────────────────────────────────────

cols = st.columns(7)

with cols[0]:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-num" style="color:#1a1f36;">{total}</div>
        <div class="stat-lbl">Total Users</div>
    </div>""", unsafe_allow_html=True)

with cols[1]:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-num" style="color:#10b981;">{active_count}</div>
        <div class="stat-lbl">Active</div>
    </div>""", unsafe_allow_html=True)

role_order = ["ME", "SME", "KE", "SUP", "ADM"]
for i, role in enumerate(role_order):
    count = int((df["role"] == role).sum()) if "role" in df.columns else 0
    color = ROLE_COLORS.get(role, "#6b7280")
    with cols[i + 2]:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-num" style="color:{color};">{count}</div>
            <div class="stat-lbl">{role}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Filters ─────────────────────────────────────────────────────────────────

fcol1, fcol2, fcol3 = st.columns([3, 2, 2])

with fcol1:
    search = st.text_input("Search", placeholder="Filter by name or username…", label_visibility="collapsed")

with fcol2:
    role_filter = st.multiselect(
        "Role",
        options=["ME", "SME", "KE", "SUP", "ADM"],
        default=[],
        placeholder="All roles",
        label_visibility="collapsed",
    )

with fcol3:
    status_filter = st.selectbox(
        "Status",
        options=["All", "Active only", "Inactive only"],
        label_visibility="collapsed",
    )

# Apply filters
filtered = df.copy()

if search:
    mask = (
        filtered["name"].str.contains(search, case=False, na=False) |
        filtered["username"].str.contains(search, case=False, na=False)
    )
    filtered = filtered[mask]

if role_filter:
    filtered = filtered[filtered["role"].isin(role_filter)]

if status_filter == "Active only":
    filtered = filtered[filtered["is_active"] == 1]
elif status_filter == "Inactive only":
    filtered = filtered[filtered["is_active"] == 0]

st.markdown(
    f'<div style="font-size:0.8rem;color:#6b7280;margin-bottom:8px;">'
    f'Showing {len(filtered)} of {total} users</div>',
    unsafe_allow_html=True,
)

# ─── Table ───────────────────────────────────────────────────────────────────

# Build a clean display DataFrame
display_df = filtered.copy()
display_df["role_label"] = display_df["role"].map(lambda r: ROLE_LABELS.get(r, r))
display_df["status"]     = display_df["is_active"].map(lambda v: "Active" if v else "Inactive")
display_df["registered"] = display_df["created_at"].apply(fmt_dt)
display_df["last_login"] = display_df["last_login_at"].apply(fmt_dt)

table_df = display_df[["id", "name", "username", "role", "role_label", "status", "registered", "last_login"]].rename(columns={
    "id":         "ID",
    "name":       "Full Name",
    "username":   "Username",
    "role":       "Role",
    "role_label": "Role Title",
    "status":     "Status",
    "registered": "Registered",
    "last_login": "Last Login",
})

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
    height=min(38 + len(table_df) * 35, 600),
    column_config={
        "ID":         st.column_config.NumberColumn("ID",         width="small"),
        "Full Name":  st.column_config.TextColumn("Full Name",    width="medium"),
        "Username":   st.column_config.TextColumn("Username",     width="medium"),
        "Role":       st.column_config.TextColumn("Role",         width="small"),
        "Role Title": st.column_config.TextColumn("Role Title",   width="medium"),
        "Status":     st.column_config.TextColumn("Status",       width="small"),
        "Registered": st.column_config.TextColumn("Registered",   width="medium"),
        "Last Login": st.column_config.TextColumn("Last Login",   width="medium"),
    },
)

# ─── Export ──────────────────────────────────────────────────────────────────

st.markdown("<br>", unsafe_allow_html=True)
exp_col1, exp_col2, _ = st.columns([2, 2, 6])

with exp_col1:
    csv = filtered[["id","name","username","role","is_active","created_at","last_login_at"]].to_csv(index=False)
    st.download_button(
        label="⬇ Export CSV",
        data=csv,
        file_name=f"crane_ai_users_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

with exp_col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# ─── Footer ──────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style="text-align:center;color:#d1d5db;font-size:0.75rem;padding:32px 0 8px 0;">
    Crane AI · User Registry · Reading from <code style="color:#9ca3af;">{DB_PATH}</code>
    · {datetime.now().strftime("%d %b %Y, %H:%M")}
</div>
""", unsafe_allow_html=True)
