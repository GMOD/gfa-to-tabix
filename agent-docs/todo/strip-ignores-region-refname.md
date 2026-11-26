---
name: strip-ignores-region-refname
description: The reference strip lays one linear frame across the whole pane and ignores a node's `stable.refName`, so in a linear view showing several regions a hover box or strip block can sit over the neighbouring region's pixels.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# The strip in a multi-region linear view

- Found by the technical Fable review of the hover fix on 26 November: `host.ts` around line 81 maps bp to x with one frame; `beyond` is on the window's own sequence (`threadFold.ts` around 149).
- True of the strip's blocks before the fix; open spans make a wrong box likelier.
- Check with a linear view showing two regions of different sequences, and box only on the region the span lies in.
