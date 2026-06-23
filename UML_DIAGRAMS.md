# UML_DIAGRAMS.md
# UML Diagram Reference — AI-Assisted Process Guidance Tool (Version 2)
# Master Thesis, RPTU / Fraunhofer IESE, 2025

This file provides descriptions, file references, and usage notes for all UML diagrams
associated with the system architecture. The actual PlantUML source files are located in
the `diagrams/` directory and can be rendered with PlantUML locally or via VS Code with
the PlantUML extension.

---

## Diagram Index

| File | Diagram Type | Purpose |
|------|-------------|---------|
| `diagrams/system_context.puml` | Context Diagram | Shows the system boundary and external actors |
| `diagrams/use_case.puml` | Use Case Diagram | All use cases grouped by actor and functional area |
| `diagrams/component_view.puml` | Component Diagram | Internal component structure and dependencies |
| `diagrams/sequence_troubleshooting_escalation.puml` | Sequence Diagram | Full chat-turn-to-escalation flow |
| `diagrams/activity_login_and_guidance.puml` | Activity Diagram | Login + intake + guided session + escalation workflow |
| `diagrams/fault_lifecycle_state.puml` | State Machine Diagram | Fault session lifecycle transitions with role labels |
| `diagrams/class_model.puml` | Class Diagram | Domain model with key entities and associations |

---

## 1. System Context Diagram

**File**: `diagrams/system_context.puml`

**Purpose**: Provides a high-level view of the system boundary. Shows which external actors interact with the system and what flows cross the system boundary. Useful for understanding the deployment context and integration points.

**Key elements**:
- The AI-Assisted Process Guidance Tool as the central system
- Human actors: Maintenance Engineer, SME, Knowledge Engineer, Supervisor, System Administrator
- External systems: Anthropic API (LLM), ChromaDB (vector store), SQLite (persistence)
- Data flows: engineer inputs, AI responses, knowledge retrieval, audit records

---

## 2. Use Case Diagram

**File**: `diagrams/use_case.puml`

**Purpose**: Provides a complete overview of all 21 use cases and which actors can perform them. Grouped by functional area. Useful for stakeholder communication and scope confirmation.

**Functional groupings**:
- Authentication and User Management
- Fault Intake and Session Management
- AI-Guided Diagnostic Workflow
- Escalation and Expert Review
- Knowledge Management
- Dashboard and Reporting
- System Administration

---

## 3. Component Diagram

**File**: `diagrams/component_view.puml`

**Purpose**: Shows the internal component structure of the backend, the multi-agent pipeline, and the frontend. Illustrates the interfaces between components and the data layer. Useful for implementation planning and code review.

**Key components**:
- Streamlit Frontend
- FastAPI Backend (API Layer, Auth Middleware, RBAC Guards)
- Session Orchestrator
- All nine AI Agents (AGT-02 through AGT-09)
- RAG System (ChromaDB + sentence-transformers)
- SQLite Database
- Anthropic API connection

---

## 4. Sequence Diagram: Troubleshooting Session with Escalation

**File**: `diagrams/sequence_troubleshooting_escalation.puml`

**Purpose**: Detailed end-to-end sequence showing the exact order of operations from the engineer submitting a chat message, through the multi-agent pipeline, to the response being displayed. Includes the escalation path where the session is handed to an SME. Useful for understanding the runtime behaviour of the system.

**Key scenarios shown**:
1. Engineer submits message
2. Orchestrator invokes Retrieval Agent → returns evidence
3. Parameter Interpretation Agent annotates measurements (if any)
4. Diagnostic Reasoning Agent generates response + session_update
5. Safety Agent evaluates and optionally flags
6. Orchestrator writes state to DB
7. Response returned to frontend
8. Engineer escalates → SME picks up and continues

---

## 5. Activity Diagram: Login, Intake, Guided Troubleshooting, and Escalation

**File**: `diagrams/activity_login_and_guidance.puml`

