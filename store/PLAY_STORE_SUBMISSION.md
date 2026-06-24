# MedCompanion AI — Google Play Store Submission (copy-paste ready)

Owner: **Millennials Creatives LLC** · Package: `com.medcompanionai.app`
Use this when filling out the Play Console "Main store listing," "App content," and "Data safety" sections.

---

## 1) App details

| Field | Value |
|---|---|
| **App name** (30 char max) | `MedCompanion AI` |
| **Category** | Medical (alt: Health & Fitness) |
| **Tags** | Health, Medical info, Symptom, Caregiver |
| **Email** | contact@millennialscreatives.com |
| **Website** | https://medcompanionai.com |
| **Privacy Policy URL** | https://medcompanionai.com/privacy |

> ⚠️ A valid, reachable **Privacy Policy URL is mandatory** for health apps. Confirm `/privacy` loads before submitting.

---

## 2) Short description (80 characters max)

```
Understand your health in plain language and prepare to talk with your doctor.
```
(78 chars)

---

## 3) Full description (4000 characters max)

```
MedCompanion AI helps you understand your health in plain language and walk into every appointment prepared — so you can partner with your doctor, not replace them.

Health information is overwhelming. Lab results, diagnoses, medication labels, and insurance letters are written for clinicians, not for you. MedCompanion AI translates all of it into clear, calm, everyday language and helps you ask better questions — always pointing you back to your own licensed clinician for diagnosis and treatment.

WHAT YOU CAN DO

• Understand your results — Paste a lab result, diagnosis, or doctor's note and get a plain-language explanation with the medical terms decoded.
• Check medication & food interactions — See how medications, supplements, and foods may interact, so you know what to ask your pharmacist or doctor.
• Prep for your visit — Turn what you're feeling into a focused, organized summary for your appointment — plus a clear list of questions to ask.
• Healthcare Advocate — Decode a confusing medical bill, understand what you're being asked to sign, and make sense of your insurance coverage.
• Log symptoms over time — Keep a private health journal so you can show your doctor how long something's been going on and how it's changed.
• Read it aloud — Have explanations read to you in a warm, conversational way — great for caregivers and loved ones.
• 15+ languages — Get information in the language you're most comfortable with.

BUILT TO WORK WITH YOUR DOCTOR
MedCompanion AI is an information and preparation tool. It does not diagnose, treat, or replace professional medical care. Every answer encourages you to confirm with your own clinician, and built-in safety guardrails route urgent or emergency situations to call 911 or your local emergency number.

WHO IT'S FOR
Everyday people, caregivers, parents, patients managing a new diagnosis, and anyone who wants to feel less alone and more prepared in the healthcare system.

PRIVACY FIRST
Your information is yours. We never sell your data. You can export or delete your account information at any time.

MedCompanion AI is a product of Millennials Creatives LLC.

IMPORTANT: MedCompanion AI provides general health information for educational purposes and is not a medical device. It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have. If you think you may have a medical emergency, call your doctor or 911 immediately.
```

---

## 4) Content rating questionnaire (IARC) — answers

Category to select: **Reference, News, or Educational** (or "Utility"). Then answer:

| Question | Answer |
|---|---|
| Violence | No |
| Sexuality / nudity | No |
| Profanity / crude humor | No |
| Controlled substances (depicts/encourages illegal drugs, alcohol, tobacco) | **No** — medication-safety education is not depiction/encouragement of illegal drug use |
| Gambling | No |
| Scary/disturbing content | No |
| User-generated content / social features | **Yes** (the app has a chat/companion + symptom log the user types into; if asked, note there is no public sharing between users) |
| Shares user location | No |
| Digital purchases | No |

**Expected result: Everyone / PEGI 3.** (Health/medical references alone don't raise the rating.)

> If asked "Does the app provide medical/health information?" answer **Yes** and that it is **educational/informational, not diagnostic**.

---

## 5) Data safety form — answers

**Does your app collect or share user data?** Yes (collect). **Sell data?** No.

**Data collected:**

| Data type | Collected? | Shared? | Processing | Purpose |
|---|---|---|---|---|
| Email address | Yes | No | Can't be made optional (account) | Account management |
| Name (if entered) | Optional | No | Optional | Account, personalization |
| Health info (symptom logs, health questions you type) | Yes | No | Optional (you choose to log) | App functionality |
| App activity / interactions | Yes | No | — | Analytics, app functionality |
| Crash logs & diagnostics | Yes | No | — | App stability |

**Security practices (check these):**
- ✅ Data is **encrypted in transit**.
- ✅ Users **can request that data be deleted** (in-app account deletion / `/user/delete`).
- ✅ You have a way for users to **export** their data (`/user/export`).
- ✅ Committed to follow the Google Play **Families / Health** policies as applicable.

> Answer truthfully to match what the app actually does. Because it handles **health data**, fill the health-data rows carefully and make sure the Privacy Policy explicitly describes health-data handling, retention, and deletion.

---

## 6) "What's new" (release notes, 500 char max)

```
Welcome to MedCompanion AI! Understand your health in plain language and prepare to partner with your doctor:
• Plain-language explanations of results, diagnoses & notes
• Medication, food & supplement interaction checks
• Visit prep with a question list
• Healthcare Advocate for bills, coverage & "what am I signing"
• Private symptom log over time
• Conversational read-aloud + 15 languages
Always works with your clinician — never replaces them.
```

---

## 7) Required graphic assets (have these ready to upload)

| Asset | Spec |
|---|---|
| App icon | 512×512 PNG, 32-bit |
| Feature graphic | 1024×500 PNG/JPG |
| Phone screenshots | 2–8, min 320px, 16:9 or 9:16 (PNG/JPG) |
| (optional) 7" / 10" tablet screenshots | recommended |

> These can be generated from `store/gen-med-store.cjs`. If you need them rebuilt to spec, say the word.

---

## 8) Pre-launch checklist / known Play review risks

1. **Privacy Policy must load** at the URL above and must cover health data. ✅ before submit.
2. **Webview/remote-content note:** the app loads the live web app. Google occasionally flags thin "webview wrapper" apps — MedCompanion is a substantive health service, which mitigates this, but be ready to explain it in the review notes if asked.
3. **Health content policy:** Do not state or imply diagnosis/treatment or "medically approved." The listing above uses "information / educational / works with your doctor" language on purpose.
4. **Account deletion link:** Play requires an account-deletion path for apps with accounts — we have `/user/delete`. Add the **"Delete account" URL** in the Data safety / App content section.
5. **Target audience:** select adults / 13+ (not "designed for families/children") to avoid the stricter Families policy, since it's a health-info tool.
6. **Ads:** select **No ads** (unless you add them).

---

### Submission order in Play Console
1. Create app → name `MedCompanion AI`, language English (US), App (not Game), Free.
2. Fill **Main store listing** (sections 1–3, 7 above).
3. **App content**: privacy policy, ads, content rating (4), target audience, data safety (5), government/health declarations, account deletion.
4. **Production → Create release** → upload `app-release.aab` → paste "What's new" (6) → roll out.
