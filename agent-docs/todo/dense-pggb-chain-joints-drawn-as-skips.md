---
name: dense-pggb-chain-joints-drawn-as-skips
description: On a pggb graph the reference passes nodes more than once and the node index stores one place a node, so the reader brings into a window every link whose stored feet lie either side of it, and the drawing measures the reference's own later steps as 15 Mb deletions: a "dense" chrY window of 14,142 nodes is 114 nodes of its own and 14,028 from megabases away, drawn with hundreds of false skip loops. The fix starts in the reader.
metadata:
  repo: bandage-core
---

# Dense pggb windows: chain joints laid and drawn as deletions

Found 2026-11-22 on the HPRC release 2 pggb chrY graph, window
`chrY:17,123,157-17,133,157` (14,142 nodes), by an Opus agent and a Fable
review. Their text, the captured requests' location and the pictures are in
`~/src/walks8-evidence/sessions-20261122/takeover/` (`fmmm-time-findings.txt`,
`reviews/fmmm-review.txt`, `fmmm-time/`).

## What is true

- **Where the nodes are placed.** 13,529 nodes of the cut are placed on the
  reference; about 75 lie in the window, and the rest at 7.5–8.1 Mb and
  22.7–23.1 Mb. All have `+` ids.
- **Run merging stopped in 14.0.0.** 10,550 links that are the only link at
  both their ends join a node of one copy to a node of the other, spelled
  `+ -`. `mergeRuns` joins only an end to a start, so the engine is handed
  14,391 nodes where plugin 9.0.0 handed it 3,841, and takes 5.6 s where it
  took 1.2 s. Since a19a53b every reference-placed segment is a fixed
  forward seed; 9.0.0 oriented a segment by the first link naming it, which
  kept chains coherent by accident.
- **The loops are not short skips.** Of 703 skip routes, 536 are measured as
  skipping 1 kb or more, typically 15 Mb, because their two nodes are placed
  in different copies. 345 are the only link at both their sides, plain
  chain joints. The cut holds a median 0.6% of what each is said to skip.
- **They are laid long and drawn wrong.** Each route is sized from the
  thousands of nodes whose coordinates lie between its feet, so the routes
  are about half the engine's vertices; and with feet under 33 px apart
  each draws as a plain stroke keyed "short skip". 9.0.0 held the same
  routes and did not stroke them.
- At fit zoom no arrowhead shows. Each such link is marked a strand turn,
  so zoomed in every joint could carry a head; not pictured.

## A second review, against the GFA's own reference path

A Fable review the same day checked the cut against GRCh38's path in
`chrY.gfa` on ada (`~/work/walks8-gates/agents/loopseval/`; its text is
`reviews/loops-eval.txt` in the evidence folder).

- **The loops are the reference's own steps.** 672 of the 703 links drawn
  as skips are consecutive steps of the reference on a later pass through
  an inverted repeat. The index stores one place a node, its first pass, so
  a link the reference steps at 22.9 Mb is measured between first-pass
  places 15 Mb apart. Three are true skips, of 1, 2 and 5 bp. The turn mark
  has the same fault: the reference itself steps 11,320 of the 11,393
  links that carry one.
- **The window is 1% of its picture.** 12,390 of the cut's 14,453 links are
  there only because their stored feet lie either side of the window:
  `anchoredCut` in graph-walks `src/rgfaBed.ts` keeps a reference link that
  jumps the whole window, "as a deletion or inversion spanning it does".
  The window's own graph is one component of 114 nodes; the other 14,028
  nodes are 553 components with no node in the window. Four of the dense
  windows share 3,723 of this one's 3,840 engine nodes, which is why their
  pictures show the same ladders.
- **So the "dense" pggb chrY windows are mostly not those windows.** Their
  node counts, and the paper's "up to 17,570 nodes", count material from
  7.5–8.1 Mb and 22.6–23.6 Mb brought in by that rule.
- **A rule over the cut alone cannot fix it.** In the cut these links look
  like a Minigraph-Cactus deletion that spans the window. The first
  review's rule clears them here and also flattens a spanning deletion and
  one with a foot outside the window, and resizes nested ones (4 of the 31
  skips in the repo's fixtures).

## A second opinion, and the prototype of the first rule

Both of 2026-11-22; texts in the evidence folder as
`reviews/readerfix-review.txt` and `reviews/loops-prototype.txt`.

- **This is the open problem already written down.** `docs/open-problems.md`,
  "Collapsed repeats in pggb graphs", says the cut "draws the wrong graph"
  for this reason, and `gfa-to-tabix build` writes a plain GFA's index in the
  contig layout because of it. The paper's benchmark indexed chrY with the
  bare command, which writes the anchored layout.
- **There is a second way in.** Off-reference components are filed under
  the hull of their first-pass attachments (`widen` in `src/anchor.rs`), so
  they come back megabases from home and bring their reference neighbours.
  With only the straddling links dropped, the 17.12 Mb window still draws
  900 nodes, 114 its own, and the 23.75 Mb window 9,592, 40 its own.
- **A window on a later pass cannot get its reference from this index.** At
  21.92 Mb, 922 of the window's 1,075 reference steps are later passes and
  the query returns 153 of its reference nodes. 384 of chrY's 2,341 bins of
  10 kb with sequence are mostly later pass. Only passes in the index would
  cure it, which ADR 0008 rejected.
- **No walk-file vouch reaches an index cut:** the plugin cuts from the
  walk file whenever a track names one.
- **The first rule, prototyped** (bandage-core branch `loops-rule`, a skip
  only if the cut holds another way round): clears the loops and halves the
  layout time, and at `chr18:78.37 Mb` shrinks nested deletions until they
  no longer read as going around. Not taken.

## What to do

A laptop session is prototyping this on branches, with pictures.

- **graph-walks:** a flag that a source is a path graph whose stored places
  are first passes, in both layouts, with tag-anchored rGFA sources kept
  exact; and for such a source in the anchored layout a cut of the
  reference nodes placed in the window, the off-reference components
  attached to them, and the reference nodes one link beyond, with the rest
  counted as filed across and not drawn. rGFA cuts must be byte-identical.
- **bandage-core:** a link is a skip, or carries a turn mark, only when the
  source states the passes, or is not so flagged, or the cut holds the
  reference whole between its feet. Seeds and the fold do not use stored
  places of a flagged source's far nodes.
- **Pictures before any of it lands:** the nine dense windows and 21.92 Mb,
  a sparse pggb window, and Minigraph-Cactus windows with a deletion
  inside, a far foot outside, a spanning deletion, a nested pair and an
  inversion, which must not move.
- **Docs:** `docs/index-format.md` says only a haplotype shows as an
  inversion, that a later-pass window gets the node's links, and that one
  query returns the whole graph under a region; none holds on such a graph.
- **Also sized by stored places,** unlooked at: `skipped()` in gfa-to-tabix
  `src/fold.rs`, and bandage-core's `levelOfDetail.ts`, `foldVariants.ts`,
  `superbubbles.ts`, `bubblesFromGraph.ts`, `referenceSpan.ts` and
  `projectAlleles.ts`.
- **The merge fix,** bandage-core branch `fmmmtime`, waits to be measured
  again after this.
- An index header stating the count of revisited nodes, and passes in the
  index, are format changes. Neither is proposed; both belong in
  `docs/open-problems.md` with these numbers.
- `tableOrientation` ignores `nodes.reversed`, so a file that states it
  could give a node a `+` id and a `-` reference strand.
