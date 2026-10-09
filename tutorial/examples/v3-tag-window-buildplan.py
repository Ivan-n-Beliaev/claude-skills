#!/usr/bin/env python3
"""Region table -> tutorialcut plan.

EXAMPLE ONLY. The speed and silence constants here are from an early run and
are superseded by scripts/buildplan.py. Kept for the shape of a real region
table and the camera measurements.

v3b. Two changes from the first cut of this video:

1. Cut points are found in the WAVEFORM, not in the ASR word timings. The
   first pass cut exactly at AssemblyAI's word boundaries; ASR marks a word's
   start at the vowel onset, not at the consonant burst in front of it, so
   every word after a short pause lost its attack. Measured on the first
   cut: 398 of 415 deletions removed speech-level energy, and the 80 ms
   deleted immediately before each resume carried 2400-3800 RMS against a
   speech average of 880. Now a cut may only land inside a stretch the
   envelope says is genuinely silent, with a guard band at each end.

2. Two cameras, no moves. `window` shows the whole screen, pillarboxed so
   nothing is ever cropped off. `panel` frames the tag window's working area.
   Framing changes on a hard cut at a chapter boundary and then holds.
"""
from pathlib import Path
import json, os, subprocess
import numpy as np

SP = os.path.dirname(os.path.abspath(__file__))
SRC = {
    "A": str(Path.home()) + "/Desktop/take1.mp4",
    "B": str(Path.home()) + "/Desktop/take2.mp4",
}

# --- cameras, in SOURCE pixels of the 2880x1800 capture -------------------
# Measured off the capture, not eyeballed:
#   menu bar      y    0 - 50
#   title bar     y   50 - 106
#   app content   y  106 - 1800   (runs to the bottom edge)
#   pane divider  x  1530
#   tag toolbar   y  110 - 172
#   tag work area x 1545 - 2440, y 190 - 1140  (union over 24 sampled frames;
#                 the Tag Editor card follows the selected button, so its
#                 x position moves through the video)
CAM = {
    # the whole screen, scaled to fit and pillarboxed. Nothing is ever cut.
    "window": {"x": 1440, "y": 900, "w": 2880, "h": 1800, "fit": True},
    # the tag window's working area. The right pane is 1350 px wide, so no
    # 16:9 frame confined to it can be taller than 759 px - and the Tag Editor
    # needs 1010. 1840 wide is the narrowest frame that holds the whole thing,
    # which means catching 490 px of the left pane. Painting that strip black
    # was tried and reverted: the tag window's tooltips overflow the divider
    # by up to 200 px, so the mask clipped their first word. 1.57x over
    # `window`.
    "panel":  {"x": 1960, "y": 622, "w": 1840},
}

