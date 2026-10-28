# ADR 0005: Node and link format 2

- **Status:** proposed, 2026-10-28
- **Decides:** the changes the next node and link format makes. [ADR
  0002](0002-two-index-files.md) defers merging the two files until a format
  change happens for another reason, and this ADR lists those reasons
- **Measured by:** HPRC release 2's pggb chrY
  (`20251014_hprc25272.p98-k311.chrY.gfa.zst`: 4.1 M nodes, 7.7 M links,
  1,053 paths) and chr22 (4.8 M nodes, 7.2 M links, 1,773 paths) on GRCh38,
  HPRC's SV rGFA, and synthetic graphs from `scripts/synthetic-gfa.py`,
  measured with `scripts/anchored-windows.mjs` and htslib's `tabix`

## Context

### Giant components swallow the anchored layout

- The anchored layout files every node of a component under the reference
  interval between its first and last attachment, so a window inside a bubble
  reads every node of it
- On pggb chrY, the index takes a minute and 5.2 GB, and writes 86 MB of
  nodes and 378 MB of links. Rows overlapping a 10 kb window:

| window on GRCh38 chrY | node rows | link rows | link text |
|---|---|---|---|
| 5.00-5.01 Mb | 122 | 239 | 0.4 MB |
| 20.00-20.01 Mb | 203,863 | 359,712 | 584 MB |
| 40.00-40.01 Mb | 3,708,710 | 7,098,863 | 9.4 GB |

- One component of 3.5 M nodes fills GRCh38's Yq12 gap, 26.6-56.8 Mb, and one
  of 203 k spans 12.5-56.9 Mb. Three components over 10,000 nodes hold 97% of
  the graph's 3.86 M nodes off the reference
- @gmod/tabix estimates a median window at 74 MB of nodes and 349 MB of links,
  and its gzip decoder failed on one window with `RuntimeError: unreachable`
- Off-reference node rows per 10 kb window, by which components keep the
  anchored filing:

| components anchored | moved | median | p99 | max |
|---|---|---|---|---|
| all | 0 | 3,708,709 | 3,708,709 | 3,712,505 |
| those spanning at most 1 Mb | 331 | 0 | 975 | 35,120 |
| those of at most 10,000 nodes | 3 | 0 | 9,682 | 10,432 |

- More than half of GRCh38 chrY lies in the Yq12 gap, which holds no reference
  node, so the median window reads no node once the gap's component moves
- A node count picks out the cost better than a span: 330 components wider
  than 1 Mb hold at most 10,000 nodes each and cost a window little
- pggb chr22 is worse throughout. Its index takes 6.5 minutes and 18.7 GB, and
  writes 1.3 GB of nodes and 3.9 GB of links. A median 10 kb window reads 2.48
  M node rows and 3.93 M link rows, 11 GB of link text, because 54% of the
  node rows on GRCh38 chr22 span over 1 Mb

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
- On pggb's chromosomes, bgzipped:

| | chrY nodes | chrY links | chr22 nodes | chr22 links |
|---|---|---|---|---|
| lists' share of the raw text | 64% of 0.97 GB | 90% of 10.5 GB | 94% of 22 GB | 95% of 77 GB |
| with `SM:Z:` lists | 86 MB | 378 MB | 1.29 GB | 3.9 GB |
| without them | 54 MB | 122 MB | 154 MB | 346 MB |

### No header

- graph-walks' `parseSegmentRow` tells the anchored layout from the contig
  layout by column count, 8 or more meaning anchored. A contig row with three
  tag columns would read as anchored
- No file names the graph it came from, so a track can pair a node file and a
  walk file from different builds without noticing

## Proposal

**Giant components**, available now as `--max-component N`, default 10,000

- A component of more than N nodes keeps its own coordinates, as a component
  attached to no reference node does. A window inside it reads only the links
  that enter it, and existing readers draw the allele's ends as stubs
- `--max-component 10000`, 50 windows of 10 kb through htslib's `tabix`:

| graph | rows per window | median | p90 | max |
|---|---|---|---|---|
| pggb chrY | node | 141 | 3,631 | 10,182 |
| pggb chrY | link | 220 | 44,139 | 69,413 |
| pggb chr22 | node | 438 | 4,830 | 12,567 |
| pggb chr22 | link | 626 | 22,004 | 83,041 |

- On both pggb graphs the limit takes a median window from millions of rows to
  hundreds, and caps node rows near 10,000, as the table in the context
  predicts. A median chr22 window still reads 4.4 MB of link text, most of it
  carrier lists
- In chrY's costliest window, 63,887 of 69,413 link rows join two reference
  nodes, and 15,367 of those join nodes over 1 Mb apart. Such a link jumps
  between repeat copies, and only per-pass filing files it narrowly. The
  synthetic repeat graph showed the same, with node bytes per window falling
  from 1.49 to 0.20 MB and links staying at 2.84 MB
- A moved component doesn't stay on one sequence. Each of its nodes keeps the
  coordinate of the path that placed it, so chrY's three giants spread over
  823 haplotype contigs, and 96% of their links join two contigs and get a row
  on each. chrY's link file grows from 378 to 682 MB
- chr22's files shrink instead, from 1.3 to 0.45 GB of nodes and 3.9 to 1.6 GB
  of links. Without the limit its giants attach to several GRCh38 sequences
  and file a row under each: 14.7 M node rows for 4.8 M nodes
- The spread also means one query can't fetch a moved component to expand its
  stubs. The writer would first have to give each component a single
  sequence's coordinates
- On HPRC's SV rGFA the limit moves one component, a 22,501-node bubble at
  GRCh38 chr1:2.65-2.78 Mb. A 10 kb window there reads 22,690 node rows and
  34,015 link rows, 6.4 MB of text, and 480 rows and 53 KB with the limit. The
  link file grows by 2%
- The limit is on by default, since it cuts window cost on every graph
  measured. A reader draws a moved component's alleles as stubs, and none
  expands them yet

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
  to the linear index ([tabix-js#158](https://github.com/GMOD/tabix-js/pull/158))
  saves 15-17% of a cold window's bytes on HPRC's MC links and a gene GFF3, and
  nothing on these files. The wide rows overlap the window, so every reader has
  to fetch them

## Before deciding

- Measure a Minigraph-Cactus graph with and without `--max-component`
- Choose whether a reader expands a moved component, which first needs the
  writer to place the component on one sequence
- One row per pass gives a node id several coordinates. graph-walks' `rgfaCut`
  keeps one segment per id, `anchoredCut`'s `side()` needs a link's pass
  coordinate, and `fold` needs one coordinate per node; check each against the
  filing rules above
- Reader changes: graph-walks (`parseSegmentRow`, `parseLinkLine`,
  `anchoredCut`), bandage-core's `carriedSamples`, and the plugin's carriage
  lane and add-track workflow
