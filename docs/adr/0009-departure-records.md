# ADR 0009: One record per departure, filed as blocks under a sibling sequence

- **Status:** accepted, 2026-10-31; amended 2026-11-03 after a second
  review and again after two more, see [Amendments of
  2026-11-03](#amendments-of-2026-11-03). Not
  ported: the items under the second round's "Open before the port" come
  first
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
  of the chunk the step's piece is filed under. A one-ended record has `.`
  in the five columns of the end it lacks: the contig has no step on S
  before the rejoin, or none after the leave, in any of its W lines. Its
  own sequence runs from the contig's first record, or to its last, with
  `missingBp` and `xb` counted as for a two-ended record
- `hapStart` is where the haplotype's own sequence between the ends starts
  on its contig, right after the leave step; it runs `ownBp` over
  `ownSteps` steps, both 0 for a direct jump. `ownSteps` counts every step
  between the ends, those on other reference sequences included.
  `missingBp` counts the part of `ownBp` no W line of the contig covers:
  the gaps between records only, never the records chained over. `xb`
  counts the part the path walks on other reference sequences, those
  records' steps included
- No direction and no type column. A reader derives them:
  `leaveStrand ≠ rejoinStrand` is a strand switch; otherwise, for a `+`
  leave the haplotype jumps back when `rejoinPos < leavePos`, and for a
  `-` leave when `rejoinPos > leavePos`, over reference it walks again;
  `rejoinPos = leavePos` is own sequence between adjacent steps; any other
  case is a jump forward. `ownBp` 0 is a direct jump; `missingBp` above 0
  is sequence the graph lacks
- Two consecutive steps on S are adjacent, and have no record, when
  `ownSteps` is 0, the strands are equal and `leavePos = rejoinPos`
- (path, `hapStart`) identifies a departure within one `S~departure`;
  every row of one departure repeats the same columns. A zero-length
  segment can give two departures one `hapStart`: the port either refuses
  such segments under `--walks` or widens the key

**Per sequence.** Departures are defined per reference sequence: for S, the
path's steps on S in order, with its steps on any other reference sequence
counted as own sequence.

- A step's position on S is the position in R that [the decoding
  rules](../walks-format.md#decoding-a-walk-row) give it when its walk row,
  or its detail record's row, is decoded against its chunk's R, step
  counts included. A step the row holds as route interior is own sequence
  on every reference sequence, so `xb` counts only steps decoded on
  another one. The placement rule picks only the chunk a step is filed
  under. The records and the walk rows therefore state one projection,
  including after the stay rule has moved a run to another chunk
- The writer takes positions from the decoder itself, never from the
  encoder's state or the placement pass: where R passes a node twice in a
  row the two can differ while the steps agree. A reader computing a
  departure inside a piece uses the same positions
- The reference's own paths lie at their offsets and have no departures
- [ADR 0001](0001-step-placement.md)'s rule 3 places route-interior nodes
  at a `ref` row's position for drawing only, never a haplotype's steps
- The stay absorbs no run holding a node the reference passes once, which
  amends ADR 0001's rule 2 and [ADR 0003](0003-long-node-lookback.md)'s
  guard, so own sequence never holds a node the reference passes once. The
  build asserts it. Nothing changes on a reference that passes every node
  once, where the stay never absorbs a run
- A piece starts at R's first copy of its first node, so a piece whose
  first step lies on a later copy shows a forward jump over the earlier
  ones. This never occurs on a reference that passes every node once. The
  rebuild counts it; naming the copy in the walk row, such as `start@k`,
  would be a walk-row format change and waits on that count
- Departures therefore depend on the placement rule, `stay` and `chunk`,
  all three stated in the header

**Which departures get a record.** Between two pieces always; inside one
piece when the stretch between the breakpoints crosses a chunk boundary or
`ownBp` is at least `fold` (65,536 bp by default); across a record gap of a
contig, chained over W lines with no step on S; one-ended at a contig's
ends from `fold`. A smaller departure inside one piece stays in the walk
row, where the reader computes it from the steps

**What a reader is promised.** A window query on `S~departure` returns
every departure whose stretch covers a base of the window where its path
has no piece, and every departure with an end in the window. A piece
covers the bases of S its decoded steps lie on, and an abridged row its
start to its end. Where the path has a piece, the piece is the answer and
a departure passing over it may be missing. The reader queries
`S~departure` over the window exactly, one more request set, and dedups on
(path, `hapStart`). A file holding more blocks than this is still valid,
so the writer's filing can change without a reader release

**Filing.** Every record is filed under the sibling sequence
`S~departure` of the same file, as bin-aligned blocks, which are the only
way a reader reaches it: there are no copies in the end chunks, and a
window query on S never reads them.

- **End blocks:** one base of each end's node beside its breakpoint,
  [bp − 1, bp) where the breakpoint is the node's end and [bp, bp + 1)
  where it is its start, so that no block lies past the end of S. An empty
  stretch has the leave end's block only. Every record therefore has at
  least one block
- **Interior blocks:** the stretch [min(leavePos, rejoinPos), max(...))
  less the bases the path's own pieces cover, in the sense above
- **Cutting:** every run of interior bases is cut at aligned multiples of
  the index's own bin sizes, 2^26, 2^23, 2^20 and 2^17 bp, whatever
  `--chunk` is, each block clipped to the run, so that each lands in a
  Tabix bin no larger than its own size. The CSI index the writer uses
  past 512 Mb has bins at the same sizes
- **Summary:** for each path, take each maximal run of bases where at least
  one of its departures passes over and none of its pieces does. When more
  than K of its departures pass over any one base of the run, the run's
  interior blocks give way to `passes` rows over the same blocks, and the
  departures' end blocks stay:

  ```
  seq~departure  a  b  passes  path fragStart n minPos maxPos detail
  ```

  The row states that the path has no piece over [a, b), that `n` of its
  departures pass over some of the run, and that their stretches lie in
  [`minPos`, `maxPos`). The `n` records in full go to detail record
  `detail`, filed as [ADR 0004](0004-abridged-detours.md)'s are, and a
  reader expands it with one request. K is the header's `passes:i:`. A
  `passes` row is a count and extents, decided per path from the file
  alone, so it calls nothing and depends on no keep set. Readers handle
  the kind from the first format 6 release: one that skipped it would
  silently lose coverage

Filing every stretch whole, as the spike did, meets the same promise with
more rows. Filing back jumps and strand switches at their ends only does
not, and neither does leaving out whole chunks where the path has a piece:
see the [amendments](#amendments-of-2026-11-03-second-round)

**Reference holes.** A reference whose sequence has gaps between its W
lines, such as a clipped haplotype used as the reference, writes a
`#hole  seq  start  end` header line for each gap, and for the stretch
before its first W line when that starts past 0, as `#long` does for long
nodes. A hole is not a departure of any haplotype. Positions on S compare
with holes removed: two steps either side of a hole with nothing between
them are adjacent and have no record, and the direction rules read a
stretch less the holes it overlaps. A window inside a hole states that the
reference has no sequence there

**Header.** `format:i:6`, `fold:i:` and a `placement` line naming the rule
that placed steps on nodes the reference passes more than once, with its
parameters and, when the rule took an input, the input's name and checksum,
such as `placement nearest-pass stay:311`, `passes:i:`, and the `#hole`
lines. `skip:i:` and `bypass:i:` are gone

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

The spike under nearest-pass placement. Its record lacks `missingBp`,
`leaveChunk` and `rejoinChunk`, takes a step's pass from the placement
rule rather than the decoded row, and cuts blocks down to 64 kb, so every
figure below predates the amendments of 2026-11-03 and bounds format 6's
sizes in neither direction: the new columns add bytes, decoded positions
and the coarser finest block remove rows. The chrY rows per window come
from the spike's first build, and its departure query costs may too; the
rest of its column is from the second:

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
  in a different chunk from the leave piece, against 1,254 of 25,185 rejoin
  breakpoints. The cause is not established: a leave node straddling the
  boundary, given before, explains at most 1.6% at `maxnode:i:1024`
  (1,024 of 65,536 bp), and 314 lie in the chunk before. No saved script
  makes this measurement
- Without the per-sequence definition, a contig that leaves chr22 for a
  random contig and returns leaves a chr22 window inside the excursion
  nothing: 15,051 of pggb chr22's 21,465 absent pairs had no block until the
  spike was changed to it; MC chr22 came out byte-identical
- The prototype's 32-chunk cap left 294 stretches uncovered on MC chr22 and
  24,629 on chrY; its `order` column was the reference's order, not the
  haplotype's. The breakdown the notes give for MC chr22's 685 "backward"
  jumps, 604 reverse-strand contigs going forward, 406 strand switches and 8
  backs, sums to 1,018, so its numbers are not to be cited. The 406 and 8
  are exactly the split of the 414 `dep.rs` mismatches, which suggests the
  two lists were run together
- The `fold` threshold moves about 1,300 records on MC chr22 and 1,150 on
  chrY between 10 kb and 64 kb
- On pggb under nearest-pass placement the file is exact and the content is
  placement: 97% of records have an end on a node the reference passes more
  than once, 87-89% carry 0 own bp, one haplotype has up to 2,065 records
  over one 64 kb window, and only 35.9% of chrY pieces land within 10 kb of
  where Minigraph-Cactus places the same contig position (35.6% in Yp11 and
  Yq11, 50.5% elsewhere). The record needs no change for any single-copy
  placement rule tried

## Consequences

- graph-walks 5 reads format 6 only: two reads per window, the walk chunks
  and the departure blocks, both fixed by the window; no follow rounds, no
  crossing cap, no direct-jump detection from steps the cut happened to
  read. Attaching a departure's own steps costs one more read per distinct
  `leaveChunk` outside the read range, which the window does not fix. Which
  records get their steps attached follows from the record alone, such as
  `ownSteps` above 0 and `ownBp` under the expansion threshold, never from
  budget order, so no haplotype's answer depends on the others. Own steps
  on other reference sequences are not in `leaveChunk`'s piece and are
  reached by following `nx`. It reads `passes` rows and expands their
  detail records from its first release, and takes a departure over a base
  where the path has a piece from that piece, not from the departure
  read. `WalkSkip`, `WalkCrossing` and `skipsOver` go
- The departure read needs its own budget beside the 8 MB cut-wide byte
  budget, and a cut over budget fails whole, never per haplotype. Its error
  is its own: zooming in does not lower the departure read, since a 1 bp
  window inside a long jump reads every record over it, so it never shows
  the walk budget's "zoom in" notice
- The `tables.skips` hand-off from graph-walks to bandage-core is
  optional, so graph-walks 5 under bandage-core 12 drops every departure
  without an error: each consumer takes both in one bump
- graph-walks 4.x's refusal tells the reader of a format 6 file to rebuild
  it with gfa-to-tabix 1.4 or later. A 4.x release before gfa-to-tabix 3.0
  says to update the viewer instead
- A departure inside one piece under `fold`, with an end on a node the
  reference passes more than once, has no pass count anywhere: the reader
  computes it from the steps and the chunk's rows hold no count. This
  occurs on pggb and not on Minigraph-Cactus GRCh38, whose reference passes
  no node twice
- The plugin's synteny lanes take strand per end and the mate span from
  `hapStart` and `ownBp`; `skipCrossings` and `sideCrossings` go;
  `EXPAND_NAMED_MAX` gives way to a per-row expansion threshold.
  jbrowse-components' multi-way header has `laneBp` on `LaneChange`
  already; `WindowDeletion` and `Placeless` need a lane-side bp to say what
  the lane carries, which can land before format 6. bandage-core draws a
  departure beside a haplotype's walk with its facts, for every haplotype;
  `deleted`, `deletionBp` and "inside a deletion" go, in BandageJS,
  ggbandage and the plugin's `pane/walkRowViews.ts` too
- graph-walks 4.x refuses format 6, so BandageJS, ggbandage and the tube map
  keep the format 5 files under their names until they move, and format 6
  files are hosted under new names. The plugin's `walks5_*` fixtures and
  graph-walks' test data are regenerated
- Hosted Minigraph-Cactus walk files are rebuilt under new names. No pggb
  walk files are hosted today, and none ship under nearest-pass placement: a
  pggb chr22 window would read up to 73 MB of departure rows. The pggb
  E. coli walk files in ggbandage, BandageJS and the tube map are
  rebuilt under nearest-pass placement, harmless at that size. Nothing
  hosted changes for users until the readers move, but then every hosted
  config moves at once: they load the plugin from `/latest/`, so plugin 9
  stops reading every format 5 file the day it is rehosted, users' own
  builds included, unless it bundles graph-walks 4 beside 5 for one release
  and picks by the header's `format`. jb2hubs pins graph-walks and
  bandage-core and names the format 5 file, and moves with the rest

## Review after acceptance

A review on 2026-11-01 found these gaps. Settle each, or confirm with the
user that it doesn't matter, before format 6 is ported:

- The sizes and byte costs above come from the spike's record. That record
  lacks `missingBp`, `leaveChunk` and `rejoinChunk`, so it understates
  format 6
- "The record needs no change for any placement rule" holds for one copy
  per step. Showing every copy as a second placement would need a placement
  key on the ends, the blocks and the walk rows' links
- Under alignment-guided placement, the working plan for pggb, 88% of
  pggb chr22's 303,171 records still have an end on a node the reference
  passes more than once, and 81% carry 0 own bp. MC chr22 has 25,234
  records
- 63% of those records are back jumps or strand switches. Filing them only
  at their ends was never weighed against filing them over the stretch,
  which the synteny lanes' mate spans use
- The chrY rows per window (114 / 23,452 / 173,357) and the 2,065 records
  per window aren't in [docs/departures/results/](../departures/results/):
  `pggbY.audit.txt` is cut short. "Every window" for pggb chr22 means 97
  sampled windows. The `dep.rs` cross-check left out 414 mismatches
- The placement comparison in open-problems has its own caveats, listed
  there

## Amendments of 2026-11-03

Six independent reviews, each from one side (evidence, the record's
semantics, filing and the reader, pggb, a design drafted before reading
this ADR, and the consumers), kept the record and the sibling filing and
found what follows. None of the 2026-11-01 gaps above had been settled.

**Changed in the Decision above.**

- **A step's position is the decoded one.** `visits_along` sets each
  step's pass, then `stay_home` moves only its chunk (`src/walks.rs`,
  `pass` and `stay_home`), and the spike built records from that pass. The
  reader decodes the walk row by nearest pass, so a record and a row could
  state two projections of one step, and a run the stay had absorbed came
  back as two chunk-crossing records. The encoder treats a step as on R
  only when the chunk's R holds its node (`encode` in `src/routes.rs`), so
  a run the stay absorbed is route interior, and now own sequence. A
  piece's decoded ends then cross a chunk boundary only at a node that
  straddles it, and most records inside a piece should go: 320,644 of
  pggb chrY's 572,051 (nearly all hops under the stay rule, by the spike
  report) and 7,782,294 of pggb chr22's 12,458,636. MC chr22's 537 stay.
  This is inferred; the rebuild measures it. [ADR
  0001](0001-step-placement.md)'s rule 3 still places such interior nodes
  at a `ref` row's position for drawing; for departures they are own
  sequence
