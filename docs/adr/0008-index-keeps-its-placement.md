# ADR 0008: The node and link index keeps its placement

- **Status:** accepted, 2026-10-30
- **Decides:** that the index gets no new placement for path graphs, and
  which product a path graph's graph track reads meanwhile
- **Measured by:** graph-walks 4.4's own cuts, the walk reader's
  `WalkReader.cut` and the index's `rgfaCut`, as the JBrowse plugin calls
  them, over windows of 10 kb: 50 over the chromosome and 10 in each region
  below. The graphs are HPRC release 2's pggb chr22, on GRCh38 and on CHM13,
  and chrY, and HPRC v2.1's Minigraph-Cactus chr22. The walk reader keeps the
  8 haplotypes the hosted HPRC walk track keeps; chrY has 2 of them, and the
  first 6 others in its header stand in.
  [docs/placement/](../placement/) has the scripts and every window's row

## Context

- The walk files place a step on a repeated node at its nearest pass and
  keep short detours in their chunk ([ADR 0001](0001-step-placement.md)).
  The index gives a repeated node its first pass and widens its links to
  reach the rest, which on pggb draws ordinary reference links as deletions
  spanning the window
- Filing by pass would bring the walks' placement to the index, as a format 3
  that graph-walks, bandage-core and the plugin read, with every hosted index
  rebuilt
- The plugin already draws a path graph from walk files when a track names
  them, so the walk files could also replace the index for path graphs

## Decision

- The index keeps format 2 and its first-pass placement. It gets no filing by
  pass, and no format 3 for placement
- Placement work for path graphs goes into the walk files and graph-walks
- The index stays the product for an rGFA, the source of every coarse tier
  and of `alleles`, and the graph track's source for a path graph. Hosted
  configs don't change

## Evidence

Windows where the walk view loses nothing a user needs, and median bytes
each reader fetches. A loss is a node on the window's reference, an allele of
a kept haplotype shown only as a skip row or not at all, a moved component,
or a link between two drawn nodes. Segmental duplications are LCR22A,
LCR22B-D and IGL on GRCh38's chr22, LCR22A and LCR22B-D on CHM13's, and Yp11
and Yq11 on chrY:

| graph | arm | control | segmental duplications | pericentromere | bytes, index / walks |
|---|---|---|---|---|---|
| MC chr22, GRCh38 | 47 of 50 | 10 of 10 | 19 of 30 | 9 of 10 | 309 / 102 KB |
| pggb chr22, GRCh38 | 43 of 50 | 10 of 10 | 14 of 30 | 5 of 10 | 582 / 167 KB |
| pggb chrY, GRCh38 | 44 of 50 | | 17 of 20 | 10 of 10 in Yq12 | 245 / 61 KB |
| pggb chr22, CHM13 | 32 of 50 | 10 of 10 | 13 of 20 | 4 of 10; p-arm 0 of 10 | 32.1 / 0.22 MB |

- On GRCh38's chr22, off segmental duplications, the walk view draws what
  the index draws, less the haplotypes it leaves out and the index's far
  passes, for about a third of the bytes. On chrY's arm and in Yq12, a median
  window holds 3 index nodes, mostly N runs, and the walk view reads more
- pggb's 5 failing pericentromeric windows lose at most 2 nodes each; 4 fail
  on links alone, up to 206 at 15.94 Mb
- In segmental duplications the index draws kept haplotypes' alleles that
  the walk view leaves out, showing the haplotype as a skip row or not at
  all. The harness counts every such node lost, so the table's losses are an
  upper bound: the index files a whole component under one interval, the
  same widening that draws 9,230 nodes a window in pggb's LCR22A against the
  walk view's 967, and so draws alleles the haplotype carries outside the
  window. On Minigraph-Cactus 49% of the counted nodes lie on such stretches,
  5% on pggb chr22 and 9% on pggb chrY. At MC chr22 18.45 Mb all 3,061 are a
  32 kb insertion before the window, and the haplotypes carry a deletion
  across it
- The walk view does lose some alleles and deletions. graph-walks draws
  nothing for a haplotype in a window inside its replaced stretch, 33% of the
  counted nodes on Minigraph-Cactus, 10% on pggb chr22 and 20% on pggb chrY.
  A deletion across a window shows nowhere when the path has a piece in that
  chunk, because `--walks` writes no skip row there and the reader keeps only
  the piece's steps on the window. On pggb, 86% and 80% of the counted nodes
  lie outside the chunks the cut read and those its skip rows name, where a
  haplotype's jump to a paralog filed them
- A row marking a path that crosses a chunk without stepping on the
  reference would not draw pggb's far-filed alleles, which lie outside every
  chunk such a row would sit in
- On CHM13 neither reader serves the short arm. The walk view loses up to
  23,534 nodes a window there, and the index draws a median 85,534
- On CHM13 the index reads 30-42 MB in 92 of 100 windows, control included,
  a median 0.9 s in control windows and 12.4 s on the short arm, because it
  files 2,383 node rows and about 5,150 link rows under the whole
  chromosome. The walk view's stratum medians run 0.1-1.7 MB
- Untraversed L lines are 19 of 7.2 M, 23 of 7.7 M and 0 of 4.7 M on pggb
  chr22, pggb chrY and MC chr22, so walk files miss next to no edge
- graph-walks 4.4 places a node at the reference's earliest pass, so it drew
  nothing at chrY 24.94 Mb and 2 of 4,751 reference nodes at CHM13 chr22
  5.20 Mb. That is a reader bug, which the walk-view figures above include

## Consequences

- Filing by pass leaves the roadmap, and the index's wide intervals on pggb
  stay as [open problems](../open-problems.md) records them
- [Open problems](../open-problems.md) keeps the question of walk files
  replacing the index for path graphs, with this measurement as its
  baseline. The question waits on detours spanning the window, deletions
  across it, pggb's paralog jumps, a zoomed-out walk tier, and carriers on a
  walk-drawn graph
- The CHM13-anchored pggb index's chromosome-wide rows are an open problem

## Alternatives rejected

- **The index adopts the walks' placement, format 3:** three readers and
  every hosted index change, and the plugin keys a segment by id, so two
  passes in one window draw as one
- **Walk files replace the index for path graphs now:** the walk view drops
  detours spanning a window and deletions across one, loses pggb's
  far-filed alleles, and walk files have no coarse tier
- **Develop both placements:** two engines to improve, for the one question
  of where a repeated node's steps go
