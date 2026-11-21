---
name: planted-file-gaps
description: No graph-walks test reads a tagged #hole line (C195); one is written on graph-walks' table-coverage branch and lands with its next release.
metadata:
  repo: gfa-to-tabix, graph-walks
---

# A tagged `#hole` line in a reader test

- C195 lets `#reference`, `#haplotype` and `#hole` lines carry tags, and
  check-walks runs `tag-hole`, but every `#hole` line in graph-walks' tests
  is untagged (`walkRows.test.ts`, `walkReader.test.ts`). Add one tagged line
  to a reader test
