---
name: gate-draws-no-faceted-track
description: The drawing gate's contact sheet and the release's final pairs draw no force track split by walk, so plugin 10.0.0 shipped with every such panel blank; add one faceted window and prove it with the 10.0.0 build.
metadata:
  repo: walks8-evidence (fab8f323/drawcheck-merged)
---

# The gate draws no faceted force track

- Plugin 10.0.0 drew blank panels for a force-layout track faceted by walk
  (`force_kiv2_facet`, `force_gstm1_three_ways`). The cause was the reader
  building facets before the pane was fitted; 10.0.1 and 10.0.2 fixed it
- The plugin's `shoot-figures.mjs` now fails a facet canvas with no ink. The
  gate's sheet still has no faceted shot
- Add a faceted KIV-2 window to the sheet with a check that every panel has
  ink, and show it fails on the 10.0.0 build
