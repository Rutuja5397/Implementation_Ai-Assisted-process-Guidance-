# USE_CASES.md
# Use Cases — AI-Assisted Process Guidance Tool (Version 2)
# Master Thesis, RPTU / Fraunhofer IESE, 2025

---

## 1. Actors

| Actor | Type | Description |
|-------|------|-------------|
| Maintenance Engineer (ME) | Human (Primary) | Field-level qualified crane maintenance engineer. Executes diagnostic sessions, records measurements, and generates initial reports. |
| Senior Maintenance Engineer / SME | Human (Primary) | Experienced engineer who reviews escalated sessions, validates hypotheses, and adds expert annotations. |
| Knowledge Engineer (KE) | Human (Secondary) | Maintains the structured knowledge base. Reviews knowledge gap cases and updates component documentation. |
| Supervisor / Maintenance Manager (SUP) | Human (Secondary) | Monitors open and escalated faults, reviews reports, and analyses fault trends. |
| System Administrator (ADM) | Human (System) | Manages user accounts, assigns roles, configures system settings, and accesses audit logs. |
| Session Orchestrator | AI System | Coordinates the multi-agent AI pipeline. Invoked by the backend on every session request. Not directly visible to users. |
| Retrieval Agent | AI System | Retrieves relevant knowledge chunks from ChromaDB on every conversational turn. |
| Diagnostic Reasoning Agent | AI System | Generates diagnostic responses grounded in retrieved evidence. |
| Parameter Interpretation Agent | AI System | Interprets numeric measurements against component reference specifications. |
| Safety / Guardrail Agent | AI System | Evaluates every AI response for safety-critical conditions before delivery. |
| Report Generation Agent | AI System | Synthesises structured fault reports from completed session data. |
| Knowledge Feedback Agent | AI System | Identifies knowledge gaps from closed sessions and flags them for KE review. |

---

## 2. Use Case Summary

| UC ID  | Use Case Name                        | Primary Actor       | Secondary Actors    | Screen |
|--------|--------------------------------------|---------------------|---------------------|--------|
| UC-01  | Sign Up                              | All roles           | ADM                 | Login/Signup |
| UC-02  | Log In                               | All roles           | —                   | Login/Signup |
| UC-03  | Log Out                              | All roles           | —                   | Navigation bar |
| UC-04  | Log Fault Issue                      | ME, SME             | Session Orchestrator, Intake Agent | Issue Intake Form |
| UC-05  | Start Diagnostic Session             | Session Orchestrator| Retrieval Agent, Diagnostic Agent  | AI Guidance Interface |
| UC-06  | Conduct Diagnostic Conversation      | ME, SME             | Session Orchestrator, all AI Agents | AI Guidance Interface |
| UC-07  | Record Physical Measurements         | ME, SME             | Parameter Interpretation Agent      | AI Guidance Interface |
| UC-08  | Review Retrieved Evidence            | ME, SME             | Retrieval Agent     | AI Guidance Interface |
| UC-09  | Escalate Unresolved Issue to SME     | ME                  | SME, Session Orchestrator           | AI Guidance Interface |
| UC-10  | Expert Review by SME                 | SME                 | Session Orchestrator, Diagnostic Agent | AI Guidance Interface |
| UC-11  | Add Expert Annotation                | SME                 | —                   | AI Guidance Interface |
| UC-12  | Flag Session for Knowledge Review    | SME                 | Knowledge Feedback Agent, KE        | AI Guidance Interface |
| UC-13  | Generate Fault Report                | ME, SME             | Report Generation Agent             | Guidance / Dashboard |
| UC-14  | View Own Session History             | ME, SME             | —                   | Dashboard |
| UC-15  | View All Sessions (Cross-Engineer)   | SME, SUP, ADM       | —                   | Dashboard |
| UC-16  | View Escalated Sessions              | SME, SUP            | —                   | Dashboard |
| UC-17  | Resume Active Session                | ME, SME             | Session Orchestrator| AI Guidance Interface |
| UC-18  | Review Crane History                 | ME, SME, KE, SUP    | —                   | Dashboard (Crane History) |
| UC-19  | View Knowledge Gap Cases             | KE, SME             | —                   | Dashboard (KE View) |
| UC-20  | Manage Users and Roles               | ADM                 | —                   | Admin Panel |
| UC-21  | View Audit Log                       | ADM, SUP            | —                   | Admin Panel |
| UC-22  | Resolve Knowledge Gap via In-App Editor | KE               | RAG System, ME, SME | Dashboard (KE View) |
| UC-23  | Receive and View Notifications       | All roles           | —                   | Navigation bar |

