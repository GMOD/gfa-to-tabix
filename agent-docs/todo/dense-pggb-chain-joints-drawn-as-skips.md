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

## What to do

- **The merge fix** is bandage-core branch `fmmmtime`; a laptop session is
  proving it changes no engine request at ordinary windows before it lands.
  It is still wanted once the cut is right.
- **The reader first** (graph-walks, and the plugin's adapter): say whether
  the source vouches that the reference passes each node once. An rGFA
  index does; a walk file's header states it; a path-graph index alone
  cannot. For a source that cannot vouch, `anchoredCut` does not keep a link
  only because its stored feet lie either side of the window.
- **Then bandage-core:** a link is a skip, or carries a turn mark, when the
  source states the passes, or states there are none, or the cut holds the
  reference whole between its feet. Otherwise it is a plain link. Sources
  that vouch must come out byte-identical.
- An index header stating the count of revisited nodes would close what is
  left. That is a format 2 change and goes through the format review; it is
  not proposed here.
- Pictures before any of it lands: the nine dense windows, and
  Minigraph-Cactus windows with a deletion inside, one with a far foot
  outside, a spanning deletion, a nested pair and an inversion.
- `tableOrientation` ignores `nodes.reversed`, so a file that states it
  could give a node a `+` id and a `-` reference strand.
