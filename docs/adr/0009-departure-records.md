# ADR 0009: One record per departure, and walk rows that name the copy

- **Status:** accepted, 2026-10-31; simplified on 2026-11-03 by the
  rebuild and on 2026-11-04 by the port, then to the minimal record,
  amended on 2026-11-05 to state pass counts and write an abridged row per
  piece, see [History](#history). Ported to gfa-to-tabix 3.0, not released
- **Decides:** what a walk file holds for every place a haplotype's path
  does not follow the reference between two of its steps on it, how the
  records are filed so that any window finds them, which copy of a node a
  walk row's step takes where the reference passes it more than once, what
  a walk row no longer carries, and how later additions get in without a
  new format. Walk format 6
- **Measured by:** a prototype writer built on HPRC v2.1
  Minigraph-Cactus chr22 and HPRC release 2 pggb chrY and chr22, on GRCh38,
  under nearest-pass and alignment-guided placement, an independent audit
  that reads its files as a reader would, and the port, compared row for
  row with the prototype; scripts and results in
  [docs/departures/](../departures/), under [Evidence](#evidence)
- **Supersedes:** [ADR 0006](0006-walks-skip-rows.md)'s `skip` rows, the
  decoding rules' own choice of copy, the `pv`, `nx`, `pg`, `pr`, `ng`
  and `nr` tags of format 5's walk rows, and
  [ADR 0004](0004-abridged-detours.md)'s one `abridged` row per path

## Context

- Format 5 writes a `skip` row only where a path has no piece in a chunk,
  with the stretch and nothing else: no own sequence, no strand, no pass
  counts, and none at all for a stretch over 32 chunks. graph-walks then
  reconstructs what it can from the pieces it happens to read, so a
  haplotype's answer depended on which other haplotypes were kept, and the
  viewers called the result a deletion
- Format 5's decoding rules chose a copy themselves where a chunk's R
  held a node more than once: a piece started at R's first copy and a
  route exit landed on the nearest, the later on a tie (`Path::first` and
  `Path::nearest` in format 5's `src/routes.rs`). Its `encode` never read
  the placement pass, which only picked the chunk. So no placement rule
  could put a step on another copy within a chunk: format 5's rules put
  3.8% to 8.6% of the steps in chunks with repeats on another copy than
  nearest-pass placement chose, and up to 63% under alignment-guided
  placement
- The tools make no variant calls; they state what the data shows. A
  haplotype's answer must not depend on the keep set. A window inside a
  jump of any length must find it from a bounded number of range requests
  near the window. No backwards compatibility. Format 6 breaks every
  reader anyway, so it aims at the ideal format, and the ideal includes
  being simple: every mechanism the rebuild measured below earned its
  place there, and the minimal record of 2026-11-04 keeps only what a
  reader cannot take from the walk read

## Decision

### The record

One `departure` record for every departure the walk read cannot show:
each place a path's consecutive steps on one reference sequence S are not
adjacent on S at the passes they took and lie in different pieces. Fields,
plain integers:

```
seq~departure  a  b  departure  path hapStart ownBp missingBp
               leavePos leaveStrand leavePasses rejoinPos rejoinStrand rejoinPasses
```

- An end is a step on S: its breakpoint on S, where the haplotype's
  sequence stops following S (the node's end for a step along S, its start
  for a step against it, and the other way round for the rejoin), and `+`
  or `-` for the step along or against S's orientation at that pass, and
  how many times the reference's paths pass the step's node, all its
  sequences counted. The leave is the step before the departure in the
  path's order and the rejoin the step after
- `hapStart` is where the haplotype's own sequence between the ends starts
  on its contig, right after the leave step, and `ownBp` how far it runs,
  0 for a direct jump: every base between the ends, on nodes of its own,
  on other reference sequences, in W lines with no step on S and in no W
  line. `missingBp` counts the part of `ownBp` no W line of the contig
  covers: the gaps between W lines only
- No direction and no type column. A reader derives them:
  `leaveStrand ≠ rejoinStrand` is a strand switch; otherwise, for a `+`
  leave the haplotype jumps back when `rejoinPos < leavePos`, and for a
  `-` leave when `rejoinPos > leavePos`, over reference it walks again;
  `rejoinPos = leavePos` is own sequence between adjacent steps; any other
  case is a jump forward. `ownBp` 0 is a direct jump; `missingBp` above 0
  is sequence the graph lacks
- Two consecutive steps on S are adjacent, and depart nowhere, when
  `ownBp` is 0, the strands are equal and `leavePos = rejoinPos`, holes
  removed (below). A step on a node of 0 bp between them is no departure
- A contig's sequence before its first step on S or after its last is no
  departure and has no record: the piece holding that step shows it as a
  route with no entry or no exit, and its steps on another sequence lie in
  pieces there
- A pass count above 1 marks the end, and so the departure, as the
  placement's choice: another pass would put it elsewhere or make it no
  departure. The far end of a record often lies outside the walk read, so
  only the record can say so (see [Pass counts](#pass-counts))
- No column names an end's node or chunk. R holds one node ending at a `+`
  leave's or `-` rejoin's breakpoint and one starting at the other kind's;
  the step's piece is filed under the chunk of that node's pass, which is
  the chunk holding the base beside the breakpoint or, for a node
  straddling a chunk boundary, the one before: both in the walk read of any
  window over the end
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
- **The stay** keeps a run home only where it returns there, holds at most
  `stay` bp of reference nodes and no node the reference passes once, and
  each of its steps on a node the home
  chunk's R holds has a copy there within `stay` bp of the offset
  `visits_along` predicts for it from the run's previous step; it
  re-places the step on the nearest such copy. A step on a node the home
  chunk's R lacks is route interior. Any other run moves the piece on, so
  the stay moves no step more than `stay` bp from its prediction. This
  amends ADR 0001's rule 2 and [ADR 0003](0003-long-node-lookback.md)'s
  guard. Under nearest-pass placement no step on a node the reference
  passes once is therefore route interior
- The reference's own paths lie at their offsets and have no departures
- [ADR 0001](0001-step-placement.md)'s rule 3 places route-interior nodes
  at a `ref` row's position for drawing only, never a haplotype's steps
- Departures therefore depend on the placement rule, which the format
  fixes, on `stay`, in the header, and on `chunk` through the stay and the
  pieces

### Walk rows name the copy

Where a chunk's R holds a node more than once, a walk row names the copy
a step takes wherever it is not the default:

```
walk      ... start[@k] choices                  choices token: t[:k][@k]
abridged  ... start[@k] end[@k] detail
```

- `k` counts the chunk's R positions holding the node, from 0, in a
  detail record too. The writer writes a copy only where it differs from
  the default, so a file has one encoding
- On `start` the default is R's first copy. On a choice token `:k` names
  the copy of the entry's node the walk leaves R from; its default is
  where stepping along R from the last landing until the entry's handle
  stops. `@k` names the copy the exit lands on as the walk takes the
  route, flip applied; its default is the copy nearest the entry's R
  index, the later on a tie. A route with no entry takes neither, since
  its exit is `start`, which `start@k` names, and a trailing route takes
  no `@k`. On an abridged row's `end` the default is the copy nearest
  `start`'s
- The encoder continues along R only where R's next position is the
  step's pass, and otherwise takes a route, with an empty interior if need
  be. A walk row has no `end`: after its last route the walk follows R
  until it has `nsteps` steps. Every choice a decoder makes is which
  occurrence, so the copies pin the row to its positions with one
  mechanism
- A file on a reference that passes every node once writes no `@` or `:`
- The decoding rules in [walks-format.md](../walks-format.md#decoding-a-walk-row)
  take `@k` and `:k` in place of R's first copy, the first handle reached
  and the nearest copy

### Pass counts

The file states, wherever a reader meets a step on the reference, how many
times the reference's paths pass its node: a `passes` column on `ref` rows,
one count per step or `.` when all are 1, and `leavePasses` and
`rejoinPasses` on records. The header's `revisited:i:` counts the nodes
passed more than once.

- A count of 1 makes a step's position, and a departure between two such
  steps, a fact of the graph. Above 1 they are the placement rule's
  choice, which the file states but does not promise is the copy the
  haplotype came from
- The `ref` rows cover the departures a reader computes inside a piece and
  any stretch of R a viewer marks; the record columns cover the far end of
  a record, which the walk read of a window often lacks. Counts are over
  the whole reference, not the chunk: a node R holds once in a chunk may
  be passed in another
- On a reference the graph was built on, such as GRCh38 in the GRCh38
  Minigraph-Cactus graph, every count is 1 and `passes` is `.` on every row

### Abridged rows stand for one piece

An `abridged` row is `path fragStart hapOffset piece nsteps bp start[@k]
end[@k] detail`, one per moved piece. Its `hapOffset` and `bp` give the
piece's stretch on R, from where its `start` step begins on its contig to
where its `end` step ends, as a reader trims a walk row's piece, and
`nsteps` counts all the piece's steps, the number its detail record
decodes. Every record ends at a piece's first or last step on S, so a
record's own bp never overlap an abridged row's, and the own steps outside
the stretch, which no record covers at a contig's ends, are not netted as
a change. A path's moved pieces in a chunk still
move together and share one detail record. Every piece of every path then
has exactly one row in its chunk, a walk row or an abridged row, and a
reader joins and keys them alike: the departures between two moved pieces
are records, and the pieces of other chunks between them are their own
rows.

### Walk rows carry no neighbour tags

Format 5's walk, `ref` and `abridged` rows named the chunk of a path's
previous and next piece (`pv`, `nx`) and, across a contig's W lines, the
bp between them and the chunk of the next line's first piece (`pg`, `ng`,
`pr`, `nr`). Format 6 drops all six:

- Readers used them for follow rounds and crossing detection, which format
  6's two reads replace, and for where a path goes on at a piece's end. A
  departure between pieces or across W lines is now a record with both
  ends' chunks and `missingBp`, and a piece's adjacent continuation lies in
  the chunk holding its breakpoint, which a window's walk read reads
- The one thing no row holds is where a path goes on another reference
  sequence: its last piece on S ends on R or off it, and its pieces on the
  other sequence hold the steps. No reader follows it today. If one needs
  it, a tag on the piece's walk row can name the chunk of the path's first
  piece there, as the extension rules allow
- They cost 0.5% of MC chr22's file and 0.35% of pggb chrY's

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
  [len − 1, len)
- That extent is cut at aligned multiples of the index's bin sizes, 2^26,
  2^23, 2^20 and 2^17 bp, whatever `--chunk` is, one row per block, so
  that each row lands in a Tabix bin no larger than its own size. The CSI
  index the writer uses past 512 Mb has bins at the same sizes
- Abridged paths' detail records stay as format 5 files them, record
  `detail` at `detail × 16384`, one Tabix leaf bin each

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
#walks	format:i:6	chunk:i:	maxnode:i:	revisited:i:	stay:i:	abridge:i:	abridgebytes:i:
#reference	GRCh38
#haplotype	...
#long	...
#hole	...
```

- `format:i:6` names the six row kinds, their columns and the placement
  rule. `skip:i:` is gone, and so is any list of the kinds: a file with a
  kind or a rule this ADR doesn't give is another format
- `revisited` counts the nodes the reference's paths pass more than once:
  0 states every position and departure in the file as a fact of the graph
- `stay`, `abridge` and `abridgebytes` record how the file was built; a
  reader ignores them

### Extension rules

These let later additions in without a format change:

- A reader refuses any format but 6. A new row kind or placement rule is a
  new format, and later additions are tags, siblings or files instead
- A reader ignores tags it doesn't know, on every row kind, in any order
  after the fixed columns, and on header lines
- A reader reads only the sequences S, `S~cs` and `S~departure`, and
  ignores any other sibling
- One file holds one placement, so no row needs a placement key. A second
  placement of the same graph, such as every copy of a repeat, is another
  file, under a header tag naming its rule where a reader need not act on
  it, and otherwise a new format


### Scope of the projection

Projecting a haplotype onto one reference is exact where the haplotype
keeps the reference's order, and a placement choice where the reference
passes a node more than once. The file says which by its pass counts, and
a viewer states a departure with an end passed more than once as a
placement choice, never as a jump, and offers the graph,
haplotype-coordinate or alignment view there. The placement rule itself is
[ADR 0001](0001-step-placement.md)'s, and a better one for repeats is an
[open problem](../open-problems.md).

- A walk file's reference should be the graph's own where the graph has
  one: the hs1 files come from HPRC v2.1's CHM13-referenced
  Minigraph-Cactus graph, not from the GRCh38 one projected onto CHM13.
  Projected onto CHM13 from the GRCh38 graph, chr9's pericentromeric
  copies, which that graph collapses, file 2.2 M records of haplotypes
  hopping between copies 1 to 100 Mb apart, and windows between 38 and 80
  Mb read up to 22 MB of departure rows
  ([results](../departures/results/minimal/README.md#where-the-chm13-files-rows-are))

### Readers

graph-walks 5 returns the record as `WalkDeparture`; the structural-forms
`Departure` keeps its name.

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
| departure rows a 64 kb window returns, p95 / max | 310 / 893 | 18,037 / 104,479 | 265 / 18,562 | 217,883 / 2,491,246 \* | 1,070 / 71,905 |
| departure read, requests max, bytes p95 / max | 1, 84 KB / 132 KB | 5, 556 KB / 1.14 MB | 2, 234 KB / 282 KB | 15, 5.2 MB / 32.9 MB \* | 4, 382 KB / 988 KB |
| build, s / peak GB | 52 / 4.1 | 132 / 12.5 | 149 / 12.2 | 587 / 36.3 | 518 / 41.0 |

\* From the port's file of 2026-11-04, which has the same rows ([The
port](#the-port)), by shard 0 of 4 of its audit, which costs the windows
over every record: 4,497 s at 39 GB. Shards 1 to 3 wait for memory on ada.
The aligned chr22 audit ran whole on 2026-11-04, at 35 GB. The densest
window, chr22:12.06-12.12 Mb, returns 2,491,246 rows from 791 paths

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
  insertions match, 24,002 more lie inside one piece, and 1,215 jumps
  differ only in the stretch, where `dep.rs` reports the gap between the
  nodes and the record the breakpoints: 1,209 with an end against S, and
  6 back jumps with both ends along it
- On pggb under nearest pass the densest windows are placement: in chrY's
  TSPY array, 98,965 of the densest window's 104,479 records have an end on
  a node the reference passes more than once, 84,748 of them with 0 own
  bp, from contigs that hop between copies. Alignment-guided placement takes chrY's
  densest window to 18,562 rows, short back jumps through a satellite node
  the reference passes 1,188 times at 26.6 Mb. The spike's file holds
  19,933 there; its audit's 1,937 was an error. On chr22 alignment-guided
  placement's densest window holds 71,905 rows, against the spike's
  130,149
- Alignment-guided files are 9-20% larger than the spike's: a step the
  alignment leaves unplaced is route interior where format 5 let the
  decoder put it on a copy, 20 M steps on chrY and 171 M on chr22. That
  is placement coverage, not the format

### The port

The writer in `src/` after the port, on the same graphs under nearest
pass, against the prototype and against format 5 built by 552b9c1
([results](../departures/results/port/README.md)).

| | MC chr22 | pggb chrY | pggb chr22 |
|---|---|---|---|
| file | 59.43 MB | 196.6 MB | 1.68 GB |
| against format 5 | +0.48% | +9.3% | +18.9% |
| rows differing from the prototype's, its cuts aside | 0 | 0 | 0 |
| build, s / peak GB | 56 / 4.1 | 115 / 8.0 | 693 / 22.4 |
| format 5 build, s / peak GB | 70 / 4.1 | 169 / 6.5 | 581 / 20.1 |

- With abridging off, MC chr22's `ref`, `nodes`, `route` and `walk` rows
  equal format 5's, neighbour tags aside
- The build phase peaks at 1.3 GiB on pggb chr22, departure records
  included: the peak is the encoding of the densest chunks. Reading
  positions straight into positions in R, holding each route once and
  dropping a chunk's whole encoding before abridging it took pggb chr22
  from the prototype's 36.3 GB to 22.4 GB. The rest over format 5 is
  positions in the sorted rows and 14% more pieces, from the bounded stay
- Shard 0 of 4 of the audit of the port's pggb chr22 file under nearest
  pass, before the minimal record, whose two-ended records the cuts leave
  as they were: 1,293,162 records each equal in every field to a departure
  that needs one, none missing, none unmatched, every departure inside a
  piece within the walk read's reach and every stretch base under a row
- The fuzz now draws references with holes and contigs whose W lines
  abut. It found the prototype missed a departure over a step on a 0 bp
  node between abutting W lines, which the port records, and two faults
  of the audit, fixed: a run along R measured by the reference's span,
  holes included, and an unseen abutting W line taken for a mismatch

### The minimal record

Measured on the port's files of 2026-11-04 on ada, before the cuts:

- `leaveChunk` and `rejoinChunk` equalled the chunk of the end node's pass
  start on every end, 49,425 on MC chr22 and 850,876 on pggb chrY, which
  is how the writer files a piece; they differ from the chunk of the base
  beside the breakpoint only for a node straddling a chunk boundary, by
  one chunk, which a window's walk read holds anyway. They were 6% of
  pggb chrY's departure bytes
- One-ended records: 129 on MC chr22, of which 26 carried bp between W
  lines and 103 repeated what the first or last piece's route shows; 796
  on pggb chrY and 10,578 on pggb chr22, 240 and 9,338 of them with own
  bp on another reference sequence, which the pieces there hold
- `leavePasses` and `rejoinPasses` sat on the 3% of departures that are
  records and on none the reader computes, and no audit checked them
- With every cut a record has 8 fields after its kind, against 16 and a
  tag

Built at 76c9223 on ada, audited, against the port's files and format 5's
([results](../departures/results/minimal/README.md)):

| | MC chr22 | pggb chrY |
|---|---|---|
| file | 59.17 MB | 190.4 MB |
| the port, before the cuts | 59.43 MB | 196.6 MB |
| against format 5 | +0.04% | +5.9% |
| records, rows | 24,648, 31,239 | 425,040, 1,224,004 |
| copies named on walk rows | 0 | 299,916 |
| departure read, requests max, bytes p95 / max | 1, 81 KB / 115 KB | 5, 569 KB / 1.05 MB |
| build, s / peak GB | 57 / 4.1 | 102 / 7.6 |

- The records lost against the port are the one-ended ones, 129 and 796.
  Every record left matches a departure the audit recomputes from the
  decoded rows in every field, none is missing, every departure inside a
  piece lies within the walk read's reach, and every stretch base lies
  under a row
- pggb chrY names 299,916 copies on its walk rows, where the port wrote
  `@k` on some and step counts on every token of 119,749 rows

### Copies

| | pggb chrY | pggb chrY, aligned | pggb chr22 | pggb chr22, aligned |
|---|---|---|---|---|
| steps in chunks with repeats that format 5's rules put on another copy | 8.6% | 63% | 3.8% | 7.6% |
| `@k` bytes, written where it differs | 1.6 MB, 0.8% | 7.6 MB, 3.4% | 38 MB, 2.3% | 27 MB, 1.5% |
| `@k` bytes, written on every node R holds more than once | 19 MB, 9.6% | 33 MB, 15% | 288 MB, 17% | 93 MB, 5.1% |
| rows with step counts, before `:k` replaced them | 119,749 | 20,871 | 561,313 | 80,411 |

- MC chr22 writes no `@k` and no `:k`
- Reference `>1>2>3>2>3>4` with 10 bp nodes, haplotype `>3>4`: format 5
  starts at R's first `>3` and exits to `>4` at 50, a 20 bp forward jump,
  though the haplotype matches the second copy. Format 6 writes `start`
  as `6@1` and needs no route
- Reference `>2>1>1>1>3` with 2 bp copies of node 1, haplotype holding one
  more `>1`: format 5 writes no step counts, since the handles round-trip,
  but decodes the extra unit at the array's start. Format 6 names the copy
  the route leaves from, `:2`, the last
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
  is needed. That was before positions: in format 6 a step's piece is
  filed under the chunk holding its pass, so an end's chunk differs from
  its breakpoint's only where the end's node crosses a chunk boundary or
  the stay kept it home. Not re-measured
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
  chooses one, computes the departures inside the pieces it reads, and
  takes every other departure from the records; it reads no neighbour tag.
  It exports one function that derives a departure's direction and type,
  holes included, so the consumers don't each re-derive them. `WalkSkip`,
  `WalkCrossing`, `skipsOver` and the `WalkStop` kinds built from the
  neighbour tags go
- Attaching a departure's own steps costs one more read per distinct leave
  chunk outside the read range, the chunk of the base beside `leavePos`
  and the one before. Which records get their steps attached follows from
  the record alone, such as `ownBp` above `missingBp` and under the
  expansion threshold, never from budget order, so no haplotype's answer
  depends on the others. Own steps on other reference sequences are not in
  the leave piece, and the file does not say where they lie until a tag on
  a walk row does
- bandage-core's label for a path that goes on elsewhere ("on nodes filed
  near chr22:20.3 Mb", from `nx`) and its "not in the graph" gap (from
  `ng`) take the record's `rejoinPos` and `missingBp` instead
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
  instead; it is to be released as 4.6.1, and bundled by the viewers,
  before gfa-to-tabix 3.0 is released or any format 6 file hosted
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
- [walks-format.md](../walks-format.md) documents format 6 since the
  port
- pggb walk files are not hosted, and the format does not depend on their
  placement: alignment-guided placement, the `--alignments` input, would
  be its own ADR with a header tag naming the rule, its input and the
  input's checksum; the port writes nearest pass only, which takes no input
- The bounded stay changes [ADR 0001](0001-step-placement.md)'s rule 2
  without its table of agreement with Minigraph-Cactus placement on pggb
  chr22, which ADR 0001 asks a replacement to report. GRCh38 passes no
  node of MC chr22 twice, so the stay keeps nothing there; in the
  genome-wide MC graph CHM13 passes 209,578 nodes more than once (ADR
  0001), so the hosted CHM13 file is the first to depend on it and on `@k`
- The hosted genome-wide MC graph, with `--refs GRCh38,CHM13`, builds in
  1 h 22 m at 13.1 GB, against format 5's 2 h 25 m: the GRCh38 file is
  1.55 GB as before, the CHM13 file 1.99 GB against 1.46 GB, since CHM13
  passes 209,578 nodes more than once and nearest-pass placement files
  5.5 M departure records there, in 42.7 M rows
  ([results](../departures/results/minimal/README.md)). An audit by
  chromosome comes before hosting. Its GRCh38 file is the hg38 file; its
  CHM13 file is not hosted, and the hs1 file comes from the
  CHM13-referenced graph built with `--refs CHM13`
- graph-walks applies its budgets, `WALK_BUDGETS`, unless a caller passes
  others, so a viewer that passes none still refuses a 22 MB departure
  read; `Infinity` lifts one
- The writer's peak memory on pggb, set by the densest chunks' encoding,
  lies above format 5's; see [The port](#the-port)

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
- **2026-11-04, the port** to gfa-to-tabix 3.0. The prototype had dropped
  `pv` and `nx` unrecorded, so its sizes left them out; measured, they
  cost 0.35-0.5%. A vibe check and two independent reviews found that
  format 6's records carry what readers took from all six neighbour tags,
  but where a path goes on another reference sequence, and that detail
  paging bounds nothing; both went, with the user's agreement. The port
  writes nearest pass only, and recorded a departure across abutting W
  lines over a step on a 0 bp node, which the prototype missed
- **2026-11-04, the minimal record,** later the same day. The user had
  asked for a minimal format. Five reviews, four per question and one deriving the record from
  the requirements alone, and measurements on the port's files cut every
  column a reader can take from the walk read or no reader uses:
  `leaveChunk` and `rejoinChunk`, `leaveNode` and `rejoinNode`,
  `leavePasses` and `rejoinPasses`, `ownSteps`, `fragStart`, `xb`, and
  one-ended records; and from the header `kinds:Z:` and `#placement`.
  Adjacency is by bp, so a step on a 0 bp node between adjacent steps is
  no departure. Filing departure rows in the chunks in place of
  `S~departure`, weighed again on the port's numbers, stayed rejected. On
  walk rows, `:k` on a choice names the copy the walk leaves R from, in
  place of step counts on every token of a row, and `end` went, since
  `nsteps` bounds the last stretch: one copy mechanism

- **2026-11-05, the format arbitration.** Every review of the stack had
  found more and handed back decisions; the findings traced to three
  places where the format left a reader to reconstruct a fact: the copy
  a departure's end is on, an abridged row's extent, and whether a read
  is safe to make. The record's pass counts came back as columns, `ref`
  rows gained `passes` and the header `revisited`, abridged rows became
  one per piece, graph-walks' budgets became its defaults, and the hs1
  files were moved to CHM13's own graph. The format number stays 6: no
  format 6 file was released or hosted, and graph-walks refuses a row
  missing the new columns rather than misread it
- **2026-11-05, the final review before release.** An abridged row's
  `hapOffset` and `bp` covered its whole piece, so an unexpanded piece
  netted the own steps at a contig's start or end, which no record covers,
  as a change. They now give the piece's stretch on R, from its `start`
  step to its `end` step, and `nsteps` stays the whole piece's, which is
  what reading its detail record costs

## Alternatives rejected

- **Neighbour tags on walk rows** (format 5's `pv`, `nx`, `pg`, `pr`, `ng`,
  `nr`): a second account of where a path goes, which the records give;
  the cross-sequence link they alone hold can come back as a record tag
- **Detail records in pages of `page` rows,** each at its own multiple of
  16384: a record's walk rows cite routes on its earlier pages, so no page
  decodes alone; @gmod/tabix merges a record's adjacent pages into one
  request; and the largest page is 90-99% of the largest record, 27.7 of
  28.0 MB raw on pggb chrY, so paging by rows caps nothing

- **A type or direction column:** derivable from the ends, and the
  prototype's `order` was wrong
- **A chunk cap:** leaves windows inside long jumps blank
- **Rows in every chunk of the stretch** (informed-2): +32% on chrY, no
  extra request, and a row per path and chunk which the reader still
  dedups. Weighed again on the port's files: departure text is 1.2% of MC
  chr22's and would be 1.8% filed per chunk, 11.5% of pggb chrY's and
  would be 34%
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
- **An `mp` tag on `ref` rows in place of record columns:** it cannot
  mark a record's far end outside the walk read, which is where a hop
  between copies tens of Mb apart lands. It was the reason the record's
  pass counts were cut on 2026-11-04 and was never written
- **A pass-count tag on records written only where above 1:** nothing on
  Minigraph-Cactus against GRCh38, where the columns cost 4 bytes a row
  (124,956 bytes of departure text on MC chr22, 3.4%, 0.007% of the
  file, `results/arbitration/sizes.txt`), but an absent tag reads the
  same as a file that predates it; a fixed column cannot be missed
- **An abridged row's contig end in place of `bp`, one row per path:** the
  extent becomes exact, but the row still stands for pieces with other
  chunks' pieces and the departures between them inside it, which every
  reader must take in; that is where graph-walks' abridged bugs came from
  twice
- **Hosting the CHM13 file of the GRCh38 graph, its chr9 and chr14 repeat
  windows refused:** CHM13's own graph is published, and the refused
  windows are those an hs1 user comes to see
- **Filing records over their stretch less `#hole`s:** clears the windows
  inside chr9's 32 Mb hole in the GRCh38 graph's CHM13, but those beside
  it still read 0.5 to 1.7 M rows; it adds a rule for a case the right
  graph removes
- **Leaving out whole chunks where the path has a piece, or filing back
  jumps and strand switches at their ends only:** both break coverage
- **A placement key on every row:** one file holds one placement instead
- **Summarising departures inside the walk row rather than abridging a
  path per chunk:** abridging stays ADR 0004's, though which paths a
  chunk abridges depends on the chunk's other paths; it does not depend on
  the keep set
- **`leaveChunk` and `rejoinChunk`:** equal to the chunk of the end's pass
  start on every end measured, which the walk read of any window over the
  end holds, since it reads from the chunk before
- **`leaveNode` and `rejoinNode`:** R holds one node at each breakpoint
  on each side, so the walk read names it; a record filed over a stretch
  needs no key
- **Cutting `leavePasses` and `rejoinPasses`** (2026-11-04, reversed
  2026-11-05): no reader could then tell a hop between copies from a jump
- **`ownSteps`:** no reader needs it; what the attach policy took from it,
  `ownBp` above `missingBp` gives. Adjacency by steps made a step on a 0
  bp node a departure over no sequence
- **`fragStart` on records:** a contig's W lines cannot overlap, so
  `hapStart` lies in one, and a reader joins pieces to records by contig
  coordinate
- **`xb`:** how much of the own sequence lies on other reference sequences,
  not where; a tag can bring back either
- **One-ended records,** for a contig's sequence before its first step on
  S or after its last: not a departure, both ends not stated, and on MC
  chr22 103 of 129 repeated what the first or last piece's route shows;
  the 26 with bp between W lines and pggb's 9,338 with bp on another
  sequence state what a reader can see from the piece's end
- **Step counts `:n` on every token of a row, and an `end` handle:** a
  second mechanism beside `@k` for pinning a row to its positions, written
  all or nothing per row, 119,749 rows on pggb chrY; `:k` on the token
  that needs it says which occurrence like `@k` does, and `nsteps` ends
  the row
- **`kinds:Z:`:** `format:i:` refuses what a reader can't read, and a new
  kind is a new format anyway; no reader read it
- **`#placement`:** one rule, which the format fixes; no reader acted on
  it, and a later rule is a header tag or a new format
- **Names:** `bypass`, `skip`, `jump`, `traversal`, `allele`, `gap`;
  `departure` was the only name every arbiter ranked in its top three, and
  the closest prior art is the gap between blocks of a UCSC chain
