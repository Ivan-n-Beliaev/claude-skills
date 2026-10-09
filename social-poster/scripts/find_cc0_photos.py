#!/usr/bin/env python3
"""Find CC0 / public-domain / CC-BY photos on Wikimedia Commons and build a contact sheet.

Why Commons: it has a documented open API and machine-readable licenses.

Set COMMONS_UA to a descriptive agent plus a contact URL or email, as the Wikimedia
User-Agent policy requires.

Usage:
    python3 find_cc0_photos.py "Ice hockey matches in Canada" "Ice hockey matches in Sweden"
    python3 find_cc0_photos.py --min-width 2400 --out sheet.png "IIHF World Championship"

Then Read the contact sheet, pick indices, and download originals with --fetch 3,7,12.
Writes index.json next to the sheet so indices map back to titles and file pages.
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

UA = {"User-Agent": os.environ["COMMONS_UA"]}
API = "https://commons.wikimedia.org/w/api.php?"
# Share-alike obligations may reach a poster built from the photo. Excluded on purpose.
PERMISSIVE = ("cc0", "public domain", "cc by 2", "cc by 3", "cc by 4")


def api(params):
    req = urllib.request.Request(API + urllib.parse.urlencode(params), headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=60))


def search(categories, min_width, min_aspect):
    found = {}
    for cat in categories:
        q = f'deepcategory:"{cat}" filetype:bitmap'
        try:
            d = api({"action": "query", "format": "json", "generator": "search",
                     "gsrsearch": q, "gsrnamespace": "6", "gsrlimit": "200",
                     "prop": "imageinfo", "iiprop": "url|extmetadata|size",
                     "iiurlwidth": "900"})
        except Exception as e:
            print(f"  ! {cat}: {e}", file=sys.stderr)
            continue
        pages = d.get("query", {}).get("pages", {})
        kept = 0
        for p in pages.values():
            if "imageinfo" not in p:
                continue
            ii = p["imageinfo"][0]
            em = ii.get("extmetadata", {})
            lic = em.get("LicenseShortName", {}).get("value", "?")
            w, h = ii.get("width", 0), ii.get("height", 0)
            if w < min_width or not h or w / h < min_aspect:
                continue
            if not lic.lower().startswith(PERMISSIVE):
                continue
            found[p["title"]] = {
                "lic": lic, "thumb": ii.get("thumburl"), "page": ii.get("descriptionurl"),
                "w": w, "h": h,
                "author": em.get("Artist", {}).get("value", "")[:120],
            }
            kept += 1
        print(f"  {cat}: {len(pages)} hits, {kept} permissive")
    return found


def get(url, timeout=60, tries=4):
    """Commons returns 429 on bursts. Back off rather than dropping the image."""
    for n in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or n == tries - 1:
                raise
            time.sleep(1.5 * (n + 1))
    raise RuntimeError("unreachable")


def contact_sheet(found, out, cols=6, cw=440, ch=300):
    from PIL import Image, ImageDraw
    os.makedirs(".poster_thumbs", exist_ok=True)
    # index.json carries every candidate, so --fetch still works for images whose
    # thumbnail failed and which therefore never made it onto the sheet.
    catalog = [{"idx": i, "title": t, **v} for i, (t, v) in enumerate(found.items())]
    json.dump(catalog, open(os.path.join(os.path.dirname(out) or ".", "index.json"), "w"), indent=1)

    items = []
    for i, (t, v) in enumerate(found.items()):
        fn = f".poster_thumbs/t{i:03d}.jpg"
        if not (os.path.exists(fn) and os.path.getsize(fn) > 1000):
            try:
                # Fetch fully BEFORE opening the file. open(...,'wb').write(get(...))
                # leaves a 0-byte file behind when get() raises, and that empty file
                # then looks like a completed download to the next resume.
                blob = get(v["thumb"])
                open(fn, "wb").write(blob)
                time.sleep(0.25)
            except Exception as e:
                print(f"  ! thumb {i}: {e}", file=sys.stderr)
                continue
        items.append((i, fn, t, v))
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, max(rows, 1) * ch), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    for k, (i, fn, t, v) in enumerate(items):
        try:
            im = Image.open(fn).convert("RGB")
        except Exception:
            continue
        im.thumbnail((cw - 8, ch - 36))
        x, y = (k % cols) * cw + 4, (k // cols) * ch + 4
        sheet.paste(im, (x, y))
        d.text((x + 4, y + ch - 30), f"{i:03d} {v['lic']}", fill=(255, 220, 80))
    sheet.save(out)
    print(f"\n{out}  ({len(items)} of {len(found)} on the sheet)"
          f"\nindex.json  (all {len(found)} candidates)"
          f"\nRead the sheet, then --fetch <indices>")


def fetch(indices, outdir):
    idx = {r["idx"]: r for r in json.load(open("index.json"))}
    os.makedirs(outdir, exist_ok=True)
    for i in indices:
        r = idx[i]
        t = r["thumb"]
        orig = t.split("/thumb/")[0] + "/" + t.split("/thumb/")[1].rsplit("/", 1)[0]
        fn = os.path.join(outdir, f"f{i:03d}.jpg")
        open(fn, "wb").write(get(orig, timeout=180))
        print(f"{fn}  {r['w']}x{r['h']}  {r['lic']}")
        print(f"   {r['page']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("categories", nargs="*", help="Commons category names, without the 'Category:' prefix")
    ap.add_argument("--min-width", type=int, default=2000)
    ap.add_argument("--min-aspect", type=float, default=1.15, help="landscape only by default")
    ap.add_argument("--out", default="sheet.png")
    ap.add_argument("--fetch", help="comma-separated indices from a previous run")
    ap.add_argument("--fetch-dir", default="full")
    a = ap.parse_args()

    if a.fetch:
        fetch([int(x) for x in a.fetch.split(",")], a.fetch_dir)
    else:
        if not a.categories:
            ap.error("give at least one category, or --fetch")
        found = search(a.categories, a.min_width, a.min_aspect)
        print(f"\n{len(found)} permissive candidates")
        contact_sheet(found, a.out)
