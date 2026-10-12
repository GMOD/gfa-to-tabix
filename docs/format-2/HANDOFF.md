# Handoff: a smaller walk format

Status on 2026-10-12: measured and reviewed, nothing implemented.

- **Problem:** a walk set's bytes per window grow linearly with the cohort,
  because Tabix indexes the reference axis and every haplotype's rows sit under
  each chunk. The plugin downloads every haplotype and drops the unselected ones
  after the fetch. Genome-wide, the two references' sets total 18 GB, against
  10 GB for HPRC's `gbz.db` with sequences
- **Format 2, the routes layout:** store each distinct off-reference traversal
  once per chunk (routes) and each haplotype's sequence of route ids (choices),
  and drop the links file. A chr22 window drops to about 0.16 of today's bytes,
  and walks rebuild exactly
- **One break:** the cheap fix (no links file, slim nodes, 0.49 of today) is a
  subset of format 2, so its changes become format 2's first commits and no
  release ships the cheap fix as a format
- **Why now:** at 464 haplotypes drawing takes longer than the download (the
  plugin's `GRAPH_TRACK.md` has the timings). The case for format 2 is hosting,
  cohorts past a few thousand haplotypes, and changing the format before others
  build walk sets
- **Not worth building yet:** an index on the haplotype axis, in Tabix or a
  custom container, and a binary encoding. Revisit past about 2,000 haplotypes

## How the numbers were made

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

## Results

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
- The routes rows leave out the reference's own path, which the decoder needs.
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

## Decisions so far

- Keep BGZF text with Tabix or CSI indexes; build no custom container and no
  binary encoding yet. After format 2 a median two-chunk read is about 0.1 MB
- Store every haplotype's choices for a chunk together. Splitting them into
  64-haplotype groups returns 84% of the choices for 8 selected haplotypes,
  and at 10,000 haplotypes the group index reaches 238 MB genome-wide, which
  `@gmod/tabix` loads whole
- Keep one choice row per haplotype per chunk, as
  [Sharing across haplotypes](#sharing-across-haplotypes) measures
- Ship the routes layout as format 2 in one break. A separate cheap-fix format
  would give the plugin a third format to read and need another genome-wide
  rebuild, 44 minutes for 18 GB, for a saving format 2 includes

## Next steps, in order

### 1. Links from steps, in the plugin

- Build links in `WalkGraph` (`src/RgfaTabixAdapter/walkRows.ts:422`) from
  consecutive decoded steps and stop reading the links file. The change works
  on today's files and cuts about a third of each window's bytes, and format 2
  needs it. `WalkTabixSyntenyAdapter` already reads with `links: false`, and
  every chunk checked held no link its walks don't imply. The links file's
  extras are the link from the previous piece, filed under both chunks; the
  `pv` tag locates that piece
- `WalkGraph.tables` keeps every link from the file whose two nodes the kept
  walks visit, including links that only unselected haplotypes take. Links from
  the kept walks' steps leave those out, so compare the drawn graph for 8
  haplotypes before and after

### 2. Format 2: the routes layout

Files and versioning:

- Open every output file with a header such as
  `#gfa-to-tabix format:i:2 kind:Z:routes chunk:i:65536`, and have `--walks`
  write a manifest. A reader tells old sets from new by this header
- Write CSI instead of TBI, which lifts the 512 Mb limit. The plugin's adapter
  reads CSI with `csi: true`
- Decide between one file per reference and two. Route and reference rows can
  list their nodes' lengths, which leaves a node file nothing to hold, and a
  window then reads one index and one range. Node rows need no placement
  columns, because a reader can compute a node's position from any decoded walk
  that visits it and that walk's hapOffset, and `launchFromGraph/contributors.ts`
  reads the result from `node.stable`. That walk can differ from the
  first-named path the converter picks today

Rows:

- **Routes** row: chunk, route id, entry and exit reference handle, carrier
  count, optional per-group counts, delta-encoded steps. A route's row number
  is its id, and a reader can count a route's uses in the choices, so write
  either column only if a reader needs it before decoding the choices
- **Choices** row: chunk, path id, hapOffset, piece, first and last reference
  handle, then per choice: route id delta and flip, and the implied reference
  step count only where the reference visits a node twice; `pv` and `nx` as
  today. Implied counts written everywhere were 28% of the choices measured
  above
- **Path table:** each path id with its `sample#haplotype#contig` and
  fragStart, filed under each reference sequence so a reader fetches it once
  per sequence. chr22's graph has 1,131 paths
- **Decoder rules**, checked on every chr22 walk row:
  - the current reference handle's orientation gives the direction of travel
  - a route lands on the occurrence of its exit node nearest the current
    position
  - each row stores its first and last reference handle
  - steps before the first or after the last reference step are open routes,
    and an open route at a row's end still records its exit, which the builder
    knows
- **Untested rule:** chr22 never runs the nearest-occurrence rule, since
  GRCh38's path visits no node twice within a chunk there. Check the rules on a
  graph whose reference does, such as a pggb build, before fixing them
- **Builder:** deduplicate routes per chunk through the existing external
  `Sorter` (`src/sorter.rs`) and assign ids in the merge. A table per chunk kept
  in memory while paths stream would hold every chunk until the end
- **Parity test:** every window's rebuilt walks equal the walk file's, step for
  step, on chr22 and on a graph whose reference revisits nodes
- Write the format up in `docs/format.md`

### 3. Correctness in the other subcommands

Format 2 needs none of these, so they can land at any time.

- Give the index and `build` the name-ordered placement that `--walks` got in
  463c392; `src/place.rs:139-170` still places by file order
- Share one path-name parser: `split_range_suffix` in `src/gfa.rs:76` reads
  `:start-end` only, while `src/walks.rs` also reads `[start]` and `#start`
- Decide rGFA or plain once, from the full parse: `build` samples the first
  100,000 S lines, while placement checks every one
- Write CSI for the segs, links and other outputs too
- Add tests that query an index larger than one BGZF block

### 4. Tiers and repeat regions

Format 2 leaves these out; its format header leaves room for them.

- A tier made by dropping routes under N bp removes 70-80% of routes and uses
  at 100 bp in typical chunks, but misses the heavy bytes: at 11.80, 18.22,
  18.68 and 38.08 Mb, 90-100% of route bytes sit in long routes at sites with
  10 or more routes. Their nested variation stays at every tier
- Prototype routes as edits against a site consensus, or as nested sites, and
  measure at 18.22 and 38.08 Mb before promising tiers. Edits against a
  consensus cut tokens to 23-26% at 18.15 and 18.68 Mb but only to 58-69% at
  38.08 and 18.22 Mb
- Routes shrink the 11.8-12.0 Mb satellite by 2.4×, so some windows there stay
  over the plugin's 8 MB byte budget. The plugin can draw those windows from
  the per-bin summary below
- A per-bin summary file (sites, non-reference haplotype fraction, largest
  allele delta, inversions) gives the plugin its planned chromosome overview,
  drawn as a wiggle

### 5. Revisit the container

Past about 2,000 haplotypes, reconsider a bigBed-style single file whose
directory a reader fetches by range, so k haplotypes cost routes plus k small
choice blocks. A binary encoding and GBWT-style choices belong to the same
decision.

## Stop rules for step 2

- Window bytes (routes + choices + nodes) at most 25% of today at the median
  chunk and at most 60% at p99
- Exact rebuild on every window of the parity test
- Otherwise ship the cheap fix as format 2 and keep the walk rows

## Against GBZ

- `chr22.gbz.db` is 196 MB, with sequences and both references. Today's walk set
  is 407 MB without sequences; the routes layout would be about 90 MB
- gbz-base takes 18-43 round trips per window; a walk set takes 3 plus its
  indexes
- Choices still grow almost linearly, about 20 GB genome-wide at 10,000
  haplotypes, so the routes layout wins on requests and static hosting, not on
  growth. The plugin's `agent-docs/reference/GBZ.md` argues the same about any
  per-haplotype store

## Other findings from the same review

- Anchored segs/links rows can span megabases (chr9:43.4-61.7 Mb on the HPRC SV
  graph), and such wide rows push Tabix's bins back: a 10 kb query on chr1 reads
  about 130 KB for 10 link rows. Filing under one base, as walks do, fixes it
- For a plain GFA the converter writes every carrier into the `SM:Z` column of
  every node row and twice into every link row, and `src/place.rs:172` checks membership with a linear `contains`
  per path step
- `build` writes one coarse tier and walk sets get none
- Docs across this README, the plugin and the jbrowse.org tutorials disagree on
  minimum versions, describe the fold tier as "one node per bubble" in six
  tutorials, and offer no guide to choosing between the tabix, walk and GBZ
  routes
