# REQUIREMENTS.md
# AI-Assisted Process Guidance Tool — Version 2 (Multi-Agent, Role-Based)
# Master Thesis, RPTU / Fraunhofer IESE, 2025

---

## 1. System Purpose

The AI-Assisted Process Guidance Tool is an industrial advisory system that supports crane maintenance engineers during structured fault diagnosis and troubleshooting. The system combines Retrieval-Augmented Generation (RAG), multi-agent LLM reasoning, and a role-based human workflow to guide engineers from initial fault intake through measurement recording, root cause identification, escalation, and formal report generation.

The system is **advisory-only**. All diagnostic conclusions, escalation decisions, and safety-critical actions remain the responsibility of qualified human personnel. The AI agents provide structured guidance, retrieve relevant technical knowledge, and synthesise findings, but do not issue commands to crane control systems.

---

## 2. Scope

The scope of this prototype covers:

- Role-based user authentication and registration
- Structured fault intake workflow
- AI-guided interactive diagnostic sessions
- Measurement recording and interpretation against known parameter ranges
- Fault lifecycle state management with role-based transitions
- Escalation from Maintenance Engineer to Senior Engineer / SME
- Fault flagging for Knowledge Engineer review
- Fault report generation and persistent storage
- Cross-engineer knowledge reuse via a crane-level history dashboard
- Role-differentiated dashboards and UI panels
- System administration for user and role management

Out of scope for Version 2 prototype:
- Integration with live crane sensor data or SCADA systems
- Automated work order generation in external ERP/CMMS systems
- Real-time streaming AI responses
- Multi-language support
- Native mobile application

---

## 3. Functional Requirements

### 3.1 Authentication and User Management

| ID    | Requirement |
|-------|-------------|
| FR-01 | The system shall provide a login screen accessible to all users before any protected resource is available. |
| FR-02 | The system shall provide a signup form with the following fields: full name, username, password, and role selection. |
| FR-03 | The system shall validate that a username is unique at registration time. |
| FR-04 | The system shall store passwords as bcrypt hashes. No plaintext passwords shall be stored or transmitted. |
| FR-05 | The system shall issue a signed JWT access token upon successful login or signup. The token shall carry the user's ID, username, and assigned role. |
| FR-06 | The JWT token shall expire after 8 hours. |
| FR-07 | The system shall reject API requests that do not carry a valid, unexpired JWT token. |
| FR-08 | The System Administrator shall be able to create, view, update, and deactivate user accounts. |
| FR-09 | The System Administrator shall be able to assign or change the role of any user. |
| FR-10 | The system shall log all authentication events (login, failed login, logout, token expiry) in an audit trail. |

### 3.2 Role-Based Access Control

| ID    | Requirement |
|-------|-------------|
| FR-11 | Each user shall have exactly one assigned role from the defined role hierarchy. |
| FR-12 | The system shall enforce role-based access control on all API endpoints. Requests from users without sufficient role permissions shall receive HTTP 403. |
| FR-13 | The frontend shall render UI elements, navigation options, and available actions based on the authenticated user's role. |
| FR-14 | Roles shall be: Maintenance Engineer, Senior Maintenance Engineer, Knowledge Engineer, Supervisor, System Administrator. |

### 3.3 Fault Intake

| ID    | Requirement |
|-------|-------------|
| FR-15 | The system shall provide a structured fault intake form to Maintenance Engineers and Senior Engineers. |
| FR-16 | The intake form shall include: crane type (dropdown), affected component (dynamic dropdown dependent on crane selection), fault description (free text), optional environmental conditions, optional recent maintenance changes, and optional error codes or warning indicator values. |
| FR-17 | On submission of the intake form, the system shall create a new TroubleshootingSession record and transition it to the LOGGED state. |
| FR-18 | The Intake Agent shall validate intake data completeness and construct a context snapshot passed to the Orchestrator. |

### 3.4 AI-Guided Diagnostic Session

