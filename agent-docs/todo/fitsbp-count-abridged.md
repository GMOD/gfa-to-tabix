---
name: fitsbp-count-abridged
description: graph-walks' early refusal suggests a zoom-in width (fitsBp) more than a tile off the widest window that draws in 5 of 32 refused windows; counting abridged pieces from their blocks rows would bring that to 4, at the cost of a fetch before refusing.
metadata:
  repo: graph-walks
---

# fitsBp from abridged pieces

The early refusal works `fitsBp` out tile by tile from the steps it surely
keeps, which leave abridged pieces at 0. Against the widest window that
truly cuts, found by bisection, it misses by more than a tile in 5 of 32
refused windows; the full cut's own estimate missed in 13.

- Counting each abridged piece's built steps from its `blocks` rows would
  bring the misses to 4 of 32, by `fits_eval.py`.
- It needs the `blocks` unit fetched before refusing, which the early
  refusal exists to avoid. Worth it only if a suggestion's miss is seen to
  matter in a viewer.
- Evidence: `~/work/followup-20261120/early-refusal/` on ada (`bisect.tsv`,
  `tilecounts2.tsv`, `refuse2.tsv`, `fits_eval.py`).
