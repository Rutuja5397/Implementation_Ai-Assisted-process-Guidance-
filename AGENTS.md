# AGENTS.md
# Multi-Agent System Design — AI-Assisted Process Guidance Tool
# Master Thesis, RPTU / Fraunhofer IESE, 2025

---

## 1. Overview

The multi-agent architecture decomposes the AI guidance pipeline into eight specialised agents, each responsible for a distinct capability within the diagnostic workflow. A central **Session Orchestrator** coordinates agent invocation and manages the shared session state. Agents communicate exclusively through the Orchestrator and do not directly invoke one another.

The design principle is: **each agent does one thing well, and the Orchestrator decides when and in what order agents are invoked**.

```
Engineer Input
      │
      ▼
┌─────────────────────────────────────┐
│         Session Orchestrator        │  ← coordinates all agents
└──┬──────┬──────┬──────┬──────┬──────┘
   │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼
Intake  Retrieval  Diagnostic  Parameter  Procedure
Agent    Agent     Reasoning   Interpret.  Guidance
                   Agent       Agent       Agent
                      │
                      ▼
               Safety / Guardrail Agent
                      │
                      ▼
              Report Generation Agent
                      │
                      ▼
           Knowledge Feedback Agent
```

---

## 2. Agent Registry

| Agent ID | Agent Name                  | Invoked By                   | Produces                         |
|----------|-----------------------------|------------------------------|----------------------------------|
| AGT-01   | Session Orchestrator        | Backend request handler      | Agent routing decisions          |
| AGT-02   | Intake Agent                | Orchestrator on session start| Validated context snapshot       |
| AGT-03   | Retrieval Agent             | Orchestrator on each turn    | Ranked evidence chunks           |
| AGT-04   | Diagnostic Reasoning Agent  | Orchestrator on each turn    | AI response + session_update     |
| AGT-05   | Parameter Interpretation Agent | Orchestrator when measurements present | Interpretation annotations |
| AGT-06   | Procedure Guidance Agent    | Orchestrator on procedure request | Step-by-step instructions   |
| AGT-07   | Safety / Guardrail Agent    | Orchestrator before response delivery | Safety evaluation verdict |
| AGT-08   | Report Generation Agent     | Orchestrator on report request | Structured JSON fault report  |
| AGT-09   | Knowledge Feedback Agent    | Orchestrator on session close | Knowledge gap signals         |

---

## 3. Agent Specifications

---

### AGT-01: Session Orchestrator

**Purpose**
The Session Orchestrator is the central coordination agent. It is the only agent with knowledge of all other agents. It receives an incoming request (session creation, chat turn, report request), determines the appropriate pipeline of agent invocations, passes data between agents in the correct sequence, and writes the final results to the session state.

**Responsibilities**
- Receive structured input from the API request handler
- Determine which agents to invoke and in what order based on the current session state and request type
- Assemble the context package passed to each agent (session state, conversation history, measurements, retrieved evidence)
- Route the output of one agent as input to the next where chaining is required
- Enforce agent boundaries: no agent receives data it is not authorised to see
- Write the final session state update to the database
- Detect safety flag signals from the Safety Agent and ensure they take precedence in the final response
- Handle agent failures gracefully: if an agent returns an error or empty result, log the failure and continue with a degraded response rather than a system crash

**Input**
```json
{
  "request_type": "chat_turn | session_start | report | escalate",
  "session_id": "string",
  "user_id": "string",
  "user_role": "ME | SME | KE | SUP | ADM",
  "message": "string (for chat turns)",
  "session_snapshot": {
    "crane": "string",
    "component": "string",
    "problem_description": "string",
    "environment": "string",
    "recent_changes": "string",
    "error_codes": "string",
    "current_state": "fault_lifecycle_state",
    "completed_steps": ["string"],
    "likely_causes": ["string"],
    "current_hypothesis": "string",
    "measurements": [{ ... }],
    "message_history": [{ "role": "string", "content": "string" }]
  }
}
```

**Output**
```json
{
  "ai_response": "string",
  "safety_flag": "boolean",
  "safety_message": "string | null",
  "evidence_chunks": [{ "source": "string", "content": "string", "score": "float" }],
  "session_update": {
    "completed_steps": ["string"],
    "likely_causes": ["string"],
    "current_hypothesis": "string",
    "new_state": "fault_lifecycle_state | null"
  }
}
```