**Purpose**: Shows the complete workflow as a flow of activities, including decision points, parallel paths, and role-based branching. Covers the full engineer journey from login to session closure or escalation. Useful for process documentation and thesis narrative.

**Activities covered**:
- User arrives at login screen
- Login or signup path
- Role-based dashboard routing
- New fault intake
- Iterative diagnostic conversation loop
- Measurement recording (parallel activity)
- Escalation branch
- Report generation and session closure

---

## 6. State Machine Diagram: Fault Lifecycle

**File**: `diagrams/fault_lifecycle_state.puml`

**Purpose**: Formal state machine showing all states in the fault session lifecycle, all valid transitions, the triggering role for each transition, and the terminal state. Useful for implementation of the state transition validator and for thesis documentation.

**States**: LOGGED, IN_PROGRESS, AWAITING_MEASUREMENT, PROBABLE_CAUSE_IDENTIFIED, UNRESOLVED, ESCALATED, SME_IN_REVIEW, KNOWLEDGE_GAP_FLAGGED, RESOLVED, CLOSED_WITH_REPORT

---

## 7. Class Diagram: Domain Model

**File**: `diagrams/class_model.puml`

**Purpose**: Shows the key domain entities, their attributes, methods, and relationships. Corresponds to the SQLAlchemy ORM models in `backend/models.py`. Useful for database design validation and for understanding the data model.

**Entities**: User, Role, TroubleshootingSession, Message, Measurement, Report, ExpertAnnotation, KnowledgeGap, StateTransition, AuditLogEntry, Crane, Component

---

## Rendering Instructions

### Option 1: VS Code PlantUML Extension
1. Install the "PlantUML" extension by `jebbs` in VS Code.
2. Set the PlantUML server in settings: `"plantuml.server": "https://www.plantuml.com/plantuml"` or install PlantUML locally.
3. Open any `.puml` file and press `Alt+D` to preview.

### Option 2: Local PlantUML JAR
```bash
# Install Java if needed
# Download plantuml.jar from https://plantuml.com/download

java -jar plantuml.jar diagrams/*.puml
# Generates PNG files alongside each .puml file
```

### Option 3: Online Rendering
Paste the content of any `.puml` file into: https://www.plantuml.com/plantuml/uml/

---

## PlantUML Inline Source

The PlantUML source for all diagrams is reproduced below for convenience and LaTeX inclusion.

---

### Diagram 1: System Context

```plantuml
@startuml system_context
!pragma layout smetana

title AI-Assisted Process Guidance Tool — System Context

skinparam rectangle {
  BackgroundColor #F5F5F5
  BorderColor #444444
}
skinparam actor {
  BackgroundColor #DDEEFF
  BorderColor #2255AA
}
skinparam database {
  BackgroundColor #FFF5DD
  BorderColor #AA8800
}
skinparam cloud {
  BackgroundColor #EEFFEE
  BorderColor #227722
}

actor "Maintenance\nEngineer" as ME
actor "Senior Engineer\n/ SME" as SME
actor "Knowledge\nEngineer" as KE
actor "Supervisor" as SUP
actor "System\nAdministrator" as ADM

rectangle "AI-Assisted Process\nGuidance Tool" as SYSTEM {
  rectangle "Streamlit\nFrontend" as FE
  rectangle "FastAPI\nBackend" as BE
  rectangle "Multi-Agent\nOrchestration" as MA
}

database "SQLite\nDatabase" as DB
database "ChromaDB\nVector Store" as CDB
cloud "Anthropic\nAPI" as ANTHRO

ME --> FE : diagnose fault,\nrecord measurements
SME --> FE : review escalated\nsessions
KE --> FE : review knowledge gaps
SUP --> FE : monitor faults,\nview reports
ADM --> FE : manage users,\nassign roles

FE --> BE : REST / HTTP
BE --> MA : invokes agent pipeline
MA --> CDB : retrieve knowledge chunks
MA --> ANTHRO : LLM API calls
BE --> DB : read / write sessions,\nreports, users

@enduml
```

