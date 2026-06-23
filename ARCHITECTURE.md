# ARCHITECTURE.md
# System Architecture — AI-Assisted Process Guidance Tool (Version 2)
# Master Thesis, RPTU / Fraunhofer IESE, 2025

---

## 1. Architecture Overview

The AI-Assisted Process Guidance Tool is structured as a three-tier web application with an embedded multi-agent AI pipeline. The system is designed to support role-differentiated workflows for crane maintenance personnel, with all AI capabilities encapsulated in independent, orchestrated agent modules.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND TIER                                │
│   Streamlit multi-screen SPA (frontend/app.py)                      │
│   Role-aware UI rendering | Screen routing | JWT session state      │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP REST (JSON)
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                        BACKEND TIER                                 │
│   FastAPI application (backend/main.py)                             │
│   Auth middleware | Role-based endpoint guards | Request routing    │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │               MULTI-AGENT ORCHESTRATION LAYER               │  │
│   │   SessionOrchestrator → Agent Pipeline Coordination         │  │
│   │                                                             │  │
│   │  AGT-02     AGT-03      AGT-04      AGT-05     AGT-06       │  │
│   │  Intake   Retrieval  Diagnostic  Parameter  Procedure       │  │
│   │  Agent     Agent     Reasoning   Interpret.   Guidance      │  │
│   │                        Agent       Agent       Agent        │  │
│   │                          │                                  │  │
│   │               AGT-07: Safety / Guardrail Agent              │  │
│   │               AGT-08: Report Generation Agent               │  │
│   │               AGT-09: Knowledge Feedback Agent              │  │
│   └─────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬────────────────────────┬────────────┘
                                │                        │
        ┌───────────────────────▼───────┐   ┌────────────▼───────────┐
        │        DATA TIER              │   │     EXTERNAL TIER      │
        │  SQLite (crane_ai.db)         │   │  Anthropic API         │
        │  ChromaDB (chroma_db/)        │   │  (claude-sonnet-4-6)   │
        │  Knowledge Base (.txt files)  │   │                        │
        └───────────────────────────────┘   └────────────────────────┘
```

---

## 2. Key Architectural Drivers

| Driver | Rationale |
|--------|-----------|
| **Safety-advisory model** | The system is advisory-only. All safety decisions remain with qualified human personnel. The Safety Agent enforces this constraint at every response delivery point. |
| **Traceability** | Every AI recommendation must be traceable to a knowledge source. The RAG pipeline preserves source metadata through to the stored report. |
| **Role-differentiated access** | Industrial maintenance organisations have clear role hierarchies. The architecture encodes this as RBAC enforced server-side, not just in the UI. |
| **Agent independence** | Each AI agent is a self-contained module. This supports independent testing, versioning, and future replacement (e.g., upgrading the Diagnostic Reasoning Agent without changing the Retrieval Agent). |
| **Session persistence** | Fault diagnosis sessions may span multiple days and multiple engineers. All session state is database-persisted and resumable at any point. |
| **Knowledge grounding** | All AI responses are grounded in structured component manuals. Open-domain LLM hallucination is constrained by injecting only retrieved, sourced evidence into the prompt. |

---

## 3. Layered Architecture View

### Layer 1: Presentation Layer (Frontend)

**Technology**: Streamlit (Python)  
**File**: `frontend/app.py`  
**Responsibilities**:
- Render the appropriate screen based on `st.session_state.screen`
- Enforce client-side navigation rules (no protected screen accessible without auth token in session state)
- Display role-appropriate navigation options
- Render chat messages using `st.chat_message` with markdown rendering
- Display Evidence, Session State, and Measurements panels in tabbed layouts
- Handle form submission and call backend REST endpoints
- Display safety alerts as visually distinct warning components

**Screen Routing**:
```
login     → show login/signup form
intake    → show fault intake form (ME, SME only)
guidance  → show AI guidance interface (session owner + SME for escalated)
dashboard → role-specific dashboard (all authenticated roles)
admin     → user management screen (ADM only)
```

**Role-Based UI Elements**:
- Navigation sidebar items are filtered by `st.session_state.user.role`
- Action buttons (Escalate, Generate Report, Add Expert Note) are conditionally rendered
- "All Engineers" dashboard view is visible to SME, SUP, ADM only
- Knowledge gap review panel is visible to KE and SME only
- User management panel is visible to ADM only

---

### Layer 2: API Layer (Backend)

**Technology**: FastAPI (Python)  
**File**: `backend/main.py`  
**Responsibilities**:
- Expose REST endpoints for all system operations
- Authenticate all requests via JWT middleware
- Enforce role-based access control per endpoint using dependency injection
- Route authenticated requests to the appropriate orchestration or data service
- Return structured JSON responses

**Authentication Dependency**:
```python
# Every protected endpoint uses:
current_user: User = Depends(get_current_user)
# Role guard example:
def require_role(*roles):
    def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return checker
