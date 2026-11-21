---
name: loose-ends
description: One-line leftovers from the format 8 release across the readers: a lockfile mismatch, stale jb2hubs docs, committed figures that drift from their release, a superseded branch, and a plugin gap on diploid-reference files.
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
- **BandageJS `links-between`** (3dac8300): superseded by the `links` setting
  (8af39101); delete the branch
- **Y-9.3M lifting:** nine walks lifted ran out of a 2 GB heap; re-measure
  after graph-walks 98cb1ff
- **graph-walks "Zoom in to about X":** the width is measured from the
  window's left end (`walkRows.ts`), noted at the release and not looked at
  since
- **Hazelnut data on ada:** `~/work/walks8-gates/agents/hazelnut/` keeps
  4.5 GB, among it the private hand-off's staging copy; it waits on the owner's word
  to remove
- **Stashes:** the tube map's and ggtubemap's `switch-f8` worktrees each
  hold a stash of an old scratch-tarball pin
- **Plugin figure, `tube_map_micb_row_hover`:** the key, taller since the
  layout switch heads it, covers the tops of two nodes at the right; 10.1.1
  drew it so, and the figure reshot for 10.2.0 shows it
- **Committed figures drift:** on 2026-11-20 ten plugin figures and four
  BandageJS figures no longer reproduced on the release they were committed
  under. Each reader's figure check (`shoot-figures.mjs --compare`, the
  BandageJS reshoot) belongs in its release steps, not after