---

### Diagram 2: Use Case Diagram

```plantuml
@startuml use_case
title AI-Assisted Process Guidance Tool — Use Cases

left to right direction

skinparam usecase {
  BackgroundColor #EEEEFF
  BorderColor #333399
}

actor "Maintenance\nEngineer" as ME
actor "Senior Engineer\n/ SME" as SME
actor "Knowledge\nEngineer" as KE
actor "Supervisor" as SUP
actor "System\nAdministrator" as ADM

rectangle "Authentication" {
  usecase "Sign Up" as UC01
  usecase "Log In" as UC02
  usecase "Log Out" as UC03
}

rectangle "Fault Diagnosis Workflow" {
  usecase "Log Fault Issue" as UC04
  usecase "Conduct Diagnostic\nConversation" as UC06
  usecase "Record Measurements" as UC07
  usecase "Review Retrieved\nEvidence" as UC08
  usecase "Generate Fault Report" as UC13
  usecase "Resume Active Session" as UC17
}

rectangle "Escalation & Expert Review" {
  usecase "Escalate to SME" as UC09
  usecase "Expert Review by SME" as UC10
  usecase "Add Expert Annotation" as UC11
  usecase "Flag Knowledge Gap" as UC12
}

rectangle "Dashboard & Knowledge Reuse" {
  usecase "View Own Sessions" as UC14
  usecase "View All Sessions" as UC15
  usecase "View Escalated Sessions" as UC16
  usecase "Review Crane History" as UC18
  usecase "View Knowledge Gaps" as UC19
}

rectangle "System Administration" {
  usecase "Manage Users & Roles" as UC20
  usecase "View Audit Log" as UC21
}

ME --> UC01
ME --> UC02
ME --> UC03
ME --> UC04
ME --> UC06
ME --> UC07
ME --> UC08
ME --> UC09
ME --> UC13
ME --> UC14
ME --> UC17
ME --> UC18

SME --> UC01
SME --> UC02
SME --> UC04
SME --> UC06
SME --> UC07
SME --> UC08
SME --> UC10
SME --> UC11
SME --> UC12
SME --> UC13
SME --> UC14
SME --> UC15
SME --> UC16
SME --> UC18
SME --> UC19

KE --> UC01
KE --> UC02
KE --> UC18
KE --> UC19

SUP --> UC01
SUP --> UC02
SUP --> UC15
SUP --> UC16
SUP --> UC18
SUP --> UC21

ADM --> UC01
ADM --> UC02
ADM --> UC20
ADM --> UC21

@enduml
```

---

### Diagram 3: Component Diagram

