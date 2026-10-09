#!/usr/bin/env python3
"""
buildplan — region table -> tutorialcut plan.json

TEMPLATE. Copy into $WORK, then edit SRC, CAM and R. Nothing below the
"policy" line should need touching.

    python3 buildplan.py [workdir]      # default: the directory it sits in

Cut points come from the WAVEFORM, never from the ASR word timings. ASR marks
a word's start at the vowel onset, not at the consonant burst in front of it,
so cutting there deletes the attack of every word that follows a pause. The
first tag-window cut did exactly that: 398 of 415 deletions removed
speech-level energy and the cut was hard to listen to. See
reference/edit-grammar.md.

The word timings are still needed - package.py maps them through the edit for
captions - but they do not decide where anything is cut.

ALWAYS run scripts/checkcuts.py on the plan before rendering. It must be 0%.
"""
from pathlib import Path
import json, os, subprocess, sys
import numpy as np

WORK = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))

# ---- EDIT: the takes, in stitch order -----------------------------------
SRC = {
    "A": str(Path.home()) + "/Desktop/take1.mp4",
    "B": str(Path.home()) + "/Desktop/take2.mp4",
}

# ---- EDIT: cameras, in SOURCE pixels of the capture ---------------------
# x/y = the point that ends up centred, w = crop width.
#
# MEASURE THESE. Do not eyeball them and do not copy them from another
# recording. Pull half-scale frames, read off the window bounds, the pane
# divider, the toolbar band, and the union bounding box of the working
# content over a dozen sampled frames. Half-scale numbers double.
#
# Two presets is the target. `window` carries its own h plus "fit", which
# scales-to-fit and pillarboxes rather than cropping - a 16:10 capture cannot
# go into a 16:9 frame without losing the toolbar or the track, and losing
# either is a defect. `panel` is sized by the content's
# HEIGHT: whatever width it takes to make 16:9 around the tallest thing that
# has to stay legible, even if that catches a strip of the next pane.
CAM = {
    "window": {"x": 1440, "y": 900, "w": 2880, "h": 1800, "fit": True},
    "panel":  {"x": 1960, "y": 622, "w": 1840},
}

# ---- EDIT: the edit ------------------------------------------------------
# src, a, b = source seconds
# cam       = key into CAM. Repeat the key to hold the framing.
# talk      = speed over words       (first run: 1.25 dense / 1.30 normal;
#             later runs cap at 1.2, see reference/edit-grammar.md)
# gap       = speed over kept pauses (3.0 normal / 4.5 repetitive)
# run       = one fixed-speed piece, no silence pass (dialogs, loads)
# mute      = silence it. MANDATORY on anything past ~3x - speech at 6x is
#             noise, and an unmuted run was in the first render.
# No `move`. Hard cuts only; see edit-grammar.md.
R = [
    dict(src="A", a=15.4,  b=133.2, cam="window", talk=1.30, gap=3.2, tag="intro"),
    dict(src="A", a=133.2, b=216.3, cam="panel",  talk=1.30, gap=3.2, tag="build-mode"),
    dict(src="B", a=425.4, b=443.6, cam="window", run=6.0, mute=True, tag="file-dialog"),
]

# ---- policy (edit-grammar.md; leave alone) ------------------------------
AR = 8000          # envelope sample rate
HOP = 0.010        # envelope hop, seconds
MIN_SIL = 0.35     # a silence shorter than this is left completely alone
GUARD = 0.15       # never cut within this of anything audible (speech
                   # decays over 100-200 ms; 0.06 was half a decay and it stepped)
SNAP = 1.50        # how far a hand-placed region edge may move to find silence.
                   # 0.60 was too small: five region boundaries found no
                   # qualifying silence in reach, fell back to "quietest 60 ms"
                   # and landed on an inhale or a word onset. Widening it is
                   # free - an edge can only ever land inside verified silence,
                   # and silence pulled INSIDE a region is collapsed to PAD by
                   # the gap policy, so nothing is added to the runtime.
BLIP = 0.06        # a sub-blip of energy this short inside a silence is a
                   # click or a mouth noise, not speech. Without merging over
                   # it a 0.75 s pause reads as three 0.2 s ones, all under
                   # MIN_SIL, and the whole pause becomes uncuttable.
