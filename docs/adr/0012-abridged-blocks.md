# ADR 0012: Abridged pieces carry their blocks on the reference

- **Status:** accepted, 2026-11-11, and amended the same day: the
  `blocks` unit is a later addition to walk format 7, not a format 8
  ([How a file declares it](#how-a-file-declares-it)). gfa-to-tabix
  writes it and both hosted files are rebuilt with it on ada
  ([The rebuilt files](#the-rebuilt-files-2026-11-11)); they aren't
  hosted until the acceptance test below passes
- **Decides:** one new unit kind, `blocks`, holding each abridged
  piece's exact stretches on the reference, and what a reader and a
  viewer may say about a piece whose steps aren't loaded
- **Keeps:** walk format 7 whole: its number, and its tiles, `abridged`
  rows, detail units, departure blocks and tables, byte for byte
- **Trigger, under [ADR 0011](0011-format-7-is-frozen.md):** a consumer
  on a hosted file. graph-walks 6.2 and bandage-core, cutting the hosted
  GRCh38 and CHM13 files, state false things about abridged pieces, and
  the user authorised a format change if it won. ADR 0011's ship gate
  holds: the plugin and bandage-core read format 7 from the hosted files
- **Measured by:** the findings in
  [the handoff](../handoff/2026-11-11-abridged-pieces.md); two blinded
  Fable deciders against [criteria written first](../walks-container/abridged/decision-criteria.md),
  which split ([P](../walks-container/abridged/ruling-P.md),
  [Q](../walks-container/abridged/ruling-Q.md)); a third that
  re-measured both and ruled ([cross-examination](../walks-container/abridged/ruling-cross.md));
  the gate below, run over every abridged tile of both hosted files; and
  two more blinded deciders on the declaration alone, against
  [criteria written first](../walks-container/abridged/declaration-criteria.md),
  which agreed ([1](../walks-container/abridged/ruling-declaration-1.md),
  [2](../walks-container/abridged/ruling-declaration-2.md))

## Context

- An `abridged` row summarises a moved piece by its first and last steps
  on R, its `bp` and its `nsteps`. graph-walks and bandage-core read that
  summary as where the piece lies, how long it is there and which way it
  runs, which it isn't for a piece that doubles back, jumps or turns
- On the hosted files that makes the every-haplotype view state, for
  pieces not loaded:
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

### The `blocks` unit

- **The new unit:** each tile with `abridged` rows has one `blocks`
  unit, named by the tile's start, after the tile's detail units in file
  order, its `start end` the hull of its rows
- **Its rows:** `seq start end blocks path fragStart piece list`, one per
  `abridged` row of the tile, keyed by `path`, `fragStart` and `piece` as
  the `abridged` row is, `start end` the hull of its blocks
- **What a block is:** a maximal run of consecutive steps of the piece on
  R, each starting where the last ended on R, all in one direction, with
  no step off R between
- **How `list` writes them:** the blocks in path order, comma-separated,
  each as `<d><+|-><len>[:<own>]`:
  - `d`: where the block begins on R (its first base in path order, the
    high end for `-`), less where the previous block ended, or less 0 for
    the first
  - `+` along R, `-` against it
  - `len`: its bp
  - `own`: the haplotype's bp between the previous block and this one,
    omitted when 0
- **Guarantees, checked at build:**
  - Σ`len` + Σ`own` equals the `abridged` row's `bp`
  - the first block begins at the `start` step and the last ends at the
    `end` step
  - the blocks equal those the detail unit's walk row decodes to
- **Everything else is format 7's.** A window read selects `blocks`
  units by extent as it does tiles; it reads them only when it keeps
  unloaded pieces

### How a file declares it

- **The header stays `#walks format:i:7`,** with no new tag. The spec
  already says a unit kind it doesn't give is a later addition, which a
  reader skips, and that later additions are tags, unit kinds or files.
  A file's tables list its `blocks` units, and that is the declaration
- **A reader released before the unit** reads a file that carries it as
  it reads one that doesn't: graph-walks 6.2 selects units by kind and
  never reads a kind it doesn't know. So the hosted files can be swapped
  before any reader is released, and no released reader ever refuses
  the file the paper cites
- **A reader that draws from blocks** refuses a sequence whose table
  lists a detail unit `cs:d` and no `blocks` unit `cs`, naming the
  gfa-to-tabix version to rebuild with. It has no second drawing path
  for such a file
- **A file with no abridged tile** is the same bytes from either writer
- **The spec's wording:** "a file with a row kind this page doesn't give
  is another format" gains "in a unit this page gives", which is what
  graph-walks 6.2 checks; and a table that leaves out an abridged tile's
  `blocks` entry is one a reader can tell

### Readers and viewers

- **graph-walks:**
  - keeps an unloaded piece where one of its blocks overlaps the drawn
    stretch
  - builds its reference steps from the blocks and the tile's `ref` rows,
    and each own run as one step of known bp and unknown identity
  - computes departures, gaps, forms and contained cuts from those
  - `expand` reads only detail units whose extent overlaps the window
    and its context
  - refuses a sequence with a detail unit and no `blocks` unit for its
    tile
- **bandage-core:**
  - draws an unloaded piece's runs in the geometry a loaded one gets
  - styles own runs "not loaded" and states exact sizes
  - never says two unloaded rows carry the same sequence: 0.3% of
    piece-windows match by blocks and differ in own nodes
- **The plugin:** offers the load action on every row with unloaded
  runs. `EXPAND_NAMED_MAX` stays, since the graph view needs node
  identities

## Gate, run 2026-11-11

`blocks-gate.ts` over all 461 + 563 abridged tiles of the hosted files on
ada ([script](../walks-container/abridged/blocks-gate.sh), per-tile
results in `blocks-gate.grch38.jsonl` and `blocks-gate.chm13.jsonl`):

| | GRCh38 | CHM13 | Limit |
|---|---|---|---|
| `blocks` units, total | 13.2 MB, 0.84% of the file | 19.4 MB, 1.10% | 2% |
| Largest `blocks` unit | 484 KB | 1.58 MB, chr2:92,078,080 | 2 MB |
| Largest tile with its `blocks` unit | 594 KB | 1.62 MB | a 1 kb window ≤ 4 MB |
| Pieces failing Σlen + Σown = bp | 0 of 74,053 | 0 of 65,396 | 0 |

- **Window bound:** a 1 kb window spans at most two of those tiles, so
  about 3.2 MB plus its departure blocks
- **Acceptance test of the build:** the gate's last condition can only
  run against the built reader. Rows built from blocks must equal the
  loaded rows on the failure windows of the handoff plus 1,000 random
  abridged-tile windows per file. The cross-examination's prototype
  matched 2,344 of 2,344 rows over five windows

## The rebuilt files, 2026-11-11

Both hosted graphs rebuilt on ada with the writer of the `blocks-unit`
branch ([script](../walks-container/abridged/genome-blocks.sh), results in
[genome/](../walks-container/abridged/genome/)):

| | GRCh38 | CHM13 | Limit |
|---|---|---|---|
| Units other than `blocks` and tables | the hosted file's bytes | the hosted file's bytes | the same bytes |
| `blocks` units | 461, one per abridged tile | 563, one per abridged tile | |
| `blocks` rows equal to graph-walks' decode of the detail row | 74,053 of 74,053 | 65,396 of 65,396 | all |
| `blocks` units, total | 19.2 MB, 1.21% of the file | 25.4 MB, 1.42% | 2% |
| Largest `blocks` unit | 1.71 MB, chr2:91,422,720 | 1.62 MB, chr2:92,078,080 | 2 MB |
| Largest two adjacent `blocks` units with their tiles | 2.14 MB | 3.31 MB | a 1 kb window ≤ 4 MB |

- **The units are larger than the gate's estimate,** which gzipped each
  unit as one stream: 45% and 31% in total, and GRCh38's largest 3.5
  times its 484 KB. The file's BGZF members deflate 64 KB at a time, so
  a row can't borrow from one in the member before. Every limit still
  holds
- **The check is independent of the writer:**
  [blocks-check.ts](../walks-container/abridged/blocks-check.ts) decodes
  each piece's detail row with graph-walks 6.2 and derives its blocks. A
  file without `blocks` units fails it, every row missing

## Alternatives rejected

- **Changing nothing:** fails Truth on every count above
- **Reader and viewer only, "not loaded" by detail extent, with
  auto-loading under a 2 MB budget** (ruling P):
  - passes Truth, but shows nothing about an unloaded piece without
    loading
  - its loading reads +300 KB and about 75 requests a window at the
    median, 2-7 s on the hosted file
  - it leaves 6-9% of 1 kb windows over abridged tiles partly unloaded,
    and 16-24% at 100 kb
- **`blocks` as a column on `abridged` rows** (ruling Q): adds 1.58 MB
  to one 40 KB CHM13 tile, so every window there reads it
- **`format:i:8`,** as this ADR first said: every released reader would
  refuse the file at the hosted URL after the swap, and the next reader
  would refuse a 4.0.0 file with no abridged tile, for a change the spec
  calls a later addition. The number came from ruling Q's column on
  `abridged` rows, which was another format; the cross-examination moved
  the data to a unit and kept the number
- **A `blocks:i:1` header tag:** says nothing the tables don't, since
  every abridged tile has a detail unit
- **Per-kb presence tags, tolerant blocks, or the true span alone:**
  approximate where exact blocks cost a little more, and the true span
  says no more than the detail extent already does
- **Spatially indexed detail units:** a redesign, unmeasured; left to
  open problems if the need returns

## Consequences

- **gfa-to-tabix:** a minor release that writes `blocks` units with
  the guarantees above checked at build, and a checker claim with its
  recorded failure on a broken writer. Both hosted files are rebuilt on
  ada
- **Swap:** the rebuilt hosted files go up first, once graph-walks 6.2
  returns the same cuts from them as from today's, which their unchanged
  units make checkable
- **graph-walks:** a major release, since it refuses abridged files
  without `blocks` units
- **bandage-core and the plugin:** follow it, with before/after renders
  shown first
- **Other consumers:** BandageJS, ggbandage, the tube map and jb2hubs go
  green on the exact versions
- **After the paper:** the format is still 7, and what it allows later
  is what it allows now: tags, unit kinds and files that a released
  reader skips
- **Reversal:** if the build fails the acceptance test, or the real
  `blocks` units exceed the gate's limits, no file carries the unit and
  readers take ruling P
