---
name: complete-adjacency-for-a-bubble-layer
description: A collapsible bubble and chain layer for zoomed-out views, kept beside the walk file rather than as its layout. A walk-file cut lists only the links its kept walks take, so verifying bubbles on the loaded subgraph needs a writer-built links unit, nodes tag or side file first; each is a legal addition and no view has been shown to need one. A blind design that read pangyplot says what a base format must give.
metadata:
  repo: gfa-to-tabix
---

# Complete adjacency for a bubble layer

## The gap

- A walk-file cut lists the links its kept walks take and no other, so it
  cannot give a loaded node's complete adjacency, and no reader rule
  recovers it. In a test graph cut with every haplotype loaded, a node
  reads as a clean insertion bubble while the GFA holds five more links at
  loaded nodes: one no path walks, one only a left-out line walks, and
  three shown paths walk from pieces filed in another tile, the
  reference's own `2+>3+` among them, with no trace in the window
  ([g4.gfa](../../../docs/walks-container/freeze-review/g4/g4.gfa),
  [its cuts](../../../docs/walks-container/freeze-review/g4/cuts.txt))
- The node and link index holds every link of a path-visited node but is
  not built for whole-genome graphs
- So a bubble or chain layer that verifies superbubbles on the loaded
  subgraph needs a writer-built addition first: a tag on `nodes` rows, a
  `links` unit kind, or a side file. Each is legal under the additions
  rule ([Later additions](../../../docs/walks-format.md#later-additions))
  and none changes a row. A site table built from the walks alone is exact
  today
- A unit kind in a table carries its sequence and integer `start end`, so
  a later unit about no sequence has to be a separate file. A kind with a
  unit per tile grows the table every reader fetches at open: with a
  links, a counts and a sites unit per tile added to a chr22 build, it grew
  from 46,338 to 84,628 bytes
  ([the format study](../../../docs/walks-container/format-study/writeup.txt))
- Links that only left-out lines walk are a separate limit, in
  `../collections/what-a-format-8-reader-cannot-say.md`
- ADR 0016 weighed a `links` unit and left it for later: no reader's view
  was shown to change
  ([The candidates](../../../docs/adr/0016-format-8-is-frozen.md#the-candidates)).
  A side file needs a pairing rule first (`side-file-pairing-rule.md`)

## The blind design that read pangyplot

`~/src/walks8-evidence/22a29087/blind-design-bubbles/DESIGN.txt`, written
during the format 8 release of 2026-11-14 from the requirement and
pangyplot's source alone, without our spec. Its reading of pangyplot cites file and line, and nobody has
checked those claims.

- **Its decision:** do not build the file layout around the bubble
  hierarchy; keep it as a later layer. One bubble can span megabases,
  repeats and tangles yield no bubbles, and bubble decompositions differ
  between tools
- **Two uses it keeps:** zoomed in, collapse-and-open computed by the
  reader on the loaded subgraph, exact if every loaded node's links are
  given; zoomed out, an optional sites layer of top-level bubbles above a
  size, each with its reference interval and a per-walk class and length
  table
- **What it says a base format needs now:** stable node ids, every link of
  a loaded node, own coordinates at reference anchors, layers a reader may
  ignore, and a deterministic build
- **Its reading of pangyplot:** bubbles come from topology alone; a
  collapsed mark says nothing per haplotype; a region over 50,000 segments
  is refused; above about 2 Mb the view is a grid of layout coordinates,
  not the hierarchy

## Against format 8

- Layers a reader may ignore: the "Later additions" rule of
  `docs/walks-format.md`
- A deterministic build: the byte identity across thread counts in
  `docs/walks-container/accept-5.0.0/4b14ee3/README.md`
- Every link of a loaded node: missing, as above
- An earlier blind design of the same day
  (`~/src/walks8-evidence/22a29087/blind-design/COMPARE.txt`) also found a
  bubble and chain hierarchy can sit beside a format 8 file as a separate
  file keyed by the same coordinates and node ids
