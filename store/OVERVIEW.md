# MedCompanion AI — Product Overview
**Prepared for our medical advisory board / clinical co-founder.**
By Millennials Creatives LLC · Web app live at https://medcompanion-ai.up.railway.app/app

---

## What it is (in one line)
MedCompanion AI is a plain-language health *companion* that helps everyday people understand health information and **prepare to partner with their own doctor** — explicitly designed *not* to diagnose, treat, or replace a clinician.

## Our core principle: work WITH the clinician, never around them
This is the heart of the product and the answer to the "patients arguing with us like Dr. Google" problem.
- Every output is framed as **understanding + questions to ask your doctor**, never as instructions or a diagnosis.
- The AI is instructed to **never tell a patient their doctor is wrong**, never tell them to change/stop a medication on their own, and to defer to the treating clinician who knows their full history.
- A persistent disclaimer appears on **every** briefing: *"This works with your doctor — not instead of them… general information, not a diagnosis or medical advice, and not for emergencies."*

---

## Features (all built and live on the web app)

### The doctor-visit journey — the part no competitor has
1. **Doctor Bridge** — every briefing generates a printable / shareable **"Doctor Visit Sheet"**: the patient's topic, a plain-language summary, **questions to ask the doctor**, the sources used, and a note to the clinician ("an AI prep tool — you decide"). The patient hands this over instead of arguing.
2. **Live Visit Companion** — a real-time, in-the-exam-room mode. The patient types or speaks what the doctor just said; it instantly translates the jargon to plain language and suggests the smart next question to ask — then compiles an **after-visit summary**.
3. **Health Memory + New-Patient One-Pager** — briefings are saved privately on the patient's device; one tap builds a one-page history summary for any *new* doctor.

### Trust & safety
4. **Reviewed by a Real Doctor** — patients can request a physician review; a board doctor co-signs via a private portal and the patient sees a **"✓ Reviewed by a licensed physician"** badge. (Portal: /doctor — accuracy/tone review only, explicitly *no* diagnosis and *no* doctor-patient relationship created.)
5. **Safety radar** — each result shows an **urgency level** (emergency / today / soon / monitor) and **red-flag "seek care now" symptoms**.
6. **Crisis & emergency guardrail** — a first-pass classifier routes mental-health crisis to **988** and medical emergencies to **911 / ER** before any briefing is generated.

### Access & comprehension (equity)
7. **Multilingual care bridge** — the patient can read the briefing in **their** language (15+ supported) while the doctor still receives the Visit Sheet in English.
8. **Read-aloud (text-to-speech)** — answers can be heard hands-free, in the patient's language. Voice input is also supported.
9. **Audience modes** — a startup picker routes to: *For myself · For a loved one · Medical professional (clinical, evidence-based, OpenEvidence-style) · Medication & interaction check.*

### Practical tools
10. **Medication & interaction checker** — flags what to avoid / use caution / is usually fine across meds, foods, and drinks, with a "confirm with your pharmacist" reminder.
11. **Snap-a-pill** — photograph medication bottles; the vision AI reads the names and runs the interaction check.
12. **Lab/image reading** — upload a lab result or photo for a plain-language explanation.
13. **Installable app (PWA)** — installs to a phone/desktop home screen and works offline.

---

## How a briefing is produced (clinically relevant)
A LangGraph pipeline with an explicit human-in-the-loop step:
**guardrail (safety/crisis screen) → extraction (their words) → normalization (lay → clinical terms, urgency, red flags) → patient confirmation → briefing (current standard of care + emerging options, web-search-grounded against NIH, Mayo Clinic, FDA, PubMed, with sources).**
Professional mode produces an evidence-forward briefing (evidence levels, guideline bodies, citations).

## Privacy
General-information tool. Health inputs are **not sold and not used for advertising.** Processed by trusted AI/search providers only to answer the question. Privacy policy: /privacy.

## Technology
- **AI:** Anthropic Claude, with web-search grounding; orchestrated via LangGraph.
- **Backend:** FastAPI (Python), deployed on Railway.
- **Frontend:** single-page web app; installable PWA.
- **Mobile:** Capacitor — Android build is store-ready; iOS pending Apple organization enrollment.
- **Accounts/persistence (optional):** Supabase.

## Status (today)
- ✅ **Web app: live** with every feature above.
- ✅ **Google Play: submission-ready** — signed-build pipeline, store assets, listing copy, and Data-Safety/Health answers all prepared; awaiting final upload.
- ⏳ **iOS:** waiting on Apple organization (LLC) enrollment verification.
- ⏳ **Physician review:** portal is live; needs the board's access key + one database table switched on to go fully active.

## Where the board comes in
Our advisory physicians (1) lend credibility, (2) co-sign briefings through the portal for the "Reviewed by a licensed physician" badge, and (3) help us tune tone and safety. This is the trust moat competitors (Perplexity, OpenEvidence, ChatGPT, WebMD) structurally cannot copy.
