"""
Role-Permission Matrix for the AI-Assisted Process Guidance Tool.

This is the single authoritative source for what each role can do.
Endpoint guards and frontend visibility controls both reference this module.

Permissions use dot-notation: resource.action[:scope]
  e.g.  session.create
        session.read.own      (own sessions only)
        session.read.all      (all engineers' sessions)
        session.chat.escalated (chat in escalated sessions the SME owns)
"""

from access_control.roles import Role

# ─── Permission strings ───────────────────────────────────────────────────────

# Auth
P_AUTH_LOGIN          = "auth.login"           # public

# Sessions — basic
P_SESSION_CREATE      = "session.create"
P_SESSION_READ_OWN    = "session.read.own"
P_SESSION_READ_ALL    = "session.read.all"
P_SESSION_READ_ESCALATED = "session.read.escalated"
P_SESSION_CHAT_OWN    = "session.chat.own"
P_SESSION_CHAT_ESCALATED = "session.chat.escalated"
P_SESSION_MEASURE     = "session.measure"
P_SESSION_ESCALATE    = "session.escalate"      # ME → SME

# SME review actions
P_SESSION_ANNOTATE    = "session.annotate"
P_SESSION_VALIDATE_CAUSE = "session.validate_cause"
P_SESSION_FLAG_GAP    = "session.flag_knowledge_gap"
P_SESSION_RESOLVE     = "session.resolve"

# Reports
P_REPORT_CREATE       = "report.create"
P_REPORT_READ_ANY     = "report.read.any"
P_FOLLOW_UP_CLOSE     = "report.follow_up.close"

# Dashboard
P_DASHBOARD_OWN       = "dashboard.own"
P_DASHBOARD_ALL       = "dashboard.all"
P_DASHBOARD_ESCALATED = "dashboard.escalated"
P_DASHBOARD_STATS     = "dashboard.stats"
P_CRANE_HISTORY       = "crane_history.read"

# Knowledge
P_KNOWLEDGE_GAP_READ  = "knowledge_gap.read"
P_KNOWLEDGE_GAP_RESOLVE = "knowledge_gap.resolve"
P_KNOWLEDGE_BASE_EDIT = "knowledge_base.edit"

# Admin
P_USER_READ           = "user.read"
P_USER_CREATE         = "user.create"
P_USER_DEACTIVATE     = "user.deactivate"
P_ROLE_ASSIGN         = "role.assign"
P_AUDIT_LOG_READ      = "audit_log.read"
P_SYSTEM_CONFIGURE    = "system.configure"


# ─── Role → Permission mapping ────────────────────────────────────────────────

ROLE_PERMISSIONS: dict[str, set[str]] = {

    Role.ME: {
        P_SESSION_CREATE,
        P_SESSION_READ_OWN,
        P_SESSION_CHAT_OWN,
        P_SESSION_MEASURE,
        P_SESSION_ESCALATE,
        P_REPORT_CREATE,
        P_REPORT_READ_ANY,
        P_FOLLOW_UP_CLOSE,
        P_DASHBOARD_OWN,
        P_DASHBOARD_STATS,
        P_CRANE_HISTORY,
    },

    Role.SME: {
        P_SESSION_CREATE,
        P_SESSION_READ_OWN,
        P_SESSION_READ_ESCALATED,
        P_SESSION_CHAT_OWN,
        P_SESSION_CHAT_ESCALATED,
        P_SESSION_MEASURE,
        P_SESSION_ANNOTATE,
        P_SESSION_VALIDATE_CAUSE,
        P_SESSION_FLAG_GAP,
        P_SESSION_RESOLVE,
        P_REPORT_CREATE,
        P_REPORT_READ_ANY,
        P_FOLLOW_UP_CLOSE,
        P_DASHBOARD_OWN,
        P_DASHBOARD_ALL,
        P_DASHBOARD_ESCALATED,
        P_DASHBOARD_STATS,
        P_CRANE_HISTORY,
        P_KNOWLEDGE_GAP_READ,
    },

    Role.KE: {
        P_REPORT_READ_ANY,
        P_DASHBOARD_STATS,
        P_CRANE_HISTORY,
        P_KNOWLEDGE_GAP_READ,
        P_KNOWLEDGE_GAP_RESOLVE,
        P_KNOWLEDGE_BASE_EDIT,
    },

    Role.SUP: {
        P_SESSION_READ_ALL,
        P_REPORT_READ_ANY,
        P_DASHBOARD_OWN,
        P_DASHBOARD_ALL,
        P_DASHBOARD_ESCALATED,
        P_DASHBOARD_STATS,
        P_CRANE_HISTORY,
        P_AUDIT_LOG_READ,
    },

    Role.ADM: {
        P_USER_READ,
        P_USER_CREATE,
        P_USER_DEACTIVATE,
        P_ROLE_ASSIGN,
        P_AUDIT_LOG_READ,
        P_SYSTEM_CONFIGURE,
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Return True if the given role holds the requested permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())


def get_permissions(role: str) -> set[str]:
    """Return the full permission set for a role (empty set if unknown)."""
    return ROLE_PERMISSIONS.get(role, set())
