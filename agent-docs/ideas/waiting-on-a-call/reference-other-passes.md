---
name: reference-other-passes
description: A reader of a walk file whose reference passes nodes more than once cannot say where the other passes lie or count a haplotype over all of them. Five routes were measured on pggb chrY against criteria fixed beforehand, changing nothing among them; none met all six, so the format stays. Taken up only if someone asks for pggb walk tracks to be hosted.
metadata:
  repo: gfa-to-tabix, graph-walks
---

# Where the reference's other passes lie

Measured 2026-11-23 on HPRC release 2 pggb chrY, with the 2023 cattle chr29
graph for sizes. Results, scripts and the per-window table are in
`~/src/walks8-evidence/sessions-20261122/passroutes/` (`out/summary.json`,
`out/routes-per-window.tsv`); the working folder is ada
`~/work/walks8-gates/agents/passroutes/`. Every check there was shown
failing on a planted fault.

## The two facts a window read lacks

- **Where:** the sequence, interval and strand of each other place the
  reference walks the window's nodes. A `ref` row gives the count, `passes`,
  and no place.
- **How many:** how often a haplotype steps those nodes in the whole graph.
  A cut holds the steps the writer filed at this pass.

## What each route gives

- **The files as they are, one read:** 22% of other passes, those inside
  the read's own tiles. Departure ends touch 0.26% of the rest and carry no
  strand, and they follow the writer's placement.
- **The files as they are, every tile's `ref` rows read once:** exact. On
  chrY that is 399 requests and 3.3 MB, once per file. No change to either
  file.
- **The node/link index as a second file:** the first pass only, 0.085% of
  other passes, with no strand, and no lookup by node id.
- **A table of runs of passes** (`start end otherStart otherEnd strand`):
  exact, and 13 times the size of the walk file. A node passed 14,656
  times pairs with itself that many times squared.
- **A table of families of intervals that share nodes:** exact. Copied into
  each tile it touches it adds 14 KB to the median window and 6.8% to the
  file (17% on cattle). As one unit a sequence it is 1.5% of the file (7.6%
  on cattle) and a first read of 3.0 MB.
- **A side file** with the same content costs the same.

A file whose reference passes every node once holds no row under any of
these: on the Minigraph-Cactus chr22 file every `passes` is 1.

## Counting over every pass

- With every pass's tiles read through the released reader, the eight
  drawn haplotypes' steps equal the GFA's in all 59 windows.
- That holds only while the writer's interior steps lie in tiles the reader
  happens to fetch. 23,845 of those steps were counted because their tile
  was read for another node's pass. One haplotype outside the eight,
  HG02668#1, has a step no pass's tile holds, so its count at
  `chrY:21.92 Mb` would be 3 where the GFA has 4. This was computed and not
  cut.

## Why nothing is changed

- No route met all six criteria. The family table misses the file-size
  limit in one layout and the first-read limit in the other, and the
  reference rows the file already holds give the same places for a similar
  one-time read.
- ADR 0011 keeps the format when the evidence is mixed, and asks for a user
  on a hosted file before a format change. No walk file with a revisited
  node is hosted.

## If it is taken up

- Start from reading the `ref` rows once, which needs no format change, and
  measure it in a reader.
- The count needs a statement of where interior steps are filed, or it
  stays short by steps no fetched tile holds.
- The three reviews a format change needs have not been run.
