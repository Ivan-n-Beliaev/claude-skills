---
name: corpus
description: Turn a NotebookLM notebook (a book, a paper set, any curated sources) into a linked corpus of atomic concept notes in the vault, with passage-anchored citations back into the sources. Use when the user says "corpus", "build a corpus", "map out this book", "turn this notebook into notes", "/corpus continue", or points at a NotebookLM notebook the user wants in their vault.
argument-hint: [new <notebook> | continue [domain] | status]
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
---

# Corpus — NotebookLM notebook → vault knowledge base

> **Sources.** Use only sources you have the right to read and process. Keep the extracted `Sources/` text private and do not redistribute it. Notes you publish should carry short quotations only. The failure rates quoted below were observed on my own runs in 2026 and are not general claims about NotebookLM.

Builds a corpus of atomic evergreen notes, each synthesized in your own voice, every claim citing a passage anchor in the source text.

**The economics that shape this skill:** In my runs NotebookLM handled retrieval and quoting at no extra cost, and Claude tokens were the constraint. So every phase front-loads NotebookLM (research, structuring, quoting) and reserves Claude for synthesis (compression, voice, cross-linking). Never ask Claude to do research NotebookLM can do.

## Commands

| Command | Action |
|---|---|
| `/corpus new <notebook name or id>` | Start a new corpus. Runs Phases 0–3, stops for template approval. |
| `/corpus continue [domain]` | Resume an in-progress corpus. **This is the normal command.** |
| `/corpus status [domain]` | Report progress without building anything. |

`/corpus continue` with no domain: if exactly one `_BUILD_PLAN.md` has unbuilt notes, use it; if several, list them and ask.

## Resume protocol (read this first on `/corpus continue`)

1. `ls Notes/Concepts/*/_BUILD_PLAN.md` — each is a resumable corpus.
2. **Read the whole `_BUILD_PLAN.md`.** It holds the locked template, notebook ID, build list with checkboxes, and every gotcha learned on that corpus. It is authoritative over this skill where they differ — it carries domain-specific decisions the user already approved.
3. Read the template note it names. Match it exactly.
4. Take the next unchecked batch from the build list. **Do not re-ask the user to approve the template** — that gate was passed when the plan was written.
5. Build the batch (Phase 4 loop). Tick the boxes. Stop.

## Session budgeting

One session = **one batch of 8–10 notes**, then stop and report. Do not try to finish a 50-note corpus in one session; it exhausts the context window and quality degrades in the back half.

Within a session the order is always: **all queries first (free, batched, backgrounded), then synthesis one note at a time.** Never interleave — a failed query mid-synthesis wastes the expensive half.

Bank the free work: even if synthesis stops early, resolve every completed query into its QA note. Those persist in the vault; scratchpad JSON does not survive the session.

## Phase 0 — Protect the corpus from link rewriters (BLOCKING, before writing any note)

If your vault runs any background job or plugin that rewrites wikilinks, it **will strip `|display` and `#anchor` from every citation** in a folder it is allowed to touch. Exclude both the concept folder and the whole of `Notes/NotebookLM/` from it, `Sources/` as well as `QA/`.

Leaving `Sources/` exposed is the worse failure: a link rewriter treats extracted source text as ordinary prose and rewrites the author's own words into wikilinks pointing back at the corpus notes. One audit found hundreds of injected links in the source files. `Sources/` is the anchor target of every citation in the corpus, so it must never change.

**The corpus's own notes are what arm this bug.** Every new concept note gives a link rewriter a new term to match inside the source text. Verify the exclusion before each batch, not just at Phase 0.

**If you ever move or rename a corpus folder, update the exclusion in the same commit.**

## Phase 1 — Import sources

```bash
nlm notebook list                     # find the notebook
nlm source list <notebook-id> --json > /tmp/<slug>-sources.json
mkdir -p "Notes/NotebookLM/<slug>"/{Sources,QA}
```

Then create one source file per source under `Sources/`. The `import_sources.py` script from the notebooklm-skill plugin does this and is not included here.

**Shorten long source titles before anything else.** NotebookLM titles are often 120-character upload filenames, and that string lands in every citation across the whole corpus. Rename the file AND patch the title in the sources JSON so `corpus_resolve.py` still resolves to it:

