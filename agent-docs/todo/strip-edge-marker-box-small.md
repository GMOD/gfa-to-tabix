---
name: strip-edge-marker-box-small
description: When a hovered node's span lies wholly past the pane's edge, the reference strip boxes the 10 px ◀ or ▶ marker, which is easy to miss now that no leader line leads the eye there.
metadata:
  repo: bandage-core
---

# The edge-marker box is small

- Since 26 November (bandage-core a71ed61) a hover outlines the node and boxes its span on the strip; a span past an edge boxes that edge's marker (`litOutline`, `src/referenceStrip.ts`).
- The user-view Fable review found the box easy to miss (`cfh-open-3-after`, `cfh-beyond-3-after` in `~/src/walks8-evidence/sessions-20261126/plugin-runs-pairs/cfh-line/`). A larger or filled marker while lit may do.
