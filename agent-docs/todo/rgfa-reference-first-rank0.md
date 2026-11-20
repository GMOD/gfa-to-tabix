---
name: rgfa-reference-first-rank0
description: bandage-core takes an rGFA's reference from the first rank-0 segment it meets, and paint order, colours and figure rows follow the file's order; both should come from a canonical order set once in the reader.
metadata:
  repo: bandage-core
---

# Reference and order follow the file's order

- `taggedReferencePath` (`src/pathAnchoring.ts`, around line 241) names the
  reference by the first node with `stable.rank === 0`, so a graph whose
  rank-0 segments name two sequences draws against whichever comes first
- Order leaks found in the 2026-11-16 order review, not rechecked since:
  - paint order follows `graph.edges`
  - an off-reference node takes its colour from the first placed neighbour
    in file order (`referenceSpan.ts`)
  - figure data rows carry the file's edge index and S order
  - the anchored and sample-row layouts break a tie by order
    (`projectAlleles.ts`)
  - the tube map's drawing lists differ with order
- The fix is to put nodes and links in canonical order once in the reader,
  remapping `departures.steps`. It changes paint order of existing drawings,
  so it needs BEFORE/AFTER pairs. Layout order independence itself landed
  (be5550e, ac39a50, 34a39ba)
