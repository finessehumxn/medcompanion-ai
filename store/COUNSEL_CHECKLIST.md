# Questions for a Digital-Health Regulatory Attorney
**Hand this to counsel so the engagement is focused and fast.** Goal: a written opinion covering FDA classification, privacy, and claims for MedCompanion AI (a general health-information app by Millennials Creatives LLC). Live product: https://medcompanion-ai.up.railway.app/app

## A. FDA / Software as a Medical Device (SaMD)
1. Based on the current feature set, is MedCompanion a **medical device** under the FD&C Act, or is it excluded as **general wellness / clinical decision support / information** under the 21st Century Cures Act and FDA's CDS and General Wellness guidance? Please issue a written **SaMD determination**.
2. Specifically classify these features, which are the closest calls:
   - The **ER-or-not triage** (urgency guidance)
   - **Lab / image reading** (plain-language explanation of an uploaded result)
   - **Medication-interaction checker** and **Pharmacist** mode
   - The **symptom -> possible-condition** normalization step
3. What exact **language, disclaimers, and UI guardrails** must we maintain to stay in the non-device lane?
4. If any feature is a device, is it **510(k), De Novo, or enforcement-discretion**, and what is the path/cost/timeline?

## B. HIPAA & privacy
5. Are we a **HIPAA covered entity or business associate** — and does that change because licensed physicians review user-submitted content through our portal?
6. If not HIPAA, confirm obligations under the **FTC Act + FTC Health Breach Notification Rule.**
7. Which **state health-data laws** apply (e.g., Washington **My Health My Data Act**, Nevada SB370, **CCPA/CPRA**), and what consent / disclosure / data-rights changes do we need?
8. Review our **privacy policy, signup consent, and data export/delete** for sufficiency.
9. Which vendors need a signed **BAA** (Anthropic/Claude, Supabase, hosting), and can you confirm each offers one?
10. Do we need anything before we may **market the app as "HIPAA compliant"**?

## C. Practice of medicine / clinical governance
11. Does anything we do constitute the **practice of medicine** or create a **doctor-patient relationship** (especially the physician-review/co-sign feature)?
12. In which states must our **reviewing physicians be licensed**, and how should the **"Reviewed by a licensed physician"** badge be worded to avoid implying individualized care?
13. Review the **Medical Advisory Board / advisor agreement** (equity advisors) for the no-doctor-patient-relationship and liability terms.
14. What would change if we later add **telehealth** (corporate practice of medicine, friendly-PC/MSO, state licensure)?

## D. The Advocate features (bills, appeals, records, consent letters)
15. Does drafting **dispute/appeal/records-request letters** as self-help templates risk **unauthorized practice of law**, and what framing keeps it safe?

## E. Marketing claims & insurance
16. Review our **marketing claims** (app store listing, website) for FTC truthfulness/substantiation.
17. What **liability insurance** do you recommend (technology E&O / professional liability), and at what coverage level for our stage?

## F. International (only if we expand)
18. What triggers **EU MDR / UK MHRA** device classification, and what is required before serving EU/UK users?

## Deliverables we want
- A written **SaMD/FDA determination** on the current feature set.
- A **HIPAA-applicability + state-privacy memo** (WA/NV/CA at minimum).
- A short **claims review** + redlines to the advisor/BAA agreements.
