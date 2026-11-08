# Handoff, 2026-11-07: the fundamentals of a walk file, and what still proves them

The user asked for confidence in format 7 and its reader and writer from
the fundamentals, not the edge cases. A walk file is sound when:

- every W or P line of the GFA with a step on the reference rebuilds from
  the file step for step, handles and strands, its pieces numbered from 0
  and each starting where the one before ends, abridged pieces from their
  detail units
- the reference's own lines rebuild from the `ref` rows likewise, with
  each step's length, so every position in the file is the GFA's
- the file holds exactly those lines, and no other
- the bytes don't depend on the machine: the same file at any thread count
- the consumer that ships, graph-walks, reads the writer's files back to
  the GFA
- all of that holds on the hosted graph, MC chr22, not only on fixtures
- each abridged row says what its detail unit's piece says: start, end,
  hapOffset, nsteps, bp and the record named. `rebuild` checks this since
  11-08, beside audit7's check; five `abridged-*` broken files prove both

## What this session added

- **`scripts/walks-truth.py rebuild WALKS GFA [--shard I/N]`** does the
  first three. It decodes every walk row by the spec's rules (the decoder
  `score` already used, made to emit handles and to refuse a step off the
  end of R instead of wrapping), takes abridged pieces from their detail
  units, hashes each piece's handles, and compares each line's pieces in
  order with the GFA's steps, 0 bp segments dropped. It replaces the
  `pieces` subcommand, which only summed bp, so a wrong node of the same
  length or a flipped strand passed it, and passed every other checker
  too. Hashing per piece keeps memory at the number of pieces, so it runs
  on MC chr22 (630 M steps) in shards
- **Eight broken files fail it** (`docs/departures/scripts/broken/`,
  `broken.sh`): three new ones only it catches, an interior step's strand
  flipped in a tile (`interior-flipped`), in a detail unit
  (`detail-interior-flipped`), and a reference step's strand flipped with
  every walk row's start there (`ref-strand-flipped`); and five existing
  ones it catches beside their checkers (`hole-inside`, `hole-trailing`,
  `last-piece-dropped`, `ref-lengths`, `reference-wrong`). Each was
  shown passing verify7, claims7 and audit7 before it was added
- **`broken/corrupt.py`** writes a broken file from a good one by exact
  text replacement, repacking the units, tables and directory, so a
  broken file is reproducible from its description
- **CI** runs the rebuild on every fixture under every option set and on
  the fuzz seeds (`check-walks.sh`, `fuzz7.sh`); all pass
- **Thread determinism:** 95 files built at 1, 2 and all 16 threads, on
  the ten walk fixtures under five option sets and five fuzz graphs under
  three, are byte-identical
- **`docs/walks-container/writer/scripts/release-check.sh`** runs the
  real-data release check on ada: builds MC chr22 and pggb chrY, compares
  bytes with the previous build, and runs verify7, claims7, audit7 and the
  rebuild in shards

## The real-data release check: done, PASSED

