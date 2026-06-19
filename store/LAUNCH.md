# MedCompanion AI — Google Play Launch Checklist

Everything in the app/repo is ready. These are the steps that require YOUR account access.

## 1. Create your upload keystore (one time, ~1 min)
On your computer (any folder), run this (Java/keytool ships with Android Studio or the JDK):

```
keytool -genkeypair -v -keystore medcompanion-release.jks -keyalg RSA -keysize 2048 -validity 9125 -alias medcompanion
```

- It asks for a **keystore password** and a **key password** — use the same strong password for both and SAVE IT somewhere safe (losing it means you can never update the app).
- For name/org you can enter: Millennials Creatives LLC.

Then base64-encode it (Git Bash):
```
base64 -w0 medcompanion-release.jks > keystore.b64.txt
```
(macOS: `base64 -i medcompanion-release.jks -o keystore.b64.txt`)

## 2. Add 4 GitHub secrets
GitHub → your repo `finessehumxn/medcompanion-ai` → **Settings → Secrets and variables → Actions → New repository secret**. Add:

| Secret name | Value |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | paste the entire contents of keystore.b64.txt |
| `ANDROID_KEYSTORE_PASSWORD` | your keystore password |
| `ANDROID_KEY_ALIAS` | `medcompanion` |
| `ANDROID_KEY_PASSWORD` | your key password |

## 3. Build the signed AAB
GitHub → **Actions → "Android Release (AAB)" → Run workflow** (branch: main).
When it finishes (~5–8 min), open the run → **Artifacts → medcompanion-release-aab** → download.
Inside is **app-release.aab** — that’s what you upload to Google Play.

## 4. Google Play Console
play.google.com/console → **Create app** (if not already created):
- App name: **MedCompanion AI** · Language: English (US) · App (not game) · Free
- Accept declarations.

Then complete (left menu):
- **Store listing** → paste from `STORE_LISTING.md`; upload icon, feature graphic, and the 6 phone screenshots from `Downloads/medcompanion-store`.
- **Privacy policy** → `https://medcompanion-ai.up.railway.app/privacy`
- **App content / Data safety** → answer:
  - Collects data: **Yes** — Health & fitness info (the symptoms/questions users type), and Email (only if they create an account).
  - Data **encrypted in transit**: Yes.
  - Data **sold**: No. Data **shared**: only with service providers to run the app (processing), not sold.
  - Users can request deletion: Yes (via email).
- **Health apps declaration** → declare it provides **general health information / education**; it is **not** a medical device and does **not** provide diagnosis or treatment. (Our in-app + listing disclaimers back this up.)
- **Content rating** → fill the questionnaire (medical/health info → typically rated for everyone/teen; answer honestly, no graphic content).
- **Target audience** → 18+ (recommended for a health-info app) or 13+; not directed at children.
- **App access** → if some features need an account, give Google test credentials; otherwise “All functionality available without special access.”

## 5. Release
- **Production** (or **Closed testing** first if you want a soft launch) → **Create release** → upload **app-release.aab** → add release notes ("Initial release") → **Review** → **Start rollout**.
- With Managed Publishing on, you click **Publish** when Google finishes review.

## Notes / honest flags
- This build loads the live app from Railway (a WebView wrapper). It works, but if Google flags "minimum functionality," the fix is to bundle the frontend + add CORS to the API. We can do that as a fast follow if needed.
- Health-app review can take a few days. Submitting tonight starts the clock.
- iOS follows once Apple finishes verifying your org enrollment (Enrollment ID 2X992D7339).
