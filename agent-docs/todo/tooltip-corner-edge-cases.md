---
name: tooltip-corner-edge-cases
description: The graph hover's tooltip moves to the bottom-left corner when it would cover the hovered node, but does not check the corner is clear, re-measure when its text grows, or avoid walk-row labels there; the node box is the polyline's bounding box.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# Tooltip corner edge cases

From the technical Fable review of plugin c16f451a on 26 November:

- A node spanning the bottom of the pane, or a tooltip wider or taller than a small pane, is covered in either corner.
- The effect's dependencies omit the tooltip's content, so text that grows while the same node stays hovered is not re-measured.
- `hoveredNodeScreenBox` is the polyline's bounding box, so a curved node can move the tooltip without being under it.
- Walk-row labels sit in the bottom-left corner.
- Only the shots prove the move; jsdom cannot measure it.