**State Read**  
Full session snapshot from the database: messages, measurements, completed steps, likely causes, hypothesis, lifecycle state.

**State Written**  
Updated messages, updated session fields (completed_steps, likely_causes, current_hypothesis, lifecycle_state), new evidence records.

**Boundaries**
- The Orchestrator does not generate any diagnostic content itself.
- The Orchestrator does not access the Anthropic API directly; it delegates to the Diagnostic Reasoning Agent.
- The Orchestrator does not modify knowledge base documents.

---

### AGT-02: Intake Agent

**Purpose**
Validates and structures the raw intake form submission into a well-formed context snapshot that can be reliably consumed by downstream agents.

**Responsibilities**
- Validate that required fields are present (crane type, component, problem description)
- Normalise free-text fields (trim whitespace, sanitise for injection)
- Construct the `context_snapshot` string used in the initial system prompt
- Identify any missing optional fields and mark them as absent rather than leaving them empty
- Check that the selected crane/component combination is in the known catalogue

**Input**
```json
{
  "crane_type": "string",
  "component": "string",
  "problem_description": "string",
  "environment": "string | null",
  "recent_changes": "string | null",
  "error_codes": "string | null"
}
```

**Output**
```json
{
  "valid": true,
  "context_snapshot": "string (structured text block for system prompt injection)",
  "component_key": "string (normalised component key for ChromaDB filter)",
  "validation_errors": []
}
```

**State Read**: None (stateless; input is the intake form payload).  
**State Written**: None (produces output passed to Orchestrator only).

**Boundaries**
- Does not perform any knowledge retrieval.
- Does not invoke any LLM calls.

---

### AGT-03: Retrieval Agent

**Purpose**
Retrieves relevant technical knowledge chunks from the ChromaDB vector store to ground the Diagnostic Reasoning Agent's responses in documented component specifications, procedures, and fault patterns.

**Responsibilities**
- Construct a composite semantic search query from the component name, problem description, and the engineer's latest message
- Execute a component-filtered query: retrieve the top 3 chunks filtered by the `source` metadata field matching the selected component document
- Execute a general corpus query: retrieve 2 additional chunks from the full knowledge base (cross-component context)
- Deduplicate chunks that appear in both result sets
- Rank final result set by cosine similarity score (descending)
- Return the ranked evidence set with source, content, and score metadata

**Input**
```json
{
  "component_key": "string",
  "query_terms": "string (composed from problem description + latest message)",
  "max_results": { "component_filtered": 3, "general": 2 }
}
```

**Output**
```json
{
  "evidence_chunks": [
    {
      "chunk_id": "string",
      "source": "string (filename)",
      "content": "string",
      "score": 0.87,
      "filter_type": "component | general"
    }
  ],
  "retrieval_metadata": {
    "query_used": "string",
    "total_chunks_considered": 120,
    "chunks_returned": 5
  }
}
```

**State Read**: ChromaDB vector store (read-only).  
**State Written**: None (evidence is passed to the Orchestrator; persisted by the Orchestrator).

**Boundaries**
- Does not modify the vector store.
- Does not make LLM API calls.
- If no relevant chunks are found for a component, the agent returns an empty array and signals `knowledge_gap_indicator: true`.

---

### AGT-04: Diagnostic Reasoning Agent

**Purpose**
The core LLM-based reasoning agent. Generates targeted diagnostic questions, interprets engineer observations, formulates and updates diagnostic hypotheses, and proposes corrective actions. Produces structured session state updates embedded in every response.

**Responsibilities**
- Construct a system prompt that includes: role context, context snapshot, retrieved evidence, all recorded measurements, current session state, and explicit constraints (do not repeat intake data, do not make safety decisions unilaterally, remain advisory)
- Invoke the Anthropic API (`claude-sonnet-4-6`) with the full conversation history as the user/assistant message sequence
- Generate a diagnostic response that is directly actionable for a field engineer
- Embed a `session_update` JSON block in every response containing: updated `completed_steps`, `likely_causes`, and `current_hypothesis`
- Flag in the response if a safety-critical condition is suspected (for the Safety Agent to evaluate)
- Indicate when a probable cause has been identified with sufficient evidence
- Indicate when the standard diagnostic path has been exhausted without resolution

**Input**
```json
{
  "system_prompt": "string (assembled by Orchestrator from context snapshot + evidence + measurements)",
  "conversation_history": [{ "role": "user|assistant", "content": "string" }],
  "session_state": { "completed_steps": [], "likely_causes": [], "current_hypothesis": "" }
}
```

