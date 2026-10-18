# Handoff: step placement and `--stay`

Status on 2026-10-18: main holds nearest-pass placement, `--stay` (default 311),
`maxnode` over reference nodes and the `stay:i:` header tag, all unreleased and
unpushed. [ADR 0001](../adr/0001-step-placement.md) records the criteria and
results; [walks-format.md](../walks-format.md) describes the rules.

- **Done:** pggb chr22 stay sweep (311 and 1024), genome-wide MC comparison of
  nearest by offset and by chunk (equal), two subagent reviews, 12,400-graph
  round-trip fuzz with no defect
- **Open:** the default stay, below. Neither stay passes ADR criteria 4, 5 or 6
  on pggb

## Decide first

- **Default stay.** 311 changes rows on graphs with no revisited node (ADR
  criterion 2 holds only at `--stay 0`) and files absorbed steps outside their
  own window, which a lookback cannot reach. Recommended: default 0, with
  `--stay 311` or `1024` opt-in for pggb. Then re-run the genome-wide MC build
  at the shipped settings and check the GRCh38 rows match 1.1.0
- **Stay 311 or 1024 for pggb.** 1024 cuts pieces by 50% (GRCh38) and 61%
  (CHM13) for under 0.5 point of strict recall

## Follow-ups

1. **Giant windows.** chr22 GRCh38 at 12.6–13.0M peaks at 205 MB gzipped under
   every stay; the CHM13 short arm at 65–75 MB, with 516 windows over 32 M
   steps. Filing moves no steps out of a chunk, so this needs a different fix
   (see the paralog-jump design memory)
2. **Reader contract.** graph-walks commit 79634c3 implements "a `ref` row's
   placement wins". Rule 3 does not say which pass wins when a node has `ref`
   rows in several chunks the reader read. Specify it, and ship the reader
   before any file written with a stay
3. **Reconcile revisit counts.** The ADR context says genome-wide MC CHM13
   revisits 209,578 nodes; `nearest.log` says 512,386 nodes are visited in more
   than one chunk. The second count cannot exceed the first
4. **Criterion 3 per region.** The per-region check at *L* = 1 lacks a
   first-visit row. Score first-visit pggb chr22 at *L* = 1 with
   `--regions scripts/walks-truth-regions.tsv`
5. **MC at the shipped settings.** The genome-wide comparison ran a binary
   without `--stay`; MC at stay 311 was never measured
6. **Rescan cost.** `stay_home` (`src/walks.rs`) can rescan an off-reference
   stretch about stay ÷ shortest-reference-node-length times where chunk
   changes are dense. The pggb chr22 build ran faster than main, so measure
   before changing
7. **Docs.**
   - Add the revisit table's memory (16–24 bytes per pass) to the Scale section
     of `docs/walks.md`
   - Shorten the comments on `visits_along` and `stay_home`
   - Wrap `docs/walks.md` lines 71 and 85
8. **Cleanup.** The `nearest-visit` worktree and branch stay until its live
   `claude` session exits: `git worktree remove` it, then `git branch -d`. Push
   main and release when the default is settled

## Where things are

- **ada:** `~/nearest-main/stay/sweep.out` (sweep), `~/nearest-main/genome/`
  (MC builds and `cost.out`), `~/nearest-main/walks-truth.py`, `score2.sh`,
  `cost.sh`
- **Fuzz test:** the scratchpad's `fuzz-walks.rs` (`fuzz_rebuilds`); promote
  it into `tests/` if it should run in CI
