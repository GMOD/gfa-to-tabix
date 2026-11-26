---
name: selected-node-over-arrowheads
description: Since the hover outline (bandage-core a71ed61), a selected node with a strip span is redrawn on the hover layer, over the arrowheads and skip curves the base canvas drew on top of it.
metadata:
  repo: bandage-core
---

# A selected node hides its arrowheads

- Found by the technical Fable review on 26 November (`paintHover`, `Canvas2DRenderer.ts` around 274). Before, this happened only during a hover.
- Redraw only the casing on the hover layer, or redraw the marks that sit on the node after it.
