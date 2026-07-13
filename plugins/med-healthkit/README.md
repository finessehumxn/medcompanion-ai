# med-healthkit — Apple Health clinical records for MedCompanion

Reads Apple Health **clinical records** (labs, medications, conditions, allergies,
immunizations, procedures, vitals) as **FHIR JSON** and hands them to the web layer.
The frontend maps them into MedCompanion records with `window.fhirToRecords()` — the
same mapper used for file import, already live and tested.

**Local-first:** this plugin returns FHIR JSON to the in-app WebView, which stores it
in on-device `localStorage`. Nothing is uploaded. It only reaches the server if the
user later taps an AI feature and consents — consistent with `/data-policy`.

The JS side already calls it (in `frontend/index.html` → `mcrConnect()`), guarded by
`window.Capacitor?.Plugins?.MedHealthkit`, with a file-import fallback when the native
plugin isn't present. So on the **current** build nothing changes; the button falls
back to file import. The steps below light up the native path.

---

## ⚠️ Why this isn't wired into the live release build yet

HealthKit needs (a) the capability enabled on the **App ID** in the Apple Developer
portal and (b) a matching **entitlement** in the build. If the entitlement is present
but the App ID capability isn't, `fetch-signing-files --create` produces a profile that
**doesn't include HealthKit**, and the archive **fails to sign** (exit 65). That's an
unverifiable break, so enabling this is a deliberate, device-tested step — not silent.

Do the one-time portal step FIRST, then the codemagic changes, then test on a device.

---

## Step 1 — One-time: enable HealthKit on the App ID (Apple Developer portal)

1. developer.apple.com → Certificates, IDs & Profiles → **Identifiers** → `com.medcompanionai.app`.
2. Enable **HealthKit**. (No separate "Clinical Health Records" toggle exists on the App ID —
   clinical access is granted at runtime via the entitlement + Info.plist string below.)
3. Save. This lets the auto-created provisioning profile include HealthKit.

## Step 2 — Add the plugin to the build (codemagic.yaml, `ios-release`)

**2a.** In the "Reconstruct Capacitor tooling" step, add the local plugin to `dependencies`:

```json
"dependencies": {
  "@capacitor/core": "^8.4.0",
  "@capacitor/ios": "^8.4.0",
  "@capacitor-community/speech-recognition": "^7.0.1",
  "med-healthkit": "file:./plugins/med-healthkit"
}
```

**2b.** In the "Inject Info.plist keys" step, add the two Health usage strings:

```bash
set_str NSHealthShareUsageDescription "MedCompanion reads your Health Records so it can explain your labs, medications and conditions in plain language. Your records stay on your device."
set_str NSHealthClinicalHealthRecordsShareUsageDescription "MedCompanion reads the clinical records you've connected in Apple Health so it can explain them in plain language, on your device."
```

**2c.** Add a new step (after "Add iOS platform", before "Capacitor sync") to write the
entitlement and point the project at it:

```yaml
- name: Add HealthKit entitlement
  script: |
    ENT=ios/App/App/App.entitlements
    cat > "$ENT" <<'EOF'
    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
    <plist version="1.0">
    <dict>
      <key>com.apple.developer.healthkit</key>
      <true/>
      <key>com.apple.developer.healthkit.access</key>
      <array><string>health-records</string></array>
    </dict>
    </plist>
    EOF
    # Point every build config at the entitlements file (idempotent).
    perl -0777 -i -pe 's/(\n(\t+)buildSettings = \{)/$1\n$2\tCODE_SIGN_ENTITLEMENTS = App\/App.entitlements;/g' ios/App/App.xcodeproj/project.pbxproj
    grep -c "CODE_SIGN_ENTITLEMENTS" ios/App/App.xcodeproj/project.pbxproj || true
```

`npx cap sync ios` (already in the workflow) will pick up the `file:` plugin, add its
pod, and compile the Swift into the app.

## Step 3 — Device test checklist (cannot be verified in a simulator or on web)

Clinical records require a **real iPhone** with **Health Records set up** (Health app →
profile → **Health Records** → add your hospital/provider via Apple's list).

- [ ] Build installs; on first tap of **Connect Apple Health / MyChart** iOS shows the Health permission sheet.
- [ ] Grant access → `queryClinicalRecords` returns FHIR JSON → records appear in **My Records**.
- [ ] "Explain my records" produces the plain-language breakdown from the imported data.
- [ ] Deny access → app shows the graceful fallback message (no crash).
- [ ] Provider with **no** linked records → "No records found in Apple Health yet" message.

---

## API (what the WebView calls)

```ts
Capacitor.Plugins.MedHealthkit.isAvailable()          // { available: boolean }
Capacitor.Plugins.MedHealthkit.requestAuthorization() // { granted: boolean }
Capacitor.Plugins.MedHealthkit.queryClinicalRecords() // { samples: string[] }  // each is FHIR JSON
```

The frontend parses each `samples[]` string and runs it through `window.fhirToRecords()`.

## Files

- `ios/Plugin/MedHealthkitPlugin.swift` — the HealthKit reader
- `ios/Plugin/MedHealthkitPlugin.m` — Capacitor registration (`MedHealthkit`)
- `MedHealthkit.podspec` / `package.json` — so `cap sync` installs it
