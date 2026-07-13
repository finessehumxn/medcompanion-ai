# MedCompanion AI — Hospital-Readiness Scorecard & Phased Plan

**Company:** Millennials Creatives LLC · **Product:** MedCompanion AI
**Last reviewed:** 2026-07-12
**Purpose:** An honest, no-spin picture of what a hospital requires before it says yes, where we actually stand, and the realistic sequence. Share this with an advisor or a prospective clinical champion — it's designed to be *believed*, not to impress.

> Companion docs: **[hipaa-baa-readiness.md](hipaa-baa-readiness.md)** (the control set), **[data-flow-one-pager.md](data-flow-one-pager.md)** (the 2-minute data story), **[epic-smart-on-fhir-roadmap.md](epic-smart-on-fhir-roadmap.md)** (Epic integration).

---

## The one-paragraph truth

MedCompanion is a **good patient product** with a **genuinely strong data-privacy architecture** (local-first, nothing stored by default, independently verifiable at `/data-policy`). That is *one* of the things a hospital cares about — and it's real. But "hospital-ready" is a stack of mostly **non-engineering** gates (SOC 2, signed BAAs, insurance, clinical validation, a sponsoring champion) that take **12–18 months and real money**. **You do not need any of that to launch the consumer product**, where the patient authorizes their own records. So the plan is: **ship consumer now, warm the hospital groundwork in parallel, and let a champion + SOC 2 unlock the hospital track later.**

---

## The scorecard

🟢 in place · 🟡 partial / in progress · 🔴 not started

| Gate a hospital checks | Status | What "done" looks like | Code fixes it? | Rough cost | Rough time |
|---|---|---|---|---|---|
| **Data-privacy architecture** | 🟢 | Local-first, no server storage by default, verifiable | ✅ done | — | done |
| **In-app transparency & consent** | 🟢 | User sees what's sent, can turn AI off, delete data | ✅ done | — | done |
| **Product itself works** | 🟡 | Coherent, honest, safe, no dead ends, clear first-run value | ✅ (Track A) | — | weeks |
| **BAAs signed** (hospital + Anthropic/AWS, Railway, Supabase) | 🔴 | Executed contracts before any PHI flows | ❌ legal/vendor | low–mid $ (attorney) | 1–3 mo |
| **HIPAA Security Rule program** | 🟡 | Risk analysis, policies, named officers, training, incident runbook | ❌ mostly process | time (+ attorney) | 1–2 mo |
| **SOC 2 Type II** (or HITRUST) | 🔴 | Audited report over a 3–12 mo observation window | ❌ auditor | **$15k–$60k+** | **6–12 mo** |
| **Cyber + professional liability (E&O) insurance** | 🔴 | Active policies | ❌ purchase | few $k/yr | weeks |
| **Clinical safety / validation** | 🔴 | Accuracy eval, harmful-output testing, physician/medical-director sign-off | ⚠️ needs a clinician + eval | time + advisor | 2–4 mo |
| **Not-a-medical-device posture** | 🟡 | Clear "information, not diagnosis"; no interpretation/guidance claims | ⚠️ copy + legal review | attorney review | weeks |
| **Vendor security questionnaire + pen test** | 🔴 | Completed questionnaire; external pen test report | ⚠️ partly process | $5k–$20k (pen test) | 1–2 mo |
| **Epic production connection** | 🔴 | Sponsoring hospital enables prod client ID in *their* Epic | ❌ their IT + BD | — | gated by champion |
| **Corporate viability** | 🟡 | Entity, insurance, references, financial stability they can vet | ❌ business maturity | — | ongoing |
| **A sponsoring clinical champion** | 🔴 | A named clinician/department that wants to pilot you | ❌ **this is sales** | BD time | **the long pole** |

**Read of the board:** the *technical* and *privacy* rows are green/yellow. The rows that actually block a hospital — **SOC 2, BAAs, insurance, clinical validation, and a champion** — are red, cost money, and take months. **None are solved by writing more app features.**

---

## Phased plan

### Phase 0 — Ship the consumer product (NOW · code, this is Track A)
Needs **none** of the red gates. The patient connects *their own* MyChart/records and authorizes their own data.
- Make the patient experience launch-ready: honest onboarding, safe empty states, emergency/crisis guidance, consistent "information not diagnosis" copy, no hospital/clinician overpromising, no dead ends.
- Keep the record-connection paths (Epic sign-in, file import, Apple Health) honest about their current state.
- **Goal:** real patients, real usage, real feedback — the traction that de-risks everything after.

### Phase 1 — Warm the groundwork (PARALLEL · non-code, Track B, start this month)
Cheap, founder-doable things that shorten Phase 2 later:
- [ ] **Draft the HIPAA Risk Analysis** (the #1 artifact OCR/hospitals ask for) — use the map in hipaa-baa-readiness.md.
- [ ] **Name a Security Officer + Privacy Officer** in writing (can be the founder).
- [ ] **Start the Anthropic BAA / zero-retention conversation** (or decide on Bedrock). No PHI in production until signed.
- [ ] **Get insurance quotes** (cyber + professional liability/E&O).
- [ ] **Engage a healthcare attorney** for a scoping call (BAA templates, device-status opinion, claims review).
- [ ] **SOC 2 readiness assessment** (not the full audit yet) — pick a platform (Vanta/Drata-style) and scope.
- [ ] **Line up a clinical advisor** — one physician willing to review outputs and, ideally, become the champion.

### Phase 2 — Land a pilot champion (BD-led, months)
- A clinician/department decides to pilot. They (or their Epic team) enable the production client ID; you sign the BAA; you complete their security questionnaire.
- Run a **small, bounded pilot** (ideally with the champion, possibly under IRB if it's framed as research).

### Phase 3 — Scale (post-pilot)
- Complete SOC 2 Type II (observation window running from Phase 1), pen test, Showroom/listing decisions, repeatable onboarding.

---

## What to STOP claiming until it's true

To protect the brand (and avoid FTC/legal risk), until the matching row is 🟢 **do not say**:
- "HIPAA compliant" / "HIPAA certified" (there is no such certification; you're at most *working toward* a HIPAA program).
- "SOC 2 certified" (until the Type II report exists).
- "Hospital-approved" / "used by hospitals" / "Epic-integrated in production."
- Anything that reads as **diagnosis, interpretation, or treatment guidance** (keeps you out of medical-device territory).

**What you CAN honestly say today:** "Your data stays on your device," "we store nothing by default," "you can verify our data policy yourself," "information to help you understand your health and prepare for visits — not a diagnosis."

---

## Honest budget & timeline to a first hospital pilot

- **Cash gates:** SOC 2 ($15k–$60k+), pen test ($5k–$20k), insurance (few $k/yr), attorney (varies). Call it **~$30k–$100k+** before a first real pilot, spread over the year.
- **Time gate:** **12–18 months**, dominated by SOC 2's observation window and by finding the champion — not by engineering.
- **The cheapest, fastest thing that moves everything:** a **sponsoring clinician**. Everything downstream gets easier and better-scoped once one real clinician wants this. That's a sales/relationship effort, and it can start today with zero code.

---

*Practical guidance, not legal advice. Confirm vendor terms, insurance, and device status with the appropriate professionals before relying on any of it.*
