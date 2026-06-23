# Complete Test Guide
## AI-Assisted Process Guidance Tool — All Scenarios

> **Who is this for?**
> Anyone testing the tool for the first time — no crane knowledge needed.
> Every answer is pre-written. Just copy, paste, and follow the steps.
>
> **What is covered:**
> - Scenario 1 — ME: Hoist Brake not releasing (Happy Path — problem found and resolved)
> - Scenario 2 — ME: Gearbox grinding noise (Escalation Path — ME escalates to SME)
> - Scenario 3 — SME: Reviews escalated session, adds expert note, flags knowledge gap
> - Scenario 4 — KE: Sees the gap, updates the knowledge base, resolves it
> - Scenario 5 — SUP: Monitoring view — reads all sessions, cannot create one
> - Scenario 6 — ADM: User management and audit log

---

## Before You Start

Open two terminal windows and run:

```bash
# Terminal 1 — Backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2 — Frontend
streamlit run frontend/app.py --server.port 8501
```

Then open your browser at: **http://localhost:8501**

---

## User Accounts

| Role | Full Name | Username | Password |
|------|-----------|----------|----------|
| ME — Field Engineer | Alice | `alice` | `test123` |
| SME — Senior Engineer | Bob | `bob` | `test123` |
| KE — Knowledge Engineer | Demo KE | `demo_ke` | `demo1234` |
| SUP — Supervisor | Demo SUP | `demo_sup` | `demo1234` |
| ADM — Administrator | Carol | `carol` | `test123` |

> If any login fails, run `python3 demo_prep.py` once in the terminal to reset all passwords.

---

---

# SCENARIO 1 — ME: Happy Path
### Component: Hoist Brake

> **Story:** Alice is a field engineer. The crane is powered on and the drive runs but the load does not lift — the hoist drum is not rotating. The fault is in the Hoist Brake. She fills the intake form, follows the AI step by step, discovers the brake coil fuse is blown, replaces it, and generates a fault report.
>
> **Expected result:** Session ends as RESOLVED with a generated fault report.

---

## S1-1 — Log in as Alice

- Username: `alice`
- Password: `test123`
- Click **Login**

**You should see:** The Fault Intake Form loads immediately.

---

## S1-2 — Fill the Intake Form

Copy each value exactly into the matching field:

| Field | Value |
|-------|-------|
| Crane Type | `Generic Crane` |
| Component | `Hoist Brake` |
| Problem Description | `The crane drive runs and I can hear it, but the load does not lift. The hoist drum is not rotating at all. The hoist brake appears to not be releasing.` |
| Environment | `Indoor workshop, normal temperature, no unusual dust or moisture` |
| Recent Changes | `No recent maintenance or changes done to the crane` |
| Error Messages | `No error codes shown. No warning lights on the control panel.` |

Click **Start Troubleshooting →**

**You should see:** The AI Guidance screen opens. An opening message appears in the chat panel on the left. The AI will NOT ask you to repeat the problem — it already knows it from the intake form.

---

## S1-3 — Check the Progress Strip

Look at the top of the chat panel. You will see a progress strip:

`● Intake → Investigation → Root Cause → Resolution`

The first phase is highlighted in blue. This will advance automatically as the diagnosis progresses.

---

## S1-4 — Chat Turn 1

The AI asks what exactly happens when you operate the hoist controls.

**Copy and paste this answer:**
```
The motor starts and I can hear it running. The motor shaft is spinning. But the hoist drum is completely still — it does not turn at all. The load stays on the ground.
```

Click **Send Answers →**

**You should see:** The AI focuses on the brake — it suspects the brake is not releasing.

---

## S1-5 — Chat Turn 2

The AI asks about the brake — whether it releases when the motor runs.

**Copy and paste this answer:**
```
I looked at the brake disc on the motor. It does not appear to move or release when the motor is running. The brake seems to be stuck in the applied position even when I operate the hoist.
```

