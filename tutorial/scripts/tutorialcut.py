#!/usr/bin/env python3
"""
tutorialcut — one plan, one render: cuts + variable speed + camera framing.

This takes a per-piece plan and renders every piece with
its own speed AND its own crop, then concatenates. That is what a tutorial
edit actually needs: talking at 1.3x, repetitive clicking at 3x, dead air
gone, and the frame parked on the panel being talked about.

    ./tutorialcut.py plan.json out.mp4
    ./tutorialcut.py plan.json out.mp4 --map times.json   # source->output map

Plan format (times in seconds of SOURCE, x/y/w in SOURCE pixels):

    {
      "output": {"width": 1920, "height": 1080, "fps": 30},
      "sources": {"A": "/path/part1.mp4", "B": "/path/part2.mp4"},
      "default_cam": {"x": 1440, "y": 900, "w": 2880},
      "pieces": [
        {"src": "A", "start": 12.0, "end": 30.5, "speed": 1.3},
        {"src": "A", "start": 30.5, "end": 44.0, "speed": 3.0, "mute": true,
         "cam": {"x": 2100, "y": 520, "w": 1480},
         "move": 0.6}
      ]
    }

cam is the frame to hold: x/y is the centre point, w the crop width in source
pixels (height follows the output aspect). `move` eases from the previous
piece's camera into this one over that many output seconds. Omit cam to
inherit the previous piece's — framing only changes where the plan says so,
so cuts stay invisible and moves stay deliberate.

Audio is NOT cut piece-by-piece. Every AAC segment carries encoder priming,
so concatenating hundreds of them puts a click at every join. Instead the
speed-changed audio is rendered to raw PCM, spliced in Python with a short
equal-power fade at each seam, and encoded once at the end. Video pieces are
rendered without audio and concatenated with stream copy.
"""

import argparse
import array
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile

RATE = 48000
CH = 2
SEAM = 0.010          # seconds of fade at each audio splice. 0.006 was used on
                      # the tag-window tutorial and the post-mortem measured it
                      # as too short to hide the step at a splice; 8-12 ms is
                      # the band that kills the discontinuity without smearing a
                      # consonant.


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", path],
        capture_output=True, text=True, check=True)
    st = json.loads(out.stdout)["streams"][0]
    return int(st["width"]), int(st["height"])


def vduration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def fit(a, samples):
    """Trim or silence-pad a PCM chunk so it matches the video piece exactly.

    Video piece lengths quantise to whole frames; audio does not. Left alone
    the two random-walk apart over hundreds of cuts, so every chunk is pinned
    to its own piece's real duration and the drift never accumulates.
    """
    want = samples * CH
    if len(a) > want:
        del a[want:]
    elif len(a) < want:
        a.extend(array.array("h", bytes(2 * (want - len(a)))))
    return a


def even(n):
    n = int(round(n))
    return n - (n % 2)


def rect(cam, src_w, src_h, out_w, out_h):
    """Turn {x,y,w} into a clamped, even (w, h, x0, y0) crop in source pixels.

    Height normally follows the output aspect so the crop fills the frame. A
    cam that carries its own "h" keeps it instead, which only makes sense
    together with "fit" — see static_filter.
    """
    w = even(min(cam["w"], src_w))
    if cam.get("h"):
        h = even(min(cam["h"], src_h))
    else:
        h = even(w * out_h / out_w)
        if h > src_h:                   # too tall for the source, pull back
            h = even(src_h)
            w = even(h * out_w / out_h)
    x0 = min(max(cam["x"] - w / 2, 0), src_w - w)
    y0 = min(max(cam["y"] - h / 2, 0), src_h - h)
    return w, h, even(x0), even(y0)


def static_filter(cam, src_w, src_h, out_w, out_h):
    """Frame one piece.

    Default is fill: crop to the output aspect, so the frame is full-bleed and
    whatever falls outside the crop is gone. `"fit": true` instead scales the
    whole crop down until it fits and pillar/letterboxes the remainder — used
    for the app window, whose 16:10 shape cannot go into a 16:9 frame without
    losing either the tag toolbar at the top or the track at the bottom.
    """
    w, h, x0, y0 = rect(cam, src_w, src_h, out_w, out_h)
    flags = "lanczos" if w > out_w else "bicubic"
    if cam.get("fit"):
        return (f"crop={w}:{h}:{x0}:{y0},"
                f"scale={out_w}:{out_h}:force_original_aspect_ratio=decrease:flags={flags},"
                f"pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2:black")
    return f"crop={w}:{h}:{x0}:{y0},scale={out_w}:{out_h}:flags={flags}"


