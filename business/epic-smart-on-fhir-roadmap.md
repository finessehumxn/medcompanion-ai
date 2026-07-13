# MedCompanion AI — Epic SMART on FHIR Integration Roadmap

**Owner:** Millennials Creatives LLC
**Product:** MedCompanion AI — plain-language explanations of diagnoses, lab results, and medical bills across 15+ languages, with patient handouts and a clinician "Pro" tier.
**Current state:** Capacitor mobile app (iOS + Android) + web app (medcompanionai.com) + FastAPI/Python backend calling the Anthropic (Claude) API.
**Positioning:** *OpenEvidence helps clinicians FIND the evidence; MedCompanion helps them EXPLAIN it to the patient.*

**Status:** Planning document. Last updated 2026-06-29.

---

## 0. Update (2026-07-12) — the patient-standalone flow is now BUILT (sandbox-ready)

The **patient standalone / MyChart** launch (Section 3, the consumer path) is implemented in the app and deployed. What's live and unit-verified today:

- **In-app:** *My Records → "🏥 Connect Epic / MyChart (sign in)"* runs a full **SMART-on-FHIR authorization-code + PKCE** flow. PKCE `S256` was verified against a reference vector (exact match); the authorize URL includes `response_type, client_id, redirect_uri, scope, state, aud, code_challenge, code_challenge_method=S256`.
- **Backend proxies** (dodge browser CORS, keep tokens transient — **nothing stored**): `GET /epic/config`, `POST /epic/token` (public client + PKCE, no secret), `POST /epic/records` (reads `Observation` (laboratory), `Condition`, `MedicationRequest`, `AllergyIntolerance` for the patient).
- **Mapping:** fetched FHIR runs through `window.fhirToRecords()` — verified against Epic R4 shapes (LOINC coding, `referenceRange.text`, `medicationReference`→contained, ICD-10 Conditions) → lands in My Records → "Explain my records."
- **Defaults point at Epic's public sandbox.** `configured:false` until `EPIC_CLIENT_ID` is set; until then the button falls back to file import.

### To turn it on in the sandbox (≈15 min, free)
1. Create a free account at **fhir.epic.com** → **Build Apps** → new app, type **Patients (standalone)**, **FHIR R4**.
2. Set **Redirect URI** to exactly `https://medcompanion-ai.up.railway.app/app` (matches `EPIC_REDIRECT_URI`).
3. Select scopes: `openid fhirUser patient/Patient.read patient/Observation.read patient/Condition.read patient/MedicationRequest.read patient/AllergyIntolerance.read`.
4. Copy the **(non-production) Client ID** → set it as `EPIC_CLIENT_ID` in Railway (Variables → Deploy). `/epic/config` will then report `configured:true`.
5. In the app tap **Connect Epic / MyChart**, sign in with an **open.epic.com sandbox test patient** (e.g. *Camila Lopez* / documented credentials), consent → records import.

### What is still gated (unchanged from below)
- **Production at a real hospital** still requires a **sponsoring health system** to enable your production Client ID against their environment (Section 2) — no code closes that gap.
- **Provider-facing EHR launch** (inside Hyperspace/Hyperdrive) and **App Orchard/Showroom** listing remain the business/partnership track.
- **PHI + BAA gates** (Section 6) apply before real patient data flows in production.

> **Honesty note up front.** Integrating into Epic is a serious, multi-month effort gated by a paid vendor program, a security review, and — critically — the willingness of a hospital customer to sponsor you in production. The first 80% of the *technical* build (sandbox prototype) is achievable in weeks by a competent engineer. The last 20% (getting live at a real site) is mostly process, contracts, and security, and is measured in months. Where exact Epic program names or fees are version-dependent, this document flags the uncertainty rather than asserting a number as gospel. **Confirm all fees, tier names, and timelines directly with Epic before budgeting against them** — Epic renamed this program recently and figures circulating online are inconsistent.

---

## 1. What SMART on FHIR is, and how apps embed in Epic