```

**Endpoint Summary**:

| Method | Path | Roles Permitted | Description |
|--------|------|-----------------|-------------|
| POST | `/auth/signup` | All (public) | Register new user with role |
| POST | `/auth/login` | All (public) | Authenticate, return JWT |
| POST | `/sessions` | ME, SME | Create fault session |
| POST | `/sessions/{id}/chat` | ME, SME | Send message, get AI response |
| POST | `/sessions/{id}/measurements` | ME, SME | Record measurement |
| POST | `/sessions/{id}/report` | ME, SME | Generate fault report |
| POST | `/sessions/{id}/escalate` | ME | Escalate to SME |
| POST | `/sessions/{id}/expert-note` | SME | Add expert annotation |
| POST | `/sessions/{id}/flag-knowledge-gap` | SME | Flag for KE review |
| GET | `/sessions/{id}` | ME (own), SME, SUP, ADM | Get session detail |
| GET | `/dashboard` | ME, SME, SUP, KE | Get session list (role-filtered) |
| GET | `/dashboard/stats` | ME, SME, SUP, KE | Get aggregate statistics |
| GET | `/dashboard/crane-history` | ME, SME, SUP, KE | Get all sessions by crane |
| GET | `/reports/{id}` | All authenticated | Get report detail |
| GET | `/knowledge-gaps` | KE, SME | Get knowledge gap records (optional `?include_resolved`) |
| PUT | `/knowledge-gaps/{id}/resolve` | KE | Update KB file, re-index, transition session, create notifications |
| GET | `/notifications` | All authenticated | Get own notifications (optional `?unread_only`) |
| GET | `/notifications/unread-count` | All authenticated | Get count of unread notifications |
| PUT | `/notifications/{id}/read` | All authenticated | Mark a notification as read |
| PUT | `/notifications/read-all` | All authenticated | Mark all notifications as read |
| GET | `/admin/users` | ADM | List all users |
| POST | `/admin/users/{id}/role` | ADM | Update user role |
| PUT | `/admin/users/{id}/deactivate` | ADM | Deactivate user account |
| GET | `/admin/audit-log` | ADM, SUP | Access audit trail |

---

### Layer 3: Orchestration Layer

**Technology**: Python modules  
**Path**: `orchestration/session_orchestrator.py`  
**Responsibilities**:
- Receive structured requests from the API layer
- Determine the agent invocation pipeline based on request type and session state
- Assemble context packages and pass them between agents
- Write consolidated results to the data layer
- Emit audit log events

The Orchestrator is the only component that accesses the database directly during an agent pipeline run. Agents receive all necessary data as function arguments and do not perform database I/O themselves.

```python
class SessionOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.intake_agent = IntakeAgent()
        self.retrieval_agent = RetrievalAgent()
        self.diagnostic_agent = DiagnosticReasoningAgent()
        self.parameter_agent = ParameterInterpretationAgent()
        self.procedure_agent = ProcedureGuidanceAgent()
        self.safety_agent = SafetyGuardrailAgent()
        self.report_agent = ReportGenerationAgent()
        self.knowledge_agent = KnowledgeFeedbackAgent()

    def handle_session_start(self, intake_data, user) -> OrchestratorResult: ...
    def handle_chat_turn(self, session_id, message, user) -> OrchestratorResult: ...
    def handle_report_request(self, session_id, user) -> OrchestratorResult: ...
    def handle_escalation(self, session_id, reason, user) -> OrchestratorResult: ...