def moving_filter(a, b, move, speed, src_w, src_h, out_w, out_h, fps):
    """Ease from rect a to rect b over `move` seconds of OUTPUT time.

    zoompan re-times its own output, so it has to sit BEFORE the setpts that
    applies the speed change — which means the ramp is written in source
    seconds here and `move` gets scaled back up by the speed.
    """
    aw, ah, ax, ay = rect(a, src_w, src_h, out_w, out_h)
    bw, bh, bx, by = rect(b, src_w, src_h, out_w, out_h)
    span = max(move * speed, 1.0 / fps)
    u = f"clip(in_time/{span:.5f},0,1)"
    s = f"({u})*({u})*(3-2*({u}))"                      # smoothstep
    lerp = lambda p, q: f"({p:.3f}+({q - p:.3f})*{s})"  # noqa: E731

    # zoompan drives off a zoom factor, so express the move as one: the widest
    # of the two rects is zoom 1 and everything else crops into it.
    base_w = even(max(aw, bw))
    base_h = min(even(base_w * out_h / out_w), even(src_h))
    base_w = min(base_w, even(src_w))
    pre_x = even(min(max((ax + aw / 2 + bx + bw / 2) / 2 - base_w / 2, 0), src_w - base_w))
    pre_y = even(min(max((ay + ah / 2 + by + bh / 2) / 2 - base_h / 2, 0), src_h - base_h))
    z = lerp(base_w / aw, base_w / bw)
    cx = lerp(ax + aw / 2 - pre_x, bx + bw / 2 - pre_x)
    cy = lerp(ay + ah / 2 - pre_y, by + bh / 2 - pre_y)
    vw, vh = f"({base_w}/({z}))", f"({base_h}/({z}))"
    x = f"clip(({cx})-{vw}/2,0,{base_w}-{vw})"
    y = f"clip(({cy})-{vh}/2,0,{base_h}-{vh})"
    return (f"crop={base_w}:{base_h}:{pre_x}:{pre_y},"
            f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={out_w}x{out_h}:fps={fps:.6f}")


def merge(pieces):
    """Fuse neighbours that are contiguous in the source at the same speed."""
    out = []
    for p in pieces:
        q = out[-1] if out else None
        if (q and "cam" not in p and q["src"] == p["src"]
                and abs(q["end"] - p["start"]) < 1e-6
                and abs(q["speed"] - p["speed"]) < 1e-9
                and bool(q.get("mute")) == bool(p.get("mute"))):
            q["end"] = p["end"]
        else:
            out.append(dict(p))
    return out


def render_video(p, cam, prev_cam, src, dims, dst, args):
    src_w, src_h = dims
    speed = float(p.get("speed", 1.0))
    move = float(p.get("move", 0)) if prev_cam and prev_cam != cam else 0
    if move > 0 and (cam.get("fit") or prev_cam.get("fit")):
        move = 0                        # zoompan cannot pad; hard-cut instead
    if move > 0:
        vf = moving_filter(prev_cam, cam, move, speed, src_w, src_h,
                           args.out_w, args.out_h, args.fps)
    else:
        vf = static_filter(cam, src_w, src_h, args.out_w, args.out_h)
    vf += f",setpts=PTS/{speed:.6f},format=yuv420p"

    codec = (["-c:v", "libx264", "-crf", "17", "-preset", "veryfast"] if args.software
             else ["-c:v", "h264_videotoolbox", "-b:v", args.bitrate])
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", f"{p['start']:.4f}", "-t", f"{p['end'] - p['start']:.4f}",
         "-i", src, "-an", "-vf", vf] + codec +
        ["-video_track_timescale", "30000", dst], check=True)


def render_audio(p, src, tmp):
    """Speed-changed PCM for one piece, as a signed-16 array."""
    speed = float(p.get("speed", 1.0))
    af = f"atempo={speed:.6f},aresample={RATE}"
    if p.get("mute"):
        af = "volume=0," + af
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error",
         "-ss", f"{p['start']:.4f}", "-t", f"{p['end'] - p['start']:.4f}",
         "-i", src, "-vn", "-af", af,
         "-f", "s16le", "-acodec", "pcm_s16le", "-ar", str(RATE), "-ac", str(CH), "-"],
        capture_output=True, check=True).stdout
    a = array.array("h")
    a.frombytes(out[:len(out) - len(out) % (2 * CH)])
    return a


