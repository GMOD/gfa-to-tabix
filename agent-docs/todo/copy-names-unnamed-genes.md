---
name: copy-names-unnamed-genes
description: bandage-core 14.0.0 to 14.1.0 leave C4B, VCY1B, RBMY1E and most TSPY and FAM197Y members unnamed, where 12.3.0 named C4B; the fix, copy-names-final 3ca2e6e, was put off to the next release and is not on main.
metadata:
  repo: bandage-core
---

# Gene copies the reference walks over go unnamed

- A reference gene copy whose stretch walks over an earlier copy's nodes
  keeps its exons and no name (core c4253cf). 14.0.0 shipped it as a known
  regression against 12.3.0
- The fix is `copy-names-final` 3ca2e6e, two commits on 8ce206c, worktree
  `~/src/bandage-core-copynames`: the copy holding the nodes is labelled
  "C4A, C4B" for two copies and "6 TSPY genes" for three or more numbered
  ones, and hover lists every member. Checked on 2026-11-20: bandage-core
  main at 14.1.0 holds neither commit nor those strings
- RBMY1B and RBMY1A1 stay unnamed under it: their own nodes hold under half
  of each
- To land: rebase onto main, run the plugin's suite from a packed tarball,
  and redraw the pairs (ggbandage's C4 ring, pggb chrY's TSPY array, VCY,
  RBMY) before and after
