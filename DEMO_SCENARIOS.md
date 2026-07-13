# Demo Scenarios — AI-Assisted Process Guidance Tool
**Master Thesis | RPTU / Fraunhofer IESE | 2025**

These six scenarios are designed for professor review. Each scenario covers a **different crane component**, a **different fault**, and demonstrates a **different system feature**. They are fully independent of each other.

---

## Login Credentials

| Role | Username | Password | Description |
|---|---|---|---|
| Maintenance Engineer | `alice` | `test123` | Field engineer who creates sessions |
| Subject Matter Expert | `bob` | `test123` | Senior engineer who handles escalations |
| Knowledge Engineer | `demo_ke` | `demo1234` | Manages and updates the knowledge base |
| Administrator | `carol` | `test123` | User management and audit log |

---

## Overview of Scenarios

| # | Component | Fault | Feature Demonstrated | Roles |
|---|---|---|---|---|
| 1 | Hoist Brake | Air gap too large | Basic ME workflow — intake → AI guidance → report | ME only |
| 2 | Gearbox | Oil leak from input shaft seal | ME resolves independently, different component | ME only |
| 3 | Limit Switch | Not stopping hoist at upper limit | Escalation — ME escalates to SME, SME resolves | ME + SME |
| 4 | Hoist Motor | Trips circuit breaker under load | Escalation with measurement-based diagnosis | ME + SME |
| 5 | Power Supply | Unknown fault code F-21 on UPS | KB Gap lifecycle — auto-detection → SME flags → KE update → resolution | ME + SME + KE |
| 6 | Control System | PLC program corrupted after power surge | SME manually identifies missing KB procedure → KE adds it → all roles notified | ME + SME + KE |

---

---

## Scenario 1: Hoist Brake — Air Gap Too Large

**Feature:** Basic ME workflow (Intake → AI Guidance → Report)
**Roles needed:** ME only
**Login:** alice / test123
**Time to complete:** ~5 minutes

### What this demonstrates
- ME fills in the intake form and the AI immediately starts diagnosis
- AI asks one simple question at a time, progressing from visual to measurement checks
- ME provides measurements, AI compares to knowledge base values
- Session ends with a generated fault report

### Intake Form — fill in exactly as shown

| Field | Value |
|---|---|
| Crane Type | `Demag EKKE 5t` |
| Component | `Hoist Brake` |
| Problem Description | `Hoist brake is not releasing properly. The drum is slow to start and the brake feels stiff when the hoist is switched on.` |
| Environment | `Indoor workshop, normal temperature` |
| Recent Changes | `Brake pads were replaced 3 weeks ago` |
| Error Messages | *(leave blank)* |

### Conversation Guide

**Turn 1 — AI asks about visual condition of the brake**
→ Reply: `The brake disc looks fine, no visible cracks or damage`

**Turn 2 — AI asks whether the brake releases when the hoist is switched on**
→ Reply: `Yes it releases but very slowly, takes about 3 seconds to fully open`

**Turn 3 — AI asks to measure the brake air gap**
→ Reply: `I measured the air gap with a feeler gauge — it is 0.5 mm`

**Turn 4 — AI identifies the fault**
The AI will state that the air gap is too large (specification: 0.2–0.3 mm) and recommend adjustment.

**Final step:** Click **Generate Report**. Review the automatically created fault report in the Dashboard.

### Expected system behaviour
- No yellow banner (Hoist Brake is well covered in the knowledge base)
- AI references the brake air gap specification from the KB
- Report includes: root cause, steps taken, recommended action

---

---

## Scenario 2: Gearbox — Oil Leak from Input Shaft Seal

**Feature:** ME resolves independently, no escalation needed
**Roles needed:** ME only
**Login:** alice / test123
**Time to complete:** ~5 minutes

### What this demonstrates
- A different component (Gearbox) with a straightforward mechanical fault
- AI follows simple-to-complex logic: visual → location → severity → oil level
- Diagnosis reached in 3–4 turns without any escalation