---

## 3. Use Case Narratives

---

### UC-01: Sign Up

**Goal**: A new user creates an account and gains access to the system with an appropriate role.

**Actors**: Any new user, optionally supervised by ADM.

**Precondition**: The user does not have an existing account. The application login/signup screen is accessible.

**Trigger**: The user selects "Create Account" on the login screen.

**Main Flow**:
1. The user enters their full name, a chosen username, a password, and selects a role from the available options (ME, SME, KE, SUP, ADM).
2. The system validates that the username is not already taken.
3. The system hashes the password using bcrypt and stores the user record with the assigned role.
4. A JWT access token is issued (8-hour expiry), embedding the user's ID, username, and role.
5. The system redirects the user to the role-appropriate dashboard.

**Alternative Flow**:
- If the username is already in use, the system displays an error and prompts the user to choose a different username.
- If required fields are missing, inline validation errors are displayed.

**Postcondition**: A verified user account exists. The user is authenticated and directed to their role-appropriate dashboard.

**Note (Prototype)**: Role selection at signup is a convenience for prototype evaluation. In production, role assignment would require System Administrator action after account creation.

---

### UC-02: Log In

**Goal**: An existing user authenticates with the system and accesses their role-appropriate dashboard.

**Actors**: Any registered user.

**Precondition**: The user has a registered account. The login screen is displayed.

**Trigger**: The user enters credentials and clicks "Login".

**Main Flow**:
1. The user enters their username and password.
2. The system verifies the password against the stored bcrypt hash.
3. A JWT token is issued and stored in browser session state.
4. The system reads the role from the JWT payload.
5. The user is redirected to the dashboard screen appropriate to their role.

**Alternative Flow**:
- If credentials are incorrect, an error is displayed. No token is issued.

**Postcondition**: The user is authenticated, their role is known to the application, and they are presented with a role-specific dashboard.

---

### UC-04: Log Fault Issue (Intake)

**Goal**: An engineer creates a new troubleshooting session by describing the fault through a structured intake form.

**Actors**: ME (primary), SME (permitted).

**Precondition**: The user is authenticated with ME or SME role.

**Trigger**: The user selects "New Fault" or "New Issue" from the navigation.

**Main Flow**:
1. The engineer selects the crane type from a dropdown (e.g., Demag EKKE 5t, Liebherr Tower Crane).
2. The engineer selects the affected component from a dynamic dropdown populated based on the crane selection (e.g., Hoist Motor, Hoist Brake, Wire Rope).
3. The engineer enters a free-text description of the observed fault.
4. Optionally, the engineer enters: environmental conditions, recent maintenance changes, and any error codes or warning indicator values.
5. The engineer submits the form.
6. The Intake Agent validates the form data and constructs a context snapshot.
7. The system creates a new TroubleshootingSession record in state LOGGED.
8. The Session Orchestrator invokes the Retrieval Agent and Diagnostic Reasoning Agent to generate an opening diagnostic message.
9. The session state transitions to IN_PROGRESS.
10. The engineer is redirected to the AI Guidance Interface with the opening message displayed.

**Postcondition**: A new session exists in IN_PROGRESS state. The diagnostic conversation has begun. The AI has acknowledged the fault context without repeating the intake data back to the engineer.

---

### UC-06: Conduct Diagnostic Conversation

