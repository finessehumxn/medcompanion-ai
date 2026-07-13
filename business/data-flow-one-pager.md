# MedCompanion AI — Data-Flow One-Pager

**For:** hospital / clinic privacy & security teams evaluating a pilot
**Company:** Millennials Creatives LLC · **Product:** MedCompanion AI
**Last reviewed:** 2026-07-12
**Verify any claim here live:** `curl https://medcompanion-ai.up.railway.app/data-policy` · human version at `/trust`

> Practical guidance, not legal advice. Confirm current vendor terms and have counsel review before PHI flows. This one-pager is the short read; the full control set is in **[hipaa-baa-readiness.md](hipaa-baa-readiness.md)**.

---

## The 60-second summary

MedCompanion is built **local-first, AI-optional, human-in-control**:

1. **Your patients' data lives on their phone.** Health Journal check-ins and My Records entries are stored only in the device's local storage. Opening the app uploads nothing.
2. **The AI sees data only when the user taps a feature** — and only the specific text for that one task, to generate the answer.
3. **Nothing health-related is stored on our server by default.** The AI endpoints are **stateless** (answer-and-forget). Server-side history is off unless a deployment explicitly sets `MC_STORE_HISTORY=1` with disclosure + consent.
4. **Text AI is single-vendor: Anthropic (Claude).** Fewer parties = smaller trust surface.
5. **The user can turn AI fully off** (core app still works) and **delete everything on the device** in one tap.
6. **It's verifiable, not just asserted.** The running server publishes its data policy as machine-readable JSON at `/data-policy`.

---

## Data flow (default consumer configuration)

```
   ┌─────────────────────────────┐
   │  Patient's phone (the app)  │
   │  • Journal check-ins        │   ← stored ONLY here (localStorage)
   │  • My Records (labs/meds)   │
   │  • Visit sheet              │
   └───────────────┬─────────────┘
                   │  ONLY when the user taps an AI feature,
                   │  and only the text for that task
                   ▼
   ┌─────────────────────────────┐
   │  MedCompanion API (Railway) │   ← stateless: processes, returns,
   │  FastAPI, HTTPS/TLS         │     does NOT write health content to a DB
   └───────┬──────────────┬──────┘
           │ text         │ voice (optional, if used)
           ▼              ▼
   ┌───────────────┐  ┌──────────────────────┐
   │ Anthropic     │  │ OpenAI / Groq         │
   │ (Claude) —    │  │ (Whisper STT / TTS) — │
   │ explanations, │  │ transcribe / read-    │
   │ summaries     │  │ aloud, not retained   │
   └───────────────┘  └──────────────────────┘

   Shared-link visit sheet: travels inside the URL #fragment,
   which browsers never send to any server → we store zero PHI for it.
```

---

## Data categories & where each lives

| Data | Where it lives | Stored on our server? |
|---|---|---|
| Journal check-ins (symptoms, severity, mood, sleep, notes) | Device localStorage | **No** (default) |
| My Records (labs, medications, conditions) | Device localStorage | **No** (default) |
| Visit sheet | Device + the shareable link's `#fragment` | **No** |
| Text sent to AI on a tap | Transits to Anthropic to generate the answer | **No** — not persisted by us |
| Voice audio (if voice features used) | Transits to OpenAI/Groq for STT/TTS | **No** — not retained by us |
| Account/history (only if `MC_STORE_HISTORY=1`) | Supabase | **Only if explicitly enabled** |

---

## Subprocessors (current, minimal set)

Verify each vendor's current HIPAA terms before relying on this; details + the P0/P1/P2 BAA checklist are in **hipaa-baa-readiness.md §2**.

| Subprocessor | Role | Touches PHI? | BAA path |
|---|---|---|---|
| **Anthropic (Claude)** | Text AI (explanations, summaries) | Yes, on a tap | Anthropic BAA (sales-enabled; note Covered-Model 30-day retention) **or** Claude via AWS Bedrock under the AWS BAA |
| **OpenAI** | Voice STT/TTS (optional) | Yes, if voice used | OpenAI offers BAA + zero-retention for API — **verify & sign before PHI voice** |
| **Groq** | Voice STT fallback (optional) | Yes, if used | BAA availability less established — **verify; prefer a BAA-covered vendor or disable for PHI** |
| **Railway** | Hosting/compute | Yes (transits) | Enterprise-track BAA (monthly-commitment gate) |
| **Supabase** | DB/Auth — **only if history enabled** | Only if `MC_STORE_HISTORY=1` | Team plan + HIPAA add-on + BAA; **not in the data path by default** |
| **Stripe** | Payments | Should be **No** | No BAA — keep PHI out of Stripe entirely |

**Key point for reviewers:** in the default configuration, the only subprocessors that touch health content are the **AI vendors on a per-tap basis** (Anthropic for text; OpenAI/Groq for voice if used) and **Railway** as the transit host. Supabase is **not** in the health-data path unless history is deliberately turned on.

---

## Controls in place today (verifiable now)

- ✅ **No server-side storage of health content by default** (`server_stores_health_content: false` in `/data-policy`).
- ✅ **Health content is not written to our logs** (provider error bodies are not logged).
- ✅ **Single text-AI vendor** (Anthropic) — minimized surface.
- ✅ **Explicit per-action consent** in the app before anything is sent to AI.
- ✅ **AI master off-switch** and **one-tap delete-everything** on device.
- ✅ **TLS/HTTPS** for all transit.
- ✅ **Published, machine-readable data policy** for independent verification.

## What is NOT yet done (honest gap → the pilot roadmap)

These are required before PHI flows *on behalf of a covered entity* and are tracked in **hipaa-baa-readiness.md**:

- ✍️ **Signed BAAs** — upstream (the clinic) and downstream (Anthropic/Bedrock, OpenAI, Railway, and Supabase if history is enabled).
- ✍️ **Zero-data-retention / covered-model configuration** confirmed per AI vendor.
- ✍️ **HIPAA Security Rule program** — risk analysis, named Security/Privacy Officers, workforce training, incident-response + breach-notification runbook.
- ✍️ **SOC 2 Type II** audit (start with a readiness assessment).
- ✍️ **De-identification/tokenization** before AI calls, to shrink scope further.

---

## How a reviewer can verify us in 2 minutes

1. `curl https://medcompanion-ai.up.railway.app/data-policy` → the running server's own statement of what it does with data.
2. Visit `/trust` → the same facts, human-readable, pulled live into the page.
3. In the app → **"Your data & AI"** shows the same live facts, the AI off-switch, and delete-everything.

**Contact:** finessehumxn@gmail.com — we'll share the current risk analysis and BAA status on request. We would rather state exactly where we are than overstate it.