Click **Send Answers →**

**You should see:** The AI asks for an electrical check — voltage at the brake coil.

---

## S1-6 — Chat Turn 3

The AI asks you to measure the voltage at the brake coil terminals while the motor is running.

**Copy and paste this answer:**
```
I measured the voltage at the brake coil terminals with the motor running. I am reading 0 volts on the brake coil. There is no voltage reaching the brake at all.
```

Click **Send Answers →**

**You should see:** The AI asks you to check the brake circuit fuse and the rectifier that supplies 24VDC to the coil.

---

## S1-7 — Chat Turn 4

The AI asks you to check the fuse protecting the brake coil circuit.

**Copy and paste this answer:**
```
I found the brake circuit fuse in the control panel. It is blown. I can see the fuse element is broken inside the glass tube. The other fuses look normal. I replaced the blown fuse with a new one of the same rating.
```

Click **Send Answers →**

**You should see:** The AI confirms a blown brake circuit fuse as the root cause and asks you to verify the brake now works.

> **Now check the right panel:**
> - Click the **Session State** tab — you will see the hypothesis and completed steps updated automatically.
> - Click the **Evidence** tab — you will see the knowledge chunks retrieved from the hoist brake manual.

---

## S1-8 — Add a Measurement

Click the **Measurements** tab on the right panel.

Click **Add Measurement**.

Fill in:

| Field | Value |
|-------|-------|
| Voltage | `0` |
| Notes | `Measured 0V at brake coil terminals with motor running. Brake circuit fuse found blown. Replaced with new fuse of correct rating. After replacement measured 24V at brake coil — brake now releasing correctly.` |

Click **Save**.

**You should see:** The measurement is recorded under "Recorded This Session".

---

## S1-9 — Chat Turn 5 (Resolution)

**Copy and paste this answer:**
```
After replacing the blown fuse, I tested the hoist again. The brake releases correctly when the motor starts. The drum rotates normally and the load lifts without any problem. The hoist is now working as expected.
```

Click **Send Answers →**

**You should see:** The AI confirms the root cause (blown brake circuit fuse causing brake not to release), summarises the steps taken, and considers the fault resolved.

---

## S1-10 — Generate the Fault Report

Click the **⚡ Generate Report** button at the top right.

Wait 5–15 seconds.

**You should see a structured report with:**
- Issue Summary
- Steps Taken
- Root Cause
- Diagnosis
- Recommendations
- Severity Level

---

## S1-11 — Check the Dashboard

Click **Dashboard** in the navigation bar.

**You should see:** The completed session with its lifecycle state badge and a link to the full report.

> **Scenario 1 complete.** Alice diagnosed a brake-not-releasing fault by systematically following AI guidance, identified a blown fuse in the brake circuit, and generated a traceable fault report.

---

---

# SCENARIO 2 — ME: Escalation Path
### Component: Gearbox

> **Story:** Alice starts a new session for a different crane fault. The gearbox is making a loud grinding noise and is leaking oil. After 4 turns of AI guidance, Alice reaches the limit of what she can check without specialist tools. She escalates to Bob (SME).
>
> **Expected result:** Session lifecycle changes to ESCALATED. Bob receives the full case.

---

## S2-1 — Log in as Alice (or stay logged in)

If Alice is not already logged in:
- Username: `alice` / Password: `test123`

Click **📋 New Issue** in the navigation bar to start a fresh session.

---

## S2-2 — Fill the Intake Form

| Field | Value |
|-------|-------|
| Crane Type | `Generic Crane` |
| Component | `Gearbox` |
| Problem Description | `There is a loud grinding noise coming from the hoist gearbox during every lift operation. The noise started two days ago and is getting worse. There is also visible vibration on the gearbox casing.` |
| Environment | `Indoor workshop. Moderate dust. Operating temperature approximately 30 degrees Celsius.` |
| Recent Changes | `No maintenance done recently. The crane has been in continuous daily use for the past 6 months without any inspection.` |
| Error Messages | `No error codes. No warning lights. The crane still operates but the noise is very loud.` |

