import os, shutil
FILE = os.path.join('frontend', 'index.html')
shutil.copy(FILE, FILE + '.bak')
with open(FILE, 'r', encoding='utf-8') as f:
    h = f.read()

# Fix 1: AVS button syntax error (extra } before ;})
h = h.replace(
    "el.innerHTML=\\'<i class=\\\\\\\"ti ti-copy\\\\\\\"></i> Copy AVS for patient\\'};},2000)",
    "el.innerHTML=\\'<i class=\\\\\\\"ti ti-copy\\\\\\\"></i> Copy AVS for patient\\';},2000)"
)

# Fix 2: Snake auto-starts
h = h.replace(
    'setTimeout(initSnake, 100);',
    'setTimeout(function(){ initSnake(); startSnake(); }, 150);'
)

# Fix 3: Hide snake overlay by default
h = h.replace(
    "'<div class=\"snake-overlay\" id=\"snakeOverlay\" onclick=\"startSnake()\">' +",
    "'<div class=\"snake-overlay\" id=\"snakeOverlay\" style=\"display:none\" onclick=\"startSnake()\">' +"
)

# Fix 4: Save lastBriefing when briefing renders
h = h.replace(
    '    renderBriefing(data.briefing);\n    var statusEl',
    '    window.lastBriefing = data.briefing;\n    renderBriefing(data.briefing);\n    var statusEl'
)

# Fix 5: Re-render on mode toggle
h = h.replace(
    "    if (chipsWrap) chipsWrap.style.display = '';\n  }\n}\n\n/* \u2500\u2500 Chip toggle",
    "    if (chipsWrap) chipsWrap.style.display = '';\n  }\n  if (window.lastBriefing) { renderBriefing(window.lastBriefing); }\n}\n\n/* \u2500\u2500 Chip toggle"
)

# Fix 6: Mobile swipe support — add after snakeDir function
swipe_code = """
/* -- Snake touch swipe -- */
(function() {
  var tx = 0, ty = 0;
  document.addEventListener('touchstart', function(e) {
    if (!_snakeRunning) return;
    tx = e.touches[0].clientX; ty = e.touches[0].clientY;
  }, {passive: true});
  document.addEventListener('touchend', function(e) {
    if (!_snakeRunning) return;
    var dx = e.changedTouches[0].clientX - tx;
    var dy = e.changedTouches[0].clientY - ty;
    if (Math.abs(dx) < 10 && Math.abs(dy) < 10) return;
    if (Math.abs(dx) > Math.abs(dy)) { snakeDir(dx > 0 ? 1 : -1, 0); }
    else { snakeDir(0, dy > 0 ? 1 : -1); }
  }, {passive: true});
})();
"""
h = h.replace(
    "/* \u2500\u2500 User Type \u2500\u2500 */",
    swipe_code + "\n/* \u2500\u2500 User Type \u2500\u2500 */"
)

with open(FILE, 'w', encoding='utf-8') as f:
    f.write(h)
print("All fixes applied")
