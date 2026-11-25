---
name: inline-own-steps-on-pggb
description: On pggb most of a small window's bytes are attach fetches for the own steps departure records leave out, and CHM13 chrY's Yq12 windows are refused even for four haplotypes. Carrying a record's own steps inline under a size cap is estimated, not built, and is to be measured on pggb chrY against the fetches it replaces, when someone asks for pggb walk tracks.
metadata:
  repo: gfa-to-tabix, graph-walks
---

# Own steps inline, against attach fetches on pggb

## The cost

- Under walk format 7 (2026-11-05), a 1 kb window on HPRC's pggb chrY read
  a median 70 KB of tiles and departure records, and 389 KB once
  graph-walks attached the own steps departure records leave out (p90
  1,358 KB); on MC chr22 the same was 29 and 30 KB
  ([evidence](../../../docs/walks-container/arbA/results/res4/))
- The attach fetches read whole tiles elsewhere on the chromosome, one per
  record whose leave piece lies outside the window
  ([Attach fetches](../../../docs/walks-reading.md#attach-fetches)). On
  pggb most come from haplotypes hopping between collapsed-repeat copies,
  so every container measured pays them; ADR 0010 leaves it unfixed as a
  record and placement question
- In format 8 (2026-11-12, graph-walks 676a0dd), CHM13 chrY's Yq12 windows
  are refused even for four haplotypes at the default budgets: the attach
  fetches or the departure read pass the reader's budgets
  ([pggbY notes](../../../docs/walks-container/pggbY/notes.md))

## Two costs no addition removes

A satellite record's detail unit is fetched whole or not at all, and a
departure record is filed in every bin of its cover, so a window inside a
long record pays for it at every zoom. A paged detail kind or a coarser
layer can bypass either; neither removes it.

## The proposal

- Carry a record's own steps inline when they are 4 kb or less. The reader
  review estimated that at about 0.1 MB compressed on MC chr22, an
  estimate, not a build
  ([reader review](../../../docs/walks-container/reviews/reader.md)); not
  measured on pggb
- A unit kind holding them is a later addition a format 8 reader skips
  ([Later additions](../../../docs/walks-format.md#later-additions))
- Measure it under a size cap on pggb chrY, the Yq12 windows first,
  against the attach fetches it replaces

## What it waits on

The measurement, and under ADR 0011 someone asking for pggb walk tracks.
Placement bears on it: a placement that hops less files fewer records
(`../waiting-on-a-call/pggb-placement-rule.md`).
