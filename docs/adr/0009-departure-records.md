# ADR 0009: One record per departure, filed as blocks under a sibling sequence

- **Status:** accepted, 2026-10-31
- **Decides:** what a walk file holds for every place a haplotype's path
  does not follow the reference between two of its steps on it, how the
  rows are filed so that any window finds them, and what the projection
  onto one reference means where the reference passes a node more than
  once. Walk format 6
- **Measured by:** a writer spike built on HPRC v2.1 Minigraph-Cactus chr22
  and HPRC release 2 pggb chrY and chr22, on GRCh38, with the scripts and
  results in [docs/departures/](../departures/)
- **Supersedes:** [ADR 0006](0006-walks-skip-rows.md)'s `skip` rows

## Context

- Format 5 writes a `skip` row only where a path has no piece in a chunk,
  with the stretch and nothing else: no own sequence, no strand, no pass
  counts, and none at all for a stretch over 32 chunks. graph-walks then
  reconstructs what it can from the pieces it happens to read, so a
  haplotype's answer depended on which other haplotypes were kept, and the
  viewers called the result a deletion
- The tools make no variant calls; they state what the data shows. A
  haplotype's answer must not depend on the keep set. A window inside a
  jump of any length must find it from a bounded number of range requests
  near the window. Long own sequence is summarised and fetchable. No
  backwards compatibility
- Four independent designs, two of them blind, converged on one record
  with each end stated on its own; the spike built that record and found
  four things it still lacked

## Decision

**The record.** One `departure` row per place a path's consecutive steps
on one reference sequence S are not adjacent on S at the passes they took.
Fields, plain integers:

```
seq~departure  a  b  departure  path fragStart hapStart ownBp ownSteps missingBp
               leavePos leaveNode leaveStrand leavePasses leaveChunk
               rejoinPos rejoinNode rejoinStrand rejoinPasses rejoinChunk  [xb:i:bp]
```

- An end is a step on S: its breakpoint on S, where the haplotype's
  sequence stops following S (the node's end for a step along S, its start
  for a step against it, and the other way round for the rejoin); the
  node; `+` or `-` for the step along or against S's orientation at that
  pass; how many times the reference's paths pass the node; and the start
  of the chunk the step's piece is filed under. A one-ended record, at a
  contig's end, has `.` in the five columns of the end it lacks
- `hapStart` is where the haplotype's own sequence between the ends starts
  on its contig, right after the leave step; it runs `ownBp` over
  `ownSteps` steps, both 0 for a direct jump. `ownSteps` counts every step
  between the ends, those on other reference sequences included.
  `missingBp` counts the part of `ownBp` no W line of the contig covers,
  across a record gap; `xb` the part the path walks on other reference
  sequences
- No direction and no type column. A reader derives them:
  `leaveStrand ≠ rejoinStrand` is a strand switch; otherwise, for a `+`
  leave the haplotype jumps back when `rejoinPos < leavePos`, and for a
  `-` leave when `rejoinPos > leavePos`, over reference it walks again;
  `rejoinPos = leavePos` is own sequence between adjacent steps; any other
  case is a jump forward. `ownBp` 0 is a direct jump; `ownBp` with
  `ownSteps` 0 is sequence the graph lacks
- (path, `hapStart`) identifies a departure; every row of one departure
  repeats the same columns

**Per sequence.** Departures are defined per reference sequence: for S, the
path's steps on S in order, with its steps on any other reference sequence
counted as own sequence. A step on a node the reference passes more than
once takes the pass the file's placement rule gives it

**Which departures get a record.** Between two pieces always; inside one
piece when the stretch between the breakpoints crosses a chunk boundary or
`ownBp` is at least `fold` (65,536 bp by default); across a record gap of a
contig, chained over W lines with no step on S; one-ended at a contig's
ends from `fold`. A smaller departure inside one piece stays in the walk
row, where the reader computes it from the steps

**Filing.** Every record is filed under the sibling sequence
`S~departure` of the same file, as bin-aligned blocks: the stretch
[min(leavePos, rejoinPos), max(...)) cut at aligned multiples of
chunk × 2^{10, 7, 4, 1, 0}, each block clipped to the stretch, so that each
lands in a Tabix bin of about its own extent. An empty stretch is one base
at the breakpoint; a one-ended record is one base at the end it has. Every
record therefore has at least one block, which is the only way a reader
reaches it: there are no copies in the end chunks. A window query on S
never reads them; the reader queries `S~departure` over the same range,
one more request set, and dedups on (path, `hapStart`)

**Header.** `format:i:6`, `fold:i:` and a `placement` line naming the rule
that placed steps on nodes the reference passes more than once, with its
parameters and, when the rule took an input, the input's name and checksum,
such as `placement nearest-pass stay:311`. `skip:i:` and `bypass:i:` are
gone

**Scope of the projection.** Projecting a haplotype onto one reference is
exact where the haplotype keeps the reference's order, and a placement
choice where the reference passes a node more than once. The format doc and
the viewers say so: on a region where the placement is a choice, a viewer
states that placement on the reference is ambiguous there and offers the
graph, haplotype-coordinate or alignment view. Pass counts stay in every
record so a viewer can flag the ambiguity without the header. The placement
rule itself is [ADR 0001](0001-step-placement.md)'s, and a better one for
repeats is an [open problem](../open-problems.md)

**Readers.** graph-walks 5 returns the record as `WalkDeparture`; the
structural-forms `Departure` keeps its name

## Evidence

The spike under nearest-pass placement:

| | MC chr22 GRCh38 | pggb chrY GRCh38 | pggb chr22 GRCh38 |
|---|---|---|---|
| format 5 file | 59.14 MB | 179.77 MB | 1,409 MB |
| format 6 file | +1.0% | +10.2% | +32.6% |
| departures, rows per departure | 25,234, 1.26 | 572,051, 2.83 | 12,458,636, 2.93 |
| (contig, chunk) pairs a contig spans without a piece | 15,698 | 92,912 | 21,465 |
| of those with no block over them | 0 | 0 | 0 |
| rows a 64 kb window returns, median / p95 / max | 4 / 310 / 893 | 114 / 23,452 / 173,357 | 9 / 328,602 / 6,539,739 |
| departure query: requests median / max, bytes p95 / max | 1 / 1, 84 KB / 126 KB | 1 / 5, 598 KB / 1.6 MB | 2 / 5, 6.2 MB / 73 MB |
| walk-chunk query bytes p95 / max | 120 KB / 374 KB | 99 KB / 796 KB | 335 KB / 1.1 MB |

- Own bp and steps agree with an enumeration straight from the GFA
  (`dep.rs`) on every comparable departure of MC chr22 (24,213 jumps and
  insertions) and pggb chrY; the stretches differ only where the
  enumeration reports the gap between the nodes and the record the
  breakpoints
- The rows `tabix` returns for a window are exactly those over it on every
  window of the three graphs. The bytes the index points at include whole
  bins, up to one level over a block's size: nothing on MC, under 2x at p95
  on pggb. Blocks of 16 kb cost three times the rows and more bytes per
  window on both graphs
- Without the per-end chunk a reader cannot find the piece holding a
  departure's own steps: on MC chr22 19,630 of 25,185 leave breakpoints lie
  in a different chunk from the leave piece, where the leave node straddles
  the boundary
- Without the per-sequence definition, a contig that leaves chr22 for a
  random contig and returns leaves a chr22 window inside the excursion
  nothing: 15,051 of pggb chr22's 21,465 absent pairs had no block until the
  spike was changed to it; MC chr22 came out byte-identical
- The prototype's 32-chunk cap left 294 stretches uncovered on MC chr22 and
  24,629 on chrY; its `order` column was the reference's order, not the
  haplotype's: 604 of MC chr22's 685 "backward" jumps were reverse-strand
  contigs going forward
- The `fold` threshold moves about 1,300 records on MC chr22 and 1,150 on
  chrY between 10 kb and 64 kb
- On pggb under nearest-pass placement the file is exact and the content is
  placement: 97% of records have an end on a node the reference passes more
  than once, 87-89% carry 0 own bp, one haplotype has up to 2,065 records
  over one 64 kb window, and only 35.9% of chrY pieces land within 10 kb of
  where Minigraph-Cactus places the same contig position (35.6% in Yp11 and
  Yq11, 50.5% elsewhere). The record needs no change for any placement rule

## Consequences

- graph-walks 5 reads format 6 only: two reads per window, the walk chunks
  and the departure blocks, both fixed by the window; no follow rounds, no
  crossing cap, no direct-jump detection from steps the cut happened to
  read; a departure's own steps are attached from the record's chunk under a
  per-record budget. `WalkSkip`, `WalkCrossing` and `skipsOver` go
- The departure read needs its own budget beside the 8 MB cut-wide byte
  budget, and a cut over budget fails whole, never per haplotype
- A departure inside one piece under `fold`, with an end on a node the
  reference passes more than once, has no pass count anywhere: the reader
  computes it from the steps and the chunk's rows hold no count. This
  occurs on pggb and not on Minigraph-Cactus GRCh38, whose reference passes
  no node twice
- The plugin's synteny lanes take strand per end and the mate span from
  `hapStart` and `ownBp`; `skipCrossings` and `sideCrossings` go;
  `EXPAND_NAMED_MAX` gives way to a per-row expansion threshold.
  jbrowse-components' multi-way header needs a `laneBp` field to say what
  the lane carries. bandage-core draws a departure beside a haplotype's walk
  with its facts, for every haplotype; `deleted`, `deletionBp` and "inside a
  deletion" go, in BandageJS and ggbandage too
- graph-walks 4.x refuses format 6, so BandageJS, ggbandage and the tube map
  keep the format 5 files under their names until they move, and format 6
  files are hosted under new names. The plugin's `walks5_*` fixtures and
  graph-walks' test data are regenerated
- Hosted Minigraph-Cactus walk files are rebuilt under new names. No pggb
  walk files are hosted today, and none ship under nearest-pass placement: a
  pggb chr22 window would read up to 73 MB of departure rows. Nothing hosted
  changes for users until the readers move

## Alternatives rejected

- **A type or direction column:** derivable from the ends, and the
  prototype's `order` was wrong
- **A chunk cap:** leaves windows inside long jumps blank
- **Rows in every chunk of the stretch** (informed-2): +32% on chrY, no
  extra request, and a row per path and chunk which the reader still dedups
- **One row per departure under its whole interval:** a coarse Tabix bin
  every query in the chromosome reads
- **Copies in the end chunks beside the blocks:** a record seen three ways
  in one cut, for nothing the end block does not give
- **A separate departure file:** two indexes to fetch and host for one
  fact
- **Blocks at Tabix's 16 kb level:** three times the rows and more bytes
  per window on both graphs
- **A record with ends on two sequences** (the converged design): no block
  on either sequence over the excursion, 15,051 uncovered pairs on pggb
  chr22
- **A record for every in-piece departure with a multi-pass end:** tens of
  millions on pggb chrY, nearly all between adjacent copies
- **Names:** `bypass`, `skip`, `jump`, `traversal`, `allele`, `gap`;
  `departure` was the only name every arbiter ranked in its top three, and
  the closest prior art is the gap between blocks of a UCSC chain
