---
name: alleles-exiting-onto-another-sequence
description: Since 8db395f an allele whose only exit is onto another reference sequence gets no row from alleles; how many that drops on a minigraph rGFA is unmeasured. Count them on HPRC's minigraph graph before deciding on breakend rows.
metadata:
  repo: gfa-to-tabix
---

# Alleles that leave one sequence for another

- Since 8db395f an allele's walk stops only at the backbone of the
  sequence it entered from, so an allele whose only exit is onto another
  sequence gets no row (`walk` in `src/alleles.rs`: "None when the walk
  never reaches the backbone of the sequence it left")
- 7a505f0 had kept those exits, because dropping them loses alleles
  minigraph graphs hold; before it, the row ran from the entry's
  coordinate to the exit's, though the two lie on different sequences
- How many alleles this drops on a minigraph rGFA is unmeasured. Only
  d4b3d90 has touched `src/alleles.rs` since 8db395f (checked 2026-11-25)

## Next

Count them on HPRC's minigraph graph. If they matter, write them as
breakends once the allele track can draw one.