```

---

### Layer 4: Data Layer

**Technology**: SQLite via SQLAlchemy ORM, ChromaDB (vector store)  
**Path**: `backend/database.py`, `backend/models.py`, `chroma_db/`

#### Relational Database Schema (SQLite)

**Table: users**
```
id (PK), username (UNIQUE), name, hashed_password, role, is_active,
created_at, last_login_at
```

**Table: troubleshooting_sessions**
```
id (PK), user_id (FK→users), crane_type, component, problem_description,
environment, recent_changes, error_codes, lifecycle_state, completed_steps (JSON),
likely_causes (JSON), current_hypothesis, escalated_to (FK→users, nullable),
escalation_reason, escalation_at, created_at, updated_at, agent_metadata (JSON)
```

**Table: messages**
```
id (PK), session_id (FK→sessions), role (user|assistant), content, created_at
```

**Table: measurements**
```
id (PK), session_id (FK→sessions), voltage_v, current_a, temperature_c,
load_kg, brake_gap_mm, insulation_resistance_mohm, vibration_mm_s_rms,
notes, created_at
```

**Table: reports**
```
id (PK), session_id (FK→sessions), crane_type, component, issue_summary,
steps_taken (JSON), root_cause, diagnosis, recommendations (JSON), severity,
follow_up_required, generated_by (FK→users), generated_at, agent_version
```

**Table: expert_annotations**
```
id (PK), session_id (FK→sessions), user_id (FK→users), annotation_text,
annotation_type (expert_note|cause_validation|procedure_correction), created_at
```

**Table: knowledge_gaps**
```
id (PK), component_key, fault_pattern, gap_type, supporting_sessions (JSON),
suggested_action, created_at, status (open|in_review|resolved), resolved_by (FK→users),
detected_by (str), missing_information (text), affected_asset_type (str),
suggested_file_to_update (str), suggested_section_or_node (str),
evidence_checked (JSON list), confidence (float),
resolution_note (text), knowledge_content_added (text)
```

**Table: notifications**
```
id (PK), user_id (FK→users), gap_id (FK→knowledge_gaps, nullable),
session_id (FK→sessions, nullable), message (text), is_read (bool), created_at
```

**Table: state_transitions**
```
id (PK), session_id (FK→sessions), previous_state, new_state, transitioned_by (FK→users),
reason, transitioned_at
```

**Table: audit_log**
```
id (PK), event_type, user_id (FK→users), resource_type, resource_id, details (JSON),
ip_address, created_at
```

#### Vector Store (ChromaDB)

- Collection: `crane_knowledge`
- Embedding model: `all-MiniLM-L6-v2`
- Metadata per chunk: `source` (component file), `chunk_id`, `document_id`
- Persistence: `./chroma_db/`
- Re-indexed from `data/knowledge_base/` on first startup or when `chroma_db/` is deleted

---

## 4. Multi-Agent Interaction Model

The following describes the data flow for a complete chat turn:

```
[Engineer sends message via frontend]
          │
          ▼
[API Layer: POST /sessions/{id}/chat]
   ← JWT validated, role checked (ME or SME only)
          │
          ▼
[SessionOrchestrator.handle_chat_turn()]
          │
    ┌─────▼──────────────────────────────────────────────────────────────┐
    │  Step 1: Load session snapshot from DB                             │
    │          messages, measurements, state fields, component_key       │
    └─────┬──────────────────────────────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────────────────────────────┐
    │  Step 2: RetrievalAgent.retrieve(component_key, query)             │
    │          → evidence_chunks (up to 5 ranked chunks)                 │
    └─────┬──────────────────────────────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────────────────────────────┐
    │  Step 3: ParameterInterpretationAgent.annotate(measurements)       │
    │          (only if new measurements since last turn)                │
    │          → annotated_measurements                                  │
    └─────┬──────────────────────────────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────────────────────────────┐
    │  Step 4: Orchestrator assembles system_prompt                      │
    │          context_snapshot + evidence + annotations + state         │
    └─────┬──────────────────────────────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────────────────────────────┐
    │  Step 5: DiagnosticReasoningAgent.respond(system_prompt, history)  │
    │          → response_text + session_update (JSON embedded)          │
    └─────┬──────────────────────────────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────────────────────────────┐
    │  Step 6: SafetyGuardrailAgent.evaluate(response_text)             │
    │          → safety_flag, modified_response                         │
    └─────┬──────────────────────────────────────────────────────────────┘
          │
    ┌─────▼──────────────────────────────────────────────────────────────┐
    │  Step 7: Orchestrator writes to DB                                 │
    │          - persist message (user + assistant)                      │
    │          - update session state fields from session_update         │
    │          - persist evidence_chunks                                 │
    │          - write audit log event                                   │
    └─────┬──────────────────────────────────────────────────────────────┘
          │
          ▼