```bash
mv "Notes/NotebookLM/<slug>/Sources/<long>.md" "Notes/NotebookLM/<slug>/Sources/<Short Name>.pdf.md"
python3 -c "import json;p='/tmp/<slug>-sources.json';d=json.load(open(p));d['sources'][0]['title']='<Short Name>.pdf';json.dump(d,open(p,'w'),indent=2)"
```

**Then archive the patched JSON into the corpus itself** — `/tmp` does not survive between sessions, and it was already found wiped once:

```bash
cp /tmp/<slug>-sources.json "Notes/NotebookLM/<slug>/raw/sources.json"
```

On resume, restore from that copy first and only regenerate from the CLI if it is missing. Record both the archive path and the patched regeneration command in `_BUILD_PLAN.md` — if `/tmp` is wiped and someone regenerates without re-patching, the pipeline creates a second source file and orphans every existing passage anchor.

If `nlm source describe` returns empty (happens on some PDFs), fall back to `nlm notebook describe <id>` and label it as notebook-level in the `## Source Guide` section.

## Phase 2 — Inventory (all NotebookLM, near-zero Claude cost)

Three queries, resolved into QA notes. These produce the build list, so **no concept in the corpus is ever invented by Claude**:

1. **Vocabulary** — "What are the core concepts, symbols, and technical terms this work develops? Inventory them with a one-line gloss and a direct quote where each is defined."
2. **Completeness push** — paste the list back: "What did that list OMIT? Be exhaustive." (On one single-book run this took 23 terms → 74.)
3. **Structure** — "What is this work's own organizing structure? Name its parts and the argument each carries, quoting its section titles."

Add a **sequence** query for anything with a narrative or procedural spine (a commentary, a history, a method): "Walk the sequence it treats, in its own order. For each: what it is, which section treats it, and what operation is happening."

Then collapse the raw inventory into a build list. **Terms that only exist as a pair get one note, not two.** Poles that carry independent weight get their own note. Give absorbed terms `aliases:` so the absorbed name still resolves.

## Phase 3 — Lock the template (STOP for the user)

Build **one** note first — the corpus's root term, the one everything else relates to. Then stop and show the user.

This gate is not optional and not a formality. Every domain needs different sections, and finding that out on note 40 is expensive. Once it is approved, the template is locked and Phases 4–6 run without further approval gates.

Structure, section order, citation format, and the unanchored-references rule: **[reference.md](reference.md)**. Read it before writing the first note.

## Phase 4 — Batch build

```bash
export SK="<path to this skill folder>"; export VAULT_ROOT="<path to your vault>"
# 1. ALL queries first, at most two at a time, with retry
for c in <concepts>; do
  "$SK/scripts/corpus-ask.sh" <notebook-id> "$c.json" "Provide a deep treatment of <CONCEPT> as developed in this work. Cover: <3-5 concept-specific hooks>. Quote directly wherever the term is defined or its function stated."
done

# 2. Then resolve, SEQUENTIALLY (passage numbering accumulates — parallel runs race)
for c in <concepts>; do
  python3 "$SK/scripts/corpus_resolve.py" --qa "$c.json" --sources /tmp/<slug>-sources.json \
    --slug <slug> --title "<Concept> — Deep Treatment" --vault "$VAULT_ROOT"
done

# 3. Then synthesize one note at a time from the resolved QA notes
```

**Write concept-specific hooks.** Generic prompts return generic answers. Pull the hooks from the Phase 2 vocabulary QA notes, which already hold each term's gloss and definition.

**Synthesis is compression, not transcription.** The QA note is raw material. The concept note is terse, structured, in your own voice, cross-linked to siblings. If the note reads like a Q&A dump, it failed.

**Keep the QA note's reference numbering.** Do not renumber by order of appearance. Concept-note ref `N` must stay QA-note citation `N` — this is the property that lets a damaged anchor be traced back to its true passage, and it is the only reason an earlier corpus was recoverable after its citations were mangled (see Gotcha 10). Cite broadly enough that the numbering stays dense and no reference sits in the list uncited.

## Phase 5 — Sequence notes (when the work has a spine)

A subfolder (`Chronology/`, `Protocol/`) with one note per step, named for the step rather than the chapter. Structure: what happens → the author's reading (cited) → which concepts are in play (wikilinks into Phase 4) → what the operation is.