**FHIR** (Fast Healthcare Interoperability Resources) is the HL7 standard data model for healthcare. Clinical facts are represented as *resources* — `Patient`, `Condition`, `Observation`, etc. — exposed over a REST API. Epic's current production API is **FHIR R4**.

**SMART on FHIR** is the open standard (from the SMART Health IT project) that layers **OAuth 2.0 / OpenID Connect authorization** and a **standard app-launch handshake** on top of FHIR. It is what lets a third-party app:

1. Be launched from inside (or alongside) the EHR,
2. Obtain an access token scoped to specific data and a specific patient, and
3. Read FHIR resources through the EHR's API — without the app vendor ever holding the hospital's database credentials.

Epic implements SMART on FHIR. There are **two embedding surfaces** that matter for MedCompanion:

### Provider-facing (clinician) launch — Hyperspace / Hyperdrive
- Epic's clinician desktop is **Hyperspace** (the classic Windows client) and **Hyperdrive** (the newer Chromium-based client that hosts web content natively). Web/SMART apps render inside an embedded browser frame.
- A clinician working in a patient's chart clicks a button/activity that **EHR-launches** MedCompanion. Epic passes a `launch` token and its FHIR endpoint; MedCompanion completes an OAuth handshake and is handed the **current patient context** automatically — no patient lookup, no manual ID entry.
- This is the **"Pro" tier home run**: the clinician is already in the chart, MedCompanion pulls the active diagnoses and recent labs, and produces a plain-language handout in the patient's language in seconds.

### Patient-facing launch — MyChart
- **MyChart** is Epic's patient portal (web + mobile). Patients see their own conditions, results, visit summaries, and bills.
- A SMART app can be surfaced to patients in two ways:
  - **Embedded/linked from MyChart** ("Connect my account" style), or
  - **Patient standalone launch** — the patient starts in MedCompanion, is redirected to MyChart to log in and consent, and MedCompanion receives a token scoped to *that patient's own data*.
- This maps directly to MedCompanion's consumer product: a patient connects their chart and gets every result and diagnosis explained in plain language, in their language.

> Both surfaces use the same SMART/OAuth machinery. The difference is **who authenticates** (a clinician vs. the patient) and **whose context** you receive.

---

## 2. Epic's third-party developer program (the business gate)

Epic's program has been **renamed and reorganized recently**, and the public terminology is genuinely confusing. Here is the accurate shape, with explicit uncertainty flags.

### Program names — what changed
- **"App Orchard"** was the legacy program/marketplace name. It is **deprecated**. Do not build a plan around that brand.
- The current ecosystem is generally referred to as **Epic Showroom** (the customer-facing gallery where hospitals discover integrations) plus **Vendor Services / Connection Hub** (the developer-side membership, registration, and listing mechanics).
- Reporting indicates Showroom is organized into tiers (commonly described as **Connection Hub**, **Toolbox**, and **Workshop**), corresponding roughly to data-integration listings, deeper/recommended integration patterns, and co-development partnerships.
- ⚠️ **Uncertainty:** the exact current tier names, what each includes, and which tier a "read FHIR, generate a handout" app belongs in are **not something I can state with certainty** — Epic moves these. Verify on Epic's developer site and with an Epic rep.

### The two portals you actually touch
| Portal | What it's for |
|---|---|
| **fhir.epic.com** ("Epic on FHIR") | Developer hub. Register app records, get **Client IDs**, read API/FHIR/SMART/CDS Hooks docs, access the sandbox. **Self-service and free to start.** |
| **open.epic.com** | Open developer resources + sandbox **test data / test patient credentials**. Public, no membership required. |

**Important and good-news distinction:** You do **not** need to pay Epic or be a marketplace member to *register an app and build/test against the sandbox*. Registration on fhir.epic.com is self-service. Membership/fees become relevant when you want to **list in Showroom** and/or go to **production**.

### Realistic costs / fees
⚠️ **Treat all numbers below as "verify before you budget."** Figures online are inconsistent and Epic does not publish a clean price list.