**Goal**: The engineer and the AI system work through a structured diagnostic sequence to identify the root cause of the fault.

**Actors**: ME or SME (human); Session Orchestrator, Retrieval Agent, Diagnostic Reasoning Agent, Parameter Interpretation Agent, Safety Agent (AI).

**Precondition**: An active session exists in IN_PROGRESS or AWAITING_MEASUREMENT state.

**Trigger**: The engineer types a message (observation, measurement result, or answer to an AI question) and submits.

**Main Flow**:
1. The engineer types an observation or answer and submits the chat input.
2. The system persists the engineer's message and assembles the conversation history.
3. The Session Orchestrator invokes the Retrieval Agent to retrieve up to five relevant knowledge chunks for the current component and message context.
4. If new measurements have been recorded since the last turn, the Parameter Interpretation Agent annotates them against reference specifications.
5. The Orchestrator assembles the system prompt: context snapshot + evidence + annotated measurements + current session state.
6. The Diagnostic Reasoning Agent generates a response with a targeted follow-up question or diagnostic instruction, grounded in the retrieved evidence.
7. The Diagnostic Reasoning Agent embeds a `session_update` JSON block in the response, updating completed steps, likely causes, and the current hypothesis.
8. The Safety Agent evaluates the response. If a safety-critical condition is identified, a prominently displayed safety alert is prepended.
9. The Orchestrator parses the session_update block and writes updated state fields to the database.
10. The AI response, retrieved evidence, and updated session state are returned to the frontend.
11. The evidence is displayed in the Evidence panel. The session state is reflected in the Session State panel.

**Alternative Flows**:
- If the Safety Agent detects a critical condition (e.g., brake not holding load), a CRITICAL safety alert is displayed above the response. The session is flagged with a safety warning. The engineer is advised to suspend crane operation.
- If the Retrieval Agent returns no relevant evidence for the component, the Diagnostic Agent explicitly acknowledges the evidence limitation and focuses on the engineer's described observations.
- If the Diagnostic Agent signals `unresolved_flag: true` (after 8+ turns without resolution), the system recommends escalation or closure.

**Postcondition**: The session record is updated with new completed steps, likely causes, and the current hypothesis. The conversation is persisted.

---

### UC-07: Record Physical Measurements

**Goal**: The engineer records numerical measurements taken during the physical inspection of the crane component.

**Actors**: ME, SME.

**Precondition**: An active session exists. The engineer has performed physical measurements at the crane site.

**Trigger**: The engineer opens the Measurements tab and submits new measurement values.

**Main Flow**:
1. The engineer opens the Measurements tab in the right panel of the guidance interface.
2. The engineer enters one or more values from the measurement fields: voltage (V), current (A), temperature (°C), load (kg), brake gap (mm), insulation resistance (MΩ), vibration (mm/s RMS).
3. An optional free-text notes field is available for qualitative observations.
4. The measurement record is stored and linked to the current session.
5. On the next conversational turn, the Parameter Interpretation Agent interprets all recorded measurements against the component's reference specifications.
6. The annotated measurements are injected into the AI system prompt, enabling the AI to interpret values and identify deviations.

**Postcondition**: Measurements are stored and visible in the panel. The AI will reference and interpret them in the next response.

---

### UC-08: Review Retrieved Evidence

**Goal**: The engineer reviews the technical knowledge base passages that the AI system retrieved as the basis for its current response.

**Actors**: ME, SME.

**Precondition**: A diagnostic conversation is active. The Retrieval Agent has returned evidence for the latest turn.

**Trigger**: The engineer clicks the Evidence tab in the right panel.

**Main Flow**:
1. The Evidence tab displays the up-to-five knowledge chunks retrieved for the latest conversational turn.
2. Each chunk shows: source document name, similarity score, and the text content of the passage.
3. The engineer can read the source documentation to verify the AI's reasoning.
4. The engineer can use this information to challenge or validate the AI's hypothesis.

