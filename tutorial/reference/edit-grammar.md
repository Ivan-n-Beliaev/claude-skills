# Edit grammar

The numbers and rules behind `buildplan.py`. Derived from the first real run
(a tag-window tutorial: 26 min of source to 11.5 min of output).

## Speed

Unscripted narration has pauses between words. The edit's job is to make that
read as deliberate rather than flat.

| What is on screen | Speed | Why |
|---|---|---|
| Talking, new material | **1.28–1.32** (first run) | Fastest that still sounds natural |
| Talking, repetitive (third button of the same kind) | **1.38–1.45** | The viewer is ahead of the narration |
| Talking, dense / a definition that matters | **1.25** | Give the one hard idea room |
| A pause with a click or drag in it | **3–4.5** | Keeps the action, kills the wait |
| A pause with nothing in it | cut to `PAD` (0.14 s) | Dead air |
| A dialog, a load, a render | **5–6**, muted | Pure waiting |

These are the first run's values. Later runs capped `talk` at 1.2 because
faster narration clipped sustained vowels; see Sanity targets below.

Never take narration past ~1.5x. Past that it stops sounding like a person
explaining something and starts sounding like a podcast on 2x.

## Gaps — the rule that does most of the work

### Where a cut may land (learned the hard way, do not relax this)

**Find cut points in the waveform. Never in the ASR word timings.**

The first version of this skill cut exactly at AssemblyAI's `word.start` and
`word.end`. In my runs ASR marked a word's start at the *vowel onset*, not at the
consonant burst in front of it, so every word following a short pause lost
its attack. On listening, words started mid-sound, and the measurement backed
it exactly:

| | first version | after the fix |
|---|---|---|
| deletions in the cut | 415 | 404 |
| deletions removing speech-level energy | **398 (96%)** | **0 (0%)** |
| RMS in the 80 ms deleted before each resume | 2400–3800 | — |

(Speech average in that recording was ~880 RMS. The loudest thing anywhere
near the cut was the plosive being deleted.)

The procedure `buildplan.py` now implements:

1. Decode the whole source once to an 8 kHz mono RMS envelope at a 10 ms hop
   and cache it. Cheap, and it makes every later decision measurable.
2. Noise floor = 5th percentile of the envelope. Silence threshold =
   `max(floor * 8, speech * 0.012)`, deliberately conservative so a quiet
   fricative never reads as silence.
3. A stretch counts as silence only if it is under threshold for
   `MIN_SIL` (**0.35 s** in `buildplan.py`). Shrink it by `GUARD`
   (**0.15 s**) at each end.
4. Cuts may only land inside what survives step 3. Everything else plays
   whole, at `talk`.

Then the old policy applies to the *verified* silence, not to the ASR gap:

- **< 0.85 s** of silence → collapse to `PAD` (**0.14 s**) at talking speed. Breath
  and word-search. Hundreds of them; removing them is most of the tightening.
- **≥ 0.85 s** → **keep the whole pause** but speed it so it lasts at most
  **1.3 s** on screen. The presenter is almost always doing something in these — a drag,
  a colour pick, a menu. Cutting them makes the video jump; speeding them
  makes it read as high-action.

**Snap the hand-placed region edges too.** The region table is written by ear
against the transcript, so its `a`/`b` values land on word boundaries and have
the same defect, just fewer instances. `snap()` moves each edge onto the
nearest verified silence within `SNAP` (1.5 s); where the narration runs straight through with no
silence at all, it falls back to the quietest 60 ms in reach, which is the
trough between two words.

**Cost:** roughly +15% runtime versus the clipping version. That is the
correct trade: length is not the problem, chopped words are.

### Verify it, every time

```bash
python3 "$SK/scripts/checkcuts.py" "$WORK/plan.json"
```

Prints the share of deletions whose edges still carry speech-level energy.
**Must be 0%.** Anything above that produces clipped words. This is a gate, not
a diagnostic — run it before the render, not after.

### Anything sped past ~3x gets muted

Speech at 6x is noise. The first render had 3 s of sped-up speech over the
file-open dialog because the `run` region had no `mute` flag. Check the
transcript across every `run` region first: if nothing is said there,
muting costs nothing.

## Camera

Framing is defined in **source pixels** as `{x, y, w}` — centre point and
crop width. Height follows the 16:9 output unless the cam carries its own
`h` together with `"fit": true`, which scales-to-fit and pillarboxes instead
of cropping.

### Prove you need a zoom before you build one

**One camera is the default. Two is the maximum. Zero extra cameras is a
legitimate and often correct answer.** A later tutorial used the
`window` frame alone.

The test is one command, and it settles the question in a minute:

```bash
ffmpeg -ss <t> -i take.mp4 -frames:v 1 \
  -vf "scale=1728:1080,pad=1920:1080:96:0:black" win_<t>.png   # then Read it
```

Render the hardest frames — the smallest type in the video — through the exact
output transform and **read them**. Do not judge legibility off the source, and
do not judge it off a half-scale contact sheet. On a 2880x1800 capture fitted to
1728x1080, the tag tooltip (`Lead: 3.0s | Lag: 5.0s`), the menu
key equivalents, the report grid and the track row labels were all legible, so
every zoom in the plan was deleted before it was built.

Two things a zoom costs that are easy to miss:

- **The relationship being taught.** In Pelaa the payoff is usually two corners
  of the screen at once: click a cell in the report at top right, tags light up
  on the track at bottom left. A crop that holds both *is* the screen. Zooming
  in on either half destroys the only thing the shot was for.
- **The keystroke badge.** CleanShot renders it at screen centre-bottom
  (measured on one capture: source x 1340–1540, y 1496–1630). Only a
  full-screen frame is guaranteed to hold it, and on a tutorial about keyboard
  shortcuts it is not decoration.