- **Sandbox + app registration on fhir.epic.com:** effectively **free**. This is where your MVP lives for the first phase.
- **Vendor Services / developer membership:** widely reported in the **low four figures per year** (numbers around ~$1,900/yr circulate, but this is unconfirmed and likely tier/usage dependent). Unlocks the formal program path.
- **Connection Hub / Showroom listing:** an additional **annual listing fee** is commonly cited (numbers around ~$500/yr circulate). Unconfirmed.
- **Bigger, less visible costs** are not Epic's line-item fees — they are: engineering time, a **security review / questionnaire**, possible third-party security attestation, legal/contract review, and the **business-development cost of landing a sponsoring hospital**.

### The customer-sponsorship reality (the single most important point)
**You cannot unilaterally "turn on" a connection to a hospital's live Epic.** Production access requires a **participating Epic customer (a hospital/health system) to enable and authorize your app against their environment.** Practically:

- A hospital must **decide to use MedCompanion**, then have their Epic team register/enable your client ID for their production environment and grant the FHIR scopes.
- This means **your real go-to-market gate is a hospital champion**, not Epic's portal. The first production site effectively co-pilots the integration with you.
- Pricing/contracting with the hospital is a separate commercial negotiation from anything you pay Epic.

> **Strategic implication for MedCompanion:** Land a pilot health system *before* (or in parallel with) heavy production-integration spend. The sandbox build is cheap; the production path only unlocks once a customer pulls you in.

---

## 3. The three SMART launch types — when to use each

| Launch type | Who authenticates | Context you get | MedCompanion use case |
|---|---|---|---|
| **EHR launch** (provider) | Clinician, via Epic SSO | Current patient (+ encounter) handed to you | **Pro tier inside Hyperspace/Hyperdrive.** Clinician opens MedCompanion in-chart → instant handout. **Highest-value, build first.** |
| **Standalone / patient launch** (MyChart) | The patient | The patient's own record | **Consumer product.** Patient connects their chart in the MedCompanion app/web → explains their own results/diagnoses/bills. |
| **Backend services** (system / client-credentials, SMART Backend Services) | No human; app authenticates with a signed JWT (asymmetric key) | Whatever the org grants at the system level | **Batch / no-user-present** jobs — e.g., pre-generating handouts for a cohort, or server-to-server pipelines. **Not the MVP.** Heavier trust bar; needs org-level authorization. |

**Rule of thumb:**
- A **human is present and it's their/the patient's chart** → EHR launch (clinician) or standalone (patient).
- **No human, server-driven, bulk** → backend services.

For MedCompanion, **EHR launch is the MVP**, **standalone/MyChart is the consumer scale-out**, and **backend services is a later optimization** — not a starting point.

---

## 4. FHIR resources MedCompanion consumes (and what each becomes in-product)

All are FHIR **R4**. For a given patient you typically `GET` each resource type with `patient={id}` plus filters. MedCompanion is fundamentally a **read-only consumer** — it never writes back to the chart, which dramatically lowers the integration and security bar.

| FHIR resource | What it contains | What MedCompanion does with it |
|---|---|---|
| **Patient** | Demographics, identifiers, **preferred language**, age | Anchors the context; **drives which of the 15+ languages to render in** (use `communication.language`). |
| **Condition** | Active/resolved problems & diagnoses (often coded SNOMED/ICD-10) | Core input: turns "Type 2 diabetes mellitus with diabetic neuropathy" into a plain-language explanation of what it is and what it means for the patient. |
| **DiagnosticReport** | Grouped diagnostic results (lab panels, imaging, pathology), with narrative | Explains a **whole report** ("your metabolic panel") as a unit, and points at the constituent `Observation`s. |
| **Observation** (labs/vitals) | Individual results: value, unit, reference range, flags | The **"explain my lab result"** feature. Reads value + reference range + abnormal flag → "Your A1c is 8.1%, above the 5.7% normal range, which means…". |
| **MedicationRequest** | Prescribed/ordered medications, dose, instructions | Explains **what each medication is for and how to take it**, in plain language and the patient's language. |
| **DocumentReference** | Pointers to clinical documents (visit summaries, discharge instructions, notes), often PDF/CDA | Source material for **handout generation** and "explain my visit summary / discharge instructions." (Note: retrieval may require fetching the referenced binary/attachment.) |
| **AllergyIntolerance** | Allergies and intolerances + criticality | **Safety context.** Ensures explanations and medication guidance respect allergies; surfaces them in handouts. |

