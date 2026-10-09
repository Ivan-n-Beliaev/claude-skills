#!/usr/bin/env python3
"""Audit one concept note's citations. Usage: audit_note.py <note.md> [--renumber]

Checks four things the three-pattern corruption grep cannot see:
  * every inline anchor points at a "### Passage N" heading that really exists
  * every inline display number has a References entry naming the same source+passage
  * every References entry is actually cited inline (no orphans)
  * display numbers are contiguous from 1

--renumber rewrites display numbers in order of first appearance and rebuilds the
References list to match, which is the only safe way to close a gap left by editing.
"""
import os
import re, sys
from pathlib import Path

VAULT = Path(os.environ.get("VAULT_ROOT", "."))
INLINE = re.compile(r'\[\[(Notes/NotebookLM/[^/]+/Sources/([^#\]]+))#Passage (\d+)\|(\d+)\]\]')
REFLINE = re.compile(r'^(\d+)\. \[([^\]]+) — Passage (\d+)\]\(<(Notes/NotebookLM/[^>]+)>\)$', re.M)


def main():
    path = Path(sys.argv[1])
    renumber = "--renumber" in sys.argv
    text = path.read_text()
    body, sep, refs_block = text.partition("\n## References\n")
    if not sep:
        sys.exit("no ## References section")

    inline = INLINE.findall(body)
    ok = True

    # 1. anchors exist
    for rel_path, title, passage, disp in inline:
        src = VAULT / f"{rel_path}.md"
        if not src.exists():
            print(f"  DANGLING source: {title}"); ok = False; continue
        if f"### Passage {passage}\n" not in src.read_text():
            print(f"  DANGLING anchor: {title} #Passage {passage} (display {disp})"); ok = False

    # 2/3. inline vs references
    declared = {int(n): (t, int(p)) for n, t, p, _ in REFLINE.findall(refs_block)}
    used = {}
    order = []
    slug = inline[0][0].split("/")[2] if inline else ""
    for _, title, passage, disp in inline:
        d = int(disp)
        if d in used and used[d] != (title, int(passage)):
            print(f"  COLLISION: display {d} used for two different passages"); ok = False
        used[d] = (title, int(passage))
        if d not in order:
            order.append(d)
    for d, v in sorted(used.items()):
        if d not in declared:
            print(f"  MISSING reference entry for display {d}"); ok = False
        elif declared[d] != v:
            print(f"  MISMATCH display {d}: inline {v} vs reference {declared[d]}"); ok = False
    for d in sorted(declared):
        if d not in used:
            print(f"  ORPHAN reference {d} (listed, never cited)"); ok = False

    gaps = [n for n in range(1, max(used) + 1) if n not in used] if used else []
    if gaps:
        print(f"  GAPS in display numbering: {gaps}")

    print(f"{path.name}: {len(inline)} inline citations, {len(used)} distinct, "
          f"{len(declared)} references — {'OK' if ok and not gaps else 'PROBLEMS'}")

    if renumber and used:
        remap = {old: i + 1 for i, old in enumerate(order)}
        new_body = INLINE.sub(
            lambda m: f"[[{m.group(1)}#Passage {m.group(3)}|{remap[int(m.group(4))]}]]", body)
        lines = []
        for old in order:
            title, passage = used[old]
            rel = f"Notes/NotebookLM/{slug}/Sources/{title}.md#Passage {passage}"
            lines.append(f"{remap[old]}. [{title} — Passage {passage}](<{rel}>)")
        tail = refs_block.split("\n\n", 1)
        rest = "\n\n" + tail[1] if len(tail) > 1 else "\n"
        path.write_text(new_body + sep + "\n".join(lines) + rest)
        print(f"  renumbered {len(order)} references")


if __name__ == "__main__":
    main()
