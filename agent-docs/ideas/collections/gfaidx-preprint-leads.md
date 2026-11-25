---
name: gfaidx-preprint-leads
description: What the gfaidx preprint (bioRxiv 2026.11.15.766357, posted 2026-11-17) adds beyond docs/comparison.md - its 84-query locus set, genes projected per haplotype, Louvain communities for graphs with no usable reference, node-first postings with predicted occurrences, and path-length checkpoints - each pointing at the idea or todo it would feed.
metadata:
  repo: gfa-to-tabix, bandage-core
---

# Leads from the gfaidx preprint

Dabbaghie and Steinegger, "Efficient genome graphs indexing, querying and
visualization with gfaidx and gfaidx-viz", bioRxiv
[10.64898/2026.11.15.766357](https://doi.org/10.64898/2026.11.15.766357).
`docs/comparison.md` already covers gfaidx as a tool, and
`../ready/gfaidx-viz-views.md` covers the copy-number track. These are the
parts of the preprint that are not in this repo yet.

- **Their locus set as our query set.** Fig. 1d queries CHM13 intervals of
  1, 10 and 100 kb and 1, 2, 5 and 10 Mb around 12 loci (84 queries): the
  chr7, chr17 and chr22 α-satellite arrays, MHC, KIR, IGK, AMY1A, SMN1, LPA,
  KANSL1, CYP2D6, and a chr3 control. Timing graph-walks on these windows
  would put our numbers beside theirs. The loci are also where walk files
  abridge or refuse to cut, which random windows rarely hit. Feeds
  `../waiting-on-a-number/query-time-unmeasured.md`
- **Genes per haplotype, off the backbone.** They join CAT GFF3 annotations
  of all 464 HPRC v2 haplotypes to the W lines by binary search over each
  walk's offsets, and colour nodes by gene. With no alignment, paralogs such
  as RHD/RHCE and C4A/C4B do not multi-map. Fig. 2b colours RHD/RHCE nodes
  and highlights an RhD-negative haplotype skipping the RHD loop.
  bandage-core's gene pins and outlines come from the reference backbone
  (`src/genes/`), so a gene copy that exists only on some haplotypes, such
  as the AMY1 copies, gets no gene. Walk rows carry `path` and `hapOffset`,
  so the same join could run in the reader
- **Louvain communities for graphs with no usable reference.** gfaidx files
  the graph by community, with 0.04% of links crossing communities on
  Minigraph-Cactus chr1 and 0.4% on pggb chr1. This is prior art for a mode
  that files by graph structure rather than by reference position: assembly
  graphs and de Bruijn graphs, which gfa-to-tabix cannot index, and the
  repeated nodes of `../waiting-on-a-call/index-wide-intervals-on-pggb.md`.
  Its cost is in `docs/comparison-details.md`: every region query reads the
  member of links between communities whole
- **Node-first postings with predicted occurrences.** For each node, `.pdx`
  lists the paths and steps that visit it. An occurrence that follows from
  the previous node in the same path costs at most one bit, and a path
  taking the other side of a bubble is predicted again where it rejoins.
  This is a cheap way to answer "which haplotypes pass this node" off the
  reference, one of the limits in
  `what-a-format-8-reader-cannot-say.md` ("haplotype counts off the
  reference"), if a later format addition takes it up
- **Path-length checkpoints.** `.pcx` stores each path's cumulative length
  every 4,096 steps, so a step's base position is one read plus a sum of at
  most 4,095 node lengths. An alternative layout for the side file in
  `../waiting-on-a-call/haplotype-coordinate-lookup.md`
- **The outreach issue.** Their Methods credit BandageJS as the prototype
  gfaidx-viz's front end was adapted from, which is the opening for the
  issue `../ready/gfaidx-viz-views.md` still asks for. `docs/comparison.md`
  could cite the preprint beside the repository link
