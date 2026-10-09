#!/usr/bin/env bash
# layout.sh <workdir> <video...>
#
# Probe every take and write sample frames. The frames are not a formality:
# the camera plan is measured off them, in source pixels.
set -euo pipefail

WORK="${1:?workdir}"; shift
mkdir -p "$WORK/frames"

i=0
for f in "$@"; do
  i=$((i + 1)); n="p$i"
  # `read` returns 1 at EOF without a trailing newline, and `set -e` would
  # kill the script on it. Feed it a here-string and guard the status.
  probe=$(ffprobe -v error -select_streams v:0 \
    -show_entries stream=width,height,r_frame_rate \
    -show_entries format=duration -of csv=p=0 "$f" | tr '\n,' '  ')
  read -r w h fps dur <<<"$probe" || true
  printf '%s  %s\n  %sx%s @ %s  %.1f s (%d:%02d)\n' \
    "$n" "$f" "$w" "$h" "$fps" "$dur" "$((${dur%.*} / 60))" "$((${dur%.*} % 60))"
  [ "$w" = "2880" ] || echo "  !! not a full-Retina capture - zooms will be soft"

  # ten evenly spaced frames, half width, enough to read the layout
  total=${dur%.*}
  for k in $(seq 0 9); do
    t=$((total * k / 10 + 2))
    ffmpeg -y -v error -ss "$t" -i "$f" -frames:v 1 -vf scale=1440:-1 \
      "$WORK/frames/${n}_$(printf '%04d' "$t").png"
  done
done

echo
echo "frames in $WORK/frames - read them before writing the camera table."
echo "coordinates in those files are HALF the source; double them for CAM."
