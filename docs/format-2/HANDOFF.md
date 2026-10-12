# Handoff: a smaller walk format

Status on 2026-10-11: investigated and measured, nothing implemented.

- **Problem:** a walk set's bytes per window grow linearly with the cohort,
  because Tabix indexes the reference axis and every haplotype's rows sit under
  each chunk. The plugin downloads every haplotype and drops the unselected ones
  after the fetch
- **Cheap fix, no new encoding:** delete the links file and slim the nodes file.
  A chr22 window drops to 0.49 of today's bytes
- **Bigger fix, new encoding:** store each distinct off-reference traversal once
  per chunk (routes) and each haplotype's sequence of route ids (choices). A
  window drops to 0.19 of today, and walks rebuild exactly
- **Not worth building yet:** an index on the haplotype axis, in Tabix or a
  custom container. Revisit past about 2,000 haplotypes

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
- `scripts/sites.py` measures how alike the routes at one site are;
  `scripts/tbi_survey.py` sizes indexes for the haplotype-group layout;
  `scripts/linkcheck.py DIR mb` compares a chunk's links file against the links
  its walk steps imply
- Run each with `python3 -I`; each needs `tabix` on PATH

## Results

Whole of chr22, GRCh38 chunks, gzip -6:

| layout                                  | walks   | nodes   | links   | total    | of today |
| --------------------------------------- | ------- | ------- | ------- | -------- | -------- |
| today                                   | 94.9 MB | 36.5 MB | 67.5 MB | 198.8 MB | 1.00     |
| walks, slim nodes, no links             | 94.9 MB | 2.9 MB  | none    | 97.7 MB  | 0.49     |
| routes 18.0 + choices 17.5, slim nodes  | 35.5 MB | 2.9 MB  | none    | 38.4 MB  | 0.19     |

- Per chunk, routes + choices over walks: median 0.36, p90 0.40, max 2.48;
  15 chunks exceed 0.5
- Per window, the routes layout over today: median 0.19, p90 0.21, max 0.45
- Choices cost 64 B per haplotype per chunk at the median, 90 at p90, 196 at
  most. Walk rows cost about 200
- The heaviest chunks sit in the 11.8-12.0 Mb satellite: 29.7 MB of walks
  becomes 12.3 MB of routes + choices
- Exact rebuild: 0 failures over 249,146 walk rows

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

## Decisions so far

- Keep BGZF text with Tabix or CSI indexes; build no custom container yet
- Store every haplotype's choices for a chunk together. Splitting them into
  64-haplotype groups returns 84% of the choices for 8 selected haplotypes,
  and at 10,000 haplotypes the group index reaches 238 MB genome-wide, which
  `@gmod/tabix` loads whole
- Ship the cheap fix before the routes encoding: it captures most of the gain
  at today's cohort sizes

## Next steps, in order

### 1. Correctness and versioning

Step 1 depends on nothing else, so it can go first.

- Open every output file with a header such as
  `#gfa-to-tabix format:i:2 kind:Z:walks chunk:i:65536`, and have `--walks`
  write a manifest
- Give the index and `build` the name-ordered placement that `--walks` got in
  463c392; `src/place.rs:139-170` still places by file order
- Share one path-name parser: `split_range_suffix` in `src/gfa.rs:76` reads
  `:start-end` only, while `src/walks.rs` also reads `[start]` and `#start`
- Decide rGFA or plain once, from the full parse: `build` samples the first
  100,000 S lines, while placement checks every one
- Write CSI instead of TBI, which lifts the 512 Mb limit
- Add tests that query an index larger than one BGZF block

### 2. The cheap fix

- Converter: stop writing `<prefix>.<sample>.links.bed.gz`, and cut node rows
  to id and length, with placement columns on rank-1 nodes only. The plugin's
  `launchFromGraph/contributors.ts` reads those placements. Kept, they cost
  11-272 KB a chunk instead of 2-47 KB, still 2-3× under today
- Plugin: build links in `WalkGraph` (`src/RgfaTabixAdapter/walkRows.ts:422`)
  from consecutive decoded steps. `WalkTabixSyntenyAdapter` already reads with
  `links: false`, and every chunk checked held no link its walks don't imply.
  The links file's extras are the link from the previous piece, filed under
  both chunks; the `pv` tag locates that piece
- A reader tells old sets from new by the format header from step 1

### 3. The routes encoding

Build it if cohorts well beyond 464 haplotypes are coming, or if window size
turns out to be the bottleneck.

- **Routes** row: chunk, route id, entry and exit reference handle, carrier
  count, optional per-group counts, delta-encoded steps
- **Choices** row: chunk, haplotype id, contig, fragStart, hapOffset, piece,
  first and last reference handle, then per choice: route id delta, flip, and
  the implied reference step count where the reference repeats a node; `pv` and
  `nx` as today
- **Decoder rules**, checked on every chr22 walk row:
  - the current reference handle's orientation gives the direction of travel
  - a route lands on the occurrence of its exit node nearest the current
    position
  - each row stores its first and last reference handle
  - steps before the first or after the last reference step are open routes,
    and an open route at a row's end still records its exit, which the builder
    knows
- **Builder:** deduplicate routes per chunk through the existing external
  `Sorter` (`src/sorter.rs`) and assign ids in the merge. A table per chunk kept
  in memory while paths stream would hold every chunk until the end
- **Parity test:** every chr22 window's rebuilt walks equal the walk file's,
  step for step
- Write the format up in `docs/format.md`

### 4. Tiers and repeat regions

- A tier made by dropping routes under N bp removes 70-80% of routes and uses
  at 100 bp in typical chunks, but misses the heavy bytes: at 11.80, 18.22,
  18.68 and 38.08 Mb, 90-100% of route bytes sit in long routes at sites with
  10 or more routes. Their nested variation stays at every tier
- Prototype routes as edits against a site consensus, or as nested sites, and
  measure at 18.22 and 38.08 Mb before promising tiers. Edits against a
  consensus cut tokens to 23-26% at 18.15 and 18.68 Mb but only to 58-69% at
  38.08 and 18.22 Mb
- A per-bin summary file (sites, non-reference haplotype fraction, largest
  allele delta, inversions) gives the plugin its planned chromosome overview,
  drawn as a wiggle

### 5. Revisit the container

Past about 2,000 haplotypes, reconsider a bigBed-style single file whose
directory a reader fetches by range, so k haplotypes cost routes plus k small
choice blocks.

## Stop rules for step 3

- Window bytes (routes + choices + nodes) at most 25% of today at the median
  chunk and at most 60% at p99
- Exact rebuild on every chr22 window
- Otherwise keep the walk rows with the cheap fix

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
