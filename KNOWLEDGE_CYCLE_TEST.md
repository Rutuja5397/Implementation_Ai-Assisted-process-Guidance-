# Knowledge Management Cycle — Full Test Scenario

## AI-Assisted Process Guidance Tool

> **Purpose:**
> This test demonstrates the complete knowledge management cycle in one continuous flow:
>
> 1. ME reports a fault → AI guidance is incomplete → ME escalates
> 2. SME reviews → identifies the knowledge gap → flags it
> 3. KE updates the knowledge base with the missing procedure
> 4. A second ME reports the EXACT same fault → AI now gives the specific procedure from the update → fault resolved without escalation
>
> **This proves that knowledge captured from one session improves the AI for all future engineers.**
>
> **Component used:** Limit Switch
> **Fault:** Hook block does not stop at the upper travel limit — over-travels into the hoist body

---

## Users Needed

| Role | Username | Password |
|------|----------|----------|
| ME — First engineer | `alice` | `test123` |
| SME — Senior engineer | `bob` | `test123` |
| KE — Knowledge engineer | `demo_ke` | `demo1234` |
| ME — Second engineer | `john_me` | `test123` |

---

---

# PHASE 1 — First ME Session (Alice)

> **What happens:** Alice reports that the hook does not stop at the top. The AI guides her through electrical checks — contact resistance, wiring continuity. She confirms the contacts are electrically fine. The AI then suggests adjusting the cam position but **cannot give specific adjustment steps** because the knowledge base does not have them. Alice escalates to the SME.

---

## P1-1 — Log in as Alice

- Username: `alice` / Password: `test123`
- Click **Login**

---

## P1-2 — Fill the Intake Form

| Field | Value |
|-------|-------|
| Crane Type | `Generic Crane` |
| Component | `Limit Switch` |
| Problem Description | `The hoist hook does not stop when it reaches the top position. It over-travelled and hit the bottom of the hoist body. The upper travel limit switch is not stopping the hoist motion in the upward direction.` |
| Environment | `Indoor workshop. Normal temperature. The crane has been in daily use for 8 months.` |
| Recent Changes | `The hoist drum rope was re-spooled two weeks ago by a contractor.` |
| Error Messages | `No error codes. The control panel shows no warning lights. Down direction still works normally.` |

Click **Start Troubleshooting →**

**You should see:** AI guidance screen opens. The AI immediately focuses on the limit switch circuit — it knows the recent rope re-spooling is relevant.

---

## P1-3 — Chat Turn 1

The AI asks about the limit switch — whether it triggers at all.

**Copy and paste:**
```
I tested the limit switch by slowly raising the hook. The hook went all the way up and touched the hoist body. The limit switch did not stop the motion at any point. The down direction works normally and there are no other issues.
```

Click **Send Answers →**

---

## P1-4 — Chat Turn 2

The AI asks you to test the limit switch contacts — measure continuity or resistance.

**Copy and paste:**
```
I measured the resistance across the limit switch terminals. With the switch in its normal resting position (not triggered), I read 0.3 ohms — which looks like a good closed contact. When I manually press the actuator arm by hand, the reading goes to open circuit as expected. The switch contacts appear to be working correctly electrically.
```

Click **Send Answers →**

> **Check the Evidence tab on the right panel.**
> You will see knowledge chunks retrieved from the limit switch manual.
> **Note what guidance is shown** — the AI will mention cam adjustment but without specific steps.

---

## P1-5 — Chat Turn 3

The AI asks about the physical position of the limit switch or the cam/actuator alignment — this is where the knowledge gap appears.

**Copy and paste:**
```
I can see the rotary cam mechanism on the side of the hoist drum gearbox. There are several cams mounted on a shaft connected to the drum. I can see the cams rotate as the drum turns. But I do not know which cam controls the upper limit, which direction to adjust it, or how far to move it. I do not have any adjustment instructions for this type of limit switch.
```

Click **Send Answers →**

**You should see:**
- The AI acknowledges that cam adjustment is needed but gives only generic guidance
- Look for the **orange confidence badge** at the bottom of the AI message:
  > *"⚠️ Low knowledge base coverage — No specific rotary cam adjustment procedure found"*

This badge confirms the knowledge gap has been detected automatically.

