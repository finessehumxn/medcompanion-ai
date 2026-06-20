// Generates Google Play store assets for MedCompanion AI:
//   - play-icon-512.png        (512x512 app icon, from the brand icon)
//   - feature-graphic-1024x500.png
//   - screenshot phone images  (1080x1920) reflecting the real app + new features
// Run: node store/gen-med-store.cjs   (output → C:/Users/lfine/Downloads/medcompanion-store)
const sharp = require("C:/Users/lfine/AppData/Local/Temp/fg/node_modules/sharp");
const fs = require("fs");
const path = require("path");

const OUT = "C:/Users/lfine/Downloads/medcompanion-store";
fs.mkdirSync(OUT, { recursive: true });

const ICON_SRC = path.join(__dirname, "app-icon-1024.png");

// App's teal companion palette (matches the live UI) + brand emerald/gold accents.
const EM = "#0B3D2E", TEAL = "#1f9d96", TEAL2 = "#15807a", GOLD = "#D4B26A",
      INK = "#0A1F1A", CREAM = "#F5EFE0", CARD = "#0e2f31", S2 = "#103b3e",
      BD = "#1f5a5c", TX = "#eafaf8", T2 = "#9fbfbb", RED = "#e0594e", AMBER = "#e8b14a";
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// ── phone screenshots: [tagline, accent, bodyBuilder] ───────────────────────
const screens = [
  { tag: "Who can I help\ntoday?", sub: "Tap once — we take you straight to what you need.", accent: TEAL,
    body: (x, w, y, u) => roleGrid(x, w, y, u) },
  { tag: "Health, finally\nexplained.", sub: "Say it in your own words. We make it make sense.", accent: GOLD,
    body: (x, w, y, u) => inputCard(x, w, y, u) },
  { tag: "We customize\nyour answer.", sub: "A clear message while we work — not a blank wait.", accent: TEAL,
    body: (x, w, y, u) => customizing(x, w, y, u) },
  { tag: "Works WITH\nyour doctor.", sub: "Built to prepare you — not to replace your doctor.", accent: GOLD,
    body: (x, w, y, u) => doctorNote(x, w, y, u) },
  { tag: "Medication &\ninteraction check.", sub: "What's safe to mix — meds, foods, and drinks.", accent: AMBER,
    body: (x, w, y, u) => medCard(x, w, y, u) },
  { tag: "Evidence-based\nmode for pros.", sub: "Clinical briefings, sourced — like OpenEvidence.", accent: TEAL,
    body: (x, w, y, u) => proCard(x, w, y, u) },
  { tag: "Bring it to\nyour doctor.", sub: "The 1st app that prepares you AND your doctor.", accent: GOLD,
    body: (x, w, y, u) => visitSheet(x, w, y, u) },
];

