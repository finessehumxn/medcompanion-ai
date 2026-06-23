// Generates About Us, Partners, and Investors pages reusing about.html's brand shell.
const fs = require("fs");
const about = fs.readFileSync("about.html", "utf8");
// reuse everything up to and including <body>
const head = about.slice(0, about.indexOf("<body>") + "<body>".length);
const footer = `\n<footer>\n  <div class="mc">Millennials Creatives LLC</div>\n  <div>MedCompanion AI is a product of Millennials Creatives LLC.</div>\n</footer>\n</body>\n</html>`;
const setTitle = (h, title, desc) => h
  .replace(/<title>[^<]*<\/title>/, `<title>${title}</title>`)
  .replace(/<meta name="description"[^>]*>/, `<meta name="description" content="${desc}" />`);

const pages = {
  "about-us.html": {
    title: "About Us — MedCompanion AI",
    desc: "MedCompanion AI helps everyday people understand their health in plain language and prepare to partner with their doctor. A product of Millennials Creatives LLC.",
    body: `
<div class="hero"><div class="wrap">
  <div class="eyebrow">About MedCompanion AI</div>
  <h1>Health, finally in <em>your language.</em></h1>
  <p class="lead">MedCompanion AI helps everyday people understand their health in plain language and walk into every appointment prepared — always working with your doctor, never replacing them.</p>
  <div class="badges"><span class="badge">✓ Plain-language health</span><span class="badge">✓ 15+ languages</span><span class="badge">✓ Works with your doctor</span><span class="badge">✓ Private by design</span></div>
</div></div>
<section><div class="wrap">
  <h2>Why we exist</h2>
  <p class="muted">You get a diagnosis. The doctor uses a word you've never heard, hands you a printout, and the visit is over in nine minutes — and then you're in the parking lot, Googling, more scared than when you walked in. <strong style="color:var(--cream)">MedCompanion AI was built for that exact moment.</strong> We turn the overwhelming language of healthcare into clear, calm words, and help you walk back in prepared and confident. Understanding your own body shouldn't be a privilege reserved for people who already speak the language of medicine. It's a right — and closing that gap is the entire reason we exist.</p>
</div></div></section>
<section><div class="wrap">
  <h2>What we do</h2>
  <div class="grid">
    <div class="card"><h3>Decode the confusing parts</h3><p>Results, diagnoses, and doctor's notes — translated into language that actually makes sense, with sources you can check.</p></div>
    <div class="card"><h3>Medication &amp; food checks</h3><p>See how medications, supplements, and foods may interact, so you know what to ask your pharmacist or doctor.</p></div>
    <div class="card"><h3>Visit prep</h3><p>Turn what you're feeling into an organized summary and a focused list of questions for your appointment.</p></div>
    <div class="card"><h3>Healthcare Advocate</h3><p>Decode a confusing bill, understand what you're signing, and make sense of insurance coverage.</p></div>
    <div class="card"><h3>Private symptom log</h3><p>Track how you've been feeling over time, privately — then turn it into a clear summary for your visit.</p></div>
    <div class="card"><h3>Read aloud, 15+ languages</h3><p>Hear everything explained like a real conversation, in the language you're most comfortable with.</p></div>
  </div>
</div></div></section>
<section><div class="wrap">
  <h2>Who it's for</h2>
  <p class="muted">Everyday people facing a new diagnosis, caregivers and parents managing a loved one's care, people juggling multiple medications, and anyone who's ever felt small or rushed in a doctor's office. No medical background required — that's the point.</p>
</div></div></section>
<section><div class="wrap">
  <h2>Built by Millennials Creatives</h2>
  <p class="muted">MedCompanion AI is a product of <strong style="color:var(--cream)">Millennials Creatives LLC</strong> — a woman-owned, minority-founded studio building technology that makes essential services understandable for everyone. Our standards are guided by clinical input and a commitment to safety and privacy. <a href="/about">See our medical standards →</a></p>
</div></div></section>
<section><div class="wrap">
  <h2>What we are — and what we are not</h2>
  <div class="disc"><strong>MedCompanion AI provides general health information for educational purposes.</strong> It is <strong>not a medical device, not a diagnosis, and not a substitute for professional medical advice</strong>, and it does not handle emergencies — if you may be experiencing one, call your local emergency number. Your own clinician knows your full history and has the final say.</div>
  <a class="cta" href="/app">← Back to MedCompanion AI</a>
</div></div></section>`,
  },

  "partners.html": {
    title: "Partnerships — MedCompanion AI",
    desc: "Bring MedCompanion AI to your patients, employees, students, or members — health systems, employers, schools, pharmacies, publishers, and nonprofits.",
    body: `
<div class="hero"><div class="wrap">
  <div class="eyebrow">Partnerships</div>
  <h1>Bring MedCompanion AI to <em>your people.</em></h1>
  <p class="lead">Health systems, employers, schools, pharmacies, publishers, and nonprofits — partner with us to make health understandable for the people you serve, in 15+ languages.</p>
  <div class="badges"><span class="badge">Health systems</span><span class="badge">Employers &amp; benefits</span><span class="badge">Education</span><span class="badge">Publishers &amp; content</span></div>
</div></div>
<section><div class="wrap">
  <h2>Who we partner with</h2>
  <div class="grid">
    <div class="card"><h3>Health systems &amp; clinics</h3><p>Patients who understand their care show up prepared, ask better questions, and follow through. Extend health literacy between visits.</p></div>
    <div class="card"><h3>Employers &amp; benefits</h3><p>A health-literacy benefit employees actually use — plain-language support, visit prep, and a Healthcare Advocate for bills and coverage.</p></div>
    <div class="card"><h3>Schools &amp; universities</h3><p>Support student health and the caregivers around them with accessible, multilingual health information.</p></div>
    <div class="card"><h3>Pharmacies</h3><p>Help patients understand their medications, interactions, and instructions — supporting adherence and safety.</p></div>
    <div class="card"><h3>Publishers &amp; medical content</h3><p>License trusted clinical content, surfaced to patients in plain language at the moment of need — with proper attribution and links back to you.</p></div>
    <div class="card"><h3>Nonprofits &amp; community health</h3><p>Extend equitable access to underserved and multilingual communities who are too often left behind by the system.</p></div>
  </div>
</div></div></section>
<section><div class="wrap">
  <h2>Why it works</h2>
  <ul class="clean">
    <li><strong style="color:var(--cream)">Prepared people.</strong> Less confusion, fewer missed instructions, better conversations with clinicians.</li>
    <li><strong style="color:var(--cream)">Equity by design.</strong> 15+ languages and plain-language explanations reach people the system usually loses.</li>
    <li><strong style="color:var(--cream)">Safety-first.</strong> Crisis routing and red-flag detection are built in; we always point back to a licensed clinician.</li>
    <li><strong style="color:var(--cream)">Trustworthy.</strong> Source-grounded answers and physician-advised standards.</li>
  </ul>
</div></div></section>
<section><div class="wrap">
  <h2>Let's build something together</h2>
  <p class="muted">Pilots, co-branded deployments, content licensing, and multilingual community programs — tell us who you serve and we'll shape the right partnership.</p>
  <a class="cta" href="mailto:team@medcompanionai.com?subject=MedCompanion%20AI%20Partnership">Start a partnership →</a>
</div></div></section>`,
  },

  "investors.html": {
    title: "For Investors — MedCompanion AI",
    desc: "MedCompanion AI: making health understandable at scale. The opportunity, what we've built, and how to reach us. A product of Millennials Creatives LLC.",
    body: `
<div class="hero"><div class="wrap">
  <div class="eyebrow">For Investors</div>
  <h1>Make health <em>understandable</em> — at scale.</h1>
  <p class="lead">A multi-trillion-dollar system speaks a language most people don't. MedCompanion AI is the plain-language layer between patients and their care — live on web and mobile, in 15+ languages.</p>
  <div class="badges"><span class="badge">AI · Health</span><span class="badge">Live product</span><span class="badge">Web + Mobile</span><span class="badge">Multilingual</span></div>
</div></div>
<section><div class="wrap">
  <h2>The opportunity</h2>
  <p class="muted">Studies suggest the large majority of U.S. adults struggle to understand basic health information — and that gap drives confusion, missed care, and cost across a multi-trillion-dollar healthcare system. AI can finally close it. MedCompanion AI translates medical information into plain language and prepares people to partner with their own clinicians — a daily-use companion across every diagnosis, medication, bill, and visit.</p>
</div></div></section>
<section><div class="wrap">
  <h2>What we've built</h2>
  <div class="grid">
    <div class="card"><h3>Live, end-to-end product</h3><p>Web app plus iOS/Android — not a prototype. Plain-language explanations grounded in reputable sources, with citations.</p></div>
    <div class="card"><h3>More than a chatbot</h3><p>Medication &amp; food interaction checks, visit prep, a Healthcare Advocate for bills and coverage, and a private symptom log over time.</p></div>
    <div class="card"><h3>Safety architecture</h3><p>Crisis routing, red-flag detection, and a "works with your doctor" stance — positioned as information, not a medical device.</p></div>
    <div class="card"><h3>Built-in reach</h3><p>15+ languages and accessible-by-default design — addressing the underserved, multilingual users competitors ignore.</p></div>
  </div>
</div></div></section>
<section><div class="wrap">
  <h2>Why now, why us</h2>
  <ul class="clean">
    <li>The AI capability to do this well only just arrived — and health is where it matters most.</li>
    <li>Our differentiation is the <strong style="color:var(--cream)">advocate suite + multilingual access + works-with-your-doctor positioning</strong>, not another symptom-checker.</li>
    <li>Physician-advised standards and source-grounded answers build the trust health products live or die on.</li>
    <li>Built by <strong style="color:var(--cream)">Millennials Creatives LLC</strong> — a woman-owned, minority-founded team that ships.</li>
  </ul>
</div></div></section>
<section><div class="wrap">
  <h2>Let's talk</h2>
  <p class="muted">We welcome conversations with mission-aligned investors. Request our deck and the details on traction, roadmap, and the raise.</p>
  <a class="cta" href="mailto:team@medcompanionai.com?subject=MedCompanion%20AI%20Investor%20Inquiry">Request the investor deck →</a>
  <div class="disc" style="margin-top:1.4rem">This page is for informational purposes only and is <strong>not an offer to sell, or the solicitation of an offer to buy, any security.</strong> Any such offer would be made only to qualified investors through definitive offering documents.</div>
</div></div></section>`,
  },
};

Object.entries(pages).forEach(([file, p]) => {
  fs.writeFileSync(file, setTitle(head, p.title, p.desc) + p.body + footer);
  console.log("wrote", file, (fs.statSync(file).size / 1024).toFixed(1) + "KB");
});
