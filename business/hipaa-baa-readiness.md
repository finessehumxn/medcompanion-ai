# MedCompanion AI — HIPAA + BAA Readiness Checklist

**Company:** Millennials Creatives LLC
**Product:** MedCompanion AI — plain-language health-explanation tool (consumer app + clinician "Pro" tier)
**Stack:** Capacitor (iOS + Android) + web app · FastAPI/Python on Railway · Supabase (data + auth) · Stripe (payments) · Anthropic Claude API (AI)
**Goal of this document:** Get to a *minimum viable* compliance posture so MedCompanion can legally run a pilot with **one clinic or hospital**.
**Last reviewed:** 2026-06-29

> ⚠️ **This is practical guidance, not legal advice.** HIPAA penalties are real and the rules are nuanced. **Have a healthcare attorney review every BAA before you sign it**, and have them confirm the analysis below maps to your actual data flows. Vendor HIPAA terms also change — re-verify each subprocessor's current offering before relying on it.

---

## 0. Update — trust-by-default architecture (2026-07-12)

Since this checklist was first written, the product moved to a **local-first, AI-optional, no-storage-by-default** architecture. This *materially reduces* the PHI surface below and should be read on top of the analysis that follows:

- **Supabase is no longer in the health-data path by default.** Server-side history is gated behind `MC_STORE_HISTORY=1` (off by default). In the default configuration, patient check-ins and records live only in device localStorage and are **never written to our database**. The subprocessor table in §2 still lists Supabase as the "primary PHI datastore" — that is only true if history is deliberately enabled.
- **The text-AI path is single-vendor (Anthropic).** Fewer parties touch PHI.
- **Voice features (optional)** send audio to OpenAI/Groq for STT/TTS — add these to your subprocessor/BAA tracking if voice is used with PHI (prefer a BAA-covered vendor; Groq's BAA is less established).
- **No health content is logged** (provider error bodies were removed from logs).
- **The running server publishes its data policy** at `/data-policy` (machine-readable) and `/trust` (human-readable) for independent verification.

**See the 2-minute [data-flow-one-pager.md](data-flow-one-pager.md)** for the current, reviewer-facing summary. The BAA/Security-Rule work in §2–§8 below is still required before PHI flows on behalf of a covered entity; the architecture change just shrinks the default surface it has to cover.

---

## 1. When does HIPAA actually apply to you?

HIPAA does not regulate "health data" in the abstract. It regulates **Protected Health Information (PHI)** held by two kinds of organizations:

- **Covered Entity (CE):** a health-care provider, health plan, or clearinghouse (e.g., a clinic or hospital).
- **Business Associate (BA):** a vendor that creates, receives, maintains, or transmits PHI **on behalf of a Covered Entity**.

This produces a sharp, scope-defining line for MedCompanion:

### Consumer / direct-to-user product → HIPAA likely does NOT apply
When an individual signs up themselves and types in their own symptoms or uploads their own labs, **the user is not a Covered Entity**, and you are not acting on behalf of one. That data is sensitive and is "consumer health data," but it is generally **outside HIPAA's scope**.

> **Important caveat — HIPAA is not the only law.** Even when HIPAA doesn't apply, the consumer product is likely covered by:
> - **FTC Act + FTC Health Breach Notification Rule** (applies to consumer health apps that aren't HIPAA-covered),
> - **State consumer-health-privacy laws** — e.g., **Washington's "My Health My Data" Act**, **Nevada SB370**, and **CCPA/CPRA** sensitive-data rules in California,
> - App-store health-data policies (Apple/Google).
> So "HIPAA doesn't apply" ≠ "no privacy obligations." It just means a *different* rulebook.

### Clinician "Pro" tier / clinic pilot → HIPAA DOES apply, and you become a Business Associate
The moment a clinic or hospital uses MedCompanion to handle PHI **on behalf of the clinic's patients** — e.g., a clinician pastes in a patient's labs, or patient data flows from the clinic to you — **MedCompanion (Millennials Creatives LLC) becomes a Business Associate of that clinic**, and the full HIPAA Security Rule + Breach Notification Rule + relevant Privacy Rule obligations attach to you.

**Bottom line:** The clinic pilot is what pulls you into HIPAA. Everything below is about being ready for *that*.

---

## 2. The Business Associate Agreement (BAA) and your subprocessor chain

### What a BAA is
A **BAA** is the contract HIPAA *requires* between a Covered Entity and its Business Associate (and between a BA and its sub-BAs). It obligates you to safeguard PHI, use it only as permitted, report breaches, flow obligations down to subcontractors, and return/destroy PHI at the end.

### Two directions you must cover
1. **Upstream:** You must **sign a BAA with each clinic/hospital** before any PHI touches your systems. (The clinic will usually provide their paper; your attorney should review it — some clinic BAAs over-reach.)
2. **Downstream (the part startups forget):** You must have a **BAA in place with every subprocessor that creates, receives, maintains, or transmits PHI on your behalf.** If a vendor touches PHI and won't sign a BAA, you **cannot** legally send PHI to it.

### Your subprocessor chain — BAA status (verify current terms before relying on this)

| Subprocessor | Role | Touches PHI? | Offers a BAA? | Plan / tier required | Action for MedCompanion |
|---|---|---|---|---|---|
| **Railway** | Hosting / compute for FastAPI backend | **Yes** — PHI passes through and may transit memory/logs | **Yes**, on the **Enterprise track**, "BAAs available upon request" | Enterprise track; gated behind a **minimum monthly commitment (≈$1,000/mo at last check)**. With a BAA in effect, Railway staff can no longer directly access your running workloads. | Contact `team@railway.com`, sign BAA, confirm encryption-at-rest + access controls in your config. |
| **Supabase** | Database + Auth (where PHI is stored) | **Yes** — primary PHI datastore | **Yes** | **Team plan or higher**, **plus** the **HIPAA add-on** must be requested/enabled and the BAA signed in-dashboard. Supabase has BAAs with its own vendors (e.g., AWS). | Upgrade to Team, enable HIPAA add-on, sign BAA, and place PHI **only** in HIPAA-enabled projects. Follow Supabase's shared-responsibility model (RLS, access, etc. are *your* job). |
| **Anthropic (Claude API)** | The AI that generates explanations | **Yes** — prompts contain PHI | **Yes** — see §6 for the important details | **1P API:** admin signs BAA, then **contact sales to enable**. **Covered Models require 30-day retention** (cannot use Zero-Data-Retention). BAA does **NOT** cover Workbench/Console, Free/Pro/Max/**Team**, or beta features. | Sign Anthropic BAA and get PHI use enabled **before** sending any PHI, **or** route Claude via Bedrock (§6). |
| **Stripe** | Payments | **Should be NO** | **No** — Stripe does **not** sign HIPAA BAAs and states it is not HIPAA-compliant | N/A | **Keep PHI out of Stripe entirely.** Payment data (name, card, billing address) is generally **not PHI** and is exempt under SSA §1179. Risk is only if PHI leaks into Stripe metadata, descriptions, invoices, receipts, or webhooks. **Architect to guarantee that never happens.** |

> **Key nuance on Stripe:** Payment processing itself is fine without a BAA — financial transactions are carved out of HIPAA. The danger is *accidental* PHI leakage into Stripe fields (e.g., putting "Patient John Doe – diabetes consult" in a charge description). Your job is to ensure no clinical/identifiable health context ever flows into Stripe.

---

## 3. Security Rule — TECHNICAL safeguards (checklist mapped to your stack)

| Safeguard | Requirement | Concrete action in this stack |
|---|---|---|
| **Encryption in transit** | TLS for all PHI movement | Enforce **HTTPS/TLS 1.2+** everywhere: Capacitor/web → FastAPI, FastAPI → Supabase, FastAPI → Anthropic. No plaintext HTTP. Enable HSTS. Pin to Railway's TLS edge. |
| **Encryption at rest** | PHI encrypted on disk | Supabase HIPAA projects encrypt at rest (AES-256, inherited from AWS). Railway encrypts volumes at rest. Confirm any file/photo/lab uploads (Supabase Storage) are in a HIPAA-enabled bucket and encrypted. |
| **Access control + unique user IDs** | Each person has a unique identity; least-privilege | Unique Supabase Auth accounts (no shared logins). **Row-Level Security (RLS)** so users/clinicians see only their own/their patients' data. Separate roles for patient vs. clinician (Pro) vs. admin. Scope service keys tightly; never ship the Supabase service-role key to the client. |
| **Authentication / MFA** | Verify identity; MFA strongly expected | Enable **MFA** in Supabase Auth, **required** for clinician/Pro and admin accounts (and offered to consumers). Enforce strong password policy. |
| **Audit logging** | Record who accessed/modified PHI | Enable Supabase audit/Postgres logging. Add **application-level audit logs** in FastAPI for every PHI read/write/export (who, what, when). Ship logs to a retained store. **Scrub PHI out of log bodies** — log identifiers/refs, not the PHI itself. |
| **Automatic logoff** | Terminate idle sessions | Set short JWT/session expiry + idle timeout in the app; re-auth on resume. Tune Supabase token refresh/expiry. |
| **Integrity controls** | Detect improper alteration/destruction of PHI | DB constraints + RLS, checksums/versioning on stored files, immutable/append-only audit log, regular backups with integrity verification. |
| **Transmission security** | Guard PHI in transit against interception | TLS everywhere (above) + authenticated API endpoints; no PHI in URL query strings; no PHI in third-party analytics or crash/telemetry payloads. |

---

## 4. Security Rule — ADMINISTRATIVE safeguards

These are the policies/process pieces. For a small startup, "right-sized but real" is the standard — written, dated, and actually followed.

- [ ] **Risk Analysis (required, foundational):** Document where PHI lives, how it flows (app → FastAPI → Supabase → Anthropic), and the threats/vulnerabilities. This is the #1 thing OCR asks for. Update it when the architecture changes.
- [ ] **Risk Management:** A plan to remediate the gaps the risk analysis finds.
- [ ] **Designate a Security Officer and a Privacy Officer** (can be the same founder at this stage — but name them in writing).
- [ ] **Workforce training:** Everyone with PHI access completes HIPAA training; record completion dates. Repeat annually.
- [ ] **Access management:** Written process for granting, reviewing, and **promptly revoking** access (especially offboarding). Least-privilege by default.
- [ ] **Incident response + Breach Notification procedures:** Written runbook for detecting, containing, investigating, and **notifying**. Under the Breach Notification Rule, as a BA you must notify the **affected Covered Entity without unreasonable delay and within 60 days** of discovery; the clinic then handles patient/HHS notice. Know your obligations *before* an incident.
- [ ] **Sanction policy:** Written consequences for workforce members who violate the policies.
- [ ] **Business Associate management:** Track which subprocessors have signed BAAs and keep copies (see §2).
- [ ] **Contingency plan:** Data backup, disaster recovery, and emergency-mode operation for PHI systems.

---

## 5. Security Rule — PHYSICAL safeguards (mostly inherited)

For a cloud-native startup, **most physical safeguards are inherited from your cloud providers** (AWS underpins Supabase; Railway's infrastructure). You rely on their data-center controls — facility access, environmental protections — documented in their SOC 2 / HIPAA reports. **Request and retain those reports** (Supabase, Railway, AWS via Supabase) as evidence.

What's still **yours** to handle:
- [ ] **Workstation security:** Laptops/devices used by anyone accessing PHI must have **full-disk encryption** (FileVault/BitLocker), screen lock, and current OS patches.
- [ ] **Device & media controls:** No PHI on USB drives or personal devices; policy for secure disposal/wipe of any device that held PHI.
- [ ] **Mobile:** Don't persist PHI unnecessarily on the Capacitor app; if cached, use secure storage and OS-level encryption.

---

## 6. The AI question — can you send PHI to Claude?

**Yes — but only under a covered configuration.** This is one of the most important sections for MedCompanion because every explanation request sends user/patient health context to the model.

You have two viable paths:

### Path A — Anthropic 1P API directly under a BAA
- Anthropic **does offer a BAA** covering its first-party API (the Messages API is an Eligible Service under the BAA) and HIPAA-ready Enterprise plans.
- To use the **1P API with PHI**: an org admin signs the BAA, then **contacts Anthropic sales to enable PHI use**. It is **not** on by default.
- **Covered Models require 30-day data retention** — you **cannot** combine PHI use with Zero-Data-Retention.
- The BAA does **NOT** cover: Workbench/Console, Claude Free/Pro/Max/**Team**, Cowork, or beta features. (So your dev playground use ≠ covered.)

### Path B — Claude via Amazon Bedrock (HIPAA-eligible config)
- **Amazon Bedrock is HIPAA-eligible**, and Claude models run inside it. PHI sent to Bedrock for inference is **covered under the AWS BAA**.
- In this setup, data stays inside AWS and **Anthropic does not see your prompts/outputs** — Bedrock isolates the model provider.
- If you're already on AWS with an AWS BAA, you can use Bedrock-hosted Claude **without a separate Anthropic contracting cycle** (often saves weeks of legal).
- **Caveat:** The AWS BAA covers Bedrock; it does **not** cover the public Anthropic API. Don't mix paths and assume coverage.

### Honest take for your situation
Either path is legitimate. **Path A (direct Anthropic BAA)** keeps your stack simple (you already call the Anthropic API) but requires the sales-enablement step and 30-day retention. **Path B (Bedrock)** adds AWS to your stack but consolidates AI coverage under the AWS BAA and keeps PHI from ever leaving AWS — attractive if you'll add other AWS services. **Confirm current terms with both vendors before committing**, and pick one path per data flow.

---

## 7. Practical data-handling gaps for a small startup

- **Know where PHI lives.** Map it explicitly: Supabase tables, Supabase Storage (lab photos/uploads), FastAPI memory/logs on Railway, Anthropic/Bedrock request payloads, backups. You can't protect what you haven't mapped. **Make sure PHI never lands in Stripe, analytics, or crash reporters.**
- **Data minimization / minimum necessary.** Collect and transmit only the PHI required to produce an explanation. Don't send the whole patient record to Claude if a subset works.
- **De-identification = the most powerful scope-reducer.** If you can strip the 18 HIPAA identifiers (Safe Harbor method) before data leaves your system — or before it hits the AI — that data **is no longer PHI** and falls outside HIPAA. For the AI calls especially, consider stripping/tokenizing direct identifiers before sending to the model. (Do this carefully; partial de-id is still PHI.)
- **Data retention + deletion.** Define retention periods. Implement **deletion on request** and **deletion at end of pilot**. Note the tension: Anthropic Covered Models require **30-day retention**, so "delete immediately everywhere" isn't literally true on the AI side — document this. Your BAA must let you **return/destroy PHI** when the clinic relationship ends.
- **Breach notification readiness.** Have the runbook (§4) and contact path to the clinic ready *now*, not during an incident. As a BA your clock is **≤60 days** from discovery to notify the Covered Entity.

---

## 8. Prioritized "pilot-ready" checklist (P0 / P1 / P2)

Target: a **minimum viable** compliant posture to run **one clinic pilot** — not enterprise-grade everything.

### P0 — Blockers (must be done before *any* PHI flows)
- [ ] **Healthcare attorney engaged** to review all BAAs and the data-flow analysis.
- [ ] **Upstream BAA signed with the pilot clinic/hospital.**
- [ ] **Downstream BAAs in place** for every PHI-touching subprocessor:
  - [ ] **Supabase** — Team plan + HIPAA add-on enabled + BAA signed; PHI only in HIPAA-enabled projects.
  - [ ] **Railway** — Enterprise track + BAA signed (note the monthly-commitment gate).
  - [ ] **Anthropic** (Path A: BAA signed + PHI enabled via sales) **or** **AWS/Bedrock** (Path B: AWS BAA, Bedrock-hosted Claude).
- [ ] **Stripe isolation confirmed** — verified architecturally that no PHI can enter Stripe.
- [ ] **TLS enforced end-to-end**; **encryption at rest confirmed** on Supabase + Railway.
- [ ] **Security Rule Risk Analysis** drafted and dated.
- [ ] **Security Officer + Privacy Officer** designated in writing.

### P1 — Strongly needed for a credible pilot
- [ ] **RLS / access controls + unique IDs** verified; least-privilege on keys.
- [ ] **MFA required** for clinician/Pro and admin accounts.
- [ ] **Audit logging** at app + DB level, with PHI scrubbed from log bodies.
- [ ] **Automatic logoff / session expiry** configured.
- [ ] **Incident response + breach notification runbook** written.
- [ ] **Workforce HIPAA training** completed and recorded.
- [ ] **Access grant/revoke (incl. offboarding) process** written.
- [ ] **Data retention + deletion** behavior defined and implemented (incl. end-of-pilot return/destroy).
- [ ] **Data-flow / PHI map** documented.
- [ ] **Workstation encryption** on all team devices with PHI access.

### P2 — Hardening / scale-up (do soon, not pilot blockers)
- [ ] **De-identification / tokenization** before AI calls to reduce scope.
- [ ] **Sanction policy** and full written policy set formalized.
- [ ] **Contingency / backup / DR plan** documented and tested.
- [ ] **Collect & retain SOC 2 / HIPAA reports** from Supabase, Railway, AWS.
- [ ] **Penetration test / security review** of the backend.
- [ ] **Consumer-side privacy compliance** (FTC Health Breach Notification Rule, WA My Health My Data, CCPA/CPRA) for the direct-to-user product.
- [ ] **Vendor/BAA register** maintained and reviewed periodically.

---

## Sources (verify current terms — these change)

- Anthropic — [Business Associate Agreements (BAA) for Commercial Customers](https://support.claude.com/en/articles/8114513-business-associate-agreements-baa-for-commercial-customers) · [HIPAA-ready Enterprise plans](https://support.claude.com/en/articles/13296973-hipaa-ready-enterprise-plans) · [Covered Models under a BAA](https://support.claude.com/en/articles/15455031-covered-models-under-a-business-associate-agreement-baa)
- Supabase — [HIPAA Compliance and Supabase](https://supabase.com/docs/guides/security/hipaa-compliance) · [HIPAA Projects](https://supabase.com/docs/guides/platform/hipaa-projects) · [Shared Responsibility Model](https://supabase.com/docs/guides/deployment/shared-responsibility-model)
- Railway — [Compliance docs](https://docs.railway.com/enterprise/compliance) · [Changelog: HIPAA BAAs](https://railway.com/changelog/2024-07-12-hipaa-baas)
- Stripe (HIPAA stance) — [Is Stripe HIPAA Compliant? (HIPAA Journal)](https://www.hipaajournal.com/is-stripe-hipaa-compliant/)
- Claude on AWS Bedrock — [HIPAA compliance for generative AI solutions on AWS](https://aws.amazon.com/blogs/industries/hipaa-compliance-for-generative-ai-solutions-on-aws/)

---

*Reminder: practical guidance, not legal advice. Confirm current vendor HIPAA terms and have a healthcare attorney review before signing any BAA or sending PHI anywhere.*

---

## Addendum — Coded terminology status (2026-07)

MedCompanion normalizes clinical free-text to standard codes via **NIH/NLM APIs** (codes are never model-generated):

| Data | Standard | Source | Status |
|---|---|---|---|
| Medications | RxNorm (RxCUI) | NIH RxNav | ✅ live, key-free |
| Labs | LOINC | NIH Clinical Tables | ✅ live, key-free |
| Conditions (billing) | ICD-10-CM | NIH Clinical Tables | ✅ live, key-free |
| Conditions (clinical) | **SNOMED CT** | NLM UMLS | ⏳ code-ready; set `UMLS_API_KEY` to activate |

**To activate SNOMED (≈10 min, free):** request a UMLS account + API key at
`https://uts.nlm.nih.gov/uts/signup-login` (SNOMED CT US edition is free under the
NLM/UMLS license), then set `UMLS_API_KEY` in Railway. `/code-config` will report
`snomed:true` and the app switches condition coding from ICD-10 to SNOMED automatically.
Not-yet: SNOMED requires accepting the UMLS license — a governance step, not code.