**Output**
```json
{
  "response_text": "string (human-readable markdown)",
  "session_update": {
    "completed_steps": ["string"],
    "likely_causes": ["string"],
    "current_hypothesis": "string",
    "probable_cause_flag": false,
    "unresolved_flag": false,
    "safety_concern_flag": false,
    "safety_concern_description": "string | null"
  },
  "tokens_used": { "input": 0, "output": 0 }
}
```

**State Read**: Session messages, session state fields, retrieved evidence (all injected via system prompt).  
**State Written**: Produces session_update payload; Orchestrator writes this to the database.

**Boundaries**
- Does not access the database directly.
- Does not retrieve knowledge independently; evidence is provided by the Retrieval Agent via the Orchestrator.
- Does not make safety determinations independently; safety evaluation is delegated to the Safety Agent.
- Does not generate reports; report synthesis is delegated to the Report Generation Agent.
- If the API call fails or times out, returns a structured error response that the Orchestrator can relay to the engineer.

**Uncertainty Handling**
When the Diagnostic Reasoning Agent cannot determine a probable cause with confidence, it must:
1. Explicitly state the current level of uncertainty and why
2. Suggest the next most informative measurement or check to reduce uncertainty
3. Set `unresolved_flag: true` after 8 or more turns without a probable cause
4. Never fabricate a root cause or assign false confidence to an untested hypothesis

---

### AGT-05: Parameter Interpretation Agent

**Purpose**
Interprets recorded numeric measurements against component-specific reference ranges and tolerances sourced from the knowledge base. Provides structured annotations that inform the Diagnostic Reasoning Agent's hypotheses.

**Responsibilities**
- Extract reference parameter ranges for the current component from the knowledge base (via a deterministic lookup, not a semantic search)
- Compare each recorded measurement value against its reference range
- Classify each measurement as: WITHIN_RANGE, BELOW_MINIMUM, ABOVE_MAXIMUM, or CRITICAL
- Generate a brief natural-language annotation per measurement (e.g., "Brake gap of 1.8 mm exceeds the 0.3–1.5 mm specification; indicates worn brake lining or improper adjustment.")
- Pass the annotated measurement set to the Orchestrator for injection into the Diagnostic Reasoning Agent's system prompt

**Input**
```json
{
  "component_key": "string",
  "measurements": [
    { "parameter": "brake_gap_mm", "value": 1.8, "unit": "mm" }
  ]
}
```

**Output**
```json
{
  "annotated_measurements": [
    {
      "parameter": "brake_gap_mm",
      "value": 1.8,
      "unit": "mm",
      "reference_min": 0.3,
      "reference_max": 1.5,
      "status": "ABOVE_MAXIMUM",
      "annotation": "Brake gap of 1.8 mm exceeds the specified maximum of 1.5 mm. Indicates worn brake lining or incorrect adjustment. Immediate inspection recommended.",
      "critical": false
    }
  ]
}
```

**State Read**: Component parameter specifications from knowledge base (static lookup table).  
**State Written**: None.

**Boundaries**
- Does not generate diagnostic conclusions; it provides measurement context that the Diagnostic Reasoning Agent uses.
- If a parameter has no reference range in the knowledge base, the agent marks it as `status: UNKNOWN_REFERENCE` and passes the raw value without annotation.

---

### AGT-06: Procedure Guidance Agent

**Purpose**
Retrieves and structures step-by-step inspection, adjustment, or repair procedures from the knowledge base for a specific component and task type. Provides numbered, action-oriented instructions.

**Responsibilities**
- Receive a procedure request (e.g., "brake gap adjustment", "insulation resistance test")
- Query the knowledge base for the relevant procedure section using the component key and procedure keyword
- Extract and return a structured numbered procedure list
- Flag if a procedure cannot be found or if it is incomplete in the knowledge base

**Input**
```json
{
  "component_key": "string",
  "procedure_type": "inspection | adjustment | test | replacement"
}
```

**Output**
```json
{
  "procedure_found": true,
  "procedure_title": "string",
  "steps": ["string"],
  "source": "string (document name)",
  "notes": "string | null"
}
```

**State Read**: Knowledge base documents (via ChromaDB or direct text lookup).  
**State Written**: None.

