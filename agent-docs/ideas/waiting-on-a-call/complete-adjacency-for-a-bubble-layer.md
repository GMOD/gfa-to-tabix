---
name: complete-adjacency-for-a-bubble-layer
description: A collapsible bubble and chain layer for zoomed-out views, kept beside the walk file rather than as its layout; a blind design that read pangyplot says what a base format must give for it, and the one thing format 8 lacks is every link of a loaded node.
metadata:
  repo: gfa-to-tabix
---

# Complete adjacency for a bubble layer

`docs/open-problems.md`, "Every link of a loaded node, and a bubble layer",
states the gap: a walk-file cut lists only the links its kept walks take,
so a reader cannot verify a superbubble on the loaded subgraph, and a
bubble or chain layer needs a writer-built addition first (a tag on
`nodes` rows, a `links` unit kind, or a side file).

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
