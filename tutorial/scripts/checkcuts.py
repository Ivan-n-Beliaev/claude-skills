#!/usr/bin/env python3
"""Gate: prove no cut in a plan lands on a word.

    python3 checkcuts.py plan.json [--verbose]

Every place the plan deletes source audio, this looks at the 80 ms on each
side of the deletion. If either side still carries speech-level energy, the
cut is eating a phoneme — almost always the consonant burst at the start of
the word that resumes, because ASR word timestamps mark the vowel onset and
not the burst in front of it.

Exit code 0 means clean. Anything else means do not render.

History: the first tag-window cut scored 398/415 (96%) and was hard to
listen to. The fix is in buildplan.py - find cut points in the waveform,
never in the word timings. This script is what keeps that fixed.
"""
import array
import json
import subprocess
import sys

RATE = 8000
EDGE = 0.08          # how much of each deletion edge to inspect
SPEECH_MULT = 0.14   # "speech-level" = this share of the file's speech RMS


def decode(path):
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-vn",
         "-f", "s16le", "-acodec", "pcm_s16le", "-ar", str(RATE), "-ac", "1", "-"],
        capture_output=True, check=True).stdout
    a = array.array("h")
    a.frombytes(out[: len(out) - len(out) % 2])
    return a


def rms(a, t0, t1):
    x = a[max(int(t0 * RATE), 0): int(t1 * RATE)]
    return (sum(v * v for v in x) / len(x)) ** 0.5 if len(x) else 0.0


def main():
    plan = json.load(open(sys.argv[1]))
    verbose = "--verbose" in sys.argv
    audio = {k: decode(v) for k, v in plan["sources"].items()}

    pieces = plan["pieces"]
    dels = [(p["src"], p["end"], q["start"])
            for p, q in zip(pieces, pieces[1:])
            if p["src"] == q["src"] and q["start"] - p["end"] > 0.01]

    bad, total_removed = [], 0.0
    for src, a, b in dels:
        total_removed += b - a
        au = audio[src]
        # speech level for this source, from a coarse sample of the whole file
        key = "_lvl_" + src
        if key not in globals():
            span = len(au) / RATE
            w = sorted(rms(au, t, t + 0.1) for t in range(0, int(span) - 1))
            globals()[key] = w[int(len(w) * 0.85)]
        thr = globals()[key] * SPEECH_MULT
        tail, head = rms(au, a, a + EDGE), rms(au, max(b - EDGE, a), b)
        if tail > thr or head > thr:
            bad.append((src, a, b, tail, head, thr))

    pct = 100 * len(bad) / max(len(dels), 1)
    print(f"deletions: {len(dels)}   source removed: {total_removed:.1f}s")
    print(f"cuts landing on speech: {len(bad)} ({pct:.0f}%)")
    if bad and verbose:
        print(f"\n{'src':>3} {'cut at':>9} {'resume':>9} {'tail':>7} {'head':>7} {'thr':>6}")
        for r in sorted(bad, key=lambda r: -max(r[3], r[4]))[:20]:
            print(f"{r[0]:>3} {r[1]:9.2f} {r[2]:9.2f} {r[3]:7.0f} {r[4]:7.0f} {r[5]:6.0f}")
    if bad:
        print("\nFAIL - fix buildplan.py before rendering. Re-run with --verbose "
              "to see which cuts.", file=sys.stderr)
        return 1
    print("\nOK - every cut lands in verified silence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
