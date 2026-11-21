# Walk files past 464 haplotypes

MC chr22 (HPRC v2.1 Minigraph-Cactus, GRCh38 reference) written as a GRCh38
walk file by gfa-to-tabix 5.0.1's release binary at its 464 real haplotypes
and at 2,000 and 5,000 haplotypes recombined from them, then read with
graph-walks 9.0.0 from local disk. On ada, 2026-11-20 and 21. Every number
below is printed by [scale-summary.py](scripts/scale-summary.py) from the
files beside this page ([scale-summary.txt](scale-summary.txt) is its
output) or read from the logs and outputs it links, unless it says it is an
estimate.

## Takeaways

- **A 4-haplotype view of a typical window stays under 1 MB at 5,000
  haplotypes, but not by much, and its first view does not.** At the
  three windows measured, a 100 kb view of HG00097#1, HG002#1, NA19240#1
  and HG00733#1 reads 0.09-0.12 MB at 464, 0.21-0.35 MB at 2,000 and
  0.47-0.74 MB at 5,000, or 0.26-0.31 MB with the 4 expanded, which a
  host showing a few haplotypes can ask for; with the abridge budgets
  scaled to the haplotype count it is 0.60-0.81 MB. Synthetic haplotypes
  repeat real rows, so a real cohort would read somewhat more
  - What crosses 1 MB on every view is the sequence's table, which a
    reader fetches whole before its first cut: 0.05 MB at 464, 1.94 MB at
    2,000 and 13.96 MB at 5,000. It is one `#entry` per unit, nearly all
    of them detail units
  - A 1 Mb window crosses 1 MB from 2,000 haplotypes on, whatever is kept:
    1.17-1.72 MB at 2,000, 1.67-3.98 MB at 5,000
  - So the threshold for writing up per-group units is met on the first
    view and on wide windows, not on a typical one; the write-up is
    [below](#proposal-for-the-owner-per-group-units), and it finds the
    writer's abridge budgets the larger lever
- **The default abridge budgets, which are writer policy, set how the file
  grows.** From 2,000 haplotypes on, ordinary tiles pass the 1,000,000-step
  budget by haplotype count alone, so the writer moves walks out of most
  tiles (550 of 776 at 5,000, against 18 at 464) into detail units, one
  per W line and tile, which compress poorly on their own
  - With the default budgets the file is 59.12 MB, 463.90 MB and
    1,885.27 MB at 464, 2,000 and 5,000 haplotypes, x31.89 for x10.78 the
    haplotypes; detail units are 1,749.56 MB of the largest
  - With abridging off it is 31.75 MB, 72.13 MB and 142.16 MB, and the
    table 0.02 MB at each
  - A median window costs about the same either way: an all-haplotype read
    of 100 kb is 0.61 MB with the default budgets at 5,000 and 0.59 MB with
    abridging off. Abridging still caps the outlier tiles, the largest of
    which is 0.17 MB with the default budgets and 8.22 MB without
- **"About 20 GB genome-wide at 10,000" is not borne out with the default
  budgets.** Growing the hosted genome-wide 464-haplotype file (1.58 GB) at
  chr22's measured rate gives 138.3 GB at 10,000; at the rate with
  abridging off, 11.0 GB. Both are extrapolations from one chromosome of
  synthetic haplotypes, which repeat real rows (below), so a real cohort
  would be larger
- **A 4-haplotype cut takes about 0.7-1.2 s at 5,000, against tens of ms
  at 464 and 2,000,** at every window size, because graph-walks builds a
  map of all 1,732,556 detail and blocks units on every cut; with the
  budgets scaled the same cut takes tens of ms. An all-haplotype cut takes
  1.5 s at 10 kb, 4-6 s at 100 kb and 2-4.5 minutes at 1 Mb at 5,000, but
  the browser preset refuses those past 10 kb with a zoom-in notice
- **Builds stay modest:** 43.4 s, 189.4 s and 495.6 s at 464, 2,000 and
  5,000 haplotypes on 16 threads, peaking at 1.12 GB, 4.07 GB and 9.15 GB;
  each round wrote the same bytes
- **The writer failed once and never again:** one of two identical builds
  of the 5,000-haplotype graph with abridging off stopped with `a step
  placed at 38417438 is not on the tile's reference path`. Thirty reruns,
  instrumented ones among them, all finished with the same bytes, and what
  the error read points at memory corruption rather than the writer
  ([below](#a-writer-failure-at-5000-haplotypes))
- **Per-group units would cut a few-haplotype view's tile bytes about
  eightfold (an estimate), but not what grows.** They leave the file size
  and the table, which come from abridging, and add entries to the table
  and bytes to an all-haplotype read. Budgets that scale with the
  haplotype count need no format change and give a 539.22 MB file with a
  0.24 MB table at 5,000

## The synthetic graphs

[scale-synth.py](scripts/scale-synth.py) writes every line of the real GFA
unchanged (H, S, L and all 1,131 W lines, GRCh38's and CHM13's among
them), then
appends synthetic haplotypes: 1,536 for the 2,000-haplotype graph and 4,536
for the 5,000 one, the first set the first 1,536 of the second
([scale-synth.txt](scale-synth.txt)). So the 464 real haplotypes, the two
references included, are in both.

- **Names:** `SYN0001#1` on, one sample per haplotype, haplotype 1, contigs
  `c1`, `c2`..., each W line from 0 to its bp
- **Layout:** each copies the contigs of one real haplotype, its template,
  the real haplotypes taken in a shuffled order in turn, so synthetic
  contigs fall where real ones do
- **Recombination:** a synthetic contig starts as its template's contig and
  switches to another real haplotype's contig at an anchor, a node GRCh38
  steps once that both contigs step exactly once and in GRCh38's
  orientation. The switch keeps the first contig's step into the anchor
  and the second's step out of it, so both links it uses are real walks'
  links. A contig mostly against GRCh38 is turned around first (267 of
  1,127), the same path read the other way
- **Spacing:** a segment is the larger of 500 kb and an exponential draw
  with mean 6 Mb, so switches fall 500,000 to 35,476,833 bp apart, median
  3,486,514; 26,249 switches, a median of 6 per haplotype. 11 of 4,536
  synthetic haplotypes have none, because every contig of their template
  is short, so each is a renamed copy of a real haplotype
- **Coverage:** a synthetic haplotype covers 35.84 Mb at the median, a real
  one 35.86 Mb ([scale-coverage.tsv](scale-coverage.tsv),
  [scale-coverage.sh](scripts/scale-coverage.sh)); the switch points are in
  [scale-switches.tsv.gz](scale-switches.tsv.gz)

### Checks

- [scale-validate.py](scripts/scale-validate.py) reads each GFA's S and L
  lines, then checks every W line: its end less its start against its
  steps' bp, its name's bytes, its path and start against every other
  line's, and every link it walks against the L lines. All three graphs
  pass with no link missing; it walked 6,729,649,212 links of the
  5,000-haplotype graph ([scale-validate.tsv](scale-validate.tsv)). No L
  line was added. It fails on planted GFAs with a link no L line gives, a
  wrong end, a repeated path and start, and a name starting `#`, and
  passes the clean one ([scale-validate-planted.sh](scripts/scale-validate-planted.sh),
  [scale-validate-planted.txt](scale-validate-planted.txt))
- scale-synth.py also checks each switch's link against the L lines: 0 of
  26,249 missing
- gfa-to-tabix itself refuses a W line whose end disagrees with its steps;
  it accepted all three

### What the synthetic graphs leave out

- **New variation.** A synthetic haplotype is copies of real stretches, so
  it brings no route, node or link the real ones lack. Within a tile, 459
  of 463 real walk rows are distinct, against 1,153 of 1,868 at 5,000
  ([scale-distinct.tsv](scale-distinct.tsv), medians over 30 tiles). A real
  cohort of 5,000 would have more routes and fewer repeated rows, so larger
  tiles and a larger file; deflate still packs a synthetic tile only a
  little tighter than a real one (7.5x to 8.6x, against 8.1x to 8.3x at 464)
- **Other chromosomes and graphs:** chr22 only, MC only

## Builds

[scale-build.sh](scripts/scale-build.sh): three interleaved rounds, each
run pinned to 16 CPUs, so 16 threads, under a 64 GB cap
([scale-build.txt](scale-build.txt)). Medians, with the range:

| | 464 | 2,000 | 5,000 |
|---|---|---|---|
| GFA, gzipped | 1.07 GB | 6.28 GB | 15.63 GB |
| wall | 43.4 s (43.3-43.5) | 189.4 s (189.3-191.7) | 495.6 s (495.0-500.1) |
| peak memory | 1.12 GB (1.11-1.12) | 4.07 GB (4.05-4.12) | 9.15 GB (8.96-9.19) |

- All three rounds of each wrote the same walk file and `.idx`, and the
  464 one is byte for byte the file the 24-thread runs of
  [musl-alloc-mc22-walks.txt](musl-alloc-mc22-walks.txt) wrote
- Time grows a little slower than the input: reading the gzipped GFA twice
  is most of it, 344.9 s of the 495.0 s of round 1 at 5,000 passing before
  the first tile is written
- Peak memory follows the densest tiles, which the sort's merge encodes on
  all cores at once
- **Load:** the brief asked for a 1-minute load below 3 before each run.
  Two other sessions' long jobs held it between 4 and 7 the whole night,
  so the runs started below 6 instead; the load before each is in the
  file. The three rounds agree within 1.3%

## File size and the table

[scale-files.tsv](scale-files.tsv) and [scale-alt-files.tsv](scale-alt-files.tsv),
by [scale-bytes.mjs](scripts/scale-bytes.mjs):

| | 464 | 2,000 | 5,000 |
|---|---|---|---|
| walk file, default budgets | 59.12 MB | 463.90 MB | 1,885.27 MB |
| of it detail units | 39.34 MB (2,468) | 405.71 MB (220,055) | 1,749.56 MB (1,732,006) |
| of it tiles | 18.21 MB | 38.44 MB | 50.09 MB |
| of it blocks units | 0.63 MB | 15.50 MB | 66.73 MB |
| table, fetched before the first cut | 0.05 MB | 1.94 MB | 13.96 MB |
| walk file, abridging off | 31.75 MB | 72.13 MB | 142.16 MB |
| table, abridging off | 0.02 MB | 0.02 MB | 0.02 MB |

- The `.idx` stays about 200 bytes: it names the table, and the table grows
- The default builds moved 223,030 walk rows to detail units at 2,000 and
  1,740,726 at 5,000 ([scale-build.txt](scale-build.txt)), of 1,083,462
  and 2,702,989 walk rows in all
  ([scale-alt-builds.txt](scale-alt-builds.txt)): about a fifth and about
  two thirds
- A median tile with the default budgets is 0.03 MB, 0.07 MB and 0.09 MB
  compressed: abridging holds it near 1,000,000 steps whatever the
  haplotype count, and the blocks unit beside it grows instead (0.11 MB at
  the median at 5,000)

### The 20 GB claim

[comparison.md](../comparison.md) ("More haplotypes") and
[comparison-details.md](../comparison-details.md) ("Growth with N
haplotypes") say walk files grow to about 20 GB genome-wide at 10,000
haplotypes. This page does not edit them.

- With the default budgets, chr22's file grows as N^1.46 from 464 to 5,000
  haplotypes; the genome-wide 464 file grown at that rate is 138.3 GB at
  10,000
- With abridging off it grows as N^0.63, and 11.0 GB at 10,000
- So the sentence holds only for a writer whose abridging keeps to outlier
  tiles, and even then only as an order of magnitude: synthetic haplotypes
  understate growth, and 10,000 is twice past what was built

## Bytes per window

A window is centred in the tile at each of the 40 starts of
`mc22.windows.tsv` (one per 1.245 Mb of chr22), widened by the browser's
1 kb context; 30 of the 40 have tiles over 1 kB, the other 10 lie in the
short arm, where GRCh38 has no sequence. Medians over those
([scale-windows.tsv](scale-windows.tsv),
[scale-alt-windows.tsv](scale-alt-windows.tsv)), compressed:

| window | 464 | 2,000 | 5,000 | 5,000, abridging off |
|---|---|---|---|---|
| 10 kb: tiles | 0.03 MB | 0.07 MB | 0.09 MB | 0.19 MB |
| 10 kb: blocks units | 0 | 0.01 MB | 0.09 MB | 0 |
| 100 kb: tiles | 0.08 MB | 0.21 MB | 0.27 MB | 0.56 MB |
| 100 kb: blocks units | 0 | 0.04 MB | 0.30 MB | 0 |
| 100 kb: all, by `bytesFor` | 0.09 MB | 0.26 MB | 0.61 MB | 0.59 MB |
| 1 Mb: tiles | 0.46 MB | 1.15 MB | 1.52 MB | 3.24 MB |
| 1 Mb: blocks units | 0 | 0.24 MB | 1.70 MB | 0 |
| 1 Mb: all, by `bytesFor` | 0.49 MB | 1.51 MB | 3.34 MB | 3.42 MB |
| largest 100 kb, all | 0.43 MB | 0.89 MB | 1.64 MB | 6.79 MB |

- A cut keeping a few haplotypes reads the same tiles as one keeping all,
  since a tile holds every haplotype's rows, and the departure bins; it
  reads a tile's blocks unit only where a kept walk is abridged there and
  not expanded, and an expanded walk's detail units instead
- What graph-walks 9.0.0 actually read, per cut on a reader already open,
  at the three windows timed below (centred at 20,545,536, the median of
  the 40 by bytes at 464; 44,204,032; and 46,694,400, the largest)
  ([scale-query-untimed.tsv](scale-query-untimed.tsv),
  [scale-query-alt-untimed.tsv](scale-query-alt-untimed.tsv); abridging
  off reads what `scaled` does at 10 kb and 100 kb and 3.93-4.00 MB at 1 Mb):

  | 4 haplotypes, compressed bytes read | 464 | 2,000 | 5,000 | 5,000, s4m | 5,000, scaled |
  |---|---|---|---|---|---|
  | 10 kb | 0.03 MB | 0.07-0.12 MB | 0.08-0.25 MB | 0.17-0.21 MB | 0.17-0.23 MB |
  | 100 kb | 0.09-0.12 MB | 0.21-0.35 MB | 0.47-0.74 MB | 0.60-0.76 MB | 0.60-0.81 MB |
  | 100 kb, the 4 expanded | 0.09-0.12 MB | 0.21-0.22 MB | 0.26-0.31 MB | 0.60-0.66 MB | 0.60-0.81 MB |
  | 1 Mb | 0.56-0.63 MB | 1.58-1.72 MB | 3.57-3.95 MB | 3.73-3.93 MB | 3.80-3.98 MB |
  | 1 Mb, the 4 expanded | 0.56-0.63 MB | 1.17-1.40 MB | 1.67-1.98 MB | 3.34-3.89 MB | 3.80-3.97 MB |

  The 4 are HG00097#1, HG002#1, NA19240#1 and HG00733#1, real haplotypes
  in every file. Unexpanded, a kept walk abridged in a tile makes the cut
  read that tile's whole blocks unit, which at 5,000 is as large as the
  tile. Expanded, it reads the walk's own detail units instead, so the
  default budgets' abridging works as a split by haplotype: the tile keeps
  about two fifths of the walks and a few-haplotype view fetches only its
  own of the rest

## Query time

graph-walks 9.0.0 cut each window from local disk on a reader opened
once per file, so a cut reads its window's units and not the table, with
`CUT_PRESETS.figure` (the browser's 1 kb context, no budgets): three runs,
the files and the three sets in an order rotating from window to window
and run to run, after one untimed pass
([scale-query.mjs](scripts/scale-query.mjs),
[scale-query.tsv](scale-query.tsv)). Each cell is the lowest and highest
of the three windows' median cut, in ms; `graph.tables` adds a little for
4 haplotypes and up to a third for all:

| cut, ms | 464 | 2,000 | 5,000 |
|---|---|---|---|
| 10 kb, 4 haplotypes | 4-10 | 52-76 | 716-735 |
| 10 kb, the 4 expanded | 4-11 | 48-53 | 718-776 |
| 10 kb, all | 39-174 | 349-676 | 1,453-1,586 |
| 100 kb, 4 haplotypes | 10-136 | 61-67 | 746-807 |
| 100 kb, the 4 expanded | 9-12 | 59-66 | 737-741 |
| 100 kb, all | 228-394 | 1,047-1,593 | 4,094-5,739 |
| 1 Mb, 4 haplotypes | 76-119 | 177-225 | 1,127-1,161 |
| 1 Mb, the 4 expanded | 82-100 | 160-182 | 890-920 |
| 1 Mb, all | 2,240-4,122 | 20,836-42,015 | 123,465-266,144 |

- **Spread:** at 5,000 the three runs of a window agree within 17%; at 464
  a cut of a few ms can vary by more than its own length
- **4 haplotypes cost 0.7-1.2 s a cut at 5,000, whatever the window.**
  That floor is graph-walks', not the format's: every cut builds maps of
  the sequence's detail and blocks units by name, and at 5,000 there are
  1,732,556 of them. The maps alone take 0.9-1.2 s on ada's slower cores,
  against 6-10 ms for the 25,651 of `scaled`, where a 10 kb cut takes
  24-42 ms ([scale-floor.txt](scale-floor.txt),
  [scale-floor.mjs](scripts/scale-floor.mjs)). Building them once per
  sequence would remove most of it, a graph-walks change not made here. Opening the 5,000 file also costs 1.8 s to
  parse its table, after fetching 13.96 MB of it
- **All haplotypes:** at 5,000 a 10 kb cut takes about 1.5 s, a 100 kb
  one 4 to 6 s and `graph.tables` 2 to 4 s more, and a 1 Mb one 2 to 4.5
  minutes and 46 to 58 s more. The abridged pieces add much of it: a
  1 Mb cut at 5,000 holds 5.6 to 6.5 million placeholder nodes, and in the
  untimed pass `s4m`, which abridges far less, cut the same 100 kb
  windows in about 60% of the default's time
- **The browser preset** (`CUT_PRESETS.browser`) fits every 4-haplotype
  cut here. It refuses an all-haplotype cut of 100 kb from 2,000
  haplotypes on, and of 1 Mb even at 464, with a zoom-in notice
  (`NodeLimitError`, "Zoom in to about ... or choose fewer haplotypes");
  at 5,000 it asks for about 21-24 kb. So the slow all-haplotype cuts are
  ones a browser does not attempt
- **Load:** each cut started at a 1-minute load below 6, for the reason
  under [Builds](#builds); the load before each is in the file

## Abridging at scale

ADR 0004 and ADR 0012 made abridging for the few tiles a collapsed repeat
or a centromere makes huge. Of chr22's 776 tiles, it abridges 18 at 464
haplotypes, 422 at 2,000 and 550 at 5,000 (one blocks unit each), because
a tile's step count grows with the haplotypes while the budget stays at
1,000,000.

- The format leaves the budgets to the writer
  ([walks-format.md](../walks-format.md), "Abridged tiles" and "What a
  reader relies on"), so changing them is no format change
- Four builds bracket the choice at 5,000 haplotypes
  ([scale-alt.sh](scripts/scale-alt.sh)):

  | 5,000 haplotypes | budgets (steps, bytes) | walk file | table | detail units | largest tile | 100 kb, all: median, largest |
  |---|---|---|---|---|---|---|
  | default | 1,000,000, 3,000,000 | 1,885.27 MB | 13.96 MB | 1,732,006 | 0.17 MB | 0.61 MB, 1.64 MB |
  | s4m | 4,000,000, 12,000,000 | 777.51 MB | 1.28 MB | 149,615 | 0.38 MB | 0.59 MB, 1.70 MB |
  | scaled | 10,776,000, 32,328,000 | 539.22 MB | 0.24 MB | 25,633 | 1.34 MB | 0.59 MB, 1.72 MB |
  | off | 0, 0 | 142.16 MB | 0.02 MB | 0 | 8.22 MB | 0.59 MB, 6.79 MB |

- `scaled` is the default budgets times 5,000/464. It abridges 18 tiles,
  as the default does at 464, and keeps the worst 100 kb read near the
  default's with a file about 3.5 times smaller and a table about 58 times
- What is left of `scaled`'s file over `off`'s is those 18 tiles' moved
  walks: 414.11 MB of detail units for rows that, kept in their tiles,
  cost a small part of that. One W line's pieces in one tile per unit is
  fixed by the format; how many lines move is not
- A median window reads the same bytes under every budget: abridging pays
  only on outlier tiles, and on those it is what keeps an all-haplotype
  read to 1.7 MB instead of 6.8 MB

## A writer failure at 5,000 haplotypes

- The first build of the 5,000-haplotype graph with `--abridge-steps 0
  --abridge-bytes 0`, pinned to CPUs 0-7, stopped after 433 s with
  `GRCh38#0#chr22:39387136: SYN1288#1#c2: a step placed at 38417438 is not
  on the tile's reference path`. The same command on CPUs 8-15 finished
  ([scale-alt-builds.txt](scale-alt-builds.txt)). The error is
  `Piece::read` in `src/routes.rs`, which decodes a sorted piece's
  positions against its tile's reference path
- The input is not at fault as far as checks reach: the GFA passes
  scale-validate.py; the 2,000-haplotype graph, which holds SYN1288, builds
  with abridging off; so does the real GFA with SYN1288's two lines added;
  and the default budgets build the 5,000-haplotype graph to the same
  bytes in every round ([scale-build.txt](scale-build.txt))
- It did not recur. The regenerated graph (scale-synth.py, seed 1, the
  same switch table) was built 30 times with the same command, two or
  three builds at a time on disjoint CPU sets, by the 5.0.1 and 5.0.0
  musl releases, a 5.0.0 glibc build and 5.0.1 instrumented to checksum
  each of the external sort's runs at push, spill and read-back, check
  every piece's positions inside its tile and every row between merge and
  encoding: every build finished, every output has one sha256, the one
  the second build above wrote, and no check fired
  ([scale-writer-reruns.tsv](scale-writer-reruns.tsv),
  [scale-writer-reruns.sh](scripts/scale-writer-reruns.sh))
- The code gives it no deterministic path. One thread pushes the sorter's
  rows, so its runs split at the same rows every time; the builder is
  single-threaded; the encoding threads only read shared data and return
  results in order; `src/` has no `unsafe`
- What the error read is two faults at once. 38417438 is a real step of
  SYN1288#1#c2, in a piece of the tile at 38404096, not of the tile at
  39387136 the message names, and 412 steps of that piece decoded against
  the reference path before it failed, so the work labelled with one tile
  held another tile's reference row and piece; and no arrangement of
  whole rows fails first at that step, so a byte changed as well. That
  reads as memory corruption, from the allocator or the hardware (ada
  reports no ECC); one event cannot tell which, nor whether 5.0.0 could
  fail the same way

## Proposal for the owner: per-group units

Decided 2026-11-21: no per-group units. The writer's default abridge
budgets are to grow with the haplotype count instead, as the `scaled` case
does. The proposal follows as it was written.

It was a proposal for the owner, not a decision. The format is frozen and
nothing here changes it. Three Fable 5.2 reviews of a draft (is it needed,
the alternatives, what it touches) shaped it; they are in
[scale-reviews/](scale-reviews/), and read data that was partly gone
from under them or not yet written (the untimed query pass, the `scaled`
build).

### The idea

Split each tile's `walk` and `abridged` rows into units by haplotype group,
groups fixed file-wide (say runs of samples in header order), so that a
reader keeping k haplotypes fetches the tile's shared rows (`ref`, `nodes`,
`route`) and at most k group units, not every haplotype's rows.

### What motivates it

- At 5,000 haplotypes a 4-haplotype view of a median 100 kb window reads
  0.47-0.74 MB at the three windows measured, or 0.26-0.31 MB with the 4
  expanded, and a 1 Mb window 3.57-3.95 MB, or 1.67-1.98 MB expanded.
  With the budgets scaled or abridging off it reads 0.60-0.81 MB and
  3.80-4.00 MB, nearly all of it other haplotypes' rows
- Nearly all of a median tile is other haplotypes' rows: with abridging
  off at 5,000, its shared rows deflate to 3.9 kB of 170.6 kB
  ([scale-rowsplit.tsv](scale-rowsplit.tsv),
  [scale-rowsplit.py](scripts/scale-rowsplit.py))
- Split into 50 groups, the shared rows and four groups' rows are 21.5 kB,
  so a 4-haplotype view would read about an eighth of the tile bytes it
  does now (an estimate: zlib on one tile's text, not BGZF units)

### What it costs

- **Bytes for everyone else:** the 50 groups' rows deflate to 214.7 kB
  against 165.0 kB together, so an all-haplotype read grows by about 30%
  (122.1 kB against 81.9 kB, about 50%, with the default budgets)
- **Table:** 776 tiles times 50 groups is 38,800 more entries on chr22, a
  few hundred kB more table at the 8 to 16 bytes an entry takes today,
  all of it fetched before the first cut, against 0.02 MB with abridging
  off
- **Reads:** up to k+1 ranges a tile where today one range covers a
  window's tiles: a 1 Mb window is 17 tiles
- **The format:** a format 9. A format 8 reader skips unknown unit kinds,
  so it would draw the reference alone. The spec's rows-per-unit rules,
  "the tiles a window reads hold a row of every line", unit names and
  order, empty units, blocks units, both abridge budgets and attach
  fetches all need rewriting
- **Readers and files:** graph-walks' format check, row kinds per unit and
  every place it takes `kind === 'tile'`, `bytesFor`'s promise that a cut
  keeping fewer walks reads no more; the writer's checks and tests; the
  hosted HPRC files rebuilt under new names; a release of every consumer
- **The rule for a new format** (ADR 0011, upheld by ADR 0016) asks for a
  real problem on a hosted file. This is synthetic data
- **What it does not touch:** the file's size and the table's growth,
  which come from abridging

### Alternatives

- **No change:** chr22 at 5,000 haplotypes is 1,885.27 MB with a 13.96 MB
  table read at open; median windows read under 1 MB below 1 Mb
- **Writer policy, no format change (first to try):** budgets that scale
  with the haplotypes, or that move only outlier walks. Measured above as
  `scaled`: 539.22 MB, a 0.24 MB table, the same median reads, the worst
  100 kb read 1.72 MB. It costs a few-haplotype view what the default's
  abridging saves it: 0.60-0.81 MB per 100 kb against 0.26-0.31 MB with
  the 4 expanded (0.47-0.74 MB not expanded), and 3.80-3.98 MB per 1 Mb
  against 1.67-1.98 MB
- **Detail units per tile and group instead of per W line:** a format
  change, aimed at the 414.11 MB of detail units `scaled` still has. ADR
  0012 set aside spatially indexed detail units as unmeasured
- **A paged table,** so a reader fetches the part over its window: a format
  change that fixes the open cost and nothing else
- **A smaller `--tile`:** writer-only and unmeasured; each tile would still
  hold every haplotype's rows

So per-group units are worth building only if a consumer on a hosted file
finds half a megabyte per 100 kb, or a few megabytes per 1 Mb, too slow
for a few-haplotype view after the writer's budgets are fixed.

## Reproduce

On ada, from `~/work/handoff-1121/runs/scale`, with numpy in a venv,
pigz, node 24, the 5.0.1 release binary in `bin/` and, in `qt/`, an npm
project with `@jbrowse/graph-walks@9.0.0` and `@gmod/bgzf-filehandle`
(copy the `.mjs` scripts there, since node resolves packages from the
script's folder). `windows.tsv` is the `start` column of
`~/work/gfaidx-compare/results/mc22.windows.tsv`.

```bash
S=~/work/handoff-1121/gfa-to-tabix-scale/docs/placement/scripts
G=~/work/perf-1119/out/mc22.gfa.gz
venv/bin/python $S/scale-synth.py $G GRCh38 synth/mc22 1 1536 4536
venv/bin/python $S/scale-validate.py $G synth/mc22.2000.gfa.gz synth/mc22.5000.gfa.gz
bash $S/scale-coverage.sh synth/mc22.5000.gfa.gz
LOAD_MAX=6 bash $S/scale-build.sh
bash $S/scale-alt.sh
W="464=walks/mc22.464.r1.GRCh38.walks.gz 2000=walks/mc22.2000.r1.GRCh38.walks.gz 5000=walks/mc22.5000.r1.GRCh38.walks.gz"
(cd qt && node scale-bytes.mjs 'GRCh38#0#chr22' ../windows.tsv 10000,100000,1000000 \
  ../scale-windows.tsv ../scale-files.tsv ${W//=/=../})
(cd qt && LOAD_MAX=6 node --max-old-space-size=32000 scale-query.mjs 'GRCh38#0#chr22' \
  20545536,44204032,46694400 10000,100000,1000000 HG00097#1,HG002#1,NA19240#1,HG00733#1 3 \
  ../scale-query.tsv ${W//=/=../})
python3 $S/scale-distinct.py 'GRCh38#0#chr22' windows.tsv 7 $W
python3 $S/scale-rowsplit.py 'GRCh38#0#chr22' windows.tsv 50 HG00097#1,HG002#1,NA19240#1,HG00733#1 $W
python3 $S/scale-summary.py ~/work/handoff-1121/gfa-to-tabix-scale/docs/placement 1580961534
```

- The alt files' bytes and the untimed pass come from the same two node
  scripts on the files `scale-alt.sh` writes (`5000-off` is its second
  abridging-off build), the untimed pass with `0` runs
- 1,580,961,534 is the byte length of the hosted
  `hprc-v2.1-mc-grch38-f8.GRCh38.walks.gz`
- [scale-walk-files.tsv](scale-walk-files.tsv) gives the sha256 and
  length of every walk file measured
