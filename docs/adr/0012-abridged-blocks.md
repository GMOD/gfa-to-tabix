# ADR 0012: Walk format 8: an abridged piece's shape in a `blocks` row

- **Status:** accepted, 2026-11-11. gfa-to-tabix writes it; no file in
  format 8 is hosted or released until graph-walks, bandage-core and the
  plugin read one end to end and the acceptance test below passes
- **Amended by:** [ADR 0013](0013-abridged-hapbp.md), 2026-11-12, which
  adds `hapBp`, the piece's bp on its contig, to the `abridged` row.
  The amended lines are marked below
- **Decides:** walk format 8. Each tile with `abridged` rows has a
  `blocks` unit whose rows give each moved piece as a chain on the
  reference; the `abridged` row keeps only what a reader needs to find
  and cost the piece's detail record; and what a reader and a viewer may
  say about a piece whose steps aren't loaded
- **Keeps:** every other unit and row of format 7, byte for byte
- **Supersedes:** [ADR 0011](0011-format-7-is-frozen.md)'s freeze of
  format 7, under its own rules, and [ADR 0004](0004-abridged-detours.md)'s
  summary row
- **Trigger, under ADR 0011:** graph-walks 6.2 and bandage-core, cutting
  the hosted GRCh38 and CHM13 files, state false things about abridged
  pieces. The findings came from reviews of those consumers, not from a
  user, and the user authorised a format change, with existing readers
  and files counting for nothing and a week before the paper freezes
  the format

## Context

- Format 7's `abridged` row summarised a moved piece by its first and
  last steps on R, the bp between them and its step count. graph-walks
  and bandage-core read that as where the piece lies, how long it is
  there and which way it runs, which it isn't for a piece that doubles
  back, jumps or turns
- On the hosted files that made the every-haplotype view state, for
  pieces not loaded
  ([handoff](../handoff/2026-11-11-abridged-pieces.md)):
  - absence where they step: 336 of 463 haplotypes at
    chr2:91,409,000-91,410,000
  - blocks where they have no step
  - sizes 65-73× the true bp at the median
  - hairpins on one node as megabase excursions
  - strand from the ends
  - forms with no cover
- The four-haplotype default loads its pieces and is not affected
- Abridging is rare. 461 of 47,140 GRCh38 tiles and 563 of 47,579 CHM13
  tiles have detail units, and their detail runs a median 363 / 466 KB a
  tile, 14.9 / 12.1 MB at worst

## Decision

[walks-format.md](../walks-format.md) is the specification; this is what
changed and why.

### The `blocks` unit and row

- **The unit:** each tile with `abridged` rows has one `blocks` unit,
  named by the tile's start, after the tile's detail units in file
  order. It is a unit of format 8, not an optional addition: a tile with
  `abridged` rows and no `blocks` unit is a broken file
- **Its rows:** `seq start end blocks path fragStart piece list`, one
  per `abridged` row, keyed and ordered as they are
- **`list` is the piece in path order,** its steps gathered into two
  kinds of item:
  - a block, `<d><+|-><len>`: a maximal run of consecutive steps on R,
    each beginning on the base the last ended on, all one way. `d` is
    where it begins on R less where the block before ended, `+` along R,
    `-` against it, `len` its bp
  - a run off R, a bare number: the bp of consecutive steps with no
    place on the tile's R