### Intake Form

| Field | Value |
|---|---|
| Crane Type | `Demag EKKE 5t` |
| Component | `Gearbox` |
| Problem Description | `Oil puddle found under the gearbox at the start of shift. Oil level is dropping.` |
| Environment | `Indoor production hall` |
| Recent Changes | `None` |
| Error Messages | *(leave blank)* |

### Conversation Guide

**Turn 1 — AI asks where the oil is coming from**
→ Reply: `The oil is leaking from the seal between the motor shaft and the gearbox housing`

**Turn 2 — AI asks how severe the leak is**
→ Reply: `It is a slow drip, about 5 to 6 drops per minute`

**Turn 3 — AI asks about oil level**
→ Reply: `Oil level is about 20% below the minimum mark on the sight glass`

**Turn 4 — AI identifies the fault**
The AI will diagnose input shaft seal failure and recommend seal replacement and oil top-up before returning the crane to service.

**Final step:** Click **Generate Report**.

### Expected system behaviour
- No yellow banner
- AI asks simple, direct questions about what the engineer can see
- Report lists: seal failure as root cause, safety recommendation to not operate until repaired

---

---

## Scenario 3: Limit Switch — Not Stopping Hoist at Upper Limit

**Feature:** Escalation from ME to SME — SME takes over and resolves
**Roles needed:** ME (alice) then SME (bob)
**Time to complete:** ~8 minutes

### What this demonstrates
- ME starts the session, does basic checks, but cannot complete the diagnosis alone
- ME escalates the session to SME using the Escalate button
- SME sees the session in their Inbox and takes over
- SME continues the AI conversation and reaches a diagnosis
- This is a safety-critical fault — hoist not stopping is dangerous

### PART A — ME Creates and Escalates (login: alice / test123)

#### Intake Form

| Field | Value |
|---|---|
| Crane Type | `Demag EKKE 5t` |
| Component | `Limit Switch` |
| Problem Description | `Upper hoist limit switch is not stopping the hoist. The hoist continues to travel past the safe upper position.` |
| Environment | `Outdoor loading bay` |
| Recent Changes | `New rope drum was installed last week` |
| Error Messages | *(leave blank)* |

#### ME Conversation Guide

**Turn 1 — AI asks about physical condition of the switch**
→ Reply: `The limit switch actuator arm looks intact and is correctly positioned`

**Turn 2 — AI asks if the switch clicks when pressed by hand**
→ Reply: `Yes, I can hear it click when I press the arm manually`

**Turn 3 — AI asks about wiring or recent changes**
→ Reply: `I am not sure about the wiring and I do not have an electrical multimeter with me`

**ME Escalation step:**
Click the **Escalate to SME** button.
Enter reason: `I have completed the visual checks. The switch clicks manually but still does not stop the hoist. Need electrical diagnosis.`

---

### PART B — SME Takes Over (logout alice, login: bob / test123)

1. Go to **SME Inbox** — find the escalated session
2. Click **Take Over Session** → the AI continues from where ME left off

#### SME Conversation Guide

**Turn 4 — AI asks to check voltage across the limit switch contacts**
→ Reply: `Measured 0 V across the contacts when the switch is pressed — circuit is open`

**Turn 5 — AI asks to check continuity between the switch and the control panel**
→ Reply: `Continuity test shows a break in the wire between the switch and the control panel terminal`

**Turn 6 — AI identifies the fault**
The AI will diagnose a broken wire in the limit switch circuit caused by damage during the rope drum installation. Recommend re-routing and reconnecting the wire.

**Final step (bob):** Click **Generate Report**.

### Expected system behaviour
- Alert style changes when the safety-critical nature is mentioned
- SME Inbox shows the escalated session with reason
- Session state shows ESCALATED → SME_IN_REVIEW → transition recorded

---

---

## Scenario 4: Hoist Motor — Trips Circuit Breaker Under Load

**Feature:** Escalation with measurement-based electrical diagnosis
**Roles needed:** ME (alice) then SME (bob)
**Time to complete:** ~8 minutes

