---
name: key-edge-mark-wording
description: The key's row for the reference strip's arrowhead still reads "graph runs past this edge", and the drawing's top and bottom edge marks share it; the approved wording and a swatch of their own sit on three unlanded branches.
metadata:
  repo: bandage-core, jbrowse-plugin-graphgenomeviewer, ggbandage
---

# Two edge marks share one key row

- Approved on 2026-11-18: the strip's arrowhead reads "graph's reference
  continues past the pane edge", and the drawing's top and bottom edge marks
  get an entry `runsPastEdge`, "drawing continues above or below the pane",
  with an `overrun` swatch (an up and a down triangle)
- Branches, none landed: bandage-core `pass-rows` 81a1968 (also moves
  `stripFadedShown` into core), plugin 744cfde, ggbandage 18ad713. BandageJS
  needs nothing
- Checked on 2026-11-20: core main's `graphKey.ts` still has "graph runs
  past this edge", and the plugin's `model.ts` passes
  `referenceStripOverhangs || runsPastEdge` as one flag
- Each branch is from before 14.1.0 and 10.1.x; rebase, then ggbandage
  rebundles