**Postcondition**: The engineer has direct visibility into the knowledge sources underpinning each AI recommendation. Full traceability is maintained.

---

### UC-09: Escalate Unresolved Issue to SME

**Goal**: A Maintenance Engineer escalates a session that they cannot resolve independently to a Senior Engineer for expert review.

**Actors**: ME (initiates), SME (receives).

**Precondition**: An active session exists in IN_PROGRESS, AWAITING_MEASUREMENT, or UNRESOLVED state. The user has ME role.

**Trigger**: The engineer clicks "Escalate to SME" in the guidance interface.

**Main Flow**:
1. The engineer clicks "Escalate to SME".
2. The system displays a text input for the engineer to describe what has been tried and why escalation is needed.
3. The engineer submits the escalation note.
4. The system records the escalation: originating engineer, timestamp, escalation reason.
5. The session lifecycle state transitions to ESCALATED.
6. The session appears on the SME dashboard under "Escalated Sessions".
7. The engineer is shown a confirmation message and the session moves to read-only for the engineer (they can still view but not continue the chat).

**Alternative Flow**:
- If no SME accounts exist in the system, the escalation still proceeds but an advisory note is shown to also contact a senior engineer directly.

**Postcondition**: The session is in ESCALATED state. The originating engineer's work and context are preserved. The SME can see the session and pick it up for review.

---

### UC-10: Expert Review by SME

**Goal**: A Senior Maintenance Engineer reviews an escalated session, continues the diagnostic conversation if needed, and resolves or further routes the case.

**Actors**: SME (primary); Diagnostic Reasoning Agent, all AI pipeline agents (secondary).

**Precondition**: A session in ESCALATED state is visible on the SME's dashboard.

**Trigger**: The SME clicks "Open for Review" on the escalated session.

**Main Flow**:
1. The SME is navigated to the AI Guidance Interface for the escalated session.
2. The full conversation history, measurements, evidence, and escalation notes are restored.
3. The session state transitions to SME_IN_REVIEW.
4. The SME can continue the diagnostic conversation using the same chat interface.
5. The system prompt is augmented with the SME role context and the escalation notes.
6. The AI Diagnostic Agent is aware it is interacting with an SME and adjusts response depth accordingly.
7. The SME can validate the likely causes, add expert annotations (UC-11), and mark the session as RESOLVED when the root cause is confirmed.
8. If the SME identifies a knowledge gap, they flag the session for KE review (UC-12).

**Postcondition**: The session has been reviewed by a subject matter expert. It is either RESOLVED with a confirmed root cause, or KNOWLEDGE_GAP_FLAGGED for knowledge base maintenance.

---

### UC-11: Add Expert Annotation

**Goal**: A Senior Engineer adds a structured expert observation or cause validation to the session record, outside the conversational chat.

**Actors**: SME.

**Precondition**: The session is in SME_IN_REVIEW state. The SME is in the AI Guidance Interface.

**Trigger**: The SME opens the Annotations panel and enters an expert note.

**Main Flow**:
1. The SME opens the Annotations panel in the guidance interface.
2. The SME enters an expert note: free text describing the validated cause, a corrected procedure, or additional technical context.
3. The annotation type is selected: Expert Note, Cause Validation, or Procedure Correction.
4. The annotation is stored in the `expert_annotations` table, linked to the session and the SME's user ID.
5. The annotation is included in the data passed to the Report Generation Agent when a report is generated.
6. The annotation is visible to the original engineer and in the dashboard.

**Postcondition**: The expert annotation is persistently stored, linked to the session, and included in any subsequent report.

---

### UC-12: Flag Session for Knowledge Review

**Goal**: A Senior Engineer identifies that the knowledge base is missing or incorrect information relevant to the fault and flags the session so the Knowledge Engineer can update the knowledge base.

**Actors**: SME (initiates), KE (receives).

**Precondition**: The session is in SME_IN_REVIEW state.

**Trigger**: The SME clicks "Flag for Knowledge Review".