---

## P1-6 — Chat Turn 4

The AI asks you to attempt the adjustment or check the drum rotation counter.

**Copy and paste:**
```
I attempted to adjust the cam slightly but I am not confident I have moved the correct cam in the correct direction. I do not want to make the situation worse. I do not have the procedure for this adjustment and I risk either not fixing the problem or setting the stop point dangerously wrong. I need expert guidance.
```

Click **Send Answers →**

**You should see:** The AI recommends escalating to a more experienced engineer. Alice is stuck — she cannot proceed safely without the specific cam adjustment procedure.

---

## P1-7 — Escalate

Click the **🚨 Escalate** button.

**Copy and paste this escalation reason:**
```
The electrical contacts on the limit switch are functioning correctly — the switch is good. The problem is that the rotary cam position needs adjustment after the rope was re-spooled. I do not have the procedure for adjusting the cam on this rotary-type limit switch. I attempted a small adjustment but cannot confirm it is correct. I need a senior engineer to guide the cam adjustment procedure safely.
```

Click **Confirm Escalation**.

**You should see:** Session lifecycle changes to **ESCALATED**.

**Log out as Alice.**

---

---

# PHASE 2 — SME Reviews and Flags the Gap

> **What happens:** Bob sees Alice's session. He reviews her observations — contacts fine, cam adjustment needed, AI gave no specific procedure. He adds an expert note explaining the cam adjustment. He then flags the knowledge gap so the KE can add the proper procedure to the knowledge base permanently.

---

## P2-1 — Log in as Bob

- Username: `bob` / Password: `test123`
- Click **📥 SME Inbox**

---

## P2-2 — Open Alice's Session

Click on Alice's escalated limit switch session.

**You should see:**
- Alice's full conversation history
- Her escalation reason
- The **yellow knowledge gap warning** in the SME Actions panel:
  > *"⚠️ Knowledge gap detected — AI reported low knowledge base coverage on X message(s)"*

This confirms the AI itself identified the gap during Alice's session.

---

## P2-3 — Open for Review

Click **🔬 Open for Review**.

**You should see:** Lifecycle changes to **SME_IN_REVIEW**.

---

## P2-4 — Add Expert Annotation

Click the **📝 Annotations** tab → **Add Annotation**.

| Field | Value |
|-------|-------|
| Annotation Type | `expert_note` |
| Text | `Alice's diagnosis is correct — the limit switch contacts are electrically sound. The root cause is that after rope re-spooling, the rotary cam position has shifted and no longer activates the limit switch at the correct drum position. The rotary cam shaft typically has 2-4 cams: one for upper limit, one for lower limit, sometimes a slack rope cam. The upper limit cam must be rotated on its shaft so that it trips the limit switch when the hook is 300mm below the hoist body. This is done by loosening the cam grub screw, rotating the cam on the shaft, and re-tightening. The knowledge base does not contain this procedure — flagging for KE to update.` |

Click **Save Annotation**.

---

## P2-5 — Flag the Knowledge Gap

Click **⚠️ Flag Knowledge Gap** in the SME Actions panel.

**You should see:** Lifecycle changes to **KNOWLEDGE_GAP_FLAGGED**.

**Log out as Bob.**

---

---

# PHASE 3 — KE Updates the Knowledge Base

> **What happens:** The Knowledge Engineer sees the gap, opens the limit_switch.txt editor, and adds the specific rotary cam adjustment procedure that was missing. After saving, the system re-indexes automatically.

---

## P3-1 — Log in as KE

- Username: `demo_ke` / Password: `demo1234`
- Click **🔍 Knowledge Gaps**

---

## P3-2 — Open the Gap

**You should see:** A gap card for the Limit Switch component with Bob's description of what is missing.

Click **✏️ Edit & Resolve**.

---

## P3-3 — Add the Missing Procedure

Scroll to the very bottom of the editor. Add the following text exactly as written:

