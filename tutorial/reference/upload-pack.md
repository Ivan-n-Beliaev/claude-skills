# Upload pack

Everything the YouTube form asks for, prepared so the user pastes and never
composes.

## Title

The title is the search query, written the way a coach would type it.

- Lead with the task, not the feature: "How to tag a hockey game" beats
  "Tag Window explained".
- Put the platform in when it narrows the search: "on a Mac".
- Under ~70 characters so it doesn't truncate.
- **No em dashes.** A colon or a comma.
- No competitor names.
- Offer the user two or three genuinely different bets, not three phrasings of
  the same one.

## Description

```
<one sentence: what the viewer will be able to do after watching>

<two or three sentences: what is actually shown, in the presenter's vocabulary>

Try it: https://<your site>/?utm_source=youtube

Chapters
0:00 ...
```

- Tag the link so visits from the video can be told apart.
- Chapters come from `chapters.txt`, first one at 0:00, each at least 10 s.
- No em dashes.
- Nothing claimed that the video does not show.

## Tags

10–15, mixed specificity, all lowercase:

- the searches a viewer would type to find this task
- the task itself, in two or three phrasings
- the context: the sport or field, the platform
- the product name, last

## Captions

Upload `captions.srt`. Its cues are the presenter's words mapped through the edit, which
beats YouTube's auto-captions and gets indexed. Never rewrite a cue to read
better — that is fabrication on a surface people quote from.

## Thumbnail

1280x720. Rendered from `templates/thumbs.html` via `scripts/thumbs.js`.
Three variants, every time.

```bash
node "$SK/scripts/thumbs.js" "$WORK/thumb" --zones
```

`--zones` also writes `_zones` proofs with YouTube's furniture drawn on top.
**Look at them.** Then downscale a variant to 360 px and look at that too; if
the hero does not read there it does not read.

### Use the app's real pixels

**Crop the UI out of the source take at full Retina resolution. Do not redraw
it in HTML.** The first version of this template rebuilt the tag buttons in
CSS, and the redrawn buttons used a different font from the app. Redrawn UI drifts from the product every time the product
changes, and it quietly misrepresents what someone is about to download.
Real pixels cannot drift and are honest. A tight crop of a bright, high
contrast control (coloured buttons, a filled panel) survives thumbnail size
fine — the earlier worry about screenshots going muddy was about cropping a
whole dark window, not one control.

### YouTube eats the edges

The frame is never shown whole. Plan for the furniture:

| Zone | Where | What lands there |
|---|---|---|
| Duration badge | bottom right, ~22% x 18% | black pill with the runtime |
| Progress bar | bottom edge, ~4% | red watched-progress line |
| Hover overlays | bottom strip | queue and menu buttons |

So: **nothing that must be read below 82% of the height, and nothing at all
in the bottom-right corner block.** The first set put the sub-headline at 89%
and the `pelaa.tv` chip bottom-right, directly under the badge. Both were
lost. Keep 5% margins on every side as well.

### The rest

- **Four words maximum** in the hero. It has to read at 320 px wide.
- **Name the subject exactly and say it is a tutorial.** "TAG WINDOW" over
  "PELAA · TUTORIAL" tells a scrolling coach what this is and what it is
  about. A slogan like "ONE KEY ONE TAG" does neither.
- **The sub-line describes, it does not claim.** "Build your own tag buttons,
  step by step" is checkable against the video. Anything that promises an
  outcome is not.
- **The sport has to be visible.** A pure-UI thumbnail does not tell a
  scrolling coach this is hockey. A darkened frame of real ice behind the UI
  does both jobs. Do not stage a dramatic moment the video does not teach —
  the first set led on a goal-scoring chance, which does not represent what
  viewers will do with the app.
- Brand red `#c1272d`, hot red `#e0353c` for text on dark. Heavy grotesque
  for the hero (`SF Pro Display` / `Helvetica Neue` at weight 900).
- **Every number on a thumbnail must be countable in the video.** Do not
  round up for rhythm.

## The note

Write it as one markdown note beside the finished video.

Structure: title options, final description block ready to paste, tags line,
chapters block, thumbnail choice, then a short **What was edited** section —
what got cut, what got sped up, and anything constructed that was not
recorded. That last part is not optional; the user needs to know what is
being published.

Any game footage visible in the tutorial must be footage you own or have
permission to show.

## Upload checklist

One screen, in order, every field already filled:

1. Upload the mp4
2. Title / description / tags pasted
3. Thumbnail uploaded
4. Captions: upload `captions.srt`, English
5. Playlist, category Education, not made for kids
6. Visibility: unlisted first, then public
