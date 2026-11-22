---
name: dense-pggb-chain-joints-drawn-as-skips
description: In a dense pggb window whose nodes are placed in two copies of the reference megabases apart, a link between the copies is measured as a deletion of 15 Mb, given a long route in the layout and stroked as a "short skip" loop, so hundreds of loops bury the structure; the same links stop the layout's run merging, which makes the engine four times slower. The merge fix is being prepared; the loops need their own rule and pictures.
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

## What to do

- **The merge fix** is bandage-core branch `fmmmtime`: `mergeRuns` joins
  across a link into either end of a node. It brings these windows to
  3.2–4.6 s drawn, against 8.4–10 s on 14.3.5 and 2.5–3.8 s on 9.0.0, and
  moves their drawings. A laptop session is proving it changes no engine
  request at ordinary windows before it lands.
- **The loops,** as a separate change with pictures: a route is half as
  long as the shortest other path between its feet in the cut, and a link
  with no such path is laid as a plain link. Here that leaves 29 routes.
  It changes a deletion whose far foot lies outside the window, and
  overlapping deletions, at Minigraph-Cactus windows too, so those need
  before and after pictures.
- `tableOrientation` ignores `nodes.reversed`, so a file that states it
  could give a node a `+` id and a `-` reference strand.
