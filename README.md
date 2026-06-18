# MedCompanion AI

**A safety-first patient health-briefing assistant built on a multi-node LangGraph pipeline.**

[![Stack](https://img.shields.io/badge/Stack-LangGraph%20%7C%20FastAPI%20%7C%20Claude-blue?style=flat)]()
[![Domain](https://img.shields.io/badge/Domain-Healthcare%20AI%20%7C%20Safety-purple?style=flat)]()
[![Deploy](https://img.shields.io/badge/Deployed-Railway%20%7C%20Capacitor-brightgreen?style=flat)]()

---

## What it does

MedCompanion AI turns a patient's plain-language description of how they feel ("my blood sugar is high and my feet tingle") into a **warm, sourced, easy-to-understand health briefing** — without ever pretending to be a doctor. Every request flows through an explicit safety pipeline that catches emergencies and crisis signals *before* any briefing is generated, and pauses for the patient to confirm what's being looked up.

The design priority is not raw capability — it's **what the system does when the input is ambiguous, emotionally loaded, or safety-critical.**

---

## Architecture

The core is a **LangGraph `StateGraph`** with a shared `PatientState`, composed of five purpose-built nodes. The graph interrupts midway for human confirmation, then resumes — a real human-in-the-loop checkpoint, not a cosmetic one.

```
raw input
   │
   ▼
┌──────────────┐   pass / emergency / crisis / off_topic / invalid
│ 1. guardrail │ ──────────────────────────────────────────────► safe exit
└──────────────┘
   │ pass
   ▼
┌──────────────┐   symptoms · duration · body parts (patient's own words)
│ 2. extraction│
└──────────────┘
   │
   ▼
┌──────────────────┐  patient language → clinical terms + condition ID
│ 3. normalization │
└──────────────────┘
   │
   ▼
┌──────────────────┐  ⏸ INTERRUPT — patient confirms or corrects
│ 4. confirmation  │
└──────────────────┘
   │ confirmed
   ▼
┌──────────────┐   full sourced briefing (web search grounded)
│ 5. briefing  │
└──────────────┘
```

| # | Node | Type | Responsibility |
|---|------|------|----------------|
| 1 | `guardrail` | LLM | Classifies input — routes emergencies/crisis to safe exits before anything else runs |
| 2 | `extraction` | LLM | Pulls symptoms, duration, and body parts from the patient's own language |
| 3 | `normalization` | LLM | Maps lay language → clinical terms and identifies the likely condition |
| 4 | `confirmation` | Human-in-loop | Graph interrupts so the patient confirms or corrects before any briefing |
| 5 | `briefing` | LLM + web search | Generates the full, source-grounded patient briefing |

---

## Stack

- **Orchestration:** LangGraph (`StateGraph`, checkpointing, interrupt/resume)
- **Model:** Claude (Anthropic API) with web search grounding
- **Backend:** FastAPI + Uvicorn — REST, session state, auth
- **Persistence/Auth:** Supabase (Postgres)
- **Observability:** LangSmith tracing
- **Deployment:** Railway (backend) · Capacitor (Android/iOS mobile wrapper)

---

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/session/start` | Runs nodes 1–3, pauses at the confirmation checkpoint |
| `POST` | `/session/{id}/confirm` | Resumes the graph — runs node 5, returns the briefing |
| `GET`  | `/session/{id}/state` | Inspect raw LangGraph state (debug) |
| `POST` | `/analyze/image` | Image-based symptom analysis |
| `GET`  | `/health` | Health check |

```bash
# Start a session — runs the safety + extraction + normalization nodes
curl -X POST http://localhost:8000/session/start \
  -H "Content-Type: application/json" \
  -d '{"raw_input": "My blood sugar is high and my feet tingle"}'
# → { thread_id, status: "awaiting_confirmation", identified_condition: ... }

# Confirm — resumes the graph and returns the full briefing
curl -X POST http://localhost:8000/session/$THREAD_ID/confirm \
  -H "Content-Type: application/json" \
  -d '{"confirmed": true}'
# → { status: "complete", briefing: ... }
```

---

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # add your ANTHROPIC_API_KEY
uvicorn backend.server:app --reload --port 8000
```

Open **http://localhost:8000/app**

---

## ⚠️ Medical disclaimer

MedCompanion AI provides general health information for educational purposes only. It is **not a medical device, not a diagnosis, and not a substitute for professional medical advice.** It does not handle emergencies — if you may be experiencing a medical emergency, call your local emergency number. The crisis/emergency guardrail is a safety layer, not a clinical safeguard.
