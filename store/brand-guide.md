# MedCompanionAI — Brand Guide (Premium Health-Tech / Option 07)

## Brand Essence
**Care that listens.** A premium AI health companion that feels as trustworthy as a private concierge clinic (Forward, Function Health) and as warm as a heart-monitor pulse. Quiet luxury meets clinical confidence.

## Logo
- **Mark**: Champagne gold heart + EKG pulse line, set inside an emerald rounded squircle.
- **Wordmark**: "MedCompanionAI" in humanist serif; "AI" subtly accented in emerald.
- **Lockups**: horizontal (primary), stacked, icon-only.

## Color Palette
| Role | Name | HEX |
|---|---|---|
| Primary | Deep Emerald | `#0B3D2E` |
| Accent | Champagne Gold | `#D4B26A` |
| Ink | Deep Ink | `#0A1F1A` |
| Surface | Warm Cream | `#F5EFE0` |
| Surface light | Cream Highlight | `#FBF6EA` |
| Support | Sage Mist | `#C9D6CC` |

OKLCH-ready tokens (drop into `src/styles.css`):
```css
--primary: oklch(0.32 0.07 160);          /* emerald */
--accent:  oklch(0.78 0.10 80);           /* champagne gold */
--foreground: oklch(0.18 0.02 160);       /* deep ink */
--background: oklch(0.96 0.02 85);        /* warm cream */
```

## Typography
- **Display / Wordmark**: Cormorant Garamond, Fraunces, or Recoleta — humanist serif.
- **Headings**: Fraunces (semibold).
- **Body**: Inter Tight or Söhne (regular / medium).
- **Numerals**: Tabular for dashboards.

## Voice
Calm, exact, never alarmist. Short sentences. Premium without being cold — "your companion," not "our platform."

## Files in this pack
| File | Use |
|---|---|
| `logo-primary-horizontal.png` | Website header, marketing, email signature |
| `logo-stacked.png` | Square placements, print, slides |
| `logo-dark.png` | Dark backgrounds |
| `logo-mono-black.png` | Print, embossing, single-color reproduction |
| `wordmark-only.png` | When the mark is already shown nearby |
| `icon-mark.png` | Favicon-large, social avatar source |
| `app-icon-1024.png` | **App Store** icon (iOS 1024×1024) — also export Android adaptive 432×432 foreground |
| `favicon-512.png` | Favicon source — export 16, 32, 48, 192, 512 |
| `social-avatar.png` | LinkedIn / X / Instagram / YouTube profile (1:1) |
| `social-banner-linkedin.png` | LinkedIn / X cover (1500×500 crop area) |
| `og-share-1200x630.png` | Open Graph / Twitter card |
| `appstore-feature.png` | App Store / Play Store feature graphic |
| `website-hero.png` | Homepage hero background |

## Export checklist (per platform)
- **Web favicon**: 16, 32, 48, 180 (apple-touch), 192, 512 PNG + `favicon.ico`.
- **iOS App Store**: 1024×1024 PNG, no alpha, no rounded corners (Apple applies mask).
- **Android Play Store**: 512×512 high-res icon + 432×432 adaptive foreground on emerald background.
- **Open Graph**: 1200×630.
- **Twitter card (summary_large_image)**: 1200×628.
- **LinkedIn cover**: 1584×396.
- **YouTube channel art**: 2560×1440 (safe area 1546×423).

## Don'ts
- Don't recolor the heart anything other than champagne gold or cream.
- Don't place the emerald icon on a competing saturated background.
- Don't stretch the wordmark or alter "AI" accent color.
- Don't add drop shadows; depth comes from the gold-on-emerald contrast.