### What this demonstrates
- A different fault type (electrical overcurrent) that requires current measurement
- ME does initial checks, escalates when measurements are needed
- SME takes motor current readings and the AI interprets them against KB values
- Shows the measurement recording feature in the right-side panel

### PART A — ME Creates and Escalates (login: alice / test123)

#### Intake Form

| Field | Value |
|---|---|
| Crane Type | `Demag EKKE 5t` |
| Component | `Hoist Motor` |
| Problem Description | `Circuit breaker trips within 2 seconds every time the hoist is started under load. Hoist works fine with no load.` |
| Environment | `Indoor steel plant, dusty environment` |
| Recent Changes | `None in the past month` |
| Error Messages | *(leave blank)* |

#### ME Conversation Guide

**Turn 1 — AI asks when exactly the breaker trips**
→ Reply: `It trips within 2 seconds of starting when there is a load on the hook`

**Turn 2 — AI asks about motor temperature**
→ Reply: `The motor is slightly warm but not hot to touch`

**Turn 3 — AI asks to check the breaker rating**
→ Reply: `I am not sure of the breaker rating and I do not have current measurement tools`

**ME Escalation step:**
Click **Escalate to SME**.
Reason: `Motor trips under load only. No visible damage. Need current measurement for further diagnosis.`

---

### PART B — SME Takes Over (login: bob / test123)

#### SME Conversation Guide

**Turn 4 — AI asks for motor current at no load**
→ Use the **Add Measurement** tab on the right side to record:
  - Current: `4.5 A`
→ Tell AI: `Current at no load is 4.5 A`

**Turn 5 — AI asks for motor current at 50% load**
→ Add Measurement: Current `18.2 A`
→ Reply: `Current at 50% load is 18.2 A`

**Turn 6 — AI interprets the measurements**
The AI will identify that 18.2 A far exceeds the rated motor current and will suspect a motor winding fault causing excessive current draw under load.

**Turn 7 — AI recommends**
Winding resistance test on each phase and motor inspection. If winding fault confirmed, motor replacement required.

**Final step (bob):** Click **Generate Report**.

### Expected system behaviour
- Measurements panel on the right shows recorded values
- AI immediately interprets each measurement against rated values from the KB
- Report includes measurements summary section

---

---

## Scenario 5: Power Supply — Unknown UPS Fault Code F-21

**Feature:** Full KB Gap lifecycle — automatic detection → SME flags → KE updates → ME resolves
**Roles needed:** ME (alice), SME (bob), KE (demo_ke / demo1234)
**Time to complete:** ~12 minutes
**This is the most important scenario — it demonstrates the knowledge management cycle.**

### What this demonstrates
1. System automatically detects that F-21 is not in the knowledge base (yellow banner)
2. AI honestly says it does not know what F-21 means
3. ME escalates to SME
4. SME flags a knowledge gap and records what information is missing
5. KE (Knowledge Engineer) reviews the gap and adds the correct information to the KB
6. Yellow banner disappears, replaced by green "Knowledge base updated" banner
7. ME can now get correct guidance

---

### PART A — ME Creates Session (login: alice / test123)

#### Intake Form

| Field | Value |
|---|---|
| Crane Type | `Generic Crane` |
| Component | `Power Supply` |
| Problem Description | `Crane will not start. Control panel shows READY but crane does not respond. UPS unit on the panel is showing fault code F-21.` |
| Environment | `Indoor warehouse` |
| Recent Changes | `None` |
| Error Messages | `F-21` |

#### What to look for immediately after submitting
- A **yellow warning banner** at the top of the guidance screen:
  `⚠️ Low knowledge base coverage detected — the system may not have full information for this fault`
- The AI will state that fault code **F-21 is not documented** in the knowledge base

#### ME Conversation

**Turn 1** — AI says F-21 is not in the knowledge base and cannot be interpreted
→ Reply: `I checked the UPS unit and it is showing F-21 on the display. The UPS has been in service for 4 years.`