[Return to API Layer → JSON response to frontend]
   { ai_response, safety_flag, evidence_chunks, session_state }
```

---

## 5. Role-Based Access Control Architecture

### 5.1 Role Hierarchy

```
ADM (System Administrator)
 └── SUP (Supervisor / Maintenance Manager)
      ├── SME (Senior Maintenance Engineer)
      │    └── ME (Maintenance Engineer)
      └── KE (Knowledge Engineer)
```

Note: The hierarchy represents organisational authority, not permission inheritance. Permissions are defined explicitly per role in the access control matrix (see REQUIREMENTS.md §7).

### 5.2 RBAC Implementation

**Token Payload**:
```json
{
  "sub": "username",
  "user_id": 42,
  "role": "ME",
  "exp": 1720000000
}
```

**Backend Enforcement** (`access_control/permissions.py`):
```python
ROLE_PERMISSIONS = {
    "ME": [
        "session:create", "session:read:own", "session:chat:own",
        "session:measure", "session:escalate", "session:report:own",
        "report:read:any", "dashboard:own", "crane_history:read"
    ],
    "SME": [
        "session:create", "session:read:own", "session:read:escalated",
        "session:chat:own", "session:chat:escalated", "session:measure",
        "session:report:own", "session:report:escalated",
        "session:annotate", "session:validate_cause",
        "session:flag_knowledge_gap", "report:read:any",
        "dashboard:own", "dashboard:all", "crane_history:read",
        "knowledge_gap:read"
    ],
    "KE": [
        "report:read:any", "dashboard:stats", "crane_history:read",
        "knowledge_gap:read", "knowledge_base:edit"
    ],
    "SUP": [
        "session:read:all", "report:read:any", "dashboard:all",
        "dashboard:stats", "crane_history:read", "audit_log:read"
    ],
    "ADM": [
        "user:create", "user:read", "user:deactivate", "role:assign",
        "system:configure", "audit_log:read", "report:read:any",
        "dashboard:all"
    ]
}
```

**Frontend Enforcement** (UX only, not security):
- Navigation items rendered conditionally based on `user.role`
- Action buttons rendered conditionally per role
- Role badge displayed in navigation bar

---

## 6. Authentication and Role-Aware UI Architecture

### 6.1 Login Flow

```
1. User submits login form (username + password)
2. Frontend: POST /auth/login
3. Backend: verify bcrypt hash, generate JWT (includes role)
4. Frontend: store token + user object in st.session_state
5. Frontend: navigate to role-appropriate dashboard screen
   - ME → dashboard screen (own sessions tab active)
   - SME → dashboard screen (escalated tab visible)
   - KE → dashboard screen (knowledge gaps tab visible)
   - SUP → dashboard screen (all sessions overview)
   - ADM → admin screen
