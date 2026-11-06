# ADR 0010: The walk file is gzip units with a unit table, not a Tabix file

- **Status:** accepted, 2026-11-05; confirmed genome-wide on GRCh38 and
  CHM13 the same day ([Genome-wide](#genome-wide)), which also amended how
  a reader finds a departure's own steps. Walk format 7, for gfa-to-tabix
  4.0 and graph-walks 6, being written
- **Decides:** how a walk file is stored and indexed, what the first three
  columns of its lines mean, how a reader finds the rows for a window, and
  what a writer guarantees. The rows' own columns and decoding rules stay
  format 6's ([ADR 0009](0009-departure-records.md))
- **Measured by:** four independent reviews, two independent arbiters who
  each built every candidate and measured it with their own HTTP
  range-logging harness on the same seeded windows, a cross-examination in
  which each arbiter rebuilt and measured the other's winner, and an
  independent prior-art and failure-mode review. Inputs: the gfa-to-tabix
  3.0.0 files for HPRC v2.1 Minigraph-Cactus chr22 and HPRC release 2 pggb
  chrY, on GRCh38. Everything is in [docs/walks-container/](../walks-container/)
- **Supersedes:** format 6's filing of every row at its chunk's first base
  (`seq cs cs+1`), its `.tbi`, the `seq~departure` and `seq~cs` sibling
  sequences, the `#long` and `maxnode` header lines, and the readers'
  chunk-before rule

## Context

- Format 6 files every row of a 64 kb chunk at `seq cs cs+1`. Drawing the
  file's real rows for the README made the problem plain: every row of the
  toy graph reads `GRCh38#0#chr1 0 1`, and a plain
  `tabix file chr1:15-35` returns nothing (98 of 100 1 kb windows on MC
  chr22). Only a reader that rounds to chunk starts gets rows
- The key came in 3953bb1 on 2026-10-08, the day after 10d3ae1 filed whole
  spans, with one sentence and no measurement: a full-span row shares a
  Tabix bin with the next chunk. 842a19b then made readers query from the
  chunk before. No ADR recorded either
- Measured now, the one-base key saved nothing: the same rows refiled at
  the chunk's span with a matched index fetch identical bytes. The bytes a
  small window wastes come from the chunk-before read, from @gmod/tabix
  reading one BGZF block past each chunk (no chunk starts a block), and on
  pggb from departure reads sized by the file-wide `maxnode` (1 Mb on
  chrY)
- Format 6 is a store of units that decode only together, a chunk's routes
  and walks, addressed through a coordinate index by a fake coordinate.
  Tabix's contract is "the rows overlapping this region", and the file
  breaks it

## Decision

The walk file is a series of gzip units with a table of their byte ranges,
the structure of a CRAM file's containers and its `.crai`. Every line states
its sequence and the stretch of it the line is about.

### Files

- `<prefix>.<sample>.walks.gz`: the data, a series of units, each a whole
  run of gzip (BGZF) members, then a BGZF EOF block
- `<prefix>.<sample>.walks.gz.idx`: the directory, plain text:
  - line 1: the data file's `#walks` line plus `bytes:i:<data file length>`
  - `#header 0 <length>`
  - one `seq <offset> <length>` line per reference sequence, giving its
    table unit. Every reference sequence is listed; one with no units has a
    table holding only its `#unit` line

### Units

- **The header unit,** first, from byte 0: `#walks format:i:7 tile:i:65536
  revisited:i: stay:i: abridge:i: abridgebytes:i:`, then the `#reference`,
  `#haplotype` and `#hole` lines. No `#long`, `chunk` or `maxnode`
- **Per reference sequence,** in file order: its `tile`, `departures` and
  `detail` units, then its `table` unit
- **Every unit but the header** starts with `#unit seq start end kind
  name`, so the file delimits itself and the tables can be rebuilt by
  walking its gzip members, as a `.fai` can be rebuilt from its FASTA
- **`tile`:** one tile of `tile:i:` bp, holding the rows format 6 writes for
  a chunk. `start end` is the tile's true extent, the union of its rows':
  it can begin after the nominal start and run past the tile's end, so a
  node or a pass longer than a tile needs no `#long` line and no reach
  rule. `name` is the nominal start. Readers address tiles by extent, never
  by `floor(base / tile)`
- **`departures`:** one block of the departure pyramid, 64 kb × 8^L (64 kb,
  512 kb, 4 Mb, 32 Mb). `start end` is the block, `name` its size. A record
  goes in the largest aligned blocks inside its tile-rounded extent: from
  `floor(start / T) × T` to `ceil(end / T) × T`, taking at each point the
  largest block aligned there that fits. Its lines in different blocks are
  identical. The pyramid is the writer's choice; readers only fetch the
  units overlapping their window
- **`detail`:** one abridged path's moved pieces in one tile, ADR 0009's
  detail record. `name` is `cs:d`, the tile's nominal start and the
  `abridged` row's detail number; `start end` is the union of its pieces'
  spans
- **`table`:** after its `#unit` line, one line per unit of the sequence in
  file order, `#entry seq start end kind name offset length`, the offset
  and length in compressed bytes as decimal text. Readers scan it

### Lines

Every line not starting with `#` begins `seq start end`, the reference
sequence and the stretch of it the line is about, then format 6's columns
from `kind` on, unchanged. These columns are data, not an index key, so
`zcat | grep` places any line.

| kind | `start end` |
|---|---|
| `walk` | the piece's span on the tile's reference path: the first base of its first placed step to the last base of its last; route interiors that hold another chunk's reference nodes lie outside it |
| `abridged` | the moved piece's stretch on the reference path |
| `ref`, `nodes`, `route` | the tile's extent: these are the tile's dictionary rows and have no span of their own |
| `departure` | the first base of its first end node to the last base of its other end node, or the breakpoint stretch if wider |

### Reading a window

For a window `[s, e)` with context `c`, `D = [s − c, e + c)`:

- At open, GET the directory and refuse any format but 7; GET the header
  unit and the sequence's table in parallel; refuse when the directory's
  line 1 differs from the header's `#walks` line or its `bytes` from the
  Content-Range total
- Select the `tile` and `departures` units with `start < D.end` and
  `end > D.start`, skipping any of length 0; merge byte ranges that touch,
  and GET each as one single-range request, never a multi-range one
- Gunzip each unit. Decode a tile's rows from `kind` on by format 6's
  rules. Keep the departure lines overlapping `D` and drop exact
  duplicates
- An attach fetch reads the tile holding the record's own steps, which
  the record names; expanding an abridged piece reads the `detail` unit
  `cs:d`. The tile is not always the one holding the leave base: for a
  record that jumps back along the reference, the contig's piece order
  can file its own steps on the rejoin side ([Genome-wide](#genome-wide))
- There is no chunk-before rule, no `maxnode`, no `#long` widening and no
  reach

With stock tools:

```
awk -F'\t' -v s="GRCh38#0#chr22" '$1==s {print $2, $3}' f.walks.gz.idx   # a sequence's table
tail -c +$((off+1)) f.walks.gz | head -c $len | gzip -dc                  # any unit
zcat f.walks.gz | awk -F'\t' '$1=="GRCh38#0#chr22" && $2<20001000 && $3>20000000'
```

### What a writer guarantees

- The header, the units, the tables and the EOF block partition the file;
  every unit starts and ends a gzip member and starts with its `#unit` line
- Each table lists every unit of its sequence, in file order, before it
- A tile's extent is the union of its lines' extents; every line lies
  within its unit's `start end`; every step placed on the reference in
  `[a, b)` is in a tile whose extent overlaps `[a, b)`; every departure
  record is in every block of its cover
- Each line's `start end` agrees with its decoded steps, checked at build
  as format 6's encode-decode check is, on every row
- Names hold no tab or newline and don't start with `#`; the build refuses
  any that do
- Offsets and lengths are exact integers below 2^53; files pass 2 GiB
  (CHM13's is 1.78 GB), so writers, readers and checks stream and never
  hold a whole file
- Every unit's name is unique within its kind and sequence
- The data file is written, then the directory, each under a temporary
  name and renamed

### Hosting

- Versioned file names, so a data file and a directory from different
  builds never meet
- Single-range requests only: CloudFront answers a multi-range request
  with the whole object

## Evidence

All from [docs/walks-container/](../walks-container/). The arbiters'
tables come from per-window results under `arbA/results/` and
`arbB/results/`, summarised by the scripts beside them.

### Bytes per window

Arbiter A's harness, 300 seeded windows per size, real HTTP range requests,
KB median / p90, walk and departure reads only (`arbA/results/res/`,
`res4/`):

| | MC 1 kb | MC 1 Mb | pggb chrY 1 kb | pggb chrY 1 Mb |
|---|---|---|---|---|
| format 6 as shipped | 95 / 145 | 570 | 1545 / 2850 | 2425 |
| T64b, arbiter B's amended Tabix design | 30 / 57 | 519 | 121 / 285 | 772 |
| format 7 (S7) | 29 / 53 | 505 | 70 / 246 | 738 |

- With attach fetches, format 7 reads 30 / 243 KB at MC 1 kb and 389 /
  1358 KB at pggb 1 kb, against T64b's 32 / 255 and 618 / 1301
- Arbiter B's harness, its own windows (`arbB/decision.md`, `## S7
  check`), 1 kb with attach fetches: MC S7 31 / 152, T64b 31 / 157; pggb
  2.78–26.67 Mb S7 418 / 1389, T64b with a 4 kb reach 444 / 1311
- The one quantile where format 7's read is not the lowest is pggb 1 Mb
  p99: 5,978 KB against T64b's 5,849
- Requests per window: one GET on MC at the median (T64b two), about 10 on
  pggb with attach fetches (T64b 11); at most two round trips (T64b three)

### Size and open cost

| | MC chr22 | pggb chrY |
|---|---|---|
| data file, format 7 | 59.31 MB | 187.92 MB |
| data file, format 6 as shipped | 59.17 MB | 192.15 MB |
| read at open, format 7 | 48.6 KB in 2 round trips | 22.1 KB |
| read at open, T64b | 87 KB in 1 | 76 KB |

- Format 7 reads one sequence's table at open; a Tabix reader reads the
  whole index. Genome-wide, arbiter A estimates chr1's table at about
  230 KB (the genome-wide build replaces this estimate)
- The `seq start end` columns cost 2.6% of the file on MC and 1.9% on
  pggb over the same layout without them; giving each `route` row its own
  span instead of the tile's cost 68.7 against 59.3 MB on MC and 24% more
  bytes per 1 kb window, for nothing a reader uses

### Correctness

- 0 wrong pieces and 0 missing departure records on 96 windows per
  dataset, decoding format 7 against format 6
- graph-walks 5.0.2's own `cut` over format 7's units and over format 6's
  rows for the same units: identical on 90 of 90 random and 365 of 365
  targeted windows on each of MC and pggb, the targeted windows covering
  LCR22A–D, 22q11, the chrY ampliconic palindromes, the long-node
  centromere, the X-transposed region and 160 strand-switch records
  (`arbA/results/res5/`)
- Against graph-walks 5's own read rule, every difference is the shipped
  rule reading more: the chunk before, and departures ±`maxnode`
- `verify7.mjs` passes the release checks on both files: 3,837 units and
  1,958,554 lines on MC, 1,492 units and 3,126,030 lines on pggb

### Genome-wide

A second session built the prototype's format 7 from the genome-wide
3.0.0 files, GRCh38 from the GRCh38 graph and CHM13 from the CHM13 graph,
and measured it against format 6
([report](../walks-container/genome/report.md), results in
`genome/res/`):

- A first view, opening the file and reading one 1 kb window, costs 3% to
  12% of format 6's: 211 against 1,841 KB on GRCh38 chr1, 62 against 1,838
  on chr22, 118 against 1,815 on CHM13 chr9. Opening reads an 8 KB
  directory, the header and one sequence's table (183 KB for GRCh38 chr1,
  176 KB for CHM13's); all the tables together are 2.15 and 2.13 MB,
  against the `.tbi`'s 1.75 and 1.71 MB, and no reader fetches them at once
- Format 7 reads fewer bytes at every window set and quantile: GRCh38 chr1
  1 kb 25 / 34 / 78 KB (median / p90 / p99) against 76 / 106 / 204; CHM13
  chr14 13–14 Mb, 1 kb with attach fetches, 296 / 385 / 475 against
  771 / 1,024 / 1,104; at most two round trips against three
- 0 wrong of 600,549 pieces and 0 missing of 117,877 departure records on
  800 windows, among them CHM13 chr9 38–80 Mb and chr14 13–14 Mb.
  graph-walks 5.0.2's cut over format 6's rows for exactly format 7's
  units: 784 of 800 identical, all 16 differences the attach-decode bug,
  800 of 800 with it fixed
- Files 0.7% to 1.7% larger than format 6 with its `.tbi`; departure lines
  repeated 2.12× and 2.14×, 3.3% to 3.6% of the file; the largest tile
  315 KB (CHM13 chr15), departure block 36 KB, detail unit 117 KB; no tile
  reaches more than 1,023 bp past its nominal 64 kb; the largest offset
  1.78 GB
- It found the jump-back case above: on CHM13 near chr14 13.20 Mb, record
  NA19185#2 leaves at 13,472,637 and rejoins at 13,135,857, and its own
  steps lie in tile 13,107,200, on the rejoin side. A fetch of the leave
  tile misses them; format 6's wide read happened to cover them
- Six windows show two fragments where format 6's lookback joined them
  through steps 80–92 kb outside the window, nothing in the window
  missing: the overlap rule reads only what overlaps
- The converter it used gave 10,993 of GRCh38's 66,981 detail units and
  1,592 of CHM13's 60,782 a shared name; no check expanded detail units,
  so nothing above depends on it. The writer names them uniquely

## Consequences

- **Walk format 7 is a format break.** The rows inside a tile decode as
  format 6's, so graph-walks' `cut` keeps its return shape: the five
  consumers (the graph plugin, BandageJS, ggbandage, the tube map,
  jb2hubs) change the line that opens the walk file and their version pin,
  not their code
- **gfa-to-tabix 4.0:** `--walks` writes the units, the tables and the
  directory, with the in-stream `#unit` lines; the header drops `#long`,
  `chunk` and `maxnode` and gains `tile`; departure records keep
  `departures.rs`'s cover, filed in pyramid units with their end-node
  extents; detail records become `detail` units; no `.tbi`. The writer
  checks every line's extent against its decoded steps, and the release
  checks of `verify7.mjs` become tests and an audit step.
  [walks-format.md](../walks-format.md) is rewritten for format 7, and the
  README's walk figure is drawn from the writer's output
- **graph-walks 6:** a source that reads the directory, the tables and
  byte ranges in place of `TabixIndexedFile`, with `WalkReader.open(url)`
  and `WalkReader.fromFilehandles({ data, table })` so a consumer's change
  is one line; tiles addressed by extent and `decoded` keyed by unit, never
  by `floor(base / chunk)`; no chunk-before rule, `maxnode`, `#long` or
  reach; refuses format 6; `pnpm release-check` reads format 7. The
  attach-decode bug (two records whose leave chunks are adjacent) is fixed
  before the release
- **Hosted data:** the genome-wide format 6 builds in `~/work/genome3`
  are superseded; GRCh38 and CHM13 are rebuilt with 4.0, and the cutover
  that was held for this ADR proceeds on format 7
- **Lost:** `tabix`, htslib's region API and pysam no longer read the walk
  file; a unit comes out with `awk`, `tail`, `head` and `gzip`, and any
  line is placed by `zcat | awk`. No tool read format 6's rows usefully
  either, since a plain query returned nothing
- **Kept on Tabix:** the node/link index (`.graph.bed.gz`), whose rows are
  real intervals ([index-format.md](../index-format.md)). The @gmod/tabix
  fix that stops a read at a chunk's end when the next starts a block goes
  upstream for it and every other Tabix user
- **Not fixed here:** on pggb most of a small window's bytes are departure
  records and attach fetches from collapsed-repeat hops, which every
  container pays; that is a record and placement question
  ([open problems](../open-problems.md))

## Alternatives rejected

- **Format 6 with reader fixes (F6p):** the same bytes as Tabix filed at
  the chunk's span, which shows the one-base key never saved anything; it
  keeps the fake key, two sibling sequences, the chunk-before rule and a
  client patch. 36 against format 7's 29 KB at MC 1 kb, and 292 KB in 3
  round trips against 70 KB in 1 at pggb 1 kb (arbiter A)
- **Tabix at the chunk's span with a CSI whose leaf is the chunk (T64,
  then T64b):** arbiter B's first choice. It reaches format 7's bytes only
  with departure rows filed at their pyramid block's interval, detail
  records under a sibling sequence at a made-up coordinate (`detail ×
  chunk`), rows that claim the chunk's span while overhanging it by
  `reach`, `#long`, a writer-built CSI that re-indexing with `tabix`
  degrades, and a patched client (58 against 28 KB at MC 1 kb without the
  patch). After the cross-examination arbiter B accepted format 7: "there
  is no byte, request or round-trip reason to prefer T64b"
- **Tabix at each row's real extent:** the only filing a plain region query
  answers exactly, at 3.3× the bytes, since wide rows climb Tabix's bins
- **16 kb tiles under TBI (T16):** against 64 kb under CSI, 6 KB cheaper at
  MC 1 kb, then 37% dearer at 100 kb and 90% at 1 Mb (1,004 against
  530 KB), and a 20% larger file (arbiter B)
- **A plain chunk table (O):** format 7 without true extents or the
  departure pyramid; its departures still need widening and a second index
  (281 against format 7's 70 KB at pggb 1 kb)
- **Interval-native site rows (N, the native review):** the smallest file
  (47.3 against 59.2 MB on MC) and the best pggb 1 Mb median, but p90 121
  against format 7's 53 KB at MC 1 kb, up to three round trips, a visit index not yet
  designed for the 60% of pggb departures it can't place (11 of 60 pggb
  windows wrong without it), and paths rebuilt by chaining site rows
  across rows and cells
- **Self-contained lines, SAM-style (Srel, Sabs):** every line decodable
  alone, at 3.1× and 4.5× the bytes on MC, because gzip cannot recover the
  route dictionary or the delta ids. Format 7 keeps both inside a tile,
  where they are the unit of meaning, as a CRAM slice's compression is
- **Detail records sharing routes by reference:** repeated routes are
  3.5 MB of MC's 40 MB detail tier, whose bulk is `nodes` rows; a
  cross-reference would add a dependent fetch to save disk, not window
  bytes

## History

- 2026-10-08: 10d3ae1 files walk rows at whole chunk spans; 3953bb1 files
  them at `seq cs cs+1` the same day, with no measurement; 842a19b makes
  readers query from the chunk before
- 2026-11-05: format 6 ships in gfa-to-tabix 3.0.0. Drawing its real rows
  for the README raised the question; four reviews, two arbiters, a
  cross-examination and a prior-art review settled it
