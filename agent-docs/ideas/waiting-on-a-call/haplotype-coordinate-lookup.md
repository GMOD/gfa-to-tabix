---
name: haplotype-coordinate-lookup
description: A side file from a haplotype's own coordinates to the tiles holding it, built from walk rows' path and hapOffset, so a reader can open a walk file at a position on a haplotype rather than the reference.
metadata:
  repo: gfa-to-tabix
---

# Looking up a haplotype's own coordinates

Walk rows carry `path` and `hapOffset`, so a side file can map a haplotype
position to tiles without changing the walk file. It falls under
`side-file-pairing-rule.md`, which a side file must answer first. Not before the freeze.