| ID    | Requirement |
|-------|-------------|
| FR-19 | On session creation, the Orchestrator shall invoke the Retrieval Agent and Diagnostic Reasoning Agent to generate an opening diagnostic message without repeating data already provided in the intake form. |
| FR-20 | The engineer shall be able to send free-text messages within the active session and receive AI-generated responses grounded in retrieved technical knowledge. |
| FR-21 | Each conversational turn shall invoke the Retrieval Agent to retrieve up to five relevant knowledge chunks from the ChromaDB vector store. |
| FR-22 | The Diagnostic Reasoning Agent shall embed a structured `session_update` JSON block in each response. The backend shall parse this block and update session state fields: `completed_steps`, `likely_causes`, and `current_hypothesis`. |
| FR-23 | The Safety/Guardrail Agent shall evaluate every AI response before delivery. If a safety-critical condition is detected, the response shall include a prominently displayed safety warning and a recommendation to suspend crane operation. |
| FR-24 | The retrieved evidence chunks shall be displayed in an Evidence panel alongside the chat interface. |
| FR-25 | The current session state (completed steps, likely causes, hypothesis) shall be visible in a dedicated Session State panel. |

### 3.5 Measurement Recording

| ID    | Requirement |
|-------|-------------|
| FR-26 | Engineers shall be able to record physical measurements within an active session. |
| FR-27 | The measurement form shall support the following fields: voltage (V), current (A), temperature (°C), load (kg), brake gap (mm), insulation resistance (MΩ), vibration (mm/s RMS), and a free-text notes field. |
| FR-28 | The Parameter Interpretation Agent shall be invoked on each subsequent conversational turn to interpret recorded measurements against component-specific reference ranges from the knowledge base. |
| FR-29 | Measurements shall be stored persistently and linked to the session. They shall remain visible across session resumption. |

### 3.6 Fault Lifecycle and State Management

| ID    | Requirement |
|-------|-------------|
| FR-30 | Every TroubleshootingSession shall have an explicit lifecycle state drawn from the set defined in Section 6. |
| FR-31 | Only authorised roles shall be permitted to trigger specific state transitions, as defined in Section 6. |
| FR-32 | State transitions shall be recorded with a timestamp and the ID of the user who triggered the transition. |
| FR-33 | A Maintenance Engineer shall be able to escalate an unresolved session to Senior Engineer / SME review. |
| FR-34 | A Senior Engineer / SME shall be able to add expert annotations, validate likely causes, and transition the session to RESOLVED or back to IN_PROGRESS. |
| FR-35 | A Senior Engineer shall be able to flag a session for Knowledge Engineer review if a knowledge gap is identified. |
| FR-36 | Escalated sessions shall appear on the Senior Engineer dashboard automatically upon escalation. |
| FR-37 | Sessions flagged for knowledge review shall appear on the Knowledge Engineer dashboard automatically. |

### 3.7 Report Generation

| ID    | Requirement |
|-------|-------------|
| FR-38 | A fault report may be generated from any session that has at least one completed conversational exchange. |
| FR-39 | The Report Generation Agent shall synthesise a structured report from the full session transcript, recorded measurements, and session state. |
| FR-40 | The generated report shall include: issue summary, diagnostic steps taken, root cause (or "undetermined"), narrative diagnosis, prioritised corrective action recommendations, severity classification, and a follow-up required flag. |
| FR-41 | Severity shall be classified as one of: critical, high, medium, or low, according to the safety and operational impact of the fault. |
| FR-42 | The report shall be stored persistently and linked to the session, the crane, the component, and the generating engineer. |
| FR-43 | Once a report is generated, the session shall transition to the CLOSED_WITH_REPORT state. |
| FR-44 | All authenticated engineers shall be able to read any generated report. |
| FR-45 | Only the session owner or a Senior Engineer / Supervisor may trigger report generation. |

### 3.8 Dashboard and Knowledge Reuse

| ID    | Requirement |
|-------|-------------|
| FR-46 | Each role shall be presented with a role-differentiated dashboard upon login. |
| FR-47 | The Maintenance Engineer dashboard shall display the engineer's own active and completed sessions with filtering by crane, component, status, and severity. |
| FR-48 | The Supervisor dashboard shall display all open and escalated sessions across all engineers, with summary statistics and trend charts. |
| FR-49 | The Knowledge Engineer dashboard shall display sessions flagged for knowledge review and known knowledge gap patterns, including structured gap detail: gap type, affected component, confidence score, missing information, and suggested knowledge file and section. |
| FR-50 | A crane-level history view shall be accessible from the dashboard. It shall display all prior fault reports for a selected crane, enabling engineers to review past diagnoses before starting a new session. |
| FR-51 | Summary statistics shall include: total sessions, completed sessions, reports generated, follow-up required count, and distribution by severity. |

