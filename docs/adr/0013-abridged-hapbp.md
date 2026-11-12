# ADR 0013: Walk format 8's `abridged` row states `hapBp`, the piece's bp on its contig

- **Status:** accepted, 2026-11-12. gfa-to-tabix 5.0.0 writes it. No file
  in format 8 is hosted or released; both genome files are rebuilt once,
  after graph-walks reads the column
- **Decides:**
  - the `abridged` row gains one column, `hapBp`, so a moved piece's
    stretch of its contig is in its tile
  - the attach rule, how a record's own steps lie in a piece, is a
    statement of the format that a file check holds every file to
  - what a reader relies on is the format, and placement, `stay`, the
    abridge budgets and the order of a tile's detail records are this
    writer's policy
  - the writer refuses a coordinate past 2^53
- **Keeps:** every other unit, row and column of format 8, byte for
  byte. The two end steps format 8 dropped from the row stay dropped
- **Amends:** [ADR 0012](0012-abridged-blocks.md), where it says a cut
  of named haplotypes never reads a `blocks` unit, and where it leaves
  the row's dropped fields to a measurement
- **Trigger:** ADR 0012 closed the row's spelling until a consumer fails
  on a real window. graph-walks' format 8 branch, cutting the genome
  files built for ADR 0012's acceptance, reads 4.54 MB for a 1 kb window
  where ADR 0012's limit is 4 MB and its own `bytesFor` said 1.6 to
  3.1 MB, on 5 of 1,689 scanned CHM13 windows
  ([scan](../walks-container/hapbp/results/measure-chm13.txt))

## Context

- Format 8's `abridged` row says where a moved piece starts on its
  contig, `hapOffset`, and not where it ends. Its end was the sum of its
  `blocks` list, in another unit
- A departure record is attached where the window's read lacks its leave
  piece or its rejoin piece. The tiles its `ownTiles` names hold its own
  steps, and where the path is abridged there the reader has to say
  which piece holds them and how many bp they are. graph-walks answered
  from the tile's `blocks` unit, every time
- A `blocks` unit can be many times its tile. At CHM13
  chr2:92,077,080 the two attach tiles are 48,534 bytes and the one
  `blocks` unit read for them is 1,364,749
  ([windows](../walks-container/hapbp/results/rules.txt))
- The tile's rows and the record don't settle it without the end. Two
  graphs that differ in how much of a record's own sequence lies in its
  leave piece, 10 bp or 5, write the same tile and the same record
  ([twin-midline-A.gfa](../walks-container/hapbp/twin-midline-A.gfa),
  [twin-midline-B.gfa](../walks-container/hapbp/twin-midline-B.gfa)).
  So a reader rule over those rows is a guess, or a proof about rows the
  read happens to hold

## Decision

[walks-format.md](../walks-format.md) is the specification; this is what
changed and why.

### The column

- `seq start end abridged path fragStart hapOffset piece nsteps hapBp detail`:
  `hapBp` after `nsteps` and before `detail`
- **`hapBp` is the sum of the lengths of all the piece's steps,** on R
  or off it. The piece covers the half-open stretch
  `[hapOffset, hapOffset + hapBp)` of its haplotype contig, forward
  along the contig whichever way its steps run on the reference. It is
  at least 1
- **It is not a length on the reference** and has nothing to do with
  `end − start`: a hairpin of 87 bp spans 40 bp of its reference
  ([hairpin-span.gfa](../walks-container/hapbp/hairpin-span.gfa))
- **It is not format 7's `bp`.** That ran from the piece's first step on
  R to its last and left out the steps off R at its ends, which is why
  ADR 0012 dropped it. `hapBp` is the whole piece: on the spec's example
  piece it is 109 where format 7's `bp` was 52
- **The end steps stay dropped.** The `blocks` list and the `ref` rows
  give them, and no measurement here asks for them back

### What the format now states

- `hapBp` is the sum of the piece's `blocks` list and the bp of the
  steps its detail walk row decodes to
