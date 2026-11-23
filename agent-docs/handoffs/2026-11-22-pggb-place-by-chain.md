---
name: 2026-11-22-pggb-place-by-chain
description: The owner asked whether pggb graphs need a different approach. One cause runs through every hard pggb case, the reference passing nodes more than once, and a laptop session proposes that the walk writer place each haplotype by a co-linear chain against the reference, built from the graph alone. The rule, how it differs from what was tried, what is measured and what is not, and the spike to run. Nothing is built, and the owner has not said go.
---

# pggb: place haplotypes by a chain, 2026-11-22

The owner asked whether reference-free graphs need a different way of
thinking, or pre-processing. This file holds the answer given and the one
proposal in it that no other file has. Delete it when the spike below has
run and its result is filed.

## State

- **Nothing is built or measured.** No branch, and no commit to any code.
- **The owner has not said go.** They asked for this to be written down.
- The sessions named `gfa-to-tabix-64` and `gfa-to-tabix-d8` were to be told
  and could not be reached. This file is how they learn of it.
- It asks no session to change what it is doing.

## The one cause

- Every row is keyed by a position on the reference. A node has one such
  position only where the reference passes it once.
- Minigraph-Cactus keeps that for its own reference: its files state
  `revisited:i:0`. pggb merges the copies of a repeat into shared nodes. On
  HPRC release 2's pggb chrY 671,879 of the reference's 827,826 steps are
  on nodes it passes more than once, one node 14,656 times
  (`docs/walks-container/pggbY/stats.GRCh38.json`).
- The graph states that the copies are the same sequence. Which copy a
  stretch of a haplotype corresponds to is in no node or link. It is only
  in the order of each path.
- The index answers "which copy" with the first pass and the walk writer
  with the nearest pass, both one step at a time. Such answers flip between
  copies, and a reader draws each flip as an event:
  - `todo/dense-pggb-chain-joints-drawn-as-skips.md`: a window of 14,142
    nodes holds 114 of its own, and 672 of its 703 drawn skips are the
    reference's own later steps.
  - `docs/walks-container/reshape/reviews/biologist.md`: HG002#1 has 561
    records across a palindrome it walks straight through.
- By a keyword count on 2026-11-22, pggb or revisited nodes are in 35 of
  the 180 entries of `docs/issues-log.md` and in 22 of the 38 sections of
  `docs/open-problems.md`: a fifth of what was fixed, and most of what
  stays open.

## What does not help

- **Rewriting the graph** with a copy of a node for each reference pass
  changes node ids, and each haplotype step on a split node still needs a
  copy picked.
- **`odgi untangle`** votes per segment with no continuity. **The wfmash
  alignments** HPRC ships overlap in the same repeats: 73.5% of chrY's
  lifted blocks overlap another block of the same contig. Both are from
  `docs/open-problems.md`, "Placement of steps on nodes the reference
  passes more than once".
- **Reader rules that judge from a window's cut** which far links are
  real. In a cut they look like a Minigraph-Cactus deletion spanning the
  window (the todo above, "A rule over the cut alone cannot fix it").

## The proposal: place by chain, in the writer

For each contig of a haplotype, in a graph whose reference passes a node
more than once:

- **Anchors:** each of its steps on a node the reference passes once in
  the whole file, as the contig's offset, the reference sequence and
  offset, and whether the two read the node on the same strand.
- **Chain:** the heaviest run of anchors that is co-linear on one sequence
  and strand, as an aligner chains seeds. Anchors off it are dropped.
- **A step on the chain** takes the chain's reference position.
- **A step on a node the reference passes several times** takes the pass
  that lies between the chain anchors either side of it, on their strand,
  where there is one.
- **Every other step is the haplotype's own sequence,** off the reference,
  though its node is one the reference passes elsewhere.
- **Where a chain ends,** at an inversion or a move to another locus, the
  next one starts, and a departure record joins the two as it does today.

A graph whose reference passes every node once is written as today, byte
for byte.

Not settled in the rule, and each the writer's policy: the weight of an
anchor and the cost of a gap, a floor under which a chain is dropped, and
whether a node passed two or three times may anchor. Write each down
before the first build and pick by it.

## How it differs from what was tried

- **Nearest pass and `stay`** (`visits_along`, `stay_home` and `rehome` in
  `src/walks.rs`) predict each step from the last placed one. Nothing
  holds a contig to one copy over a distance.
