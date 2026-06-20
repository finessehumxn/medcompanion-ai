# MedCompanion AI — HIPAA readiness (honest status)

**Read this with your clinical co-founder and a healthcare attorney before claiming "HIPAA compliant."**

## The honest truth
HIPAA compliance is a **legal + operational** state, not a code feature. We have built the *technical foundation*, but you are **not** compliant until the legal steps below are done. **Do not advertise "HIPAA compliant" until then.**

## First question: are we even a HIPAA "covered entity"?
A consumer app a person chooses to use is often **not** a HIPAA covered entity — that data may be governed instead by the **FTC Act + FTC Health Breach Notification Rule** and **state privacy laws (e.g. CCPA)**. BUT once licensed physicians review patient data through our portal, and if we integrate with providers, we may cross into HIPAA territory. **Only a healthcare attorney can make this call.** Get that opinion before marketing.

## What is built (technical foundation — done)
- ✅ Real accounts (email + password) via Supabase Auth.
- ✅ Health data (symptom logs, sessions) stored per-user with Row-Level Security (users only see their own).
- ✅ Encryption in transit (HTTPS) and at rest (Supabase/Postgres default).
- ✅ Data minimization — we store only what the feature needs.
- ✅ The app works fully **without** an account (logging is opt-in).

## What YOU must do to actually be HIPAA-ready (legal/operational)
1. **Sign BAAs (Business Associate Agreements)** with every vendor that touches health data:
   - **Anthropic (Claude API):** offers a BAA + Zero Data Retention for healthcare — request it.
   - **Supabase:** HIPAA is available on paid plans with a signed BAA + the HIPAA add-on — enable it.
   - **Railway:** confirm a BAA is available, or move the backend to a HIPAA-eligible host (AWS/GCP/Azure under BAA).
   - Any other processor (email, analytics) — BAA or remove it.
2. **Turn off / isolate non-compliant services** (e.g. any analytics that sees PHI).
3. **Add the operational safeguards:** access controls + audit logging, a written risk assessment, breach-notification procedure, written privacy/security policies, and workforce training.
4. **Add patient rights flows:** data export and account/data deletion on request (we can build these next).
5. **Get a healthcare attorney** to review the above and your marketing claims.

## Recommended near-term posture (safe + honest)
Until BAAs are signed, market as: **"Private and secure. We never sell your data."** — not "HIPAA compliant."
This is true today and avoids legal exposure. Flip to a compliance claim only after counsel signs off.

## What we can build next (technical, on request)
- One-tap **export my data** and **delete my account + data**.
- **Audit log** of access to a record.
- Field-level encryption for the most sensitive notes.
- A consent screen at signup describing exactly what is stored and why.
