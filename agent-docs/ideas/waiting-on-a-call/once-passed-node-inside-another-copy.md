---
name: once-passed-node-inside-another-copy
description: Of a file with revisited nodes the format promises nothing about once-passed nodes, and pggb chrY's node at 9,394,014 shows the writer's rule is not plainly right there - kept on the reference, each of seven walks reads as an 88.8 kb skip; filed off it, the node's tile lacks those lines. No file says which the writer did. Decided when a pggb walk file is to be hosted.
metadata:
  repo: gfa-to-tabix, graph-walks
---

# A once-passed node walked inside another copy

## What the format promises

- That no route interior holds a node the reference passes once, only of
  a file that states `revisited:i:0`
  ([What a reader relies on](../../../docs/walks-format.md#what-a-reader-relies-on),
  [ADR 0016](../../../docs/adr/0016-format-8-is-frozen.md#the-ruling-on-c27)).
  Of a file with revisited nodes it promises nothing: a window's rows can
  lack a line that steps a once-passed reference node in it, and a reader
  cannot tell from the file whether they do
- gfa-to-tabix keeps the rule on every file it writes, pggb chrY among
  them ([whole-file runs](../../../docs/walks-container/accept-5.0.0/whole-file/README.md),
  [What the writer guarantees](../../../docs/walks-writer.md#what-the-writer-guarantees)),
  but the header names no writer, so a reader of a file with revisited
  nodes that says "N of M haplotypes step this node" of a once-passed
  node says it on the writer's word

## Where the rule is not plainly right

- On pggb chrY a 1 bp node the reference passes once, at 9,394,014
  (node 408455), is walked by seven of eight haplotypes inside the TSPY
  copy near 9,482,842
  ([the drawing check's rows](../../../docs/walks-container/pggbY/once-passed-node.tsv),
  on the file [pggbY](../../../docs/walks-container/pggbY/notes.md)
  builds)
- Kept on the reference, as this writer keeps it, each of those walks
  reads as an 88.8 kb skip, in the graph and the rows alike. Filed off
  the reference with its neighbours, the node's own tile would lack the
  seven lines
- No file states which the writer did for a given node, and no pggb file
  is hosted
- The graph holds no fact that picks the copy. A later tag could say that
  a once-passed node's place is borrowed where its neighbours lie
  elsewhere

## What it waits on

A call, when a pggb walk file is to be hosted. It sits beside the
placement question (`pggb-placement-rule.md`), and the place-by-chain
proposal, which drops once-passed anchors that lie off a contig's chain,
bears on it (`../../handoffs/2026-11-22-pggb-place-by-chain.md`).