- A line's piece 0 starts at `fragStart`, and `hapOffset + hapBp` is the
  `hapOffset` of the line's next piece
- **The attach rule:** a record's own steps in a piece of its path on
  its sequence are the piece's steps within `[hapStart, hapStart +
  ownBp) ∩ [hapOffset, hapOffset + hapBp)`. Where that is not empty it
  is the piece's whole run off R after its last step on R, the record's
  leave, or before its first, its rejoin: one run at one end, never the
  whole piece
- So an attach fetch builds a record's own run in an abridged piece
  from the `abridged` row and the record, and reads no `blocks` unit.
  A reader still reads a tile's `blocks` unit to draw its moved pieces
  unexpanded
- **Why the rule holds:** every piece has a step on R; a record lies
  between two consecutive steps of its path on S that are in different
  pieces; its leave is its piece's last step on R and its rejoin its
  piece's first. A piece's steps on R are steps on S, so none lies
  strictly between a leave and its rejoin, and the record's own steps in
  the piece can only be all the steps after its last on R or all those
  before its first. On the contig that is the two stretches' overlap
- The page puts the `blocks` list's grammar in ABNF. Its exact form,
  with no leading zero and no `-0`, was stated only in a checker

### The format and this writer's policy

- walks-format.md gains
  [What a reader relies on](../walks-format.md#what-a-reader-relies-on):
  the invariants that hold of any format 8 file, each with a file check
- Which pass a step takes on a node the reference passes more than once,
  `stay`, the abridge budgets and "costliest first" are named as
  gfa-to-tabix's policy. A file that places a step otherwise and keeps
  the invariants is format 8
- No byte changes and no reader reads a file differently for it

### Coordinates

- The writer refuses a W or P line that starts or ends past 2^53 on its
  contig, and a reference sequence whose last tile ends past it. Every
  coordinate a file states, `hapOffset + hapBp` among them, is then at
  most 2^53, which a reader holding numbers as doubles reads exactly
- Before, a line at 2^53 + 1 built, and a start near 2^63 panicked

## How it was decided

- Three independent reviews took the question
  ([brief](../walks-container/hapbp/brief.md)) under a writer's, a
  referee's and a reader's lens, each writing its criteria before it
  read the measurements
  ([writer](../walks-container/hapbp/criteria-writer.md),
  [referee](../walks-container/hapbp/criteria-referee.md),
  [reader](../walks-container/hapbp/criteria-reader.md)). Each wrote its
  own script against the genome files and built its own adversarial
  graphs. All three ruled to add the column
- It rests on two things: what the every-haplotype view's attach fetches
  read, and one case where a cut of four named haplotypes needs a
  piece's end. It does not rest on the totals a cut of four named
  haplotypes reads on the worst tiles, which ADR 0012 asked for: those
  bytes come from how graph-walks chose what to load, and a reader rule
  removes them with no column
  ([four-chm13.txt](../walks-container/hapbp/results/four-chm13.txt),
  [four-grch38.txt](../walks-container/hapbp/results/four-grch38.txt))

## Evidence

Measured on the two genome files of ADR 0012's acceptance,
`hprc-v2.1-mc-chm13.CHM13.walks.gz` and
`hprc-v2.1-mc-grch38.GRCh38.walks.gz`, with the column simulated from
each piece's `blocks` row. CHM13 first, then GRCh38.

- **The attach rule holds on every row.** Of 25,864 and 18,772 records
  naming an abridged tile where their path is abridged, 25,117 and
  17,670 pieces hold own steps. In each the overlap of the two stretches
  is the list's one leading or trailing run, with 0 exceptions, by three
  scripts written apart
  ([measure.py](../walks-container/hapbp/scripts/measure.py),
  [referee.py](../walks-container/hapbp/scripts/referee.py),
  [rule.py](../walks-container/hapbp/scripts/rule.py); results in
  [referee.txt](../walks-container/hapbp/results/referee.txt) and
  [rules.txt](../walks-container/hapbp/results/rules.txt))
- **What attach fetches read on the worst windows.** A 1 kb window with
  every haplotype, in the tile before, at and after each of the 30 tiles
  with the largest `blocks` units, 180 windows a genome
  ([windows.py](../walks-container/hapbp/scripts/windows.py),
  [windows.txt](../walks-container/hapbp/results/windows.txt)):

  | | CHM13 | GRCh38 |
  |---|---|---|
  | Attach tiles read, bytes | 27,848,444 | 24,535,333 |
  | `blocks` units read to attach, format 8 without the column | 44,330,095 | 22,828,363 |
  | ...with the sound reader rule below | 13,036,693 | 8,025,901 |
  | ...with `hapBp` | 0 | 0 |
  | Windows reading a `blocks` unit to attach, of 180 | 87 | 103 |
  | ...with the sound reader rule | 63 | 44 |
  | Worst window, `blocks` bytes read to attach | 2,879,401 | 1,665,231 |
  | ...with the sound reader rule | 365,413 | 273,988 |

- **The window that broke ADR 0012's limit.** CHM13
  chr2:92,077,080-92,078,080, nothing loaded: 4,539,070 bytes read
  against a `bytesFor` of 3,125,787; 3,174,321 with the column, the
  difference from `bytesFor` being the attach tiles
  ([rules.txt](../walks-container/hapbp/results/rules.txt))
- **A cut that needs a piece's end and has no rule for it.** GRCh38
  chr6:32,570,392-32,571,392, four named haplotypes expanded: the cut
  trims a line at a piece it doesn't load and states the bp past the
  trim, which needs where that piece ends. It reads 656,120 bytes,
  423,965 of them one `blocks` unit, under format 8 as it was and under
  every reader rule tried; 232,155 with the column, where format 7 and
  graph-walks 6.2 read 241,130
  ([scan.txt](../walks-container/hapbp/results/scan.txt),
  [four-grch38.txt](../walks-container/hapbp/results/four-grch38.txt))
- **Bytes, simulated.** The abridged tiles grow 173,136 and 175,880
  bytes, 0.26% and 0.37% of their own size and 0.015% and 0.016% of all
  tiles, 2.65 and 2.38 bytes a row. The tile that grows most gains
  1,378 and 4,053 bytes. On pggb chrY, not hosted, 1.94% and 1.71% of
  abridged tiles
  ([alt-bytes.txt](../walks-container/hapbp/results/alt-bytes.txt))
- **Bytes, written.** gfa-to-tabix 5.0.0 on HPRC v2.1's
  Minigraph-Cactus chr22, against the format 8 file the writer made
  before the column
  ([chr22.sh](../walks-container/hapbp/scripts/chr22.sh),
  [chr22.txt](../walks-container/hapbp/results/chr22.txt)):
  - the file grows 5,737 bytes of 59,115,081, 0.0097%
  - its 18 tiles with `abridged` rows grow 5,763 bytes of 2,102,254,
    0.274%, 2.24 bytes for each of 2,572 rows; the tile that grows most
    gains 766 bytes on 87,413
  - no line differs but for the column; the `blocks`, `detail` and
    departure units keep their bytes
  - spec8 disagrees with nothing in the file, and claims7, expand7 and
    verify7 pass it. Every format 7 `abridged` row of the same graph is
    still recomputed from it
    ([against-format7.py](../walks-container/abridged/against-format7.py))
- **The writer has it for nothing.** It sums the lengths of a piece's
  steps where it writes the row, with no pass and no state added
- **The checks fail when broken.**
  - The build reads back each `blocks` list and refuses a `hapBp` its
    items don't add up to
  - Nine broken files, each failed by every checker
    [cases.tsv](../departures/scripts/broken/cases.tsv) names for it:
    `hapBp` as format 7's `bp`, as the span, off by one, 0, the next
    piece's and ending at the last step on R; a row without the column;
    and two records whose stretch is not a run at an end of a list
  - Five broken writers
    ([broken-writers.py](../walks-container/hapbp/broken-writers.py),
    [results](../walks-container/hapbp/results/broken-writers.txt)):
    with the build check each is refused; past it, the tests fail and
    claims7, audit7, expand7, spec8 and `walks-truth.py rebuild` each
    fail the files it writes
- **Adversarial graphs,** each a test: twins whose tiles and records
  differ in `hapBp` alone, with the own run before a later W line, before
  a piece on another sequence, and 700 or 690 bp of 810; three rows
  alike but for path with own runs of 7, 7 and 6 bp
  ([adv.gfa](../walks-container/hapbp/adv.gfa)); a record with own
  steps in two pieces, in two tiles and in one; a hairpin
  ([the graphs](../walks-container/hapbp/))

## Alternatives rejected

- **`hapEnd`, the piece's end on its contig, in place of its bp:** the
  same fact at 1.7 and 1.9 times the bytes, 295,316 and 339,384, and
  8,990 bytes on GRCh38's worst tile
- **`lead` and `trail`, the bp off R at the piece's ends:** fewer
  bytes, 85,074 and 63,982, and they give an own run's size. They don't
  give the piece's end, so not which piece of a line follows which, not
  the bp past a trim, and not which piece a record leaves where two of
  its line's pieces are in the tile
  ([pick-wrong.gfa](../walks-container/hapbp/pick-wrong.gfa)). They
  restate two items of the list, as the fields ADR 0012 dropped did
- **The own bp in each tile, on the departure record:** 335,186 and
  191,494 bytes more in the departure bins over abridged tiles, 8.1%
  and 5.9% of them, read by every window over those bins whether it
  attaches or not; and it answers attach alone
- **Attach information in the `blocks` unit:** that is the read to
  avoid
- **Shipping unchanged, with the sound next-piece rule:** a leave
  piece ends where the line's next piece starts, where the read holds
  that piece's row. It is never wrong. It leaves 3,416 of 11,579 and
  3,366 of 18,326 attached records on the worst windows to a `blocks`
  unit, and 53 of 357 and 17 of 269 abridged tiles an attach can name
  still need theirs. It holds of the rows a read happens to have, not
  of the file
- **The record alone, taking `ownBp` as the run:** right for 12,016 of
  12,521 and 9,815 of 10,595 pieces within the attach limit, and a false
  size for the rest, where part of `ownBp` lies between W lines, on
  another sequence or in another piece. The record of
  [twin-own-700.gfa](../walks-container/hapbp/twin-own-700.gfa) and
  [twin-own-690.gfa](../walks-container/hapbp/twin-own-690.gfa) is the
  same line
- **Picking the piece by `hapOffset`,** the last to start before
  `hapStart`: it picks a piece with none of the record's steps 506 and
  1,201 times, and gives no size
- **A different abridging boundary,** so that a record's own steps are a
  piece of their own or stay in the tile: it changes which steps a piece
  holds, so the piece numbers, the records and every row of an abridged
  tile, to answer what one number on the row answers
- **A tag after the freeze:** a format 8 reader ignores a tag it doesn't
  know, so a file without it would be format 8 too and every reader
  would keep the `blocks` read for it. The rule would hold of some
  files. No format 8 file is released, so waiting saves nothing

## Consequences

- **gfa-to-tabix 5.0.0** writes the column and refuses coordinates past
  2^53. Its file checkers read eleven columns and refuse ten
- **graph-walks 7** attaches from the row and the record, states a
  trimmed piece's bp from `hapBp`, and has a `bytesFor` that is what a
  cut reads. Until it does, gfa-to-tabix's CI job that rebuilds every
  path with graph-walks fails: it pins a format 7 reader
- **One genome rebuild,** after the reader, then ADR 0012's acceptance
  list on the rebuilt files
- **ADR 0012's 4 MB limit for a 1 kb window's read stands.** The window
  that broke it reads 3.17 MB with the column, by the simulation above;
  the rebuilt files are measured by what a cut reads
- **The format freezes with the paper,** about 2026-11-18. After that a
  change is an addition a reader ignores, or another format under
  [ADR 0011](0011-format-7-is-frozen.md)'s rules
