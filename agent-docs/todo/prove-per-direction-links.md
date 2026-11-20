---
name: prove-per-direction-links
description: Prove a walk-file cut's per-direction link crossings against the GFA before bandage-core builds gfaidx-viz's per-direction path list on them.
metadata:
  repo: gfa-to-tabix (docs/comparison/visits)
---

# Prove the per-direction link list

Follow `docs/comparison/visits/`, which proved the copy-number counts:

- truth from the GFA: for each haplotype and each link between two
  reference nodes of a tile, its crossings in each direction
- cut side: the same from consecutive fragment steps and their strands
- compare, stretches inside tiles included
- plant a reversed crossing and a dropped one; both must fail
- a link with an end off the reference gives a lower bound: report how often
  the cut falls short, don't judge it
- run on ada under the caps in `run.sh`

Then [gfaidx-viz-views](../ideas/ready/gfaidx-viz-views.md).
