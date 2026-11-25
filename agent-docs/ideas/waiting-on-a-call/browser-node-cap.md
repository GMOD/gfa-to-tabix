---
name: browser-node-cap
description: Whether the browser readers cap a cut at 30,000 nodes as graph-walks' held node-limit-preset branch does, cap per layout, warn with "Draw anyway", or draw a folded or reference-only picture instead of refusing. docs/node-cap-study.md times the readers and sets out the options; a call picks one.
metadata:
  repo: graph-walks, bandage-core, jbrowse-plugin-graphgenomeviewer
---

# A node cap for the browser readers

- graph-walks' branch `node-limit-preset` (2bf643c, 2026-11-20) caps a
  browser cut at 30,000 nodes, `BROWSER_NODE_LIMIT`, where each browser
  reader capped its own count, from 20,000 to 100,000. It is not on main
  (checked 2026-11-25)
- [node-cap-study.md](../../../docs/node-cap-study.md) times BandageJS and
  the plugin laying out and drawing 4-haplotype cuts from 1,000 to 1.2
  million nodes on chr22 and in the MHC, in five layouts
- The default FMMM layout's first drawing passes 5 s at about 60,000
  nodes on chr22 and about 30,000 in the MHC; walk rows draw a million
  nodes; the stress engine, the tube map and the ordered layout hold the
  tab for their whole time

## The options the study sets out

- One cap in the browser preset, 30,000 as held
- A cap per layout
- A warning with "Draw anyway"
- Drawing a folded or reference-only picture in place of a refusal

The faults the study hit at large cuts are
`../../todo/reader-faults-from-node-cap.md`.