### 3.9 Knowledge Gap Resolution

| ID    | Requirement |
|-------|-------------|
| FR-52 | The Knowledge Feedback Agent shall produce a structured gap object upon session close, including: `gap_type`, `missing_information`, `affected_asset_type`, `suggested_file_to_update`, `suggested_section_or_node`, `evidence_checked`, `confidence`, and `detected_by`. |
| FR-53 | The Knowledge Engineer dashboard shall display all structured gap fields per gap record, enabling the KE to understand exactly what is missing and where to add it. |
| FR-54 | The Knowledge Engineer shall be able to update a knowledge base document directly within the tool via an in-app editor, without manual file system access. The editor shall show the current file content, allow the KE to compose new content, and optionally target a specific section header for insertion. |
| FR-55 | On submission of a KE update, the system shall: (a) append or insert the new content into the correct `.txt` knowledge file, (b) automatically re-index the ChromaDB vector store without requiring a server restart, (c) transition the associated session from KNOWLEDGE_GAP_FLAGGED to IN_PROGRESS, (d) mark the gap record as resolved with the KE's resolution note. |
| FR-56 | After a knowledge base update, the system shall create in-app notification records for the Maintenance Engineer and SME associated with the original session, indicating that updated knowledge is available and diagnosis can resume. |
| FR-57 | All authenticated users shall be able to view their own in-app notifications. Users shall be able to mark individual notifications or all notifications as read. |
| FR-58 | The AI Guidance Interface shall display a banner when the engineer resumes a session that was previously flagged as KNOWLEDGE_GAP_FLAGGED and the gap has since been resolved. |

---

## 4. Non-Functional Requirements

### 4.1 Performance

| ID     | Requirement |
|--------|-------------|
| NFR-01 | The system shall return an AI diagnostic response within 15 seconds under normal operating conditions. |
| NFR-02 | The RAG retrieval query shall complete within 2 seconds. |
| NFR-03 | The report generation endpoint shall return within 30 seconds. |
| NFR-04 | The dashboard shall load and display session data within 3 seconds for up to 200 sessions. |

### 4.2 Reliability and Availability

| ID     | Requirement |
|--------|-------------|
| NFR-05 | The system shall handle Anthropic API timeouts gracefully, returning an informative error message to the engineer rather than an unhandled exception. |
| NFR-06 | Session data and measurements shall be committed to the database before the AI response is returned to the frontend, preventing data loss on connection failure. |

### 4.3 Security

| ID     | Requirement |
|--------|-------------|
| NFR-07 | All API endpoints except `/auth/login` and `/auth/signup` shall require a valid JWT token. |
| NFR-08 | The JWT secret key shall be loaded from environment variable and shall not be committed to source control. |
| NFR-09 | Passwords shall be stored exclusively as bcrypt hashes with a work factor of at least 12. |
| NFR-10 | Role permissions shall be enforced server-side. Frontend visibility controls shall be treated as UX aids only and not as security boundaries. |
| NFR-11 | An audit log shall record: user login/logout, session creation, state transitions, report generation, and user management operations. |

### 4.4 Maintainability

| ID     | Requirement |
|--------|-------------|
| NFR-12 | Each AI agent shall be implemented as an independent module with a defined input/output contract. Agent implementations shall not directly import or call each other; coordination shall route through the Orchestrator. |
| NFR-13 | Role permissions shall be defined in a single access control configuration module (e.g., `access_control/permissions.py`). Permission changes shall not require modification of endpoint handler code. |
| NFR-14 | The knowledge base documents shall be maintained as plain-text files in `data/knowledge_base/` and can be updated without modifying application code. Re-indexing shall be triggered automatically after a KE in-app update via the `/knowledge-gaps/{id}/resolve` endpoint. Manual re-indexing can also be triggered by deleting `chroma_db/` and restarting the backend. |

