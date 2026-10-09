#!/usr/bin/env python3
"""
guide — build the raw material for a detailed written guide from the take.

Two outputs, both meant to be *read by whoever writes the PDF*, not shipped:

  guide-transcript.md   chapter-headed narration on the EDITED timeline
  figures/*.png         full-Retina stills pulled from the SOURCE, not the
                        1080p render, so they survive print

Figures come from the source files because the published mp4 is already
cropped and downscaled. A figure at 2880x1800 crops to any panel and still
prints sharp.
TEMPLATE. Copy into $WORK and edit SRC, CROP and FIGURES. Run it after
package.py, because it reads chapters.txt.

    python3 guide.py <output-dir>
"""
from pathlib import Path
import json, os, subprocess, sys

SP = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else SP
SRC = {          # EDIT: same paths as buildplan.py
    "A": str(Path.home()) + "/Desktop/take1.mp4",
    "B": str(Path.home()) + "/Desktop/take2.mp4",
}
FILE = {"A": "p1", "B": "p2"}
FIXUP = {"Pella": "Pelaa", "Pella.": "Pelaa.", "Pella,": "Pelaa,"}

# crop presets in source pixels: (w, h, x, y). "none" keeps the whole frame.
CROP = {
    "full":  None,
    "panel": (1560, 878, 1105, 110),
    "wide":  (1560, 878, 1180, 110),
    "track": (1920, 1080, 40, 700),
    "play":  (2400, 1350, 0, 40),
}

# (src, source second, crop, slug, what it shows)
FIGURES = [
    ("A",  30, "full",  "01-empty-app",        "Tag window sits in the top-right quadrant"),
    ("A",  46, "full",  "02-plus-sign",        "Starting a template from the plus sign"),
    ("A",  75, "full",  "03-shipped-window",   "The tag window every copy ships with"),
    ("A", 140, "panel", "04-edit-bar",         "The edit bar on a new template"),
    ("A", 200, "panel", "05-new-button-label", "New Button and New Label on the canvas"),
    ("A", 240, "panel", "06-tag-editor",       "Tag Editor, tag button vs label"),
    ("A", 312, "panel", "07-shortcut-order",   "Name, shortcut C, order 1"),
    ("A", 352, "panel", "08-behavior",         "Single-press vs toggle"),
    ("A", 425, "panel", "09-lead-lag",         "Lead and lag times"),
    ("A", 455, "panel", "10-colors",           "Fill and text colour"),
    ("A", 522, "panel", "11-goal-button",      "GOAL: shortcut g, order 2, lead 5 lag 3"),
    ("A", 565, "panel", "12-shift-duplicate",  "Shift-drag duplicates a button"),
    ("A", 612, "panel", "13-influences",       "Influences on the GOAL button"),
    ("A", 645, "panel", "14-link-lines",       "Link lines drawn between buttons"),
    ("A", 690, "panel", "15-influenced-by",    "Scoring chance is influenced by goal"),
    ("A", 745, "panel", "16-defense-button",   "A Defense toggle button"),
    ("A", 790, "panel", "17-deactivation",     "Red deactivation links"),
    ("A", 822, "panel", "18-exclusive",        "Yellow exclusive links"),
    ("B",  55, "panel", "19-label-mode",       "A label and its Label Mode"),
    ("B", 100, "panel", "20-latest-engaged",   "Latest Engaged"),
    ("B", 150, "panel", "21-action-only",      "Action Only, the helper label"),
    ("B", 235, "panel", "22-cut-all-tags",     "Cut All Tags Now"),
    ("B", 300, "panel", "23-label-13",         "Label #13"),
    ("B", 330, "panel", "24-snapping",         "The blue snap line while dragging"),
    ("B", 355, "panel", "25-tidy-window",      "The finished tag window"),
    ("B", 396, "full",  "26-save-template",    "Save Template As"),
    ("B", 412, "full",  "27-open-video",       "Start Live Capture or Open Video"),
    ("B", 462, "full",  "28-game-loaded",      "A real game loaded next to the window"),
    ("B", 505, "full",  "29-coach-tagged",     "The Coach tag on the track"),
    ("B", 545, "full",  "30-defense-active",   "Defense recording while play develops"),
    ("B", 585, "track", "31-label-attached",   "Label 13 attached to the scoring chance"),
    ("B", 600, "track", "32-search-by-label",  "Filtering the track by label"),
    ("B", 620, "track", "33-auto-deactivated", "Defense switched off by the link"),
]


