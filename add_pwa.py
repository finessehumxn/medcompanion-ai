import os
FILE = os.path.join('frontend', 'index.html')
with open(FILE, 'r', encoding='utf-8') as f:
    h = f.read()
pwa_head = '<link rel="manifest" href="/manifest.json">\n<meta name="theme-color" content="#0D4855">\n<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-title" content="MedCompanion AI">'
pwa_sw = '<script>\nif ("serviceWorker" in navigator) {\n  navigator.serviceWorker.register("/sw.js");\n}\n</script>'
if 'manifest.json' not in h:
    h = h.replace('</head>', pwa_head + '\n</head>')
    h = h.replace('</body>', pwa_sw + '\n</body>')
    with open(FILE, 'w', encoding='utf-8') as f:
        f.write(h)
    print("PWA added")
else:
    print("Already present")