```

### 6.2 Signup Flow

```
1. User submits signup form (name, username, password, role)
2. Frontend: POST /auth/signup
3. Backend: validate uniqueness, hash password, create user record, issue JWT
4. Frontend: same flow as login from step 4
```

### 6.3 Session State Structure (Streamlit)

```python
st.session_state = {
    "token": "JWT string",
    "user": {
        "id": int,
        "username": str,
        "name": str,
        "role": "ME | SME | KE | SUP | ADM"
    },
    "screen": "login | intake | guidance | dashboard | admin",
    "active_session_id": int | None,
    "active_session_data": { ... } | None
}
```

---

## 7. Fault Lifecycle Handling

### 7.1 State Transition Logic

State transitions are managed exclusively by the Orchestrator and written to the `state_transitions` table. The frontend cannot directly set a lifecycle state; it can only trigger actions (escalate, generate report) that cause the Orchestrator to transition states.

```python
ALLOWED_TRANSITIONS = {
    "LOGGED":                    ["IN_PROGRESS"],
    "IN_PROGRESS":               ["AWAITING_MEASUREMENT", "PROBABLE_CAUSE_IDENTIFIED", "UNRESOLVED"],
    "AWAITING_MEASUREMENT":      ["IN_PROGRESS"],
    "PROBABLE_CAUSE_IDENTIFIED": ["RESOLVED", "UNRESOLVED"],
    "UNRESOLVED":                ["ESCALATED", "IN_PROGRESS"],
    "ESCALATED":                 ["SME_IN_REVIEW"],
    "SME_IN_REVIEW":             ["RESOLVED", "KNOWLEDGE_GAP_FLAGGED"],
    "KNOWLEDGE_GAP_FLAGGED":     ["SME_IN_REVIEW", "IN_PROGRESS"],
    "RESOLVED":                  ["CLOSED_WITH_REPORT"],
    "CLOSED_WITH_REPORT":        []  # terminal state
}

TRANSITION_ROLE_PERMISSIONS = {
    ("LOGGED", "IN_PROGRESS"):                     ["ME", "SME"],
    ("IN_PROGRESS", "AWAITING_MEASUREMENT"):        ["ME", "SME"],
    ("IN_PROGRESS", "PROBABLE_CAUSE_IDENTIFIED"):   ["ME", "SME"],  # AI-suggested
    ("IN_PROGRESS", "UNRESOLVED"):                  ["ME", "SME"],
    ("UNRESOLVED", "ESCALATED"):                    ["ME"],
    ("ESCALATED", "SME_IN_REVIEW"):                 ["SME"],
    ("SME_IN_REVIEW", "RESOLVED"):                  ["SME"],
    ("SME_IN_REVIEW", "KNOWLEDGE_GAP_FLAGGED"):     ["SME"],
    ("KNOWLEDGE_GAP_FLAGGED", "IN_PROGRESS"):       ["KE"],   # after KB update via resolve endpoint
    ("RESOLVED", "CLOSED_WITH_REPORT"):             ["ME", "SME"],
}
```

### 7.2 AI-Triggered State Suggestions

The Diagnostic Reasoning Agent may suggest state transitions via the `session_update` payload:
- `probable_cause_flag: true` → Orchestrator recommends transitioning to PROBABLE_CAUSE_IDENTIFIED (engineer confirms)
- `unresolved_flag: true` → Orchestrator recommends transitioning to UNRESOLVED (engineer confirms)
- `safety_concern_flag: true` → Safety Agent is invoked; session flagged with safety alert

The engineer always confirms AI-suggested transitions; they are never automatic.

---

## 8. Crane Dashboard and Report Storage

### 8.1 Dashboard Architecture

The dashboard is a read-focused view that aggregates session and report data. It is served by dedicated dashboard endpoints that apply role-based filtering at the database query level.

```
GET /dashboard?role_filter=own|all|escalated&crane=X&component=Y&status=Z&severity=W
```

Role-based query filtering:
- ME: `WHERE user_id = current_user.id`
- SME: `WHERE user_id = current_user.id OR lifecycle_state IN ('ESCALATED', 'SME_IN_REVIEW')`
- SUP: no user filter (all sessions)
- KE: `WHERE lifecycle_state = 'KNOWLEDGE_GAP_FLAGGED'` (knowledge gaps view)
- ADM: no filter (all sessions)

### 8.2 Crane History View

The crane history view is a cross-engineer view of all past sessions and reports for a selected crane type. It is accessible to ME, SME, KE, and SUP roles.

```
GET /dashboard/crane-history?crane_type=Demag+EKKE+5t
```

Returns all CLOSED_WITH_REPORT sessions for the crane, with embedded report data. This enables engineers to review prior diagnoses before starting a new session on the same crane.

### 8.3 Report Visibility

All generated fault reports are readable by any authenticated user. Reports are stored in the `reports` table and linked to sessions. They are accessible via:
- Dashboard session row expansion
- `GET /reports/{id}` endpoint
- Crane history view

---

## 9. RAG Subsystem Architecture

```
Knowledge Base (.txt files in data/knowledge_base/)
          │
          ▼ (on startup or after chroma_db/ deletion)
