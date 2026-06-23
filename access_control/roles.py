"""
Role definitions for the AI-Assisted Process Guidance Tool.
Single source of truth for all role strings used across the application.
"""

from enum import Enum


class Role(str, Enum):
    ME  = "ME"   # Maintenance Engineer (field-level)
    SME = "SME"  # Senior Maintenance Engineer / Subject Matter Expert
    KE  = "KE"   # Knowledge Engineer
    SUP = "SUP"  # Supervisor / Maintenance Manager
    ADM = "ADM"  # System Administrator


# Ordered from lowest to highest authority (informational only — not used for inheritance)
ROLE_DISPLAY_NAMES = {
    Role.ME:  "Maintenance Engineer",
    Role.SME: "Senior Engineer / SME",
    Role.KE:  "Knowledge Engineer",
    Role.SUP: "Supervisor",
    Role.ADM: "System Administrator",
}

# Roles that are allowed to perform diagnostic work (create/chat sessions)
DIAGNOSTIC_ROLES = {Role.ME, Role.SME}

# Roles that can see cross-engineer session data
MANAGEMENT_ROLES = {Role.SME, Role.SUP, Role.ADM}

# Roles that can see knowledge gap cases
KNOWLEDGE_ROLES  = {Role.KE, Role.SME}

# Roles that can access the admin panel
ADMIN_ROLES      = {Role.ADM}