ada came back in the afternoon and
`docs/walks-container/writer/scripts/release-check.sh` ran there on MC
chr22 and pggb chrY (results and numbers in
[writer/README.md](../walks-container/writer/README.md#the-release-check-of-2026-11-07),
files under `writer/results/release.*`). MC chr22 is byte-identical to
the 11-06 build; both files pass verify7, rebuild every line step for
step from the file against the GFA in 24 shards, and pass audit7 with
the GFA. claims7 --own did not run: see the issues log for its memory and
time on a chromosome, and the script's `CLAIMS7=1`.

To rerun: bundle main, copy it to `ada:~/work/release/writer.bundle`,
and run `bash ~/work/release/launch.sh` there (it clones the bundle's
main and starts the script detached; `kill.sh` beside it stops a run).
`release.done` says PASSED or FAILED. Beware on ada: cap every python
with the script's `systemd-run` scopes; don't `pkill -f` a pattern that
appears in your own ssh command line.

## Side quests, not for this session

Ideas raised on 2026-11-07 and parked, each with where it is written up:

- **odgi's path-Jaccard placement** as a graph-only rule for collapsed
  repeats: candidate and criteria in
  [open-problems.md](../open-problems.md#placement-of-steps-on-nodes-the-reference-passes-more-than-once).
  Measure only when someone asks for pggb tracks
- **Fix `agree.py`'s caveats and rerun** the nearest-pass versus
  alignment-guided scores, so the impg-based figures are trustworthy before
  any pggb placement decision (caveats listed in open-problems.md)
- **odgi viz / bin** as prior art for a zoomed-out summary row kind, if a
  coarse tier for walk files is ever wanted; no trigger today
- **Push graph-walks** so the new `rebuild` CI job, pinned to e7259ee, can
  run on GitHub

## The consumer ports, done the same evening

Per ADR 0011's next steps, every consumer now reads format 7 through
graph-walks 6, each landed on its own `main` as a fast-forward, nothing
pushed:

- **graph-walks** `e6e5a74` (27 commits ahead of origin, 6.0.0 unreleased):
  `bytesFor` refuses a range that is not finite; `pathChains` chains by the
  untrimmed contig stretch; the release check compares reads on tile extents
- **bandage-core** `aa479d0`: the walk tests open `test_data/walks7/*.walks.gz`
  with graph-walks 6, every expectation unchanged; and a fix, `818a1c6`, for
  a departure hidden behind its flank steps at the default context (issues
  log). One existing expectation flipped with it: a lone flank beside a
  departure crossing the window reads stepless, as it already did at
  context 0, not "goes on"
- **jbrowse-plugin-graphgenomeviewer** `8a0242e`: a two-major port from
  graph-walks 4.6.0 and bandage-core 12.7.1. The walk file is
  `<prefix>.<ref>.walks.gz` with its directory from the `walksIndex` slot or
  `<walksLocation>.idx` beside it; `walksUri` resolves both. The byte gate
  reads `reader.bytesFor`; reference nodes come from `reader.referenceNodes`;
  lanes read departures in place of skip rows and crossings. The format 5
  fixtures were decoded with graph-walks 4.6.0 into GFAs under
  `src/RgfaTabixAdapter/test_data/walks7/`, rebuilt in format 7 by
  `build.sh` there
- **BandageJS** `13a3272a`, **sequenceTubeMapModern** `a07e923`,
  **ggbandage** `2b289c2` (R package, bundle rebuilt byte-identical to its
  commit), **jb2hubs** `53c77095` (website): each from its earlier
  graph-walks 5 branch under `~/src/port`, now removed; no expectation
  changed in any of them. Each names the format 7 HPRC file
  `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38.GRCh38.walks.gz`,
  which is not hosted yet
- **Gates:** typecheck, lint, format check and the full unit suites are
  green in all seven; ggbandage's `R CMD check` 0 errors 0 warnings. Not
  run: browser and e2e suites. The plugin's five chr22 real-data tests ran
  on 11-08 against `~/work/scratch/walks7/chr22.GRCh38.walks.gz` (the
  release-check MC chr22 build) and `chr22.CHM13.walks.gz` (a copy of the
  genome-wide CHM13 file), all 22 of `walkFiles.test.ts` pass; after a
  port landed from a worktree, run `pnpm install` in the main checkout
  before trusting its tests, since its node_modules still held graph-walks 4

Every consumer pins the unreleased packages by `file:` tarballs under
`~/src/vendor/walks6-pack/` (graph-walks packed from `e6e5a74`,
bandage-core from `818a1c6`). pnpm writes a `file:` path relative to the
lockfile, so a lockfile written in a deeper worktree breaks `pnpm install`
in the main checkout: the four repos ported under `~/src/port` got a
lockfile commit for that. The bandage-core tarball itself lists graph-walks
as a `file:` devDependency; swap that before publishing.

### The release sequence, each step gated by the one before

- **Host the genome-wide files.** `ada:~/work/genome7/genome7.sh` builds
  `hprc-v2.1-mc-grch38.GRCh38.walks.gz` and `hprc-v2.1-mc-chm13.CHM13.walks.gz`
  (plus `.idx`) with the writer at 1e698f4 from the GFAs genome3 left, and
  runs verify7 on each; `genome7.done` says PASSED or FAILED. Then
  `graph-walks` on ada (`~/work/genome7/graph-walks`, main at e7259ee,
  installed): `WALKS=~/work/genome7/hprc-v2.1-mc-grch38.GRCh38.walks.gz pnpm release-check`
  (REF_NAME chr22 by default). Upload both files and both `.idx` with
  jbrowse-components' `scripts/deploy-demo.sh <file> hprc/<name>`, never a
  bare `aws s3 cp`, then run the same release-check with `WALKS` as the
  hosted URL. The hosted format 5 files stay for old sessions
- **Release-check result, 2026-11-08:** with graph-walks e6e5a74 both
  files pass 28 of 28 (the CHM13 failures were the check's assumption and
  one reader chain fault, issues log); both are ready to host
- **Push graph-walks** and let gfa-to-tabix's `rebuild` CI job run; tag
  `v6.0.0` and publish
- **bandage-core:** pin `^6.0.0`, `pnpm install`, gates, `pnpm version minor`
  (the row fix changes what a row says), which pushes and publishes through
  its hooks
- **The plugin:** pin graph-walks `^6.0.0` and the published bandage-core,
  gates, push, wait for the Push workflow (`ci-green`), `pnpm version major`
  (the `walksIndex` slot and format 7 only), then `~/src/jbrowse-plugin-list`
  `pnpm dep` to rehost `latest/`
- **BandageJS, the tube map, ggbandage, jb2hubs:** swap pins, install,
  gates, release each the way its repo does; jb2hubs' `upload.sh` and the
  `.hprc-grch38-uploaded.json` stamp after the files are hosted
- **Swap the configs in one pass:** jbrowse-components `demos/hprc/config.json`
  and `test_data/graphgenomeview/*.json` to the format 7 names, the plugin's
  `latest/`, and the paper's Data Availability URL
  (`hprc-v2.1-mc-grch38-f5s.GRCh38.walks.bed.gz` today)
- **Look at real windows**

## The README schematic, 2026-11-07

`docs/figures/walks-schematic.svg` (README) shows each W line beside its
stroke and the real rows it became for one tile, the window shaded, one
request's bytes; `walks-bytes.svg` (spec, "Files and units") shows the
`.idx`, the data file as a byte bar of units, and the window's two adjacent
units as one request. Both are drawn by `scripts/figures.py` from the
writer's output on `walks-schematic.gfa`, so CI's figure check holds them
to the tool. Chosen from three variants after an independent read; the
old pipeline figure `walks-simple-figure.svg` is gone.

## The paper, 2026-11-07

`~/paper` `003affe`: reviewer 1's comment 4 (gfa-to-pairwise-paf's shared-node
alignments, repeated nodes) is answered in
`reviews/2026-11-03-reviewer1-response.md`, with Method and Results
sentences and Supplementary Table S7 in `\rev`. GRCh38 passes every node
of the MC graph once (83,303,684 nodes, counted over the full GFA);
minimap2 agrees with the graph-derived rows on 99.3 to 99.9% of bases at
the CFHR window and 99.6% genome-wide for HG00133#1; the one disagreement
over 1 kb is the breakpoint's place inside the 960 bp repeat pair flanking
the 84.7 kb deletion. Measurements under `bench/paf-vs-minimap2/` there and
`ada:~/work/paf-vs-minimap2/`. `make push-response` sends the response
draft to the Google Doc; not run. Owed: the supplementary figure with both
alignment sets as rows

## The paper, 2026-11-08

`~/paper` `835fd78`: two supplementary figures for reviewer 1, both in
`\rev`. `fig:bubble-intervals` is the histogram of the reference interval
each HPRC v2.1 SV rGFA bubble is filed under (comment 3; jb2bench `143b713`
`scripts/paperfigs/bubble-intervals.R`, drawn by `make plots` as figS11).
`fig:paf-vs-minimap2` is the CFHR window with the graph-derived rows over
minimap2's (comment 4): jbrowse-components spec
`website/scripts/specs/paper-hprc-minimap2.ts`, `paper/hprc_rows_graph_vs_minimap2`,
which reads `https://jbrowse.org/demos/hprc_multiway/hprc_cfhr_minimap2.pif.gz`.
That PIF (minimap2 primary rows, PanSN target names, built by
`bench/paf-vs-minimap2/scripts/make_minimap2_pif.sh`) is at
`ada:~/work/paf-vs-minimap2/pif/` and is not hosted; the paper's PNG is a
local render of the same bytes. Hosting it belongs with the hosting pass
above: `deploy-demo.sh` the two files to `hprc_multiway/`, re-render,
`pnpm figures:push --filter paper/hprc_rows_graph_vs_minimap2`, then add the
figure to `figures/sync-website.py`. Also found: the 3 November EC2
benchmark run (reviewer 1 comments 1 and 2) never ran; jb2bench's
`results/ec2/2026-11-03-1041/` holds only the preflight log and the instance
is gone, so it has to be launched again.
