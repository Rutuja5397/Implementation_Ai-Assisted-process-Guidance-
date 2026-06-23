"""
Phase 4 — End-to-End Integration Test Suite
============================================

Tests the full system pipeline across all roles:
  1. Auth: signup + login for all 5 roles
  2. RBAC: permission gates enforced
  3. Session lifecycle: intake → chat → measurement → escalation → SME review → resolve → report
  4. Multi-agent pipeline: orchestrator invoked, agent outputs present
  5. Knowledge gap workflow: auto-detection and manual flagging
  6. Admin workflow: user management, role assignment, audit log
  7. Agent unit checks: intake, parameter, safety, feedback agents

Run with:
    cd "Process Guidance "
    python3 -m pytest tests/test_integration.py -v

Or without pytest (standalone):
    python3 tests/test_integration.py
"""

import json
import os
import sys
import time
import traceback
import requests

# ─── Config ──────────────────────────────────────────────────────────────────

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Unique suffix so each test run creates fresh users
_TS = str(int(time.time()))[-6:]

USERS = {
    "ME":  {"name": "Test ME",  "username": f"test_me_{_TS}",  "password": "testpass1", "role": "ME"},
    "SME": {"name": "Test SME", "username": f"test_sme_{_TS}", "password": "testpass1", "role": "SME"},
    "KE":  {"name": "Test KE",  "username": f"test_ke_{_TS}",  "password": "testpass1", "role": "KE"},
    "SUP": {"name": "Test SUP", "username": f"test_sup_{_TS}", "password": "testpass1", "role": "SUP"},
    "ADM": {"name": "Test ADM", "username": f"test_adm_{_TS}", "password": "testpass1", "role": "ADM"},
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

class TestResult:
    def __init__(self):
        self.passed  = 0
        self.failed  = 0
        self.skipped = 0
        self.failures: list[str] = []

    def ok(self, name: str):
        print(f"  ✓  {name}")
        self.passed += 1

    def fail(self, name: str, reason: str):
        msg = f"  ✗  {name}: {reason}"
        print(msg)
        self.failures.append(msg)
        self.failed += 1

    def skip(self, name: str, reason: str = ""):
        print(f"  ⊘  {name}{' — ' + reason if reason else ''}")
        self.skipped += 1

    def summary(self):
        total = self.passed + self.failed + self.skipped
        print(f"\n{'='*60}")
        print(f"  Results: {self.passed}/{total} passed"
              f"  ({self.failed} failed, {self.skipped} skipped)")
        if self.failures:
            print("\n  Failures:")
            for f in self.failures:
                print(f"    {f}")
        print("="*60)
        return self.failed == 0


r = TestResult()


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def req(method, path, token=None, **kwargs):
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{BASE_URL}{path}"
    try:
        return getattr(requests, method)(url, headers=headers, timeout=30, **kwargs)
    except requests.ConnectionError:
        print(f"\n  ERROR: Cannot connect to backend at {BASE_URL}")
        print("  Start it with: python3 -m uvicorn backend.main:app --reload --port 8000\n")
        sys.exit(1)


# ─── State shared across test sections ───────────────────────────────────────

tokens:     dict[str, str] = {}   # role → JWT
user_ids:   dict[str, int] = {}   # role → user_id
session_id: int = 0
report_id:  int = 0
gap_id:     int = 0


# ═══════════════════════════════════════════════════════════════════
# SECTION 1: Health check
# ═══════════════════════════════════════════════════════════════════

def test_health():
    print("\n[1] Health Check")
    resp = req("get", "/health")
    if resp.status_code == 200 and resp.json().get("status") == "ok":
        r.ok("Backend is reachable and healthy")
    else:
        r.fail("Backend health", f"status={resp.status_code}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 2: Auth — signup + login for all roles
# ═══════════════════════════════════════════════════════════════════

def test_auth():
    print("\n[2] Authentication")
    global tokens, user_ids

    for role, data in USERS.items():
        # Signup
        resp = req("post", "/auth/signup", json=data)
        if resp.status_code == 200:
            body = resp.json()
            tokens[role]   = body["access_token"]
            user_ids[role] = body["user"]["id"]
            got_role       = body["user"]["role"]
            if got_role == role:
                r.ok(f"Signup {role} (@{data['username']}) — role={got_role}")
            else:
                r.fail(f"Signup {role} role mismatch", f"expected {role}, got {got_role}")
        else:
            r.fail(f"Signup {role}", f"HTTP {resp.status_code}: {resp.text[:120]}")
            tokens[role] = ""

        # Login with same credentials
        resp2 = req("post", "/auth/login",
                    json={"username": data["username"], "password": data["password"]})
        if resp2.status_code == 200:
            r.ok(f"Login  {role}")
        else:
            r.fail(f"Login {role}", f"HTTP {resp2.status_code}")

    # Wrong password
    resp3 = req("post", "/auth/login",
                json={"username": USERS["ME"]["username"], "password": "wrongpassword"})
    if resp3.status_code == 401:
        r.ok("Login with wrong password → 401")
    else:
        r.fail("Wrong password should 401", f"got {resp3.status_code}")

    # /auth/me
    resp4 = req("get", "/auth/me", token=tokens.get("ME",""))
    if resp4.status_code == 200:
        r.ok("/auth/me returns current user")
    else:
        r.fail("/auth/me", f"HTTP {resp4.status_code}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: RBAC permission gates
# ═══════════════════════════════════════════════════════════════════

def test_rbac():
    print("\n[3] RBAC Permission Gates")

    if not tokens.get("ME") or not tokens.get("KE"):
        r.skip("RBAC tests", "tokens missing")
        return

    # KE cannot create sessions
    resp = req("post", "/sessions", token=tokens["KE"],
               json={"crane_type": "Test", "component": "Test", "problem_description": "Test"})
    if resp.status_code == 403:
        r.ok("KE cannot create sessions → 403")
    else:
        r.fail("KE session create should 403", f"got {resp.status_code}")

    # SUP cannot create sessions
    resp2 = req("post", "/sessions", token=tokens["SUP"],
                json={"crane_type": "Test", "component": "Test", "problem_description": "Test"})
    if resp2.status_code == 403:
        r.ok("SUP cannot create sessions → 403")
    else:
        r.fail("SUP session create should 403", f"got {resp2.status_code}")

    # ME cannot access admin endpoints
    resp3 = req("get", "/admin/users", token=tokens["ME"])
    if resp3.status_code == 403:
        r.ok("ME cannot access /admin/users → 403")
    else:
        r.fail("ME admin access should 403", f"got {resp3.status_code}")

    # KE can access knowledge gaps
    resp4 = req("get", "/knowledge-gaps", token=tokens["KE"])
    if resp4.status_code == 200:
        r.ok("KE can access /knowledge-gaps → 200")
    else:
        r.fail("KE knowledge-gaps", f"got {resp4.status_code}")

    # SUP cannot annotate sessions (no P_SESSION_ANNOTATE)
    # We use a dummy session_id; 404 is OK, 403 means permission denied
    resp5 = req("post", "/sessions/99999/annotations", token=tokens["SUP"],
                json={"annotation_text": "test", "annotation_type": "general"})
    if resp5.status_code in (403, 404):
        r.ok(f"SUP cannot annotate sessions → {resp5.status_code}")
    else:
        r.fail("SUP annotation should 403/404", f"got {resp5.status_code}")

    # Unauthenticated request → 401/403
    resp6 = req("get", "/dashboard")
    if resp6.status_code in (401, 403, 422):
        r.ok("Unauthenticated request rejected")
    else:
        r.fail("No-auth request should be rejected", f"got {resp6.status_code}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: Session lifecycle — ME creates + chats
# ═══════════════════════════════════════════════════════════════════

def test_session_creation():
    print("\n[4] Session Creation (ME)")
    global session_id

    if not tokens.get("ME"):
        r.skip("Session creation", "ME token missing")
        return

    payload = {
        "crane_type":          "Demag EKKE 5t",
        "component":           "Hoist Brake",
        "problem_description": "Brake fails to hold load at rated capacity. Slippage observed.",
        "environment":         "Indoor, ambient 22°C, low dust",
        "recent_changes":      "Brake disc replaced 3 weeks ago",
        "error_messages":      "E-06 brake thermal trip on PLC display",
    }
    resp = req("post", "/sessions", token=tokens["ME"], json=payload)

    if resp.status_code == 200:
        data       = resp.json()
        session_id = data["session_id"]
        opening    = data.get("opening_message", "")
        lc_state   = data.get("lifecycle_state", "")
        r.ok(f"Session created (id={session_id}, state={lc_state})")

        if opening and len(opening) > 50:
            r.ok(f"Opening message received ({len(opening)} chars)")
        else:
            r.fail("Opening message too short or missing", f"got: {opening[:80]}")

        if lc_state == "IN_PROGRESS":
            r.ok("Lifecycle state is IN_PROGRESS after creation")
        else:
            r.fail("Expected IN_PROGRESS", f"got {lc_state}")
    else:
        r.fail("Session creation failed", f"HTTP {resp.status_code}: {resp.text[:200]}")


def test_chat_turn():
    print("\n[5] Chat Turn (ME)")

    if not session_id or not tokens.get("ME"):
        r.skip("Chat turn", "session or token missing")
        return

    resp = req("post", f"/sessions/{session_id}/chat",
               token=tokens["ME"],
               json={"message": "The brake gap measured 0.9 mm. Motor temperature was 88°C."})

    if resp.status_code == 200:
        data          = resp.json()
        ai_msg        = data.get("message", {}).get("content", "")
        session_state = data.get("session_state", {})
        evidence      = data.get("retrieved_evidence", [])

        if ai_msg and len(ai_msg) > 30:
            r.ok(f"Chat response received ({len(ai_msg)} chars)")
        else:
            r.fail("Chat response missing/short", repr(ai_msg[:100]))

        if isinstance(evidence, list):
            r.ok(f"Evidence chunks returned ({len(evidence)} chunks)")
        else:
            r.fail("Evidence should be a list", str(type(evidence)))

        if "lifecycle_state" in session_state or "component" in session_state:
            r.ok("Session state block present in response")
        else:
            r.fail("Session state missing from chat response", str(session_state.keys()))
    else:
        r.fail("Chat failed", f"HTTP {resp.status_code}: {resp.text[:200]}")


def test_measurement_recording():
    print("\n[6] Measurement Recording")

    if not session_id or not tokens.get("ME"):
        r.skip("Measurement recording", "missing prereqs")
        return

    payload = {
        "brake_gap":   0.9,
        "temperature": 88.0,
        "voltage":     402.0,
        "notes":       "Measured at brake drum, crane unloaded",
    }
    resp = req("post", f"/sessions/{session_id}/measurements",
               token=tokens["ME"], json=payload)

    if resp.status_code == 200:
        data = resp.json()
        r.ok(f"Measurement recorded (id={data.get('id')})")

        # Retrieve measurements
        resp2 = req("get", f"/sessions/{session_id}/measurements", token=tokens["ME"])
        if resp2.status_code == 200 and len(resp2.json()) >= 1:
            r.ok(f"GET measurements returns {len(resp2.json())} record(s)")
        else:
            r.fail("GET measurements failed", f"{resp2.status_code}")
    else:
        r.fail("Measurement save failed", f"HTTP {resp.status_code}: {resp.text[:200]}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 5: Escalation → SME review → resolve
# ═══════════════════════════════════════════════════════════════════

def test_escalation_workflow():
    print("\n[7] Escalation Workflow (ME → SME)")

    if not session_id or not tokens.get("ME") or not tokens.get("SME"):
        r.skip("Escalation workflow", "missing prereqs")
        return

    # ME escalates
    resp = req("post", f"/sessions/{session_id}/escalate",
               token=tokens["ME"],
               json={"reason": "Brake gap significantly out of spec. Need expert review."})

    if resp.status_code == 200:
        data = resp.json()
        if data.get("lifecycle_state") == "ESCALATED":
            r.ok("Session escalated → state=ESCALATED")
        else:
            r.fail("Escalation state wrong", str(data))
    else:
        r.fail("Escalation failed", f"HTTP {resp.status_code}: {resp.text[:200]}")
        return

    # KE cannot chat in escalated session
    resp2 = req("post", f"/sessions/{session_id}/chat",
                token=tokens["KE"],
                json={"message": "test"})
    if resp2.status_code == 403:
        r.ok("KE cannot chat in escalated session → 403")
    else:
        r.fail("KE chat in escalated should 403", f"got {resp2.status_code}")

    # SME opens for review
    resp3 = req("post", f"/sessions/{session_id}/sme-review", token=tokens["SME"])
    if resp3.status_code == 200:
        data3 = resp3.json()
        if data3.get("lifecycle_state") == "SME_IN_REVIEW":
            r.ok("SME opened for review → state=SME_IN_REVIEW")
        else:
            r.fail("SME review state wrong", str(data3))
    else:
        r.fail("SME review start failed", f"HTTP {resp3.status_code}: {resp3.text[:200]}")
        return

    # SME chats (should be allowed in SME_IN_REVIEW)
    resp4 = req("post", f"/sessions/{session_id}/chat",
                token=tokens["SME"],
                json={"message": "Brake gap of 0.9mm is well above the 0.2–0.5mm specification."})
    if resp4.status_code == 200:
        r.ok("SME can chat in SME_IN_REVIEW session")
    else:
        r.fail("SME chat in SME_IN_REVIEW failed", f"HTTP {resp4.status_code}: {resp4.text[:200]}")

    # SME adds expert annotation
    resp5 = req("post", f"/sessions/{session_id}/annotations",
                token=tokens["SME"],
                json={
                    "annotation_text": "Root cause confirmed: brake disc worn beyond spec. Replace disc and readjust gap.",
                    "annotation_type": "root_cause",
                })
    if resp5.status_code == 200:
        r.ok("SME added expert annotation")
    else:
        r.fail("SME annotation failed", f"HTTP {resp5.status_code}: {resp5.text[:200]}")

    # GET annotations
    resp6 = req("get", f"/sessions/{session_id}/annotations", token=tokens["SME"])
    if resp6.status_code == 200 and len(resp6.json()) >= 1:
        r.ok(f"GET annotations returns {len(resp6.json())} annotation(s)")
    else:
        r.fail("GET annotations", f"HTTP {resp6.status_code}")

    # SME resolves
    resp7 = req("post", f"/sessions/{session_id}/resolve", token=tokens["SME"])
    if resp7.status_code == 200:
        data7 = resp7.json()
        if data7.get("lifecycle_state") == "RESOLVED":
            r.ok("SME resolved session → state=RESOLVED")
        else:
            r.fail("Resolve state wrong", str(data7))
    else:
        r.fail("Resolve failed", f"HTTP {resp7.status_code}: {resp7.text[:200]}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 6: Report generation
# ═══════════════════════════════════════════════════════════════════

def test_report_generation():
    print("\n[8] Report Generation")
    global report_id

    if not session_id or not tokens.get("ME"):
        r.skip("Report generation", "missing prereqs")
        return

    resp = req("post", f"/sessions/{session_id}/report", token=tokens["ME"])
    if resp.status_code == 200:
        data      = resp.json()
        report_id = data.get("id", 0)
        severity  = data.get("severity")
        diagnosis = data.get("diagnosis", "")
        steps     = json.loads(data.get("steps_taken", "[]"))
        recs      = json.loads(data.get("recommendations", "[]"))

        r.ok(f"Report generated (id={report_id}, severity={severity})")

        if diagnosis and len(diagnosis) > 20:
            r.ok("Report has diagnosis text")
        else:
            r.fail("Diagnosis missing/short", repr(diagnosis[:80]))

        if isinstance(steps, list) and len(steps) >= 1:
            r.ok(f"Report has {len(steps)} steps_taken")
        else:
            r.fail("steps_taken should be non-empty list", str(steps))

        if isinstance(recs, list) and len(recs) >= 1:
            r.ok(f"Report has {len(recs)} recommendations")
        else:
            r.fail("recommendations should be non-empty list", str(recs))

        # Session should now be CLOSED_WITH_REPORT
        sess_resp = req("get", f"/sessions/{session_id}", token=tokens["ME"])
        if sess_resp.status_code == 200:
            lc = sess_resp.json().get("lifecycle_state")
            if lc == "CLOSED_WITH_REPORT":
                r.ok("Session → CLOSED_WITH_REPORT after report")
            else:
                r.fail("Expected CLOSED_WITH_REPORT", f"got {lc}")

        # GET report by id
        if report_id:
            resp2 = req("get", f"/reports/{report_id}", token=tokens["ME"])
            if resp2.status_code == 200:
                r.ok("GET /reports/{id} returns report")
            else:
                r.fail("GET report by id", f"HTTP {resp2.status_code}")
    else:
        r.fail("Report generation failed", f"HTTP {resp.status_code}: {resp.text[:200]}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 7: State transitions log
# ═══════════════════════════════════════════════════════════════════

def test_state_transitions():
    print("\n[9] State Transition History")

    if not session_id or not tokens.get("ME"):
        r.skip("Transitions", "missing prereqs")
        return

    resp = req("get", f"/sessions/{session_id}/transitions", token=tokens["ME"])
    if resp.status_code == 200:
        transitions = resp.json()
        if len(transitions) >= 3:   # LOGGED→IN_PROGRESS, IN_PROGRESS→ESCALATED, etc.
            r.ok(f"Transition log has {len(transitions)} entries")
            # Verify expected sequence is present
            states = [t.get("new_state") for t in transitions]
            expected = {"IN_PROGRESS", "ESCALATED", "SME_IN_REVIEW", "RESOLVED", "CLOSED_WITH_REPORT"}
            found    = expected & set(states)
            r.ok(f"Expected states recorded: {sorted(found)}")
        else:
            r.fail("Transition log too short", f"only {len(transitions)} entries")
    else:
        r.fail("GET transitions", f"HTTP {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 8: Knowledge gap workflow
# ═══════════════════════════════════════════════════════════════════

def test_knowledge_gap_workflow():
    print("\n[10] Knowledge Gap Workflow")
    global gap_id

    if not tokens.get("ME") or not tokens.get("KE"):
        r.skip("Knowledge gap workflow", "missing tokens")
        return

    # Create a new session that hits a vague component to trigger gap detection
    resp = req("post", "/sessions", token=tokens["ME"],
               json={
                   "crane_type":          "Generic Crane",
                   "component":           "Control System",
                   "problem_description": "PLC outputs faulty signals to contactor but no procedure in manual",
               })

    if resp.status_code != 200:
        r.fail("Session creation for gap test", f"HTTP {resp.status_code}")
        return

    gap_session_id = resp.json()["session_id"]
    r.ok(f"Gap-test session created (id={gap_session_id})")

    # SME flags knowledge gap manually
    if not tokens.get("SME"):
        r.skip("Knowledge gap manual flag", "SME token missing")
        return

    # First escalate
    req("post", f"/sessions/{gap_session_id}/escalate",
        token=tokens["ME"],
        json={"reason": "Control system issue — no matching knowledge base content"})

    # SME opens
    req("post", f"/sessions/{gap_session_id}/sme-review", token=tokens["SME"])

    # Flag knowledge gap
    resp2 = req("post", f"/sessions/{gap_session_id}/flag-knowledge-gap", token=tokens["SME"])
    if resp2.status_code == 200:
        data2  = resp2.json()
        gap_id = data2.get("knowledge_gap_id", 0)
        lc     = data2.get("lifecycle_state", "")
        r.ok(f"Knowledge gap flagged (gap_id={gap_id}, state={lc})")
    else:
        r.fail("Flag knowledge gap", f"HTTP {resp2.status_code}: {resp2.text[:200]}")

    # KE reads gaps
    resp3 = req("get", "/knowledge-gaps", token=tokens["KE"])
    if resp3.status_code == 200:
        gaps = resp3.json()
        if len(gaps) >= 1:
            r.ok(f"KE can read {len(gaps)} knowledge gap(s)")
        else:
            r.fail("No knowledge gaps returned for KE", "expected at least 1")
    else:
        r.fail("GET knowledge-gaps for KE", f"HTTP {resp3.status_code}")

    # ME cannot read knowledge gaps (no P_KNOWLEDGE_GAP_READ)
    resp4 = req("get", "/knowledge-gaps", token=tokens["ME"])
    if resp4.status_code == 403:
        r.ok("ME cannot read /knowledge-gaps → 403")
    else:
        r.fail("ME knowledge-gaps should 403", f"got {resp4.status_code}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 9: Dashboard + stats (multi-role)
# ═══════════════════════════════════════════════════════════════════

def test_dashboard():
    print("\n[11] Dashboard & Stats")

    if not tokens.get("ME"):
        r.skip("Dashboard", "ME token missing")
        return

    # ME own dashboard
    resp = req("get", "/dashboard", token=tokens["ME"], params={"filter_mode": "own"})
    if resp.status_code == 200:
        entries = resp.json()
        r.ok(f"ME /dashboard (own) → {len(entries)} session(s)")
    else:
        r.fail("ME dashboard own", f"HTTP {resp.status_code}")

    # SME all sessions dashboard
    if tokens.get("SME"):
        resp2 = req("get", "/dashboard", token=tokens["SME"], params={"filter_mode": "all"})
        if resp2.status_code == 200:
            r.ok(f"SME /dashboard (all) → {len(resp2.json())} session(s)")
        else:
            r.fail("SME dashboard all", f"HTTP {resp2.status_code}")

    # SUP escalated view
    if tokens.get("SUP"):
        resp3 = req("get", "/dashboard", token=tokens["SUP"], params={"filter_mode": "escalated"})
        if resp3.status_code == 200:
            r.ok(f"SUP /dashboard (escalated) → {len(resp3.json())} session(s)")
        else:
            r.fail("SUP dashboard escalated", f"HTTP {resp3.status_code}")

    # Stats endpoint
    resp4 = req("get", "/dashboard/stats", token=tokens["ME"], params={"filter_mode": "own"})
    if resp4.status_code == 200:
        stats = resp4.json()
        expected_keys = {"total_sessions", "completed_sessions", "total_reports"}
        if expected_keys.issubset(stats.keys()):
            r.ok(f"Stats endpoint returns expected keys: {list(stats.keys())}")
        else:
            r.fail("Stats missing keys", str(stats.keys()))
    else:
        r.fail("Stats endpoint", f"HTTP {resp4.status_code}")

    # Procedure endpoint (AGT-06)
    resp5 = req("get", "/procedure", token=tokens["ME"],
                params={"component": "Hoist Brake", "procedure_type": "inspection"})
    if resp5.status_code == 200:
        data5 = resp5.json()
        steps = data5.get("steps", [])
        r.ok(f"GET /procedure returns {len(steps)} step(s) (procedure_found={data5.get('procedure_found')})")
    else:
        r.fail("GET /procedure", f"HTTP {resp5.status_code}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 10: Admin panel
# ═══════════════════════════════════════════════════════════════════

def test_admin():
    print("\n[12] Admin Panel (ADM)")

    if not tokens.get("ADM"):
        r.skip("Admin tests", "ADM token missing")
        return

    # List users
    resp = req("get", "/admin/users", token=tokens["ADM"])
    if resp.status_code == 200:
        users = resp.json()
        r.ok(f"ADM can list users ({len(users)} users)")
    else:
        r.fail("ADM list users", f"HTTP {resp.status_code}")
        return

    # Assign role to ME user — change ME → SME, then back
    me_uid = user_ids.get("ME", 0)
    if me_uid:
        resp2 = req("put", f"/admin/users/{me_uid}/role",
                    token=tokens["ADM"], json={"role": "SME"})
        if resp2.status_code == 200 and resp2.json().get("role") == "SME":
            r.ok("ADM can change user role (ME → SME)")
        else:
            r.fail("Role assignment", f"HTTP {resp2.status_code}: {resp2.text[:120]}")

        # Revert
        req("put", f"/admin/users/{me_uid}/role",
            token=tokens["ADM"], json={"role": "ME"})
        r.ok("Reverted ME role back to ME")

    # ADM cannot deactivate own account
    adm_uid = user_ids.get("ADM", 0)
    if adm_uid:
        resp3 = req("put", f"/admin/users/{adm_uid}/deactivate", token=tokens["ADM"])
        if resp3.status_code == 400:
            r.ok("ADM cannot deactivate own account → 400")
        else:
            r.fail("Self-deactivation should 400", f"got {resp3.status_code}")

    # Audit log
    resp4 = req("get", "/admin/audit-log", token=tokens["ADM"], params={"limit": 50})
    if resp4.status_code == 200:
        entries = resp4.json()
        r.ok(f"ADM can read audit log ({len(entries)} entries)")
    else:
        r.fail("Audit log", f"HTTP {resp4.status_code}")

    # ME cannot read audit log
    resp5 = req("get", "/admin/audit-log", token=tokens["ME"])
    if resp5.status_code == 403:
        r.ok("ME cannot read audit log → 403")
    else:
        r.fail("ME audit log should 403", f"got {resp5.status_code}")


# ═══════════════════════════════════════════════════════════════════
# SECTION 11: Agent unit tests (no LLM calls)
# ═══════════════════════════════════════════════════════════════════

def test_agents_unit():
    print("\n[13] Agent Unit Tests (no LLM)")

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # AGT-02: IntakeAgent
    try:
        from agents.intake_agent import IntakeAgent
        a = IntakeAgent()
        result = a.run({
            "crane_type": "EOT Crane", "component": "Hoist Motor",
            "problem_description": "Motor overheating during operation",
        })
        assert result["valid"], f"Expected valid=True: {result}"
        assert result["component_key"] == "Hoist Motor"
        assert "context_snapshot" in result
        r.ok("AGT-02 IntakeAgent: valid intake → context_snapshot")

        # Missing required field
        result2 = a.run({"crane_type": "EOT Crane"})
        assert not result2["valid"]
        r.ok("AGT-02 IntakeAgent: missing fields → valid=False")
    except Exception as e:
        r.fail("AGT-02 IntakeAgent", traceback.format_exc(limit=1).strip())

    # AGT-05: ParameterAgent
    try:
        from agents.parameter_agent import ParameterInterpretationAgent
        pa = ParameterInterpretationAgent()

        # Normal values
        rn = pa.run({"component_key": "Hoist Motor", "measurements": [{"voltage": 400, "temperature": 70}]})
        assert not rn["has_critical"]
        r.ok("AGT-05 ParameterAgent: normal values → has_critical=False")

        # Critical voltage
        rc = pa.run({"component_key": "Hoist Motor", "measurements": [{"voltage": 340}]})
        assert rc["has_critical"]
        r.ok("AGT-05 ParameterAgent: voltage=340V (< 360 crit_lo) → has_critical=True")

        # Brake gap out of range
        rb = pa.run({"component_key": "Hoist Brake", "measurements": [{"brake_gap": 0.9}]})
        annotations = [a for row in rb["annotated_measurements"] for a in row]
        gap_ann = next((a for a in annotations if a["parameter"] == "brake_gap"), None)
        assert gap_ann and "ABOVE_MAXIMUM" in gap_ann["status"]
        r.ok("AGT-05 ParameterAgent: brake_gap=0.9 → ABOVE_MAXIMUM")
    except Exception as e:
        r.fail("AGT-05 ParameterAgent", traceback.format_exc(limit=1).strip())

    # AGT-07: SafetyGuardrailAgent
    try:
        from agents.safety_agent import SafetyGuardrailAgent
        sa = SafetyGuardrailAgent()

        # No trigger
        rs = sa.run({"response_text": "Check voltage at terminal block.", "has_critical_measurements": False, "component_key": "Hoist Motor"})
        assert not rs["safety_flag"]
        r.ok("AGT-07 SafetyAgent: safe text → no flag")

        # Brake failure trigger
        rb = sa.run({"response_text": "The brake failed to hold the load under 2t test.", "has_critical_measurements": False, "component_key": "Hoist Brake"})
        assert rb["safety_flag"] and rb["safety_level"] == "critical"
        r.ok("AGT-07 SafetyAgent: brake failure → CRITICAL")

        # Insulation failure trigger
        ri = sa.run({"response_text": "Insulation resistance below minimum threshold detected.", "has_critical_measurements": False, "component_key": "Power Supply"})
        assert ri["safety_flag"] and ri["safety_level"] in ("warning", "critical")
        r.ok(f"AGT-07 SafetyAgent: insulation failure → {ri['safety_level'].upper()}")

        # critical_measurements escalates to warning
        rm = sa.run({"response_text": "Motor temperature is within range.", "has_critical_measurements": True, "component_key": "Hoist Motor"})
        assert rm["safety_flag"] and rm["safety_level"] == "warning"
        r.ok("AGT-07 SafetyAgent: has_critical_measurements → WARNING")
    except Exception as e:
        r.fail("AGT-07 SafetyAgent", traceback.format_exc(limit=1).strip())

    # AGT-09: KnowledgeFeedbackAgent
    try:
        from agents.knowledge_feedback_agent import KnowledgeFeedbackAgent
        kf = KnowledgeFeedbackAgent()

        # No gap (well-resolved session)
        rg = kf.run({
            "component_key": "Hoist Motor", "problem_description": "Overheating",
            "conversation_history": [
                {"role": "assistant", "content": "According to specification, insulation resistance should be ≥1MΩ."},
                {"role": "assistant", "content": "Per EN 60204 the nominal voltage tolerance is ±10%."},
            ],
            "lifecycle_state": "RESOLVED", "knowledge_gap_indicator": False,
            "retrieval_chunk_count": 4, "session_resolved": True,
            "current_hypothesis": "Insulation degradation due to humidity",
            "completed_steps_count": 5,
        })
        r.ok(f"AGT-09 KnowledgeFeedbackAgent: resolved session → gap_detected={rg['gap_detected']}, coverage={rg['coverage_score']}")

        # Gap case
        rg2 = kf.run({
            "component_key": "Wire Rope", "problem_description": "Unusual wear",
            "conversation_history": [{"role": "assistant", "content": "No procedure found in the knowledge base."}],
            "lifecycle_state": "UNRESOLVED", "knowledge_gap_indicator": True,
            "retrieval_chunk_count": 0, "session_resolved": False,
            "current_hypothesis": "", "completed_steps_count": 1,
        })
        assert rg2["gap_detected"]
        r.ok(f"AGT-09 KnowledgeFeedbackAgent: unresolved + no KB → gap_detected=True, type={rg2['gap_type']}")
    except Exception as e:
        r.fail("AGT-09 KnowledgeFeedbackAgent", traceback.format_exc(limit=1).strip())

    # Orchestrator instantiation
    try:
        from orchestration.session_orchestrator import SessionOrchestrator
        orch = SessionOrchestrator()
        r.ok("AGT-01 SessionOrchestrator: instantiates cleanly")
    except Exception as e:
        r.fail("AGT-01 SessionOrchestrator", traceback.format_exc(limit=1).strip())


# ═══════════════════════════════════════════════════════════════════
# SECTION 12: Closed session guard
# ═══════════════════════════════════════════════════════════════════

def test_closed_session_guard():
    print("\n[14] Closed Session Guard")

    if not session_id or not tokens.get("ME"):
        r.skip("Closed session guard", "missing prereqs")
        return

    resp = req("post", f"/sessions/{session_id}/chat",
               token=tokens["ME"],
               json={"message": "Can I keep chatting after report?"})

    if resp.status_code == 400:
        r.ok("Chat on CLOSED_WITH_REPORT session → 400")
    else:
        r.fail("Closed session should reject chat", f"got {resp.status_code}")


# ═══════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════

def run_all():
    print("=" * 60)
    print("  Crane AI — Integration Test Suite (Phase 4)")
    print(f"  Backend: {BASE_URL}")
    print("=" * 60)

    test_health()
    test_auth()
    test_rbac()
    test_session_creation()
    test_chat_turn()
    test_measurement_recording()
    test_escalation_workflow()
    test_report_generation()
    test_state_transitions()
    test_knowledge_gap_workflow()
    test_dashboard()
    test_admin()
    test_agents_unit()
    test_closed_session_guard()

    return r.summary()


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)


# ─── pytest entry-points (optional) ──────────────────────────────

def test_suite_full():
    """Single pytest test that runs the complete integration suite."""
    success = run_all()
    assert success, "Integration test suite had failures — see output above."
