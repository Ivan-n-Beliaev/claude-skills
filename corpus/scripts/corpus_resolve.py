#!/usr/bin/env python3
"""Turn a raw nlm ask-JSON into a passage-cited QA note in the vault.

Does the step that the notebooklm-skill plugin's extract_passages.py and
resolve_citations.py did. I had patched those locally and a reinstall replaced my
patches, so this script owns the whole step. It reads the same JSON and writes the
same `### Passage N` format.

Usage:
  corpus_resolve.py --qa in.json --sources sources.json --slug my-book \
      --title "Concept - Deep Treatment" [--dashboard "..."] [--date YYYY-MM-DD]

Two numbering systems, deliberately:
  * PASSAGE numbers are per source file and monotonic. They only ever grow, so an
    anchor written today still resolves after later batches append more passages.
  * REFERENCE numbers are per QA note, compact, assigned in order of first appearance
    in the answer. Unresolvable markers (NotebookLM returns cited_text: null for ~30%
    of refs) keep NotebookLM's own number, so a bare [3] and an anchored 3 in the same
    note can mean different references. That collision is expected; see SKILL.md #16.
"""
import os
import argparse, json, re, sys
from datetime import date
from pathlib import Path

VAULT = Path(os.environ.get("VAULT_ROOT", "."))


def safe_filename(title):
    t = re.sub(r'[/:*?"<>|]', '-', title)
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:120].rstrip(' -') if len(t) > 120 else t


OFFER = re.compile(
    r'\n+(?:[^\n]{0,6})?(?:Would you like|Do you want|Shall I|Should I)\b[^\n]*\?[^\n]*\s*$',
    re.IGNORECASE)


BACKTICKED = re.compile(r'`((?:\[\d+(?:\s*[-,]\s*\d+)*\]\s*)+)`')


def unbacktick_markers(answer):
    """Unwrap citation markers NotebookLM sometimes emits as code spans: `[1]`, `[2] [3]`.

    Seen on one run in 30 of 57 markers in one answer. Left alone, the
    resolved wikilink lands inside the code span and Obsidian renders it as literal text.
    """
    return BACKTICKED.sub(r'\1', answer)


def strip_trailing_offer(answer):
    """Drop NotebookLM's closing offer ("Would you like me to turn this into a PDF? \U0001F4C4").

    It is chat furniture, not source content, and it survives into the concept note's
    raw material where it reads as if the author said it.
    """
    return OFFER.sub('', answer).rstrip()


def load_qa(path):
    d = json.load(open(path))
    d = d.get("value", d)
    if d.get("error"):
        sys.exit(f"ask JSON carries an error: {d.get('message')}")
    if not d.get("answer"):
        sys.exit("ask JSON has no answer field")
    return d["answer"], d.get("references") or []


def expand(spec):
    out = []
    for part in spec.split(','):
        part = part.strip()
        if '-' in part:
            try:
                a, b = part.split('-', 1)
                out.extend(range(int(a), int(b) + 1))
            except ValueError:
                continue
        else:
            try:
                out.append(int(part))
            except ValueError:
                continue
    return out


