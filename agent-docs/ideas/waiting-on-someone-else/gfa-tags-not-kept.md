---
name: gfa-tags-not-kept
description: Walk files and the node and link index keep no GFA tag beyond SN, SO, SR and LN, so depth, colours and annotations on S, L, P and W lines cannot be drawn, where a viewer of gfaidx's output can. A per-node tag unit kind or a side file could keep them; nothing is measured on a graph that has such tags.
metadata:
  repo: gfa-to-tabix
---

# GFA tags neither file keeps

- The writer reads `SN`, `SO`, `SR` and `LN` from S lines (`src/gfa.rs`)
  and keeps no other tag. It drops an S line's depth (`DP`, `RC`, `KC`,
  `FC`), colours and annotations, an L line's tags and overlap, a P or W
  line's tags, and the H lines. A walk file keeps a node's id, length and
  reference passes, and its bases with `--sequences`. The node and link
  index keeps a node's interval, rank and `SB` bits
- Paths are kept exactly: `walks-truth.py rebuild` rebuilds each kept line
  step for step. What is lost is metadata
- Neither hosted set loses anything: Minigraph-Cactus and pggb S lines
  carry no tags beyond rGFA's. Tags matter on assembly graphs (depth), on
  graphs coloured by their assembler, and on graphs annotated after
  building
- gfaidx returns S, L and P lines with their tags as written (gfaidx 2.3.2
  on a three-node GFA with `DP`, `CL`, `RC`, an L tag and a P tag, run on
  2026-11-18), and gfaidx-viz colours nodes by `DP`, `RC`, `FC` or `KC`. A
  viewer of gfaidx's output can draw these and a viewer of ours cannot
  ([comparison-details.md](../../../docs/comparison-details.md))

## Ways to keep them

Each is a later addition under the additions rule that changes no row
([Later additions](../../../docs/walks-format.md#later-additions)):

- a unit kind of per-node tag rows in each tile, keyed by node id and
  carrying the S line's tags as written. A kind with a unit per tile grows
  the table every reader fetches at open
  (`../waiting-on-a-call/complete-adjacency-for-a-bubble-layer.md` has the
  measurement)
- a side file keyed by node id, once a pairing rule exists
  (`../waiting-on-a-call/side-file-pairing-rule.md`)
- link tags in the `links` unit kind that complete adjacency suggests
- a tag on a `nodes` row, which would need a list aligned with the row's
  nodes
- the index has a row per node, where a tag would sit naturally, but
  whether its readers ignore an unknown tag is not checked

Nothing has been measured on a graph that has such tags.

## What it waits on

A graph that has such tags, or someone asking to draw them.
