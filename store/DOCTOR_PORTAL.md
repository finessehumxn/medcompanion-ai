# MedCompanion AI — "Reviewed by a Real Doctor" setup

This turns on the physician co-sign system: patients tap "Get a real doctor to review this,"
your medical board reviews it in a private portal, and the patient sees a
"✓ Reviewed by a licensed physician" badge. No competitor can copy this — it requires your board.

## 1. Create the Supabase table (one time)
Supabase dashboard -> SQL Editor -> run:

```sql
create table if not exists public.physician_reviews (
  id uuid default gen_random_uuid() primary key,
  raw_input text,
  condition text,
  briefing jsonb,
  status text default 'pending',
  doctor_name text,
  verdict text,            -- 'accurate' | 'edited' | 'see_your_doctor'
  note text,
  created_at timestamptz default now(),
  reviewed_at timestamptz
);
alter table public.physician_reviews enable row level security;
-- The server uses the SUPABASE_SERVICE_KEY (bypasses RLS); no public policies needed.
```

## 2. Set two environment variables on Railway
Railway -> your MedCompanion service -> Variables:
- `SUPABASE_URL` = your project URL (likely already set)
- `SUPABASE_SERVICE_KEY` = your Supabase **service role** key (Settings -> API)
- `DOCTOR_KEY` = a strong passcode you give ONLY to your board doctors (e.g. a long random string)

Redeploy after adding them.

## 3. Give your doctors the portal
- URL: **https://medcompanion-ai.up.railway.app/doctor**
- They enter their name + credentials and the `DOCTOR_KEY`.
- They see briefings awaiting review, pick a verdict (Accurate / Needs an edit / Defer to their doctor),
  add an optional plain-language note, and co-sign.
- The patient's app shows the verdict + the doctor's name live.

## How it stays safe / liability-aware
- The portal states clearly: reviewing AI general-information for accuracy + tone, **not** diagnosing or
  treating the requester, and **no doctor-patient relationship is created**.
- The "Defer to their doctor" verdict lets a physician flag anything that must be left to the treating clinician.
- The patient badge always reminds them their own doctor knows their full history and has the final say.

## Equity note
Your two onboarding doctors get equity for lending their license + time to review. This portal is how they do it.
