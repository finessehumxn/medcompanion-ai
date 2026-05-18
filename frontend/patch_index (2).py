"""patch_index.py v3 — zero regex, pure string replacement"""
import sys, shutil, os

FILE = os.path.join('frontend', 'index.html')
BACKUP = FILE + '.bak'

if not os.path.exists(FILE):
    print("ERROR: frontend/index.html not found. Run from project root.")
    sys.exit(1)

shutil.copy(FILE, BACKUP)
print("Backup:", BACKUP)

with open(FILE, 'r', encoding='utf-8') as f:
    html = f.read()
orig = len(html)

# FIX 1: add viewer_type to fetch call
old1 = ('      body: JSON.stringify({\n'
        '        raw_input: raw,\n'
        '        image_data: uploadedImageData,\n'
        '        image_media_type: uploadedMediaType,\n'
        '        user_id: currentUser ? currentUser.user_id : null\n'
        '      })')
new1 = ('      body: JSON.stringify({\n'
        '        raw_input: raw,\n'
        '        image_data: uploadedImageData,\n'
        '        image_media_type: uploadedMediaType,\n'
        '        user_id: currentUser ? currentUser.user_id : null,\n'
        '        viewer_type: window.currentUserType || \'everyday\'\n'
        '      })')
if old1 in html:
    html = html.replace(old1, new1)
    print("Fix 1 (viewer_type): OK")
else:
    print("Fix 1 SKIP: pattern not found (may already have viewer_type)")

# FIX 2: add window.currentUserType to setUserType
old2 = "function setUserType(type) {\n  userType = type;"
new2 = "function setUserType(type) {\n  window.currentUserType = type;\n  userType = type;"
if old2 in html:
    html = html.replace(old2, new2)
    print("Fix 2 (window.currentUserType): OK")
else:
    print("Fix 2 SKIP: already present or pattern differs")

# FIX 3: footer email
for old, new in [
    ('href="mailto:finessehumxn@gmail.com" class="footer-link">'
     '<i class="ti ti-mail" aria-hidden="true"></i> finessehumxn@gmail.com</a>',
     'href="mailto:hello@medcompanionai.com" class="footer-link">'
     '<i class="ti ti-mail" aria-hidden="true"></i> hello@medcompanionai.com</a>'),
    ('href="mailto:finessehumxn@gmail.com">Contact Us</a>',
     'href="mailto:hello@medcompanionai.com">Contact Us</a>'),
    ('reach out at finessehumxn@gmail.com.',
     'reach out at hello@medcompanionai.com.'),
    ('reach out at <strong>finessehumxn@gmail.com</strong>.',
     'reach out at <strong>hello@medcompanionai.com</strong>.'),
]:
    html = html.replace(old, new)
print("Fix 3 (footer email): OK")

# FIX 4: replace renderBriefing with dual-mode version
func_marker = "function renderBriefing(b) {"
comment_marker = "/* \u2500\u2500 Briefing render \u2500\u2500 */"
start = html.find(comment_marker)
if start == -1:
    start = html.find(func_marker)
func_start = html.find(func_marker, start)
if func_start == -1:
    print("Fix 4 FAILED: renderBriefing not found")