**Collaboration**: The Procedure Guidance Agent is invoked by the Orchestrator when the Diagnostic Reasoning Agent's response indicates that a specific procedure should be presented to the engineer. Its output is injected into the next system prompt turn or displayed directly in the Procedure panel.

---

### AGT-07: Safety / Guardrail Agent

**Purpose**
Evaluates every AI-generated response before delivery to the engineer. Detects safety-critical conditions, physically dangerous recommendations, or out-of-scope content. Ensures that safety warnings are never suppressed and are visually prominent in the UI.

**Responsibilities**
- Scan the Diagnostic Reasoning Agent's response for indicators of safety-critical fault conditions
- Maintain a safety rule set covering: brake failure indicators, structural failure indicators, electrical isolation failure, overload conditions, and legal/regulatory references
- If a safety condition is detected, prepend a structured safety alert block to the response
- Recommend crane shutdown if load-bearing or safety-critical systems are implicated
- Block any response that recommends actions the system is not qualified to advise on (e.g., structural welding repairs, electronic control board modifications beyond the scope of the manual)
- Log all safety flag events to the audit trail

**Input**
```json
{
  "response_text": "string",
  "component_key": "string",
  "session_state": { "current_hypothesis": "string", "likely_causes": ["string"] }
}
```

**Output**
```json
{
  "approved": true,
  "safety_flag": false,
  "safety_level": "none | advisory | warning | critical",
  "safety_message": "string | null",
  "modified_response": "string (original response with prepended safety block if flagged)"
}
```

**State Read**: Safety rule configuration (static; loaded at startup).  
**State Written**: Safety flag events written to audit log (via Orchestrator).

**Boundaries**
- Does not modify diagnostic content; it only prepends safety context.
- Cannot be bypassed or disabled by user role or configuration for active sessions.
- If the Safety Agent itself fails, the Orchestrator must default to blocking the response and returning a generic safety advisory to the engineer.

**Safety Rule Examples**
- Brake gap > 2.0 mm on a load-bearing hoist → CRITICAL
- Insulation resistance < 0.5 MΩ → WARNING (electrical safety risk)
- Motor temperature > 120°C → WARNING
- Any mention of "brake failure" + "lifting load" → CRITICAL (suspend operation)
- Wire rope with visible broken strands exceeding 10% of wires in any lay length → CRITICAL

---

### AGT-08: Report Generation Agent

**Purpose**
Synthesises a complete, structured fault report from the full session transcript, all recorded measurements, and the final session state. Produces a JSON-structured report that is stored persistently and rendered in the dashboard.

**Responsibilities**
- Receive the complete session data: full message history, all measurements with annotations, context snapshot, session state, escalation records, and expert annotations (if any)
- Invoke the Anthropic API to generate a structured JSON report
- Enforce a strict output schema (issue summary, steps taken, root cause, diagnosis, recommendations, severity, follow-up flag)
- Parse and validate the JSON output; fall back to a template-based partial report if the LLM output is malformed
- Store the report linked to the session, crane, component, and generating user
- Transition the session lifecycle state to CLOSED_WITH_REPORT upon successful report storage

**Input**
```json
{
  "session_id": "string",
  "context_snapshot": { ... },
  "message_history": [{ "role": "string", "content": "string" }],
  "measurements": [{ "parameter": "string", "value": "float", "annotation": "string" }],
  "session_state": { "completed_steps": [], "likely_causes": [], "current_hypothesis": "string" },
  "escalation_records": [{ "escalated_by": "string", "reviewed_by": "string", "expert_notes": "string" }],
  "generating_user_id": "string"
}
```

**Output**
```json
{
  "report": {
    "session_id": "string",
    "crane_type": "string",
    "component": "string",
    "issue_summary": "string",
    "steps_taken": ["string"],
    "root_cause": "string",
    "diagnosis": "string",
    "recommendations": ["string"],
    "severity": "critical | high | medium | low",
    "follow_up_required": true,
    "generated_by": "string (user_id)",
    "generated_at": "ISO8601 datetime",
    "agent_version": "string"
  },
  "success": true,
  "errors": []
}
```

**State Read**: Full session record, all messages, all measurements from the database.  
**State Written**: New report record; session lifecycle state → CLOSED_WITH_REPORT.

**Boundaries**
- Does not conduct further diagnosis; it synthesises existing session content.
- Does not modify the knowledge base.
- If the session has no conclusive diagnosis, the report must record root_cause as "undetermined" rather than speculating.

---

### AGT-09: Knowledge Feedback Agent

