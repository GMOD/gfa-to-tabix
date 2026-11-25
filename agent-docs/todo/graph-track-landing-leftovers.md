---
name: graph-track-landing-leftovers
description: Five things the 25 November Fable landing review of the graph track found and did not block on. A long departure at HLA-II draws no mark and its event text says the walk ends. A range label reads 5 bp as 100 bp. Turn-link arrowheads, now the only reversal cue, have no key entry. A thread-fold hover lists more names than haplotypes. Pins for genes outside the window depend on the fit.
metadata:
  repo: bandage-core
---

# What the graph-track landing review left open

Found by the review of bandage-core `owner-asks-c` (38be5f0) on 25 November. Its probes are on ada in `~/work/walks8-gates/agents/landing-review/`.

- **An 89 kb departure draws nothing.**
  - HG01109 and HG02055 leave GRCh38 at chr6:32,486,357 and, per the VCF, rejoin about 89 kb on: 2,363 bp of their own for 88,983 bp of reference.
  - Neither the release nor the stack draws a mark for it.
  - graph-fold's event text calls it "walk ends inside the window", which is false wherever it is shown.
- **A range label overstates a spread.** "3.6–3.7 kb" stands for alleles of 3,650 and 3,655 bp, 5 bp apart, but reads as a 100 bp range.
- **The only reversal cue has no key entry.** Since the node's backward heads are gone, arrowheads on turn links and skip arches are the only drawn sign of reversal, and the key does not name them.
- **A hover lists more names than haplotypes.** The node hover on a thread fold prints one thread's "4 haplotypes on 4 distinct walks…" line, then other threads' names, so five names sit under "4 haplotypes".
- **Out-of-window gene pins depend on the fit.** Whether a gene outside the window gets a pin depends on how the layout fits the pane.