def splice(chunks, path):
    """Concatenate PCM chunks with an equal-power fade across every seam."""
    n = int(SEAM * RATE)
    buf = array.array("h")
    for k, a in enumerate(chunks):
        if k and len(a) > n * CH and len(buf) > n * CH:
            for i in range(n):
                g = math.sin(math.pi / 2 * (i / n)) ** 2
                for c in range(CH):
                    j = len(buf) - (n - i) * CH + c
                    buf[j] = int(buf[j] * (1 - g))
                    a[i * CH + c] = int(a[i * CH + c] * g)
        buf.extend(a)
    with open(path, "wb") as fh:
        fh.write(buf.tobytes())
    return len(buf) / CH / RATE


def main():
    ap = argparse.ArgumentParser(description="Cut, speed-ramp and frame a screen recording.")
    ap.add_argument("plan")
    ap.add_argument("output")
    ap.add_argument("--map", help="write a source->output time map here")
    ap.add_argument("--bitrate", default="14M")
    ap.add_argument("--software", action="store_true")
    ap.add_argument("--workdir", help="keep piece files here (also resumes)")
    ap.add_argument("--audio-only", action="store_true",
                    help="rebuild the audio and remux, reusing rendered video")
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH")

    plan = json.loads(open(args.plan).read())
    args.out_w = int(plan.get("output", {}).get("width", 1920))
    args.out_h = int(plan.get("output", {}).get("height", 1080))
    args.fps = float(plan.get("output", {}).get("fps", 30))
    sources = plan["sources"]
    dims = {k: probe(v) for k, v in sources.items()}
    pieces = merge(plan["pieces"])

    work = args.workdir or tempfile.mkdtemp(prefix="tutorialcut-")
    os.makedirs(work, exist_ok=True)
    print(f"{len(plan['pieces'])} pieces -> {len(pieces)} after merge")

    cam, prev_cam = plan.get("default_cam"), None
    files, chunks, mapping, clock = [], [], [], 0.0
    for i, p in enumerate(pieces):
        if "cam" in p:
            prev_cam, cam = cam, p["cam"]
        else:
            prev_cam = None
        if cam is None:
            sys.exit("no camera: give the plan a default_cam or the first piece a cam")
        src = sources[p["src"]]
        dst = os.path.join(work, f"v{i:05d}.mp4")
        if not (args.workdir and os.path.exists(dst) and os.path.getsize(dst) > 800):
            if not args.audio_only:
                render_video(p, cam, prev_cam, src, dims[p["src"]], dst, args)
        files.append(dst)
        out_dur = vduration(dst)
        chunks.append(fit(render_audio(p, src, work), round(out_dur * RATE)))
        mapping.append({"i": i, "src": p["src"], "src_start": p["start"],
                        "src_end": p["end"], "out_start": round(clock, 3),
                        "out_end": round(clock + out_dur, 3), "speed": p.get("speed", 1.0)})
        clock += out_dur
        print(f"\r  {i + 1}/{len(pieces)}  {clock / 60:5.2f} min", end="", flush=True)

    print("\n  splicing audio…")
    wav = os.path.join(work, "audio.pcm")
    adur = splice(chunks, wav)

    listfile = os.path.join(work, "concat.txt")
    with open(listfile, "w") as fh:
        for f in files:
            fh.write(f"file '{os.path.abspath(f)}'\n")
    print("  muxing…")
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "concat", "-safe", "0", "-i", listfile,
         "-f", "s16le", "-ar", str(RATE), "-ac", str(CH), "-i", wav,
         "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-shortest",
         "-movflags", "+faststart", args.output], check=True)

    if args.map:
        json.dump(mapping, open(args.map, "w"), indent=1)
    src_total = sum(p["end"] - p["start"] for p in pieces)
    print(f"\nwrote {args.output} — video {clock / 60:.2f} min, audio {adur / 60:.2f} min, "
          f"from {src_total / 60:.2f} min of source ({src_total / max(clock, 1):.2f}x)")
    if not args.workdir:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