**Purpose**
Identifies knowledge gaps and recurring fault patterns from closed sessions. Produces structured signals for the Knowledge Engineer dashboard to support knowledge base maintenance.

**Responsibilities**
- Analyse closed sessions where the fault was escalated or remained unresolved before closure
- Identify sessions where the Retrieval Agent returned zero or low-confidence evidence for the component
- Detect recurring fault patterns across multiple sessions for the same crane/component combination
- Generate a structured knowledge gap report: affected component, fault description, gap type (missing procedure, missing parameter range, outdated specification), and suggested knowledge base update
- Flag the session for Knowledge Engineer review and create a knowledge gap record

**Input**
```json
{
  "session_id": "string",
  "retrieval_metadata": { "chunks_returned": 0, "knowledge_gap_indicator": true },
  "session_history": { ... },
  "resolution_status": "UNRESOLVED | ESCALATED | CLOSED_WITH_REPORT"
}
```

**Output**
```json
{
  "gap_detected": true,
  "gap_type": "no_procedure | no_specs | unresolved | low_coverage | missing_manual_info | missing_troubleshooting_step | outdated_knowledge | missing_threshold | unknown_fault",
  "gap_description": "string",
  "suggested_action": "string",
  "fault_pattern": "string | null (only if session resolved with hypothesis)",
  "coverage_score": 0.0,
  "detected_by": "diagnostic_agent",
  "missing_information": "string",
  "affected_asset_type": "string",
  "suggested_file_to_update": "string (e.g. hoist_brake.txt)",
  "suggested_section_or_node": "string (e.g. === DIAGNOSTIC PROCEDURE ===)",
  "evidence_checked": ["doc_id_1", "doc_id_2"],
  "confidence": 0.85
}
```

**State Read**: Closed session records, retrieval metadata, existing knowledge gap records.  
**State Written**: Produces a structured gap record (Orchestrator writes it to `knowledge_gaps` table).

**Gap Type Detection Logic**:
- `unresolved` — lifecycle state is UNRESOLVED/ESCALATED and fewer than 3 steps completed
- `no_specs` — zero KB chunks returned (knowledge_gap_indicator: true)
- `no_procedure` — ≥ 2 gap-indicator phrases in AI response text
- `low_coverage` — coverage score < 0.25 (few specification references in AI responses)

**Component-to-File Mapping**: The agent maps the component key to its corresponding `.txt` knowledge file and the gap type to the relevant section header, enabling the KE to locate the exact update point in the document.

---

## 4. Orchestration Logic

### 4.1 Session Start Pipeline

```
Request: POST /sessions (intake form submission)

1. Orchestrator invokes AGT-02 (Intake Agent)
   → validates intake data
   → produces context_snapshot, component_key

2. Orchestrator invokes AGT-03 (Retrieval Agent)
   → query: problem_description from intake
   → returns initial evidence chunks

3. Orchestrator invokes AGT-04 (Diagnostic Reasoning Agent)
   → context_snapshot + evidence injected into system prompt
   → generates opening diagnostic message
   → no session_update fields expected (first turn)

4. Orchestrator invokes AGT-07 (Safety Agent)
   → evaluates opening message
   → prepends safety block if needed

5. Orchestrator writes session record (state: IN_PROGRESS)
   → persists message, evidence
   → returns response to frontend
```

### 4.2 Chat Turn Pipeline

```
Request: POST /sessions/{id}/chat (engineer sends message)

1. Orchestrator loads full session snapshot from DB

2. Orchestrator invokes AGT-03 (Retrieval Agent)
   → query: component_key + problem_description + latest message
   → returns evidence chunks

3. Orchestrator invokes AGT-05 (Parameter Interpretation Agent)
   → only if new measurements recorded since last turn
   → returns annotated measurements

4. Orchestrator invokes AGT-06 (Procedure Guidance Agent)
   → only if previous AI response indicated a specific procedure
   → returns structured procedure steps

5. Orchestrator assembles system prompt
   → context snapshot + evidence + annotated measurements + procedures + session state

6. Orchestrator invokes AGT-04 (Diagnostic Reasoning Agent)
   → full conversation history + assembled system prompt
   → returns response_text + session_update

7. Orchestrator invokes AGT-07 (Safety Agent)
   → evaluates response_text
   → modifies response if safety flag raised

8. Orchestrator parses session_update from AI response
   → writes completed_steps, likely_causes, current_hypothesis to DB
   → updates lifecycle state if flagged (PROBABLE_CAUSE_IDENTIFIED, UNRESOLVED)

9. Orchestrator persists message, evidence, updated session state
   → returns final response + evidence + session state to frontend
```