```plantuml
@startuml component_view
title AI-Assisted Process Guidance Tool — Component View

skinparam component {
  BackgroundColor #F0F0FF
  BorderColor #333366
}
skinparam database {
  BackgroundColor #FFFACC
  BorderColor #887700
}
skinparam cloud {
  BackgroundColor #E8FFE8
  BorderColor #226622
}
skinparam package {
  BackgroundColor #FAFAFA
  BorderColor #AAAAAA
}

package "Frontend Tier" {
  [Streamlit App\n(app.py)] as FE
  note right of FE : Role-aware UI\nScreen routing\nJWT session state
}

package "Backend Tier" {
  [FastAPI App\n(main.py)] as API
  [Auth Middleware\n(auth.py)] as AUTH
  [RBAC Guards\n(access_control/)] as RBAC

  package "Orchestration Layer" {
    [Session Orchestrator\n(AGT-01)] as ORCH
  }

  package "Agent Layer" {
    [Intake Agent\n(AGT-02)] as A02
    [Retrieval Agent\n(AGT-03)] as A03
    [Diagnostic Agent\n(AGT-04)] as A04
    [Parameter Agent\n(AGT-05)] as A05
    [Procedure Agent\n(AGT-06)] as A06
    [Safety Agent\n(AGT-07)] as A07
    [Report Agent\n(AGT-08)] as A08
    [Knowledge Feedback\n(AGT-09)] as A09
  }

  package "Session & Lifecycle Layer" {
    [Session Manager] as SM
    [Fault Lifecycle\nController] as FLC
  }
}

database "SQLite\n(crane_ai.db)" as DB
database "ChromaDB\n(chroma_db/)" as CDB
cloud "Anthropic API\n(claude-sonnet-4-6)" as ANTHRO
[Knowledge Base\n(.txt documents)] as KB

FE --> API : HTTP REST
API --> AUTH : validate JWT
API --> RBAC : check permissions
API --> ORCH : route request
ORCH --> A02 : validate intake
ORCH --> A03 : retrieve evidence
ORCH --> A04 : generate response
ORCH --> A05 : annotate measurements
ORCH --> A06 : get procedure steps
ORCH --> A07 : safety check
ORCH --> A08 : generate report
ORCH --> A09 : detect knowledge gaps
ORCH --> SM : read/write session
SM --> DB : ORM queries
SM --> FLC : state transitions
A03 --> CDB : vector search
A04 --> ANTHRO : LLM API
A08 --> ANTHRO : LLM API
A03 ..> KB : indexed into CDB

@enduml
```

---

### Diagram 4: Sequence Diagram — Troubleshooting Session with Escalation

```plantuml
@startuml sequence_troubleshooting_escalation
title Diagnostic Chat Turn → Escalation Sequence

actor "Maintenance\nEngineer" as ME
participant "Streamlit\nFrontend" as FE
participant "FastAPI\nBackend" as API
participant "Session\nOrchestrator" as ORCH
participant "Retrieval\nAgent" as RA
participant "Parameter\nAgent" as PA
participant "Diagnostic\nAgent" as DA
participant "Safety\nAgent" as SA
database "SQLite DB" as DB
participant "Anthropic\nAPI" as ANTHRO
actor "SME" as SME

== Chat Turn ==

ME -> FE : enters observation,\nclicks Send
FE -> API : POST /sessions/{id}/chat\n{message, token}
API -> API : validate JWT, check role (ME/SME)
API -> ORCH : handle_chat_turn(session_id, message, user)

ORCH -> DB : load session snapshot\n(messages, state, measurements)
DB --> ORCH : session snapshot

ORCH -> RA : retrieve(component_key, query)
RA -> RA : component-filtered query (top 3)
RA -> RA : general query (top 2)
RA --> ORCH : evidence_chunks (≤5 ranked)

alt new measurements exist
  ORCH -> PA : annotate(measurements, component_key)
  PA --> ORCH : annotated_measurements
end

ORCH -> ORCH : assemble system_prompt\n(context + evidence + annotations + state)

ORCH -> DA : respond(system_prompt, history)
DA -> ANTHRO : messages API call
ANTHRO --> DA : response_text + session_update JSON
DA --> ORCH : {response_text, session_update}

ORCH -> SA : evaluate(response_text)
alt safety condition detected
  SA --> ORCH : {safety_flag: true, safety_message, modified_response}
  note over ORCH : prepend CRITICAL safety alert
else no safety issue
  SA --> ORCH : {safety_flag: false, modified_response: original}
end

ORCH -> DB : persist message (user)
ORCH -> DB : persist message (assistant)
ORCH -> DB : update session state\n(steps, causes, hypothesis)
ORCH -> DB : write audit log event

ORCH --> API : {ai_response, safety_flag, evidence_chunks, session_state}
API --> FE : JSON response
FE -> ME : display response + evidence + state panels

== Escalation Path ==

ME -> FE : clicks "Escalate to SME"
FE -> ME : show escalation reason dialog
ME -> FE : enters escalation note, confirms
FE -> API : POST /sessions/{id}/escalate\n{reason, token}
API -> API : validate JWT, check role == ME
API -> ORCH : handle_escalation(session_id, reason, user)
ORCH -> DB : create escalation record
ORCH -> DB : transition state: UNRESOLVED → ESCALATED
ORCH -> DB : write state_transition record
ORCH -> DB : write audit log event
ORCH --> API : {success, new_state: ESCALATED}
API --> FE : confirmation
FE -> ME : show "Escalated to SME" confirmation

== SME Picks Up Escalated Session ==

SME -> FE : opens "Escalated Sessions" tab
FE -> API : GET /dashboard?filter=escalated\n{SME token}
API --> FE : escalated sessions list
FE -> SME : display session list with escalation notes
SME -> FE : clicks "Open for Review"
FE -> API : POST /sessions/{id}/start-sme-review\n{SME token}
API -> ORCH : handle_sme_review_start(session_id, sme_user)
ORCH -> DB : transition state: ESCALATED → SME_IN_REVIEW
ORCH -> DB : write state_transition record
ORCH --> API : session data (full history + escalation notes)
API --> FE : session restored
FE -> SME : display full session with escalation context

@enduml
```

