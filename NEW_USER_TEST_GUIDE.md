# New User Test Guide
## AI-Assisted Process Guidance Tool — Crane Maintenance
**Master's Thesis | RPTU / Fraunhofer IESE | 2025**

> This guide is written for someone who has **never used this system before**.
> Follow the steps in order. Each scenario takes 5–10 minutes.
> You do not need any crane knowledge — just follow the instructions exactly.

---

## Before You Start — Setup Checklist

Complete this once before running any scenario.

- [ ] **Clone the repository**
  ```bash
  git clone https://github.com/Rutuja5397/Process-Guidance.git
  cd Process-Guidance
  git checkout v2-implementation
  ```

- [ ] **Create a virtual environment and install packages**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate          # Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  ```

- [ ] **Set your Anthropic API key**
  ```bash
  cp .env.example .env
  ```
  Open `.env` and replace `your_anthropic_api_key_here` with your real key:
  ```
  ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxx
  ```
  > Get a free key at: https://console.anthropic.com

- [ ] **Create demo user accounts**
  ```bash
  python3 demo_prep.py
  ```
  You should see: `✓ Demo users created successfully`

- [ ] **Start the application**
  ```bash
  ./start.sh
  ```
  Wait until you see both:
  - `Uvicorn running on http://127.0.0.1:8000`
  - `You can now view your Streamlit app in your browser`

- [ ] **Open the app in your browser**
  ```
  http://localhost:8501
  ```
  You should see a login screen.

---

## Login Accounts

Use these accounts throughout the scenarios. Do not change the passwords.

| Role | Username | Password | Who They Are |
|------|----------|----------|--------------|
| Maintenance Engineer | `alice` | `test123` | Field engineer on the shop floor |
| Subject Matter Expert | `bob` | `test123` | Senior engineer who handles complex faults |
| Knowledge Engineer | `demo_ke` | `demo1234` | Manages and updates the knowledge base |
| Supervisor | `demo_sup` | `demo1234` | Read-only view of all sessions |
| Administrator | `carol` | `test123` | User management |

---

## How the System Works (30-second overview)

```
1. Engineer fills in an INTAKE FORM (crane type, component, fault description)
        ↓
2. AI reads the form and starts asking DIAGNOSTIC QUESTIONS one at a time
        ↓
3. Engineer answers each question (Yes/No buttons, number inputs, text)
        ↓
4. AI narrows down the fault and asks for MEASUREMENTS when needed
        ↓
5. Engineer clicks GENERATE REPORT → structured fault report is created
```

The AI only uses knowledge from the built-in technical manuals.
If something is not in the manuals, the AI will say so (knowledge gap).

---

---

## Scenario 1 — Basic Fault Diagnosis (ME only)
**Component:** Hoist Brake | **Fault:** Brake air gap too large
**Roles:** Maintenance Engineer only
**Time:** ~5 minutes
**What this tests:** Standard intake → AI guidance → report workflow

---

### Step 1 — Log in as Alice (ME)
- Open `http://localhost:8501`
- Username: `alice` | Password: `test123`
- You will land on the **Dashboard**

### Step 2 — Start a new session
- Click **New Session** or **Start Troubleshooting**
- Fill in the intake form exactly as shown:

| Field | Enter This |
|-------|-----------|
| Crane Type | `Demag EKKE 5t` |
| Component | `Hoist Brake` |
| Problem Description | `Hoist brake is not releasing properly. The drum is slow to start and the brake feels stiff when the hoist is switched on.` |
| Environment | `Indoor workshop, normal temperature` |
| Recent Changes | `Brake pads were replaced 3 weeks ago` |
| Error Messages | *(leave blank)* |

- Click **Submit**

### Step 3 — Follow the AI diagnosis

The AI will open with a summary and ask its first question.
Answer each question using the buttons or input fields provided.

| AI Question | Your Answer |
|-------------|-------------|
| Is the brake disc visually damaged or cracked? | **No** |
| Does the brake release when the hoist is switched on? | **Yes, but slowly — takes about 3 seconds** |
| What is the brake air gap? (in mm) | **0.5** |

After the third answer, the AI will identify the fault:
> *"The measured air gap of 0.5 mm exceeds the specification of 0.2–0.3 mm. The brake requires adjustment."*