**Product mapping summary:**
- *"Explain my diagnosis"* → `Condition` (+ `Patient.language`)
- *"Explain my lab result"* → `Observation` / `DiagnosticReport`
- *"Explain my medication"* → `MedicationRequest` (+ `AllergyIntolerance` for safety)
- *"Explain my visit / discharge"* → `DocumentReference`
- *"Explain my bill"* → **largely outside clinical FHIR.** Billing maps to FHIR financial resources (`ExplanationOfBenefit`, `Claim`, `Coverage`) and/or 835/837 X12 data, whose availability via Epic's standard read API is limited and org-dependent. ⚠️ **Treat bill-explanation as a separate, harder track** — do not assume the medical-bill feature comes "for free" from the clinical FHIR integration.

> **Caveat:** Not every resource/field is exposed in every Epic org, and some require specific scopes the customer must grant. Confirm exact resource availability and field coverage in Epic's R4 API spec and against the sandbox.

---

## 5. Concrete technical build steps

### 5.1 The SMART App Launch / OAuth2 flow (EHR launch)
This is the standard SMART **authorization-code** flow:

1. **Launch.** Epic invokes your registered launch URL with `iss` (the FHIR base URL / issuer) and `launch` (an opaque launch token).
2. **Discover.** Fetch `{iss}/.well-known/smart-configuration` (or the FHIR `metadata` / CapabilityStatement) to learn the **authorize** and **token** endpoints.
3. **Authorize.** Redirect the browser to the authorize endpoint with `response_type=code`, your `client_id`, `redirect_uri`, the `launch` token, `scope`, `state`, and **PKCE** (`code_challenge`). The clinician is already SSO'd in Epic, so this is typically transparent.
4. **Token exchange.** Epic redirects back to your `redirect_uri` with a `code`. Your backend POSTs to the token endpoint (with PKCE `code_verifier`) and receives an `access_token`, the granted `scope`, and crucially a **`patient` context** (the FHIR `Patient` id).
5. **Call FHIR.** Use the bearer token to `GET` `Condition`, `Observation`, etc. for that patient.
6. **Refresh** as needed (if `offline_access`/refresh tokens are granted).

For **patient standalone**, the flow is identical except the **patient** authenticates via MyChart and consents; no `launch` token (you specify `aud` = the FHIR base instead).

For **backend services**, there is no browser: you authenticate with a **signed JWT client assertion** (asymmetric key you pre-register) at the token endpoint to get an app-level access token.

### 5.2 Scopes
SMART scopes look like `patient/Condition.read`, `patient/Observation.read`, `user/Patient.read`, `launch`, `openid`, `fhirUser`, `offline_access`. For MedCompanion's read-only MVP, request the **minimum**:
```
launch openid fhirUser
patient/Patient.read
patient/Condition.read
patient/Observation.read
patient/DiagnosticReport.read
patient/MedicationRequest.read
patient/AllergyIntolerance.read
patient/DocumentReference.read
```
- Use `patient/*` scopes for patient-context launches; `user/*` for broader clinician-context reads where appropriate.
- ⚠️ Epic supports both granular (SMART v2) and coarser scope styles depending on version; confirm the exact scope syntax Epic expects for your target version. **Request least privilege** — security reviewers reward this and customers grant it faster.