The first version of this skill used five hand-typed camera rectangles with
gliding moves between them. The zoom looked awkward and the window was
badly cut: three of the five cameras were geometrically wrong:

- the cold-open camera sliced the app window, cutting a track row through the
  middle and clipping the right edge of the tag panel;
- the `full` camera cut 180 px off the **bottom** of an 1800 px capture,
  which is where the track lives, not off the top;
- the `panel` camera framed 1560 px around a content column ~530 px wide, so
  it zoomed in and still spent two thirds of the frame on empty background.
  That is what "awkward" was: the frame moved and nothing got closer.

### The rules that replaced them

1. **Measure the geometry off the capture. Never eyeball it.** Before writing
   a single `CAM` entry, pull half-scale frames and read the real numbers:
   window bounds, pane divider, toolbar band, the union bounding box of the
   working content across a dozen sampled frames. On the tag-window capture
   that was: menu bar `y 0–50`, title bar `y 50–106`, app content
   `y 106–1800`, divider `x 1530`, tag toolbar `y 110–172`, tag work area
   `x 1545–2440, y 190–1140`. Every camera falls out of those numbers.
2. **Two frames, not five.** One for the whole window, one for the panel that
   carries the work. Every extra camera is another rectangle that can be
   wrong, and the viewer gains nothing from a third.
3. **Never crop the app window.** A 2880x1800 capture does not fit 16:9;
   cropping loses either the toolbar at the top or the track at the bottom.
   Use `{"w": 2880, "h": 1800, "fit": true}` — scale to fit, pillarbox the
   remainder. On a dark UI the bars are invisible, and *nothing is ever cut*,
   which was the defect in the first version.
4. **A panel crop is sized by content height, not width.** The tag window's
   pane is 1350 px wide, so any 16:9 frame inside it is at most 759 px tall —
   and the Tag Editor needs 1010. The narrowest frame that holds the whole
   thing is 1840 px, which necessarily catches ~490 px of the neighbouring
   pane. **Accept the strip.** Painting it black was tried and reverted: the
   app's tooltips overflow the divider by up to 200 px, so the mask clipped
   their first word — reintroducing exactly the defect being fixed.
5. **Hard cuts only. No moves.** A gliding camera over a screen recording is
   decoration, and every glide is another chance to be wrong. Cut at a chapter
   boundary and hold. (`move` still works in the renderer; do not use it.)
6. **Change framing only where the content changes**, not per cut. A run of
   forty pieces sharing one camera has forty invisible cuts.
7. **Once the layout changes for good, stay wide.** In the tag-window video
   the divider is dragged at 6:00 and a real game is loaded right after, so
   both panes matter from there to the end — one camera change, not four.
8. **Zoom past ~1.9x from a 2880 source and it softens.** `w = 1500` is about
   the floor for a sharp 1080p; the `panel` frame above is 1.57x.

Preset names that earned their keep: `window` (whole screen, fitted) and
`panel` (the working panel). That is the whole set.

## Cuts

- **Slates go.** "Video one. Tag window." is for the editor, not the viewer.
- **Fumbles: cut the dead-end, keep the correction.** When the presenter names the wrong
  modifier and corrects it, the correction names both keys — that is
  better teaching than the clean take. Cut only the "oh, sorry" and the
  four seconds of nothing around it.
- **Repeated half-sentences:** keep the second, complete one.
- **A stitch between two takes needs no transition** if the second take
  opens by naming where it is ("we figured out how tag buttons work, now
  let's go through the labels"). Use that sentence
  as the seam and cut the second slate.

## Cold open

If beat 1 of the beat card was not recorded, build it: 10–15 s from late in
the take where the thing being taught visibly works, with its own audio, cut
at a sentence boundary. Then hard cut to the real opening line.

Flag it to the user explicitly. The footage and words are theirs, but the
order is not the one they recorded.

## Sanity targets

Recalibrated **twice**. The original targets (1.8–2.0x, output half the source)
were only reachable by deleting word onsets. The second set (1.45–1.65x, output
55–60%) was only reachable at `talk` 1.28–1.32, which the audio post-mortem
then measured as the thing eating sustained vowels. Both are dead. The numbers
below assume the 1.2 cap, and they are what a later tutorial actually hit.

- **1.25–1.35x** on kept source. That is what a 1.2 talk cap plus collapsed
  silence produces; there is no honest way to beat it.
- Output around **70%** of total source length. On a dense feature, expect it.
- **Runtime is no longer a speed problem, it is a content problem.** Once
  `talk` is capped and the dead air is gone, tightening the silence policy
  further buys seconds, not minutes: on one tutorial, dropping `PAD` to
  0.12 and `GAP_MAX_OUT` to 0.90 saved **6.6 seconds off 19 minutes**. If a cut
  has to be shorter, cut content and say which, do not reach for the speed
  knob.
- **`checkcuts.py` must report 0%.** This one is not a target, it is a gate.
- **Splices per output minute under 55.** The single number that predicts how
  the edit will feel.

### Two boundary fixes the gate will otherwise catch

Both are now in `buildplan.py`.

1. **Merge quiet runs separated by a blip** (`BLIP = 0.06`). A single 10 ms
   frame of energy inside a 0.75 s pause splits it into three sub-MIN_SIL
   fragments, and the whole pause becomes uncuttable.
2. **`SNAP` is 1.50, not 0.60.** Five hand-placed region edges found no
   qualifying silence within 0.6 s, fell through to the "quietest 60 ms"
   fallback, and landed on an inhale or a word onset. Widening it is free:
   an edge can only ever land inside verified silence, and silence pulled
   *inside* a region is collapsed to `PAD` by the gap policy, so it adds
   nothing to the runtime.