**Main Flow**:
1. The SME provides a brief description of the knowledge gap (e.g., "The hoist brake manual does not include procedures for contaminated brake lining — only wear-related adjustment is covered.").
2. The system creates a knowledge gap record: component, fault pattern, gap type, reference session ID.
3. The session state transitions to KNOWLEDGE_GAP_FLAGGED.
4. The knowledge gap record appears on the Knowledge Engineer's dashboard.
5. The Knowledge Feedback Agent is invoked to check for other sessions with similar patterns.

**Postcondition**: The knowledge gap is recorded. The KE is notified via their dashboard. The session is preserved as a reference case.

---

### UC-13: Generate Fault Report

**Goal**: Generate a structured, AI-synthesised fault report from the completed or resolved session.

**Actors**: ME, SME (initiates); Report Generation Agent (executes).

**Precondition**: The session has at least one completed conversational exchange. The session is in IN_PROGRESS, PROBABLE_CAUSE_IDENTIFIED, RESOLVED, or SME_IN_REVIEW state.

**Trigger**: The engineer or SME clicks "Generate Report" in the guidance interface or from the dashboard session row.

**Main Flow**:
1. The system collects the full session data: conversation transcript, all measurements with annotations, expert annotations, session state, and escalation records.
2. The Report Generation Agent receives the complete data and is prompted to synthesise a structured JSON fault report.
3. The AI generates the report fields: issue summary, steps taken, root cause, narrative diagnosis, recommendations, severity, and follow-up flag.
4. The system parses and validates the JSON output.
5. The report is stored in the database, linked to the session, crane, component, and generating engineer.
6. The session state transitions to CLOSED_WITH_REPORT.
7. The Knowledge Feedback Agent is invoked to check for knowledge gaps in the closed session.
8. The engineer is redirected to the dashboard where the report is immediately visible.

**Severity Assignment**:
- **critical**: Immediate safety risk; crane must not be operated.
- **high**: Significant fault; operation should be suspended pending repair.
- **medium**: Degraded operation; repair should be scheduled within 48 hours.
- **low**: Minor issue; address at next planned maintenance interval.

**Postcondition**: A structured, AI-synthesised fault report is stored and accessible to all authenticated engineers. The session is closed.

---

### UC-14: View Own Session History

**Goal**: An engineer reviews their own past troubleshooting sessions, including generated reports and session states.

**Actors**: ME, SME.

**Precondition**: The user is authenticated. At least one session exists for the user.

**Trigger**: The user navigates to the Dashboard and views the "My Sessions" tab.

**Main Flow**:
1. The dashboard retrieves all sessions belonging to the logged-in engineer.
2. Sessions are displayed in reverse chronological order with: crane type, component, problem description, lifecycle state badge, date, and severity badge (if report generated).
3. The engineer can filter by crane type, component, status, and severity.
4. Expanding a session row reveals the full fault report (if generated), a Resume or View button, and a Generate Report button if no report exists.
5. Summary statistics are displayed: total sessions, completed, reports generated, follow-up required.

**Postcondition**: The engineer has a complete view of their diagnostic history.

---

### UC-16: View Escalated Sessions

**Goal**: A Senior Engineer or Supervisor reviews sessions that have been escalated for SME attention.

**Actors**: SME, SUP.

**Precondition**: At least one session is in ESCALATED or SME_IN_REVIEW state.

**Trigger**: The user navigates to the "Escalated" tab on their dashboard.

**Main Flow**:
1. The dashboard retrieves all sessions in ESCALATED or SME_IN_REVIEW state.
2. Sessions display: originating engineer, crane, component, problem description, escalation date, escalation reason, and current state.
3. SME users see a "Open for Review" button on each session.
4. Supervisor users see the sessions in read-only mode for monitoring.

**Postcondition**: The SME or Supervisor has an overview of all cases requiring expert attention.

---

### UC-18: Review Crane History

**Goal**: An engineer or supervisor reviews all past fault reports for a specific crane to inform diagnosis or maintenance planning.