┌──────────────────────────────────────────────────┐
│           Indexing Pipeline                      │
│  1. Read and chunk each .txt document            │
│  2. Embed chunks with all-MiniLM-L6-v2           │
│  3. Store in ChromaDB with source metadata       │
└──────────────────────────────────────────────────┘
          │
          ▼ (persisted at ./chroma_db/)
┌──────────────────────────────────────────────────┐
│           ChromaDB Vector Store                  │
│  Collection: crane_knowledge                     │
│  ~120 chunks from 9 component documents          │
│                                                  │
│  RAGSystem.initialize()    — idempotent load     │
│  RAGSystem.reinitialize()  — delete + re-index   │
│    (called automatically by resolve endpoint     │
│     after KE updates a knowledge file)           │
└──────────────────────────────────────────────────┘
          │
          ▼ (at query time: AGT-03 Retrieval Agent)
┌──────────────────────────────────────────────────┐
│           Retrieval Pipeline (per turn)          │
│  Query 1: component-filtered (where source=X)    │
│           → top 3 chunks by cosine similarity    │
│  Query 2: general (no filter)                    │
│           → top 2 chunks by cosine similarity    │
│  Deduplication → up to 5 final chunks            │
│  Ranked by similarity score (descending)         │
└──────────────────────────────────────────────────┘
          │
          ▼
Injected into DiagnosticReasoningAgent system prompt
Stored as evidence records linked to session + turn
Displayed in Evidence panel in the UI
```

**Component–File Mapping** (`backend/rag_system.py`):
```
hoist_motor      → data/knowledge_base/hoist_motor.txt
hoist_brake      → data/knowledge_base/hoist_brake.txt
wire_rope        → data/knowledge_base/wire_rope.txt
gearbox          → data/knowledge_base/gearbox.txt
control_system   → data/knowledge_base/control_system.txt
limit_switch     → data/knowledge_base/limit_switch.txt
trolley_motor    → data/knowledge_base/trolley_bridge_motor.txt
hook_block       → data/knowledge_base/hook_block.txt
power_supply     → data/knowledge_base/power_supply.txt
```

---

## 10. Report Generation Subsystem

```
Engineer requests report
          │
          ▼
Orchestrator loads full session data
          │
          ▼
ParameterInterpretationAgent annotates all measurements
          │
          ▼
ReportGenerationAgent constructs structured prompt:
  - Role: report synthesis agent
  - Input: full transcript, annotations, session state, expert notes
  - Output schema: strict JSON with 7 required fields
          │
          ▼
Anthropic API call (claude-sonnet-4-6)
          │
          ▼
JSON parse → validate schema
          │ (if parse fails: fallback extractor)
          ▼
Store report record in database (reports table)
Link to: session_id, generating user, crane, component, timestamp
          │
          ▼
Transition session state → CLOSED_WITH_REPORT
Invoke KnowledgeFeedbackAgent to check for gaps
          │
          ▼
