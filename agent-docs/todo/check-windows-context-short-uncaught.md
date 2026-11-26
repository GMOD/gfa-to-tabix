---
name: check-windows-context-short-uncaught
description: A fixture-only check-windows run after the move to @gmod/gfa-tabix 10 caught 15 of its 16 planted mistakes but not `context-short`. Settle on ada whether skipped random seeds explain it, or whether the checker no longer fails when the reader clips context short.
metadata:
  repo: gfa-to-tabix
---

# check-windows missed `context-short`

## What is true

- On 26 November, graph-fold-24 moved gfa-to-tabix's scripts to `@gmod/gfa-tabix` 10 (local main 7fce160): `check-windows.sh` now plants its mistakes into `walkFile.ts`.
- A fixture-only run with seed 0, on the laptop, caught 15 of the 16 planted mistakes. It missed `context-short`.
- The code that mistake is planted into is identical in v9.1 and v10, so skipped random seeds is the likely cause. That is unconfirmed.

## To settle, on ada

- Run `check-windows.sh` with the seeds that held `context-short` before, on v10, and on v9.1 with the same seeds.
- If v9.1 catches it and v10 does not, the checker or the plant is broken. Fix it until the mutant fails.
- If neither catches it at these seeds, make the run choose seeds that hold the mutant's case, so it cannot pass by chance.

Relevant to `claims-inventory.md`: a check that does not fail when broken is not a check.
