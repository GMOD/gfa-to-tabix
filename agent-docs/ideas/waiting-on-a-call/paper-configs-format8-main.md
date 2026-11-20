---
name: paper-configs-format8-main
description: The live paper_hprc.json loads plugin 9.0.0 on the plain GRCh38 walk name, which serves format 8 since the cutover; jbrowse-components branch format8-main fixes it and waits on the owner's push.
metadata:
  repo: jbrowse-components
---

# The paper's live config reads format 8 with plugin 9.0.0

- origin/main's `test_data/graphgenomeview/paper_hprc.json` loads
  `graphgenomeviewer/9.0.0` and sets `walksUri` to
  `https://jbrowse.org/demos/hprc/hprc-v2.1-mc-grch38.GRCh38`, whose bytes are
  format 8 since the 2026-11-19 cutover. Plugin 9 reads format 7
- Local branch `format8-main` (worktree `~/src/gw8-worktrees/jbrowse-components`)
  moves the paper configs to plugin 10.0.1 and the `-f8` file, fixes the
  top-level `color` key and the relative gene-file paths, and updates the HPRC
  README and the graph tutorial. The owner chose this on 2026-11-20; main is
  theirs to push
- Paper Figures 2c and 5 keep their plugin 9.0.0 renders, which read the rGFA
  index, not the walk file