---

### Diagram 5: Activity Diagram — Login, Intake, Guided Session, Escalation

```plantuml
@startuml activity_login_and_guidance
title Activity Diagram: Login → Intake → Guided Troubleshooting → Escalation

|User|
start
:Open Application;

if (Has Account?) then (yes)
  :Enter Username\nand Password;
  :POST /auth/login;
  if (Credentials Valid?) then (yes)
    :Receive JWT Token;
  else (no)
    :Display Error;
    stop
  endif
else (no)
  :Fill Signup Form\n(name, username,\npassword, role);
  :POST /auth/signup;
  :Receive JWT Token;
endif

|System|
:Decode JWT → extract role;
:Route to role-appropriate\ndashboard;

|User|
if (User Role?) then (ME or SME)
  :View Dashboard\n(own sessions);
  :Click "New Fault";

  |System|
  :Display Fault\nIntake Form;

  |User|
  :Select Crane Type;
  :Select Component;
  :Describe Fault\n(free text);
  :Add optional context\n(environment,\nchanges, error codes);
  :Submit Intake Form;

  |System|
  :Intake Agent validates data;
  :Create TroubleshootingSession\n(state: LOGGED);
  :Invoke Retrieval Agent;
  :Invoke Diagnostic Agent\n(opening message);
  :Safety Agent evaluates;
  :Transition state → IN_PROGRESS;
  :Display AI Guidance Interface;

  |User|
  repeat
    :Read AI response;
    fork
      :Record physical measurement\n(voltage, current, temp…);
      |System|
      :Store measurement record;
      |User|
    fork again
      :Review Evidence panel\n(retrieved knowledge chunks);
    endfork

    :Type observation\nor answer;
    :Submit message;

    |System|
    :Retrieval Agent → fetch evidence;
    :Parameter Agent → annotate measurements;
    :Diagnostic Agent → generate response;
    :Safety Agent → evaluate;
    :Update session state;
    :Return response + evidence;

    |User|
    if (Safety Alert?) then (yes)
      :Read CRITICAL safety warning;
      :Suspend crane operation\nif required;
    endif

  repeat while (Probable cause not identified AND not unresolved?)

  if (Probable Cause Identified?) then (yes)
    |System|
    :Suggest transition →\nPROBABLE_CAUSE_IDENTIFIED;
    |User|
    :Confirm transition;
    :Generate Fault Report;
    |System|
    :Report Agent synthesises\nstructured JSON report;
    :Store report;
    :Transition → CLOSED_WITH_REPORT;
    :Knowledge Feedback Agent\nchecks for gaps;
    |User|
    :View report on dashboard;
    stop

  else (no — unresolved)
    |System|
    :Recommend escalation;
    |User|
    if (Escalate?) then (yes)
      :Click "Escalate to SME";
      :Enter escalation reason;
      |System|
      :Record escalation;
      :Transition → ESCALATED;
      |User|
      :Session handed to SME;

      |SME|
      :View escalated session\non dashboard;
      :Open for Review;
      |System|
      :Transition → SME_IN_REVIEW;
      |SME|
      :Continue diagnostic conversation;
      :Add expert annotations;
      if (Knowledge Gap Found?) then (yes)
        :Flag for Knowledge Review;
        |System|
        :Transition → KNOWLEDGE_GAP_FLAGGED;
        :Create knowledge gap record;
        |KE|
        :Review knowledge gap;
        :Update knowledge base document;
        :Mark gap as resolved;
      else (no)
        |SME|
        :Validate root cause;
        :Transition → RESOLVED;
        :Generate Report;
        |System|
        :Transition → CLOSED_WITH_REPORT;
      endif
      stop

    else (no — close without report)
      :Close session;
      stop
    endif
  endif

else (SUP or KE or ADM)
  :View role-specific dashboard;
  stop
endif

@enduml
```

