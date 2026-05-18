import os, shutil
FILE = os.path.join('frontend', 'index.html')
shutil.copy(FILE, FILE + '.bak')
with open(FILE, 'r', encoding='utf-8') as f:
    h = f.read()

fixes = 0

# 1: Save lastBriefing when data comes back
old = '    renderBriefing(data.briefing);\n    var statusEl'
new = '    window.lastBriefing = data.briefing;\n    renderBriefing(data.briefing);\n    var statusEl'
if old in h: h = h.replace(old, new); fixes += 1; print("Fix 1 (lastBriefing save): OK")
else: print("Fix 1 SKIP")

# 2: Re-render on toggle — find the closing of setUserType else block
old2 = "    if (chipsWrap) chipsWrap.style.display = '';\n  }\n}"
new2 = "    if (chipsWrap) chipsWrap.style.display = '';\n  }\n  if (window.lastBriefing) { renderBriefing(window.lastBriefing); }\n}"
if old2 in h: h = h.replace(old2, new2); fixes += 1; print("Fix 2 (re-render on toggle): OK")
else: print("Fix 2 SKIP — checking if already present:", "lastBriefing" in h)

# 3: Snake auto-start
old3 = 'setTimeout(initSnake, 100);'
new3 = 'setTimeout(function(){ initSnake(); startSnake(); }, 150);'
if old3 in h: h = h.replace(old3, new3); fixes += 1; print("Fix 3 (snake autostart): OK")
else: print("Fix 3 SKIP")

# 4: Hide snake overlay by default
old4 = "'<div class=\"snake-overlay\" id=\"snakeOverlay\" onclick=\"startSnake()\">' +"
new4 = "'<div class=\"snake-overlay\" id=\"snakeOverlay\" style=\"display:none\">' +"
if old4 in h: h = h.replace(old4, new4); fixes += 1; print("Fix 4 (hide overlay): OK")
else: print("Fix 4 SKIP")

# 5: Mobile swipe
if 'touchstart' not in h:
    swipe = """\n/* -- Snake swipe -- */\n(function(){\n  var tx=0,ty=0;\n  document.addEventListener('touchstart',function(e){if(!_snakeRunning)return;tx=e.touches[0].clientX;ty=e.touches[0].clientY;},{passive:true});\n  document.addEventListener('touchend',function(e){if(!_snakeRunning)return;var dx=e.changedTouches[0].clientX-tx,dy=e.changedTouches[0].clientY-ty;if(Math.abs(dx)<10&&Math.abs(dy)<10)return;Math.abs(dx)>Math.abs(dy)?snakeDir(dx>0?1:-1,0):snakeDir(0,dy>0?1:-1);},{passive:true});\n})();\n"""
    h = h.replace('\n/* -- Snake touch', '\n/* already */')  # avoid double
    # insert before User Type section
    h = h.replace('\n/* \u2500\u2500 User Type', swipe + '\n/* \u2500\u2500 User Type')
    fixes += 1; print("Fix 5 (mobile swipe): OK")
else: print("Fix 5 SKIP (already present)")

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(h)
print(f"\nDone — {fixes} fixes applied")
