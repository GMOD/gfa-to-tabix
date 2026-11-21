---
name: reader-faults-from-node-cap
description: Faults the node-cap study hit in bandage-core and its readers at large cuts: the edge hit-test grid stamps a long link over millions of cells and crashes BandageJS on hover, the ordered and stress layouts build the drawing several times, and the plugin's tube map cuts twice.
metadata:
  repo: bandage-core, BandageJS, jbrowse-plugin-graphgenomeviewer
---

# Reader faults at large cuts

Found by [node-cap-study.md](../../docs/node-cap-study.md), 2026-11-21.
Clones and raw runs: `~/work/handoff-1121/runs/nodecap/` on ada.

- **Hover crashes BandageJS from about 36,000 nodes (FMMM, the MHC).** The
  first pointer move builds bandage-core's edge hit-test grid, which stamps
  each link's whole bounding box: two links of the MHC's 400 kb window are
  stamped over about 22 million cells each, and the tab runs out of heap
  (`docs/node-cap/hover-oom.txt`). Index a link by the cells its curve
  crosses, or by its bounding box only up to a cell budget. Check whether
  the plugin's hover shares it
- **The ordered and stress layouts build the drawing 2–4 times before the
  first paint,** in both readers: at chr22 10 Mb the ordered layout takes
  about 1 s and the duplicated builds 83 s and 108 s
- **The plugin's tube map cuts and lays out twice** where a cut holds
  placeholders (chr22 10 Mb, chr6 0.4 and 1.8 Mb)
- **The plugin's ordered view is replaced by a `ChunkLoadError`** at chr22
  10 Mb and chr6 5.5 Mb, apparently JBrowse timing out a code chunk while
  the layout holds the page
- **The tube map crashes the tab** at 277,560 nodes in the MHC and 1.2 M on
  chr22; not diagnosed