### Step 4 — Generate the fault report
- Click **Generate Report**
- A structured report appears with: root cause, steps taken, recommended action, severity

### What to check ✓
- [ ] No yellow warning banner appeared (brake is well-covered in the KB)
- [ ] AI cited a specific value ("0.2–0.3 mm") — this comes from the knowledge base
- [ ] The structured question widgets appeared (not just a text box)
- [ ] The fault report was generated successfully

---

---

## Scenario 2 — Different Component, ME Works Alone
**Component:** Gearbox | **Fault:** Oil leak from input shaft seal
**Roles:** Maintenance Engineer only
**Time:** ~5 minutes
**What this tests:** Different component, different KB file, measurement interpretation

---

### Step 1 — Stay logged in as Alice, start a new session
- Click **New Session**

### Step 2 — Fill in the intake form

| Field | Enter This |
|-------|-----------|
| Crane Type | `Overhead Bridge Crane 10t` |
| Component | `Gearbox` |
| Problem Description | `Oil leak visible under the gearbox near the input shaft. Grinding noise when hoisting at full load.` |
| Environment | `Outdoor, exposed to temperature variation` |
| Recent Changes | `None` |
| Error Messages | *(leave blank)* |

### Step 3 — Answer the AI questions

| AI Question | Your Answer |
|-------------|-------------|
| Is oil visibly dripping or just a stain? | **Actively dripping** |
| What is the current oil level? (check sight glass) | **Below the minimum mark** |
| Describe the grinding noise — constant or only under load? | **Only when hoisting, gets worse under full load** |

### Step 4 — Generate the report

### What to check ✓
- [ ] AI recommended checking oil level as a first step (simple before complex)
- [ ] AI cited the correct oil grade (ISO VG 220) from the knowledge base
- [ ] Grinding noise was linked to low oil level — logical fault chain
- [ ] Report generated with root cause: worn input shaft seal + low oil level

---

---

## Scenario 3 — Escalation from ME to SME
**Component:** Limit Switch | **Fault:** Upper limit not stopping the hoist
**Roles:** Alice (ME) starts → Bob (SME) continues
**Time:** ~8 minutes
**What this tests:** Escalation workflow — session transfers between roles

---

### Part A — Alice (ME) starts the session

#### Intake form

| Field | Enter This |
|-------|-----------|
| Crane Type | `Demag EKKE 5t` |
| Component | `Limit Switch` |
| Problem Description | `Upper travel limit switch is not stopping the hoist. Hook block travels past the top limit position.` |
| Environment | `Indoor` |
| Recent Changes | `Limit switch was adjusted last month` |
| Error Messages | *(leave blank)* |

#### Answer 2 questions from the AI

| AI Question | Your Answer |
|-------------|-------------|
| Is the limit switch actuator arm visually intact? | **Yes, looks fine** |
| Does the switch click when you manually press it? | **I am not sure, I need a senior engineer to check the wiring** |

#### Escalate to SME
- Click the **Escalate to SME** button
- Add a note: `Need SME to check switch wiring and cam adjustment`
- Click **Confirm Escalation**
- Log out of Alice's account

---

### Part B — Bob (SME) takes over

- Log in as `bob` / `test123`
- Go to **Dashboard** — you will see Alice's escalated session
- Open it and click **Take Over Session**

#### Answer 2 more questions from the AI

| AI Question | Your Answer |
|-------------|-------------|
| Measure continuity across the limit switch contacts — open or closed? | **Open (no continuity) — switch contacts are stuck open** |
| Has the cam actuator position shifted from the set point? | **Yes, it moved about 5mm from the marked position** |

#### The AI identifies the root cause:
> *"The cam actuator has shifted out of position, preventing the switch from closing. Reset the cam to the factory-marked position and verify continuity."*

- Click **Generate Report**

### What to check ✓
- [ ] Session appeared in Bob's dashboard after Alice escalated
- [ ] Bob saw Alice's full conversation history
- [ ] Session status changed from `IN_PROGRESS` → `ESCALATED` → `SME_IN_REVIEW`
- [ ] Report was generated by Bob after resolving

---

