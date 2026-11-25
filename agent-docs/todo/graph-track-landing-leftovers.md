---
name: graph-track-landing-leftovers
description: What is left of the 25 November Fable landing review of the graph track. A long departure at HLA-II draws no mark and its event text says the walk ends. Turn-link arrowheads, now the only reversal cue, have no key entry. The plugin's thread-fold hover must adopt core's per-thread line. Pins for genes outside the window depend on the fit.
metadata:
  repo: bandage-core
---

# What the graph-track landing review left open

Found by the review of bandage-core `owner-asks-c` (38be5f0) on 25 November. Its probes are on ada in `~/work/walks8-gates/agents/landing-review/`.

- **An 89 kb departure draws nothing.**
  - HG01109 and HG02055 leave GRCh38 at chr6:32,486,357 and, per the VCF, rejoin about 89 kb on: 2,363 bp of their own for 88,983 bp of reference.
  - Neither the release nor the stack draws a mark for it.
  - graph-fold's event text calls it "walk ends inside the window", which is false wherever it is shown.
- **The only reversal cue has no key entry.** Since the node's backward heads are gone, arrowheads on turn links and skip arches are the only drawn sign of reversal, and the key does not name them.
- **A hover lists more names than haplotypes.** The plugin's node hover on a thread fold (`HoverTooltip.tsx`, `foldedNodeLines`) prints one thread's "4 haplotypes on 4 distinct walks…" line, then other threads' bare names, so five names sit under "4 haplotypes". bandage-core 56d4f9b gives each thread from `threadsThrough` a `line` that opens on its count ("1 haplotype: HG00097#1"); the plugin prints `thread.line` once a core release carries it.
- **Out-of-window gene pins depend on the fit.** Whether a gene outside the window gets a pin depends on how the layout fits the pane.
