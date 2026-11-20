---
name: planted-file-gaps
description: Two cases no check plants or tests: a walk file with three ownTiles, and a graph-walks test reading a tagged #hole line (C195).
metadata:
  repo: gfa-to-tabix, graph-walks
---

# Planted-file gaps

- The 2026-11-20 rollout audit found no planted or fixture file with a
  departure naming three `ownTiles`; plant one, and check C85 and C86 hold
  it
- C195 lets `#reference`, `#haplotype` and `#hole` lines carry tags, and
  check-walks runs `tag-hole`, but every `#hole` line in graph-walks' tests
  is untagged (`walkRows.test.ts`, `walkReader.test.ts`). Add one tagged line
  to a reader test