### 5.3 Register the app (fhir.epic.com)
1. Create an Epic developer account; in **Build Apps** create an app record.
2. Choose app type: **Patients (standalone)**, **Clinicians (EHR launch)**, or **Backend**.
3. Set **redirect URI(s)**, requested **FHIR R4 resources/scopes**, and (for backend) upload a **public key**.
4. Receive a **(non-production) Client ID**. Mark **"Ready for Sandbox."**
5. ⚠️ **Epic gotcha:** once an app is marked **production-ready, it cannot be edited** — changes require a **new app record / new Client ID**. Plan your scope set carefully before promoting.

### 5.4 Test against the sandbox
- Point your app at Epic's **sandbox FHIR endpoint** and use **open.epic.com** test patients/credentials.
- Validate the full loop: launch → authorize → token → read each resource → generate the handout.
- Test edge cases: missing `Patient.language`, empty problem list, labs with no reference range, allergies present, non-English patient.

### 5.5 Production connection (with a real Epic site)
- Requires a **sponsoring customer** (Section 2). The hospital's Epic team registers/enables your production Client ID against **their** environment and grants scopes.
- Each customer environment has **its own FHIR base URL**; your app must handle **per-customer endpoints** (don't hardcode one base URL). This is why step 1 of the launch (`iss` discovery) matters — you key off the issuer you're launched from.
- Complete Epic's **security review / questionnaire** and any program steps before go-live (Section 6).

---

## 6. Security / compliance gates that gate go-live

These tie to the companion HIPAA document; summary of what blocks production:

- **HIPAA.** You will handle **PHI**. You need a **Business Associate Agreement (BAA)** with each customer health system, and — because MedCompanion's backend calls the Anthropic (Claude) API — a **BAA with your AI/infra subprocessors** (Anthropic offers HIPAA-eligible/BAA arrangements; confirm and execute). No PHI should reach any subprocessor without a BAA in place.
- **Data minimization & retention.** Read least-privilege scopes; avoid persisting PHI unless required, and if you do, encrypt at rest, define retention/deletion, and log access.
- **Encryption in transit.** TLS everywhere; OAuth tokens and FHIR responses never logged in plaintext.
- **OAuth hygiene.** PKCE, exact redirect-URI matching, short-lived tokens, secure refresh-token storage, key rotation for backend services.
- **Epic's security review / vendor questionnaire.** Expect a formal questionnaire and possibly a request for security attestations (e.g., SOC 2 / HITRUST). Not having these slows or blocks enterprise customers even if Epic's minimum is met.
- **Auditability.** Log who/what accessed which patient's data and when.
- **Clinical-safety / scope-of-use posture.** MedCompanion explicitly does **not** diagnose; its guardrail pipeline (emergency/crisis detection, human-in-the-loop confirmation) is a compliance and trust asset — document it for reviewers and customers.

> ⚠️ Confirm current Anthropic HIPAA/BAA terms and any required configuration before sending **any** PHI to the Claude API. This is a hard gate, not a nice-to-have.

See: `business/` HIPAA companion document for the full compliance program.

---

## 7. Phased timeline & effort estimate

Honest framing: the **sandbox prototype is fast**; **production is slow** because it depends on a customer and a security process, not on your code. Estimates assume 1–2 competent engineers plus part-time business/compliance effort. **These are planning ranges, not commitments.**

| Phase | Goal | Eng effort | Calendar (incl. external waits) |
|---|---|---|---|
| **0. Prep** | Epic dev account, read R4 docs, design scope set | ~days | 1–2 weeks |
| **1. Sandbox prototype** | EHR-launch SMART app: launch → OAuth → read `Condition` + `Observation` → generate handout against sandbox patients | 2–4 weeks | 3–6 weeks |
| **2. Hardened MVP** | Add `MedicationRequest`, `AllergyIntolerance`, `DocumentReference`, language handling, error/edge cases; security hardening | 3–6 weeks | 1–2 months |
| **3. Compliance + program** | BAAs (incl. Anthropic), security questionnaire, Vendor Services membership, decide Showroom tier | mostly non-eng | 1–3 months (gated by reviews/contracts) |
| **4. Pilot site (production)** | Sponsoring hospital enables prod Client ID; live testing with real (consented) data; per-customer endpoint handling | 2–4 weeks eng + integration support | **2–4+ months**, dominated by the customer's IT schedule |
| **5. Marketplace listing / scale** | Showroom listing; repeatable onboarding for new customers; standalone/MyChart consumer flow | ongoing | 8–16 weeks for listing per public reports; ongoing thereafter |

**Realistic total to first live pilot:** roughly **4–9 months**, the back half gated almost entirely by **finding/landing a sponsoring health system** and clearing security/legal — not by engineering.

---

## 8. Pragmatic MVP-first sequencing

**Smallest valuable integration to build first:**

> **A provider-facing (EHR-launch) SMART app, embedded in Hyperspace/Hyperdrive, that reads the current patient's active `Condition`s and recent `Observation`s (labs) and produces a plain-language, patient-language handout — read-only, no write-back.**

Why this is the right first slice:
- **Highest value density:** the clinician is already in the chart; context is handed to you; output is immediate. It directly demonstrates the "OpenEvidence finds it, MedCompanion explains it" pitch.
- **Lowest risk:** **read-only** (no chart writes), **least-privilege scopes**, no patient-auth UX to build, no billing data.
- **Demoable in the sandbox** — you can show a sponsoring hospital a working integration **before** asking them to commit, which is exactly the artifact that lands a pilot.

**MVP build order:**
1. EHR-launch OAuth loop working against the Epic sandbox (auth code + PKCE, `patient` context).
2. Read `Condition` (active) + `Observation` (recent labs).
3. Feed into the existing FastAPI/Claude pipeline → generate the handout.
4. Use `Patient.communication.language` to pick the output language.
5. Add `MedicationRequest` + `AllergyIntolerance` (safety) once the core loop is solid.
6. Add `DocumentReference` (visit/discharge summaries) next.

**Deliberately deferred:**
- **Patient standalone / MyChart** flow (consumer scale-out) — comes after the clinician MVP proves the integration.
- **Medical-bill explanation** — depends on financial resources (`ExplanationOfBenefit`/`Claim`/`Coverage`) with limited/org-dependent read availability; **separate track**, do not block the MVP on it.
- **Backend / bulk** services — only once a customer needs cohort-scale handout generation.

---

## Open questions to confirm with Epic before committing budget
1. **Exact current program/tier names and fees** (Vendor Services / Connection Hub / Showroom / Toolbox / Workshop) — figures here are unconfirmed.
2. Which **scope syntax/version** (SMART v1 vs v2 granular) Epic expects for your target customers.
3. Real-world **availability of `DocumentReference` binaries** and **financial/billing resources** via standard read APIs.
4. Epic's current **security review requirements** and whether SOC 2 / HITRUST is expected for your target customers.
5. **Anthropic HIPAA/BAA** terms and required configuration for sending PHI to Claude.

---

### Sources
- [Epic on FHIR — Documentation](https://fhir.epic.com/Documentation)
- [open.epic — Developer Resources](https://open.epic.com/DeveloperResources)
- [Epic Showroom](https://showroom.epic.com/)
- [Epic launches new 'Showroom' website for 3rd-party apps (Fierce Healthcare)](https://www.fiercehealthcare.com/health-tech/epic-launches-new-showroom-website-3rd-party-apps-services)
- [Epic Showroom / App Orchard Publishing Guide (Saga IT)](https://saga-it.com/blog/epic-showroom-app-orchard-publishing)
- [Epic EHR API Integration reality guide (Invene)](https://www.invene.com/blog/epic-ehr-api-integration)
- [SMART App Launch (HL7 / SMART Health IT standard)](https://hl7.org/fhir/smart-app-launch/)

> All program names, fees, and timelines above should be re-verified directly with Epic; this document deliberately flags uncertainty rather than asserting unconfirmed specifics.
