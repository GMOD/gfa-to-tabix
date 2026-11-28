---
name: tube-maps-read-removed-graph-fold-api
description: sequenceTubeMapModern and ggtubemap import graph-fold's branchLabel and read Branch.description, which graph-fold 2 removes; until migrated they stay on 1.x and keep the "n of m" sentences and the 5% clustering that draws a haplotype off its own route.
metadata:
  repo: sequenceTubeMapModern, ggtubemap
---

# Tube maps read API that graph-fold 2 removes

Found by the technical Fable review of the `claims` branches on 27 November.

- `~/src/sequenceTubeMapModern` (`@jbrowse/graph-fold` `^1.3.0`): imports `branchLabel` (`src/util/tubemap.ts:14`), prints it at `:1406`, `:1757`, `:1789`, and folds with `cluster: true` (`src/components/tubeMapData.ts:85`).
- `~/src/gmod/ggtubemap` (`^1.1.0`): imports `branchLabel` and reads `b.description` (`tools/walks.js:4`, `:118`, `:135`).
- A major version keeps them from breaking. They keep the sentences classed false in `claims-inventory.md` and the released clustering until moved to 2.x: drop the sentences, take branch `kind`, sizes and `haplotypes` as data.
