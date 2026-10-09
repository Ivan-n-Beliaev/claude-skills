---
name: social-poster
description: Build a LinkedIn/social poster image whose job is to stop the scroll and drive clicks. Use when the user asks for a post image, launch graphic, announcement card, feature-release visual, or "a picture to post alongside". Produces a 4:5 2400x3000 PNG rendered from HTML via puppeteer, verified at feed size before delivery.
---

# Social poster

The deliverable is one image that (1) stops the thumb, (2) makes the caption worth
reading, (3) sends people to a URL. It is not a spec sheet. Features live in the
caption, never in the image.

## The one non-negotiable rule

**Verify at feed size before delivering.** Downscale the finished poster to 440px
wide and Read it. Anything you cannot read at 440px does not exist. This single
check kills most bad posters — it is how the three-column feature layout that
looked fine at full res was caught as unreadable mush.

```python
Image.open('poster.png').resize((440,550), Image.LANCZOS).save('feed.png')
```

Then actually Read `feed.png`. Do not skip because it "looks obviously fine".

## Copy budget (hard ceilings)

| Element | Ceiling |
|---|---|
| Eyebrow | product + version, e.g. `PELAA 1.0.4` |
| Headline | 5 words, verb-first, one accent word in brand red |
| Sub | one sentence, ≤14 words, may be 3 short clauses |
| Footer | `pelaa.tv` + a 4-word status like `Out now for Mac` |
| Feature bullets | **zero** |

Headline pattern that works: `<Product> now <verb>s <the thing>`. Concrete verb,
not a category noun. "Pelaa now records the game" beats "The biggest update since 1.0"
because a verb tells a coach what changed.

No em dashes anywhere. Periods over dashes.

## Layout (the shape that won)

4:5 portrait, 1200x1500 CSS px rendered at deviceScaleFactor 2 → **2400x3000**.
4:5 claims more vertical feed space on mobile than 1.91:1 landscape.

```
┌──────────────────────┐
│  photo, top ~50%     │  ← real sport/product imagery, gradient-faded into black
│  small REC/status    │     at the bottom edge so type sits on solid ground
│  pill, top right     │
├──────────────────────┤
│  EYEBROW             │  25px, .40em tracking, #8A8A93
│  Headline            │  124px / 900 / -0.035em / line-height .98
│  Sub                 │  42px / 400 / #B0B0B8
│                      │
│  ───────────────     │  1px rgba(255,255,255,.12)
│  ⬛ pelaa.tv    status│  42px bold + 30px muted, icon 54px
└──────────────────────┘
```

Type sizes are for the 1200px-wide CSS canvas. Headline caps-height must survive
the 440px check — 118 to 132px is the working band; below ~110px it starts to go.

## Brand tokens (Pelaa)

