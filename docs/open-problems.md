# Open problems

Each section is a problem measured but not yet decided, with the fix it
suggests. A fix that gets built gets an ADR in [adr/](adr/); this page holds
nothing decided.

## Collapsed repeats in pggb graphs

- `place.rs` gives a node the reference passes several times one coordinate,
  its first pass. `anchor.rs` then widens the node's links, and the components
  beside it, to cover every pass
- A 20 Mb graph with 20 haplotypes and repeats at pggb's density
  (`synthetic-gfa.py --repeats 2000 --copies 3`) has 15% of its link rows over
  1 Mb. Median over 50 windows of 10 kb:

| | without repeats | with repeats |
|---|---|---|
| node bytes read, @gmod/tabix | 0.12 MB | 1.49 MB |
| link bytes read, @gmod/tabix | 0.21 MB | 2.84 MB |
| node and link bytes read, htslib's `tabix` | 0.023 MB | 2.2 MB |
| nodes graph-walks' `anchoredCut` keeps | 71 | 3,808 |
| of those, over 100 kb outside the window | 0 | 3,285 |

- The cut also draws the wrong graph. A repeated node's first-pass coordinate
  makes an ordinary reference link look like a deletion spanning the window,
  and `anchoredCut` keeps every link that spans the window
- On HPRC's pggb chrY, `--max-component` caps a window's node rows but leaves
  link rows reaching 69,413. In that window 63,887 link rows join two
  reference nodes, and 15,367 of those join nodes over 1 Mb apart
- Minigraph-Cactus and rGFA graphs have no such nodes

**Candidate fix: file by pass**

- A node the reference passes several times gets one node row per pass, each
  stating that pass's coordinate
- A link the reference path takes files under the pass where it takes it, and
  each link row states its nodes' coordinates at that pass
- A link the reference never takes, such as a deletion or a jump between
  repeat copies, files under the span between the nearest passes of its two
  nodes
- A component attaches to the pass of each repeated node nearest its
  attachments on nodes the reference passes once, as the walk files' nearest
  pass does
- Every link files under the intervals of both its nodes
- Blocked on readers: graph-walks' `rgfaCut` keeps one segment per id,
  `anchoredCut`'s `side()` needs a link's pass coordinate, and `fold` needs one
  coordinate per node

**Ruled out**

- **File a wide link under its reference end only:** links fall from 2.84 to
  0.17 MB, but each cut gets a median 367 nodes with no link, so "every link
  with a node under the region" no longer holds
- **Cap a link's interval at, say, 1 Mb:** drops real deletions longer than the
  cap on rGFA and Minigraph-Cactus graphs
- **Fix the reader only:** the wide rows overlap the window, so every reader
  has to fetch them. A @gmod/tabix change that starts each chunk at the linear
  index ([tabix-js#158](https://github.com/GMOD/tabix-js/pull/158)) saves
  nothing on these files

## Stubs for a component over `--max-component`

- A graph track draws a moved component as dead-end nodes where it joins the
  reference ([ADR 0005](adr/0005-giant-components.md)).
  [graph-walks#1](https://github.com/GMOD/graph-walks/pull/1) tags those nodes
  and [bandage-core#2](https://github.com/GMOD/bandage-core/pull/2) fades them
- A reader can't fetch the component with one more query, because its nodes
  sit on whichever haplotype contig placed each one, and pggb chrY's three
  giants spread over 823 contigs
- Expanding stubs needs the writer to place each moved component on one
  sequence, and a reader change in graph-walks

## Walk files

- graph-walks 4.2 ignores `skip` rows ([ADR 0006](adr/0006-walks-skip-rows.md)),
  so a window inside a haplotype's deletion draws no crossing.
  [graph-walks#1](https://github.com/GMOD/graph-walks/pull/1) reads them and
  [bandage-core#2](https://github.com/GMOD/bandage-core/pull/2) draws each as a
  deletion row
- pggb chrY's skip rows don't separate deletions from hops between repeat
  copies. Scoring the jumps against impg's alignments, as ADR 0001 scores
  placement, would
- [ADR 0004](adr/0004-abridged-detours.md)'s abridging hasn't been rescored by
  `walks-truth.py`, which can lose at most the 0.5% of pairs left with no kept
  piece, nor timed in the JBrowse plugin, nor measured on Minigraph-Cactus at
  1.4's weighting

## bandage-fold places paths in file order

- `gfa-to-tabix` places a plain GFA's nodes walking reference paths first,
  then the rest in byte order of name. bandage-core's `bandage-fold` walks them
  in file order, so the two place an off-reference node on different paths
  when a GFA's paths aren't in name order
- `scripts/parity-fold.sh` passes because its pggb fixture lists paths in name
  order. [bandage-core#1](https://github.com/GMOD/bandage-core/pull/1) adopts
  the same rule
