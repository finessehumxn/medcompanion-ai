# MedCompanion — iOS In-App Purchase (RevenueCat) setup

Hybrid billing: **Stripe on the web** (already live), **Apple IAP inside the iOS app**
(Apple 3.1.1 requires StoreKit for in-app digital goods). The purchase code is
**staged and wired** — it activates once these one-time steps are done. Web checkout
is unaffected by any of this.

## What's already done (in the code)
- `frontend/founding.html` → `go(key)` routes **web → Stripe**, **in-app → Apple IAP** via
  `window.Capacitor.Plugins.Purchases` (RevenueCat). Includes a **Restore purchases** link (Apple requires it).
- Product-key → App Store product-ID map (`MC_IAP.PRODUCT`): `mc_plus_monthly`,
  `mc_plus_yearly`, `mc_plus_lifetime`, `mc_pro_monthly`, `mc_pro_yearly`, `mc_pro_lifetime`.
- Backend `/rc-config` serves the RevenueCat **public** SDK key from env `RC_PUBLIC_KEY`;
  the app fetches it on load (in-app only) and configures RevenueCat.
- `codemagic.yaml` iOS build installs `@revenuecat/purchases-capacitor`.

## Step 1 — App Store Connect: create the IAP products
In App Store Connect → your app → **In-App Purchases / Subscriptions**, create products with
these **exact IDs** (or change the IDs in `MC_IAP.PRODUCT` to match yours):

| Product | Type | ID | Price |
|---|---|---|---|
| Plus Monthly | Auto-renewable sub | `mc_plus_monthly` | $9.99/mo |
| Plus Yearly | Auto-renewable sub | `mc_plus_yearly` | $59.99/yr |
| Plus Lifetime | Non-consumable | `mc_plus_lifetime` | $129.99 |
| Pro Monthly | Auto-renewable sub | `mc_pro_monthly` | $39/mo |
| Pro Yearly | Auto-renewable sub | `mc_pro_yearly` | $349/yr |
| Pro Lifetime | Non-consumable | `mc_pro_lifetime` | $799 |

(Put the two subs in a subscription group; fill in the review screenshot + description.)

## Step 2 — RevenueCat
1. Create a RevenueCat project → add your app (bundle `com.medcompanionai.app`).
2. Paste your **App Store Connect shared secret** + the App Store API key so RevenueCat can validate receipts.
3. Add the products above; map them into an Offering (optional — we purchase by product ID).
4. Copy the **Apple public SDK key** (`appl_…`).

## Step 3 — Railway
Set env **`RC_PUBLIC_KEY`** = the `appl_…` key. `/rc-config` then serves it; the app configures on load.

## Step 4 — Build & test on a device
Run the Codemagic `ios-release` build (it now installs the RevenueCat plugin), install on a
real device, and test with a **Sandbox tester** (App Store Connect → Users and Access → Sandbox).
Verify: tap a plan → Apple sheet → purchase → entitlement active; then **Restore purchases**.

## Reality check
- **Web Stripe works right now** — nothing here blocks it.
- **In-app purchase cannot be verified without** the ASC products + RC key + a device build
  (StoreKit doesn't run in a browser or simulator reliably). The code is written to the
  RevenueCat Capacitor contract; treat Step 4 as the verification.
- **Entitlement gating** (what Plus/Pro unlock) is a separate step: after purchase, RevenueCat
  reports the active entitlement — wire that to unlock family profiles / pro tools. Say the word
  and I'll stage that too.