---

### Diagram 6: State Machine — Fault Lifecycle

```plantuml
@startuml fault_lifecycle_state
title Fault Session Lifecycle — State Machine

skinparam state {
  BackgroundColor #EEF0FF
  BorderColor #333388
  ArrowColor #333388
}
skinparam state<<critical>> {
  BackgroundColor #FFEEEE
  BorderColor #AA2222
}
skinparam state<<terminal>> {
  BackgroundColor #EEFFEE
  BorderColor #227722
}

[*] --> LOGGED : ME/SME submits intake form

LOGGED --> IN_PROGRESS : ME/SME opens session\n[Orchestrator: initial AI message sent]

IN_PROGRESS --> AWAITING_MEASUREMENT : AI requests measurement\n[ME/SME: "Measuring now"]
AWAITING_MEASUREMENT --> IN_PROGRESS : ME/SME records measurement\n[Orchestrator: resumes conversation]

IN_PROGRESS --> PROBABLE_CAUSE_IDENTIFIED : AI signals probable_cause_flag\n[ME/SME confirms]
PROBABLE_CAUSE_IDENTIFIED --> RESOLVED : ME/SME confirms resolution

IN_PROGRESS --> UNRESOLVED : ME/SME: "Cannot resolve"\nOR AI signals unresolved_flag (8+ turns)
PROBABLE_CAUSE_IDENTIFIED --> UNRESOLVED : ME/SME: "Cause unconfirmed"

UNRESOLVED --> ESCALATED : ME escalates\n[enters escalation reason]
UNRESOLVED --> IN_PROGRESS : ME/SME: "Continue diagnosing"

ESCALATED --> SME_IN_REVIEW : SME opens session\n[Orchestrator: restore full context]

SME_IN_REVIEW --> RESOLVED : SME validates root cause
SME_IN_REVIEW --> KNOWLEDGE_GAP_FLAGGED : SME flags knowledge gap\n[KnowledgeFeedbackAgent invoked]

KNOWLEDGE_GAP_FLAGGED --> SME_IN_REVIEW : KE updates knowledge base;\nSME resumes review

RESOLVED --> CLOSED_WITH_REPORT <<terminal>> : ME/SME generates report\n[ReportGenerationAgent]

note right of CLOSED_WITH_REPORT
  Terminal state.
  Report stored.
  Visible on crane history.
  All engineers can read.
end note

state IN_PROGRESS <<critical>> {
  note : Safety Agent evaluates\nevery response.\nCritical flags displayed\nimmediately.
}

@enduml
```

---

### Diagram 7: Class Diagram — Domain Model

