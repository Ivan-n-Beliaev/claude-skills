#!/bin/bash
# corpus-ask.sh — query a NotebookLM notebook, with retry on transient failures.
#
# Usage: corpus-ask.sh <notebook-id> <outfile.json> "<prompt>"
#
# The CLI is `nlm` (notebooklm-mcp-cli), not `notebooklm`. The older `notebooklm ask`
# binary from notebooklm-py is not needed: `nlm notebook query --json --new-conversation` gives the same
# {answer, references:[{source_id, citation_number, cited_text}]} payload, and
# --new-conversation replaces the old `notebooklm clear` step.
#
# Chat requests time out roughly 1 in 8, returning either an error object or no
# answer field. Both are detected and retried here, so anything consuming this
# output can assume a well-formed answer.
#
# Throttling: with five or more queries in flight the notebook starts answering
# {"status":"error","error":"The notebook returned no answer"} for many of them
# (19 of 52 on one run). Keep concurrency at 2 and let the backoff grow.

set -uo pipefail

NB_ID="${1:?usage: corpus-ask.sh <notebook-id> <outfile.json> <prompt>}"
OUT="${2:?missing outfile}"
PROMPT="${3:?missing prompt}"
MAX_TRIES="${CORPUS_MAX_TRIES:-5}"
TIMEOUT="${CORPUS_TIMEOUT:-240}"

for try in $(seq 1 "$MAX_TRIES"); do
  nlm notebook query "$NB_ID" "$PROMPT" --json --new-conversation -t "$TIMEOUT" \
    2>/dev/null | sed -n '/^{/,$p' > "$OUT"

  if python3 - "$OUT" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception as e:
    print(f"  unparseable JSON: {e}", file=sys.stderr); sys.exit(1)
d = d.get("value", d)
if d.get("error"):
    err = d.get("message") or (d["error"] if isinstance(d["error"], str) else "unknown")
    print(f"  API error: {err}", file=sys.stderr); sys.exit(1)
if not d.get("answer"):
    print("  no answer field", file=sys.stderr); sys.exit(1)
refs = d.get("references") or []
anchorable = sum(1 for r in refs if r.get("cited_text"))
print(f"  len={len(d['answer'])} refs={len(refs)} anchorable={anchorable}")
PY
  then
    exit 0
  fi

  echo "  attempt $try/$MAX_TRIES failed for $OUT" >&2
  [ "$try" -lt "$MAX_TRIES" ] && sleep $((try * 30))
done

echo "FAILED after $MAX_TRIES attempts: $OUT" >&2
exit 1
