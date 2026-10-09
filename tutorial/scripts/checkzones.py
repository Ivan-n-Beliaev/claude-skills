#!/usr/bin/env python3
"""Gate: prove no thumbnail content sits where YouTube paints its furniture.

    python3 checkzones.py thumb_a.png thumb_b.png ...

YouTube never shows the whole frame. The duration badge covers the
bottom-right corner, the watched-progress bar covers the bottom edge, and
hover overlays cover the bottom strip. The first tag-window set put the
sub-headline at 89% height and the pelaa.tv chip bottom-right, so both were
lost in the feed.

Anything bright is type or UI - the backgrounds in this template are dark by
construction - so counting bright pixels in the forbidden regions is enough.
Exit code 0 means clean.
"""
import sys
import numpy as np
from PIL import Image

SAFE_BOTTOM = 0.82     # nothing that must be read below this
BADGE_X = 0.78         # duration badge starts here
BRIGHT = 120           # above this is type or UI, never the darkened photo
TOL = 40               # a few stray pixels from a gradient are fine


def main():
    bad = False
    for path in sys.argv[1:]:
        im = np.array(Image.open(path).convert("L")).astype(int)
        h, w = im.shape
        y0, x0 = int(h * SAFE_BOTTOM), int(w * BADGE_X)
        below = int((im[y0:, :] > BRIGHT).sum())
        badge = int((im[y0:, x0:] > BRIGHT).sum())
        ok = below <= TOL and badge <= TOL
        bad |= not ok
        print(f"{'ok  ' if ok else 'FAIL'} {path}: "
              f"bright px below {SAFE_BOTTOM:.0%} = {below}, in badge box = {badge}")
    if bad:
        print("\nMove the offending element up. Re-render with --zones to see it.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