else:
    depth = i = 0
    i = func_start
    block_end = -1
    in_str = False
    sc = None
    while i < len(html):
        ch = html[i]
        if in_str:
            if ch == '\\': i += 2; continue
            if ch == sc: in_str = False
        else:
            if ch in ('"', "'", '`'): in_str = True; sc = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: block_end = i + 1; break
        i += 1

    if block_end == -1:
        print("Fix 4 FAILED: could not find function end")
    else:
        NEW_FN = (
            "/* -- Briefing render -- */\n"
            "function renderBriefing(b) {\n"
            "  var isPro = (window.currentUserType === 'professional');\n"
            "  var soc = b.standard_of_care || {};\n"
            "  var holistic = b.holistic || {};\n"
            "\n"
            "  function pb(p) {\n"
            "    p = (p||'').toLowerCase();\n"
            "    if (p.includes('first')||p.includes('approved')||p.includes('standard')) return 'badge-first';\n"
            "    if (p.includes('phase')||p.includes('trial')) return 'badge-trial';\n"
            "    if (p.includes('emerging')||p.includes('breakthrough')) return 'badge-emerging';\n"
            "    return 'badge-other';\n"
            "  }\n"
            "\n"
            "  var srcRows = (b.sources||[]).map(function(s,i){\n"
            "    return '<div class=\"src-item\"><div class=\"src-num\">'+(i+1)+'</div><div><div class=\"src-name\">'+clean(s.title)+'</div><div class=\"src-url\" onclick=\"window.open(\\''+clean(s.url)+'\\',\\'_blank\\')\">'+clean(s.url)+'</div></div></div>';\n"
            "  }).join('');\n"
            "\n"
            "  var fbk = '<div style=\"margin-top:1rem;padding:1rem 1.25rem;background:var(--lteal);border-radius:14px;border:1.5px solid var(--border);display:flex;align-items:center;gap:1rem;flex-wrap:wrap\"><div style=\"flex:1;font-size:14px;color:var(--text-body);line-height:1.5;min-width:180px\"><strong style=\"color:var(--text-dark)\">Was this helpful?</strong> Your feedback shapes what MedCompanion AI becomes next.</div><a href=\"https://docs.google.com/forms/d/e/1FAIpQLSdDaTyD5q2OnlDxIiPzAtgU_jFvm8mbsCPtr6MwLh-0B3_FjQ/viewform?usp=header\" target=\"_blank\" rel=\"noopener\" style=\"background:var(--teal);color:#fff;text-decoration:none;padding:9px 18px;border-radius:10px;font-size:13px;font-weight:700;white-space:nowrap;display:inline-flex;align-items:center;gap:6px;flex-shrink:0\"><i class=\"ti ti-message-circle\"></i> Give Feedback</a></div>';\n"
            "\n"
            "  var bodyEl = document.getElementById('briefingBody');\n"
            "  if (!bodyEl) return;\n"
            "\n"
            "  /* EVERYDAY PERSON */\n"
            "  if (!isPro) {\n"
            "    var txRows = (soc.treatments||[]).map(function(t){\n"
            "      return '<div class=\"tx-item\"><div class=\"tx-name\">'+clean(t.name)+'</div><span class=\"tx-badge '+pb(t.phase)+'\">'+clean(t.phase)+'</span><p class=\"tx-desc\">'+clean(t.plain_description)+'</p>'+(t.what_this_means_for_you?'<div class=\"tx-you\">What this means for you: '+clean(t.what_this_means_for_you)+'</div>':'')+'</div>';\n"
            "    }).join('');\n"
            "    var emRows = (b.emerging||[]).map(function(t){\n"
            "      return '<div class=\"tx-item\"><div class=\"tx-name\">'+clean(t.name)+'</div><span class=\"tx-badge '+pb(t.phase)+'\">'+clean(t.phase)+'</span><p class=\"tx-desc\">'+clean(t.plain_description)+'</p></div>';\n"
            "    }).join('');\n"
            "    var hRows = (holistic.options||[]).map(function(h){\n"
            "      return '<div class=\"h-item\"><div class=\"h-name\">'+clean(h.name)+'</div><span class=\"h-type\">'+clean(h.type||'Complementary')+'</span><p class=\"h-desc\">'+clean(h.plain_description)+'</p>'+(h.note?'<p class=\"h-note\">'+clean(h.note)+'</p>':'')+'</div>';\n"
            "    }).join('');\n"
            "    var coCards = (b.companies||[]).map(function(c){\n"
            "      return '<div class=\"co-card\"><div class=\"co-name\">'+clean(c.name)+'</div><div class=\"co-type\">'+clean(c.type)+'</div><div class=\"co-focus\">'+clean(c.focus)+'</div></div>';\n"
            "    }).join('');\n"
            "    bodyEl.innerHTML =\n"
            "      '<div class=\"brief-condition\">'+clean(b.plain_name||b.condition_name)+'</div>'+\n"
            "      '<div class=\"brief-meta\">Explained in plain language &middot; '+(b.sources?b.sources.length:0)+' trusted sources reviewed</div>'+\n"
            "      '<div style=\"font-size:16px;line-height:1.8;color:var(--text-body);margin-bottom:1.5rem;padding:1.25rem;background:var(--lteal);border-radius:14px;border-left:4px solid var(--teal)\">'+clean(b.opening)+'</div>'+\n"
            "      '<div class=\"card\" style=\"margin-bottom:.85rem\"><div class=\"card-header\"><div class=\"card-icon ci-teal\"><i class=\"ti ti-stethoscope\"></i></div><div class=\"card-title\">What doctors usually do for this</div></div><p style=\"font-size:15px;color:var(--text-body);line-height:1.75;margin:.5rem 0 '+(txRows?'1rem':'0')+'\">'+clean(soc.plain_summary)+'</p>'+txRows+'</div>'+\n"
            "      '<div class=\"card\" style=\"margin-bottom:.85rem\"><div class=\"card-header\"><div class=\"card-icon ci-sage\"><i class=\"ti ti-flask\"></i></div><div class=\"card-title\">What is being worked on that could also help</div></div><p style=\"font-size:15px;color:var(--text-body);line-height:1.75;margin:.5rem 0 '+(emRows?'1rem':'0')+'\">Researchers are working on new options:</p>'+(emRows||'<p style=\"font-size:14px;color:var(--text-soft)\">No specific emerging treatments found right now.</p>')+'</div>'+\n"
            "      '<button class=\"holistic-btn\" id=\"holisticBtn\" onclick=\"toggleHolistic()\"><i class=\"ti ti-leaf\"></i> Would you also like holistic and alternative options?</button>'+\n"
            "      '<div class=\"holistic-body\" id=\"holisticBody\"><div class=\"card\" style=\"margin-top:.75rem;margin-bottom:.85rem\"><div class=\"card-header\"><div class=\"card-icon ci-sage\"><i class=\"ti ti-plant\"></i></div><div class=\"card-title\">Holistic and alternative approaches</div></div>'+(holistic.intro?'<p style=\"font-size:15px;color:var(--text-body);line-height:1.75;margin:.5rem 0 1rem;padding:12px 16px;background:var(--lsage);border-radius:12px;border-left:3px solid var(--sage)\">'+clean(holistic.intro)+'</p>':'')+(hRows||'<p style=\"font-size:14px;color:var(--text-soft)\">No holistic options found right now.</p>')+(holistic.reminder?'<div class=\"holistic-reminder\"><i class=\"ti ti-info-circle\"></i> '+clean(holistic.reminder)+'</div>':'')+'</div></div>'+\n"
            "      '<div class=\"card\" style=\"margin-top:.85rem;margin-bottom:.85rem\"><div class=\"card-header\"><div class=\"card-icon ci-slate\"><i class=\"ti ti-building-hospital\"></i></div><div class=\"card-title\">Who is actively working on this</div></div><p style=\"font-size:14px;color:var(--text-soft);margin:.5rem 0 .85rem\">These organisations are doing some of the most important work around this condition right now:</p><div class=\"co-grid\">'+coCards+'</div></div>'+\n"
            "      '<div class=\"card\" style=\"margin-bottom:.85rem\"><div class=\"card-header\"><div class=\"card-icon ci-teal\"><i class=\"ti ti-certificate\"></i></div><div class=\"card-title\">Where this comes from &mdash; so you can check it yourself</div></div><p style=\"font-size:14px;color:var(--text-soft);margin:.5rem 0 .85rem\">Everything here is based on trusted sources. Click any link to read the original:</p>'+srcRows+'</div>'+\n"
            "      '<div class=\"closing-card\">'+clean(b.closing)+'</div>'+\n"
            "      '<div class=\"disclaimer\"><i class=\"ti ti-alert-circle\"></i><div class=\"disclaimer-text\"><strong>Important</strong> MedCompanion AI provides general health information for educational purposes only. It is NOT a substitute for professional medical advice. Always consult a qualified healthcare provider. In an emergency, call 911.</div></div>'+\n"
            "      '<div class=\"reset-row\"><span class=\"reset-hint\">Want to look up something else?</span><button class=\"reset-btn\" onclick=\"reset()\"><i class=\"ti ti-refresh\"></i> Search something different</button></div>'+\n"
            "      fbk;\n"
            "\n"
            "  /* MEDICAL PROFESSIONAL */\n"
            "  } else {\n"
            "    var avsParts = [\n"
            "      'Condition: '+clean(b.plain_name||b.condition_name)+'.',\n"
            "      clean(b.opening),\n"
            "      'Treatment overview: '+clean(soc.plain_summary),\n"
            "      soc.treatments&&soc.treatments[0]?'First-line: '+clean(soc.treatments[0].name)+'.':'',\n"
            "      holistic.reminder?clean(holistic.reminder):'',\n"
            "      'Contact your care team before making any changes to your treatment plan.'\n"
            "    ].filter(Boolean).join(' ');\n"
            "    var txP = (soc.treatments||[]).map(function(t){\n"
            "      return '<div class=\"tx-item\" style=\"border-left:3px solid var(--teal);padding-left:1rem\"><div style=\"display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin-bottom:.35rem\"><div class=\"tx-name\">'+clean(t.name)+'</div><span class=\"tx-badge '+pb(t.phase)+'\">'+clean(t.phase)+'</span></div><p class=\"tx-desc\" style=\"font-size:14px;margin:.25rem 0\">'+clean(t.plain_description)+'</p>'+(t.what_this_means_for_you?'<div style=\"font-size:13px;color:var(--text-soft);font-style:italic;margin-top:.25rem;padding:4px 10px;background:var(--lteal);border-radius:6px\">Patient framing: '+clean(t.what_this_means_for_you)+'</div>':'')+'</div>';\n"
            "    }).join('');\n"
            "    var emP = (b.emerging||[]).map(function(t){\n"
            "      return '<div class=\"tx-item\" style=\"border-left:3px solid var(--sage);padding-left:1rem\"><div style=\"display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin-bottom:.35rem\"><div class=\"tx-name\">'+clean(t.name)+'</div><span class=\"tx-badge '+pb(t.phase)+'\">'+clean(t.phase)+'</span></div><p class=\"tx-desc\" style=\"font-size:14px;margin:.25rem 0\">'+clean(t.plain_description)+'</p></div>';\n"
            "    }).join('');\n"
            "    var hP = (holistic.options||[]).map(function(h){\n"
            "      return '<div class=\"h-item\"><div class=\"h-name\">'+clean(h.name)+'</div><span class=\"h-type\">'+clean(h.type||'Complementary')+'</span><p class=\"h-desc\" style=\"font-size:14px\">'+clean(h.plain_description)+'</p>'+(h.note?'<p class=\"h-note\" style=\"font-size:13px\">Evidence note: '+clean(h.note)+'</p>':'')+'</div>';\n"
            "    }).join('');\n"
            "    bodyEl.innerHTML =\n"
            "      '<div style=\"display:flex;align-items:flex-start;gap:1rem;flex-wrap:wrap;margin-bottom:1.25rem\"><div style=\"flex:1\"><div class=\"brief-condition\">'+clean(b.condition_name)+'</div><div style=\"font-size:13px;color:var(--text-soft);margin-top:.25rem\">Common name: '+clean(b.plain_name||b.condition_name)+' &middot; '+(b.sources?b.sources.length:0)+' sources &middot; Evidence-based</div></div><span style=\"background:#1a3a4a;color:#7ecfc0;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:4px 10px;border-radius:6px\">Clinical Pro</span></div>'+\n"
            "      '<div style=\"background:#f0f9f7;border:1.5px solid var(--teal);border-radius:14px;padding:1.25rem;margin-bottom:1.25rem\"><div style=\"display:flex;align-items:center;gap:.5rem;margin-bottom:.75rem\"><i class=\"ti ti-file-text\" style=\"color:var(--teal);font-size:18px\"></i><strong style=\"font-size:15px;color:var(--text-dark)\">After Visit Summary &mdash; Patient-Ready Language</strong><span style=\"font-size:11px;color:var(--text-soft);margin-left:auto\">Copy and give directly to patient</span></div><p id=\"avsContent\" style=\"font-size:14px;line-height:1.8;color:var(--text-body);margin:0 0 .75rem\">'+avsParts+'</p><button onclick=\"navigator.clipboard.writeText(document.getElementById(\\'avsContent\\').innerText);this.textContent=\\'Copied!\\';var el=this;setTimeout(function(){el.innerHTML=\\'<i class=\\\\\\\"ti ti-copy\\\\\\\"></i> Copy AVS for patient\\';},2000)\" style=\"background:var(--teal);color:#fff;border:none;padding:7px 14px;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;display:inline-flex;align-items:center;gap:6px\"><i class=\"ti ti-copy\"></i> Copy AVS for patient</button></div>'+\n"
            "      '<div class=\"card\" style=\"margin-bottom:.85rem\"><div class=\"card-header\"><div class=\"card-icon ci-teal\"><i class=\"ti ti-stethoscope\"></i></div><div class=\"card-title\">Standard of Care</div></div><p style=\"font-size:14px;color:var(--text-body);line-height:1.7;margin:.5rem 0 '+(txP?'1rem':'0')+';padding:.75rem;background:#f8f8f8;border-radius:8px\">'+clean(soc.plain_summary)+'</p>'+txP+'</div>'+\n"
            "      '<div class=\"card\" style=\"margin-bottom:.85rem\"><div class=\"card-header\"><div class=\"card-icon ci-sage\"><i class=\"ti ti-flask\"></i></div><div class=\"card-title\">Emerging &amp; Investigational Therapies</div></div><p style=\"font-size:13px;color:var(--text-soft);margin:.25rem 0 .85rem\">Sourced from PubMed, OpenEvidence, and ClinicalTrials.gov:</p>'+(emP||'<p style=\"font-size:14px;color:var(--text-soft)\">No emerging therapies identified.</p>')+'</div>'+\n"
            "      '<div class=\"card\" style=\"margin-bottom:.85rem\"><div class=\"card-header\"><div class=\"card-icon ci-sage\"><i class=\"ti ti-plant\"></i></div><div class=\"card-title\">Integrative &amp; Complementary Options</div></div><p style=\"font-size:13px;color:var(--text-soft);margin:.25rem 0 .85rem\">Evidence-informed options patients may be using or asking about:</p>'+(hP||'<p style=\"font-size:14px;color:var(--text-soft)\">None identified.</p>')+(holistic.reminder?'<div class=\"holistic-reminder\" style=\"font-size:13px\"><i class=\"ti ti-info-circle\"></i> '+clean(holistic.reminder)+'</div>':'')+'</div>'+\n"
            "      '<div class=\"card\" style=\"margin-bottom:.85rem\"><div class=\"card-header\"><div class=\"card-icon ci-teal\"><i class=\"ti ti-certificate\"></i></div><div class=\"card-title\">Sources &amp; References</div></div>'+srcRows+'</div>'+\n"
            "      '<div class=\"reset-row\"><span class=\"reset-hint\">Generate another briefing?</span><button class=\"reset-btn\" onclick=\"reset()\"><i class=\"ti ti-refresh\"></i> New clinical briefing</button></div>'+\n"
            "      fbk;\n"
            "  }\n"
            "}"
        )
        html = html[:start] + NEW_FN + html[block_end:]
        print("Fix 4 (dual renderBriefing): OK")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"\nDone: {orig} -> {len(html)} chars. Backup at {BACKUP}")
