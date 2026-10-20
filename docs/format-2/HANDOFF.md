# Handoff: walk format 2

Status on 2026-10-12: gfa-to-tabix 1.0.0 writes format 2, which
[docs/walks-format.md](../walks-format.md) describes, and graph genome viewer
6.27.0 reads it. HPRC v2.1's format-2 sets are hosted on jbrowse.org, and the
demo config and tutorials read them.

- **Problem:** a format-1 walk set's bytes per window grow linearly with the
  cohort, because Tabix indexes the reference axis and every haplotype's rows
  sit under each chunk. The plugin downloads every haplotype and drops the
  unselected ones after the fetch. Genome-wide, the two references' sets total
  18 GB, against 10 GB for HPRC's `gbz.db` with sequences
- **Format 2:** one file per reference. A chunk holds the reference's path
  through it once, each distinct route a haplotype takes off that path once,
  the lengths of the nodes those routes visit, and each path piece as the list
  of routes it takes
- **Measured genome-wide:** the two files total 2.85 GB against format 1's
  18.4 GB, and a two-chunk read fetches 0.14 of format 1's at the median on both
  references. Every piece checked rebuilds step for step
- **Next:** walk rows at Mb scale need the plugin's walk-row pipeline reworked;
  see step 2
- **Not worth building yet:** an index on the haplotype axis, a custom
  container and a binary encoding. Revisit when the choices in a two-chunk read
  pass about 2 MB

## Format 2 genome-wide

HPRC v2.1, `hprc-v2.1-mc-grch38.W.gfa.gz` (53,150 paths, 38.4 G steps), built
on ada with `--walks --refs GRCh38,CHM13` into `~/hprc-gbz/walks-f2/` and
hosted then as `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38-f2.{GRCh38,CHM13}`,
since removed; jbrowse.org hosts only the format 4 set, `-f4`.
The format-1 set compared is `hprc-v2.1-mc-grch38-w6` from gfa-to-tabix 0.6.0.

| measure                                   | GRCh38            | CHM13             |
| ----------------------------------------- | ----------------- | ----------------- |
| file, format 1's three → format 2's one   | 9.03 → 1.22 GB    | 9.34 → 1.63 GB    |
| index, format 1's three → format 2's one  | 2.08 → 0.67 MB    | 1.95 → 0.63 MB    |
| two-chunk read over format 1: median, p99 | 0.136, 0.190      | 0.135, 0.183      |
| two-chunk read: median, max               | 0.046, 0.31 MB    | 0.047, 4.5 MB     |

- The build takes 28.6 minutes and peaks at 12.9 GB on ada's 24 cores, where
  format 1 took 44 minutes and 16.1 GB. No walk row needs step counts
- `check_format2.py` decoded 6 chunks of every chromosome of both references,
  282 chunks with 176 M steps, and matched format 1 in all of them. The read
  sizes come from 439 and 429 two-chunk reads sampled across the chromosomes
- Read over HTTP from jbrowse.org, eight windows on both references cut the
  same GFA from both formats, format 2 in 0.08-0.85 s against format 1's
  0.13-1.48 s from a cold start

## Format 2 on chr22

HPRC v2.1 chr22, `--walks --refs GRCh38,CHM13`, written to
`~/work/scratch/walks-20261008/f2/` and compared with the Oct 8 format-1 build.
`scripts/window_sizes.py` gzips each chunk's rows on their own and sums a chunk
and the one before it; `scripts/check_format2.py` decodes format-2 rows without
the encoder and compares every piece with format 1.

| measure                                     | GRCh38                | CHM13                  |
| ------------------------------------------- | --------------------- | ---------------------- |
| file                                        | 32.1 MB               | 39.0 MB                |
| per-chunk gzip total, format 1 → 2          | 201.3 → 30.8 MB       | 194.3 → 37.4 MB        |
| two-chunk read over format 1: median, p99   | 0.136, 0.237          | 0.137, 0.168           |
| two-chunk read over format 1: max           | 0.41                  | 0.53                   |
| two-chunk read: median, p99, max            | 0.05, 0.53, 6.79 MB   | 0.06, 0.58, 10.19 MB   |
| reads over the 8 MB budget, format 1 → 2    | 5 → 0                 | 3 → 2                  |
| parity, every 7th chunk                     | 112 chunks, 99 M steps | 114 chunks, 82 M steps |

- The build takes 2 min 22 s and peaks at 1.8 GB on 16 cores, where format 1
  took 2 min 20 s and 1.4 GB. Encoding chunks in parallel raised the peak from
  0.8 GB, since satellite chunks decode side by side