**Actors**: ME, SME, KE, SUP.

**Precondition**: At least one fault report exists in the system.

**Trigger**: The user selects a crane type from the Crane History view on the dashboard.

**Main Flow**:
1. The user selects a crane type from the dropdown.
2. The system retrieves all CLOSED_WITH_REPORT sessions for that crane across all engineers.
3. The history view displays: session date, component, problem summary, root cause, severity, recommendations, and the engineer who diagnosed it.
4. The user can filter by component, severity, and date range.
5. The user can expand any entry to read the full fault report.

**Postcondition**: The engineer has access to documented fault patterns and prior resolutions for the selected crane, enabling informed diagnosis and maintenance planning.

---

### UC-19: View Knowledge Gap Cases

**Goal**: The Knowledge Engineer reviews flagged knowledge gaps and understands what is missing and where to add it.

**Actors**: KE (primary), SME (can view).

**Precondition**: At least one session has been flagged as a knowledge gap by an SME or auto-detected by the Knowledge Feedback Agent.

**Trigger**: KE navigates to the Knowledge Gaps tab on their dashboard.

**Main Flow**:
1. The KE dashboard displays all open knowledge gap records with structured detail: component, fault pattern, gap type, missing information description, confidence score, suggested knowledge file to update, and suggested section.
2. The KE reviews the structured gap detail to understand the diagnostic context.
3. KE can toggle to also view previously resolved gaps.
4. The KE proceeds to UC-22 to resolve the gap via the in-app editor.

**Postcondition**: The KE has a clear view of what is missing, where it should be added, and with what level of confidence the gap was detected.

---

### UC-22: Resolve Knowledge Gap via In-App Editor

**Goal**: The Knowledge Engineer adds missing knowledge directly in the tool, triggering automatic KB re-indexing and notification of affected engineers.

**Actors**: KE (primary); RAG System, ME and SME of the original session (receive notifications).

**Precondition**: An open knowledge gap record exists. The KE is authenticated with KE role.

**Trigger**: KE clicks "Update & Resolve" on a knowledge gap card in the KE dashboard.

