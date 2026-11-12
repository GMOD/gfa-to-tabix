# Handoff, 2026-11-11, end of session: walk format 8, where it stands

Walk format 8 is written by gfa-to-tabix and read by a graph-walks branch,
both unreleased, and checked on chr22. Nothing is pushed, released or
hosted; the hosted files and the paper are still on format 7 and
gfa-to-tabix 4.0.0. bandage-core is ported on a branch with pictures the
user has not yet approved; the plugin is not started; no genome-wide
format 8 file exists. [ADR 0012](../adr/0012-abridged-blocks.md) is the
decision and holds the acceptance list that stands before hosting;
[the earlier handoff](2026-11-11-abridged-pieces.md) has what the view
gets wrong on format 7 and the tests a fix must pass.

## What is decided, and not to be reopened

A change to any of these needs a consumer failing on a real window, not
another review of the row.

- **Format 8,** not format 7 with an addition: existing readers and
  files count for nothing until the paper is finalized, about
  2026-11-18, and the format doesn't change after that
- **The rows:**
  `seq start end abridged path fragStart hapOffset piece nsteps detail`
  and `seq start end blocks path fragStart piece list`, the list the
  piece in path order, a block `<d><+|-><len>` and a run off R a bare
  number
- **`+` and `-`,** not `>` and `<`, for a block's direction: two
  deciders and two reviewers split evenly
- **The `abridged` row stays slim.** A cut of named haplotypes reads a
  tile's `blocks` unit where one of them has a moved piece there off the
  drawn stretch: 45 KB on one chr22 window, at most 1.7 MB on a genome
  file's worst tile. Giving the row the piece's bp back would not close
  everything; that needs its end steps as well. The cost is measured on
  the genome files as part of acceptance
- **`d` counts along the sequence whichever way the blocks run,** so a
  piece walking steadily against the reference has negative `d`
- **Order:** every consumer reads a file end to end before anything is
  hosted or released

## State by repository

| Repository | Where | Commit | Holds | Pushed |
|---|---|---|---|---|
| gfa-to-tabix | `~/src/gfa-to-tabix`, `main` | the commit of this page | the format 8 writer, spec, proof, six file checkers, ADR 0012 | no; origin and the released 4.0.0 write format 7 |
| gfa-to-tabix | `~/src/gfa-to-tabix-blocks`, `blocks-unit` | the same commit | the worktree the work was done in | no |
| graph-walks | `~/src/graph-walks-blocks`, `blocks-unit` | 7a97d1a | a reader of format 8 only, with its equality harness | no; `main` and the released 6.2.0 read format 7 |
| bandage-core | `~/src/bandage-core-blocks`, `blocks-unit` | 727c540 | the port, the "not loaded" drawing, its equality script and render script | no; `main` (c216a72) untouched |
| JBrowse plugin | `~/src/jb2plugins/jbrowse-plugin-graphgenomeviewer` | 9.1.0 | nothing yet | |
| paper | `~/paper` | | cites gfa-to-tabix 4.0.0 and the format 7 hosted file | |

- **gfa-to-tabix's version is still 4.0.0.** A push to main with a new
  version in Cargo.toml publishes it. Main also isn't pushed before
  graph-walks 7 is released: its CI job that rebuilds every path with
  graph-walks needs a reader of format 8
- **`~/src/gfa-to-tabix/target/` holds stale binaries that write format
  7.** Rebuild before using one; `~/src/gfa-to-tabix-blocks/target/` and
  ada's `~/work/blocks/src/target/release/` are current
- **bandage-core's worktree links graph-walks by a symlink** in
  `node_modules`, not in `package.json`, which still says `^6.2.0`

## What exists as data

- **Format 8, chr22 only:** `ada:~/work/blocks/chr22/f8.GRCh38.walks.gz`,
  HPRC v2.1 Minigraph-Cactus on GRCh38, 18 abridged tiles, 2,572
  abridged pieces; a copy is in the session's scratch directory
- **Format 7, the same graph:** `ada:~/work/blocks/chr22/old.GRCh38.walks.gz`,
  from the released 4.0.0 writer
- **No genome-wide format 8 file.** The genome rebuilds in
  [genome/](../walks-container/abridged/genome/) were of the row as
  first built, under format 7, and are deleted; their figures don't
  carry over. `genome-blocks.sh` rebuilds both, about two hours on ada,
  from `~/work/arb-format-opus/in/{grch38,chm13}.gbz`; its comparison
  with the hosted files must first be changed to leave out `abridged`
  rows, which format 8 rewrites
- **Hosted:** format 7, unchanged

## What is checked, and by whom

