---
name: reader-faults-from-node-cap
description: What is left of the faults the node-cap study hit at large cuts once the crashes were fixed: the plugin's tube map cutting twice, slow tube-map ordering past 200,000 nodes, no tube-map node limit in BandageJS and the plugin, the plugin's ChunkLoadError, and stale KIV-2 figures.
metadata:
  repo: bandage-core, BandageJS, jbrowse-plugin-graphgenomeviewer
---

# Reader faults at large cuts

Found by [node-cap-study.md](../../docs/node-cap-study.md), 2026-11-21.
Clones and raw runs: `~/work/handoff-1121/runs/nodecap/` on ada.

- **Fixed 2026-11-22/23:** the hover crash (bandage-core 14.3.3), the
  duplicated layout builds (14.4.0, plugin 10.5.1), the tube map laying out
  twice (plugin 10.5.1) and its out-of-memory ordering pass (tubemap-core
  2.1.1, bandage-core 14.4.1)
- **The plugin's tube map still cuts twice** where a cut abridges walks it
  draws: one cut needs the adapter to report which walks it expanded
- **The tube map's ordering is still slow past ~200,000 nodes:** each
  insertion shifts everything to its right, settled once since 2.1.1; the
  5.5 Mb MHC window settles about 557 M nodes in ~107 s, and chr22's
  1.2 M-node window ran 40 minutes without finishing the first pass. Apply
  a track's shifts at once, or another ordering
- **BandageJS and the plugin have no tube-map node limit before layout;**
  sequenceTubeMap's 50,000 backstop and 30,000-visit render cap
  (`GBZBaseAPI.ts:273`, `TubeMapContainer.tsx:85`) are its own
- **The plugin's ordered view is replaced by a `ChunkLoadError`** at chr22
  10 Mb and chr6 5.5 Mb, apparently JBrowse timing out a code chunk while
  the layout holds the page
- **bandage-core's KIV-2 figures are stale:** `img/figure_kiv2_facets.svg`,
  `figure_kiv2_threads.svg` and `figure_kiv2_walks.svg` were drawn by
  13.3.0; `scripts/render-figures.mjs` on 14.3.0 draws the new key row,
  layout and grey threads. CI does not render them; reshoot and look
