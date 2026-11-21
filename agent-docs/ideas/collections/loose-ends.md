---
name: loose-ends
description: One-line leftovers from the format 8 release across the readers: a lockfile mismatch, stale jb2hubs docs, figures that differ from a reshoot, a superseded branch, and a plugin gap on diploid-reference files.
metadata:
  repo: several
---

# Loose ends from the release

- **Plugin, diploid-reference files:** the forms track resolves by header
  sample and errors on a file whose reference sample has two haplotypes, and
  Add Track needs `HG002#1` typed
- **gbz-base versions:** bandage-core locks `@gmod/gbz-base` 7.4.0 and the
  plugin 7.4.1; under a hand-linked setup the plugin's typecheck fails in
  `GbzBaseSyntenyAdapter.ts`. Bump core's
- **jb2hubs docs:** `reference/PANGENOME_PAGES.md:137` still says "under 8 M
  steps" and `ideas/ready/gene-lanes-and-threaded-graph.md:35` says the walk
  file is format 7
- **jb2hubs fly/chrM:** a launch failure seen on 2026-11-15, to check on main
- **BandageJS figures:** 15 of its 18 committed README and tutorial figures
  differ from a reshoot of main made before the graph-walks 8.0.1 bump; look
  at the pairs before recommitting
- **BandageJS `links-between`** (3dac8300): superseded by the `links` setting
  (8af39101); delete the branch
- **Y-9.3M lifting:** nine walks lifted ran out of a 2 GB heap; re-measure
  after graph-walks 98cb1ff
- **graph-walks "Zoom in to about X":** the width is measured from the
  window's left end (`walkRows.ts`), noted at the release and not looked at
  since
- **Hazelnut data on ada:** `~/work/walks8-gates/agents/hazelnut/` keeps
  1.9 GB of the private hand-off's staging copy; it waits on the owner's word
  to remove
- **Stashes:** the tube map's and ggtubemap's `switch-f8` worktrees each
  hold a stash of an old scratch-tarball pin
- **Local checkouts behind origin (2026-11-20):** `~/src/BandageJS`,
  `ggbandage`, `sequenceTubeMapModern` and `gmod/ggtubemap` are 6 to 60
  commits behind, so their `package.json` shows pins origin left long ago;
  read `origin/<default>` instead
