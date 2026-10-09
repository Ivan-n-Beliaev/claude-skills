---
name: tutorial
description: Turn raw screen-recording takes of an app into a finished, publishable YouTube tutorial — stitch the parts, cut dead air, ramp the speed, add camera framing, fix the fumbles, then produce captions, chapters, title, description, tags and thumbnails. USE WHEN the user says "edit the tutorial", "I recorded a tutorial", "/tutorial", hands over CleanShot .mp4 paths of an app walkthrough, or asks for a YouTube upload pack from a screen recording.
argument-hint: [path/to/take1.mp4] [path/to/take2.mp4] ...
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Tutorial — recording to upload pack

One take (or several) goes in. What comes out is a finished 1080p mp4 plus
everything the YouTube upload form asks for. The user's only remaining job is
picking a thumbnail and clicking through the upload list.

**Read this whole file before running anything.** The three reference files
carry the parts that are easy to get wrong; load them at the step that names
them, not before.

- `reference/edit-grammar.md` — how fast, how tight, where the camera goes
- `reference/ffmpeg-gotchas.md` — encoder facts that cost real time to learn
- `reference/upload-pack.md` — title, description, tags, thumbnail rules
- `examples/v3-tag-window-buildplan.py` — the real region table from the
  tag-window video, as revised after the first review.
  Use it for the shape of a region table and the camera measurements. Its
  speed and silence constants are older than `scripts/buildplan.py`, which
  is the current source of truth.

> **Three defects appeared in the first run and all three are now fixed in
> the tooling. Do not reintroduce them.**
> 1. Cuts landed on ASR word timings and clipped the attack off every word
>    after a pause — 96% of deletions ate speech. `checkcuts.py` is now a
>    gate; it must read 0% before you render.
> 2. Five hand-typed camera rectangles with gliding moves, three of them
>    cutting through the app window. Now two measured cameras, hard cuts, and
>    the window frame pillarboxes rather than crops.
> 3. Thumbnail UI redrawn in CSS with the wrong font, and copy sitting under
>    YouTube's duration badge. Now real pixels cropped from the take, inside
>    a checked safe box.

Renderer: `scripts/tutorialcut.py`.

---

## 0 · Set up

```bash
export SK="<path to this skill folder>"
export WORK="<scratchpad>/tutorial-<slug>"     # a scratch folder, not your notes or repo
mkdir -p "$WORK"
```

Everything intermediate lives in `$WORK`. Only the finished mp4, the
thumbnails and the upload-pack note leave it.

**Ask the user nothing yet.** Watch the footage first — most questions answer
themselves, and the ones that don't get asked once, at step 6.

## 1 · Probe and stitch order

```bash
bash "$SK/scripts/layout.sh" "$WORK" "take1.mp4" "take2.mp4"
```

Prints resolution/duration per file and writes sample frames to
`$WORK/frames/`. **Read those frames, then measure them.**

Reading is not enough — the first run eyeballed the camera rectangles and
three of five cut through the app window. Write down, in source pixels:

- the app window bounds, and the menu bar / title bar bands above it
- every pane divider
- any fixed toolbar band
- the **union bounding box of the working content** over a dozen frames
  sampled across the whole take, because panels move (an editor card that
  follows the selected object shifts hundreds of pixels)

Half-scale frames are fine to read off; double the numbers. Note when the
layout changes for good — a divider drag, a video loading — because that is
where the framing changes and nowhere else.

Wants `2880x1800`. At `1440x900` the recording was made at logical
resolution: say so plainly, because every zoom will be soft and no edit
fixes it.

Order the parts by the on-screen clock in the frames (CleanShot filenames
already sort correctly, but a re-take can break that).

## 2 · Transcribe — AssemblyAI, not local whisper

```bash
bash "$SK/scripts/transcribe.sh" "$WORK" "take1.mp4" "take2.mp4"
```

Writes `p1_aai.json` … (word-level) and `p1_phrases.txt` … (readable, with
the gap before each phrase printed). `$ASSEMBLYAI_API_KEY` must be set in the
environment. **This uploads the recording's audio to AssemblyAI.**

> Local `whisper-cli` is the alternative. On a slow machine it runs slower
> than realtime and starves the ffmpeg renders of CPU. In my runs AssemblyAI returned 25 minutes of word-level audio in about 2 minutes.

**Read `*_phrases.txt` end to end.** This is the edit. Everything after this
step is mechanical.

