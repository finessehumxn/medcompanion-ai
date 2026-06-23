"""Generate Android launcher icons (legacy + round + adaptive foreground) from the MedCompanion icon."""
from PIL import Image, ImageDraw
import os

SRC = os.path.join(os.path.dirname(__file__), "..", "frontend", "icon-512.png")
RES = os.path.join(os.path.dirname(__file__), "app", "src", "main", "res")

im = Image.open(SRC).convert("RGBA")

# 1) Trim the white border down to the green rounded square
px = im.load()
w, h = im.size
def is_white(p): return p[0] > 235 and p[1] > 235 and p[2] > 235
xs, ys = [], []
for y in range(0, h, 2):
    for x in range(0, w, 2):
        if not is_white(px[x, y]):
            xs.append(x); ys.append(y)
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
g = im.crop((x0, y0, x1 + 1, y1 + 1))

# make it square (pad with the sampled green so heart stays centered)
side = max(g.size)
# 2) sample emerald background color (top-center area, above the heart -> green)
gp = g.load()
bg = gp[g.size[0] // 2, max(2, g.size[1] // 12)]
bg = (bg[0], bg[1], bg[2], 255)
print("emerald bg sampled:", bg)

# 3) clean: replace any near-white pixels inside g with the emerald bg
g2 = Image.new("RGBA", g.size, bg)
gpix = g.load()
for y in range(g.size[1]):
    for x in range(g.size[0]):
        p = gpix[x, y]
        if not is_white(p):
            g2.putpixel((x, y), p)
# center on a square emerald canvas
core = Image.new("RGBA", (side, side), bg)
core.paste(g2, ((side - g.size[0]) // 2, (side - g.size[1]) // 2), g2)

LEGACY = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
FOREG = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}

def circular(img):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).ellipse((0, 0, img.size[0], img.size[1]), fill=255)
    out = img.copy(); out.putalpha(m); return out

for dens, sz in LEGACY.items():
    d = os.path.join(RES, f"mipmap-{dens}")
    sq = core.resize((sz, sz), Image.LANCZOS)
    sq.save(os.path.join(d, "ic_launcher.png"))
    circular(sq).save(os.path.join(d, "ic_launcher_round.png"))
    # adaptive foreground: core fills the full foreground canvas (heart lands in safe zone), transparent canvas
    fz = FOREG[dens]
    fg = Image.new("RGBA", (fz, fz), (0, 0, 0, 0))
    scaled = core.resize((fz, fz), Image.LANCZOS)
    fg.paste(scaled, (0, 0), scaled)
    fg.save(os.path.join(d, "ic_launcher_foreground.png"))
    print("wrote", dens, sz)

# 4) set adaptive background color to emerald
hexbg = "#%02X%02X%02X" % (bg[0], bg[1], bg[2])
bgxml = os.path.join(RES, "values", "ic_launcher_background.xml")
with open(bgxml, "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">%s</color>\n</resources>\n' % hexbg)
print("background color set to", hexbg)
