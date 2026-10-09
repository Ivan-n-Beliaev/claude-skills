"""Build the browsable picking gallery.

Thumbnails are loaded straight from Wikimedia's thumb CDN with loading="lazy" rather than
mirrored locally, to keep request volume low.

Locally cached thumbs, when present, are preferred so the page still works offline.
"""
from pathlib import Path
import hashlib, html, json, os

OUT = str(Path.home()) + "/Desktop/poster-gallery"   # written outside the repo on purpose
os.makedirs(OUT, exist_ok=True)
# Not live play in an arena: ceremonies, fan zones, exteriors, celebrations, portraits.
SKIP = ("parade", "ceremony", "fans", "supporter", "logo", "jersey", "trophy", "medal",
        "press", "conference", "portrait", "statue", "museum", "banner", "mascot", "zamboni",
        "handshake", "anthem", "flag raising", "opening", "booth", "boutique",
        "hall of fame", "skills competition", "award", "draft", "locker", "all star",
        "allstar", "celebrat", "bench", "warm-up", "warmup", "practice")

# Winter-Olympics categories leak other sports in. These are not hockey.
OTHER_SPORT = ("speed skating", "short track", "figure skating", "curling", "bobsleigh",
               "luge", "skeleton", "1000m", "1500m", "500m", "5000m", "relay")

# Gear, board ads and rosters date a frame fast. Only the last three seasons survive.
MIN_YEAR = 2023

found = json.load(open("harvest.json"))
found = {t: v for t, v in found.items()
         if not any(k in t.lower() for k in SKIP + OTHER_SPORT)}

# harvest_commons.py stores the year parsed from extmetadata DateTimeOriginal.
# Drop anything older than MIN_YEAR, and anything with no date at all — an undated
# file is far more likely to be an old upload than a recent one.
before = len(found)
found = {t: v for t, v in found.items() if (v.get("year") or 0) >= MIN_YEAR}
print(f"recency filter ({MIN_YEAR}+): {before} -> {len(found)}")
if len(found) < 25:
    print("  NOTE: the openly-licensed recent pool is this thin every time. Tell the user\n"
          "  up front and offer footage they have the rights to instead of\n"
          "  presenting a gallery that cannot deliver.")

# Local scores exist only for thumbnails mirrored earlier.
scores = {}
old = f"{OUT}/index.json"
if os.path.exists(old):
    for r in json.load(open(old)):
        scores[r["title"]] = r["score"]

rows = []
for t, v in found.items():
    title = t[5:]
    key = hashlib.sha1(t.encode()).hexdigest()[:10]
    local = f"{OUT}/thumbs/{key}.jpg"
    rows.append({
        "title": title, "lic": v["lic"], "page": v["page"], "w": v["w"], "h": v["h"],
        "author": v.get("author", ""), "thumb": v["thumb"],
        "src": f"thumbs/{key}.jpg" if os.path.exists(local) and os.path.getsize(local) > 1000 else v["thumb"],
        "score": scores.get(title, -1),
    })

# CC0/PD first (no attribution to manage), then by ice-action score, then by resolution.
def rank(r):
    free = r["lic"].lower().startswith(("cc0", "public domain"))
    return (0 if free else 1, -r["score"], -r["w"])

rows.sort(key=rank)
for n, r in enumerate(rows):
    r["i"] = n
json.dump(rows, open(f"{OUT}/index.json", "w"), indent=1)

cards = []
for r in rows:
    free = r["lic"].lower().startswith(("cc0", "public domain"))
    cards.append(f"""
  <figure class="card" data-lic="{'cc0' if free else 'by'}">
    <a href="{html.escape(r['page'])}" target="_blank" rel="noopener">
      <img src="{html.escape(r['src'])}" loading="lazy" alt="">
    </a>
    <figcaption>
      <span class="id">#{r['i']:03d}</span>
      <span class="lic {'ok' if free else 'attr'}">{html.escape(r['lic'])}</span>
      <span class="dim">{r['w']}&times;{r['h']}</span>
    </figcaption>
  </figure>""")

n_free = sum(1 for r in rows if r["lic"].lower().startswith(("cc0", "public domain")))

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Hockey poster candidates</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0B0B0B; color: #E8E8EC;
    font: 15px/1.5 -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
    -webkit-font-smoothing: antialiased; padding-bottom: 80px;
  }}
  header {{
    position: sticky; top: 0; z-index: 10;
    background: rgba(11,11,11,.94); backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(255,255,255,.10);
    padding: 18px 28px; display: flex; align-items: center; gap: 22px; flex-wrap: wrap;
  }}
  h1 {{ font-size: 18px; font-weight: 800; letter-spacing: -.01em; white-space: nowrap; }}
  h1 em {{ color: #E11D2C; font-style: normal; }}
  .note {{ color: #8A8A93; font-size: 13px; max-width: 620px; line-height: 1.45; }}
  .note b {{ color: #E8E8EC; }}
  .filters {{ margin-left: auto; display: flex; gap: 8px; }}
  button {{
    font: inherit; font-size: 13px; font-weight: 600; color: #C8C8D0;
    background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12);
    border-radius: 999px; padding: 7px 15px; cursor: pointer; white-space: nowrap;
  }}
  button.on {{ background: #E11D2C; border-color: #E11D2C; color: #fff; }}
  .grid {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
    gap: 18px; padding: 24px 28px;
  }}
  .card {{ background: #141418; border-radius: 10px; overflow: hidden;
           border: 1px solid rgba(255,255,255,.07); }}
  .card img {{ width: 100%; aspect-ratio: 3/2; object-fit: cover; display: block; background: #1C1C22; }}
  figcaption {{ display: flex; align-items: center; gap: 10px; padding: 9px 12px; font-size: 12.5px; }}
  .id {{ font-weight: 800; font-size: 14px; }}
  .lic {{ padding: 2px 8px; border-radius: 999px; font-weight: 700; font-size: 11px; }}
  .lic.ok {{ background: rgba(52,199,89,.16); color: #7BE49A; }}
  .lic.attr {{ background: rgba(255,196,61,.14); color: #FFD277; }}
  .dim {{ color: #74747E; margin-left: auto; }}
  @media (max-width: 820px) {{ .grid {{ grid-template-columns: 1fr; padding: 16px; }} }}
</style></head>
<body>
<header>
  <h1>Hockey candidates <em>&middot;</em> {len(rows)}</h1>
  <p class="note">License metadata read from the Wikimedia API. Re-check each file page before use.
  Share-alike excluded on purpose. <b>{n_free} need no credit at all</b> (green); the amber ones
  want a photographer credit in the caption. Click any photo for the full-size original.
  <b>Then just tell me the number.</b><br>
  Sorted no-credit-first, then widest views of live play. The sort cannot see where the puck is,
  so scan for the real thing: bodies converging on a set goalie.</p>
  <div class="filters">
    <button class="on" data-f="all">All</button>
    <button data-f="cc0">No credit needed</button>
    <button data-f="by">Credit needed</button>
  </div>
</header>
<div class="grid">{''.join(cards)}
</div>
<script>
  const btns = document.querySelectorAll('button');
  btns.forEach(b => b.onclick = () => {{
    btns.forEach(x => x.classList.remove('on')); b.classList.add('on');
    const f = b.dataset.f;
    document.querySelectorAll('.card').forEach(c =>
      c.style.display = (f === 'all' || c.dataset.lic === f) ? '' : 'none');
  }});
</script>
</body></html>
"""
open(f"{OUT}/index.html", "w").write(page)
print(f"{OUT}/index.html   {len(rows)} cards, {n_free} need no credit")