- **Placing only on once-passed nodes, with no chain,** was rejected on
  2026-11-06 (open-problems, "Placing nothing there instead"). Inside a
  repeat the once-passed nodes are the variants that tell its copies
  apart, and a haplotype carries now one copy's and now another's, so
  2,693 of 2,760 records at chrY 23.6 Mb still joined ends over 1 Mb
  apart. The chain drops those anchors.
- **The `--chain` spike** of 2026-10-30 searched over passes and did not
  finish chrY in 2 h (`docs/departures/results/chain.txt`). Its code was a
  scratch copy of `src/walks.rs` and is not in the repo. Anchors on
  once-passed nodes never list a node's passes.
- **Alignment-guided placement** (`docs/departures/scripts/primary.py`)
  chains wfmash blocks, so it needs a second input file. This takes the
  graph alone.

## Measured, and not

- **Measured, with outside alignments as the guide:** departure records
  fall from 425,836 to 30,329 on pggb chrY and from 5,333,737 to 177,475
  on chr22, and chrY's rows per window at p95 from 18,037 to 265
  (`docs/departures/results/rebuild/`, the `pggbY`, `pggbYa`, `pggb22` and
  `pggb22a` logs and audits). This is the size of gain to hope for, not a
  result for the proposal.
- **Its agreement with Minigraph-Cactus is not to be quoted** until
  `agree.py`'s faults are mended. open-problems lists them.
- **Not measured, on any graph:** the chain from the graph alone. Whether
  once-passed anchors are dense enough off the satellites, what the build
  costs, and whether every path rebuilds from its rows under it.

## What it costs, and what it leaves open

- **Sequence that matches several copies shows at one.** Under the
  alignment-guided placement LCR22A's strict recall went from 93.5% to
  71.5%. The other copies still show the shared nodes.
- **Showing every copy stays open.** One placement per file does not rule
  out a second file under another rule, and the HPRC pggb team may weigh
  in.
- **Satellites, and arrays whose copy counts differ,** have no anchors, so
  each comes out as one stretch of own sequence between two anchors. A
  mark for "present, copy unresolved" there needs the biologist review's
  table of collapsed runs and `refBp`. **Those are format additions,** to
  be raised and reviewed as one. This proposal does not need them.
- **More runs off the reference will hold a node the reference passes
  elsewhere,** the case where a loaded and an unloaded cut differ today
  (open-problems, "pggb chrY in walk format 8").

## Standing against the frozen format

- Pass choice is this writer's policy and not format 8.
  `docs/walks-format.md`, "What a reader relies on", says a reader never
  chooses a pass, and promises that a step on a once-passed node is on R
  only of a file that states `revisited:i:0`.
- No hosted walk file changes: none has a revisited node.
- `verify7.py` holds a file with revisited nodes to today's policy and
  would fail one written this way, where `spec8.py` passes it
  (open-problems, "Checkers that hold a file to more, or less, than the
  format").
- A file does not name its placement rule. A `#walks` tag for it is an
  addition to the format, to be raised on its own.

## The spike

- **Where:** ada, beside the queue session and in none of its checkouts.
  The graph was at `~/work/arb-format-opus/in/pggbY.gfa` on 2026-11-12;
  check that it still is. pggb chr22's GFA was gone from ada on
  2026-11-06.
- **What:** a third column beside nearest pass and the alignment-guided
  projection, on pggb chrY first: departure records and rows, rows per
  64 kb window, the bytes of a 1 kb window with its attach fetches, build
  time, and `walks-truth.py rebuild` on the file.
- **The bar,** as open-problems writes it for the Jaccard candidate and
  taken unchanged: agreement with Minigraph-Cactus's placement within 5
  points of the alignment-guided projection's in every stratum and below
  nearest pass in none, departure records at least halved from nearest
  pass's, every path rebuilt from its rows, and build time within twice
  nearest pass's.
- **Minigraph-Cactus must not move:** a chr22 build, byte for byte.
- **Then look at it** in a reader, before and after, at the biologist
  review's windows: the palindrome at chrY 23.6 Mb, Yq11 at 18.61 Mb and
  18.55 Mb, the control at 14.5 Mb, and with them TSPY at 9.39 Mb and a
  Yq12 window.

## For readers, whatever the writer does

- A size, a skip, a turn mark or an orientation computed from a node's
  stored place is wrong on a graph whose reference revisits nodes. The
  reference's steps give them. The todo names seven files not yet looked
  at.
- The node and link index holds one place a node (ADR 0008), so it cannot
  give a later-pass window its reference. There the walk file is the
  graph track's source.
