---
name: rgfacut-doc-whole-bubbles-and-a-source-check
description: rgfaCut's doc does not say that a cut holds what attaches under the window and not whole bubbles, nor that a hop count on the contig layout is no guarantee of a closed cut; and nothing in graph-walks checks a node/link cut against its source rGFA. A jb2hubs session wrote such a check and measured both on eight hosted graphs.
metadata:
  repo: graph-walks
---

# rgfaCut: say what a cut holds, and check it against the source

From a jb2hubs session cutting Bandage figures out of the hosted format 2
files on 2026-11-22: 77 cuts over eight minigraph rGFA graphs, each checked
against its source GFA.

## What is true

- **An anchored cut holds what attaches under the window.** The writer
  files an off-reference component under the reference interval from the
  first to the last reference node it links to (`src/anchor.rs`), and a
  reference node under its own coordinate. A bubble of `.bubbles.bed.gz`
  that crosses the window's edge therefore has members the cut lacks: 17 at
  CFHR, 107 at KIR and 203 at MHC on HPRC. The jb2hubs session classified
  every missed member at the six HPRC windows that had any, 337 in all:
  each is a reference node outside the window or in a component attached
  only outside it. So this is the design and not a fault.
- **A figure that wants whole bubbles widens the window** until no bubble of
  the bubble file crosses it, then cuts.
- **On the contig layout a hop count does not close a cut.** Most of the 77
  closed at 2 hops; Arabidopsis RPP5 took 8 after widening and rice Pup1 46,
  and without widening Pup1 had not closed at 60. The bubble file's member
  ids are the test that a cut is whole, as `rgfaCut.ts`'s own comment says.
- **Nothing here checks a cut against its source.** `scripts/parity.sh`
  checks index rows, `src/rgfaCut.test.ts` fixtures, and the window oracle
  walk files. The jb2hubs check streams the source rGFA and tests each S
  line's LN, SN, SO and SR, rank-0 cover of the window, links both ways,
  dangling links and bubble members; it fails on a dropped S line, a
  dropped L line and an SO shifted by 1. A copy is in
  `~/src/walks8-evidence/sessions-20261122/jb2hubs-cut-validator/`.

## What to do

- State the first three points in graph-walks' README under "Segment
  indexes".
- Take the check into graph-walks' tests or release check, with its planted
  faults, on the fixtures and a few hosted windows.
- Consider a `closed` flag or the unread frontier in rgfaCut's result, so a
  caller need not cut twice to learn a contig cut stopped short.