- No chr22 walk row needs step counts. `tests/data/walks-loop.gfa`, whose
  reference passes two nodes twice, has two that do, and
  `tests/walks.rs` rebuilds every fixture path from its rows
- Route rows are the largest part. Writing each route's node lengths on its
  row cost 9 MB of GRCh38's 43, because nested variation repeats nodes across
  routes; one `nodes` row per chunk replaced them
- The two CHM13 reads over the budget sit in the satellite at 0.26 and
  0.39 Mb, where routes are 61-82% singletons

## How the investigation's numbers were made

- Data: the Oct 8 chr22 walk build, HPRC v2.1 Minigraph-Cactus, 463 haplotypes,
  at `~/work/scratch/walks-20261008/settle/s0/chr22.{walks,nodes,links}.bed.gz`.
  It predates 0.5.0, so one set holds both references; every figure below counts
  GRCh38 chunks only, recompressed with gzip -6
- `scripts/eval_routes.py DIR mb [mb ...] [--sub 50,100,200] [--json out]`
  encodes routes and choices for the 64 kb chunks at the given positions,
  rebuilds every walk row from them and reports sizes, rebuild failures and
  subsampled sizes
- `chr22-chunks.jsonl.gz` holds its output for all 768 GRCh38 chunks;
  `scripts/summarize_all.py chr22-chunks.jsonl.gz` prints the totals below