- **Blocks follow the index's bin sizes, not the chunk.** The spike cut at
  `chunk << k`, and `--chunk` takes any value: at `--chunk 100000` the
  largest blocks land in the 512 Mb bin every query on the sequence reads.
  The spike's 64 kb level lands in the same 128 kb bins as its 128 kb one
- **End blocks lie on the end's own node.** The spike's [bp, bp + 1) lies
  past the node for a `+` leave or a `-` rejoin, and past the end of S for
  a contig that overhangs S's last node, where no window finds it
- **Reference holes,** which [the haplotype-reference
  handoff](../handoff/2026-11-02-haplotype-references.md) asks format 6 to
  state
- **Definitions:** one-ended records, `missingBp` and `xb` across chained
  record gaps, the adjacency test, the key's scope, and `missingBp` in
  place of "`ownBp` with `ownSteps` 0"

**Open before the port** (as of the first round; the second round below
settles the filing and the summary row and gives the current list).

- **Which stretches get blocks between their ends.** Strand switches and
  back jumps are 76% of pggb chr22's records under nearest-pass placement
  and 63% under alignment-guided placement. Ends alone break coverage: a
  contig on [50, 60) that jumps back to [0, 10) crosses 30 only by the
  jump
- **A per-path summary row** when a path's departures over a window pass a
  bound, after [ADR 0004](0004-abridged-detours.md)'s abridged rows