```plantuml
@startuml class_model
title Domain Model — Key Entities

skinparam class {
  BackgroundColor #F5F5FF
  BorderColor #333388
  ArrowColor #333388
}

enum Role {
  ME
  SME
  KE
  SUP
  ADM
}

enum FaultLifecycleState {
  LOGGED
  IN_PROGRESS
  AWAITING_MEASUREMENT
  PROBABLE_CAUSE_IDENTIFIED
  UNRESOLVED
  ESCALATED
  SME_IN_REVIEW
  KNOWLEDGE_GAP_FLAGGED
  RESOLVED
  CLOSED_WITH_REPORT
}

enum Severity {
  critical
  high
  medium
  low
}

enum MessageRole {
  user
  assistant
}

class User {
  +id: int
  +username: str
  +name: str
  +hashed_password: str
  +role: Role
  +is_active: bool
  +created_at: datetime
  +last_login_at: datetime
  --
  +check_password(plain: str): bool
  +has_permission(action: str): bool
}

class Crane {
  +id: int
  +crane_type: str
  +components: list[str]
}

class TroubleshootingSession {
  +id: int
  +crane_type: str
  +component: str
  +problem_description: str
  +environment: str
  +recent_changes: str
  +error_codes: str
  +lifecycle_state: FaultLifecycleState
  +completed_steps: list[str]
  +likely_causes: list[str]
  +current_hypothesis: str
  +escalation_reason: str
  +created_at: datetime
  +updated_at: datetime
  +agent_metadata: dict
  --
  +transition_to(new_state, actor): void
  +can_transition(new_state, role): bool
}

class Message {
  +id: int
  +role: MessageRole
  +content: str
  +created_at: datetime
}

class Measurement {
  +id: int
  +voltage_v: float
  +current_a: float
  +temperature_c: float
  +load_kg: float
  +brake_gap_mm: float
  +insulation_resistance_mohm: float
  +vibration_mm_s_rms: float
  +notes: str
  +created_at: datetime
}

class Report {
  +id: int
  +crane_type: str
  +component: str
  +issue_summary: str
  +steps_taken: list[str]
  +root_cause: str
  +diagnosis: str
  +recommendations: list[str]
  +severity: Severity
  +follow_up_required: bool
  +generated_at: datetime
  +agent_version: str
}

class ExpertAnnotation {
  +id: int
  +annotation_text: str
  +annotation_type: str
  +created_at: datetime
}

class EscalationRecord {
  +id: int
  +escalation_reason: str
  +escalated_at: datetime
}

class KnowledgeGap {
  +id: int
  +component_key: str
  +fault_pattern: str
  +gap_type: str
  +supporting_sessions: list[str]
  +suggested_action: str
  +status: str
  +created_at: datetime
}

class StateTransition {
  +id: int
  +previous_state: FaultLifecycleState
  +new_state: FaultLifecycleState
  +reason: str
  +transitioned_at: datetime
}

class AuditLogEntry {
  +id: int
  +event_type: str
  +resource_type: str
  +resource_id: str
  +details: dict
  +ip_address: str
  +created_at: datetime
}

' Associations
User "1" --> "0..*" TroubleshootingSession : creates (user_id)
User "1" --> "0..*" TroubleshootingSession : escalated_to
User "1" --> "0..*" Report : generates
User "1" --> "0..*" ExpertAnnotation : authors
User "1" --> "0..*" StateTransition : triggers
User "1" --> "0..*" AuditLogEntry : actor

TroubleshootingSession "1" --> "0..*" Message : contains
TroubleshootingSession "1" --> "0..*" Measurement : records
TroubleshootingSession "1" --> "0..1" Report : produces
TroubleshootingSession "1" --> "0..*" ExpertAnnotation : has
TroubleshootingSession "1" --> "1" EscalationRecord : may have
TroubleshootingSession "1" --> "0..*" StateTransition : history
TroubleshootingSession "*" --> "1" FaultLifecycleState : current state

User --> Role : assigned
Report --> Severity : classified as

@enduml
```