- `scripts/share.py`, with the same arguments, measures how much a chunk's
  choices share across haplotypes in several layouts, and what each column of a
  choice row costs. `share-chunks.jsonl.gz` holds its output for 56 chunks
  spaced evenly over 16-50 Mb and the chunks at 11.80, 18.22, 18.68 and
  38.08 Mb; `scripts/summarize_share.py share-chunks.jsonl.gz` prints the
  figures under [Sharing across haplotypes](#sharing-across-haplotypes)
- `scripts/sites.py` measures how alike the routes at one site are;
  `scripts/tbi_survey.py` sizes indexes for the haplotype-group layout;
  `scripts/linkcheck.py DIR mb` compares a chunk's links file against the links
  its walk steps imply
- Run each with `python3 -I`; each needs `tabix` on PATH

## Investigation results

Whole of chr22, GRCh38 chunks, gzip -6:

| layout                                       | walks       | nodes   | links   | total       | of today   |
| -------------------------------------------- | ----------- | ------- | ------- | ----------- | ---------- |
| today                                        | 94.9 MB     | 36.5 MB | 67.5 MB | 198.8 MB    | 1.00       |
| walks, slim nodes, no links                  | 94.9 MB     | 2.9 MB  | none    | 97.7 MB     | 0.49       |
| routes 18.0 + choices 17.5, slim nodes       | 35.5 MB     | 2.9 MB  | none    | 38.4 MB     | 0.19       |
| the same, implied counts left out            | 30.6 MB     | 2.9 MB  | none    | 33.5 MB     | 0.17       |
| the same, contig and fragStart in path table | about 28 MB | 2.9 MB  | none    | about 31 MB | about 0.16 |

- The last row applies the saving measured under
  [Sharing across haplotypes](#sharing-across-haplotypes) to the whole
  chromosome
- The routes rows leave out the reference path, which the decoder needs.
  It adds 0.3 MB
- Per chunk, routes + choices over walks: median 0.36, p90 0.40, max 2.48;
  15 chunks exceed 0.5
- Per window, the routes layout over today: median 0.19, p90 0.21, max 0.45
- Choices cost 64 B per haplotype per chunk at the median, 90 at p90, 196 at
  most. Walk rows cost about 200
- The heaviest chunks sit in the 11.8-12.0 Mb satellite: 29.7 MB of walks
  becomes 12.3 MB of routes + choices
- Exact rebuild: 0 failures over 249,146 walk rows, with or without implied
  counts. GRCh38's path visits no node twice within any chunk, so no walk
  starts or lands on a repeated reference node

Growth with haplotype count, fitted on subsamples of 50, 100, 200 and 463 in 20
chunks (median exponent):

| quantity        | grows as  |
| --------------- | --------- |
| distinct routes | N^0.38    |
| routes, gzipped | N^0.36    |
| choices         | N^0.86    |
| walks           | N^0.98    |

- At 10,000 haplotypes a typical 100 kb window would hold about 1.5 MB of
  choices against about 6 MB of walks
- LCR chunks break that: at 18.22 Mb the routes grow as N^0.94, because 356
  haplotypes each take a private excursion of about 6,000 steps. The
  extrapolation gives 14.7 MB of routes there at 10,000
- Singleton routes are 30-50% of routes in typical chunks, 70-76% at 11.80 and
  38.08 Mb, so deduplication weakens as the cohort grows

## Sharing across haplotypes

Choices are the one term that still grows almost linearly. Over the 55 chunks
at 16-50 Mb, with implied counts left out, reordering or transposing them
changes their size and growth little:

| layout of the route ids                   | bytes | grows as, 200 to 463 |
| ----------------------------------------- | ----- | -------------------- |
| one row per haplotype, in file order      | 1.00  | N^0.88               |
| the same rows sorted by their route ids   | 0.90  | N^0.81               |
| each route lists the haplotypes taking it | 0.86  | N^0.75               |
| xz over the chunk, a bound for LZ         | 0.75  | N^0.75               |

- A chunk's 463 haplotypes hold about 440 distinct sequences of route ids, so
  storing each distinct sequence once saves nothing
- A route's list of haplotypes has no order, so a haplotype that revisits a
  site or turns at an inversion would need a second channel. Choices stay one
  row per haplotype
- Choices that grow sublinearly need GBWT-style positional structure, which
  belongs to the container question in step 5
- The columns before the route ids are 39% of choices and grow as N^0.96.
  Dropping one column saves this share of them: contig name 30%, fragStart
  26%, hapOffset 26%, haplotype id 12%, piece 6%, the rest 2%
- The contig name and fragStart are the same in every chunk a path crosses.
  Moving both to a path table saves 54% of those columns, 21% of choices

## Decisions

- Format 2 replaces format 1 in one break, with no intermediate format. A
  reader tells them apart by `format:i:2` on the walk file's first header line
- One file per reference, `<prefix>.<sample>.walks.bed.gz`, so `walksUri`
  configs keep their names. A window reads one index and one range, and the
  index is the larger part of a cold load: the hosted GRCh38 format-1 set's
  three indexes are 2.1 MB
- Keep one choice row per haplotype per chunk, as
  [Sharing across haplotypes](#sharing-across-haplotypes) measures, and store
  every haplotype's choices for a chunk together. Splitting them into
  64-haplotype groups returns 84% of the choices for 8 selected haplotypes,
  and at 10,000 haplotypes the group index reaches 238 MB genome-wide, which
  `@gmod/tabix` loads whole
- The encoder decodes every walk row it writes and writes step counts where the
  default rule would misread one, so an exact rebuild does not depend on the
  graph
- Node lengths appear once per chunk. Positions of nodes off the reference are
  not stored: a reader takes them from the walks it decodes
- No path table: it would take a window from about 0.17 to 0.16 of format 1
  for an extra read per sequence. `--settle` and `--cap` are gone; with
  `--settle 0` no path was left out and 41 windows matched gbz-base against 39
- Keep BGZF text and TBI. Write CSI only once a reference sequence passes
  512 Mb, because the plugin takes the index type from its config

## Next steps, in order

### 1. The plugin's format-2 reader (done)

Landed in jbrowse-plugin-graphgenomeviewer as c5f28fe and released in 6.27.0.
`agent-docs/reference/GRAPH_TRACK.md` ("Format 2") describes it.

- `WalkReader` reads the walk file's header, and on format 2 reads and sizes
  that file alone; `getFeatures` reads the `ref` rows, and both adapters take
  reference names from the walk file's index
- Each chunk decodes once into the step arrays `joinPieces` takes. Positions of
  nodes off R and the links wait for `WalkGraph.tables(kept)`, which handles
  only the nodes a cut keeps: deciding per chunk lost links in the 22q11
  repeats, where one node sits in routes of several chunks
- Parity, `walkFormat2.test.ts`: 50 chr22 windows on GRCh38 and CHM13 against
  0.11.0's format-1 files give the same GFA, apart from 3,111 nodes off R in
  one 22q11 window whose first-named path is filed under an unread chunk. The
  four `walks_*` fixtures, rebuilt in both formats, match too
- Speed: the 50 windows take 2.66 s against format 1's 2.74 s. The slowest
  window relative to format 1 sits in the 16.3 Mb repeats, 0.24 s against
  0.12 s, where long nested routes repeat nodes that format 1 listed once

### 2. Walk rows at Mb scale

Format 2 lets a window of every haplotype's walk rows reach Mb scale, which
format 1's 8 MB byte budget refused at chr22:20-23 Mb. The plugin's walk-row
pipeline is now the limit:

| every haplotype from 20 Mb | time   | heap     |
| -------------------------- | ------ | -------- |
| 0.1 Mb                     | 0.39 s | +57 MB   |
| 1 Mb                       | 3.7 s  | +90 MB   |
| 3 Mb                       | 13.3 s | +1.0 GB  |

- At 1 Mb format 2's decoding is 10% of the time. `walkCut` (35%) and
  `tables()` (31%) take most of the rest, with a Map or Set lookup per step
  over about 14 M steps, and format 1 pays the same
- Rows from the choices skip both: a stretch along R is a run on the reference
  spanning R's positions, and a route is a run off it spanning its nodes'
  lengths. The cut would hand the pane runs and the reference walk alone, so
  this changes ADR-043, whose repeat pick re-slices the walks' steps on the main
  thread
- Merge identical local haplotypes before drawing, as GBZ-base does
- Stop rule: every haplotype over 3 Mb at chr22:20 Mb drawn in under 3 s warm

### 3. Release and rehost (done)

- Graph genome viewer 6.27.0 reads both formats, and gfa-to-tabix 1.0.0 writes
  format 2
- `demos/hprc/config.json` and jbrowse-components'
  `test_data/graphgenomeview/hprc.json` read the `-f2` sets, and the
  pangenome tutorials describe the one-file set. The format-1 sets stay hosted
  for configs that name them
- @jbrowse/graph-walks 1.0.0 reads format 2 only, and the plugin (unreleased
  after 6.27.0), BandageJS and the tube map read through it. Their hosted HPRC
  examples, jb2hubs' `hprc-grch38.json` and jbrowse-components'
  `demos/hprc/README.txt` name the `-f2` files

### 4. Benchmarks against GBZ-base

- Query 1,000 random intervals at each length from 100 bp to 1 Mbp on both
  references with a cold cache, locally and over HTTP, and record wall time
  and peak memory against `chr22.gbz.db`, as the GBZ-base paper does (Fig. 3,
  Supp. 7). Format 2 reads a whole chunk even for 100 bp

### 5. Later, on evidence

- A per-bin summary file (sites, non-reference haplotype fraction, largest
  allele delta, inversions) for the planned chromosome overview, drawn as a
  wiggle; a chromosome's routes are too much to read whole
- The container question when choices in a two-chunk read pass about 2 MB: a
  bigBed-style single file whose directory a reader fetches by range, so k
  haplotypes cost routes plus k small choice blocks. A binary encoding,
  column-wise compression (16-30% in GAF-base) and GBWT-style choices belong to
  the same decision
- The graph's identity in the header, `NM:Z:` with its pggname, as GBZ-base
  records it
- HPRC release 2's whole-genome pggb graph, whose references revisit nodes, for
  parity and route bytes
- Tiers and nested routes:
  - A tier made by dropping routes under N bp removes 70-80% of routes and uses
    at 100 bp in typical chunks, but misses the heavy bytes: at 11.80, 18.22,
    18.68 and 38.08 Mb, 90-100% of route bytes sit in long routes at sites with
    10 or more routes
  - Edits against a site consensus cut tokens to 23-26% at 18.15 and 18.68 Mb
    but only to 58-69% at 38.08 and 18.22 Mb

### Correctness in the other subcommands

Format 2 needs none of these, so they can land at any time.

- Give the index and `build` the name-ordered placement that `--walks` got in
  463c392; `src/place.rs:139-170` still places by file order
- Share one path-name parser: `split_range_suffix` in `src/gfa.rs:76` reads
  `:start-end` only, while `src/walks.rs` also reads `[start]` and `#start`
- Decide rGFA or plain once, from the full parse: `build` samples the first
  100,000 S lines, while placement checks every one
- Add tests that query an index larger than one BGZF block

## Against GBZ

[gbz-comparison.md](../gbz-comparison.md) compares format 2 with gbz-base and
gbz-haplotype-index.

## Other findings from the same review

- Anchored segs/links rows can span megabases (chr9:43.4-61.7 Mb on the HPRC SV
  graph), and such wide rows push Tabix's bins back: a 10 kb query on chr1 reads
  about 130 KB for 10 link rows. Filing under one base, as walks do, fixes it
- For a plain GFA the converter writes every haplotype with the allele into the
  `SM:Z` column of every node row and twice into every link row, and
  `src/place.rs:172` checks membership with a linear `contains` per path step
- `build` writes one coarse tier and walk sets get none
- Docs across this README, the plugin and the jbrowse.org tutorials disagree on
  minimum versions, describe the fold tier as "one node per bubble" in six
  tutorials, and offer no guide to choosing between the tabix, walk and GBZ
  routes
