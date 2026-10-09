#!/usr/bin/env python3
"""
reuse — carry already-rendered pieces across a plan edit.

Editing the plan (adding a cut, moving a camera) renumbers every piece after
the change, so `--workdir` alone re-renders most of the video. This matches
pieces by CONTENT instead of index and hard-links the survivors into a new
workdir. On the first run it turned a 45-minute re-render into 4 minutes:
1136 of 1138 pieces reused.

    cp plan.json plan_old.json      # BEFORE editing buildplan.py
    python3 buildplan.py            # writes the new plan.json
    python3 reuse.py <workdir> <workdir_new> [plan_old.json] [plan.json]
    python3 tutorialcut.py plan.json out.mp4 --workdir <workdir_new> --map ...

A piece matches only if source, in/out, speed, mute, camera AND move are all
identical.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tutorialcut import merge          # noqa: E402


def resolved(plan):
    """Merged pieces with the inherited camera made explicit on each one."""
    cam, keys = plan["default_cam"], []
    for p in merge(plan["pieces"]):
        if "cam" in p:
            cam = p["cam"]
        keys.append((p["src"], round(p["start"], 3), round(p["end"], 3),
                     round(p["speed"], 4), bool(p.get("mute")),
                     cam["x"], cam["y"], cam["w"], cam.get("h"), cam.get("fit"),
                     p.get("move", 0)))
    return keys


def main():
    old_dir, new_dir = sys.argv[1], sys.argv[2]
    old_plan = sys.argv[3] if len(sys.argv) > 3 else "plan_old.json"
    new_plan = sys.argv[4] if len(sys.argv) > 4 else "plan.json"

    index = {}
    for j, k in enumerate(resolved(json.loads(open(old_plan).read()))):
        index.setdefault(k, j)

    os.makedirs(new_dir, exist_ok=True)
    new = resolved(json.loads(open(new_plan).read()))
    hit = 0
    for i, k in enumerate(new):
        j = index.get(k)
        src = f"{old_dir}/v{j:05d}.mp4" if j is not None else None
        dst = f"{new_dir}/v{i:05d}.mp4"
        if src and os.path.exists(src) and not os.path.exists(dst):
            os.link(src, dst)          # hard link: no copy, no extra disk
            hit += 1
        elif os.path.exists(dst):
            hit += 1
    print(f"{len(new)} pieces: {hit} reused, {len(new) - hit} to render")


main()
