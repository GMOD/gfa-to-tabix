---
name: odgi-jaccard-placement
description: odgi position's path-Jaccard rule as an unmeasured candidate for which pass a step takes where the reference passes a node more than once. It needs only the graph, as nearest pass does; the criteria it must meet were written before any measurement.
metadata:
  repo: gfa-to-tabix
---

# odgi position's path-Jaccard rule

One candidate under `../waiting-on-a-call/pggb-placement-rule.md`. Nobody
here has measured it.

## The rule

- `odgi position --jaccard-context N` lifts a query step onto a reference
  that passes its node more than once by walking up to N bp (default
  10,000) along the query and along each candidate pass, and taking the
  pass whose surrounding node set has the highest Jaccard overlap with
  the query's
- Source: `src/algorithms/path_jaccard.hpp` in the odgi checkout at
  `~/src/vendor/odgi`
- It needs only the graph, as nearest pass does, where the
  alignment-guided projection needs an alignment input

## Criteria, written before any measurement

For it to replace nearest pass as the writer's rule on pggb graphs:

- scored by `agree.py` with its caveats fixed
  ([placement-scores.md](../../../docs/departures/placement-scores.md#caveats-from-the-review-of-2026-11-01)),
  its agreement with Minigraph-Cactus's placement on pggb chrY and chr22
  reaches the alignment-guided projection's figures within 5 points in
  every stratum, with no stratum below nearest pass
- its departure records on chr22 fall by at least half from nearest
  pass's
- every path rebuilds from its rows
- build time stays within twice nearest pass's

The place-by-chain spike takes the same bar unchanged
(`../../handoffs/2026-11-22-pggb-place-by-chain.md`, "The bar").

## When

- Measure it as a third column of the spike only when someone asks for
  pggb walk tracks, per ADR 0011
- The text of 2026-11 called adopting a placement rule a format change
  under ADR 0011's gate. The format page now calls the pass the writer's
  pick ([Exact and chosen](../../../docs/walks-format.md#exact-and-chosen)),
  so a new rule writes format 8 files; naming the rule in the file would
  be an addition (`../waiting-on-a-call/name-the-placement-policy.md`)
