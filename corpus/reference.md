# Corpus — note template, citation format, build-plan schema

Loaded on demand by [SKILL.md](SKILL.md). Read before writing the first note of a corpus.

## The three layers

| Layer | Path | Who writes it | Editable by hand |
|---|---|---|---|
| Raw | `Notes/NotebookLM/<slug>/{Sources,QA}/` | scripts only | no — auto-managed |
| Polished | `Notes/Concepts/<Domain>/` | Claude, synthesized | no — machine-generated |
| Hub | `Notes/MOCs/<Corpus Name>.md` | Claude, then the user | yes |

Commentary and disagreement go in **new** notes that link back, never as edits to a corpus note.

## Concept note template

```yaml
---
type: note
status: active
date: YYYY-MM-DD
tags: [<domain tags>]
keywords: [<searchable terms>]
aliases: [<every term this note absorbs>]
related:
  - "[[Sibling]]"          # pre-wire to notes that don't exist yet; they resolve as the batch lands
ingested: true
---
```

Section order:

1. `# Title`
2. `## Definition` — crisp, 2–3 citations. State what the term is **not**, when the modern reading misleads.
3. `## Why It Is the Root Term` / `## Why It Matters` — placement in the system.
4. **Pair section** — for polar terms: the complement and why they are inseparable.
5. `## How It Operates Across Scales` — table, where the source has a scale structure.
6. `## Where It Appears in <Source Spine>` — bulleted, each linking to a Phase 5 note.
7. `## Contrast with the Modern Reading` — table. **Only where the source actually polemicizes.** Cut it where it would be padding; a table that restates the definition sideways is noise.
8. `## Related Concepts` — wikilinks, each with a one-line gloss saying *why* it relates.
9. `## Sources` — work, edition, part.
10. `---`
11. `## References` + unanchored block.

### Voice

Terse, operator-focused, structured. Short paragraphs. A one-line paragraph landing the point is good.

The test for a finished note: **does it say something the QA note didn't?** Synthesis means finding the load-bearing claim and putting it first, naming what the concept rules out, and connecting it to siblings. Transcription with better headings is a failed note.

Do not invent examples, applications, or implications the source doesn't make. If a connection is yours, mark it `[unverified — inference]`.

## Citation format (load-bearing — do not improvise)

Inline, in body — full path, passage anchor, cite number as display text, wrapped in parens:
```
... claim ([[Notes/NotebookLM/<slug>/Sources/<Short Name>.pdf#Passage 52|1]]).
```

References section — plain markdown link, angle-bracketed, **`.md` present**:
```
1. [<Short> — Passage 52](<Notes/NotebookLM/<slug>/Sources/<Short Name>.pdf.md#Passage 52>)
```

Note the asymmetry: the inline wikilink has **no** `.md`; the reference link **does**. Obsidian wikilinks omit the extension; markdown links need the real path.

Cite numbers in the body must match the References list, and passage anchors must match real `### Passage N` headings in the source file. The resolver's bibliography in the QA note gives you both — copy from it, don't derive them.

**Never** put a `[[X|N]]` wikilink inside a markdown table cell. Put the citations on a line below the table:

```markdown
| Scale | What it is here |
| --- | --- |
| Large | ... |

Large row: ([[...#Passage 59|12]]). Small row: ([[...#Passage 57|9]]).
```

## The unanchored-references rule

In my runs about 30% of NotebookLM's citations came back with `cited_text: None` (1-char spans). The resolver leaves those as bare `[8]`, `[9]`. The quoted text is still verbatim from the source — only the location is unpinned.

**Do not drop them, and do not present them as anchored.** Keep the quote, keep the bare number, and list them in a labelled block:

```markdown
**Unanchored references** — quoted verbatim from the book by NotebookLM, but the citation
returned no resolvable text span, so no passage anchor exists. Quotes are reliable; the
location is not yet pinned. Full context: [[Notes/NotebookLM/<slug>/QA/<date> <X> — Deep Treatment]].

- [8] <short gloss of the claim>
- [9]–[11] <short gloss>
```

When every citation resolves, say so instead: `*All citations in this note resolved to passage anchors.*`

This is the honesty discipline made visible. A reader can tell at a glance which claims are pinned to a location and which are only pinned to a quote.