Click **Start Troubleshooting →**

---

## S2-3 — Chat Turn 1

The AI asks about the nature of the noise and when exactly it occurs.

**Copy and paste:**
```
The noise is a loud grinding or crunching sound. It happens every time the hoist lifts or lowers a load. The noise is louder under heavy load. It started two days ago and each day it seems to be getting worse and louder.
```

Click **Send Answers →**

---

## S2-4 — Chat Turn 2

The AI asks you to check the gearbox oil level and condition.

**Copy and paste:**
```
I checked the oil sight glass on the gearbox. The oil level is below the minimum mark — the sight glass is almost empty. The oil I can see is very dark brown, almost black. When I opened the drain plug slightly I could see small grey metallic particles in the oil.
```

Click **Send Answers →**

---

## S2-5 — Chat Turn 3

The AI asks about oil leakage and external condition of the gearbox.

**Copy and paste:**
```
I can see oil seeping from the seal around the output shaft on the side of the gearbox. The outside of the gearbox casing is warm to the touch — much warmer than usual. I can also feel strong vibration through the gearbox casing when the crane runs.
```

Click **Send Answers →**

---

## S2-6 — Chat Turn 4

The AI suggests performing an oil sample analysis and internal gear inspection.

**Copy and paste:**
```
I do not have tools for oil analysis here. I cannot open the gearbox safely on my own and I do not have the knowledge to inspect the internal gears or bearings. I am not sure if it is safe to continue operating the crane at all.
```

Click **Send Answers →**

**You should see:** The AI acknowledges the safety concern and recommends stopping crane operation. It indicates that internal gear or bearing inspection is needed by a specialist. Alice has reached the limit of what she can safely do alone.

---

## S2-7 — Escalate the Session

Find the **🚨 Escalate** button at the top of the screen.

Click it. A form appears asking for a reason.

**Copy and paste this escalation reason:**
```
The gearbox has metallic particles in the oil, low oil level, an active oil leak, and is overheating. I cannot perform an oil sample analysis or open the gearbox for internal inspection. The crane may not be safe to operate. I need a senior engineer to assess the severity and advise whether the crane should be taken out of service immediately.
```

Click **Confirm Escalation**.

**You should see:**
- The lifecycle state badge changes to **ESCALATED**
- Alice is told the session has been handed over to a senior engineer

**Log out as Alice.**

---

---

# SCENARIO 3 — SME: Reviews the Escalated Gearbox Session

> **Story:** Bob is the Senior Engineer. He sees Alice's escalated gearbox case in his inbox, reviews the full history, adds an expert annotation, continues the diagnosis with his expertise, and flags a knowledge gap because the AI did not have a specific procedure for gearbox oil analysis.
>
> **Expected result:** Bob adds an annotation. Session moves to SME_IN_REVIEW. Knowledge gap is flagged.

---

## S3-1 — Log in as Bob

- Username: `bob`
- Password: `test123`

**You should see:** Bob's navigation shows **📥 SME Inbox** — no "New Issue" button. This confirms the SME role is for reviewing, not creating new cases.

---

## S3-2 — Open the SME Inbox

Click **📥 SME Inbox** in the navigation bar.

**You should see:** Alice's escalated gearbox session listed with her escalation reason visible.

---

## S3-3 — Open Alice's Session

Click on Alice's session to open it.

**You should see:**
- Alice's complete conversation history (all 4 turns)
- Her escalation reason shown at the top of the SME Actions panel
- Lifecycle state: **ESCALATED**

Bob has the complete diagnostic picture without Alice needing to brief him separately.

---

## S3-4 — Check for Knowledge Gap Warning

Look at the **SME Actions** panel at the top of the chat area.

