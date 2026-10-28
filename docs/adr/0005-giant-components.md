# ADR 0005: A giant component keeps its own coordinates

- **Status:** accepted, 2026-10-28
- **Decides:** how the anchored layout files a component of nodes off the
  reference that is too large for a browser to read in one window
- **Measured by:** HPRC release 2's pggb chrY
  (`20251014_hprc25272.p98-k311.chrY.gfa.zst`: 4.1 M nodes, 7.7 M links,
  1,053 paths) and chr22 (4.8 M nodes, 7.2 M links, 1,773 paths), HPRC v2.1's
  Minigraph-Cactus chr22, cut from `hprc-v2.1-mc-grch38.gbz`, and HPRC's SV
  rGFA, all on GRCh38, through htslib's `tabix` over 50 windows of 10 kb

## Context

- The anchored layout files every node off the reference under the reference
  interval between its component's first and last attachment, so a window
  under a component reads every node and link of it
- pggb grows components of millions of nodes across reference gaps and repeat
  arrays. On chrY, one of 3.5 M nodes fills GRCh38's Yq12 gap, 26.6-56.8 Mb,
  and a 10 kb window there overlaps 3.7 M node rows and 7.1 M link rows, 10 GB
  of text. @gmod/tabix's gzip decoder failed on one such window with
  `RuntimeError: unreachable`
- On chr22, one of 2.48 M nodes hangs from 10.5 to 50.8 Mb, and a median
  window reads 2.48 M node rows and 3.93 M link rows

## Decision

- A component of more than `--max-component` nodes, default 10,000, keeps its
  own coordinates, as a component attached to no reference node does. A
  window under it reads only the links into it, which a graph track draws as
  dead-end nodes
- `--max-component none` files every component under the reference
- The limit applies to every anchored file: the index, `build`'s fine index
  and coarse tier, and `fold`
- The tool lists each moved component, its node count and the interval it
  would have filed under, so a user can set the limit between a bubble they
  want drawn and the giants
- The README's FAQ explains the option to users

## Evidence

Rows per 10 kb window with the default limit:

| graph | rows | median | p90 | max |
|---|---|---|---|---|
| pggb chrY | node | 141 | 3,631 | 10,182 |
| pggb chrY | link | 220 | 44,139 | 69,413 |
| pggb chr22 | node | 438 | 4,830 | 12,567 |
| pggb chr22 | link | 626 | 22,004 | 83,041 |
| MC chr22 | node | 392 | 1,006 | 9,344 |
| MC chr22 | link | 544 | 1,445 | 13,241 |

- pggb chrY moves 3 components holding 3.74 M nodes, and chr22 moves 4
  holding 2.53 M
- The SV rGFA moves one, a 22,501-node bubble at chr1:2.65-2.78 Mb. A window
  under it reads 22,690 node rows and 34,015 link rows, 6.4 MB, and 189 and
  291 rows, 53 KB, with the limit
- MC chr22 (3.1 M nodes, 4.7 M links, 1,131 paths) moves 14 components, the
  largest of 208,833 nodes at 11.82-11.88 Mb beside the centromere, others in
  the segmental duplications at 18-25 Mb. Without the limit its median window
  barely differs, 398 node and 575 link rows, but its p90 window reads 22,827
  and 31,583 and its costliest 110,259 and 181,879, 403 MB. Its link file
  grows 5%, from 853 to 895 MB
- A node count picks out the cost better than a span. Off-reference node rows
  per chrY window:

| components anchored | moved | median | p99 | max |
|---|---|---|---|---|
| all | 0 | 3,708,709 | 3,708,709 | 3,712,505 |
| those spanning at most 1 Mb | 331 | 0 | 975 | 35,120 |
| those of at most 10,000 nodes | 3 | 0 | 9,682 | 10,432 |

## Consequences

- A window reads about 10,000 node rows at most, plus their links
- A graph track shows a moved component only where it joins the reference.
  The walk files and the contig layout keep every node, so a haplotype view
  still draws each path through it
- A moved component's nodes sit on whichever haplotype contig placed each
  one, so pggb chrY's three giants spread over 823 contigs. A link joining two
  contigs gets a row on each, and chrY's link file grows from 378 to 682 MB.
  chr22's files shrink, from 1.3 to 0.45 GB of nodes and 3.9 to 1.6 GB of
  links, because without the limit its giants filed a row under each GRCh38
  sequence they attach to
- Link rows keep a long tail on pggb graphs. In chrY's costliest window,
  63,887 of 69,413 link rows join two reference nodes, from collapsed repeats
  that the limit doesn't touch ([open problems](../open-problems.md))
- No reader expands a moved component, and one query can't fetch it while its
  nodes spread over contigs ([open problems](../open-problems.md))

## Alternatives rejected

- **No limit:** a pggb window under a giant reads gigabytes, and an MC window
  beside a centromere 403 MB
- **Move components spanning over 1 Mb:** moves 331 on chrY, most of them
  small ones that cost a window little, and keeps a 35,120-row window
- **Cap a link's interval:** drops real deletions longer than the cap on rGFA
  and Minigraph-Cactus graphs, and leaves node rows uncapped