### 4.5 Traceability

| ID     | Requirement |
|--------|-------------|
| NFR-15 | Every AI recommendation in a diagnostic response shall be traceable to the specific knowledge base source chunk(s) that informed it. Source metadata shall be stored with retrieved evidence. |
| NFR-16 | Every fault report shall record the session ID, the generating user ID, the timestamp, and the agent version identifier used at the time of generation. |
| NFR-17 | All fault lifecycle state transitions shall be stored with timestamp, user ID, previous state, and new state. |

---

## 5. User Roles

### 5.1 Role Definitions

#### Maintenance Engineer (ME)
A field-level qualified crane maintenance engineer. Primary user of the diagnostic guidance system. Creates troubleshooting sessions, records measurements, interacts with the AI guidance interface, and generates initial fault reports. Can escalate sessions to Senior Engineers when unable to resolve independently.

#### Senior Maintenance Engineer / Subject Matter Expert (SME)
An experienced engineer with deep component-specific or crane-specific expertise. Reviews escalated sessions, validates diagnostic hypotheses, adds expert annotations, and can continue diagnostic conversations within escalated sessions. Can flag sessions for knowledge review.

#### Knowledge Engineer (KE)
A specialist responsible for maintaining the technical knowledge base. Reviews sessions flagged as knowledge gaps, identifies missing or incorrect procedures in the manual documents, and updates the structured knowledge base. Does not conduct field diagnostics.

#### Supervisor / Maintenance Manager (SUP)
A management-level role responsible for overseeing maintenance operations. Monitors open faults, reviews escalated sessions, approves reports for critical faults, and analyses recurring fault trends and crane-level history for maintenance planning.

#### System Administrator (ADM)
Responsible for system configuration, user account management, and role assignment. Has no diagnostic role in the maintenance workflow. Accesses system audit logs and configuration settings.

---

## 6. Fault Lifecycle

### 6.1 States

| State                    | Description |
|--------------------------|-------------|
| LOGGED                   | Fault intake form submitted; session record created. |
| IN_PROGRESS              | Active diagnostic conversation in progress with the AI system. |
| AWAITING_MEASUREMENT     | AI has requested physical measurements; engineer is performing field tests. |
| PROBABLE_CAUSE_IDENTIFIED| AI Diagnostic Agent has identified a probable root cause with sufficient evidence. |
| UNRESOLVED               | Engineer has exhausted the standard diagnostic path; no conclusive cause found. |
| ESCALATED                | Session escalated to Senior Engineer / SME for expert review. |
| SME_IN_REVIEW            | Senior Engineer is actively reviewing and annotating the session. |
| KNOWLEDGE_GAP_FLAGGED    | Senior Engineer has flagged the session for Knowledge Engineer review. |
| RESOLVED                 | Root cause confirmed; corrective action identified and documented. |
| CLOSED_WITH_REPORT       | Formal fault report generated and stored; session archived. |

### 6.2 Role Involvement per State

| State                    | Can Act                        | Can View               | Can Transition To              |
|--------------------------|--------------------------------|------------------------|--------------------------------|
| LOGGED                   | ME                             | ME, SUP, ADM           | IN_PROGRESS (ME)               |
| IN_PROGRESS              | ME                             | ME, SME, SUP           | AWAITING_MEASUREMENT, PROBABLE_CAUSE_IDENTIFIED, UNRESOLVED (ME) |
| AWAITING_MEASUREMENT     | ME                             | ME, SME, SUP           | IN_PROGRESS (ME)               |
| PROBABLE_CAUSE_IDENTIFIED| ME                             | ME, SME, SUP           | RESOLVED, UNRESOLVED (ME)      |
| UNRESOLVED               | ME                             | ME, SME, SUP           | ESCALATED (ME), IN_PROGRESS (ME) |
| ESCALATED                | SME                            | ME, SME, SUP           | SME_IN_REVIEW (SME)            |
| SME_IN_REVIEW            | SME                            | ME, SME, SUP           | RESOLVED, KNOWLEDGE_GAP_FLAGGED (SME) |
| KNOWLEDGE_GAP_FLAGGED    | KE, SME                        | KE, SME, SUP           | IN_PROGRESS (KE after KB update), SME_IN_REVIEW (SME) |
| RESOLVED                 | ME, SME                        | ME, SME, SUP, KE       | CLOSED_WITH_REPORT (ME, SME)   |
| CLOSED_WITH_REPORT       | Read-only                      | All authenticated users| —                              |

