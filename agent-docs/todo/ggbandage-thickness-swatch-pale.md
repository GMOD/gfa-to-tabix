---
name: ggbandage-thickness-swatch-pale
description: ggbandage's gallery on the released 14.10.0 bundle draws the Thickness key's swatches pale grey in kiv2_walks, syng_overlay and syng_rhd, where the committed gallery shows them charcoal; the gallery was not redrawn when the bundle moved, so it no longer shows what the package draws.
metadata:
  repo: ggbandage
---

# Pale thickness swatches in ggbandage's walk figures

- Drawn on 27 November with `scripts/gallery.R`: ggbandage main (bundle
  14.10.0) and the 15.0.0 bundle draw the three figures identically, and both
  differ from the committed gallery only in the Thickness swatches (about 0.1%
  of pixels each).
- The swatch colour comes from bandage-core's `graphKey` (`key_rows` in
  `R/geoms.R`). With walks lifted, the swatch now takes the faded grey of
  the unlifted threads, the same as "other haplotypes", and a pale bar on white
  barely reads.
- Before and after crops: `~/src/walks8-evidence/sessions-20261127/ggbandage-swatch/`.
- To decide: whether the key's thickness swatch should show the faded ink it
  stands for or a charcoal one that reads, then redraw and commit the gallery
  either way, since it is stale now.