**Turn 2** — AI recommends escalation since it lacks the fault code definition

**ME Escalation step:**
Click **Escalate to SME**.
Reason: `AI could not identify fault code F-21 from UPS. Need SME with manufacturer documentation.`

---

### PART B — SME Reviews and Flags KB Gap (login: bob / test123)

1. Go to **SME Inbox** → open the escalated session
2. Click **Take Over Session**

**Turn 3 — SME has manufacturer documentation**
→ Reply: `I checked the UPS manufacturer manual. F-21 means Battery Overtemperature fault. Battery temperature exceeded 40°C. Normal operating range is 15–35°C.`

**SME Flags Knowledge Gap:**
- Click the **Flag Knowledge Gap** button
- In the text box, enter:
  `Fault code F-21 on this UPS model indicates Battery Overtemperature. The battery temperature has exceeded the safe operating limit of 35°C. Engineer should check battery ventilation, ambient temperature, and replace the battery if swollen or damaged.`
- Click Submit

---

### PART C — KE Updates the Knowledge Base (login: demo_ke / demo1234)

1. Go to **KB Gaps** tab in the left navigation
2. Find the gap for Power Supply / F-21
3. Click **View Session** to review the context (optional)
4. Click **Update & Resolve**
5. Fill in:
   - **Resolution Note:** `Added F-21 fault code definition from UPS manufacturer manual`
   - **Content to Add to KB:** `UPS Fault Code F-21 — Battery Overtemperature: This fault triggers when the UPS battery temperature exceeds 35°C. Check battery compartment ventilation, ensure ambient temperature is within 15–35°C range, and inspect battery for swelling or damage. Battery replacement required if temperature persists above threshold.`
6. Click **Resolve & Update KB**

---

### PART D — ME Continues with Updated Knowledge (login: alice / test123)

1. Go to **Dashboard** → open the Power Supply session
2. The **yellow banner is now replaced** by a green banner:
   `✅ Knowledge base updated — new information has been added for this component`
3. Continue the conversation — the AI now knows about F-21
4. Reply to any AI question, and the AI will now give correct guidance on battery overtemperature
5. Click **Generate Report**

### Expected system behaviour summary

| Step | What you see |
|---|---|
| Session created | ⚠️ Yellow banner appears |
| AI response | "F-21 is not documented in this knowledge base" |
| SME flags gap | Gap record created in KB Gaps tab |
| KE resolves gap | KB file updated, ChromaDB re-indexed |
| ME re-opens session | ✅ Green banner replaces yellow |
| AI response | Correct F-21 guidance now provided |

---

---

## Scenario 6: Control System — PLC Program Corrupted After Power Surge

**Feature:** SME manually identifies a missing KB procedure → KE adds it → ME and SME receive bell notifications
**Roles needed:** ME (alice), SME (bob), KE (demo_ke / demo1234)
**Time to complete:** ~12 minutes

### How this is different from Scenario 5
- Scenario 5: System **automatically** detects the KB gap (yellow banner) because a fault code was not indexed
- Scenario 6: The KB gap is **manually identified by the SME** during diagnosis — the SME finds that the knowledge base has the fault description but **no restore procedure** for a corrupted PLC program

This demonstrates two different ways the knowledge gap mechanism can be triggered in the system.

### What this demonstrates
1. ME finds the crane completely unresponsive after a power outage overnight
2. ME does basic checks from the KB (isolator, fuses, E-stop) and escalates
3. SME takes over, identifies the PLC CPU fault, but finds no backup/restore procedure in the KB
4. SME manually flags the gap, describing exactly what procedure is missing
5. KE adds the PLC restore procedure to the knowledge base
6. ME and SME both receive an in-app notification (bell icon)
7. SME continues with the correct procedure and generates the report

---

### PART A — ME Creates Session and Escalates (login: alice / test123)

#### Intake Form

