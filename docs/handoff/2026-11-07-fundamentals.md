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
- **Push graph-walks** so the new `rebuild` CI job, pinned to c0d8a23, can
  run on GitHub