PAD = 0.14         # what a collapsed silence leaves on screen
GAP_TRIM = 0.85    # silences shorter than this collapse to PAD
GAP_MAX_OUT = 1.30 # a kept silence never runs longer than this on screen

_env = {}


def envelope(src):
    """RMS envelope of a whole source at HOP resolution, cached on disk."""
    if src in _env:
        return _env[src]
    cache = f"{WORK}/env_{src}.npy"
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
    """Silence threshold: well above the room floor, well under speech.

    Deliberately conservative - about 1% of speech level - so that a quiet
    fricative at the end of a word never reads as silence.
    """
    e = envelope(src)
    floor = float(np.percentile(e, 5))
    speech = float(np.percentile(e, 85))
    return max(floor * 8.0, speech * 0.012), floor, speech


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
    # merge spans separated by a blip shorter than BLIP
    merged = []
    for s, t in spans:
        if merged and (s - merged[-1][1]) * HOP <= BLIP:
            merged[-1] = (merged[-1][0], t)
        else:
            merged.append((s, t))
    spans = merged

    out = []
    for s, t in spans:
        if (t - s) * HOP < MIN_SIL:
            continue
        p, q = a + s * HOP + GUARD, a + t * HOP - GUARD
        if q - p > 0.02:
            out.append((p, q))
    return out


def snap(src, t):
    """Move a hand-placed region edge onto the nearest verified silence.

    The region table is written by ear against the transcript, so its edges
    land on word boundaries - the same defect the automatic cuts had, just
    fewer of them.
    """
    best = None
    for p, q in silences(src, max(t - SNAP, 0), t + SNAP):
        c = min(max(t, p), q)
        if best is None or abs(c - t) < abs(best - t):
            best = c
    if best is not None:
        return best
    # The narration runs straight through. Fall back to the quietest 60 ms in
    # reach, which is the trough between two words.
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
        placed = False

        def add(a, b, speed):
            nonlocal placed
            if b - a < 0.06:
                return
            p = {"src": r["src"], "start": round(a, 3), "end": round(b, 3),
                 "speed": round(speed, 4)}
            if r.get("mute"):
                p["mute"] = True
            if not placed:
                p["cam"] = CAM[r["cam"]]
                placed = True
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
                add(p, min(p + PAD, q), r["talk"])
            else:
                # keep the pause - there is usually a click or a drag in it -
                # but run it fast so it reads as action, not dead air.
                add(p, q, max(r["gap"], d / GAP_MAX_OUT))
            t = q
        if t < r["b"]:
            add(t, r["b"], r["talk"])
        report.append((r, first))

    plan = {"output": {"width": 1920, "height": 1080, "fps": 30},
            "sources": SRC, "default_cam": CAM[R[0]["cam"]], "pieces": pieces}
    json.dump(plan, open(f"{WORK}/plan.json", "w"), indent=1)

    src_total = sum(p["end"] - p["start"] for p in pieces)
    out_total = sum((p["end"] - p["start"]) / p["speed"] for p in pieces)
    ncut = sum(1 for x, y in zip(pieces, pieces[1:])
               if x["src"] == y["src"] and y["start"] - x["end"] > 0.01)
    print(f"{len(pieces)} pieces | {ncut} deletions | source kept "
          f"{src_total/60:.1f} min -> output {out_total/60:.2f} min "
          f"({src_total/out_total:.2f}x)")
    for s in SRC:
        thr, floor, speech = threshold(s)
        print(f"  {s}: floor {floor:6.1f}  speech {speech:7.1f}  threshold {thr:6.1f}")
    print(f"\n{'tag':24} {'cam':>8} {'src':>7} {'out':>7} {'x':>5}")
    for k, (r, first) in enumerate(report):
        last = report[k + 1][1] if k + 1 < len(report) else len(pieces)
        seg = pieces[first:last]
        s = sum(p["end"] - p["start"] for p in seg)
        o = sum((p["end"] - p["start"]) / p["speed"] for p in seg)
        x = s / max(o, .01)
        flag = "" if r.get("run") or 1.25 <= x <= 2.0 else "   <- check"
        print(f"{r['tag']:24} {r['cam']:>8} {s:6.1f}s {o:6.1f}s {x:4.2f}x{flag}")
    print("\nNow run:  python3 $SK/scripts/checkcuts.py plan.json   (must be 0%)")


main()
