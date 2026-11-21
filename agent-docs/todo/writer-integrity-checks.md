---
name: writer-integrity-checks
description: Land the walk writer's integrity checks from the 5,000-haplotype failure hunt (sorter run checksums, positions inside their tile, rows unchanged between merge and encoding), so a recurrence says where data changed.
metadata:
  repo: gfa-to-tabix
---

# Integrity checks in the walk writer

A 5.0.1 build once failed with a tile reading another tile's rows plus a
changed byte, and 30 reruns never failed
([scale-past-464.md](../../docs/placement/scale-past-464.md#a-writer-failure-at-5000-haplotypes)).

- The instrumented build is commit b19a617, local branch `race-instrument`
  in `~/work/handoff-1121/gfa-to-tabix-race` on ada, on v5.0.1, unpushed. It
  checksums each sorter run at push, sort, spill and read-back, checks
  merge and tile order, every piece's positions inside its tile at push,
  and each row between merge and encoding. Its output equals the release's.
- No measurable cost in those runs; measure on pggb chrY and MC chr22
  before landing, and keep the error message naming the stage.
- If a failure recurs only under jemalloc, that argues for musl's allocator
  again.