function visitSheet(x, w, y, u) {
  const h = 78 * u;
  const line = (yy, t, c, fs, fw) => `<text x="${x+5*u}" y="${yy}" font-size="${(fs||3.4)*u}" fill="${c}" font-weight="${fw||400}" font-family="Arial">${esc(t)}</text>`;
  const label = (yy, t) => `<text x="${x+5*u}" y="${yy}" font-size="${2.7*u}" fill="${TEAL}" font-weight="800" letter-spacing="0.5" font-family="Arial">${esc(t)}</text>`;
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${3*u}" fill="#ffffff"/>`
    + `<text x="${x+5*u}" y="${y+9*u}" font-size="${5.2*u}" fill="${EM}" font-weight="800" font-family="Georgia,serif">📋 Doctor Visit Sheet</text>`
    + line(y+13.5*u, "Prepared with MedCompanionAI · today", "#7a8c8e", 2.6)
    + `<rect x="${x+5*u}" y="${y+16*u}" width="${w-10*u}" height="${0.3*u}" fill="#e3eceb"/>`
    + label(y+22*u, "WHAT I WANT TO TALK ABOUT")
    + line(y+27*u, "Type 2 diabetes — early signs", EM, 3.7, 700)
    + label(y+34*u, "QUESTIONS FOR MY DOCTOR")
    + line(y+39*u, "1. Should I be tested for diabetes?", "#16323a", 3.2, 600)
    + line(y+43.5*u, "2. What do my numbers mean?", "#16323a", 3.2, 600)
    + line(y+48*u, "3. What changes help most first?", "#16323a", 3.2, 600)
    + label(y+55*u, "WHAT I READ")
    + line(y+60*u, "NIH · Mayo Clinic · FDA", "#5d7274", 3)
    + `<rect x="${x+5*u}" y="${y+64*u}" width="${w-10*u}" height="${0.3*u}" fill="#cdd9d8"/>`
    + `<text x="${x+5*u}" y="${y+69.5*u}" font-size="${2.7*u}" fill="#7a8c8e" font-family="Arial">For my doctor: an AI prep tool — not a diagnosis.</text>`
    + `<text x="${x+5*u}" y="${y+73.5*u}" font-size="${2.7*u}" fill="#7a8c8e" font-family="Arial">Your clinical judgment has the final say.</text>`;
}