## 3 · Mark the structure

From the phrases file, write down:

1. **Slates to cut** — "Video one. Tag window." spoken markers, and the
   silence around them. Never ship a slate.
2. **The real first sentence** and the real last one.
3. **Section boundaries** — where the topic turns. These become both the
   region table and the chapter list; do them once.
4. **Fumbles.** Look for `sorry`, `cut, again`, a repeated half-sentence, a
   wrong modifier key named then corrected. For each, decide: cut the
   dead-end and **keep the correction** — the correction usually carries
   information the clean take never states. Get word-level timestamps from
   the `_aai.json` before cutting; phrase boundaries are too coarse.
5. **Dead stretches with action in them** — a file-open dialog, a long
   render. These are not cuts, they are 5–6x runs.
6. **Whether a cold open exists.** The opening beat should be the
   finished thing playing. If none was recorded, lift 10–15 s of the
   payoff from late in the take and put it first. Flag that you did.

## 4 · Author the plan

Copy `scripts/buildplan.py` into `$WORK`, then edit two tables in it:

- `CAM` — camera presets in **source** pixels, from the measurements in
  step 1. Two presets: `window` (whole screen, `"fit": true`, pillarboxed so
  nothing is ever cropped) and `panel` (the working area, sized by content
  height). No `move` keys — hard cuts only.
- `R` — one row per region: `src`, `a`, `b`, `cam`, `talk`, `gap`, `tag`.
  Mark every sped-up dialog or load `run=` **and** `mute=True`.

Read `reference/edit-grammar.md` now — it gives the speed numbers, the camera
rules and the silence policy the script implements. The script finds its cut
points in the waveform, not in the word timings; that is not a knob.

```bash
python3 "$WORK/buildplan.py"                       # writes plan.json + report
python3 "$SK/scripts/checkcuts.py" "$WORK/plan.json"   # GATE: must be 0%
```

**Do not render until `checkcuts.py` reads 0%.** It reports the share of
deletions whose edges still carry speech-level energy; anything above zero
means words are being clipped, which is the one defect the user cannot listen
past. Re-run with `--verbose` to see which cuts.

Then check the per-region report against the sanity targets at the end of
`reference/edit-grammar.md`.

## 5 · Render

**Test-render 40 pieces first.** A full pass was 45 minutes for 1138 pieces in my run; a camera mistake
found afterwards costs all of it. Slice a handful of pieces from each camera
into a throwaway plan, render that, and look at the frames.

```bash
python3 - <<'PY'
import json
p = json.load(open('plan.json')); ps = p['pieces']
i = next(k for k, x in enumerate(ps) if x.get('cam', {}).get('w') == 1840)  # a panel piece
p['pieces'] = ps[:18] + ps[i:i+22]
json.dump(p, open('plan_test.json', 'w'), indent=1)
PY
python3 "$SK/scripts/tutorialcut.py" plan_test.json test.mp4 --workdir worktest
ffmpeg -ss 2 -i test.mp4 -frames:v 1 -y t1.png     # then Read the pngs
```

Check on every camera: is any edge of the app window cut mid-element? Is more
than a third of the frame empty? Both were true on the first run and both are
visible in one frame.

Then the real thing:

```bash
python3 "$SK/scripts/tutorialcut.py" "$WORK/plan.json" \
  "$WORK/<slug>.mp4" --workdir "$WORK/work" --map "$WORK/timemap.json"
```

Budget **about 2 seconds per merged piece** — a 25-minute source is
roughly 1000 pieces. **Run it in the
background** and do steps 6–8 while it works.

`--workdir` makes it resumable, but only by index — editing the plan
renumbers everything after the change. **Always `cp plan.json plan_old.json`
before touching `buildplan.py`**, then carry the survivors across:

```bash
python3 buildplan.py
python3 "$SK/scripts/reuse.py" "$WORK/work" "$WORK/work2"
python3 "$SK/scripts/tutorialcut.py" "$WORK/plan.json" \
  "$WORK/<slug>.mp4" --workdir "$WORK/work2" --map "$WORK/timemap.json"
```

`reuse.py` matches pieces by content, not position. Adding one cut on the
first run reused 1136 of 1138 pieces and turned a 45-minute re-render into
four minutes. Without it, every note the user gives costs a full render.

Read `reference/ffmpeg-gotchas.md` if you touch the renderer. Every fact in
it was paid for once already.