### 4.3 Report Generation Pipeline

```
Request: POST /sessions/{id}/report

1. Orchestrator loads full session data from DB

2. Orchestrator invokes AGT-05 (Parameter Interpretation Agent)
   → annotates all measurements for inclusion in report

3. Orchestrator invokes AGT-08 (Report Generation Agent)
   → full session data passed as input
   → returns structured JSON report

4. Orchestrator writes report record to DB
   → transitions session state to CLOSED_WITH_REPORT

5. Orchestrator invokes AGT-09 (Knowledge Feedback Agent)
   → checks for knowledge gaps in the closed session
   → creates knowledge gap record if applicable

6. Returns report to frontend
```

---

## 5. Session State Ownership

| State Field              | Written By                         | Read By                                     |
|--------------------------|------------------------------------|---------------------------------------------|
| `lifecycle_state`        | Orchestrator (based on agent flags)| All agents, all roles via dashboard         |
| `completed_steps`        | Orchestrator ← AGT-04 session_update | AGT-04 (next turn context), dashboard    |
| `likely_causes`          | Orchestrator ← AGT-04 session_update | AGT-04 (next turn context), dashboard    |
| `current_hypothesis`     | Orchestrator ← AGT-04 session_update | AGT-04 (next turn context), dashboard    |
| `messages`               | Orchestrator (persists each turn)  | AGT-04 (full history), reporting, dashboard |
| `measurements`           | Engineer via Measurement endpoint  | AGT-05, AGT-04 (via injection), AGT-08     |
| `evidence_chunks`        | Orchestrator ← AGT-03              | AGT-04 (injected), Evidence panel           |
| `escalation_records`     | Orchestrator (on escalation action)| SME dashboard, AGT-08                       |
| `knowledge_gap_records`  | Orchestrator ← AGT-09              | Knowledge Engineer dashboard                |
| `report`                 | AGT-08 via Orchestrator            | All roles (read-only)                       |

---

## 6. Escalation Handling

When a session is escalated (state → ESCALATED), the following occurs:

1. The Orchestrator records the escalation event: originating user, timestamp, escalation reason (engineer-provided text).
2. The session becomes visible on the Senior Engineer (SME) dashboard.
3. The SME can resume the session: the full conversation history is restored.
4. When the SME sends a message, the same chat turn pipeline runs with the SME's user context. The system prompt is augmented with: the SME role context, all escalation notes, and any expert annotations previously added.
5. The SME can add structured expert annotations outside the chat (via the Annotations panel).
6. If the SME resolves the session, the state transitions to RESOLVED.
7. If the SME identifies a knowledge gap, the state transitions to KNOWLEDGE_GAP_FLAGGED and AGT-09 is invoked.

---

## 7. Uncertainty Handling

| Situation | Agent Behaviour |
|-----------|-----------------|
| Retrieval Agent returns 0 relevant chunks | Returns empty evidence array, sets `knowledge_gap_indicator: true`. Orchestrator signals this to Diagnostic Agent. Diagnostic Agent explicitly acknowledges evidence limitation. |
| Diagnostic Agent cannot identify cause after 8+ turns | Sets `unresolved_flag: true`. Orchestrator transitions state to UNRESOLVED. Engineer is prompted to escalate or record findings and close. |
| Safety Agent detects critical condition | Prepends CRITICAL safety block regardless of diagnostic state. Session cannot progress to CLOSED_WITH_REPORT without engineer acknowledging the safety alert. |
| Report Generation Agent receives malformed LLM JSON | Falls back to extracting fields via regex; marks uncertain fields as "generated with low confidence". Never returns an empty report. |
| Parameter out of reference range but no safety risk | AGT-05 marks as ABOVE_MAXIMUM or BELOW_MINIMUM. AGT-04 uses this to focus diagnosis. AGT-07 evaluates safety implications separately. |

---

## 8. Agent Versioning

Each agent implementation shall carry a version identifier (e.g., `diagnostic_reasoning_agent_v1.0`). The version shall be stored in:
- Every generated report (field: `agent_version`)
- The audit log for each chat turn
- The session record's `agent_metadata` field

This enables comparison between versions during thesis evaluation and supports future regression testing when agent prompts or models are updated.