# --- the edit ------------------------------------------------------------
# talk = speed over speech. gap = speed over pauses kept for their action.
R = [
    # ---------- COLD OPEN: the finished tag window doing the job ----------
    dict(src="B", a=559.60, b=575.60, cam="window", talk=1.30, gap=2.2, tag="cold-open"),

    # ---------- P1: intro + orientation (menu bar is referenced) ----------
    dict(src="A", a=15.40,  b=48.00,  cam="window", talk=1.28, gap=3.2, tag="intro"),
    dict(src="A", a=48.00,  b=122.30, cam="window", talk=1.30, gap=3.5, tag="shipped-template"),
    dict(src="A", a=122.30, b=133.20, cam="window", talk=1.30, gap=3.0, tag="new-template"),

    # ---------- P1: the panel, build mode ----------
    dict(src="A", a=133.20, b=216.30, cam="panel", talk=1.30, gap=3.2, tag="edit-bar"),
    dict(src="A", a=216.30, b=299.00, cam="panel", talk=1.28, gap=3.2, tag="button-vs-label"),
    dict(src="A", a=299.00, b=343.00, cam="panel", talk=1.30, gap=3.2, tag="name-shortcut-order"),
    dict(src="A", a=343.00, b=441.50, cam="panel", talk=1.30, gap=3.2, tag="behavior-timing"),
    dict(src="A", a=441.50, b=467.00, cam="panel", talk=1.32, gap=3.5, tag="colors"),

    # building GOAL / SC / SHOT — repetitive, push it along
    dict(src="A", a=467.00, b=535.00, cam="panel", talk=1.42, gap=4.5, tag="build-goal"),
    dict(src="A", a=535.00, b=579.10, cam="panel", talk=1.42, gap=4.5, tag="build-sc"),
    # cuts "Order 4- sorry," and keeps the clean "order 4"
    dict(src="A", a=581.80, b=594.00, cam="panel", talk=1.42, gap=4.5, tag="build-shot"),

    # ---------- P1: influences + links ----------
    dict(src="A", a=594.00, b=649.90, cam="panel", talk=1.30, gap=3.2, tag="influences"),
    dict(src="A", a=659.78, b=700.00, cam="panel", talk=1.30, gap=3.2, tag="link-lines"),
    dict(src="A", a=700.00, b=749.90, cam="panel", talk=1.35, gap=4.0, tag="defense-button"),
    dict(src="A", a=749.90, b=804.00, cam="panel", talk=1.30, gap=3.2, tag="deactivation-links"),
    dict(src="A", a=804.00, b=823.80, cam="panel", talk=1.30, gap=3.2, tag="exclusive-links"),
    dict(src="A", a=828.00, b=862.40, cam="panel", talk=1.30, gap=3.2, tag="exclusive-example"),

    # ---------- P2: labels ----------
    dict(src="B", a=21.30,  b=59.00,  cam="panel", talk=1.30, gap=3.5, tag="labels-open"),
    dict(src="B", a=59.00,  b=141.00, cam="panel", talk=1.28, gap=3.5, tag="label-modes"),
    dict(src="B", a=141.00, b=205.00, cam="panel", talk=1.30, gap=3.2, tag="action-only"),
    dict(src="B", a=205.00, b=278.50, cam="panel", talk=1.30, gap=3.2, tag="cut-all-tags"),
    dict(src="B", a=278.50, b=309.00, cam="panel", talk=1.38, gap=4.5, tag="make-13"),
    dict(src="B", a=309.00, b=358.50, cam="panel", talk=1.32, gap=3.5, tag="snapping"),

    # divider drag + save: needs both panes, and from here on the video pane
    # is in use, so the frame stays on the whole window to the end
    dict(src="B", a=358.50, b=402.30, cam="window", talk=1.32, gap=3.5, tag="resize-save"),

    # ---------- P2: on real footage ----------
    # 425.55, not 425.40: "and" runs to 425.33 and the old boundary ate it
    dict(src="B", a=402.30, b=425.55, cam="window", talk=1.30, gap=3.5, tag="open-video"),
    # 6x through the file-open dialog. There is not one word of narration
    # between 425.33 and 443.89, so muting costs nothing - and speech at 6x is
    # just noise, which is what the first cut had.
    dict(src="B", a=425.55, b=443.60, cam="window", talk=1.0, gap=1.0, run=6.0,
         mute=True, tag="file-dialog"),
    dict(src="B", a=443.60, b=470.00, cam="window", talk=1.28, gap=3.0, tag="pick-a-moment"),
    dict(src="B", a=470.00, b=507.50, cam="window", talk=1.28, gap=3.0, tag="tag-the-coach"),
    dict(src="B", a=507.50, b=528.50, cam="window", talk=1.28, gap=3.0, tag="zoom-the-track"),
    dict(src="B", a=528.50, b=576.20, cam="window", talk=1.28, gap=3.0, tag="defense-turnover"),
    dict(src="B", a=576.20, b=624.00, cam="window", talk=1.25, gap=2.8, tag="what-happened"),
    dict(src="B", a=624.00, b=658.60, cam="window", talk=1.28, gap=3.0, tag="outro"),
]

# --- dead-air policy ------------------------------------------------------
AR = 8000          # envelope sample rate
HOP = 0.010        # envelope hop, seconds
MIN_SIL = 0.26     # a silence shorter than this is left completely alone
GUARD = 0.06       # never cut within this of anything audible
SNAP = 0.60        # how far a hand-placed region edge may move to find silence
PAD = 0.16         # what a collapsed silence leaves on screen
GAP_TRIM = 0.85    # silences shorter than this collapse to PAD
GAP_MAX_OUT = 1.30 # a kept silence never runs longer than this on screen

_env = {}