function pill(x, y, w, h, t, u, bg, fg, weight) {
  return `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${Math.min(h/2,10*u)}" fill="${bg}"/><text x="${x+w/2}" y="${y+h*0.66}" font-size="${3.3*u}" fill="${fg}" font-weight="${weight||700}" text-anchor="middle" font-family="Arial">${esc(t)}</text>`;
}
function roleOpt(x, y, w, u, ic, t) {
  return `<rect x="${x}" y="${y}" width="${w}" height="${13*u}" rx="${3*u}" fill="${S2}" stroke="${BD}"/>`
    + `<text x="${x+5*u}" y="${y+8.5*u}" font-size="${6*u}" font-family="Arial">${ic}</text>`
    + `<text x="${x+13*u}" y="${y+8.2*u}" font-size="${3.7*u}" fill="${TX}" font-weight="700" font-family="Arial">${esc(t)}</text>`;
}
function roleGrid(x, w, y, u) {
  return roleOpt(x, y, w, u, "💚", "For myself")
    + roleOpt(x, y+15*u, w, u, "🤝", "For a loved one")
    + roleOpt(x, y+30*u, w, u, "🩺", "I'm a medical professional")
    + roleOpt(x, y+45*u, w, u, "💊", "Medication & interaction check");
}
function inputCard(x, w, y, u) {
  return `<rect x="${x}" y="${y}" width="${w}" height="${34*u}" rx="${3*u}" fill="${S2}" stroke="${BD}"/>`
    + `<text x="${x+5*u}" y="${y+9*u}" font-size="${3.6*u}" fill="${T2}" font-family="Arial">"My blood sugar is high and my</text>`
    + `<text x="${x+5*u}" y="${y+15*u}" font-size="${3.6*u}" fill="${T2}" font-family="Arial">feet keep tingling lately..."</text>`
    + `<rect x="${x+5*u}" y="${y+21*u}" width="${10*u}" height="${10*u}" rx="${2*u}" fill="${CARD}" stroke="${BD}"/><text x="${x+8*u}" y="${y+28*u}" font-size="${5*u}" text-anchor="middle" font-family="Arial">🎤</text>`
    + `<rect x="${x+17*u}" y="${y+21*u}" width="${10*u}" height="${10*u}" rx="${2*u}" fill="${CARD}" stroke="${BD}"/><text x="${x+22*u}" y="${y+28*u}" font-size="${5*u}" text-anchor="middle" font-family="Arial">📷</text>`
    + pill(x, y+38*u, w, 11*u, "💚  Help Me Understand This", u, TEAL, "#fff", 800);
}
function customizing(x, w, y, u) {
  return `<rect x="${x}" y="${y}" width="${w}" height="${16*u}" rx="${3.5*u}" fill="${TEAL}"/>`
    + `<circle cx="${x+6*u}" cy="${y+8*u}" r="${2*u}" fill="#fff"/>`
    + `<text x="${x+11*u}" y="${y+7*u}" font-size="${4*u}" fill="#fff" font-weight="800" font-family="Arial">Customizing your response…</text>`
    + `<text x="${x+11*u}" y="${y+12.5*u}" font-size="${3*u}" fill="#eafaf8" font-family="Arial">Straight to the answers you came for.</text>`
    + `<g>${[0,1,2,3].map(i=>`<rect x="${x+i*(w/4)}" y="${y+22*u}" width="${w/4-2*u}" height="${5*u}" rx="${2.5*u}" fill="${i<3?TEAL2:S2}"/>`).join("")}</g>`
    + `<text x="${x}" y="${y+34*u}" font-size="${3.4*u}" fill="${T2}" font-family="Arial">Checking · Listening · Understanding · Looking it up</text>`;
}
function doctorNote(x, w, y, u) {
  return `<rect x="${x}" y="${y}" width="${w}" height="${30*u}" rx="${3*u}" fill="rgba(31,157,150,0.12)" stroke="${TEAL}"/>`
    + `<text x="${x+5*u}" y="${y+10*u}" font-size="${4.6*u}" fill="${TX}" font-weight="800" font-family="Arial">💙 With your doctor —</text>`
    + `<text x="${x+5*u}" y="${y+16*u}" font-size="${4.6*u}" fill="${TX}" font-weight="800" font-family="Arial">not instead of them.</text>`
    + `<text x="${x+5*u}" y="${y+23*u}" font-size="${3.4*u}" fill="${T2}" font-family="Arial">Helps you prepare for a better visit.</text>`
    + `<text x="${x+5*u}" y="${y+27.5*u}" font-size="${3.4*u}" fill="${T2}" font-family="Arial">Your care team has the final say.</text>`;
}
function medCard(x, w, y, u) {
  const row = (yy, name, sev, col) => `<rect x="${x}" y="${yy}" width="${w}" height="${11*u}" rx="${2.5*u}" fill="${S2}" stroke="${BD}"/>`
    + `<text x="${x+4*u}" y="${yy+7.2*u}" font-size="${3.5*u}" fill="${TX}" font-family="Arial">${esc(name)}</text>`
    + pill(x+w-26*u, yy+2.5*u, 23*u, 6*u, sev, u, col, "#fff", 800);
  return row(y, "Ibuprofen + Lisinopril", "Caution", AMBER)
    + row(y+13*u, "Warfarin + Grapefruit", "Avoid", RED)
    + row(y+26*u, "Metformin + food", "Usually fine", TEAL)
    + `<text x="${x}" y="${y+44*u}" font-size="${3.2*u}" fill="${T2}" font-family="Arial">Always confirm with your pharmacist.</text>`;
}
function proCard(x, w, y, u) {
  return `<rect x="${x}" y="${y}" width="${w}" height="${30*u}" rx="${3*u}" fill="${S2}" stroke="${BD}"/>`
    + `<text x="${x+4.5*u}" y="${y+8*u}" font-size="${3.6*u}" fill="${GOLD}" font-weight="800" font-family="Arial">◆ First-line · per ADA / NICE</text>`
    + `<text x="${x+4.5*u}" y="${y+15*u}" font-size="${3.4*u}" fill="${TX}" font-family="Arial">Metformin — strong evidence, GI-tolerated.</text>`
    + `<text x="${x+4.5*u}" y="${y+22*u}" font-size="${3.2*u}" fill="${T2}" font-family="Arial">Sources: NIH · PubMed · FDA label</text>`
    + pill(x, y+34*u, w, 10*u, "📄  Generate Clinical Briefing", u, EM, GOLD, 800);
}