def out_time(m, src, t, strict=False):
    """Source second -> output second. strict=True returns None for a moment
    that was cut, instead of falling forward to the next kept piece - which
    is what drags cut words like the slate into the transcript.

    Returns the EARLIEST output occurrence: a constructed cold open lifts
    footage from late in the take, so that source second exists twice."""
    hits, following = [], None
    for seg in m:
        if seg["src"] != src:
            continue
        if seg["src_start"] <= t < seg["src_end"]:
            span = seg["src_end"] - seg["src_start"]
            frac = (t - seg["src_start"]) / span if span else 0
            hits.append(seg["out_start"] + frac * (seg["out_end"] - seg["out_start"]))
        elif seg["src_start"] >= t and (following is None or seg["out_start"] < following):
            following = seg["out_start"]
    if hits:
        return min(hits)
    return None if strict else following


def mmss(t):
    m, s = divmod(int(t), 60)
    return f"{m}:{s:02d}"


def transcript(m):
    """Narration in output order, split under the chapter headings."""
    chapters = []
    for line in open(f"{SP}/chapters.txt"):
        t, _, title = line.strip().partition(" ")
        mm, ss = t.split(":")[-2:]
        chapters.append((int(mm) * 60 + int(ss), title))

    words = []
    for src, key in FILE.items():
        for w in json.load(open(f"{SP}/{key}_aai.json"))["words"]:
            o = out_time(m, src, w["start"] / 1000, strict=True)
            if o is not None:
                words.append((o, FIXUP.get(w["text"], w["text"]), src,
                              w["start"] / 1000))
    words.sort()

    figs = {}
    for src, t, _, slug, cap in FIGURES:
        o = out_time(m, src, t)
        if o is not None:
            figs.setdefault(slug, (o, cap))

    lines = ["# Tag Window — narration on the edited timeline", "",
             "Source material for a detailed written guide. Every sentence "
             "below is the user's, in the order the published video says it. "
             "Timecodes are the published cut, so a figure and a paragraph "
             "can be lined up without rewatching.", ""]
    ci, prev_o, para = 0, None, []
    for o, t, src, st in words:
        while ci < len(chapters) and o >= chapters[ci][0]:
            if para:
                lines.append(" ".join(para)); lines.append(""); para = []
            lines.append(f"## {mmss(chapters[ci][0])} — {chapters[ci][1]}")
            lines.append("")
            for slug, (fo, cap) in sorted(figs.items(), key=lambda x: x[1][0]):
                nxt = chapters[ci + 1][0] if ci + 1 < len(chapters) else 1e9
                if chapters[ci][0] <= fo < nxt:
                    lines.append(f"> figure `{slug}.png` — {cap}")
            lines.append("")
            ci += 1
        if prev_o is not None and o - prev_o > 1.2 and para:
            lines.append(" ".join(para)); lines.append(""); para = []
        para.append(t)
        prev_o = o
    if para:
        lines.append(" ".join(para))
    open(f"{OUT}/guide-transcript.md", "w").write("\n".join(lines) + "\n")
    print(f"guide-transcript.md — {len(words)} words, {len(chapters)} chapters")


def figures():
    d = f"{OUT}/figures"
    os.makedirs(d, exist_ok=True)
    for src, t, crop, slug, cap in FIGURES:
        vf = []
        if CROP[crop]:
            w, h, x, y = CROP[crop]
            vf.append(f"crop={w}:{h}:{x}:{y}")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(t),
                        "-i", SRC[src], "-frames:v", "1"]
                       + (["-vf", ",".join(vf)] if vf else [])
                       + [f"{d}/{slug}.png"], check=True)
    print(f"figures/ — {len(FIGURES)} stills at full capture resolution")
    with open(f"{d}/index.md", "w") as fh:
        fh.write("# Figures\n\nPulled from the source takes, not the render, "
                 "so they stay sharp in print.\n\n| file | source | shows |\n"
                 "|---|---|---|\n")
        for src, t, crop, slug, cap in FIGURES:
            fh.write(f"| `{slug}.png` | take {src} @ {mmss(t)} ({crop}) | {cap} |\n")


os.makedirs(OUT, exist_ok=True)
m = json.load(open(f"{SP}/timemap.json"))
transcript(m)
figures()
