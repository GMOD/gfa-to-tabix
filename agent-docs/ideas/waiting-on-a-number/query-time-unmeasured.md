---
name: query-time-unmeasured
description: Query time against gfaidx is measured only in Node on ada; not yet in a real browser, over a slow connection, with a keep list of a few haplotypes, or after graph-walks 98cb1ff halved the every-haplotype cut.
metadata:
  repo: gfa-to-tabix (docs/comparison)
---

# Query time not yet measured

`docs/comparison.md`, "Reading a 64 kb window", times graph-walks against
gfaidx on 40 windows each of MC chr22 and pggb chrY, in Node on ada, local and
over HTTP. gfaidx was about 2x faster on chr22 windows, and decoding, not
reads, was the cost. Not measured:

- graph-walks after 98cb1ff (a cut of every haplotype in under half the time)
- a real browser, end to end in the reader a user runs
- a slow connection
- a `keep` list of a few haplotypes, which should cut time in proportion to
  steps decoded

Rerun with `docs/comparison/scripts/` (setup.sh, then build.sh and windows.sh
on ada; ada `~/work/gfaidx-compare` keeps the indexes) and regenerate the
tables with `tables.py`.