**You may see** a yellow warning box if the AI reported low confidence during Alice's session:
> *"⚠️ Knowledge gap detected — the AI reported low knowledge base coverage on X message(s)"*

This tells Bob exactly where the knowledge base is weak — in this case, the oil sample analysis procedure.

---

## S3-5 — Accept the Session for Review

Click **🔬 Open for Review** in the SME Actions panel.

**You should see:** Lifecycle state changes to **SME_IN_REVIEW**.

---

## S3-6 — Add an Expert Annotation

Click the **📝 Annotations** tab in the right panel.

Click **Add Annotation**.

Fill in:

| Field | Value |
|-------|-------|
| Annotation Type | `expert_note` |
| Text | `Grey metallic particles in oil combined with low oil level and increasing grinding noise under load is a strong indicator of advanced gear tooth pitting or bearing race damage. The gearbox must be taken out of service immediately — continued operation risks catastrophic failure and load drop. Recommended actions: 1) Stop crane operation now. 2) Drain oil and send sample for laboratory analysis. 3) Remove gearbox cover for visual inspection of gear teeth and bearings. 4) Replace oil with correct ISO VG 220 grade regardless of findings. 5) Contact OEM service if gear damage is confirmed.` |

Click **Save Annotation**.

**You should see:** The annotation appears in the annotations tab with Bob's name and a timestamp.

---

## S3-7 — Continue the Diagnosis as Bob

In the chat input area at the bottom, type:

```
This is the senior engineer taking over. Based on the metallic particles and grinding noise, I am treating this as a critical fault. I am taking the crane out of service now and will perform an oil drain and visual gear inspection today.
```

Click **Send Answers →**

**You should see:** The AI adapts to the senior engineer's input and provides specific next steps for internal inspection and oil change procedure.

---

## S3-8 — Flag the Knowledge Gap

Click **⚠️ Flag Knowledge Gap** in the SME Actions panel.

**You should see:** The session lifecycle changes to **KNOWLEDGE_GAP_FLAGGED**. The Knowledge Engineer (demo_ke) will now see this gap in their dashboard.

---

---

# SCENARIO 4 — KE: Resolves the Gearbox Knowledge Gap

> **Story:** The Knowledge Engineer sees the gap flagged by Bob. The gap is about gearbox oil sample analysis — the knowledge base does not have a specific field procedure for this. The KE writes the missing procedure, saves it, and resolves the gap. Alice and Bob are notified.
>
> **Expected result:** Knowledge base updated. Session returns to IN_PROGRESS. Notifications sent.

---

## S4-1 — Log in as Knowledge Engineer

**Log out as Bob first.**

- Username: `demo_ke`
- Password: `demo1234`

**You should see:** The KE navigation includes **🔍 Knowledge Gaps**.

---

## S4-2 — Open Knowledge Gaps

Click **🔍 Knowledge Gaps** in the navigation bar.

