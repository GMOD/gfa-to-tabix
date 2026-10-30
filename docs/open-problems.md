# Open problems

Each section is a problem measured but not yet decided, with the fix it
suggests. A fix that gets built gets an ADR in [adr/](adr/); this page holds
nothing decided.

## One placement engine

- The node and link index and the walk files each place a path graph's nodes
  on the reference, two ways. The walk files place a step at the nearest pass
  of a repeated node and keep short detours in their chunk
  ([ADR 0001](adr/0001-step-placement.md)); the index gives a repeated node
  one coordinate and widens its links
  ([collapsed repeats](#collapsed-repeats-in-pggb-graphs))
- Four reviews agreed the walk files' placement should be the only one, and
  that the index stays as it is for an rGFA, which has no paths
- They split on how to get there:
  - **Walks replace the index for path graphs:** the plugin draws a pggb or
    Minigraph-Cactus graph from its walk files, and the index serves rGFA
    only. Needs a zoomed-out walk tier first, since the coarse tier, alleles
    and bubbles exist only for the index
  - **The index adopts the walks' placement:** one node row per pass, in a
    format 3 that also renames the carrier tags. Needs graph-walks,
    bandage-core and the plugin to change, and every hosted index rebuilt
- On chr22, the plugin draws the same graph from format 2 walk files as from
  the index in 49 of 50 windows; the 50th, in 22q11, lacks 3,111 nodes off the
  reference ([gbz-comparison.md](gbz-comparison.md))

**Decision rule**

- Walks replace the index if a path graph's L lines that no path traverses
  are under 0.1%, and windows outside abridged chunks lose no node the index
  cut keeps
- Otherwise the index adopts the walks' placement
- `scripts/placement-crux.py` measures both: `edges` counts untraversed L
  lines in a GFA, and `windows` compares, window by window, the nodes and
  edges an index query keeps with those the walk chunks hold

**Measured, 2026-10-30**

`placement-crux.py` on HPRC's pggb chr22 and chrY and on HPRC v2.1's
Minigraph-Cactus chr22, each against its GRCh38 walk file, over 50 windows of
10 kb:

| | pggb chr22 | pggb chrY | Minigraph-Cactus chr22 |
|---|---|---|---|
| L lines no path traverses | 19 of 7,174,759 | 23 of 7,685,990 | 0 of 4,737,114 |
| windows whose chunks hold every node the index cut keeps | 33 | 0 | 43 |
| windows whose walk file holds every such node somewhere | 50 | 50 | 49 |

- Untraversed links fall far under the rule's 0.1% on all three graphs
- Nearly every index node a window's walk chunks lack, the walk file files in
  another chunk. On pggb that fits the collapsed repeats below, whose wide
  links pull far passes into a window, against the nearest pass the walk
  files keep; on Minigraph-Cactus chr22, 3,882 such nodes sit in the
  immunoglobulin lambda window at 22.8 Mb, which fits the paralog jumps
  [walks-format.md](walks-format.md#paralogs-and-collapsed-repeats)
  describes. This run checks neither cause
- The walk file holds nowhere only 6 of the index's nodes, all in that window:
  1 and 2 bp alleles on NA18960#2's 5.5 kb fragment
  `CM101570.1:20688610-20694142`, whose 783 nodes include none of GRCh38's.
  `--walks` leaves out a path that never touches the reference, and the index
  files the fragment only because its component links to GRCh38 through other
  haplotypes' nodes
- By the rule, walk files replace the index on both pggb graphs, and miss on
  Minigraph-Cactus chr22 by those 6 nodes, which no GRCh38-anchored file can
  place. The measurement gives the index no reason to adopt the walks'
  placement
- Before the plugin draws path graphs from walk files alone, the walk files
  need a zoomed-out tier, since the coarse tier, alleles and bubbles exist only
  for the index today

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
- `build` points a pggb graph's track and coarse tier at the anchored layout
  all the same. On a synthetic 5 Mb graph with 500 repeats, 12.8% of its link
  rows and 93% of the 50 bp tier's span over 1 Mb, and the contig layout has
  none. The hosted E. coli config switches by hand
- The fix waits on [one placement engine](#one-placement-engine): if walk
  files replace the index for path graphs, nothing reads these rows

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
- A component that hangs from repeated nodes only, such as a SNP between
  paralogs, has no pass to prefer, so it needs rows at every pass. Filed
  under one, it shows as a moved-component stub at the others
- `side()` in graph-walks' `anchoredCut` reads whatever coordinates a link
  row states, so it needs no change
- The plugin keys a segment by id (`uniqueId: segment.id`), so two passes in
  one window draw as one feature, and every reader keeps one coordinate per
  id, which collapses tandem copies in one window
- `fold` places nodes by rGFA tags, one `SO` per node, so the coarse tier
  stays on first passes unless its output changes shape
- A model of the fix on a 2 Mb synthetic graph cut a 10 kb window's link rows
  from 1,187 to 72, against 88 for the same graph without repeats

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

- The JBrowse plugin draws a moved component as faded dead-end nodes where it
  joins the reference ([ADR 0005](adr/0005-giant-components.md))
- A reader can't fetch the component with one more query, because its nodes
  sit on whichever haplotype contig placed each one, and pggb chrY's three
  giants spread over 823 contigs
- Expanding stubs needs the writer to place each moved component on one
  sequence, and a reader change in graph-walks
- The smallest writer change files the moved components' rows under a
  sibling sequence, such as `GRCh38#0#chrY~moved`, which a window query never
  names, as walk files file their detail records. A reader expands a stub by
  querying the same window there
- The stubs stay as they are: pggb chrY's three giants are satellite tangles
  no budget could draw, and `--max-component` already draws mid-size
  components whole

## Format 2's carrier tags

- The tool writes a link row's two carrier tags under one name, `SB:H:`, with
  values that aren't SAM `H` hex
  ([what the file holds](index-format.md#what-the-file-holds))
- Today's readers cope. graph-walks, the only one that parses `SB`, takes the
  two tags by column (`rgfaBed.ts` `parseGraphRow`), and bandage-core gets
  carriers as `SM:Z:` from graph-walks
- Renaming the target's tag within format 2 would break graph-walks, which
  rewrites only columns that start `SB:H:`, so the far ends would lose their
  carriers
- A list of assembly numbers, where shorter than the bitmask, saves 12% of
  node tag text and 7% of link tag text on pggb chrY's 151 assemblies, and
  nothing after gzip

**Candidate fix, with the next format change**

- Name the target's bits `TB`, type both `Z`, and write the shorter of the
  bitmask and a list. Measure the list again at HPRC's 470 assemblies first

## Walk files

- Given `--refs HG002`, the tool treats each of the sample's haplotypes as its
  own reference. It writes `ref` rows for HG002#2 and no walk for it in
  HG002#1's chunks. A node both haplotypes pass counts as passed twice, which
  turns off the rules for nodes passed once
- If the tool took `--refs HG002#1`, the file name would need a spelling
  without `#`, which starts a URL fragment. The plugin's `walkFileSample` reads
  the sample from the text after the file name's last dot, so `HG002.1` reads
  as sample `1`: the plugin has to read `#reference` from the header first
- pggb chrY's skip rows don't separate deletions from hops between repeat
  copies. Counting the jumps with an end on a node the reference passes more
  than once needs only the graph; scoring them against impg's alignments, as
  ADR 0001 scores placement, comes after
- [ADR 0004](adr/0004-abridged-detours.md)'s abridging hasn't been timed in
  the JBrowse plugin, nor counted on Minigraph-Cactus at 1.4's weighting. Its
  recall needs no rescoring: by construction it loses at most the 0.5% of
  pairs left with no kept piece