| Field | Value |
|---|---|
| Crane Type | `Demag EKKE 5t` |
| Component | `Control System` |
| Problem Description | `Crane is completely unresponsive this morning. There was a power outage overnight. The control panel is powered on but the crane does not respond to any pendant commands. The PLC CPU LED is red.` |
| Environment | `Indoor factory, normal temperature` |
| Recent Changes | `Power outage occurred overnight — power restored this morning` |
| Error Messages | `PLC CPU LED red` |

#### ME Conversation Guide

**Turn 1 — AI asks about main isolator and incoming power**
→ Reply: `Main isolator is ON. I checked incoming voltage — all 3 phases are present at 400V`

**Turn 2 — AI asks about the E-stop buttons**
→ Reply: `All E-stop buttons are released and pulled out. Safety relay shows no fault`

**Turn 3 — AI asks about control transformer output voltage**
→ Reply: `Control voltage reads 24V DC — that is normal`

**Turn 4 — AI asks about PLC status LEDs**
→ Reply: `The PLC CPU LED is solid red. The RUN LED is off. The BATT LED is green. The PLC is not running any program.`

**ME Escalation step:**
PLC CPU fault after a power surge is beyond ME capability to fix alone.

Click **Escalate to SME**.
Reason: `PLC CPU LED is red and crane is not running. All power and E-stop checks are normal. Suspect PLC program was lost or corrupted during the power surge. Need SME to restore the PLC program.`

---

### PART B — SME Reviews and Flags KB Gap (login: bob / test123)

1. Go to **SME Inbox** → find the escalated session
2. Click **Take Over Session**

#### SME Conversation Guide

**Turn 5 — AI confirms PLC CPU fault and asks SME to check the PLC diagnostics**
→ Reply: `I accessed the PLC programming terminal. The CPU is in STOP mode and the program memory shows a checksum error — the program has been corrupted. I need to restore the backup program.`

**Turn 6 — AI tries to provide a restore procedure**
The AI will mention that the PLC has a program fault but the knowledge base does not contain a step-by-step backup/restore procedure for this PLC type.

→ Reply: `I cannot find a PLC program restore procedure in the system. What are the steps to reload the program from backup?`

**SME Flags Knowledge Gap:**
Click the **Flag Knowledge Gap** button.
In the text box, enter:
`The knowledge base documents the PLC CPU fault (red LED) but contains no procedure for restoring a corrupted or lost PLC program from backup. Engineers need step-by-step instructions for: (1) connecting to the PLC via programming software, (2) loading the backup program file, (3) verifying the program after restore, and (4) returning the crane to service safely. This situation occurs after power surges and is likely to happen again.`

Click **Submit**.

---

### PART C — KE Adds the Restore Procedure (login: demo_ke / demo1234)

1. Go to **KB Gaps** tab in the left navigation
2. Find the gap: *Control System — PLC program backup/restore procedure missing*
3. Click **View Session** to read the context (optional)
4. Click **Update & Resolve**
5. Fill in:

**Resolution Note:**
`Added PLC program backup and restore procedure for Siemens S7-300 series PLC used on Demag cranes`

**Content to Add to KB:**
```
PLC Program Restore Procedure (After Power Surge or Program Corruption)

Pre-condition: PLC CPU LED is red, crane is in STOP mode, program memory fault confirmed.

Required: Laptop with SIMATIC Manager or TIA Portal software, backup program file (.s7p or .ap15), USB/MPI/PROFIBUS cable.

Step 1 — Connect to PLC
  - Connect laptop to PLC using MPI cable (port on front of CPU module)
  - Open SIMATIC Manager → accessible nodes → confirm CPU is visible

Step 2 — Put CPU in STOP mode (if not already)
  - Right-click CPU → Operating Mode → STOP
  - CPU LED should be solid yellow

Step 3 — Load backup program
  - File → Retrieve → select the backup .s7p file from the designated backup folder
  - Right-click the program blocks → Download to Module → confirm overwrite

Step 4 — Verify program integrity
  - Compare: Program → Module → Compare → confirm all blocks match
  - Check I/O assignments have not changed

Step 5 — Restart CPU
  - Right-click CPU → Operating Mode → RUN
  - CPU LED should go solid green within 10 seconds

Step 6 — Functional test before returning to service
  - Test each axis at low speed with no load
  - Confirm all limit switches respond correctly
  - Confirm E-stop chain is functional
  - Record restore date, backup file used, and test results in maintenance log

NOTE: Backup program files are stored on the shared drive at: \\server\crane-plc-backups\
Contact the electrical supervisor if backup files are not available.
```