## `_BUILD_PLAN.md` schema

Lives at `Notes/Concepts/<Domain>/_BUILD_PLAN.md`, `type: handoff`. **This file is the resume mechanism** — it must let a cold agent with zero context continue without asking the user anything.

Required sections:

1. **What is being built** — the work, the notebook, the three layers.
2. **Key IDs and paths** — table: notebook ID, slug, source file, sources JSON, patched-scripts path. Include the *patched* sources-JSON regeneration command.
3. **Status** — phases with ✅/⏳.
4. **The work's own structure** — from the Phase 2 structure query.
5. **Build list** — grouped, **with checkboxes**, so progress is machine-readable:
   ```markdown
   ### Batch 3 — <part of the source>
   - [x] <Concept A>
   - [ ] <Concept B>
   - [ ] <Concept C>
   ```
6. **Sequence list** for Phase 5.
7. **Workflow per note** — the four steps with real commands, real IDs.
8. **Locked template** — points at the approved note, states any domain-specific deviation.
9. **Phase 6 bridge rules** — the three-source constraint, if the corpus has a bridge layer.
10. **Gotchas** — everything learned on *this* corpus.
11. **Verification** and **Done means**.

Update the checkboxes at the end of every batch. That is what makes `/corpus continue` cheap.

## Batch composition

Group by the source's own structure, not alphabetically. Notes in one batch should be the ones that cite each other — you write the shared distinction once and cross-reference it, instead of re-deriving it in four separate sessions.

Build polar pairs adjacent for the same reason.

8–10 notes per session. Below that the query-batching overhead dominates; above it, quality degrades in the back half.

## Recovering mangled citations

If a corpus loses its citations (a link rewriter, a bad edit), the damage has three shapes and only two of them are mechanically fixable:

| Shape | Example | Fixable |
|---|---|---|
| A — wikilink injected into a reference link target | `(<.../Sources/[[Name.pdf]].md#Passage 7>)` | yes, deterministic: strip `[[`/`]]` inside `(<...>)` |
| B — nested brackets | `[[[X]] [[X]]]]` | yes, from sentence context |
| C — flattened inline citation | `([[Name.pdf]])`, anchor and cite number gone | only by re-verification |

**The References section is the recovery mechanism.** It is a plain markdown list, so the mangler leaves it structurally intact even when it corrupts the paths inside. That list enumerates exactly which passages the note drew on — which turns Type C from an open search over hundreds of passages into a bounded one over the 7–22 that note actually cited.

So the recovery method is: for each flattened citation, take the note's own References list as the candidate set, read those passages in the source file, and assign the one that **contains the specific claim** — not merely the same topic. Restore by reusing the existing reference number; never renumber or append entries.

Leave anything you cannot verify flattened. A wrong citation is far worse than an imprecise one, and a flattened link still resolves to the source — it just lands on the file instead of the passage. Notes with zero unused reference slots are usually unrecoverable: the original pointed at a passage the note never listed.

Mark what you reconstruct:
```markdown
‡ Citations 6, 9, 11 were reconstructed <date> after wikilink corruption: the passage text
was read and confirmed to support the claim. All other citations are original
NotebookLM-grounded anchors.
```
The rule: a Claude-verified anchor and a NotebookLM-grounded one have different provenance and the corpus records the difference.

**Design consequence:** always write the References section as plain markdown links, never as wikilinks. It is the corpus's redundant copy of its own citation graph, and its survivability is why recovery is possible at all.

## Domain adaptation

Two corpora built with this skill differed in ways worth anticipating:

| | Multi-source corpus | Single-book corpus |
|---|---|---|
| Sources | 18 PDFs, 3 notebooks | 1 PDF |
| Vocabulary shape | independent concepts | polar pairs |
| Spine | none | a narrative sequence |
| Citation collisions | yes — same filename in 2 notebooks | none |
| Special failure | image-only PDF, `cited_text` all null | ~30% null, chat timeouts |

**Image-only PDF fallback:** if `cited_text` is null for *every* reference, the PDF has no text layer. The standard pipeline cannot work. Instead: ask NotebookLM for rich quoted material per concept, hand-build the `## Cited Passages` block in the source file from those verbatim quotes, and cite those manually-built anchors normally. Note the fallback in `_BUILD_PLAN.md`.
