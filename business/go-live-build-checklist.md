# MedCompanion — Go-Live Build Checklist

**Goal:** one Codemagic `ios-release` build activates everything currently staged:
reminders (meds + appointments) and Apple IAP. Then a single Railway flag turns on
the freemium split. **Nothing here touches the live web app or requires App Review**
for the reminder features — the reminders ship inside the native binary via TestFlight/App Store.

Order matters. Do the sections top to bottom.

---

## 0. Pre-flight (5 min)
- [ ] Confirm the live app is healthy: open `https://medcompanion-ai.up.railway.app/app`.
- [ ] Confirm `codemagic.yaml` deps already include (they do): `@revenuecat/purchases-capacitor`
      **and** `@capacitor/local-notifications` in **both** the iOS and Android `dependencies`.
- [ ] Note the signing facts baked into the yaml: bundle `com.medcompanionai.app`,
      team `357ABX659P`, ASC integration **"BarterThat ASC Key"** (that's just the *name* of the
      Codemagic integration holding the *team* API key — an ASC API key is team-wide, so it
      uploads MedCompanion fine; no change needed).

---

## 1. Reminders — NO setup, just the build ✅
Local notifications need **no** entitlement and **no** Info.plist usage string. The plugin is
already in the build deps, and the app calls `requestPermissions()` the first time a user sets a
med schedule or adds an appointment (contextual OS prompt). So:
- [ ] Nothing to configure. Reminders "just work" once Section 4's build lands on a device.
- [ ] After install, verify on the device:
  - Med schedule (set a slot) → allow notifications when prompted → confirm alerts fire at 8/12/18/22.
  - Add a future appointment → confirm evening-before + morning-of alerts.

*(Meds use notification IDs 9101–9104; appointments use 9200–9279. They don't collide.)*

---

## 2. Apple IAP — the only real setup (30–45 min)
Full detail in `ios-iap-setup.md`. Summary:

**2a. App Store Connect → In-App Purchases / Subscriptions** — create these EXACT IDs
(put the two subs of each tier in one subscription group):

| Product | Type | ID | Price |
|---|---|---|---|
| Plus Monthly | Auto-renewable sub | `mc_plus_monthly` | $9.99/mo |
| Plus Yearly | Auto-renewable sub | `mc_plus_yearly` | $59.99/yr |
| Plus Lifetime | Non-consumable | `mc_plus_lifetime` | $129.99 |
| Pro Monthly | Auto-renewable sub | `mc_pro_monthly` | $39/mo |
| Pro Yearly | Auto-renewable sub | `mc_pro_yearly` | $349/yr |
| Pro Lifetime | Non-consumable | `mc_pro_lifetime` | $799 |

- [ ] Products created with those IDs (or change `MC_IAP.PRODUCT` in `frontend/founding.html` to match).
- [ ] Fill each product's review screenshot + description (ASC won't approve blank ones).

**2b. RevenueCat**
- [ ] New RevenueCat project → add app, bundle `com.medcompanionai.app`.
- [ ] Paste the **ASC shared secret** + an **App Store API key** (so RevenueCat validates receipts).
- [ ] Add the 6 products above.
- [ ] **Create two entitlements** and attach products:
      - `plus` ← the three `mc_plus_*` products
      - `pro`  ← the three `mc_pro_*` products
      *(the app's `mcTier()` reads these entitlement names — see Section 3).*
- [ ] Copy the **Apple public SDK key** (`appl_…`).

**2c. Railway env**
- [ ] Set `RC_PUBLIC_KEY = appl_…`  → `/rc-config` serves it; the app configures RevenueCat on load (in-app only).

---

## 3. Verify the entitlement → tier wiring (10 min, on device)
The freemium gate reads the tier from RevenueCat in-app. Confirm the entitlement names
match what `mcTier()` expects (`plus` / `pro`). If RevenueCat reports a different customer-info
key, tell me the exact string and I'll align `mcTier()` — this is the one spot where a name
mismatch silently leaves a paid user on "free."
- [ ] Sandbox tester (ASC → Users and Access → Sandbox) installed on the device.
- [ ] Tap a Plus plan → Apple sheet → buy → confirm a Plus feature unlocks.
- [ ] Tap **Restore purchases** → entitlement returns.
- [ ] Buy a Pro plan (or use a second sandbox tester) → confirm Pro tools unlock.

---

## 4. The build (Codemagic)
- [ ] Push is already done (all staged code is on `main`).
- [ ] Run the **`ios-release`** workflow in Codemagic.
      It reconstructs Capacitor, generates `ios/`, injects plist keys, signs, bumps the version
      (`1.0.YYMMDD` + unix build number), builds the IPA, and uploads to App Store Connect.
      `submit_to_testflight: false` — so it lands in ASC for you to push to TestFlight/Review.
- [ ] (Optional) Run `android-release` too — same deps, builds a signed `.aab` artifact to
      upload in Play Console.
- [ ] Install the TestFlight build → run Section 1 + Section 3 checks on the real device.

---

## 5. Turn the freemium split ON (LAST — only after Section 3 passes)
Until this flag flips, gating is OFF and the app is 100% unlocked (current behavior).
- [ ] Railway env: `MC_GATING = 1`  (optionally set `MC_FREE_AI_DAILY`, default 5).
- [ ] Re-open the app; confirm:
      - Free user: 5 AI explanations/day → quota paywall; Plus/Pro → unlimited.
      - Clinician tools: 5/month free → Pro paywall.
- [ ] If anything reads wrong, set `MC_GATING=0` to instantly revert — no deploy needed.

---

## Rollback levers (each is instant, no rebuild)
- Freemium too aggressive → `MC_GATING=0`.
- RevenueCat key wrong → unset `RC_PUBLIC_KEY` (in-app falls back to non-gated).
- A bad frontend change → it's a normal Railway deploy; revert the commit and push.

## What CANNOT be verified without this build
- IAP (StoreKit doesn't run in a browser/simulator reliably).
- Real phone notifications firing (web is a verified no-op; native logic is unit-verified via a
  mocked plugin, but the OS-level delivery only happens on-device).
Everything else in the app is already verified live on the web deployment.
