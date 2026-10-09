#!/usr/bin/env python3
"""
package — map the word timings through the edit, emit SRT + chapters.

TEMPLATE. Copy into $WORK and edit CHAPTERS (title, src key, SOURCE second).
Chapter titles are the section boundaries already marked when reading the
phrases file; do not invent new ones here.

    python3 package.py [workdir]

Needs timemap.json, written by tutorialcut.py --map.
"""
import json, os, sys

WORK = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
TRANSCRIPT = {"A": "p1", "B": "p2"}

# ---- EDIT: transcriber mishearings. Spelling only, never wording. --------
# In my runs AssemblyAI transcribed "Pelaa" as "Pella".
FIXUP = {"Pella": "Pelaa", "Pella.": "Pelaa.", "Pella,": "Pelaa,",
         "Pela": "Pelaa", "Pelah": "Pelaa"}

# ---- EDIT: (title, src key, source second the section starts) ------------
CHAPTERS = [
    ("What we're building", "B", 559.60),
    ("Where it lives",      "A", 15.40),
]


def out_time(m, src, t, tol=0.0):
    """Source second -> output second. Falls forward if the moment was cut.

    Returns the EARLIEST output occurrence, because a constructed cold open
    lifts footage from late in the take and that source second then exists
    twice in the output. Returning whichever matched first put the cold-open
    chapter at 14:23 instead of 0:00.

    `tol` widens the match so a chapter marker that buildplan's snap() nudged
    by a fraction of a second still finds its region. Chapters pass tol=0.8;
    captions pass 0, because a word that was cut must not reappear.
    """
    hits, following = [], None
    for seg in m:
        if seg["src"] != src:
            continue
        if seg["src_start"] - tol <= t < seg["src_end"]:
            span = seg["src_end"] - seg["src_start"]
            frac = min(max((t - seg["src_start"]) / span, 0.0), 1.0) if span else 0
            hits.append(seg["out_start"] + frac * (seg["out_end"] - seg["out_start"]))
        elif seg["src_start"] >= t and (following is None or seg["out_start"] < following):
            following = seg["out_start"]
    if hits:
        return min(hits)
    return following


def out_times(m, src, t):
    """Every output second a source second maps to, earliest first.

    `out_time` deliberately returns only the earliest, so a constructed cold
    open resolves its chapter to 0:00 rather than to the middle of the video.
    Captions need the opposite: the cold open lifts 16 s that also plays in
    full at 6:30, and returning only the earliest left that stretch of the
    body with no captions at all. Emit a cue at each occurrence.
    """
    hits = []
    for seg in m:
        if seg["src"] != src or not (seg["src_start"] <= t < seg["src_end"]):
            continue
        span = seg["src_end"] - seg["src_start"]
        frac = min(max((t - seg["src_start"]) / span, 0.0), 1.0) if span else 0
        hits.append(seg["out_start"] + frac * (seg["out_end"] - seg["out_start"]))
    return sorted(hits)


def ts(t, sep=","):
    h, r = divmod(max(t, 0), 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)):03d}"


def mmss(t):
    m, s = divmod(int(t), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def main():
    m = json.load(open(f"{WORK}/timemap.json"))
    total = max(s["out_end"] for s in m)

    # Each word carries its SOURCE position too, so a cue never spans an edit
    # cut. Without that, the first pass merged the last line of the cold open
    # into the first line of the intro: "That's it. Hello everyone".
    cues = []
    for src, key in TRANSCRIPT.items():
        p = f"{WORK}/{key}_aai.json"
        if not os.path.exists(p):
            continue
        for w in json.load(open(p))["words"]:
            starts = out_times(m, src, w["start"] / 1000)
            ends = out_times(m, src, w["end"] / 1000)
            for a in starts:
                b = min((x for x in ends if x > a), default=None)
                if b is None or b - a > 1.5:
                    b = a + 0.20
                cues.append((a, max(b, a + 0.08),
                             FIXUP.get(w["text"], w["text"]),
                             src, w["start"] / 1000))
    cues.sort()

    lines, cur = [], None
    for a, b, t, src, st in cues:
        cut = cur is not None and (src != cur[3] or not -0.001 <= st - cur[4] <= 1.0)
        if (cur and not cut and a - cur[1] < 0.7
                and len(cur[2]) + len(t) < 42 and cur[1] - cur[0] < 4.5):
            cur[1], cur[2], cur[4] = b, cur[2] + " " + t, st
        else:
            if cur:
                lines.append(cur)
            cur = [a, b, t, src, st]
    if cur:
        lines.append(cur)

    # Fold one- and two-word orphans into a neighbour rather than flashing
    # them on screen for a third of a second.
    i = 1
    while i < len(lines):
        if lines[i][1] - lines[i][0] < 0.9 or len(lines[i][2].split()) < 3:
            prev = lines[i - 1]
            if (prev[3] == lines[i][3] and lines[i][0] - prev[1] < 0.6
                    and len(prev[2]) + len(lines[i][2]) < 58):
                prev[1], prev[2] = lines[i][1], prev[2] + " " + lines[i][2]
                del lines[i]
                continue
        i += 1

    for i in range(len(lines) - 1):
        lines[i][1] = min(lines[i][1], lines[i + 1][0] - 0.02)

    with open(f"{WORK}/captions.srt", "w") as fh:
        for i, ln in enumerate(lines, 1):
            fh.write(f"{i}\n{ts(ln[0])} --> {ts(max(ln[1], ln[0] + 0.3))}\n{ln[2]}\n\n")
    with open(f"{WORK}/captions.vtt", "w") as fh:
        fh.write("WEBVTT\n\n")
        for ln in lines:
            fh.write(f"{ts(ln[0], '.')} --> {ts(max(ln[1], ln[0] + 0.3), '.')}\n{ln[2]}\n\n")
    print(f"captions.srt / .vtt - {len(lines)} cues")

    rows = sorted((out_time(m, s, t, tol=0.8), title) for title, s, t in CHAPTERS
                  if out_time(m, s, t, tol=0.8) is not None)
    rows[0] = (0.0, rows[0][1])
    out = []
    for i, (o, title) in enumerate(rows):
        if i and o - out[-1][0] < 10:      # YouTube requires >=10s per chapter
            print(f"  ! dropped (too close): {title}", file=sys.stderr)
            continue
        out.append((o, title))
    with open(f"{WORK}/chapters.txt", "w") as fh:
        for o, title in out:
            fh.write(f"{mmss(o)} {title}\n")
    print(f"chapters.txt - {len(out)} chapters, runtime {mmss(total)}\n")
    print(open(f"{WORK}/chapters.txt").read())


main()
