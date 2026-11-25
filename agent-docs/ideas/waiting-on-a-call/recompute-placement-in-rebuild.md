---
name: recompute-placement-in-rebuild
description: No file checker places a step itself where the reference passes a node twice, so a file with a step put on the other copy passes all six. State nearest pass and stay exactly, then recompute each such step's pass from the GFA in walks-truth.py rebuild, as a check of gfa-to-tabix rather than of the format, once a pggb walk file is to be hosted.
metadata:
  repo: gfa-to-tabix
---

# No check recomputes placement on revisited nodes

- A file with a step put on the other copy of a node the reference passes
  twice, and its detail, `abridged` and `blocks` rows all agreeing with
  that, passes all six file checkers
  ([review](../../../docs/walks-container/abridged/reviews.md#format-8-from-the-spec-alone),
  2026-11-11). The build's own check and the tests catch a writer that
  does it; a file checker can't without placing the step itself
- The pages don't pin the rule tightly enough to place a step from them:
  what the nearest pass is predicted from for a step against the
  reference, and the order a stay evaluates its steps in
- It can't happen where `revisited` is 0, so not on a Minigraph-Cactus
  file, and no hosted walk file has a revisited node
- The format page calls the pass the writer's pick
  ([Exact and chosen](../../../docs/walks-format.md#exact-and-chosen)), so
  a file placed otherwise is a format 8 file with another placement, not a
  broken one; the check would be of gfa-to-tabix, not of the format.
  Which checkers mix the two is
  `../../todo/checkers-hold-a-file-to-the-format-alone.md`

## The change

State the two rules exactly, then recompute each such step's pass from
the GFA in `scripts/walks-truth.py rebuild`.

## What it waits on

pggb placement work starting, or a pggb walk file to be hosted
(`pggb-placement-rule.md`, `../../handoffs/2026-11-22-pggb-place-by-chain.md`).