```
=== ROTARY CAM LIMIT SWITCH — ADJUSTMENT PROCEDURE (Post Rope Re-spooling) ===

After hoist rope replacement or re-spooling, the rotary cam position must be reset
because the drum reset changes the relative cam-to-drum alignment.

TOOLS REQUIRED: 3mm Allen key (for cam grub screws), permanent marker, feeler gauge (optional)

IDENTIFYING THE CAMS:
The cam shaft is mounted on the side of the drum gearbox or drum frame.
Typical cam layout (front to back on shaft):
  - Cam 1 (closest to motor): Upper hoist limit — stops UP direction
  - Cam 2: Lower hoist limit — stops DOWN direction (slack rope protection)
  - Cam 3 (if present): Intermediate slow-down cam (yellow, pre-limit warning)
Do NOT adjust Cam 2 or Cam 3 unless required. Mark each cam with a marker before adjusting.

ADJUSTMENT STEPS — UPPER LIMIT CAM (Cam 1):
1. LOTO: isolate crane power and lock out.
2. Manually lower the hook to mid-travel position (away from both limits).
3. Locate cam shaft — loosen Cam 1 grub screw (do not remove).
4. Physically raise the hook block by hand (or slowly with power briefly restored
   under direct supervision) to the desired stop position: 300mm minimum clearance
   below hoist body.
5. At this exact hook position, rotate Cam 1 on the shaft until its lobe contacts
   and depresses the limit switch roller — you will hear/feel the switch click.
6. Hold cam in this position and tighten the grub screw firmly.
7. Lower hook back to mid-travel.
8. Restore power. Slowly raise hook in UP direction.
9. Hook must stop at the position set in step 4.
10. Verify DOWN direction still operates normally after limit activation.
11. Record: date, technician, cam position, clearance measured.

COMMON MISTAKES:
- Adjusting Cam 2 instead of Cam 1 — will break lower limit protection
- Grub screw not fully tightened — cam shifts during operation
- Setting clearance less than 300mm — violates EN 14502 safety requirement
- Not testing DOWN direction after adjustment — critical verification step
```

Click **💾 Save to Knowledge Base & Resolve Gap**.

**You should see:**
- Success message: gap resolved, knowledge base updated
- Alice and Bob receive a notification (bell badge at top)

> **This is the moment the knowledge base improves.**
> The system has re-indexed ChromaDB with the new procedure.
> Every future session on the Limit Switch component will now retrieve this content.

**Log out as KE.**

---

---

# PHASE 4 — Second ME Reports the Same Fault

> **What happens:** John (a different ME) reports the exact same fault — hook over-travels the upper limit. This time, the AI retrieves the newly added cam adjustment procedure and gives John specific, actionable steps. John resolves the fault without escalating.
>
> **This is the proof that the knowledge gap was resolved and the update is working.**

---

## P4-1 — Log in as John

- Username: `john_me` / Password: `test123`
- Click **Login**

---

## P4-2 — Fill the Intake Form

> **Important:** Use the same component and a similar problem description to Alice's session.

| Field | Value |
|-------|-------|
| Crane Type | `Generic Crane` |
| Component | `Limit Switch` |
| Problem Description | `The hook does not stop at the upper travel position. It over-travels upward. The upper limit switch is not activating to stop the hoist.` |
| Environment | `Indoor workshop. Normal conditions.` |
| Recent Changes | `Hoist rope was replaced last week.` |
| Error Messages | `No error codes or warning lights.` |

Click **Start Troubleshooting →**

> **Watch for the "Known Fault Found" screen.**
> If Alice's session has already been closed with a report, the system may show
> a previously resolved case. If it appears, click **"My issue is different — Start new diagnosis"**
> to proceed to the full diagnostic session so you can see the updated AI guidance.

---

## P4-3 — Chat Turn 1

The AI asks what happens when John raises the hook.

**Copy and paste:**
```
When I press the up button, the hook raises and does not stop at the top. It continues up and makes contact with the hoist body before I release the button manually. The down direction works fine.
```

Click **Send Answers →**

---

## P4-4 — Chat Turn 2

The AI asks about the limit switch contacts or circuit.

**Copy and paste:**
```
I checked the limit switch contacts with a multimeter. The contacts are working correctly — they read 0.3 ohms when open and open circuit when manually triggered. The switch itself seems fine electrically. The crane rope was just replaced so the cam position may have shifted.
```

Click **Send Answers →**

