# MedCompanion AI — Regulatory & Licensing Overview (for investors)

**Not legal advice.** This is a plain-language landscape summary to brief investors. Before launch/scale, obtain a formal written opinion from a **healthcare regulatory attorney** (FDA + digital health). Investors will expect this; it is normal diligence.

## The headline
MedCompanion AI is **deliberately designed as a general health-information and education tool — NOT a medical device and NOT the practice of medicine.** Every result is framed as "understand and prepare to talk to your doctor," with disclaimers, a human-in-the-loop step, and no individualized diagnosis or treatment. **That design is the strategy: it keeps the app in the lighter-regulation lane** (no FDA premarket clearance required) rather than the heavy Software-as-a-Medical-Device lane. The product decisions we already made (no diagnosis, defer to the clinician, "not for emergencies") are what preserve that position.

## 1. FDA — Software as a Medical Device (SaMD) — the big one
- US software that **diagnoses, treats, or drives a specific clinical decision** is an FDA-regulated device (may need 510(k)/De Novo clearance).
- The **21st Century Cures Act** and FDA's Clinical Decision Support / General Wellness guidance generally **exclude** software that provides **general information, education, and references** and lets the user/clinician independently review the basis — which is how MedCompanion is positioned.
- **Risk areas to watch (keep informational, not diagnostic):** the ER-or-not triage, lab/image interpretation, and medication-interaction features. As built they say "this is not a diagnosis — when in doubt, seek care," which supports the non-device position. A regulatory attorney should confirm the classification of these specific features.
- **Likely outcome:** non-device / no FDA clearance **if** positioning and disclaimers are maintained — but this needs a formal SaMD determination.

## 2. HIPAA + health-data privacy (compliance, not a "license")
- HIPAA applies only if we are a **covered entity or business associate.** A consumer app users choose may **not** be a HIPAA covered entity — but it is then governed by the **FTC Act + FTC Health Breach Notification Rule** and **state laws.**
- Because licensed physicians review patient-submitted content (the review board), counsel should confirm whether/where HIPAA attaches.
- **State health-data laws matter a lot now:** Washington's **My Health My Data Act**, Nevada SB370, and **CCPA/CPRA** (California) impose consent, disclosure, and data-rights requirements on health apps. We already built consent at signup + data export/delete.
- **GDPR/UK** apply if we serve EU/UK users.
- Action: sign **BAAs** with Anthropic, Supabase, and the host before any compliance claim; maintain the privacy policy; do a data-protection assessment.

## 3. State medical-practice / corporate practice of medicine
- We do **not** practice medicine: no diagnosis, no doctor-patient relationship, physicians only review general information for accuracy. This is the key mitigation.
- Physician reviewers should be **licensed** in relevant states; their advisory agreement states no doctor-patient relationship is formed.
- **If we ever add real telehealth/care delivery**, that triggers provider licensing in each state and likely a "friendly-PC / MSO" corporate structure — a much bigger regulatory step. Not in scope today.

## 4. The Advocate features (bills, appeals, letters) — UPL note
- Drafting dispute/appeal/records letters as **self-help templates the user reviews and sends** is generally fine. Avoid giving **specific legal advice** (which could raise unauthorized-practice-of-law questions). Keep the "general guidance, not legal advice" framing we built in.

## 5. FTC / advertising claims
- The FTC regulates health claims. Marketing must be **truthful and substantiated** — avoid implying diagnosis, cure, or outcomes. "Not HIPAA compliant" must not be claimed until BAAs are signed.

## 6. Standard business items
- The LLC (Millennials Creatives LLC) is registered; maintain general business licensing. 
- Carry **liability insurance** (technology errors & omissions / professional liability) — investors will ask. Not a license, but expected.

## 7. International (only if/when we expand)
- **EU MDR** and **UK MHRA** treat health software more strictly; a "device" classification there can require CE/UKCA marking. Scope per market before launching abroad.

## What this means for investors (the soundbite)
- **No FDA premarket clearance is anticipated** under the current information-only design — the main near-term needs are **privacy compliance (BAAs + state health-data laws), truthful-claims discipline, and liability insurance**, plus a **formal regulatory opinion** to confirm the SaMD classification.
- The biggest regulatory *decisions* are triggered only if we change the product into **diagnosis, autonomous triage, or telehealth** — each of which we would scope with counsel before building.

## Recommended next step
Engage a **digital-health regulatory attorney** for: (1) a written SaMD/FDA determination on the current feature set, (2) a HIPAA-applicability + state-privacy (WA/NV/CA) memo, and (3) review of marketing claims and the advisory/BAA agreements. Budget for this in the raise.
