# ADR 0009: One record per departure, and walk rows that name the copy

- **Status:** accepted, 2026-10-31; simplified on 2026-11-03 by the
  rebuild, see [History](#history). Not ported
- **Decides:** what a walk file holds for every place a haplotype's path
  does not follow the reference between two of its steps on it, how the
  records are filed so that any window finds them, which copy of a node a
  walk row's step takes where the reference passes it more than once, and
  how later additions get in without a new format. Walk format 6
- **Measured by:** a prototype writer built on HPRC v2.1
  Minigraph-Cactus chr22 and HPRC release 2 pggb chrY and chr22, on GRCh38,
  under nearest-pass and alignment-guided placement, and an independent
  audit that reads its files as a reader would; scripts and results in
  [docs/departures/](../departures/), under [Evidence](#evidence)
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
  another copy within a chunk: format 5's rules put 3.8% to 8.6% of the
  steps in chunks with repeats on another copy than nearest-pass placement
  chose, and up to 63% under alignment-guided placement
- The tools make no variant calls; they state what the data shows. A
  haplotype's answer must not depend on the keep set. A window inside a
  jump of any length must find it from a bounded number of range requests
  near the window. No backwards compatibility. Format 6 breaks every
  reader anyway, so it aims at the ideal format, and the ideal includes
  being simple: every mechanism below earned its place in the rebuild

## Decision

### The record

One `departure` record for every departure the walk read cannot show:
each place a path's consecutive steps on one reference sequence S are not
adjacent on S at the passes they took and lie in different pieces, and each
end of a contig with own sequence beyond its first or last step on S.
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
  of the chunk the step's piece is filed under
- A one-ended record has `.` in the five columns of the end it lacks: the
  contig has no step on S before the rejoin, or none after the leave, in
  any of its W lines. Its own sequence runs from the contig's first
  record, or to its last, and it is written whenever that is not empty
- `hapStart` is where the haplotype's own sequence between the ends starts
  on its contig, right after the leave step; it runs `ownBp` over
  `ownSteps` steps, both 0 for a direct jump. `ownSteps` counts every step
  between the ends, those on other reference sequences and in W lines with
  no step on S included. `missingBp` counts the part of `ownBp` no W line
  of the contig covers: the gaps between records only. `xb` counts the
  part the path walks on other reference sequences. One-ended records
  count all three the same way
- `fragStart` is the W line of the leave step, or of the rejoin step for a
  record with no leave end
- No direction and no type column. A reader derives them:
  `leaveStrand ≠ rejoinStrand` is a strand switch; otherwise, for a `+`
  leave the haplotype jumps back when `rejoinPos < leavePos`, and for a
  `-` leave when `rejoinPos > leavePos`, over reference it walks again;
  `rejoinPos = leavePos` is own sequence between adjacent steps; any other
  case is a jump forward. `ownBp` 0 is a direct jump; `missingBp` above 0
  is sequence the graph lacks
- Two consecutive steps on S are adjacent, and depart nowhere, when
  `ownSteps` and `ownBp` are 0, the strands are equal and `leavePos =
  rejoinPos`, holes removed (below)
- A departure inside one piece has no record: the reader computes it from
  the piece's steps. A record and a computed departure never stand for the
  same departure, so a reader needs no key to match them
- Every row of one record repeats the same columns, and a reader dedups on
  all of them but `a` and `b`

### Positions

Departures are defined per reference sequence: for S, the path's steps on
S in order, with its steps on any other reference sequence counted as own
sequence.

- A step's position on S is the pass the placement rule gives it, or the
  stay's re-placement below, and its walk row states that pass, so readers
  never choose a copy. A step the placement leaves off S is route
  interior, even where the chunk's R holds its node, and own sequence on
  every reference sequence
- The writer fails the build if any row decodes to another (handle,
  position) than the one it placed
- **The stay** keeps a run home only where it returns there, holds no node
  the reference passes once, and each of its steps on a node the home
  chunk's R holds has a copy there within `stay` bp of the offset
  `visits_along` predicts for it from the run's previous step; it
  re-places the step on the nearest such copy. A step on a node the home
  chunk's R lacks is route interior. Any other run moves the piece on, so
  the stay moves no step more than `stay` bp from its prediction. This
  amends ADR 0001's rule 2 and [ADR 0003](0003-long-node-lookback.md)'s
  guard. Under nearest-pass placement own sequence therefore holds no node
  the reference passes once
- The reference's own paths lie at their offsets and have no departures
- [ADR 0001](0001-step-placement.md)'s rule 3 places route-interior nodes
  at a `ref` row's position for drawing only, never a haplotype's steps
- Departures therefore depend on the placement rule and `stay`, both in
  the header, and on `chunk` through the stay and the pieces

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
  differs from the steps in handle or in position
- A file on a reference that passes every node once writes no `@`
- The decoding rules in [walks-format.md](../walks-format.md#decoding-a-walk-row)
  take `@k` in place of R's first copy and the nearest copy

### What a reader is promised

The walk read and the departure read over the same extent give together
every departure over it, each once. The extent is what the cut draws, the
window and its context.

- The walk read gives every departure inside its pieces. Both steps of one
  lie in the piece's chunk, so the stretch between them lies in that chunk
  and the next, or in a `#long` pass that starts in one of them, and a
  reader of any window over it reads the piece's chunk
- A query on `S~departure` returns every record whose stretch, end bases
  included, overlaps the extent
- A file holding more rows than the filing below is still valid, so the
  filing can change without a reader release

### Filing

Every record is filed under the sibling sequence `S~departure` of the same
file, which is the only way a reader reaches it: there are no copies in the
chunks, and a window query on S never reads it.

- A record covers its stretch, from one base of the first end's node beside
  its breakpoint to one base of the other end's: [bp − 1, bp) where the
  breakpoint is the node's end and [bp, bp + 1) where it is its start, for
  a node of 0 bp [bp, bp + 1), each clipped to S, so at S's end
  [len − 1, len). A one-ended record covers its one end's base
- That extent is cut at aligned multiples of the index's bin sizes, 2^26,
  2^23, 2^20 and 2^17 bp, whatever `--chunk` is, one row per block, so
  that each row lands in a Tabix bin no larger than its own size. The CSI
  index the writer uses past 512 Mb has bins at the same sizes
- Abridged paths' detail records are numbered by their first page: their
  rows lie from `detail × 16384`, at most the header's `page:i:` rows a
  page, and their later pages at the following multiples of 16384, so the
  next record's `detail` is this one's plus `pages`. The `abridged` row
  states `pages`. So no expansion reads more than `page` rows a request

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
#walks	format:i:6	chunk:i:	maxnode:i:	stay:i:	abridge:i:	abridgebytes:i:	page:i:	kinds:Z:ref,nodes,route,walk,abridged,departure
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
- A reader reads only the sequences S, `S~cs` and `S~departure`, and
  ignores any other sibling
- One file holds one placement. A second placement of the same graph, such
  as every copy of a repeat, is another file with its own `#placement`
  line, so no row needs a placement key

The first expected tag is `mp:Z:i,n,count;...` on `ref` rows: from the
row's step `i`, `n` steps whose nodes the reference's paths pass `count`
times, so a viewer can mark where placement on the reference is a choice
without a departure there. It waits for a viewer that draws it.

### Scope of the projection

Projecting a haplotype onto one reference is exact where the haplotype
keeps the reference's order, and a placement choice where the reference
passes a node more than once. The format doc and the viewers say so: on a
region where the placement is a choice, a viewer states that placement on
the reference is ambiguous there and offers the graph, haplotype-coordinate
or alignment view. Records carry pass counts at both ends. The placement
rule itself is [ADR 0001](0001-step-placement.md)'s, and a better one for
repeats is an [open problem](../open-problems.md).

### Readers

graph-walks 5 returns the record as `WalkDeparture`; the structural-forms
`Departure` keeps its name.

## Open before the port

- The writer's peak memory, 36-41 GB on pggb chr22 against the spike's
  21-23 GB: the port holds a record's body once and the steps' positions
  per piece, not per path
- Whether pggb walk files ship, and under which placement; the format does
  not depend on it
- The `walks-format.md` rewrite and the test suite: the prototype's
  `tests/walks.rs` still expects format 5 rows in seven tests
- `#placement`'s `sha256:Z:`, which the prototype does not write

## Evidence

### The rebuild

A prototype of this Decision, read back by an independent audit
([results](../departures/results/rebuild/README.md)). Format 5 files are
the hosted builds of the same graphs; pggb's are under nearest-pass
placement.

| | MC chr22 | pggb chrY | pggb chrY, aligned | pggb chr22 | pggb chr22, aligned |
|---|---|---|---|---|---|
| file | 59.47 MB | 196.6 MB | 219.4 MB | 1.68 GB | 1.81 GB |
| against format 5 | +0.54% | +9.3% | +22.0% | +19.0% | +28.6% |
| records | 24,777 | 425,836 | 30,329 | 5,333,737 | 177,475 |
| departure rows | 31,368 | 1,224,800 | 43,415 | 17,434,823 | 452,672 |
| departures the walk rows hold | 25.97 M | 8.13 M | 10.95 M | 172.3 M | 67.2 M |
| departure rows a 64 kb window returns, p95 / max | 310 / 893 | 18,037 / 104,479 | 265 / 18,562 | not audited | 1,070 / 71,889 \* |
| departure read, requests max, bytes p95 / max | 1, 84 KB / 132 KB | 5, 556 KB / 1.14 MB | 2, 234 KB / 282 KB | not audited | 4, 376 KB / 988 KB \* |
| build, s / peak GB | 52 / 4.1 | 132 / 12.5 | 149 / 12.2 | 587 / 36.3 | 518 / 41.0 |

\* From the whole-stretch variant of the amended Decision, the same filing
with 205 records inside a piece and 1,532 fewer one-ended ones. The audits
of the simplified pggb chr22 files, and of nearest pass on chr22 at all,
were killed when other jobs filled ada's memory; nearest pass on chr22
needs the audit's `--shard`, at about 37 GB a shard.

- The audit decodes every walk row to positions by the decoding rules,
  recomputes every departure, and finds on every graph each record equal
  in every field to a departure that needs one, each departure that needs
  one recorded, every departure inside a piece within the walk read's
  reach, and every base of every record's stretch under one of its rows.
  It agrees with the writer on the test fixtures and on 450 random graphs
  at chunks of 8 to 64 bp. A W line with no step on the reference has no
  rows, so a reader cannot see its steps; MC chr22 has 35 records over one
- Against `dep.rs`'s enumeration from the GFA, on departures with both
  ends on nodes passed once: on MC chr22 36,845 jumps and 10,032
  insertions match, 24,002 more lie inside one piece, and 1,209 differ
  only in the stretch, where an end runs against S and `dep.rs` reports
  the gap between the nodes and the record the breakpoints
- On pggb under nearest pass the densest windows are placement: in chrY's
  TSPY array, 99,378 of 104,479 rows are records with an end on a node the
  reference passes more than once, about 85,000 of them with 0 own bp, from
  contigs that hop between copies. Alignment-guided placement takes chrY's
  densest window to 18,562 rows, short back jumps through a satellite node
  the reference passes 1,188 times at 26.6 Mb. The spike's file holds
  19,933 there; its audit's 1,937 was an error. On chr22 alignment-guided
  placement's densest window holds 71,889 rows, against the spike's
  130,149
- Alignment-guided files are 9-20% larger than the spike's: a step the
  alignment leaves unplaced is route interior where format 5 let the
  decoder put it on a copy, 20 M steps on chrY and 171 M on chr22. That
  is placement coverage, not the format

### Copies

| | pggb chrY | pggb chrY, aligned | pggb chr22 | pggb chr22, aligned |
|---|---|---|---|---|
| steps in chunks with repeats that format 5's rules put on another copy | 8.6% | 63% | 3.8% | 7.6% |
| `@k` bytes, written where it differs | 1.6 MB, 0.8% | 7.6 MB, 3.4% | 38 MB, 2.3% | 27 MB, 1.5% |
| `@k` bytes, written on every node R holds more than once | 19 MB, 9.6% | 33 MB, 15% | 288 MB, 17% | 93 MB, 5.1% |
| step counts, rows | 119,749 | 20,871 | 561,313 | 80,411 |

- MC chr22 writes no `@k` and no step counts it did not write before
- Reference `>1>2>3>2>3>4` with 10 bp nodes, haplotype `>3>4`: format 5
  starts at R's first `>3` and exits to `>4` at 50, a 20 bp forward jump,
  though the haplotype matches the second copy. Format 6 writes `start`
  as `6@1` and needs no route
- Reference `>2>1>1>1>3` with 2 bp copies of node 1, haplotype holding one
  more `>1`: format 5 writes no step counts, since the handles round-trip,
  but decodes the extra unit at the array's start. Format 6 writes counts
  wherever positions differ
- The bounded stay keeps fewer runs than ADR 0001's: on pggb chrY 71,277
  runs, against 112,985 more the old rule kept; it refused 139,610 runs
  holding a node passed once and 73,690 with no home copy within `stay`

### Filing

On the amended Decision's filings, built side by side
([variants](../departures/results/rebuild/variants/)):

| | pggb chrY | pggb chrY, aligned | MC chr22 |
|---|---|---|---|
| stretch less the path's pieces, rows a 64 kb window returns p95 / max | 18,034 / 104,511 | 265 / 18,558 | 310 / 893 |
| whole stretch, the same | 18,034 / 104,511 | 265 / 18,558 | 310 / 893 |
| departure read bytes p95, less pieces / whole | 688 KB / 549 KB | 226 KB / 225 KB | 83 KB / 83 KB |
| file with crowds at K 8 / without | 1.96 GB / 199 MB | 224 MB / 221 MB | 59.8 MB / 59.8 MB |

- Subtracting the path's own pieces saves nothing once a stretch is cut at
  the bin sizes and each block clipped to the bases left in it: a block
  goes only where the pieces cover all of it. Subtracting without the
  bin-hull rule fragmented records instead, up to 3,499 rows for one
  3.2 Mb MC record
- A crowd's detail record copies every record over its run, and a path
  that hops between copies has thousands of runs over the same records:
  109 M crowd detail rows on pggb chrY and 263 M on pggb chr22 aligned,
  whose file went from 1.81 GB to 5.2 GB. Crowds lowered pggb chrY's p95
  window from 18,034 rows to 5,926 and raised its densest from 104,511 to
  136,435; they replace interior rows, and the dense windows are end rows

### The spike

Under nearest-pass placement, before positions, copies or bin-sized
blocks; its record lacked `missingBp`, `leaveChunk` and `rejoinChunk`.
Kept for the measurements the rebuild did not repeat.

- On MC chr22 19,630 of 25,185 leave breakpoints lie in a different chunk
  from the leave piece, against 1,254 rejoin breakpoints, so `leaveChunk`
  is needed
- Without the per-sequence definition, a contig that leaves chr22 for a
  random contig and returns leaves a chr22 window inside the excursion
  nothing: 15,051 of pggb chr22's 21,465 absent (contig, chunk) pairs had
  no block until the spike was changed to it
- The prototype's 32-chunk cap left 294 stretches uncovered on MC chr22
  and 24,629 on chrY
- Only 35.9% of pggb chrY pieces under nearest pass land within 10 kb of
  where Minigraph-Cactus places the same contig position
  ([chrY.placement-vs-mc.txt](../departures/results/chrY.placement-vs-mc.txt))

## Consequences

- graph-walks 5 reads format 6 only: two reads per cut, the walk chunks
  and the departure blocks, both fixed by the cut's extent; no follow
  rounds for coverage, no crossing cap, no direct-jump detection from
  steps the cut happened to read. It takes copies from `@k` and never
  chooses one, computes the departures inside the pieces it reads, takes
  every other departure from the records, and expands detail records page
  by page from its first release. It exports one function that derives a
  departure's direction and type, holes included, so the consumers don't
  each re-derive them. `WalkSkip`, `WalkCrossing` and `skipsOver` go
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
- Hosted Minigraph-Cactus walk files are rebuilt under new names
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
- **2026-11-03, three rounds of amendment,** seventeen reviews: positions
  from the placement pass and walk rows that name the copy (`@k`), the
  stay bounded by `stay`, counts written wherever positions differ, blocks
  at the index's bin sizes, end blocks on the end's own node, `#hole`
  lines, the extension rules, one file per placement; and, since cut by
  the rebuild, base-level filing less the path's own pieces with a
  whole-stretch exception, `crowd` rows with paged `S~crowd` detail
  records, in-piece records from `recordbp` with a reader match key, and
  `mp` on every `ref` row
- **2026-11-03, the rebuild.** A prototype of the amended Decision on all
  three graphs under both placements, read back by an independent audit,
  simplified it: whole-stretch filing for every record, records only
  where the walk read cannot show a departure, no crowds, no `recordbp`,
  `mp` deferred to a tag. Two vibe checks, before and after the numbers,
  agreed

## Alternatives rejected

- **A type or direction column:** derivable from the ends, and the
  prototype's `order` was wrong
- **A chunk cap:** leaves windows inside long jumps blank
- **Rows in every chunk of the stretch** (informed-2): +32% on chrY, no
  extra request, and a row per path and chunk which the reader still dedups
- **One row per departure under its whole interval:** a coarse Tabix bin
  every query in the chromosome reads
- **Copies in the chunks beside the rows under `S~departure`:** a record
  seen twice in one cut, for nothing the departure read does not give
- **A separate departure file:** two indexes to fetch and host for one
  fact
- **Blocks at Tabix's 16 kb level:** 2.2 to 3.3 times the rows of 64 kb
  blocks in the spike
- **A record with ends on two sequences** (the converged design): no block
  on either sequence over the excursion, 15,051 uncovered pairs on pggb
  chr22
- **Positions from the decoder:** the decoder's choice of copy became the
  projection, and no placement rule could change it within a chunk
- **`@k` on every node R holds more than once,** so that readers need no
  default rule: 5-17% of the pggb files, against 0.8-3.4%
- **Walk rows by position deltas into R in place of handles,** from a
  blind design: exact positions too, but `@k` gives them at 0 bytes on
  Minigraph-Cactus without a new row syntax
- **Filing a record's stretch less the path's own pieces,** with whole
  stretches for strand switches and back jumps with both ends on nodes
  passed once: the same rows as the whole stretch once blocks are cut at
  the bin sizes, more bytes on pggb chrY, two rules and a reader exception
  for nothing. It was chosen on a proxy that subtracted exactly
- **`crowd` rows standing in for a path's dense runs,** with paged
  `S~crowd` detail records: a tenfold larger file on pggb chrY, and the
  dense windows are end rows they do not replace
- **Records for departures inside a piece,** from `recordbp` bp of own
  sequence or across a chunk boundary: the walk read holds them already,
  and a record that repeats a computed departure needs a key to match the
  two, which collides on 0 bp nodes. Long own sequence inside a piece is
  the abridging of [ADR 0004](0004-abridged-detours.md)
- **`mp` on every `ref` row now:** 2.6% of pggb chrY for a mark no viewer
  draws yet; it is the first expected tag
- **Leaving out whole chunks where the path has a piece, or filing back
  jumps and strand switches at their ends only:** both break coverage
- **A placement key on every row:** one file holds one placement instead
- **Summarising departures inside the walk row rather than abridging a
  path per chunk:** abridging stays ADR 0004's, though which paths a
  chunk abridges depends on the chunk's other paths; it does not depend on
  the keep set
- **Names:** `bypass`, `skip`, `jump`, `traversal`, `allele`, `gap`;
  `departure` was the only name every arbiter ranked in its top three, and
  the closest prior art is the gap between blocks of a UCSC chain