def append_passages(src_path, chunks):
    """Append new chunks as ### Passage N, continuing existing numbering.

    Returns {chunk_key: passage_number} for every chunk, new or already present.
    """
    content = src_path.read_text()
    existing, highest = {}, 0
    for m in re.finditer(r'### Passage (\d+)\n\n(.+?)(?=\n### Passage |\Z)', content, re.DOTALL):
        n = int(m.group(1))
        highest = max(highest, n)
        existing[m.group(2).strip()[:100]] = n

    mapping, additions = {}, []
    for c in chunks:
        key = c[:100]
        if key in existing:
            mapping[key] = existing[key]
            continue
        highest += 1
        existing[key] = highest
        mapping[key] = highest
        additions.append((highest, c))

    if additions:
        if "## Cited Passages" not in content:
            content = content.rstrip() + "\n\n## Cited Passages\n"
        block = "".join(f"\n### Passage {n}\n\n{c}\n" for n, c in additions)
        src_path.write_text(content.rstrip() + "\n" + block)
    return mapping, len(additions)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qa", required=True)
    ap.add_argument("--sources", required=True)
    ap.add_argument("--slug", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--dashboard", default="")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--vault", default=str(VAULT))
    args = ap.parse_args()

    vault = Path(args.vault)
    sdata = json.load(open(args.sources))
    sources = sdata if isinstance(sdata, list) else sdata.get("sources", [])
    titles = {s["id"]: safe_filename(s["title"].strip()) for s in sources}

    answer, refs = load_qa(args.qa)
    answer = strip_trailing_offer(unbacktick_markers(answer))
    sources_dir = vault / "Notes/NotebookLM" / args.slug / "Sources"
    rel_sources = f"Notes/NotebookLM/{args.slug}/Sources"

    # Group anchorable cited_text by source, preserving citation order
    by_source, cn_chunk = {}, {}
    for r in refs:
        ct = (r.get("cited_text") or "").strip()
        cn = r.get("citation_number")
        sid = r.get("source_id")
        if not ct or cn is None or sid not in titles:
            continue
        cn_chunk[cn] = (sid, ct)
        seen = by_source.setdefault(sid, [])
        if ct[:100] not in {c[:100] for c in seen}:
            seen.append(ct)

    # Write passages, sequentially per source file
    passage_of = {}
    for sid, chunks in by_source.items():
        f = sources_dir / f"{titles[sid]}.md"
        if not f.exists():
            print(f"  MISSING source file: {f.name}", file=sys.stderr)
            continue
        mapping, added = append_passages(f, chunks)
        print(f"  {titles[sid]}: +{added} passages", file=sys.stderr)
        for key, n in mapping.items():
            passage_of[(sid, key)] = n

    # cn -> (title, passage)
    anchor = {}
    for cn, (sid, ct) in cn_chunk.items():
        n = passage_of.get((sid, ct[:100]))
        if n is not None:
            anchor[cn] = (titles[sid], n)

    # Rewrite [N] markers; compact display numbering by first appearance
    display, refs_out = {}, []

    def sub(m):
        links = []
        for n in expand(m.group(1)):
            if n not in anchor:
                links.append(f"[{n}]")
                continue
            if n not in display:
                title, p = anchor[n]
                display[n] = len(display) + 1
                refs_out.append((display[n], title, p))
            title, p = anchor[n]
            links.append(f"[[{rel_sources}/{title}#Passage {p}|{display[n]}]]")
        return " ".join(links)

    resolved = re.sub(r'\[(\d+(?:\s*[-,]\s*\d+)*)\]', sub, answer)

    ref_lines = "\n".join(
        f"{d}. [{t} — Passage {p}](<{rel_sources}/{t}.md#Passage {p}>)"
        for d, t, p in refs_out
    )
    cited_titles = sorted({t for _, t, _ in refs_out})
    src_lines = "\n".join(f"- [[{rel_sources}/{t}|{t}]]" for t in cited_titles)
    related = f'\nrelated:\n  - "[[{args.dashboard}]]"' if args.dashboard else ""

    out = vault / "Notes/NotebookLM" / safe_filename(args.slug) / "QA" / f"{args.date} {safe_filename(args.title)}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""---
type: reference
status: current
date: {args.date}
source: "notebooklm:{args.slug}"{related}
---

# {args.title}

{resolved}

---

## References

{ref_lines}

## Sources

{src_lines}
""")
    bare = len(set(re.findall(r'(?<!\|)\[(\d+)\]', resolved)))
    print(f"CREATED: {out.name} — {len(refs_out)} anchored, {bare} bare, {len(cited_titles)} sources",
          file=sys.stderr)


if __name__ == "__main__":
    main()