**Main Flow**:
1. An in-app editor expands on the selected gap card.
2. The editor displays the current content of the suggested knowledge file (read-only preview).
3. The KE composes new content to add (free-text field) and optionally specifies a target section header for insertion (pre-filled from the gap's `suggested_section_or_node` value).
4. The KE enters a resolution audit note explaining the change made.
5. The KE submits the form.
6. The system writes the new content into the correct `.txt` file at the target section or appends to end-of-file if section not found.
7. The system calls `RAGSystem.reinitialize()` to delete and re-index the ChromaDB collection. Future retrievals will include the new content.
8. The system transitions the session associated with the gap from KNOWLEDGE_GAP_FLAGGED back to IN_PROGRESS, enabling the ME to resume diagnosis.
9. The system marks the gap record as resolved with the KE's resolution note and audit timestamp.
10. Notification records are created for the ME and SME of the original session: "Knowledge base has been updated for [component] by [KE]. You may resume diagnosis."
11. A success message is displayed to the KE confirming the file update and re-indexing.

**Alternative Flow**:
- If the target section is not found in the file, the new content is appended to the end of the file with an auditable section block marker.
- If re-indexing fails, an error is shown to the KE and the update is rolled back (file reverted).

**Postcondition**: The knowledge file is updated. ChromaDB reflects the new content. The ME can resume diagnosis with the updated knowledge available. The gap is marked resolved. ME and SME are notified.

---

### UC-23: Receive and View Notifications

**Goal**: An engineer or supervisor receives and dismisses in-app notifications about events relevant to their sessions.

**Actors**: All authenticated roles.

**Precondition**: At least one notification exists for the user.

**Trigger**: The user sees the notification bell in the top navigation bar showing an unread count badge.

**Main Flow**:
1. The user clicks the notification bell icon in the top navigation bar.
2. A popover opens showing the user's last 10 notifications with message text and timestamp.
3. Each notification is marked as read when the popover is viewed.
4. The unread count badge clears after reading.
5. Notifications remain visible in the popover (not deleted when read).

**Postcondition**: The user is informed of relevant system events (e.g., knowledge base updated for their session, session escalated). Notifications are marked as read.

---

### UC-20: Manage Users and Roles

**Goal**: The System Administrator creates, manages, and assigns roles to user accounts.

**Actors**: ADM.

**Precondition**: The user is authenticated with ADM role.

**Trigger**: The ADM navigates to the Admin Panel.

**Main Flow**:
1. The Admin Panel displays all registered users with: name, username, role, account status, and last login date.
2. The ADM can create a new user account: enter name, username, temporary password, and assign role.
3. The ADM can change the role of an existing user from a role dropdown.
4. The ADM can deactivate a user account, preventing login without deleting the account.
5. All administrative actions are written to the audit log.

**Postcondition**: User accounts and role assignments reflect the ADM's changes. The audit log records all administrative actions.

---

### UC-21: View Audit Log

**Goal**: An Administrator or Supervisor reviews the system audit trail to monitor activity and investigate incidents.

**Actors**: ADM, SUP.

**Precondition**: The user is authenticated with ADM or SUP role.

**Trigger**: The user navigates to the Audit Log view in the Admin Panel.

**Main Flow**:
1. The audit log view displays a chronological list of recorded events: event type, actor, affected resource, timestamp, and details.
2. The user can filter by event type (login, session_create, report_generate, state_transition, role_assign, etc.) and date range.
3. Events are read-only; no modifications are possible.

**Postcondition**: The administrator or supervisor has a complete chronological record of system activity for the filtered period.

---

## 4. Use Case Relationships

```
UC-01 (Sign Up) ────────────────────── extends ──────► UC-02 (Log In) [implicit]
UC-02 (Log In) ──────── includes ──────► (Role-based dashboard routing)
UC-04 (Log Fault) ──────────────────── includes ──────► UC-05 (Start Session)
UC-05 (Start Session) ──────────────── includes ──────► UC-06 (Conduct Conversation)
UC-06 (Conduct Conversation) ──────── includes ──────► UC-07 (Record Measurements) [optional]
UC-06 (Conduct Conversation) ──────── includes ──────► UC-08 (Review Evidence)
UC-06 (Conduct Conversation) ────── extends ──────────► UC-09 (Escalate) [when unresolved]
UC-09 (Escalate) ───────────────────── triggers ──────► UC-10 (Expert Review by SME)
UC-10 (Expert Review) ─────────────── includes ──────► UC-11 (Expert Annotation) [optional]
UC-10 (Expert Review) ─────────────── extends ──────► UC-12 (Flag Knowledge Gap) [when gap found]
UC-06 or UC-10 ──────────────────────── leads to ──────► UC-13 (Generate Report)
UC-13 (Generate Report) ──────────── triggers ──────► (Knowledge Feedback Agent)
UC-14 (View Own History) ────────────── extends ──────► UC-13 (Generate Report) [if missing]
UC-14 (View Own History) ────────────── includes ──────► UC-17 (Resume Session) [if active]
UC-15 (View All Sessions) ──────────── extends ──────► UC-16 (View Escalated) [SME/SUP]
UC-18 (Crane History) ──────────────── depends on ──► UC-13 (Generated Reports)
UC-19 (Knowledge Gaps) ─────────────── triggered by ► UC-12 (Flag Knowledge Gap)
UC-19 (Knowledge Gaps) ─────────────── leads to ──────► UC-22 (Resolve via In-App Editor)
UC-22 (Resolve KB Gap) ─────────────── triggers ──────► UC-23 (Notifications to ME/SME)
UC-22 (Resolve KB Gap) ─────────────── transitions ──► Session back to IN_PROGRESS
UC-20 (Manage Users) ────────────────── enables ──────► UC-01 (Sign Up) [production]
```