| Claim | Run by | Result |
|---|---|---|
| The writer's tests, with ten broken writers failing them | the session | pass |
| The repo's CI steps on ada but for the graph-walks rebuild job | the session | pass, at e3e49de |
| chr22: every unit but `blocks` and tables is the released 4.0.0 writer's bytes | the session, on the row as first built and again with end columns | equal; not rerun on format 8, where `abridged` rows differ by design |
| chr22: every `blocks` row equals graph-walks 6.2's decode of the detail row | the session, `blocks-check.ts`, on the two earlier rows | equal; the script reads the earlier row and is not updated for format 8 |
| chr22, format 8: a reader written from the spec alone reproduces every piece, row and record | a reviewer, `spec8.py` now in the repo | no disagreement |
| What a `blocks` row determines | a prover, from spec and code | proved; 1,870 random graphs |
| graph-walks: unloaded cuts equal loaded ones on chr22 | its author; a reviewer ran an independent comparison against 6.2 | 0 differences in 900 pairs; fails when broken |
| graph-walks' whole suite at 40ec13b | the session | 363 pass, typecheck clean; lint fixed one commit later |
| bandage-core: rows from unloaded cuts equal rows from loaded ones on chr22 | its author only | 0 differences in 432,620 rows; not reviewed |
| bandage-core's suite | its author only | 966 pass on ada; `foldParity.test.ts` fails 7 with ada's 4.0.0 binary, as on main |
| Anything on a genome file in format 8 | nobody | not run |

## Open, in order

- **graph-walks, one gap found by bandage-core:** an unloaded piece that
  reaches the tables only as placeholders among a departure's own steps
  or a gap's steps has no step count anywhere, so its row gets no
  `abridgedSteps` and a host can't offer to load it. 18,104 row-cuts on
  chr22; chr22:11,950,000-11,951,000 HG01433#1#CM086491.1 is one. State
  it in the cut and the tables, then rerun the harness
- **bandage-core, before it lands anywhere:**
  - the user sees the pictures first; they are made, not yet approved
  - `graphTablesGFA` now tags a placeholder's S line `nl:i:1` in
    exported GFA, a new tag nobody ruled on
  - its branch has had no independent review
  - its equality script exits 1 on the gap above alone
- **The plugin:** the load action on every row with unloaded runs,
  following bandage-core's renamed fields; a canvas bar painter draws
  the new `rim`
- **chr22 end to end** through all three, then both genome files rebuilt
  and ADR 0012's acceptance list
- **The spec's remaining prose:** an opening map to GFA, rGFA and PAF
  terms; the departure pyramid's blocks renamed bins, since "block" means
  three things; a last pass over "Reading a window" once the reader is
  settled. `blocks-check.ts` and `piece-ends.ts` read earlier rows
- **Two files still pass every checker:** a step on the other copy of a
  node the reference passes twice
  ([open problems](../open-problems.md#no-check-recomputes-placement-where-the-reference-passes-a-node-twice)).
  `spec8.py` tracebacks on three broken files that it should refuse
  cleanly
- **Releases, with the user's go-ahead and in this order:** graph-walks
  7; gfa-to-tabix 5.0 with main pushed; bandage-core, the plugin and the
  other consumers green on the exact versions; the hosted files swapped
  with them
- **The paper:** the gfa-to-tabix version that built the hosted walk
  file, the sentence measuring a read of eight rows, and three sentences
  that say what a walk file is to a reader who knows GFA
  ([prior art](../walks-container/abridged/reviews.md#prior-art)). If
  the consumers aren't green in time it cites 4.0.0 and today's hosted
  files, which none of this touches

## How the user wants this run

- Experiments, test suites and runs go to `ssh ada`, one agent at a time
  on one connection, capped and niced; edits and a single small test
  file stay local
- Design calls go to independent subagent reviews with criteria written
  first; the user isn't handed a bare choice
- Any change to a drawing is shown before and after, before it lands
- Nothing is pushed or released without their go-ahead

## Where the session's files are

Under `/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/23c92d3c-4125-4046-ad0f-b420d6ec1782/scratchpad/`,
which a reboot may clear:

- `renders/`: the before, after and loaded pictures of five chr22
  windows with a README; `scripts/unloaded/render.entry.ts` on
  bandage-core's branch remakes them
- `f8review/`: the from-spec reader's graphs, 25 hand-broken files and
  its list of where the spec left it guessing
- `review/`, `review2/`: the two reviews of graph-walks' branch, with
  their scripts
- `proof/`: the prover's check and fuzz driver
- `chr22f8/`: a copy of the format 8 chr22 file

On ada, under `~/work/blocks/`: `src` (gfa-to-tabix), `graph-walks-blocks`,
`graph-walks-6.2`, bandage-core's clone, `chr22/`, and `genome-8col/`
with the first rebuild's logs.

## Runs at the end of the session

On ada, by the session, after the last subagent reported:

- **gfa-to-tabix at e3e49de,** the commit before this page: `cargo fmt
  --check`, clippy with warnings denied, 140 tests in release,
  `figures.py --check`, `check-links.py`, `check-claims.py` and the whole
  of `scripts/check-walks.sh`, with its 100 broken files and fuzz seeds
  1 to 6, all pass. The job that rebuilds every path with graph-walks
  was not run: `scripts/graph-walks-rebuild.mjs` needs graph-walks'
  branch, and nobody has run it against that yet
- **graph-walks at 40ec13b:** 363 tests in 11 files pass and the
  typecheck is clean; lint failed on one shadowed name in a test. That
  is renamed in 7a97d1a, where lint and that test file pass locally; the
  whole suite has not been rerun on 7a97d1a
- **bandage-core at 727c540:** nothing run by the session; the figures
  were looked at, and the "after" of chr22:15,952,653 shows hollow
  amber-rimmed bars of 4.4 to 11 kb where "before" drew amber bands of
  16 to 50 kb