6. Click **Resolve & Update KB**

---

### PART D — ME and SME Receive Notification (login: alice / test123 or bob / test123)

1. Log back in as alice or bob
2. Check the **bell icon** in the top navigation bar — unread notification badge is visible
3. Click the bell → notification reads:
   `Knowledge base updated: Control System — PLC program backup/restore procedure has been added by the Knowledge Engineer.`
4. Click **Mark as Read**

---

### PART E — SME Completes the Session (login: bob / test123)

1. Go back to the Control System session
2. Continue the conversation — the AI now has the restore procedure

**Turn 7 — SME confirms restore was successful**
→ Reply: `I followed the restore procedure. Connected to PLC via MPI, loaded the backup from the shared drive, downloaded the program. CPU is now in RUN mode — green LED.`

**Turn 8 — AI asks about functional test**
→ Reply: `Ran functional test on all axes with no load. All limit switches responding correctly. E-stop confirmed working. Crane is ready for service.`

**Turn 9 — AI confirms resolution**
The AI will confirm the root cause (power surge corrupted PLC program) and that the crane has been successfully restored and tested.

**Final step (bob):** Click **Generate Report**.

### Expected system behaviour summary

| Step | What you see |
|---|---|
| ME creates session | No yellow banner (Control System is in KB) |
| ME escalates | Session moves to ESCALATED state |
| SME identifies gap | SME manually clicks Flag Knowledge Gap |
| Gap form | SME writes description of missing procedure |
| KE resolves | KB file updated with PLC restore procedure |
| alice/bob logs in | Bell icon shows unread notification badge |
| Notification | "Knowledge base updated — PLC restore procedure added" |
| SME continues | AI now provides the restore procedure from KB |
| Report generated | Includes root cause: power surge + PLC program corruption |

---

### Key difference from Scenario 5 — for the professor review

| | Scenario 5 (Power Supply) | Scenario 6 (Control System) |
|---|---|---|
| Gap detection | **Automatic** — system detects low KB coverage (yellow banner at session start) | **Manual** — SME reads the KB mid-diagnosis and identifies a missing procedure |
| Trigger | Missing fault code (F-21 not indexed) | Missing procedure (PLC restore steps not documented) |
| Who flags | SME (prompted by yellow banner) | SME (proactive, based on domain knowledge) |
| Notification | ME gets notified when KE resolves | ME **and** SME both get notified |
| Visual indicator | Yellow banner → Green banner | Bell notification badge |

---

---

## Tips for the Demo

- **Start fresh:** Delete any existing sessions from the Dashboard before presenting, so each scenario starts clean.
- **Show the Dashboard** after each scenario — the lifecycle state progression (IN_PROGRESS → CLOSED_WITH_REPORT) is visible there.
- **Show the Report** after generating it — click the session in the Dashboard to expand the report card.
- **For Scenarios 5 and 6**, make sure to log in and out of different roles to show the multi-role nature of the system.
- **KB Gaps tab** is only visible to KE and SME roles — show this by logging in as bob (SME) first, then demo_ke (KE).
- **Notifications (bell icon)** are best demonstrated in Scenario 6 — both ME and SME receive a notification when KE resolves the gap.
- **Scenario 5 vs Scenario 6** show two different ways knowledge gaps are discovered: automatic (system-detected, yellow banner) vs manual (SME-identified, bell notification).
- **Admin Panel** (carol / test123) can be shown separately to demonstrate user management and the audit log.