This is the layer that makes a corpus usable while actually reading the source, rather than only searchable afterward.

## Phase 6 — Bridge notes (DIFFERENT RULES — read carefully)

A corpus about X often exists because the user wants X applied to their own work. **That application is almost never in the source.** Bridge notes therefore run under a hard constraint — every sentence is exactly one of:

1. **The source's claim** → passage anchor.
2. **A named source's claim** → cite the note holding their actual words.
3. **The user's or Claude's extension** → `[unverified — inference]`, no exceptions.

Build these **in dialogue with the user**, not autonomously. The user has the domain judgment and NotebookLM has the source. Claude's job is holding the three honest, not authoring the connection. The temptation to make the bridge land harder than the evidence supports is exactly the failure mode.

## Phase 7 — Wire it in

- `Notes/MOCs/<Corpus Name>.md` — sectioned index, provenance paragraph, `## Recent Context` changelog.
- Cross-link to adjacent existing domains.

## Verification (run after every batch)

```bash
cd "$VAULT_ROOT"
for f in "Notes/Concepts/<Domain>"/*.md; do
  printf "%-30s inline:%-4s corrupt:%s\n" "$(basename "$f" .md)" \
    "$(grep -o 'Passage [0-9]*|[0-9]*\]\]' "$f" | wc -l | tr -d ' ')" \
    "$(grep -o '\[\[\[\|\]\]\]\|Sources/\[\[' "$f" | wc -l | tr -d ' ')"
done
```

`corrupt` must be 0 everywhere. Those three patterns are the exact damage a link rewriter causes.

**Checksum the source files** (`md5 -q Notes/NotebookLM/*/Sources/*.md`) before and after any vault-wide job. The concept-note check alone passes while source text is being silently rewritten.

Note: `grep -c` exits 1 when the count is 0, so a corruption check that passes will look like a "failed" command in a chained shell call. Use `grep -o | wc -l` as above.

## Gotchas

1. **CLI output can carry a non-JSON line before the JSON.** Strip to the first `{` with `sed -n '/^{/,$p'`. `corpus-ask.sh` handles it.
2. **Chat requests time out** (~1 in 8 observed) returning `{"error": true, ...}` with no `answer` key. `corpus-ask.sh` detects and retries; anything else you write must too.
3. **Start each query in a new conversation** (`--new-conversation`), or earlier answers leak into later ones.
4. **This skill started on the notebooklm-skill plugin's scripts.** `scripts/corpus_resolve.py` now does extraction and resolution itself, so only `import_sources.py` is still needed from the plugin.
5. **In my runs about 30% of citations returned `cited_text: None`.** Expected, not a bug. Handle per the unanchored-references rule in [reference.md](reference.md).
6. **Never resolve in parallel.** Passage numbering accumulates in the source file.
7. **Never put a `[[X|N]]` wikilink inside a markdown table cell** — `|` is the column delimiter. Put citations on a line below the table.
8. **Don't hand-edit corpus notes in Obsidian.** "Use shortest path possible" normalizes wikilinks on save and strips anchors. Commentary goes in separate notes linking back.
9. **Multi-source notebooks:** the same filename can exist in two notebooks with different `source_id`s. Always write full paths in citations.
10. **The corpus folder path lives in more than one place, and the copies drift.** Any exclusion rule and the corpus's own `_BUILD_PLAN.md` both hold it. After one folder move the rule kept the old path and a link rewriter stripped citation anchors from many notes without any error. Nothing errored. After any move, grep for the old path in the same commit.
11. **Audit an inherited corpus before extending it.** Inline-vs-reference count drift is the cheap tell: a note with 6 inline citations and 15 reference entries has ~9 stripped anchors. The three-pattern corruption check does **not** catch this class — a stripped citation is still valid markdown. Use the fuller audit (dangling anchors, orphan refs, stripped `/Sources/` wikilinks lacking `#Passage`).
12. **In my runs NotebookLM sometimes mislabelled a chapter or section reference while quoting accurately.** The quote and passage anchor can be correct while the stated chapter is wrong. Verify section references before they enter a concept note; flag rather than silently correct.

