#!/usr/bin/env python3
"""Audit passage anchors: is the anchored passage the BEST match for the quote?

Usage: CORPUS_SOURCE=<path to the source .md> audit_anchors.py "<glob of notes>" [-v]

For each **"quote"** followed by (…#Passage N|k …), score the quote against every
passage in the source by 4-gram word-shingle overlap, then compare:
  BEST  - an anchored passage is the top scorer
  NEAR  - an anchored passage scores >=0.6 of the top score
  WRONG - top scorer is some other passage, by a clear margin
  WEAK  - nothing scores well (quote is a paraphrase / too short) -> untestable
"""
import os
import re, sys, glob
from pathlib import Path

SRC = Path(os.environ["CORPUS_SOURCE"])

def norm(s):
    s = (s or '').replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    s = re.sub(r'\[[^\]]*\]', ' ', s)          # drop NotebookLM's [bracketed] insertions
    s = re.sub(r'[^a-z0-9\' ]+', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def shingles(s, n=4):
    w = norm(s).split()
    return {tuple(w[i:i+n]) for i in range(len(w)-n+1)}

passages = {}
for m in re.finditer(r'### Passage (\d+)\n\n(.*?)(?=\n### Passage |\Z)', SRC.read_text(), re.DOTALL):
    passages[int(m.group(1))] = shingles(m.group(2))

def audit(path):
    text = Path(path).read_text()
    counts = {"BEST":0, "NEAR":0, "WRONG":0, "WEAK":0}
    wrongs = []
    for m in re.finditer(r'\*\*"(.{40,400}?)"\*\*\s*\(((?:\s*\[\[[^\]]*?\]\],?)+)\s*\)', text, re.DOTALL):
        q = shingles(m.group(1))
        nums = [int(x) for x in re.findall(r'#Passage (\d+)\|', m.group(2))]
        if not nums or len(q) < 4:
            continue
        scores = {p: len(q & sh)/len(q) for p, sh in passages.items()}
        top_p, top_s = max(scores.items(), key=lambda kv: kv[1])
        if top_s < 0.30:
            counts["WEAK"] += 1; continue
        mine = max(scores.get(n, 0) for n in nums)
        if mine >= top_s - 1e-9:            counts["BEST"] += 1
        elif mine >= 0.6*top_s:             counts["NEAR"] += 1
        else:
            counts["WRONG"] += 1
            wrongs.append((nums, top_p, round(mine,2), round(top_s,2), norm(m.group(1))[:60]))
    return counts, wrongs

TOT = {"BEST":0,"NEAR":0,"WRONG":0,"WEAK":0}
for path in sorted(glob.glob(sys.argv[1])):
    c, w = audit(path)
    for k in TOT: TOT[k] += c[k]
    flag = "  <<<" if c["WRONG"] else ""
    print(f"{Path(path).stem[11:58]:50} best={c['BEST']:3} near={c['NEAR']:3} WRONG={c['WRONG']:3} weak={c['WEAK']:3}{flag}")
    if len(sys.argv) > 2:
        for nums, top, mine, ts, q in w[:6]:
            print(f"       anchored {nums} ({mine}) but P{top} scores {ts} :: {q}")
print(f"\n{'TOTAL':50} best={TOT['BEST']} near={TOT['NEAR']} WRONG={TOT['WRONG']} weak={TOT['WEAK']}")