Verify when it finishes:

```bash
ffprobe -v error -show_entries stream=codec_type,duration -of csv=p=0 "$WORK/<slug>.mp4"
```

Video and audio durations must match to the millisecond. If they don't, the
audio pinning in `tutorialcut.py` broke — fix it there, not with a patch.

## 6 · Ask the user the one round of questions

Only what the user alone can decide, and only once, batched:

- Title, if two candidates are genuinely different bets
- Thumbnail variant
- Anything the footage left factually ambiguous

Never ask about craft: cut points, speeds, framing, caption wording.

## 7 · Package

```bash
python3 "$WORK/package.py"          # copy from scripts/, edit the CHAPTERS table
```

Maps the word timings through `timemap.json` and writes `captions.srt` and
`chapters.txt`. Chapter titles come from the section boundaries you already
marked in step 3.

Then read `reference/upload-pack.md` and write the upload-pack note.

## 8 · Thumbnails

Two assets, both cut from the **source take** at full Retina resolution:

```bash
mkdir -p "$WORK/thumb" && cp "$SK/templates/thumbs.html" "$WORK/thumb/"
# ui.png  - the app control the video is about, cropped tight
ffmpeg -ss <t> -i take.mp4 -frames:v 1 -vf "crop=W:H:X:Y" -y "$WORK/thumb/ui.png"
# ice.png - a 16:9 frame of real ice, used dark behind everything.
#           Only from footage you own or have written permission to use,
#           never a broadcast. Otherwise use a plain dark background.
ffmpeg -ss <t> -i take.mp4 -frames:v 1 -vf "crop=1580:888:170:112" -y "$WORK/thumb/ice.png"
node "$SK/scripts/thumbs.js" "$WORK/thumb" --zones
```

**Never redraw the UI in CSS.** Real pixels cannot drift from the product and
cannot get the font wrong.

Then two checks, both of which the first set failed:

```bash
python3 "$SK/scripts/checkzones.py" "$WORK"/thumb/thumb_?.png   # GATE
```

1. **`checkzones.py` must pass.** It counts bright pixels below 82% height
   and inside the bottom-right badge block. The first set scored 5951 and
   1712 there; both regions are painted over in the feed. Read the `_zones`
   proofs to see what to move.
2. **Downscale to 360 px and read it.** If the hero does not survive that, it
   does not survive the feed.

Three variants, always — the user decides by reacting to something real.
`reference/upload-pack.md` has the full rules: four words maximum, name the
subject and say it is a tutorial, and **every claim must be true of what the
video shows.**

## 8b · Guide material (do this every time, it is nearly free)

```bash
python3 "$WORK/guide.py" "<deliverable>/guide-material"   # copy from scripts/
```

Writes a chapter-headed transcript on the **edited** timeline plus full-
Retina figures pulled from the **source** takes, not the 1080p render, so
they stay sharp in print. That pair is the spine of a detailed written guide
later, with no rewatching and no re-recording.

Edit the `FIGURES` table to name the moments worth a still. Aim for one or
two per chapter and caption each with what it shows, not what it is.

> **Strict mapping matters here.** `out_time(..., strict=True)` returns None
> for a moment that was cut. Without it, cut words fall forward onto the next
> kept piece and the slate ends up glued to the first real sentence. The same
> trap applies to captions — a word that was cut must not appear in the SRT.

## 9 · Deliver

Open the mp4 and the three thumbnails for the user. State plainly:
runtime, source-to-output ratio, what was cut, and anything you constructed
that was not recorded (a cold open especially).

---

## Hard rules

- **Notes folders and repos never hold media.** Renders and takes stay in
  the scratch folder; only the upload-pack note is kept.
- **No invented content.** Captions are the presenter's words. Chapter titles
  describe what was actually done. Thumbnail claims are countable from the footage.
- **No em dashes in outbound copy** — title, description and thumbnail text
  are outbound.
- **No competitor names** anywhere in the copy.
- **Never re-record.** 70% quality ships. If a section is genuinely
  unusable, cut it and say what is missing.
- **`checkcuts.py` reads 0% or you do not render.** Runtime is negotiable;
  chopped words are not.
- **Anything past ~3x is muted.** Speech at 6x is noise.
- **Nothing gets cropped off the app window.** Fit and pillarbox instead.
- **Real app pixels on thumbnails.** Never redrawn UI.