---

## Scenario 4 — Escalation with Measurement Recording
**Component:** Hoist Motor | **Fault:** Circuit breaker trips under full load
**Roles:** Alice (ME) → Bob (SME)
**Time:** ~8 minutes
**What this tests:** Measurement panel, SME annotation, threshold interpretation

---

### Part A — Alice (ME)

#### Intake form

| Field | Enter This |
|-------|-----------|
| Crane Type | `Demag EKKE 5t` |
| Component | `Hoist Motor` |
| Problem Description | `Circuit breaker trips after approximately 10 minutes of operation under full rated load. Motor feels hot to the touch.` |
| Environment | `Hot environment, ambient temp around 35°C` |
| Recent Changes | `None` |
| Error Messages | *(leave blank)* |

#### Answer questions and record a measurement

| AI Question | Your Answer |
|-------------|-------------|
| Has the motor been running more frequently than normal today? | **Yes, continuous use for 3 hours** |
| What is the motor surface temperature? (use infrared thermometer, in °C) | **92** |

> When the AI asks for a measurement (temperature, voltage, current):
> Use the **Record Measurement** button in the right panel to log it formally.
> Enter `92` in the temperature field and click Save.

#### Escalate to SME
- Add note: `Motor surface temp 92°C — above what I can safely diagnose`
- Escalate

---

### Part B — Bob (SME)

- Log in as `bob`, open the escalated session

| AI Question | Your Answer |
|-------------|-------------|
| What is the motor duty cycle rating (S-rating on the nameplate)? | **S3 40%** |
| What is the insulation resistance between phase and earth? (in MΩ) | **12** |

> Record insulation resistance: 12 MΩ in the measurement panel

- AI will conclude: motor operated beyond rated duty cycle causing thermal overload
- Click **Generate Report**
- As SME, add an **Expert Annotation**: `Recommend enforcing 40% duty cycle — maximum 24 minutes on, 60 minutes off`

### What to check ✓
- [ ] Measurement panel recorded temperature and insulation resistance
- [ ] AI compared 92°C against the KB thermal limit
- [ ] SME annotation was added to the session
- [ ] Measurements appear in the generated report

---

---

## Scenario 5 — Automatic Knowledge Gap Detection
**Component:** Power Supply | **Fault:** Unknown fault code F-21
**Roles:** Alice (ME) → Bob (SME) → demo_ke (KE)
**Time:** ~10 minutes
**What this tests:** Automatic KB gap detection, yellow banner, gap resolution

> **This is the most important scenario for the thesis.**
> It shows what happens when the AI does not know something.

---

### Part A — Alice (ME) triggers the KB gap

#### Intake form

| Field | Enter This |
|-------|-----------|
| Crane Type | `Overhead Bridge Crane 10t` |
| Component | `Power Supply` |
| Problem Description | `UPS unit showing fault code F-21 on the display panel. Control system is not powering up.` |
| Environment | `Indoor substation` |
| Recent Changes | `UPS battery replaced 2 months ago` |
| Error Messages | `F-21` |

#### What you will see immediately after submitting:
> A **yellow warning banner** appears at the top of the chat panel:
> *"Knowledge gap detected: the knowledge base may not fully cover this fault."*

This banner appears because the system detected (via cosine similarity score < 0.45) that the knowledge base does not have documentation for fault code F-21.

#### AI response:
The AI will say something like:
> *"Error code F-21 is not documented in this system's knowledge base. This is a knowledge gap — please escalate so the knowledge base can be updated."*

#### Escalate to SME
- Note: `F-21 not in KB — need SME to investigate and flag for KE`
- Escalate

---

### Part B — Bob (SME) flags the gap

- Log in as `bob`, open the session
- Click **Flag Knowledge Gap**
- Fill in:
  - **Gap Description:** `Fault code F-21 on the ABB UPS unit is not documented. It indicates a battery ground fault. The isolation procedure and reset sequence are missing from the knowledge base.`
- Click **Submit Gap**

> Session status changes to: `KNOWLEDGE_GAP_FLAGGED`

- Log out of Bob

---

### Part C — demo_ke (KE) resolves the gap