- **It is a chain,** as UCSC's chain format and a PAF `cg` tag give one,
  with a direction on each block and a `d` that can be negative, so a
  piece that turns or jumps back stays one row. On chr22 every row
  converts to a `cg` string, at 0.99 times the bytes
  ([prior art](../walks-container/abridged/reviews.md#prior-art))
- **What it determines is proved:** with its tile's `ref` rows, the
  piece with each run off R as its bp, and nothing else
  ([proof](../walks-container/abridged/blocks-proof.md)). What a loaded
  piece has beyond it is which nodes make up each run

### The `abridged` row

- `seq start end abridged path fragStart hapOffset piece nsteps detail`:
  the leading columns of the piece's walk row in its detail record, and
  the record's number. ADR 0013 adds `hapBp` between `nsteps` and
  `detail`: the bp of all the piece's steps, which is not the `bp`
  dropped here
- **Gone from format 7's row:** `bp` and the two end steps, which the
  list and the `ref` rows give
- **Changed in meaning:** `start end` is the span of all the piece's
  steps on R, where it was the two end steps'; `hapOffset` is where the
  piece starts on its contig, as on a walk row, where it was where its
  first step on R begins. On chr22 the old `hapOffset` was not the
  piece's start in 113 pieces, and `hapOffset` to `hapOffset + bp` was
  not the whole piece in 1,089 of 2,572
- **Why it stays in the tile:** a cut of a few named haplotypes reads
  the tile and loads their detail records. It needs the key, the cost
  and the record's number. This said such a cut never reads the `blocks`
  unit, which the genome files showed false: 12 and 11 of 60 cuts of
  four named haplotypes on the worst tiles read one. graph-walks sent
  every moved piece it met and didn't load through the unit, which a
  reader rule over the `abridged` rows spares; and a cut that trims a
  line at a piece it doesn't load needs that piece's end, which
  [ADR 0013](0013-abridged-hapbp.md) puts on the row as `hapBp`

### Readers and viewers

- **graph-walks:**
  - refuses any format but 8 at open
  - builds an unloaded piece from its `blocks` row and the tile's `ref`
    rows as an ordinary fragment, each run off R one placeholder step of
    known bp and unknown identity
  - keeps it where one of its blocks overlaps the drawn stretch
  - computes departures, gaps, forms and contained cuts from those steps
  - expands only the pieces a window or an attach needs
- **bandage-core:**
  - draws an unloaded piece's runs in the geometry a loaded one gets
  - styles runs off R "not loaded" and states exact sizes
  - never says two unloaded rows carry the same sequence, nor that a run
    is sequence the reference lacks
- **The plugin:** offers the load action on every row with unloaded
  runs. `EXPAND_NAMED_MAX` stays, since the graph view needs node
  identities

## How it was decided

Each step's criteria were written before its deciders ran; the files are
in [walks-container/abridged/](../walks-container/abridged/).

- **A summary to draw from, not loading.** Two blinded deciders split
  between a reader-only fix with budgeted loading and exact blocks
  ([P](../walks-container/abridged/ruling-P.md),
  [Q](../walks-container/abridged/ruling-Q.md)); a third re-measured
  both and ruled for blocks in their own unit
  ([cross-examination](../walks-container/abridged/ruling-cross.md)).
  Loading instead reads +300 KB over about 75 requests at the median and
  takes 2-7 s, and leaves 6-9% of 1 kb windows over abridged tiles
  partly unloaded
- **The whole piece.** The row first stopped at the piece's first and
  last steps on R. The reader built on it differed from the loaded cut
  wherever a piece went on off R: 23% and 34% of the hosted graphs'
  abridged pieces do, 32 and 37 kb at the median
  ([ruling](../walks-container/abridged/ruling-piece-ends.md))
- **Runs as items of the list.** The end runs were columns for a few
  hours, beside a suffix on each block that said the same kind of thing.
  Two deciders moved every run into the list
  ([1](../walks-container/abridged/ruling-final-row-1.md),
  [2](../walks-container/abridged/ruling-final-row-2.md)); deltas
  against absolute starts were measured, 2.4 times smaller
  ([bytes](../walks-container/abridged/list-grammar.chr22.txt)). They
  split on `>` and `<` for a block's direction, as did two later
  reviewers, so the signs stay, as PAF and this format's departure rows
  write a strand
- **Format 8.** The unit was first added under `format:i:7`, as a later
  addition a released reader skips
  ([1](../walks-container/abridged/ruling-declaration-1.md),
  [2](../walks-container/abridged/ruling-declaration-2.md)). That
  weighed released readers, which the owner had never asked for. With
  them counting for nothing, two deciders ruled for format 8 and the
  slimmer `abridged` row
  ([1](../walks-container/abridged/ruling-format8-1.md),
  [2](../walks-container/abridged/ruling-format8-2.md),
  [criteria](../walks-container/abridged/format8-criteria.md)): one
  check at open in place of a table scan, and no field kept that the
  list states or that means something narrower than it looks
- **Reviewed as a whole,** twice the same day: one review found the plan
  hosting before integrating, and the order changed
  ([Consequences](#consequences)); another found the end state right and
  nothing to put back, and a third that the file is GFA's W lines
  re-encoded for range access and not a rebuilding of them, with the
  list a chain under another name
  ([reviews](../walks-container/abridged/reviews.md))

## Evidence so far

- **The first-built row on both genomes.** Both hosted graphs were
  rebuilt on ada with the unit as first built, under format 7
  ([script](../walks-container/abridged/genome-blocks.sh), results in
  [genome/](../walks-container/abridged/genome/)): every unit but
  `blocks` and tables had the hosted file's bytes; all 74,053 and 65,396
  rows equalled graph-walks' decode of the piece's detail row; the units
  were 1.21% and 1.42% of the files, the largest 1.71 MB, against limits
  of 2% and 2 MB. Those files are deleted. The numbers are redone on
  format 8 files before anything is hosted; on chr22 the final list is
  3.5% smaller than the row measured there
- **The writer's checks fail when broken:** the build reads back every
  list; the tests decode each piece's detail row and compare; five file
  checkers, one of which expands a row as an unloaded reader does, fail
  the 74 broken files named for them; ten broken writers fail the tests
- **A reader from the spec alone** reproduced every piece of chr22 and
  of 85 small files, and found the document's faults, since fixed
  ([review](../walks-container/abridged/reviews.md#format-8-from-the-spec-alone))
- **graph-walks' branch on chr22:** its harness shows no difference
  between unloaded and fully loaded cuts in 900 pairs with every
  haplotype together, fails on a broken reader, and has passed a second
  review. Links into a run off R, which the proof says a list doesn't
  determine, are counted apart
- **Not yet shown:** any of it on the genome files, the cost of cuts on
  the worst windows, and two of the three consumers

## Acceptance, before anything is hosted

- graph-walks' equality harness shows no difference between a cut with
  nothing loaded and the same cut fully loaded, each run off R collapsed
  to its bp, on the handoff's failure windows and 1,000 random
  abridged-tile windows per genome file, plain and contained, and fails
  on a broken reader
- Its time and peak memory on chr2:91,409,000 (GRCh38) and
  chr2:92,078,080 (CHM13), every haplotype, against graph-walks 6.2 and
  against the loaded cut
- On both genome files: every unit but `blocks`, tables, the header and
  the abridged tiles has the hosted file's bytes; each abridged tile is
  the hosted one's lines but for its `abridged` rows; and each hosted
  `abridged` row is recomputed from the format 8 rows
- The `blocks` units are within 2% of each file, the largest within
  2 MB, and a 1 kb window's read within 4 MB
- A decoder written from walks-format.md alone reproduces a genome
  file's pieces, its 936 hairpins among them; chr22 has no piece that
  turns
- What a cut of four named haplotypes reads on the ten tiles with the
  largest `blocks` units, against format 7 today. Such a cut reads the
  unit where one of its haplotypes has a moved piece in the tile off
  the drawn stretch: 45 KB on one chr22 window, and up to 1.7 MB on a
  genome file's worst tile. The `abridged` row could spare it that with
  the piece's bp and end steps back, which format 8 dropped; they stay
  dropped unless this number says otherwise. Measured, 60 cuts a
  genome: 17.8 MB against format 7's 12.0 on CHM13 and 17.7 against
  13.7 on GRCh38, the worst cut 1.45 MB against 0.61 and 0.95 against
  0.39. Most of that is graph-walks loading by rule, not the format.
  What no reader rule removes is a piece's end, which
  [ADR 0013](0013-abridged-hapbp.md) puts on the row as `hapBp`; the
  end steps and format 7's `bp` stay dropped
- The file checkers and graph-walks 7 read a file with an unknown tag
  on every row, an unknown header line and an unknown unit kind as they
  read the same file without them
- bandage-core and the plugin read chr22 end to end, with before and
  after renders at chr2:91,409,000 and the four-haplotype default as a
  control shown to the user

## Alternatives rejected

- **Changing nothing:** false on every count in Context
- **Reader and viewer only, "not loaded" over a piece's detail extent,
  with loading under a budget** (ruling P): truthful, but shows nothing
  about an unloaded piece without loading, at the cost above. It is the
  fallback if the acceptance test or the cost measurement fails
- **No abridging:** 14.9 / 12.1 MB tiles in front of every view, the
  four-haplotype default included
- **The list on the `abridged` row, in the tile:** a cut of named
  haplotypes reads 28-30% more over abridged tiles, and one CHM13 tile
  grows from 40 KB to 1.6 MB
- **One row in the `blocks` unit and none in the tile:** a named cut
  must read the unit to find a detail record, or detail units must be
  named by path, which reaches outside the abridged tier
- **Format 7 with the unit as a later addition:** a reader must infer a
  missing unit from a table, three row shapes shared the number in one
  day, and the old row's misleading fields stay beside the truth
- **Absolute block starts:** 2.4 times the bytes, and GRCh38's largest
  unit past 2 MB
- **A standard format in place of the walk file:** GFA fragments per
  tile cost 32 times the bytes, tabix GAF 6.6 to 32 times and is not a
  standard layout either, and PAF rows lose node identity
- **Per-kb presence tags, tolerant blocks, or the true span alone:**
  approximate where exact blocks cost a little more
- **Spatially indexed detail units:** a redesign, unmeasured

## Consequences

- **gfa-to-tabix 5.0** writes format 8. Its version changes at release:
  a push to main with a new version in Cargo.toml publishes it, and its
  CI job that rebuilds every path with graph-walks needs graph-walks 7
- **graph-walks 7** reads format 8 only
- **bandage-core and the plugin** follow it, with before and after
  renders shown first; BandageJS, ggbandage, the tube map and jb2hubs go
  green on the exact versions
- **Order:** chr22 end to end through all three consumers, then both
  genome files rebuilt and the acceptance list above, then releases and
  the hosted swap together, with the user's go-ahead. The row changed
  twice once a first reader was built on it; two consumers are not yet
  built
- **No further rulings on the row's spelling.** A change from here needs
  a consumer failing on a real window
- **Reversal:** if the acceptance test or the cost measurement fails and
  can't be mended in the reader, no file carries format 8, the hosted
  files stay format 7, and the readers take ruling P
