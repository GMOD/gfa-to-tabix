---
name: index-wide-intervals-on-pggb
description: The node and link index files a node the reference passes several times at its first pass, so on a pggb graph a window in a repeat reads megabytes of far rows and draws ordinary reference links as deletions. No fix is adopted; build now writes a plain GFA's index in the contig layout, and what the contig layout draws in LCR22 against the anchored one is not measured.
metadata:
  repo: gfa-to-tabix
---

# The index's wide intervals on pggb graphs

- `place.rs` gives a node the reference passes several times one
  coordinate, its first pass, and `widen` in `src/anchor.rs` stretches its
  links and the components beside it over every pass. A window in a
  repeat then reads megabytes of rows, most from far outside it, and the
  cut draws an ordinary reference link as a deletion spanning the window
  ([index-format.md](../../../docs/index-format.md#wide-intervals),
  measurements of 2026-10-28 to 10-30 in
  [index-measurements.md](../../../docs/placement/index-measurements.md#collapsed-repeats-in-pggb-graphs))
- Minigraph-Cactus and rGFA graphs have no such nodes, so no hosted
  Minigraph-Cactus index is touched
- Ruled out, with their numbers on the measurements page: filing a wide
  link under its reference end only, a reader-only fix, filing by pass
  ([ADR 0008](../../../docs/adr/0008-index-keeps-its-placement.md)) and
  capping a link's interval
  ([ADR 0005](../../../docs/adr/0005-giant-components.md))

## Since then

- `gfa-to-tabix build` writes a plain GFA's index and tier in the contig
  layout and no anchored file, because the anchored layout files a
  segment under every reference position its branch spans
  (`src/cli.rs`, `docs/subcommands.md`, checked 2026-11-25). The bare
  command still writes the anchored layout, and the paper's chrY benchmark
  used it (`../../todo/dense-pggb-chain-joints-drawn-as-skips.md`)
- jbrowse-components' `build_ecoli_pangenome_graph.sh` copied a
  contig-layout file under the anchored name for the hosted E. coli pggb
  track (as of 2026-10-30, not rechecked)
- The revisited-reference study found that an index of such a graph
  cannot say whether the reference takes a link, and a reviewer there
  recommends `revisited:i:N` on the index's header
  (`../../handoffs/2026-11-22-revisited-reference-study.md`). An index
  header stating the count of revisited nodes, and passes in the index,
  are index-format changes; the dense-chain todo above has the numbers
  for them, and neither is proposed

## Not yet done

- Trace which components the CHM13-anchored pggb chr22 rows belong to
  (2,383 node rows and about 5,150 link rows filed under CHM13 0-51.3 Mb)
- Measure what the contig layout draws in LCR22 against the anchored one

## What it waits on

The study's ticks and its format question
(`../../handoffs/2026-11-22-revisited-reference-study.md`), and the
measurement above.