13. **In my runs NotebookLM also anchored accurate quotes to the wrong passage.** Distinct from 12 and more common. On one run it anchored the same quote to an unrelated footnote in **three separate answers**. When the anchored passage plainly does not contain the claim, do not propagate it: keep the reference entry, leave it uncited inline, and record it in a `> [!warning] Citation hygiene` callout. A wrong anchor is worse than a missing one.

14. **The copy of the plugin's `resolve_citations.py` I was using, with my own patches, mapped `[N]` to the Nth unique non-null chunk, not to `citation_number`. `corpus_resolve.py` uses `citation_number`.** The answer's `[N]` markers *are* NotebookLM's `citation_number` values. Because ~30% of refs come back with `cited_text: None` and were skipped when building the ordered list, every citation after the first null in an answer landed on a neighbouring passage — silently, since the resulting links are structurally valid and point at real passages. It went unnoticed because every existing check (the three corruption patterns, inline-vs-reference count drift) passes on a confidently wrong anchor.

    **Verify the mapping empirically on any corpus you inherit.** Find quotes traceable to exactly one reference, then score each quote against every passage by word-shingle overlap and check that the anchored passage is the top match. On one corpus that gave 20/21 correct after the fix versus 9/29 before it — an unmissable split. Any corpus built with the old mapping carries shifted anchors and needs remediation.

    Remediation is not mechanical: the raw query JSONs live in `/tmp` and do not survive, so it means re-querying (free), re-resolving, and re-mapping each concept note against a freshly numbered answer. **Never let the raw JSONs be the only copy** — write them to the scratchpad and keep them until the batch is verified.

15. **When an anchored passage plainly cannot contain the claim, open the source and read it.** One `awk '/^### Passage N$/,/^### Passage N+1$/'` on the source file settles it in seconds, and it is the only check that catches a confidently wrong anchor — the three corruption patterns, count drift, and the shingle-overlap audit all pass on one. On one corpus this caught a **fourth** hit on the same wrong passage two batches after the first three were recorded. Suspect any anchor that repeats across unrelated answers.

16. **The QA note's bibliography numbers and its leftover bare markers collide.** The resolver renumbers anchored citations compactly (1..N in order of first appearance in the answer), but unresolvable markers stay as NotebookLM's *original* numbers. So one QA note can carry an anchored `3` and a bare `[3]` that mean different references. In the concept note, keep the bibliography numbers unchanged (the invariant) and number the unanchored entries from N+1, labelling each with its origin: `- [14] *(QA note bare marker [3])* — …`.

17. **The CLI is `nlm`** (the unofficial notebooklm-mcp-cli). Query with `nlm notebook query <id> "<q>" --json --new-conversation -t 240`. Check NotebookLM's terms before using an unofficial client.

18. **Extraction and resolution run in one step, in `scripts/corpus_resolve.py`.** Earlier versions called two plugin scripts that I had patched locally; a reinstall replaced my patches, so this skill now does the step itself.

19. **Run `scripts/audit_note.py` on every concept note before ticking its box.** It cross-checks each inline anchor against the References list, and catches the one failure that every other check passes on: an anchor written with the *display* number in place of the *passage* number. On the first note of one corpus that was 33 of 39 citations, each a structurally valid link to a real passage that said something the author never said there. `--renumber` closes a gap left by editing.

20. **A quoted phrase is not evidence that the source contains it.** In my runs NotebookLM put its own paraphrases inside quotation marks (on one run, a quoted two-word phrase that appears in none of the five sources). Grep any distinctive quoted phrase against the raw source text before it enters a note. Sources are hard-wrapped, so a `grep -o ".\{200\}<phrase>.\{200\}"` context window fails silently across a newline; flatten with `tr '\n' ' ' | tr -s ' '` first, or a real quote will look fabricated.

21. **Strip NotebookLM's closing offer.** In my runs answers often ended "Would you like me to turn this into a PDF? 📄". `corpus_resolve.py` removes it; anything else reading the raw JSON must too, or it lands in the QA note reading as if the author said it.

## Self-annealing

Any error this skill hits gets fixed **and** patched back into this file or its scripts so it cannot recur. Gotchas 2 and 4 above were both learned from real failures. Add to the list rather than fixing silently.

## Resources

- Note template, section order, citation format, unanchored rule, `_BUILD_PLAN.md` schema: [reference.md](reference.md)