- **A rebuild of the three graphs with the amended record:** sizes; bytes
  and requests per window, counted the way @gmod/tabix reads them (it
  merges reads only up to 5 MB, so 73 MB is many requests, not 5); distinct
  `leaveChunk`s per window; the `.tbi` size; the leave-chunk measurement,
  with its script saved; the `dep.rs` mismatches split by field; a check
  that every `dep.rs` departure without a record lies inside one piece
  under `fold`; and `pggbY.audit.txt` in full
- **Pass counts for departures inside a piece** with an end on a node the
  reference passes more than once: a `ref`-row tag listing such positions
  of R with their counts, or a plain statement that the reader cannot know
  them
- **Zero-length segments:** they can give two departures one `hapStart`,
  and put an end block off its node, at −1 at the start of S. Refuse them
  under `--walks`, or widen the key and define their end block

**Not changed.** The placement rule stays ADR 0001's, but for the stay's
guard, which the second round amends. Decoding already makes the runs the
stay absorbed own sequence. Extending that to the hop-and-return runs the
stay does not absorb today, and a per-end placement class (once, aligned,
predicted), belong to the placement ADR for pggb.

**Before format 6, with no format change:** graph-walks 4.x's refusal
wording; bandage-core's `WalkSkips` keeping the `offBp` and `offSteps`
graph-walks already sends, in place of `offReferenceBp: 0`; the lane-side
bp in jbrowse-components' header; and a count, on the hosted
Minigraph-Cactus format 5 file, of the (contig, chunk) pairs no piece and
no `skip` row covers, which says how urgent format 6 is. `audit.py` counts
coverage from departure rows only and needs a `skip` mode for it.

