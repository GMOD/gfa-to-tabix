---
name: query-time-unmeasured
description: Query time against gfaidx is measured only in Node on ada; not yet in a real browser, over a slow connection, or with a keep list of a few haplotypes.
metadata:
  repo: gfa-to-tabix (docs/comparison)
---

# Query time not yet measured

`docs/comparison-details.md`, "Reading a 64 kb window", times graph-walks
9.1.0 against gfaidx on 40 windows each of MC chr22 and pggb chrY, in Node on
ada, local and over HTTP, tile-aligned and with the browser preset. gfaidx is
faster on most chr22 windows, and decoding, not reads, is the cost. Not
measured:

- a real browser, end to end in the reader a user runs
- a slow connection
- a `keep` list of a few haplotypes, which should cut time in proportion to
  steps decoded

Rerun with `docs/comparison/scripts/` (setup.sh, then build.sh, windows.sh and times.sh
on ada; ada `~/work/gfaidx-compare` keeps the indexes) and regenerate the
tables with `tables.py`.
