# ffmpeg facts learned the hard way

Every line here cost a failed render. Do not re-derive them.

Measured with ffmpeg 8.0.1 on macOS,
`h264_videotoolbox` available.

## zoompan

**`zoompan` must come BEFORE the `setpts` that changes speed.**
It re-times its own output from an internal frame counter at its `fps=`
option, so anything that changed PTS upstream is discarded.

**Never put an `fps=` filter after `setpts`.** Measured: a 3-second piece at
`crop,zoompan,setpts=PTS/1.3,fps=30` produced **13846 frames / 461 seconds**
instead of 70 frames / 2.33 s. The working order is:

```
crop → zoompan → setpts=PTS/speed → format=yuv420p
```

with no `fps` filter and no `-r`. Verified: 70 frames, 2.333 s, correct.

Because zoompan sits upstream of `setpts`, its `in_time` runs on the
**source** clock. A camera move specified in output seconds must be
multiplied by the piece's speed before it goes into the expression.

## h264_videotoolbox

- Rejects `-q:v` — `qscale not available for encoder`. Use `-b:v` (14M for
  1080p screen content).
- Roughly 3.5x realtime for a static crop at 1080p out; zoompan pieces are
  several times slower, which is another reason to use few camera moves.
- Pass `-video_track_timescale 30000` on every piece so the concat demuxer
  gets a consistent timebase.

## Concatenating hundreds of pieces

**Never stream-copy AAC segments together.** Each AAC segment carries
encoder priming (~1024 samples). Concatenating 1000 of them puts a click at
every join and drifts the whole timeline.

What works, and what `tutorialcut.py` does:

1. Render every video piece **without audio** (`-an`).
2. Render each piece's audio to **raw PCM** (`-f s16le`) and splice the
   chunks in Python with a ~10 ms equal-power fade at each seam.
3. Concat the video with the concat demuxer and `-c:v copy`, mux the single
   PCM stream, encode AAC **once**.

**Pin every audio chunk to its video piece's real duration.** Video lengths
quantise to whole frames, audio does not. Left alone the two random-walk
apart over a thousand cuts. Probe each rendered piece with
`ffprobe -show_entries format=duration` and trim or silence-pad the PCM to
match. Verified result: video 32.700 s, audio 32.700 s, exactly.

## atempo

ffmpeg 8's `atempo` accepts 0.5–100 in one instance, so no chaining is
needed even at 6x. Pitch is preserved.

## Seeking

Put `-ss` and `-t` **before** `-i`. Input seeking decodes only what the
piece needs, which is what keeps a thousand-piece render at about a second
per piece. Output seeking would decode from zero every time.

Re-encode rather than stream-copy when cutting: a copy snaps to keyframes
and drifts the cut by up to a second.

## Merging pieces before rendering

A plan generated from word timings produces adjacent pieces at the same
speed (a speech run plus its trailing pad). Fusing those before rendering
took the first run from 1567 pieces to about 1050 — a third less wall clock
and a third fewer encode seams. `tutorialcut.py` does this in `merge()`.

## Silence detection — this file used to say the opposite

> Superseded. The old text read: *"the real cut points come from
> AssemblyAI word timings, which are far more precise than an energy gate."*
> **That was wrong and it produced a cut with clipped words.** ASR word
> timestamps mark the vowel onset, not the consonant burst in front of it, so
> cutting there removes the attack of every word after a pause. Measured on
> that cut: 398 of 415 deletions removed speech-level energy.

Cut points come from an **energy envelope of the source**, computed once:
8 kHz mono, RMS over 10 ms hops, cached as `.npy`. Threshold
`max(5th-percentile * 8, 40)`, silence must hold for `MIN_SIL`, then shrink by
`GUARD` at each end (current values are in `buildplan.py`). Word timings are still needed for captions; they
decide nothing about the cut. Full rationale in `edit-grammar.md`.

`silencedetect` is not used — an in-process numpy envelope is faster than
parsing ffmpeg's log and lets `buildplan.py` reason about margins directly.

## Two things that are NOT the cause of chopped audio

Both were suspected and both were measured innocent. Do not spend the time
again.

- **Per-piece `-ss` seeking into AAC is sample-accurate.** Extracting a
  window with its own `-ss` versus slicing it out of one long decode agreed
  to within 0.02 ms, with identical sample counts and identical head energy.
  Decoder priming after a seek is not a problem here.
- **`atempo` does not eat the head of a chunk.** Head RMS is preserved at
  every chunk length down to 0.16 s. It does get the *length* wrong by up to
  ±10 ms on short chunks, which `fit()` then pins back to the video piece's
  real duration — that is why the pinning exists.

## Fitting a 16:10 capture into a 16:9 frame

A 2880x1800 screen has no 16:9 crop that keeps everything: 2880 wide gives
1620 of height and the app needs ~1694. Cropping loses either the top toolbar
or the bottom track, and losing either is what "the window is very poorly
cut" meant.

`tutorialcut.py` takes a cam with its own `h` plus `"fit": true` and does
scale-to-fit plus pad instead of crop:

```
crop=W:H:X:Y,scale=1920:1080:force_original_aspect_ratio=decrease:flags=lanczos,
pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black
```

2880x1800 lands as 1728x1080 with 96 px pillarbox each side — invisible on a
dark UI, and nothing is ever cut.

`zoompan` cannot pad, so a `move` into or out of a fitted cam is silently
downgraded to a hard cut. That is fine; the grammar says hard cuts anyway.

**Do not mask the spare strip to black.** Tried on the panel camera and
reverted: app tooltips overflow their pane by up to 200 px, so the mask
clipped their first word.