Return report to frontend → display in dashboard
```

---

## 11. Proposed Folder Structure (Version 2)

```
Process Guidance /
├── agents/
│   ├── __init__.py
│   ├── base_agent.py              # Abstract base class for all agents
│   ├── intake_agent.py            # AGT-02
│   ├── retrieval_agent.py         # AGT-03
│   ├── diagnostic_agent.py        # AGT-04
│   ├── parameter_agent.py         # AGT-05
│   ├── procedure_agent.py         # AGT-06
│   ├── safety_agent.py            # AGT-07
│   ├── report_agent.py            # AGT-08
│   └── knowledge_feedback_agent.py # AGT-09
├── orchestration/
│   ├── __init__.py
│   ├── session_orchestrator.py    # AGT-01: central coordinator
│   └── agent_registry.py         # maps agent IDs to instances
├── access_control/
│   ├── __init__.py
│   ├── roles.py                   # Role enum definitions
│   ├── permissions.py             # ROLE_PERMISSIONS dict
│   └── rbac.py                    # require_role() dependency factory
├── auth/
│   ├── __init__.py
│   └── auth.py                    # bcrypt, JWT create/decode, user CRUD
├── session/
│   ├── __init__.py
│   ├── session_manager.py         # session CRUD, state transition logic
│   └── fault_lifecycle.py         # ALLOWED_TRANSITIONS, TRANSITION_ROLE_PERMISSIONS
├── knowledge/
│   ├── __init__.py
│   ├── rag_system.py              # ChromaDB indexing and retrieval
│   └── parameter_specs.py         # Component parameter reference ranges
├── reporting/
│   ├── __init__.py
│   └── report_generator.py        # Delegates to AGT-08
├── workflows/
│   ├── __init__.py
│   ├── escalation_workflow.py     # Escalation state management
│   └── knowledge_gap_workflow.py  # Knowledge gap creation and management
├── backend/
│   ├── __init__.py
│   ├── database.py                # SQLAlchemy engine, SessionLocal
│   ├── models.py                  # Extended ORM models (v2 schema)
│   ├── schemas.py                 # Pydantic v2 request/response schemas
│   └── main.py                    # FastAPI app, all endpoints
├── frontend/
│   └── app.py                     # Streamlit role-aware UI
├── data/
│   └── knowledge_base/            # Component .txt documents
├── diagrams/                      # PlantUML source files
├── chroma_db/                     # Auto-created vector store
├── crane_ai.db                    # Auto-created SQLite database
├── .env                           # Local secrets (not committed)
├── .env.example
├── requirements.txt
├── start.sh
├── CLAUDE.md
├── REQUIREMENTS.md
├── AGENTS.md
├── ARCHITECTURE.md
├── UML_DIAGRAMS.md
└── USE_CASES.md
```

---

## 12. Deployment Assumptions

| Assumption | Detail |
|------------|--------|
| Single-node deployment | Backend and frontend run on the same machine or local network. No load balancing required for prototype. |
| Local network access | Engineers access the tool via browser on the same local network as the server (e.g., workshop LAN). |
| Anthropic API reachability | The server must have outbound HTTPS access to `api.anthropic.com`. |
| SQLite concurrency | SQLite supports limited concurrent writes. For production multi-user deployment, migrate to PostgreSQL by changing `DATABASE_URL`. |
| ChromaDB persistence | The `chroma_db/` directory must persist across server restarts. Deletion triggers full re-indexing on next startup. |
| Environment secrets | `ANTHROPIC_API_KEY` and `SECRET_KEY` are loaded from `.env` via `python-dotenv`. These must never be committed to version control. |

---

## 13. Risks and Future Extensions

### Known Risks

| Risk | Mitigation |
|------|------------|
| LLM hallucination producing incorrect diagnostic guidance | All AI responses are grounded in retrieved manual chunks. Safety Agent validates outputs. Reports include traceability to source. |
| SQLite write contention under concurrent access | Acceptable for prototype (1–5 concurrent users). PostgreSQL migration path documented. |
| ChromaDB retrieval returning irrelevant chunks for novel fault types | Knowledge Feedback Agent detects low-confidence retrievals and flags for KE review. |
| JWT token compromise | Short 8-hour expiry. Secret key loaded from environment. HTTPS required in production. |
| Safety Agent false negatives | Safety rule set is static. Requires expert review and extension as new fault types are encountered. |

### Future Extensions

| Extension | Description |
|-----------|-------------|
| Streaming AI responses | Implement server-sent events for token-by-token response delivery to improve perceived latency. |
| Knowledge base file upload | Allow Knowledge Engineers to upload new manual documents via the UI, triggering automatic re-indexing. |
| PDF report export | Generate PDF versions of fault reports from the dashboard. |
| Multi-tenant isolation | Namespace database and vector store by organisation for multi-customer deployments. |
| PostgreSQL migration | Replace SQLite with PostgreSQL for production load handling. |
| Offline mode | Cache knowledge base embeddings locally to support operation without Anthropic API access. |
| Integration with CMMS | Export fault reports to external maintenance management systems via REST webhook. |
| Enhanced Safety Agent | Replace static safety rules with a trained classifier for safety-critical condition detection. |
