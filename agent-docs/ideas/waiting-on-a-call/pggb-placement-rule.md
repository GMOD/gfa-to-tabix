---
name: pggb-placement-rule
description: Which copy a haplotype's step is shown on where the reference passes a node more than once - one copy by a better rule than nearest pass, every copy, or none. Nearest pass ships; the working plan of 2026-11 was alignment-guided placement with nearest pass as the fallback, and a place-by-chain spike from the graph alone waits on a go. Taken up when someone asks for pggb walk tracks.
metadata:
  repo: gfa-to-tabix, graph-walks, bandage-core
---

# Placement on nodes the reference passes more than once

The live thread is `../../handoffs/2026-11-22-pggb-place-by-chain.md`: the
place-by-chain proposal, how it differs from what was tried, its spike and
its bar. What a reader cannot say of the other passes is
`reference-other-passes.md`, and what other tools do is
`../../reference/field-practice-at-collapsed-repeats.md`. This file holds
the rest of the question and does not restate those.

## What ships

- gfa-to-tabix places a step on a node the reference passes more than
  once at the nearest pass, with `stay`
  ([ADR 0001](../../../docs/adr/0001-step-placement.md),
  [Repeats in pggb graphs](../../../docs/walks-writer.md#repeats-in-pggb-graphs)).
  The format calls the pick the writer's
  ([Exact and chosen](../../../docs/walks-format.md#exact-and-chosen)), so
  another rule writes a format 8 file with another placement, not a new
  format
- No hosted walk file has a revisited node; Minigraph-Cactus's GRCh38
  path passes every node once
- ADR 0011 keeps collapsed repeats open and names two fixes that add to
  the format, a table of collapsed runs with each record's own bp on
  reference nodes, and placement from an alignment; either is taken up
  only when someone asks for pggb walk tracks
  ([ADR 0011](../../../docs/adr/0011-format-7-is-frozen.md#decision))

## What nearest pass gives on pggb

Measured on the departure-record builds of 2026-10-30 to 11-04
(`docs/departures/`):

- On chrY 97% of records have an end on a node the reference passes more
  than once, 87% carry 0 own bp, one haplotype has up to 2,065 records
  over one 64 kb window, and 35.9% of pieces land within 10 kb of where
  Minigraph-Cactus places the same contig position (35.6% in Yp11 and
  Yq11)
- On chr22 a window can read 73 MB of departure rows in the spike's
  format, and 32.9 MB in 2,491,246 rows in the port's
- Scores of nearest pass against two alignment-guided placements, and the
  review's caveats that keep the agreement figures from being quoted, are
  in [placement-scores.md](../../../docs/departures/placement-scores.md)

## Rules on record, none evaluated here

- `odgi untangle` votes per segment with no continuity term and ties
  identical copies; vg deconstruct assigns alleles by a 10 kb context
  vote; HPRC release 2 ships no projection of its pggb graphs, only the
  wfmash all-vs-1 alignments; VRPG copies a collapsed node for the
  reference's later passes and places no haplotype on the copies
- The wfmash alignments are ambiguous in repeats themselves: wfmash maps
  every segment of an array to its best copy
- `odgi position`'s path-Jaccard rule: `../waiting-on-a-number/odgi-jaccard-placement.md`

## The working plan, not a closed choice

- Show one copy: alignment-guided placement as an optional `--alignments`
  input recorded in the header with the alignment's name and checksum,
  nearest pass as the fallback, and a viewer that says where a step is one
  of several copies, lists the reference's other passes and offers the
  graph view
- Before adopting it, check that every path rebuilds from its rows under
  that placement: the chaining spike was checked, the alignment-guided one
  was not
- A header tag naming the alignment is an addition to the format, raised
  on its own; place by chain needs no second input and no tag
- The cost of one copy: sequence that matches several copies shows at
  one. In LCR22A strict recall went from 93.5% to 71.5% under the
  projection

## Showing every copy

- Stays open. ADR 0009 holds one placement per file, so other copies
  could come later as a second file, under a header tag naming its rule
- The HPRC pggb team may weigh in:
  `../waiting-on-someone-else/questions-for-the-pggb-authors.md`

## Not pggb's alone

A reference that is not the graph's own revisits nodes too: CHM13 as a
haplotype of the GRCh38-referenced Minigraph-Cactus graph gave 5.5 M
departure records, 32.4 M rows on chr9 alone, and was not hosted
([placement-scores.md](../../../docs/departures/placement-scores.md#chm13-as-the-reference-of-the-grch38-referenced-graph)).
The hosted hs1 files come from the CHM13-referenced graph, which passes
every node once.

## What it waits on

- A go or no go on the place-by-chain spike (`../../handoffs/2026-11-22-synthesis.md`, "Place by chain")
- The scores rerun with `agree.py`'s faults fixed
- Under ADR 0011, someone asking for pggb walk tracks to be hosted
