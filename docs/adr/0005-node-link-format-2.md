# ADR 0005: Node and link format 2

- **Status:** proposed, 2026-10-28
- **Decides:** the changes the next node and link format makes. [ADR
  0002](0002-two-index-files.md) defers merging the two files until a format
  change happens for another reason, and this ADR lists those reasons
- **Measured by:** `scripts/synthetic-gfa.py` and `scripts/anchored-windows.mjs`.
  The numbers below come from synthetic graphs. Rerun both scripts on HPRC's
  pggb chr22 before deciding

## Context

### Collapsed repeats break the anchored layout

- `place.rs` gives a node the reference passes several times one coordinate,
  its first pass. `anchor.rs` then widens the node's links, and the components
  beside it, to cover every pass
- A 20 Mb graph with 20 haplotypes and repeats at pggb's density
  (`synthetic-gfa.py --repeats 2000 --copies 3`) has 15% of its link rows over
  1 Mb
- Median over 50 windows of 10 kb:

| | without repeats | with repeats |
|---|---|---|
| node bytes read, @gmod/tabix | 0.12 MB | 1.49 MB |
| link bytes read, @gmod/tabix | 0.21 MB | 2.84 MB |
| node and link bytes read, htslib's `tabix` | 0.023 MB | 2.2 MB |
| nodes graph-walks' `anchoredCut` keeps | 71 | 3,808 |
| of those, over 100 kb outside the window | 0 | 3,285 |

- The cut also draws the wrong graph. A repeated node's first-pass coordinate
  makes an ordinary reference link look like a deletion spanning the window,
  and `anchoredCut` keeps every link that spans the window
- Minigraph-Cactus and rGFA graphs have no such nodes, which is why
  [index-format.md](../index-format.md#wide-intervals) found wide intervals few
  on chr22

### Carrier lists dominate the rows at pangenome scale

- A plain GFA's rows list every assembly carrying the node by name, as
  `SM:Z:HG002.1,HG00097.1,...`, and each link row repeats the lists of both its
  nodes
- On a 2 Mb synthetic graph with 400 haplotypes, bgzipped:

| | node file | link file |
|---|---|---|
| with `SM:Z:` lists | 1.69 MB | 3.55 MB |
| without them | 0.15 MB | 0.25 MB |
| with a hex bitmask over a sample list | 0.40 MB | 0.54 MB |

- The lists are 97% of the node rows' raw bytes and 98% of the link rows' (2.8
  and 6.1 KB per row), which the browser parses whatever gzip saves
- The synthetic graph's alternate alleles have random carriers, which compress
  worse than real haplotypes' would, while all 401 assemblies carry every
  reference node, which compresses better

### No header

- graph-walks' `parseSegmentRow` tells the anchored layout from the contig
  layout by column count, 8 or more meaning anchored. A contig row with three
  tag columns would read as anchored
- No file names the graph it came from, so a track can pair a node file and a
  walk file from different builds without noticing

## Proposal

**Filing**

- A node the reference passes several times gets one node row per pass, each
  stating that pass's coordinate
- A link the reference path takes files under the pass where it takes it, and
  each link row states its nodes' coordinates at that pass. A window then sees
  one coordinate per node unless two passes fall inside it
- A link the reference never takes, such as a deletion or a jump between repeat
  copies, files under the span between the nearest passes of its two nodes. A
  deletion between nodes the reference passes once files as it does today, so
  a deletion spanning a window still comes back
- A component attaches to the pass of each repeated node nearest its
  attachments on nodes the reference passes once, as the walk files' nearest
  pass does
- Every link files under the intervals of both its nodes, never under one end
  alone

**Carriers**

- A `#samples` header line lists the assemblies, and each node row states its
  carriers as a bitmask over that list in a new tag, such as `SB:H:`
- The tool drops the two carrier columns from link rows. A reader takes
  carriers from the node rows of the same query

**Header and versioning**

- The first line is `#gfa-to-tabix  format:i:2  layout:Z:anchored  graph:Z:<hash>`,
  where the hash covers every segment's id and length and ignores their order.
  Walk files gain the same `graph:Z:` tag
- Readers refuse a format they don't know, and skip tags, header lines and row
  kinds they don't know. A file with no `#gfa-to-tabix` line is format 1

**One file**

- Nodes and links share one file with a row-type column, as ADR 0002 measured

## Alternatives rejected

- **File a wide link under its reference end only:** links fall from 2.84 to
  0.17 MB, but each cut gets a median 367 nodes with no link, so "every link
  with a node under the region" no longer holds
- **Cap a link's interval at, say, 1 Mb:** drops real deletions longer than the
  cap on rGFA and Minigraph-Cactus graphs, which have no repeated nodes
- **Keep `SM:Z:` and rely on gzip:** the browser still parses 2.8 to 6.1 KB of
  text per row
- **Reuse the `SM` tag for the bitmask:** graph-walks' `segmentSamples`,
  bandage-core's `carriedSamples` and the plugin's carriage lane parse `SM:Z:`
  as a list of names
- **Fix the reader only:** a @gmod/tabix change that clamps each chunk's start
  to the linear index halves bytes on files without wide rows and saves nothing
  on these. The wide rows overlap the window, so every reader has to fetch them

## Before deciding

- Rerun `anchored-windows.mjs` on HPRC pggb chr22 and on the HPRC v2.1 SV rGFA,
  and measure the carrier columns there
- One row per pass gives a node id several coordinates. graph-walks' `rgfaCut`
  keeps one segment per id, `anchoredCut`'s `side()` needs a link's pass
  coordinate, and `fold` needs one coordinate per node; check each against the
  filing rules above
- Reader changes: graph-walks (`parseSegmentRow`, `parseLinkLine`,
  `anchoredCut`), bandage-core's `carriedSamples`, and the plugin's carriage
  lane and add-track workflow