function phoneSvg(W, H, s) {
  const u = W / 100, px = 8 * u, pw = W - 16 * u, top = 14 * u;
  const [l1, l2] = s.tag.split("\n");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${S2}"/><stop offset="0.55" stop-color="${INK}"/><stop offset="1" stop-color="${INK}"/></linearGradient>
    <radialGradient id="gl" cx="50%" cy="12%" r="55%"><stop offset="0" stop-color="${s.accent}" stop-opacity="0.22"/><stop offset="1" stop-color="${s.accent}" stop-opacity="0"/></radialGradient>
    <clipPath id="ic"><rect x="${px}" y="${top}" width="${11*u}" height="${11*u}" rx="${2.6*u}"/></clipPath></defs>
    <rect width="${W}" height="${H}" fill="url(#g)"/><rect width="${W}" height="${H}" fill="url(#gl)"/>
    <image href="data:image/png;base64,${ICON_B64}" x="${px}" y="${top}" width="${11*u}" height="${11*u}" clip-path="url(#ic)"/>
    <text x="${px+13.5*u}" y="${top+7.6*u}" font-size="${4.6*u}" fill="${TX}" font-weight="800" font-family="Georgia,serif">MedCompanion<tspan fill="${GOLD}">AI</tspan></text>
    <text x="${px}" y="${top+26*u}" font-size="${9.5*u}" fill="${TX}" font-weight="800" font-family="Georgia,serif">${esc(l1)}</text>
    <text x="${px}" y="${top+37*u}" font-size="${9.5*u}" fill="${s.accent}" font-weight="800" font-family="Georgia,serif">${esc(l2)}</text>
    <text x="${px}" y="${top+46*u}" font-size="${3.4*u}" fill="${T2}" font-family="Arial">${esc(s.sub)}</text>
    <g>${s.body(px, pw, top + 54 * u, u)}</g>
    <text x="${W/2}" y="${H-7*u}" font-size="${2.9*u}" fill="${T2}" text-anchor="middle" font-family="Arial">General health info · not a diagnosis · not for emergencies</text>
  </svg>`;
}

function featureSvg(W, H) {
  const u = W / 100;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
    <defs><linearGradient id="fg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${EM}"/><stop offset="1" stop-color="${INK}"/></linearGradient></defs>
    <rect width="${W}" height="${H}" fill="url(#fg)"/>
    <image href="data:image/png;base64,${ICON_B64}" x="${5*u}" y="${H/2-12*u}" width="${24*u}" height="${24*u}"/>
    <text x="${33*u}" y="${H*0.40}" font-size="${6.6*u}" fill="${CREAM}" font-weight="800" font-family="Georgia,serif">MedCompanion<tspan fill="${GOLD}">AI</tspan></text>
    <text x="${33*u}" y="${H*0.58}" font-size="${3.7*u}" fill="${GOLD}" font-family="Arial" font-weight="700">Health, finally explained.</text>
    <text x="${33*u}" y="${H*0.72}" font-size="${3.1*u}" fill="${CREAM}" font-family="Arial">Works with your doctor — never instead of them.</text>
  </svg>`;
}

let ICON_B64 = "";
(async () => {
  // 1) Play icon 512
  await sharp(ICON_SRC).resize(512, 512).png().toFile(path.join(OUT, "play-icon-512.png"));
  ICON_B64 = (await sharp(ICON_SRC).resize(256, 256).png().toBuffer()).toString("base64");

  // 2) Feature graphic 1024x500
  await sharp(Buffer.from(featureSvg(1024, 500))).png().toFile(path.join(OUT, "feature-graphic-1024x500.png"));

  // 3) Phone screenshots 1080x1920
  for (let i = 0; i < screens.length; i++) {
    await sharp(Buffer.from(phoneSvg(1080, 1920, screens[i]))).png()
      .toFile(path.join(OUT, `phone-${String(i + 1).padStart(2, "0")}.png`));
  }
  console.log("Done →", OUT);
  fs.readdirSync(OUT).forEach(f => console.log("  ", f));
})();