> **PROOF POINT 1 — Check the Evidence tab now.**
> You should see a knowledge chunk retrieved that includes text about
> "ROTARY CAM LIMIT SWITCH — ADJUSTMENT PROCEDURE".
> This chunk was NOT available during Alice's session — it was added by the KE.
> The AI is now using the updated knowledge.

---

## P4-5 — Chat Turn 3

**You should see:** The AI now provides the specific cam adjustment procedure — identifying which cam to adjust, the grub screw steps, the 300mm clearance requirement, and the verification steps.

> **PROOF POINT 2 — Compare AI response quality.**
> Alice received: *"You may need to adjust the cam position on the rotary limit switch"* (generic)
> John receives: Specific steps — cam identification, grub screw loosening, positioning method, tightening, and verification.
>
> The difference is entirely due to the KE's knowledge base update.

**Copy and paste:**
```
I found the cam shaft on the side of the drum gearbox. I can see three cams. I identified Cam 1 as the upper limit cam. I loosened the grub screw, manually raised the hook to 300mm below the hoist body, rotated Cam 1 until I heard the limit switch click, and tightened the grub screw. I then tested the hoist and it stopped correctly at the right position.
```

Click **Send Answers →**

---

## P4-6 — Chat Turn 4 (Resolution Confirmation)

**Copy and paste:**
```
After the cam adjustment, I ran three full test cycles raising the hook to the limit position. The limit switch activates correctly every time and stops the hoist at approximately 300mm below the hoist body. The down direction continues to work normally. The fault is fully resolved.
```

Click **Send Answers →**

**You should see:** The AI confirms the root cause (cam position shifted after rope replacement), summarises the steps, and considers the fault resolved.

---

## P4-7 — Generate the Fault Report

Click **⚡ Generate Report**.

Wait 5–15 seconds.

**You should see a structured report that specifically references:**
- Root cause: rotary cam position shifted after rope re-spooling
- Steps taken: cam identification, grub screw adjustment, 300mm clearance verified
- Recommendations: re-check cam position after any rope replacement

> **PROOF POINT 3 — This report now becomes a reusable knowledge asset.**
> If any future engineer reports the same fault, the "Known Fault Found" screen
> will show this report immediately — reducing resolution time to near zero.

---

---

# PHASE 5 — Optional: Third ME Sees "Known Fault Found"

> Log out as John. Log back in as Alice or any other ME.
> Fill the intake form again with the same Limit Switch / upper limit fault.
> You should see the **"Known Fault Found"** screen with John's report.
> Click **"This fixes my issue — Apply & Close"** to close instantly without diagnosis.

---

---

# What This Scenario Proves

| Claim | Evidence in the Test |
|-------|---------------------|
| AI detects its own knowledge gaps | Orange confidence badge on Alice's session — Turn 3 |
| SME receives automatic gap warning | Yellow warning box in SME Actions panel — Phase 2 |
| KE can update KB without file system access | In-app editor used in Phase 3 |
| System re-indexes after KE update | Next session retrieves new chunk — visible in Evidence tab |
| Updated knowledge improves AI guidance | Alice got generic advice; John got specific cam steps |
| Resolved sessions become reusable knowledge | "Known Fault Found" screen for third engineer |
| Complete audit trail | Every action (escalation, annotation, gap flag, KB update) is logged |

---

# Checklist

- [ ] Alice session created — Limit Switch / upper limit fault
- [ ] Contacts checked — electrically OK
- [ ] AI gave generic cam advice with **orange low-confidence badge** visible
- [ ] Alice escalated with reason
- [ ] Bob logged in — yellow knowledge gap warning visible in SME Actions panel
- [ ] Bob added expert annotation
- [ ] Bob flagged knowledge gap → lifecycle = KNOWLEDGE_GAP_FLAGGED
- [ ] KE logged in — gap visible in Knowledge Gaps screen
- [ ] KE added rotary cam adjustment procedure and saved
- [ ] Success confirmation shown — gap resolved
- [ ] John logged in and submitted same fault
- [ ] Evidence tab in John's session shows KE-updated chunk
- [ ] AI response in Turn 3 contains specific cam adjustment steps
- [ ] John resolved the fault — no escalation needed
- [ ] John's fault report generated with specific root cause
- [ ] (Optional) Third session shows "Known Fault Found" screen