## Amendments of 2026-11-03, second round

Two more reviews took the two hardest points of the first round, the
decoded positions and a bound on pggb's departure read, and tried to break
them. Both kept the direction and changed the Decision as follows.

**Positions.** Changes to "Per sequence" above:

- **From the decoder itself.** The reviewer fuzzed ports of `encode` and
  the decoding rules: in 343 of 1.8 M rows the encoder's position and the
  decoded one differ while the steps agree, every time where R passes a
  node twice in a row, as pggb's tandem repeats do. A writer that
  re-implements the on-R test and the nearest pass would drift. The
  writer can decode against each chunk's R at cut time, from the
  first-pass visits, and fail the build if a piece's positions differ from
  what `write_chunk` decodes, as the round-trip check does
- **The stay's guard.** ADR 0003's guard lets the stay absorb a node the
  reference passes once when a reader of the home chunk reaches it. Then
  unambiguous reference sequence becomes own sequence while ADR 0001's
  rule 3 draws the node on the reference. Reference `>1>2>3>4>5>6>9>7>9`
  with 4 bp nodes, haplotype `>1>2>3>4>9>3>4>5>6`, `--chunk 10 --stay
  311`: node 4, passed once at 12-16, sits in the route interior. Under
  `--chunk 20`, or `--stay 0`, it is a step on R
