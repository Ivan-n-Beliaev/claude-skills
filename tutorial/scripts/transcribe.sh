#!/usr/bin/env bash
# transcribe.sh <workdir> <video...>
#
# Word-level transcription via AssemblyAI. Writes, per input:
#   pN.m4a          64 kbps mono upload copy
#   pN_aai.json     full response (words[] carries ms-accurate timings)
#   pN_phrases.txt  readable transcript, gap before each phrase printed
#
# The phrases file is what the edit is authored from; the json is what the
# cut points and the captions are computed from.
set -euo pipefail

WORK="${1:?workdir}"; shift
: "${ASSEMBLYAI_API_KEY:?ASSEMBLYAI_API_KEY not set}"
mkdir -p "$WORK"

i=0
declare -a IDS NAMES
for f in "$@"; do
  i=$((i + 1)); n="p$i"; NAMES+=("$n")
  ffmpeg -y -v error -i "$f" -vn -ac 1 -c:a aac -b:a 64k "$WORK/$n.m4a"

  url=$(curl -sS -X POST https://api.assemblyai.com/v2/upload \
        -H "authorization: $ASSEMBLYAI_API_KEY" \
        --data-binary @"$WORK/$n.m4a" \
        | python3 -c 'import sys,json; print(json.load(sys.stdin)["upload_url"])')

  id=$(curl -sS -X POST https://api.assemblyai.com/v2/transcript \
       -H "authorization: $ASSEMBLYAI_API_KEY" -H "content-type: application/json" \
       -d "{\"audio_url\":\"$url\",\"language_code\":\"en_us\",\"punctuate\":true,\"format_text\":true,\"disfluencies\":true}" \
       | python3 -c 'import sys,json; print(json.load(sys.stdin)["id"])')
  IDS+=("$id"); echo "$n queued: $id"
done

# Poll. Parse the status out of the BODY - do not fold curl's -w http_code
# into the same capture, which silently turns every status into "200completed"
# and makes the loop run until it times out.
for k in "${!IDS[@]}"; do
  n="${NAMES[$k]}"; id="${IDS[$k]}"
  for _ in $(seq 1 80); do
    curl -sS "https://api.assemblyai.com/v2/transcript/$id" \
         -H "authorization: $ASSEMBLYAI_API_KEY" -o "$WORK/${n}_aai.json"
    st=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$WORK/${n}_aai.json")
    [ "$st" = "completed" ] && { echo "$n done"; break; }
    [ "$st" = "error" ] && {
      python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('error'))" "$WORK/${n}_aai.json" >&2
      exit 1; }
    sleep 10
  done
done

python3 - "$WORK" "${NAMES[@]}" <<'PY'
import json, sys
work, names = sys.argv[1], sys.argv[2:]
for n in names:
    ws = json.load(open(f"{work}/{n}_aai.json"))["words"]
    groups, cur = [], [ws[0]]
    for w in ws[1:]:
        if (w["start"] - cur[-1]["end"]) / 1000 > 0.75:
            groups.append(cur); cur = [w]
        else:
            cur.append(w)
    groups.append(cur)
    out, prev = [], 0.0
    for g in groups:
        s, e = g[0]["start"] / 1000, g[-1]["end"] / 1000
        out.append(f"[{s:7.2f}-{e:7.2f}] (gap {s - prev:5.1f}s) "
                   + " ".join(x["text"] for x in g))
        prev = e
    open(f"{work}/{n}_phrases.txt", "w").write("\n".join(out) + "\n")
    print(f"{n}: {len(ws)} words, {len(groups)} phrases -> {n}_phrases.txt")
PY