- Background `#0B0B0B`, accent red `#E11D2C`, muted `#8A8A93`, body `#B0B0B8`
- Font: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`
- Icon: your app icon as `icon.png` beside the template (not included)
- Ambient glow, keep it quiet:
  `radial-gradient(760px 620px at 12% 6%, rgba(225,29,44,0.22) 0%, transparent 62%)`
- Red appears **once or twice**: the headline accent word, and a status dot. Scattering
  red across section labels dilutes it.

## Imagery rules

Rank by what survives 440px:

1. **A real photo of the sport** — a scoring chance from an elevated side angle, like a press-box camera.
   Wins on stopping power and reads as sport, not as another dark SaaS card.
2. **A wide product frame** (video pane, a strip of the track/timeline) — colored
   row bars stay legible as texture with intent.
3. **A dense UI panel** (button walls, small labels) — becomes noise. Do not use.

### Sport-photo gate — apply ALL of these before a photo reaches the user

Every one of these came from a real rejection. Filter in code where possible; do
not make the user scroll past images that fail a mechanical check.

1. **Live play, in an arena, on the ice.** Not fan zones, arena exteriors, queues,
   ceremonies, honour guards, anthems, locker rooms, celebrations, mascots, press
   conferences, skills competitions or all-star events.
2. **Last three seasons only.** Commons exposes `DateTimeOriginal` in `extmetadata` —
   parse the year and hard-filter. Older frames date themselves through gear, skates,
   sticks, board advertising, and rosters that no longer exist. Anything that starts to
   look archaic is out, regardless of composition.
3. **Right sport.** Winter Olympics categories mix in short track speed skating, figure
   skating and curling. Filter titles for those and check before shipping.
4. **Wide enough to be a play, not a portrait.** Single-player telephoto close-ups fail
   even when the action is real. The frame has to hold the zone.
5. **Camera height must match how the app records a game.** Elevated from the side, at
   press-box height, looking across the zone — a fixed camera a coach would actually
   mount. A near-overhead shot looking straight down is disqualifying even when it is
   otherwise the best chance in the set. This is subtle and cost a whole gallery pass.
6. **It has to be a chance.** See below.

**A wide shot of play is not the same as a chance.**
Why one frame beat two others: the winner had players breaking out
past the defence toward a goalie who is set, with the puck live in the slot even though
you cannot see it. The rejects had the puck elsewhere, players looking away, or no clear
shape to the play. So look for: a set goalie squared to the play,
attackers converging on the crease, defenders beaten or trailing, everyone's body
oriented at the same point. Empty-ice wide angles and neutral-zone skating do not
qualify no matter how clean the composition. No automatic score can see this — it is
the one judgement that has to be made by eye, which is why the picking gallery exists.

**Expect the openly-licensed pool to fail.** Measured on Commons in mid-2026: 201
permissive hockey images, only 29 from 2023 or later, and after removing other sports,
skills events and ceremonies, **17 remained — none of which cleared the gate.** The
recency rule alone removes about 85%. Say this out loud early rather than presenting a
large gallery that cannot deliver, and put the real option on the table: use a frame
from footage you have the rights to. Do not keep grinding the search.

Treatment: crop to ~1.58 landscape, upscale to 2400 wide, then
`Color 1.18 / Contrast 1.12 / Brightness 0.95` and a slight warm shift
(R x1.03, B x0.98). Photos taken from the stands are often flat and cool-toned.

Fade the photo into the page rather than boxing it:
```css
background: linear-gradient(180deg, rgba(11,11,11,0.30) 0%, rgba(11,11,11,0.05) 34%,
                            rgba(11,11,11,0.86) 84%, #0B0B0B 100%);
```

## Licensing — get this right before using any photo

Do not use broadcast frames as the hero of a promo. Prefer:

- **CC0 / Public domain** — no attribution required. Still check trademark and personality rights.
- **CC BY** — usable, needs a credit line (caption is enough).
- **CC BY-SA** — I avoid it. Share-alike obligations may reach a poster built from the
  photo, and I did not want to rely on an interpretation.

Working source: Wikimedia Commons, searched by deep category, filtered by license.
Commons has an open API and machine-readable license metadata. The metadata is supplied by uploaders, so verify it.

**Picking works by scrolling and pointing, not searching.** Do not hand over a
search link or a filter UI. Build the browsable gallery:

```bash
export SK="<path to this skill folder>"   # harvest.json is read and written in the current folder
python3 "$SK/scripts/harvest_commons.py"          # → harvest.json (edit the category list)
python3 "$SK/scripts/build_picking_gallery.py"    # → ~/Desktop/poster-gallery/index.html
```

The user opens the HTML, scrolls, and replies with a number. The page shows a license badge
per image, filters to "no credit needed" vs "credit needed", and links each photo to
its full-size original.

**Hotlink thumbnails from Wikimedia with `loading="lazy"` instead of bulk-downloading them.** This avoids bulk downloading. `find_cc0_photos.py` mirrors thumbs for an offline contact sheet; use it only for small sets and keep its backoff.

If you do mirror files: **fetch the bytes fully before opening the output file.**
`open(fn,'wb').write(get(url))` leaves a 0-byte file when `get` raises, and that empty
file then looks like a finished download to the next resume pass. A failed fetch once left 0-byte files that looked like finished downloads.

Always re-check the license on each file's own page before shipping
(`extmetadata.LicenseShortName`), and record photographer + file page in the delivery
notes. A permissive copyright license does not clear trademark or personality rights:
identifiable players, team and league marks need their own check before commercial use.

## Build loop

1. Read the release notes / source of truth. Pick the ONE claim.
2. Write the HTML (copy `reference/poster_template.html`).
3. Render: `node scripts/render.js poster.html poster.png 1200 1500 2`
4. **Downscale to 440px and Read it.** Fix what does not survive.
5. Render 2-3 variants that differ in a real way (photo vs type-only vs product strip),
   not in nudges. Show them as one feed-size strip so the comparison is honest.
6. Deliver full-res files plus the strip.

## Failure modes already paid for

- Three feature columns at 26px: invisible at feed size. Features go in the caption.
- Composite slide inside an app screenshot: the app's button wall turns to static and
  fights the type. Works only when the copy is one giant claim.
- `margin-top: auto` on the headline with a `justify-content: center` parent: pins the
  headline low and leaves a dead band. Pick one centering mechanism.
- Screenshotting an old build to announce a new feature: the frame silently contradicts
  the claim. Check what is actually on screen.
- Arguing image strategy in the abstract. Downscale first, then argue.