- **A piece's first copy.** Reference `>1>2>3>2>3>4` with 10 bp nodes,
  haplotype `>3>4`: the row starts at R's first `>3`, at 20, and exits to
  `>4` at 50, a 20 bp jump forward, though the haplotype matches the
  reference's second copy exactly. The same happens at contig starts,
  clipped record starts and returns from a jump, wherever R holds the
  first node twice in one chunk. It never happens on Minigraph-Cactus
  GRCh38, and is expected on pggb and CHM13 satellites. Fixing it needs
  the copy named in the walk row, a walk-row format change, so the
  rebuild counts it first
- **What departures depend on:** the placement rule, `stay` and `chunk`.
  A hop-and-return run the stay absorbed is own sequence; the same run at
  `--stay 0` is two records. The stay holds at most `stay` bp of nodes the
  reference passes more than once, and with the guard above no node it
  passes once, so a real excursion to a single-copy paralog always gives
  records

**Filing.** The first round's candidates fail:

- **Leaving out whole chunks where the path has a piece:** a piece over
  [64k, 70k) and a jump forward over [70k, 190k) leave a window at 100k
  with neither a piece nor a block of that path, the bug ADR 0006 fixed. A
  chunk-aligned query repairs that, but then must read the walk query's
  lookback, and in pggb chrY's TSPY window it reads more than the whole
  stretch, about 60,000 rows against 45,000 (by the proxy below). It also
  drops a path's other departures over a chunk where the path has any
  short piece
