---
name: lanes-ribbons-against-reference
description: A lanes track fed from a walk file draws each lane's ribbons against its neighbour because the plugin's adapter declares a capability that turns the display's against-the-anchor mode off; its records against the reference come from a chain search and not from the placement the walk file stores. Three reviews on 2026-11-22 put ribbons against the reference first.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# Walk-fed lanes read against the reference

## What is true

- **The display has the mode.** `MultiWaySyntenyDisplay/sourceShape.ts`,
  `rowsReadAgainstAnchor`, draws every lane against the anchor, and the
  PAF-fed track uses it; that is its "vs hg38" badge.
- **The walk adapter opts out.** `WalkTabixSyntenyAdapter/index.ts` declares
  `lanePairsOnAnchor`, so the display fetches neighbour pairs and drops any
  pair that holds the anchor. No track or display setting overrides it.
- **The records against the reference are already fetched,** for the first
  fetch, the headers and the top lane's band (`anchorFeatures`).
- **They are not a lookup.** `anchorAligner` in `walkLanes.ts` runs
  gbz-base's weighted longest common subsequence of the haplotype's steps
  against the reference fragment, and pair chaining where enough is turned.
  It keeps one pass and loses HG00128's reversed 29 kb at amylase.
- **The walk file stores the placement.** graph-walks gives every step of a
  fragment its position on the reference (`refStarts`, `against`). Nothing
  in the plugin reads them.
- The paper session asked for lanes against hg38 for Figure 5 on 2026-11-22.

## What to do

- Read each lane's records against the reference from the stored placement,
  with no chain search. Gate it on the diagonals of the PAF
  `gfa_to_pairwise_paf.py` writes from the same GFA, and on pictures, a pggb
  graph among them, where the reference itself steps nodes twice and the
  writer's placement rule decides the pass.
- Make ribbons against the reference what a walk-fed track draws, with
  neighbour against neighbour a setting if it is kept at all:
  `todo/lane-aligner-leftover-stretches.md`, "Reviews".
- This takes gbz-base's `lcs` and `pairAlignment` out of the lanes against
  the reference.