**You should see:** A gap card showing:
- Component: Gearbox
- Description of what the AI could not provide
- The session it came from (Alice's escalated case)

---

## S4-3 — Open the Gap Editor

Click **✏️ Edit & Resolve** on the gap card.

**You should see:** A text editor showing the current content of `gearbox.txt`.

---

## S4-4 — Add the Missing Procedure

Scroll to the bottom of the editor and add this text:

```
=== FIELD OIL SAMPLE PROCEDURE ===

When metallic particles, discolouration, or abnormal gearbox noise are observed,
perform the following field oil check before escalating for laboratory analysis:

TOOLS REQUIRED: Clean sample bottle (500ml), clean funnel, lint-free cloth

PROCEDURE:
1. Stop crane and allow gearbox to cool for 10 minutes (oil settles, particles sink)
2. Place clean container under drain plug
3. Open drain plug slowly — collect first 200ml of oil
4. Reseal drain plug immediately
5. Observe oil sample:
   - Colour: amber/golden = normal | dark brown = oxidised | milky = water ingress
   - Particles: grey metallic = gear/bearing wear | black sludge = severe degradation
   - Smell: burnt smell = overheating

IMMEDIATE STOP criteria (do not operate crane if any of these are present):
- Grey or silver metallic particles visible to naked eye
- Oil level below minimum on sight glass
- Oil temperature above 80 degrees Celsius
- Milky or foamy oil appearance

REPORTING:
Record oil colour, particle description, oil level reading, and gearbox housing
temperature in the session measurements before escalating.
```

Click **💾 Save to Knowledge Base & Resolve Gap**.

**You should see:**
- A success message confirming the gap is resolved and the knowledge base is updated
- Alice and Bob receive a notification (the bell icon at the top shows a new badge)

---

## S4-5 — Verify the Update

The system automatically re-indexes ChromaDB. The next session involving the Gearbox component will include this oil sample procedure in the AI's guidance.

---

---

# SCENARIO 5 — SUP: Monitoring View

> **Story:** The Supervisor logs in to see an overview of all active and completed sessions. They can read everything but cannot create, modify, or chat in any session.
>
> **Expected result:** Supervisor sees all sessions from all engineers. No action buttons are available.

---

## S5-1 — Log in as Supervisor

- Username: `demo_sup`
- Password: `demo1234`

**You should see:**
- Navigation bar shows only **📊 Dashboard** — no New Issue, no SME Inbox
- The dashboard shows sessions from ALL engineers (Alice's hoist brake and gearbox sessions are both visible)

---

## S5-2 — Verify Read-Only Access

Click on any session to open it.

**You should see:** The full session details are visible but there is no chat input box, no escalate button, and no generate report button. The Supervisor can read but cannot act.

---

## S5-3 — Use the Dashboard Filters

On the dashboard, try the lifecycle state filter:
- Select **ESCALATED** — only escalated sessions appear
- Select **CLOSED_WITH_REPORT** — only completed sessions with reports appear

**You should see:** The session list updates based on your filter selection.

> **Scenario 5 complete.** The Supervisor has a full monitoring view across all engineers and all sessions.

---

---

# SCENARIO 6 — ADM: User Management

> **Story:** Carol is the Administrator. She manages user accounts, changes roles, and reviews the audit log of every action taken in the system.
>
> **Expected result:** Carol can change a user's role and verify the audit trail.

---

## S6-1 — Log in as Carol

- Username: `carol`
- Password: `test123`

**You should see:** The navigation bar includes **⚙️ Admin**.

---

## S6-2 — Open the Admin Panel

Click **⚙️ Admin**.

**You should see:** Two tabs — **👥 User Management** and **📋 Audit Log**.

---

## S6-3 — View the User List

Click **👥 User Management**.

**You should see:** A full list of all registered users with their current role assigned.

---

## S6-4 — Change a User Role

Find `alice` in the user list.

Use the role dropdown next to her name to change her role from `ME` to `SME`.

Click **Update Role**.

**You should see:** A confirmation message. Alice is now an SME.

**Change it back to `ME` before finishing** to keep the system consistent for future tests.

---

## S6-5 — View the Audit Log

Click **📋 Audit Log**.

**You should see:** A timestamped record of every action in the system including:
- Login events (alice, bob, demo_ke, demo_sup, carol)
- Session creation (both of Alice's sessions)
- Escalation actions
- Knowledge gap flag and resolution
- Role change you just made

Every action is logged automatically — no manual recording needed.

> **Scenario 6 complete.** The Administrator has full control over users and full visibility into all system actions.

---

---

# Complete Test Checklist

Use this to confirm all scenarios passed.

## Scenario 1 — ME: Hoist Brake Happy Path
- [ ] Alice logged in and reached the intake form
- [ ] Intake form submitted with Hoist Brake component
- [ ] AI guidance screen loaded — AI did NOT ask Alice to repeat the problem
- [ ] Progress strip visible at the top of the chat panel
- [ ] 5 chat turns completed using copy-paste answers
- [ ] Voltage measurement (0V at brake coil) recorded in Measurements tab
- [ ] AI confirmed root cause: blown brake circuit fuse
- [ ] Fault report generated with summary, steps, root cause, recommendations, severity
- [ ] Session visible in Alice's dashboard

## Scenario 2 — ME: Gearbox Escalation Path
- [ ] Alice started a new session with Gearbox component
- [ ] 4 chat turns completed — AI could not provide oil analysis or internal inspection procedure
- [ ] Alice escalated with a clear safety-related reason
- [ ] Session lifecycle changed to ESCALATED

## Scenario 3 — SME: Gearbox Review
- [ ] Bob logged in — no "New Issue" button visible (SME role confirmed)
- [ ] Escalated gearbox session visible in SME Inbox
- [ ] Bob opened the session and saw Alice's full conversation history
- [ ] Knowledge gap warning shown in SME Actions panel (if AI had low confidence)
- [ ] Bob accepted the session → lifecycle changed to SME_IN_REVIEW
- [ ] Bob added an expert annotation with timestamp and his name
- [ ] Bob continued the chat from where Alice left off
- [ ] Bob flagged a knowledge gap → lifecycle changed to KNOWLEDGE_GAP_FLAGGED

## Scenario 4 — KE: Resolves Gearbox Gap
- [ ] KE logged in and saw the gap in Knowledge Gaps screen
- [ ] Gap editor opened showing current gearbox.txt content
- [ ] KE added the oil sample field procedure and saved
- [ ] Success confirmation shown — gap resolved
- [ ] Notifications sent to Alice and Bob (bell icon shows badge)

## Scenario 5 — SUP: Monitoring View
- [ ] Supervisor logged in — only Dashboard visible in navigation
- [ ] Both of Alice's sessions (hoist brake and gearbox) visible in dashboard
- [ ] No chat, escalate, or report buttons available on any session
- [ ] Dashboard filters (lifecycle state) work correctly

## Scenario 6 — ADM: User Management
- [ ] Carol logged in and opened Admin Panel
- [ ] Full user list visible with current roles
- [ ] Alice's role changed to SME and back to ME successfully
- [ ] Audit log shows all actions from all scenarios in order

---

---

# What Each Scenario Demonstrates

| Feature | Scenario |
|---------|----------|
| Structured fault intake form | S1-2, S2-2 |
| AI starts at diagnostic depth — no re-asking | S1-3 |
| Diagnostic progress strip (phase indicator) | S1-3 |
| Structured question widgets (Yes/No, number, choice) | S1-4 to S1-9 |
| AI confidence badge on low-coverage messages | S1-4 onwards |
| Session state tracking (hypothesis, completed steps) | S1-7 |
| Structured measurement recording | S1-8 |
| AI-generated structured fault report | S1-10 |
| Session history and traceability | S1-11 |
| Safety-triggered escalation by ME | S2-6, S2-7 |
| SME Inbox — role-based session visibility | S3-2 |
| Full conversation history preserved for SME review | S3-3 |
| Automatic knowledge gap warning for SME | S3-4 |
| Expert annotation by SME with timestamp | S3-6 |
| Collaborative continuation of diagnosis by SME | S3-7 |
| Knowledge gap flagging by SME | S3-8 |
| KE in-app knowledge base editor | S4-3, S4-4 |
| Automatic re-indexing after knowledge base update | S4-5 |
| Notifications sent to ME and SME after gap resolved | S4-5 |
| Supervisor read-only monitoring of all sessions | S5-1, S5-2 |
| Role-based access control (no New Issue for SUP/SME) | S5-1 |
| Dashboard lifecycle and severity filters | S5-3 |
| Administrator user and role management | S6-3, S6-4 |
| Audit log for compliance and traceability | S6-5 |