### 6.3 Escalation Triggers

Escalation from IN_PROGRESS or UNRESOLVED to ESCALATED is triggered when:
- The engineer explicitly clicks "Escalate to SME" after identifying inability to resolve.
- The AI Safety Agent has flagged a critical safety condition and the engineer chooses to escalate.
- The session has exceeded 10 conversational turns without a probable cause being identified (system recommendation, not automatic transition).

### 6.4 Knowledge Gap Triggers

A session is flagged as KNOWLEDGE_GAP_FLAGGED when:
- A Senior Engineer determines that the knowledge base contains incomplete, outdated, or absent guidance for the observed fault pattern.
- The AI Retrieval Agent consistently returns zero relevant evidence for a specific component-fault combination.

---

## 7. Access Control Requirements

### 7.1 Role-Permission Matrix

| Action                          | ME  | SME | KE  | SUP | ADM |
|---------------------------------|-----|-----|-----|-----|-----|
| Login / Signup                  | ✓   | ✓   | ✓   | ✓   | ✓   |
| Create new fault session        | ✓   | ✓   |     |     |     |
| View own sessions               | ✓   | ✓   |     |     |     |
| View all sessions               |     | ✓   |     | ✓   | ✓   |
| View escalated sessions         |     | ✓   |     | ✓   |     |
| Chat / interact with AI (own)   | ✓   | ✓   |     |     |     |
| Chat / interact with AI (escalated) |  | ✓   |     |     |     |
| Record measurements             | ✓   | ✓   |     |     |     |
| Escalate session to SME         | ✓   |     |     |     |     |
| Add expert annotation           |     | ✓   |     |     |     |
| Validate likely cause           |     | ✓   |     |     |     |
| Flag for knowledge review       |     | ✓   |     |     |     |
| Generate fault report           | ✓   | ✓   |     |     |     |
| View any generated report       | ✓   | ✓   | ✓   | ✓   | ✓   |
| View crane-level history        | ✓   | ✓   | ✓   | ✓   |     |
| View dashboard statistics       | ✓   | ✓   | ✓   | ✓   |     |
| View knowledge gap cases        |     | ✓   | ✓   |     |     |
| Edit knowledge base entries (in-app) |  |  | ✓   |     |     |
| Resolve knowledge gap           |     |     | ✓   |     |     |
| Receive and view notifications  | ✓   | ✓   | ✓   | ✓   | ✓   |
| Manage users (create/deactivate)|     |     |     |     | ✓   |
| Assign roles                    |     |     |     |     | ✓   |
| View audit logs                 |     |     |     | ✓   | ✓   |
| Configure system settings       |     |     |     |     | ✓   |

---

## 8. Login and Authentication Requirements

| ID    | Requirement |
|-------|-------------|
| AUTH-01 | The system shall display a single login/signup screen as the entry point. No authenticated content shall be visible before login. |
| AUTH-02 | The signup form shall present a role selection field. For the prototype, all five roles shall be available for selection to enable evaluation. In production, role assignment shall be restricted to System Administrators. |
| AUTH-03 | Upon successful authentication, the system shall redirect the user to a role-appropriate dashboard without requiring additional navigation. |
| AUTH-04 | The authenticated user's name, username, and role shall be visibly displayed in the top navigation bar at all times. |
| AUTH-05 | A logout function shall be accessible from the navigation bar and shall invalidate the local session state and JWT token. |
| AUTH-06 | Role information from the JWT token shall be verified server-side on every protected API call. |

---

## 9. UI Requirements