- Log in as `demo_ke` / `demo1234`
- Go to **Dashboard** → **Knowledge Gaps** tab
- You will see the gap flagged by Bob

#### Resolve the gap:
- Click **Resolve Gap**
- In the editor that opens, add the following text to the Power Supply knowledge base:

```
FAULT CODE F-21 — BATTERY GROUND FAULT (ABB UPS)
Cause: Insulation breakdown between battery negative terminal and earth.
Symptom: F-21 on display, control system fails to start.
Isolation procedure:
  1. Switch UPS to bypass mode using the manual bypass switch.
  2. Isolate battery bank via the battery disconnect switch.
  3. Measure insulation resistance between battery negative and earth — should be >1 MΩ.
Reset procedure:
  1. If insulation resistance is acceptable, reconnect battery and clear fault via display menu: Alarm > Clear > F-21.
  2. If insulation resistance is low, replace battery bank before reset.
Reference: ABB UPS Service Manual, Section 4.3.
```

- Click **Save & Re-index Knowledge Base**

> The system will re-index ChromaDB automatically — takes about 10 seconds.
> Alice and Bob will receive a **notification** that the KB was updated.

---

### Part D — Alice resumes and closes

- Log in as `alice`
- Check the **notification bell** — you should see: *"Knowledge base updated — your session can now continue"*
- Open the session
- The yellow banner is now gone
- Continue the session — the AI now answers F-21 questions correctly
- Click **Generate Report**

### What to check ✓
- [ ] Yellow banner appeared immediately after submitting the intake form
- [ ] AI said "not documented in the knowledge base" (did not guess)
- [ ] SME was able to flag the gap with a description
- [ ] KE resolved the gap using the in-app editor
- [ ] ChromaDB re-indexed automatically
- [ ] Alice and Bob both received a notification
- [ ] After resolution, AI correctly described the F-21 procedure

---

---

## Scenario 6 — Full Lifecycle: ME + SME + KE (PLC Corruption)
**Component:** Control System | **Fault:** PLC CPU red fault LED after power surge
**Roles:** Alice (ME) → Bob (SME) flags gap → demo_ke (KE) resolves → all notified
**Time:** ~12 minutes
**What this tests:** Complete system lifecycle from intake to KB resolution

---

### Part A — Alice (ME)

#### Intake form

| Field | Enter This |
|-------|-----------|
| Crane Type | `Overhead Bridge Crane 10t` |
| Component | `Control System` |
| Problem Description | `After a power surge, the PLC CPU module is showing a solid red LED. The crane is completely non-operational. All operator controls are unresponsive.` |
| Environment | `Outdoor, storm caused power spike` |
| Recent Changes | `No recent changes` |
| Error Messages | `PLC CPU RED LED` |

#### Answer 2 questions

| AI Question | Your Answer |
|-------------|-------------|
| Have you power-cycled the PLC (switch off, wait 30 seconds, switch on)? | **Yes — red LED returns immediately after restart** |
| Are any other PLC modules (I/O cards) showing fault indicators? | **No, only the CPU module has the red light** |

#### Escalate
- Note: `PLC CPU hardware fault after power surge — need SME for advanced diagnosis`
- Escalate

---

### Part B — Bob (SME)

- Log in as `bob`, open the session
- Answer 1 more question from the AI

| AI Question | Your Answer |
|-------------|-------------|
| Can you access the PLC programming software to read the CPU diagnostic log? | **Yes — diagnostic log shows Program Memory Checksum Error** |

- AI identifies: PLC program memory corrupted by the power surge
- AI will note it cannot find a restore/recovery procedure in the knowledge base

#### Flag the gap
- Click **Flag Knowledge Gap**
- Description: `PLC CPU program memory restore procedure is missing from the knowledge base. The fault is identified (checksum error from power surge) but the recovery steps — connecting programming laptop, loading program backup from EEPROM, verifying I/O — are not documented.`
- Submit

---

### Part C — demo_ke (KE) resolves

- Log in as `demo_ke`
- Open the Knowledge Gaps tab
- Click **Resolve Gap** on the Control System gap

Add this text to the Control System knowledge base:

```
PLC CPU PROGRAM MEMORY RESTORE PROCEDURE
Applies to: Siemens S7-300/400, Allen-Bradley ControlLogix after power surge
Symptom: CPU solid red LED, Program Memory Checksum Error in diagnostic log.

Recovery steps:
  1. Connect programming laptop via MPI or Ethernet cable to PLC CPU port.
  2. Open TIA Portal (Siemens) or Studio 5000 (Allen-Bradley).
  3. Go to: Online > Download to Device > Program.
  4. Select the last known-good program backup from the EEPROM or backup folder.
  5. After download, perform a Cold Restart: CPU switch STOP → RUN.
  6. Verify all I/O modules go green. Check analog inputs for correct scaling.
  7. Run a no-load operational test before returning crane to service.
  8. Log the surge event and install a surge protection device if not present.
Reference: Siemens S7 Manual Section 6.4 — CPU Memory Recovery.
```

- Click **Save & Re-index Knowledge Base**

---

### Part D — Return to service

- Log in as `alice` — check notification bell
- Open the session — yellow banner is gone
- The AI now provides the restore procedure
- Click **Generate Report**

- Log in as `bob` — check notification bell for KB update
- Log in as `demo_sup` / `demo1234` — view the Dashboard in read-only mode
  - You should see all 6 sessions across all engineers

### What to check ✓
- [ ] Full lifecycle completed: LOGGED → IN_PROGRESS → ESCALATED → SME_IN_REVIEW → KNOWLEDGE_GAP_FLAGGED → IN_PROGRESS → CLOSED_WITH_REPORT
- [ ] KB gap appeared in KE's knowledge gaps tab
- [ ] KE edited the KB and re-indexed in-app
- [ ] Both Alice and Bob received notifications
- [ ] AI gave the correct restore procedure after gap was resolved
- [ ] Supervisor (demo_sup) can see all sessions in read-only mode

---

---

## After All Scenarios — Final Checks

### Dashboard (any user)
- [ ] All 6 sessions visible with their correct statuses
- [ ] Reports viewable for each closed session
- [ ] Session timeline shows all state transitions

### Admin Panel (log in as carol / test123)
- [ ] All 5 users visible
- [ ] Roles correctly assigned
- [ ] User management works (do not delete any users during testing)

### Supervisor view (log in as demo_sup / demo1234)
- [ ] Can see all sessions
- [ ] Cannot create sessions or edit anything (read-only)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| App does not open at localhost:8501 | Run `./start.sh` again; check terminal for errors |
| "ANTHROPIC_API_KEY not set" error | Check your `.env` file has the real key, not the placeholder |
| AI gives no response | Check backend is running at localhost:8000; check API key is valid |
| Yellow banner on every session | The KB threshold may need recalibration — contact the developer |
| demo_prep.py fails | Delete `crane_ai.db` if it exists and run again: `rm -f crane_ai.db && python3 demo_prep.py` |
| Cannot log in | Run `python3 demo_prep.py` to recreate user accounts |
| chroma_db error on startup | Delete it and restart: `rm -rf chroma_db/ && ./start.sh` |

---

## Quick Reference — What Each Role Can Do

| Action | ME (alice) | SME (bob) | KE (demo_ke) | SUP (demo_sup) | ADM (carol) |
|--------|-----------|-----------|--------------|----------------|-------------|
| Create session | ✓ | ✓ | ✓ | — | ✓ |
| Chat with AI | ✓ | ✓ | ✓ | — | ✓ |
| Record measurements | ✓ | ✓ | ✓ | — | ✓ |
| Escalate to SME | ✓ | — | — | — | — |
| Take over escalated session | — | ✓ | — | — | — |
| Flag knowledge gap | — | ✓ | ✓ | — | — |
| Resolve knowledge gap | — | — | ✓ | — | — |
| Edit knowledge base | — | — | ✓ | — | — |
| Generate report | ✓ | ✓ | ✓ | — | ✓ |
| View all sessions | — | — | — | ✓ | ✓ |
| Manage users | — | — | — | — | ✓ |

---

*Thesis: AI-Assisted Knowledge Management for Industrial Process Guidance*
*RPTU Kaiserslautern-Landau / Fraunhofer IESE — Master's Thesis 2025*
*Author: Rutuja Jagtap*
