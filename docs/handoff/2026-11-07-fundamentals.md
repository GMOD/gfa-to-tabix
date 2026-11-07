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

## Not done: the real-data release check

ada answered ping but refused port 22 all day (first "Too many
authentication failures", then "Connection refused"), so nothing ran on
MC chr22 or pggb chrY. Run first when it is back:

```bash
git bundle create /tmp/writer.bundle main
ssh ada mkdir -p ~/work/release && scp /tmp/writer.bundle ada:~/work/release/
ssh ada 'cd ~/work/release && SHARDS=24 nohup bash -c "git clone -q writer.bundle src && bash src/docs/walks-container/writer/scripts/release-check.sh ~/work/release ~/work/arb-format-opus/in ~/work/impl-writer" > release.log 2>&1 &'
```

`release.done` says PASSED or FAILED; `release.<graph>.<check>.txt`
summarise each check and `release.<graph>.cmp.txt` says whether the data
file is byte-identical to the 2026-11-05 build in `~/work/impl-writer`
(it should be: the writer changes since leave real graphs' bytes
unchanged, and MC chr22 was shown identical on 11-06 after the dense
numbering). Commit the `release.*.txt` files under
`docs/walks-container/writer/results/`.

Beware on ada: cap every python with the script's `systemd-run` scopes;
don't `pkill -f` a pattern that appears in your own ssh command line.

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