def envelope(src):
    """RMS envelope of a whole source at HOP resolution, cached on disk."""
    if src in _env:
        return _env[src]
    cache = f"{SP}/env_{src}.npy"
    if os.path.exists(cache):
        _env[src] = np.load(cache)
        return _env[src]
    raw = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", SRC[src], "-vn",
         "-f", "s16le", "-acodec", "pcm_s16le", "-ar", str(AR), "-ac", "1", "-"],
        capture_output=True, check=True).stdout
    a = np.frombuffer(raw[: len(raw) - len(raw) % 2], dtype="<i2").astype(np.float32)
    n = int(HOP * AR)
    a = a[: len(a) // n * n].reshape(-1, n)
    e = np.sqrt((a * a).mean(axis=1))
    np.save(cache, e)
    _env[src] = e
    return e


def threshold(src):
    """Silence threshold: well above the room floor, well under speech."""
    e = envelope(src)
    floor = float(np.percentile(e, 5))
    speech = float(np.percentile(e, 85))
    return max(floor * 8.0, 40.0), floor, speech


def silences(src, a, b):
    """Verified-silent intervals inside [a,b], already guard-shrunk."""
    e = envelope(src)
    thr = threshold(src)[0]
    i0, i1 = int(a / HOP), min(int(b / HOP), len(e))
    quiet = e[i0:i1] < thr
    spans, run = [], None
    for k, q in enumerate(quiet):
        if q and run is None:
            run = k
        elif not q and run is not None:
            spans.append((run, k))
            run = None
    if run is not None:
        spans.append((run, len(quiet)))
    out = []
    for s, t in spans:
        if (t - s) * HOP < MIN_SIL:
            continue                       # too short to be worth touching
        p, q = a + s * HOP + GUARD, a + t * HOP - GUARD
        if q - p > 0.02:
            out.append((p, q))
    return out


def snap(src, t):
    """Move a hand-placed region edge onto the nearest verified silence.

    The region table was written by ear against the transcript, so its edges
    land on word boundaries too - same defect as the automatic cuts had, just
    fewer of them. Nudging each edge into real silence fixes the last two.
    """
    best = None
    for p, q in silences(src, max(t - SNAP, 0), t + SNAP):
        c = min(max(t, p), q)                  # closest point inside it
        if best is None or abs(c - t) < abs(best - t):
            best = c
    if best is not None:
        return best
    # No qualifying silence nearby - the narration runs straight through. Fall back
    # to the quietest 60 ms in reach, which is the trough between two words.
    e = envelope(src)
    i0, i1 = int(max(t - SNAP, 0) / HOP), min(int((t + SNAP) / HOP), len(e) - 6)
    if i1 <= i0:
        return t
    scores = [(e[i:i + 6].mean(), abs(i * HOP + 0.03 - t), i) for i in range(i0, i1)]
    lo = min(s[0] for s in scores)
    near = [s for s in scores if s[0] <= lo * 1.5 + 1.0]
    return min(near, key=lambda s: s[1])[2] * HOP + 0.03


def main():
    for r in R:
        r["a"], r["b"] = snap(r["src"], r["a"]), snap(r["src"], r["b"])

    pieces, report = [], []
    for r in R:
        cam_used = False

        def add(a, b, speed):
            nonlocal cam_used
            if b - a < 0.06:
                return
            p = {"src": r["src"], "start": round(a, 3), "end": round(b, 3),
                 "speed": round(speed, 4)}
            if r.get("mute"):
                p["mute"] = True
            if not cam_used:
                p["cam"] = CAM[r["cam"]]
                cam_used = True
            pieces.append(p)

        first = len(pieces)
        if r.get("run"):
            add(r["a"], r["b"], r["run"])
            report.append((r, first))
            continue

        # walk the region: everything audible is kept whole, verified
        # silence is collapsed or sped up
        t = r["a"]
        for p, q in silences(r["src"], r["a"], r["b"]):
            if p > t:
                add(t, p, r["talk"])
            d = q - p
            if d < GAP_TRIM:
                add(p, min(p + PAD, q), r["talk"])       # collapse it
            else:
                # keep the pause - there is usually a click or a drag in it -
                # but run it fast so it reads as action, not dead air.
                add(p, q, max(r["gap"], d / GAP_MAX_OUT))
            t = q
        if t < r["b"]:
            add(t, r["b"], r["talk"])
        report.append((r, first))

    plan = {"output": {"width": 1920, "height": 1080, "fps": 30},
            "sources": SRC, "default_cam": CAM["window"], "pieces": pieces}
    json.dump(plan, open(f"{SP}/plan.json", "w"), indent=1)

    src_total = sum(p["end"] - p["start"] for p in pieces)
    out_total = sum((p["end"] - p["start"]) / p["speed"] for p in pieces)
    ncut = sum(1 for x, y in zip(pieces, pieces[1:])
               if x["src"] == y["src"] and y["start"] - x["end"] > 0.01)
    print(f"{len(pieces)} pieces | {ncut} deletions | source kept "
          f"{src_total/60:.1f} min -> output {out_total/60:.2f} min")
    for s in SRC:
        thr, floor, speech = threshold(s)
        print(f"  {s}: floor {floor:6.1f}  speech {speech:7.1f}  threshold {thr:6.1f}")
    print(f"\n{'tag':22} {'cam':>7} {'src':>7} {'out':>7} {'x':>5}")
    for k, (r, first) in enumerate(report):
        last = report[k + 1][1] if k + 1 < len(report) else len(pieces)
        seg = pieces[first:last]
        s = sum(p["end"] - p["start"] for p in seg)
        o = sum((p["end"] - p["start"]) / p["speed"] for p in seg)
        print(f"{r['tag']:22} {r['cam']:>7} {s:6.1f}s {o:6.1f}s {s/max(o,0.01):4.2f}x")


main()