| ID    | Requirement |
|-------|-------------|
| UI-01 | The application shall be implemented as a multi-screen single-page application. The active screen shall change based on navigation actions and role without full page reloads where possible. |
| UI-02 | The top navigation bar shall be persistent across all authenticated screens and shall display: application name, crane logo, logged-in user name, user role badge, and logout button. |
| UI-03 | Navigation items in the sidebar shall be filtered to show only those accessible to the current user role. |
| UI-04 | The chat interface shall use a standard conversational message layout. AI messages shall be visually distinct from engineer messages. Markdown content shall be rendered (not displayed as raw symbols). |
| UI-05 | Safety warnings generated by the Safety Agent shall be displayed as visually distinct alerts (e.g., red background, warning icon) above the regular chat content. |
| UI-06 | The Evidence panel shall display retrieved document chunks with source file name and similarity score for each chunk. |
| UI-07 | The Session State panel shall display current fault lifecycle state, completed steps list, likely causes list, and current hypothesis in a structured, readable format. |
| UI-08 | The measurement input form shall display the recommended reference ranges alongside each measurement field, sourced from the knowledge base for the selected component. |
| UI-09 | The Crane Dashboard shall support filtering by: crane type, component, fault status, severity, and date range. |
| UI-10 | Fault lifecycle state shall be displayed as a status badge with colour coding: LOGGED (grey), IN_PROGRESS (blue), ESCALATED (orange), CRITICAL/SAFETY (red), CLOSED_WITH_REPORT (green). |

---

## 10. Safety Requirements

| ID    | Requirement |
|-------|-------------|
| SAF-01 | The system shall never issue commands to crane control systems or safety-critical equipment. It is advisory-only. |
| SAF-02 | The Safety/Guardrail Agent shall be invoked on every AI response before delivery to the user. |
| SAF-03 | If a safety-critical condition is detected (e.g., brake not holding rated load, insulation resistance below minimum, structural component failure indicators), the AI response shall include an explicit safety warning recommending crane shutdown and contacting a qualified safety officer. |
| SAF-04 | Safety warnings shall be stored persistently as part of the session record and included in the generated fault report. |
| SAF-05 | The system shall not suppress or override safety warnings based on user role or preference. |

---

## 11. Reporting Requirements

| ID    | Requirement |
|-------|-------------|
| RPT-01 | The Report Generation Agent shall produce a structured JSON report that is stored in the database and rendered in a human-readable format in the dashboard. |
| RPT-02 | Reports shall include a version identifier of the agent configuration used at generation time, to support future reprocessing or comparison. |
| RPT-03 | Reports shall be exportable as PDF from the dashboard. (Prototype: structured display only; PDF export is a future extension.) |
| RPT-04 | All past reports for a given crane and component combination shall be accessible from the crane history view. |

---

## 12. Traceability Requirements

| ID    | Requirement |
|-------|-------------|
| TRC-01 | Every AI recommendation shall cite the knowledge base source document and chunk ID from which it was derived. |
| TRC-02 | The session record shall store the complete message history, all measurements, all state transitions (with timestamps and actor IDs), and all retrieved evidence sets. |
| TRC-03 | The fault report shall reference the session ID, the specific evidence chunks used during diagnosis, and the engineer(s) who contributed to the session. |
| TRC-04 | Escalation records shall log the originating engineer, the SME who received the escalation, and any annotations added during SME review. |

---

## 13. Assumptions and Constraints

| ID    | Statement |
|-------|-----------|
| ASS-01 | The knowledge base consists of structured plain-text documents. Knowledge Engineers can update these documents via the in-app editor; file upload from external sources is not in scope for Version 2 prototype. |
| ASS-02 | The system operates as a single-tenant deployment. Multi-tenant isolation is not in scope. |
| ASS-03 | The Anthropic API (`claude-sonnet-4-6`) is available and accessible via a valid API key stored in the environment. |
| ASS-04 | The embedding model (`all-MiniLM-L6-v2`) is available locally via sentence-transformers. |
| ASS-05 | The prototype uses SQLite as the database backend. Concurrent multi-user write throughput is limited and PostgreSQL migration is recommended for production. |
| ASS-06 | Users are assumed to be qualified personnel. The system does not implement ability-testing or formal qualification verification. |
| ASS-07 | Role assignment at signup is a prototype convenience. In production, role assignment shall require System Administrator action. |
| CON-01 | The system must operate without a live connection to crane hardware, sensors, or SCADA systems. |
| CON-02 | The system must function in a workshop or office network environment without guaranteed high-bandwidth connectivity. |
