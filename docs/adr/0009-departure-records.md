# ADR 0009: One record per departure, and walk rows that name the copy

- **Status:** accepted, 2026-10-31; amended on 2026-11-03 after seventeen
  reviews, see [History](#history). Not ported: [Open before the
  port](#open-before-the-port) comes first
- **Decides:** what a walk file holds for every place a haplotype's path
  does not follow the reference between two of its steps on it, how the
  rows are filed so that any window finds them, which copy of a node a
  walk row's step takes where the reference passes it more than once, and
  how later additions get in without a new format. Walk format 6
- **Measured by:** a writer spike built on HPRC v2.1 Minigraph-Cactus chr22
  and HPRC release 2 pggb chrY and chr22, on GRCh38, with the scripts and
  results in [docs/departures/](../departures/), and simulations over the
  format 5 pggb chrY builds, under [Evidence](#evidence)
- **Supersedes:** [ADR 0006](0006-walks-skip-rows.md)'s `skip` rows, and
  the decoding rules' own choice of copy in
  [walks-format.md](../walks-format.md#decoding-a-walk-row)

## Context

- Format 5 writes a `skip` row only where a path has no piece in a chunk,
  with the stretch and nothing else: no own sequence, no strand, no pass
  counts, and none at all for a stretch over 32 chunks. graph-walks then
  reconstructs what it can from the pieces it happens to read, so a
  haplotype's answer depended on which other haplotypes were kept, and the
  viewers called the result a deletion
- Format 5's decoding rules choose a copy themselves where a chunk's R
  holds a node more than once: a piece starts at R's first copy and a
  route exit lands on the nearest, the later on a tie (`Path::first` and
  `Path::nearest` in `src/routes.rs`). `encode` never reads the placement
  pass, which only picks the chunk. So no placement rule can put a step on
  another copy within a chunk, and on pggb a tenth to a fifth of the steps
  on R in chunks with repeats decode elsewhere than placement put them
- The tools make no variant calls; they state what the data shows. A
  haplotype's answer must not depend on the keep set. A window inside a
  jump of any length must find it from a bounded number of range requests
  near the window. Long own sequence is summarised and fetchable. No
  backwards compatibility. Format 6 breaks every reader anyway, so it aims
  at the ideal format: what it leaves out costs a format 7

## Decision

### The record

One `departure` row per place a path's consecutive steps on one reference
sequence S are not adjacent on S at the passes they took. Fields, plain
integers:

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
  of the chunk the step's piece is filed under
- A one-ended record has `.` in the five columns of the end it lacks: the
  contig has no step on S before the rejoin, or none after the leave, in
  any of its W lines. Its own sequence runs from the contig's first
  record, or to its last
- `hapStart` is where the haplotype's own sequence between the ends starts
  on its contig, right after the leave step; it runs `ownBp` over
  `ownSteps` steps, both 0 for a direct jump. `ownSteps` counts every step
  between the ends, those on other reference sequences included.
  `missingBp` counts the part of `ownBp` no W line of the contig covers:
  the gaps between records only, never the records chained over. `xb`
  counts the part the path walks on other reference sequences, those
  records' steps included. One-ended records count all three the same way
- `fragStart` is the W line of the leave step, or of the rejoin step for a
  record with no leave end
- No direction and no type column. A reader derives them:
  `leaveStrand ≠ rejoinStrand` is a strand switch; otherwise, for a `+`
  leave the haplotype jumps back when `rejoinPos < leavePos`, and for a
  `-` leave when `rejoinPos > leavePos`, over reference it walks again;
  `rejoinPos = leavePos` is own sequence between adjacent steps; any other
  case is a jump forward. `ownBp` 0 is a direct jump; `missingBp` above 0
  is sequence the graph lacks
- Two consecutive steps on S are adjacent, and have no record, when
  `ownSteps` and `ownBp` are 0, the strands are equal and
  `leavePos = rejoinPos`
- Every row of one departure repeats the same columns, and a reader
  dedups on all of them but `a` and `b`

### Positions

Departures are defined per reference sequence: for S, the path's steps on
S in order, with its steps on any other reference sequence counted as own
sequence.

- A step's position on S is the pass the placement rule gives it, or the
  stay's re-placement below, and its walk row states that pass, so readers
  never choose a copy. A step the placement leaves off S is route
  interior, even where the chunk's R holds its node, and own sequence on
  every reference sequence, so `xb` counts only steps placed on another
  one
- The writer fails the build if any row decodes to another (handle,
  position) than the one it placed
- **The stay** keeps a run home only where each of its steps on a node the
  home chunk's R holds has a copy there within `stay` bp of the offset
  `visits_along` predicts for it from the run's previous step, and
  re-places the step on the nearest such copy. A step on a node the home
  chunk's R lacks is route interior. Any other run moves the piece on, so
  the stay moves no step more than `stay` bp from its prediction
- The stay absorbs no run holding a node the reference passes once, under
  every placement rule, which amends ADR 0001's rule 2 and [ADR
  0003](0003-long-node-lookback.md)'s guard. Under nearest-pass placement
  own sequence therefore holds no such node, and the build asserts it.
  Other rules, such as alignment-guided placement, may place such a node
  off S, and readers rely on neither
- The reference's own paths lie at their offsets and have no departures
- [ADR 0001](0001-step-placement.md)'s rule 3 places route-interior nodes
  at a `ref` row's position for drawing only, never a haplotype's steps
- Departures therefore depend on the placement rule and `stay`, both in
  the header, and on `chunk` only through the stay. Which of them get a
  record, and their blocks, also depend on `chunk`

### Walk rows name the copy

Where a chunk's R holds a node more than once, a walk row names the copy
a step takes wherever it is not the default:

```
walk      ... start[@k] end choices ...              choices token: t[:n][@k]
abridged  ... start[@k] end[@k] detail pages ...
```

- `k` counts the chunk's R positions holding the node, from 0, in a
  detail record too. The writer writes `@k` only where it differs from
  the default, so a file has one encoding
- On `start` the default is R's first copy. On a choice token `@k` names
  the copy the exit lands on as the walk takes the route, flip applied;
  its default is the copy nearest the entry's R index, the later on a
  tie. A route with no entry or no exit takes no `@k`: a leading route's
  exit is `start`, which `start@k` names, and a trailing route has no
  exit. On an abridged row's `end` the default is the copy nearest
  `start`'s
- The encoder continues along R only where R's next position is the
  step's pass, and otherwise takes a route, with an empty interior if need
  be. It writes step counts `:n` wherever the row decoded without them
  differs from the steps in handle or in position: handles alone pass a
  row whose positions are wrong, as where a haplotype holds one more unit
  of a looping array than R
- A file on a reference that passes every node once writes no `@`
- The decoding rules in [walks-format.md](../walks-format.md#decoding-a-walk-row)
  take `@k` in place of R's first copy and the nearest copy

### Pass counts in the walk read

Each `ref` row lists, over its own steps, the runs on nodes the reference
passes more than once, as `mp:Z:i,n,count;...`: from the row's step `i`,
counted from 0, `n` steps whose nodes the reference's paths pass `count`
times in all, as `leavePasses` counts. A row with no such run has no tag.
So a viewer can say where a haplotype's placement is a choice, departure
or not.

### Which departures get a record

Between two pieces always; inside one piece when the stretch between the
breakpoints crosses a chunk boundary or `ownBp` is at least `recordbp`
(65,536 bp by default); across a record gap of a contig, chained over W
lines with no step on S; one-ended at a contig's ends from `recordbp`. A
reader computes every departure inside a piece from its steps, so
`recordbp` is the writer's choice; where a record repeats a departure the
reader computed, the reader keeps the record, matched on (`path`,
`hapStart`, `leavePos`, `rejoinPos`).

### What a reader is promised

The walk read and the departure read over the same extent give together
every departure over it. The extent is what the cut draws, the window and
its context.

- The walk read gives the departures inside its pieces
- A query on `S~departure` returns every record whose stretch covers a
  base of the extent where its path has no piece; every record with an
  end block in the extent; and every strand switch and back jump both of
  whose ends lie on nodes the reference passes once, over its whole
  stretch. A `crowd` row stands in for each record it counts, over its
  run
- A piece covers the bases of S its steps lie on. An abridged row covers
  the bases from the lower of its `start` and `end` positions to the end
  of the higher one's node, which is exactly what the writer subtracts
- Elsewhere, where the path has a piece, the piece is the answer and a
  departure passing over it may be missing
- A file holding more blocks than this is still valid, so the writer's
  filing can change without a reader release

### Filing

Every record is filed under the sibling sequence `S~departure` of the same
file, as bin-aligned blocks, which are the only way a reader reaches it:
there are no copies in the end chunks, and a window query on S never reads
them.

- **End blocks:** one base of each end's node beside its breakpoint,
  [bp − 1, bp) where the breakpoint is the node's end and [bp, bp + 1)
  where it is its start; for a node of 0 bp, [bp, bp + 1). Each is
  clipped to S, and at S's end is [len − 1, len). An empty stretch has the
  leave end's block only, and a one-ended record its one end's block.
  Every record therefore has at least one block
- **Interior blocks:** the stretch [min(leavePos, rejoinPos), max(...))
  less the bases the path's own pieces cover; for a strand switch or back
  jump with both ends on nodes the reference passes once, the whole
  stretch. On Minigraph-Cactus those are real duplications and
  inversions, few, and a window inside one states its extent
- **Cutting:** every run of interior bases is cut at aligned multiples of
  the index's own bin sizes, 2^26, 2^23, 2^20 and 2^17 bp, whatever
  `--chunk` is, each block clipped to the run, so that each lands in a
  Tabix bin no larger than its own size. The CSI index the writer uses
  past 512 Mb has bins at the same sizes
- **Crowds:** for each path, take each maximal run of bases where at least
  one of its departures passes over and none of its pieces does. When more
  than K of its departures pass over any one base of the run, the run's
  interior blocks, whole-stretch ones included, give way to `crowd` rows
  over the same blocks, and the departures' end blocks stay:

  ```
  seq~departure  a  b  crowd  path fragStart n minPos maxPos detail pages
  ```

  The row states that the path has no piece over [a, b), that `n` of its
  departures pass over some of the run, and that their stretches lie in
  [`minPos`, `maxPos`). The `n` records in full are detail record
  `detail` of the sequence `S~crowd`. K is the header's `crowdmax:i:`. A
  `crowd` row is a count and extents, decided per path from the file
  alone, so it calls nothing and depends on no keep set. Readers dedup
  `crowd` rows on (`path`, `fragStart`, `detail`)
- **Pages:** every detail record, an abridged one under `S~cs` or a crowd
  one under `S~crowd`, is numbered by its first page: its rows lie from
  `detail × 16384`, at most the header's `page:i:` rows a page, and its
  later pages at the following multiples of 16384, so the next record's
  `detail` is this one's plus `pages`. The row pointing at it states
  `pages`. So no expansion reads more than `page` rows a request

### Reference holes

A reference whose sequence has gaps between its W lines, such as a
clipped haplotype used as the reference, writes a `#hole  seq  start  end`
header line for each gap, and for the stretch before its first W line when
that starts past 0, as `#long` does for long nodes. A hole is not a
departure of any haplotype. Positions on S compare with holes removed: two
steps either side of a hole with nothing between them are adjacent and
have no record, and the direction rules read a stretch less the holes it
overlaps. A window inside a hole states that the reference has no sequence
there.

### Header

```
#walks	format:i:6	chunk:i:	maxnode:i:	stay:i:	abridge:i:	abridgebytes:i:	recordbp:i:	crowdmax:i:	page:i:	kinds:Z:ref,nodes,route,walk,abridged,departure,crowd
#placement	nearest-pass
#reference	GRCh38
#haplotype	...
#long	...
#hole	...
```

- `kinds:Z:` lists, comma-separated, every row kind the file holds,
  detail records included. `skip:i:` and `bypass:i:` are gone
- `#placement` names the rule that placed steps on nodes the reference
  passes more than once, then its parameters as typed tags, and, when the
  rule took an input, `input:Z:` with the input's name and `sha256:Z:`
  with its checksum

### Extension rules

These let later additions in without a format change:

- A reader refuses a file whose `kinds:Z:` names a row kind it doesn't
  know, and reads every kind it lists. A new row kind is therefore a
  format change in all but number, and later additions are tags, siblings
  or files instead
- A reader ignores tags it doesn't know, on every row kind, in any order
  after the fixed columns
- A reader reads only the sequences S, `S~cs`, `S~departure` and
  `S~crowd`, and ignores any other sibling
- One file holds one placement. A second placement of the same graph, such
  as every copy of a repeat, is another file with its own `#placement`
  line, so no row needs a placement key

So a per-end placement class, the sequence an excursion goes to, own bp
the file does not hold and the chunks of an excursion's own steps are
tags; a map of the reference's own copies is a sibling; secondary
placements are files.

### Scope of the projection

Projecting a haplotype onto one reference is exact where the haplotype
keeps the reference's order, and a placement choice where the reference
passes a node more than once. The format doc and the viewers say so: on a
region where the placement is a choice, a viewer states that placement on
the reference is ambiguous there and offers the graph,
haplotype-coordinate or alignment view. Pass counts stay in every record,
and `mp` gives them in the walk read, so a viewer can flag the ambiguity
without the header. The placement rule itself is [ADR
0001](0001-step-placement.md)'s, and a better one for repeats is an [open
problem](../open-problems.md).

### Readers

graph-walks 5 returns the record as `WalkDeparture`; the structural-forms
`Departure` keeps its name.

## Open before the port

- **The rebuild on ada** of MC chr22, pggb chr22 under nearest-pass and
  alignment-guided placement, and pggb chrY, with this record, `@k`, `mp`,
  pages and the filing above. Compare whole-stretch filing against it,
  with `crowd` at K 4 and K 8. Over every window, at 64 kb and at 1 bp,
  with end and interior blocks counted apart:
  - rows, bytes and requests the way @gmod/tabix reads them (it merges
    reads only up to 5 MB)
  - bases with a departure over them and neither a piece, a block nor a
    computed departure, which must be 0
  - the 130,149-row window of pggb chr22 under alignment-guided placement,
    broken down
  - that Minigraph-Cactus writes no `crowd` row
- **Positions, in the same rebuild,** from the writer itself: carry each
  step's `visits_along` pass into the pieces, decode each row to R
  positions after the round-trip check, and count per row the steps on R,
  those in chunks with repeats, those whose pass differs from the decoded
  position, those the stay kept, starts not on the first copy and exits
  not on the nearest. Then the `@k` and `mp` bytes on pggb chr22 and on
  Minigraph-Cactus CHM13, `@k` written only where it differs against
  written on every node R holds more than once, which would let readers
  drop the nearest rule; and the pieces the stay's new rule changes
- **The rest of the rebuild:** the number of `#hole` lines for HG002#1,
  against the first BGZF block the header should fit; distinct
  `leaveChunk`s per window; the `.tbi` size; the leave-chunk measurement
  below, with its script saved; the `dep.rs` mismatches split by field; a
  check that every `dep.rs` departure without a record lies inside one
  piece; `pggbY.audit.txt` in full
- **`recordbp`:** whether any reader needs records inside a piece once
  every reader computes in-piece departures from the steps
- **The names** `crowd`, `crowdmax`, `recordbp`, `page`, `kinds` and
  `#placement`, before the port writes them

## Evidence

### The spike

Under nearest-pass placement. Its record lacks `missingBp`, `leaveChunk`
and `rejoinChunk`, takes positions from neither `@k` nor the decoder,
files whole stretches and cuts blocks down to 64 kb, so these figures
bound format 6's sizes in neither direction. The chrY rows per window come
from the spike's first build, and its departure query costs may too; the
rest of its column is from the second.

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
  breakpoints. The check matches records on (path, `hapStart`) and puts
  stretch, strand and own-bp disagreements in one bucket, so it tests the
  arithmetic more than placement or completeness
- The rows `tabix` returns for a window are exactly those over it on every
  window of the three graphs; pggb chr22's "every window" is 97 sampled
  ones. The bytes the index points at include whole bins, up to one level
  over a block's size: nothing on MC, under 2x at p95 on pggb. Blocks of
  16 kb cost 3.3 times the rows on MC and 2.2 times on chrY, against the
  spike's 64 kb blocks
- On MC chr22 19,630 of 25,185 leave breakpoints lie in a different chunk
  from the leave piece, against 1,254 rejoin breakpoints, so `leaveChunk`
  is needed. The cause is not established: a leave node straddling the
  boundary explains at most 1.6% at `maxnode:i:1024` (1,024 of 65,536
  bp), and 314 lie in the chunk before. No saved script makes this
  measurement
- Without the per-sequence definition, a contig that leaves chr22 for a
  random contig and returns leaves a chr22 window inside the excursion
  nothing: 15,051 of pggb chr22's 21,465 absent pairs had no block until
  the spike was changed to it; MC chr22 came out byte-identical
- The prototype's 32-chunk cap left 294 stretches uncovered on MC chr22
  and 24,629 on chrY. Its `order` column was the reference's order, not
  the haplotype's. The breakdown the notes give for MC chr22's 685
  "backward" jumps, 604 reverse-strand contigs going forward, 406 strand
  switches and 8 backs, sums to 1,018 and is not to be cited; the 406 and
  8 are exactly the split of the 414 `dep.rs` mismatches
- The spike's `fold`, now `recordbp`, moves about 1,300 records on MC
  chr22 and 1,150 on chrY between 10 kb and 64 kb
- On pggb under nearest-pass placement the content is placement: 97% of
  records have an end on a node the reference passes more than once,
  87-89% carry 0 own bp, one haplotype has up to 2,065 records over one
  64 kb window, and only 35.9% of chrY pieces land within 10 kb of where
  Minigraph-Cactus places the same contig position (35.6% in Yp11 and
  Yq11, 50.5% elsewhere). Under alignment-guided placement 88% of pggb
  chr22's 303,171 records still have an end on a node the reference
  passes more than once, 81% carry 0 own bp, and 63% are back jumps or
  strand switches
- Records inside a piece were 537 of MC chr22's, 320,644 of pggb chrY's
  (nearly all hops under the stay rule, by the spike report) and 7,782,294
  of pggb chr22's. Under this Decision most of the pggb ones should go;
  that is inferred, and the rebuild measures it

### Filing, by a proxy

On a local format 5 build of pggb chrY, the spike's baseline, at chunk
granularity, under nearest-pass placement, over all 869 windows, counting
a join between a path's pieces in chunks that are not adjacent as a
departure, leaving out departures inside one piece:

| filing | rows per 64 kb window, p95 | max |
|---|---|---|
| whole stretch | 17,404 | 37,228 |
| less the path's pieces, exact query | 5,160 | 15,521 |
| less the path's chunks, chunk-aligned query | 7,269 | 21,908 |

- In the densest windows most rows are end blocks, which grow with the
  pieces, so they cost about what the walk read does
- Over runs where the path has no piece, one contig gave up to 229 rows in
  one chunk and a window up to 6,559, which one row per path takes to 258.
  A contig ping-ponging between copies far apart, and satellite contigs
  placed off the reference, are bounded only by `crowd`
- Leaving out whole chunks where the path has a piece breaks coverage
  under an exact query: a piece over [64k, 70k) and a jump forward over
  [70k, 190k) leave a window at 100k with nothing. With a chunk-aligned
  query instead it read about 60,000 rows in the TSPY window against
  45,000 for whole stretches
- Filing strand switches and back jumps at their ends only breaks
  coverage: a contig on [50, 60) that jumps back to [0, 10) crosses 30
  only by the jump
- The reader rule the Decision keeps drops only departures over a path's
  own pieces, which no current reader uses: the plugin's synteny lanes
  keep a skip only for a haplotype with no walk in the window
  (`WalkTabixSyntenyAdapter.ts`, `!walking.has`), and graph-walks'
  `skipsOver` keeps a skip row's jump only for a path the cut holds no
  walk of, beside the crossings it finds between the steps it read
- On Minigraph-Cactus chr22 the worst window holds 893 departure rows over
  464 haplotypes, so `crowd` at K 8 is expected never to appear there

### Copies

A simulation over the local format 5 pggb chrY builds re-encoded every
walk row with `@k` in the chunks whose R holds a node twice (655 of 1,071
chunks on GRCh38, 2,553 of 2,952 on CHM13), against a port of
`visits_along` restarted at each piece and limited to the chunk's R:

| | pggb chrY GRCh38 | pggb chrY CHM13 |
|---|---|---|
| steps on R in those chunks the decoder places elsewhere | 7.7% | 16.3% |
| walk rows with such a step | 65,242 | 230,121 |
| `start@k` written | 19,362 | 101,310 |
| exit `@k` written, of all choices | 469,256 of 7.69 M | 614,275 of 8.96 M |
| those chunks' walk and route rows, zlib | +0.60% | +0.50% |

- Every row decoded back to its steps and its positions. On a reference
  that passes every node once the cost is 0 by construction
- These are lower bounds. An audit ran an exact port of `visits_along`
  over whole paths, three on GRCh38 and two on CHM13: the decoder places
  elsewhere 12.9% of such steps on the GRCh38 three, and 5.4% and 19.1%
  on the CHM13 two,
  against the restarted port's 9.0%, 4.8% and 15.0%. Much of the gap is
  steps the stay kept, which the restarted port chained inside the home
  chunk. So roughly 9-11% on GRCh38 and 18-20% on CHM13, and the `@k`
  bytes perhaps +0.7-0.9% of those rows, under 0.5% of the file, which is
  extrapolated
- In HG002's piece 183 in the TSPY array, the decoder starts on R's copy
  at 9,344,124, where `visits_along` predicts and takes the copy at
  9,364,418: the whole 1,288-step run is shifted by one 20.3 kb unit
- Reference `>1>2>3>2>3>4` with 10 bp nodes, haplotype `>3>4`: format 5
  starts at R's first `>3` and exits to `>4` at 50, a 20 bp forward jump,
  though the haplotype matches the second copy. Format 6 writes `start`
  as `6@1` and needs no route
- Reference `>2>1>1>1>3` with 2 bp copies of node 1, haplotype holding one
  more `>1`: format 5 writes no step counts, since the handles round-trip,
  but decodes the extra unit at the array's start. A brute-force check of
  200,000 random pairs found 355 such rows, all where R holds a node at
  adjacent positions, and with counts written wherever positions differ
  every one decoded exactly
- A stay that re-placed a kept step on the home chunk's nearest copy
  without a bound turned a step 1 bp from its prediction into a back jump
  and a forward jump of 8 bp at `--chunk 10`, up to a chunk at 64 kb, so
  the stay is bounded by `stay`

## Consequences

- graph-walks 5 reads format 6 only: two reads per cut, the walk chunks
  and the departure blocks, both fixed by the cut's extent; no follow
  rounds for coverage, no crossing cap, no direct-jump detection from
  steps the cut happened to read. It takes copies from `@k` and never
  chooses one, reads `crowd` rows and expands detail records page by page
  from its first release, and takes a departure over a base where the path
  has a piece from that piece, but for the strand switches and back jumps
  filed whole. It exports one function that derives a departure's
  direction and type, holes included, so the consumers don't each
  re-derive them. `WalkSkip`, `WalkCrossing` and `skipsOver` go
- Attaching a departure's own steps costs one more read per distinct
  `leaveChunk` outside the read range. Which records get their steps
  attached follows from the record alone, such as `ownSteps` above 0 and
  `ownBp` under the expansion threshold, never from budget order, so no
  haplotype's answer depends on the others. Own steps on other reference
  sequences are not in `leaveChunk`'s piece and are reached by following
  `nx`, outside the cut's two reads
- The departure read has its own budget beside the 8 MB cut-wide byte
  budget, and a cut over budget fails whole, never per haplotype. Its
  error is its own: zooming in does not lower the departure read, so it
  never shows the walk budget's "zoom in" notice
- The `tables.skips` hand-off from graph-walks to bandage-core is
  optional, so graph-walks 5 under bandage-core 12 would drop every
  departure without an error. Its successor is required, and each
  consumer takes both in one bump
- graph-walks 4.x refused a format 6 file by asking for a rebuild with
  gfa-to-tabix 1.4 or later. graph-walks a51b7bf asks for a newer viewer
  instead; it is to be released as 4.6.1 before any format 6 file exists
- The plugin's first format 6 release bundles graph-walks 4 beside 5 under
  an alias and picks by the header's `format`, with one bandage-core. A
  format 5 file draws its pieces, drops its skip rows and says to rebuild
  with gfa-to-tabix 3.0 to see departures. The next plugin release drops
  graph-walks 4. Every hosted config loads the plugin from `/latest/`, so
  without this the release would stop every format 5 file the day it is
  rehosted, users' own builds included
- The plugin's synteny lanes take strand per end and the mate span from
  `hapStart` and `ownBp`; `skipCrossings` and `sideCrossings` go;
  `EXPAND_NAMED_MAX` gives way to a per-row expansion threshold.
  jbrowse-components' multi-way header has `laneBp` on `LaneChange`
  already; `WindowDeletion` and `Placeless` need a lane-side bp to say
  what the lane carries, and the header a duplication kind. bandage-core
  draws a departure beside a haplotype's walk with its facts, for every
  haplotype; `deleted`, `deletionBp` and "inside a deletion" go, in
  BandageJS, ggbandage and the plugin's `pane/walkRowViews.ts` too
- BandageJS, ggbandage and the tube map pin graph-walks 4, keep the format
  5 files under their names until they move, and format 6 files are
  hosted under new names. jb2hubs pins graph-walks and bandage-core and
  names the format 5 file, and moves with the plugin. The plugin's
  `walks5_*` fixtures and graph-walks' test data are regenerated, and the
  pggb E. coli walk files in ggbandage, BandageJS and the tube map are
  rebuilt
- Hosted Minigraph-Cactus walk files are rebuilt under new names. No pggb
  walk files are hosted today; whether pggb ships, and under which
  placement, waits on the rebuild. By estimate, alignment-guided placement
  would keep pggb chr22's departure rows under 1% of the file and a
  window's departure read under 1.4 MB, and nearest pass would not be
  pleasant to view
- [walks-format.md](../walks-format.md) documents format 5 until the port,
  which rewrites it for format 6

## History

- **2026-10-31, accepted.** Four designs, two of them blind, converged on
  one record with each end stated on its own; a writer spike built it and
  added `leaveChunk`, `rejoinChunk`, `missingBp` and the per-sequence
  definition
- **2026-11-01, review.** The spike's sizes came from a narrower record;
  showing every copy would need a placement key; filing back jumps and
  strand switches only at their ends was never weighed; chrY's rows per
  window and the 2,065 records were not in the results; the `dep.rs`
  check left out 414 mismatches
- **2026-11-03, first round,** six reviews (evidence, semantics, filing,
  pggb, a blind design, consumers) and one of the amendment:
  - positions from the decoded row rather than the placement pass, since
    `stay_home` moves only a step's chunk and the spike's records and rows
    stated two projections; superseded in the third round
  - blocks at the index's bin sizes rather than `chunk << k`, which put
    blocks in the 512 Mb bin at `--chunk 100000`
  - end blocks on the end's own node, since the spike's [bp, bp + 1) lay
    past the node and, at a contig overhanging S's end, past S
  - `#hole` lines, the haplotype-reference handoff's request
  - definitions of one-ended records, `missingBp` and `xb` across chained
    gaps, adjacency and the key
  - evidence corrections: the leave-chunk cause, the 604/685 breakdown,
    the chrY build mix
- **2026-11-03, second round,** two adversarial reviews:
  - positions from the decoder itself, since a fuzzed port of `encode`
    and the decoding rules disagreed on 343 of 1.8 M rows; superseded
  - the stay absorbs no node the reference passes once
  - the reader promise and filing less the path's own pieces, with a
    summary row then named `passes`, and the departure query over the
    window exactly; the extent became the cut's in the third round
- **2026-11-03, third round,** five reviews aiming at the ideal format
  (copy naming, a compromise audit, a blind design, the ideal viewer, the
  ideal pggb end state), then three of the amendment (an attack on `@k`,
  consistency, an audit of the copy simulation):
  - walk rows name the copy, since the decoder's own choice made it the
    projection; four of the five reached it on their own
  - the stay bounded by `stay` and re-placing on the home copy, counts
    written wherever positions differ, and `@k` defaults for every token
  - the extension rules, with "one file, one placement" in place of a
    placement key
  - whole-stretch filing for strand switches and back jumps with both
    ends on nodes passed once; `mp` on `ref` rows; the promise counting
    the walk read's departures inside pieces, which the second round's
    contradicted; the cut's extent; pages; the whole-record dedup key
  - `passes` renamed `crowd` and `fold` renamed `recordbp`, since
    `passes` named a row, a column and a header and `fold` names the
    index's coarse tier

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
- **Blocks at Tabix's 16 kb level:** 2.2 to 3.3 times the rows of the
  spike's 64 kb blocks
- **A record with ends on two sequences** (the converged design): no block
  on either sequence over the excursion, 15,051 uncovered pairs on pggb
  chr22
- **A record for every in-piece departure with a multi-pass end:** tens of
  millions on pggb chrY, nearly all between adjacent copies
- **Positions from the decoder:** the decoder's choice of copy became the
  projection, and no placement rule could change it within a chunk
- **Filing whole stretches for every record:** 3.4 times the rows at p95
  on chrY by the proxy, for departures over the path's own pieces that no
  reader uses; kept only for strand switches and back jumps with both
  ends on nodes passed once
- **Leaving out whole chunks where the path has a piece, or filing back
  jumps and strand switches at their ends only:** both break coverage
- **A placement key on every row:** one file holds one placement instead
- **Walk rows by position deltas into R in place of handles,** from the
  blind design: exact positions too, but `@k` gives them at 0 bytes on
  Minigraph-Cactus without a new row syntax
- **Summarising departures inside the walk row rather than abridging a
  path per chunk:** abridging stays [ADR 0004](0004-abridged-detours.md)'s,
  though which paths a chunk abridges depends on the chunk's other paths;
  it does not depend on the keep set
- **Names:** `bypass`, `skip`, `jump`, `traversal`, `allele`, `gap`;
  `departure` was the only name every arbiter ranked in its top three, and
  the closest prior art is the gap between blocks of a UCSC chain