- **Back jumps and strand switches at their ends only:** breaks coverage,
  as the first round showed

The Decision takes the reviewer's base-level form instead: interior blocks
over the stretch less the bases the path's own pieces cover, and the
`passes` summary row. A window inside a departure where its path has a
piece loses the departure, which no current reader uses: the plugin's
synteny lanes keep a skip only for a haplotype with no walk in the window
(`WalkTabixSyntenyAdapter.ts`, `!walking.has`), and graph-walks'
`skipsOver` keeps a skip row's jump only for a path the cut holds no walk
of, beside the crossings it finds between the steps it read. Exact queries also
settle the lookback question: the departure read covers the window.

A proxy on a local format 5 build of pggb chrY, the spike's baseline, at
chunk granularity,
under nearest-pass placement, over all 869 windows, counting a join
between a path's pieces in chunks that are not adjacent as a departure,
leaving out departures inside one piece:

| filing | rows per 64 kb window, p95 | max |
|---|---|---|
| whole stretch | 17,404 | 37,228 |
| less the path's pieces, exact query | 5,160 | 15,521 |
| less the path's chunks, chunk-aligned query | 7,269 | 21,908 |

- In the densest windows most rows are end blocks, which grow with the
  pieces, so they cost about what the walk read does
- What the pieces don't bound is the rows over runs where the path has no
  piece: up to 229 from one contig in one chunk, 6,559 in one window,
  which one row per path takes to 258. A contig ping-ponging between two
  copies far apart, and satellite contigs placed off the reference, are
  bounded only by `passes`
- The 130,149-row window of pggb chr22 under alignment-guided placement,
  622 contigs at about 209 records each, looks like that case and is
  unmeasured; it was one of 97 sampled windows
- On Minigraph-Cactus chr22 the worst window holds 893 departure rows over
  464 haplotypes, so `passes` at K 8 is expected never to appear there

**Settled for the port:** the reader's promise, the `passes` kind with its
detail record and `passes:i:`, and the exact window query, all in the
first format 6 reader. **Can change without a reader release:** K, how
much of each stretch the writer files beyond the promise, whether abridged
pieces' end blocks go to the abridged detail, and the placement rule.

**Open before the port**, the current list:

- **A rebuild** of MC chr22 and pggb chr22 under both placements, and pggb
  chrY, with the amended record, comparing the whole stretch against the
  Decision's filing with `passes` at K 4 and K 8. Over every window, at
  64 kb and at 1 bp, with end blocks and interior blocks counted apart:
  rows, bytes and requests the way @gmod/tabix reads them (it merges reads
  only up to 5 MB); bases with a departure over them and neither a piece
  nor a block, which must be 0; the 130,149-row window broken down; that
  MC writes no `passes` row
- **In the same rebuild:** runs the old guard absorbed with a node the
  reference passes once, and the pieces refusing them adds; pieces whose
  first step lies on a node R holds more than once, which decides
  `start@k`; records inside a piece, against the spike's; distinct
  `leaveChunk`s per window; the `.tbi` size; the leave-chunk measurement,
  with its script saved; the `dep.rs` mismatches split by field; a check
  that every `dep.rs` departure without a record lies inside one piece
  under `fold`; `pggbY.audit.txt` in full
- **Pass counts for departures inside a piece**, and **zero-length
  segments**, as in the first round

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
