# Open problems

Each section is a problem measured but not yet decided, with the fix it
suggests. A fix that gets built gets an ADR in [adr/](adr/); this page holds
nothing decided.

## Walk files in place of the index for path graphs

- [ADR 0008](adr/0008-index-keeps-its-placement.md) keeps the index's
  placement and its role for path graphs. Its measurement, graph-walks' own
  cuts over 80 to 100 windows per graph, is the baseline here
  ([docs/placement/](placement/))
- On GRCh38's chr22, off segmental duplications, a graph track drawing from
  walk files loses nothing a user needs and reads about a third of the bytes
- Four things stand in the way:
  - **The reader drops alleles:** on Minigraph-Cactus chr22, 82% of the
    allele nodes the walk view loses in segmental duplications lie on the
    haplotype's own steps in chunks graph-walks already read
  - **pggb's paralog jumps:** on pggb, 80-86% of lost (node, haplotype) pairs
    lie outside the chunks the cut read and those its skip rows name, where a
    haplotype's jump to a paralog filed them. A row marking a crossing without
    reference steps would sit in the window's chunk and draw none of them
  - **Zoomed out:** the coarse tier, alleles and bubbles exist only for the
    index
  - **Carriers:** a walk-drawn graph colours no node by its samples, so the
    hosted `ecoli_pggb_carriage` track has no walk-file source
- Suggested next steps: find where graph-walks drops Minigraph-Cactus's
  alleles, land its fix for placing a node at the reference's earliest pass,
  and rerun `docs/placement/scripts` on both
- An earlier rule tested whether the walk file held the index's nodes anywhere
  in the file. Any node of a path that touches the reference passes that test,
  so its verdict, that walk files replace the index on both pggb graphs, no
  longer stands. `scripts/placement-crux.py` still counts untraversed links:
  19 of 7.2 M, 23 of 7.7 M and 0 of 4.7 M on pggb chr22, pggb chrY and
  Minigraph-Cactus chr22, near zero because pggb and `vg convert` derive links
  from paths

## Chromosome-wide rows in a CHM13-anchored pggb index

- pggb chr22 indexed on CHM13 files 2,383 node rows and about 5,150 link rows
  under CHM13 0-51.3 Mb, so 92 of 100 windows read 30-42 MB: a median 0.9 s in
  control windows and 12.4 s on the short arm
- The same graph on GRCh38 reads 0.58 MB a window
- Suggested next step: trace whether these rows belong to the 1.4 M-node
  component the tool moves, or to a smaller one whose first and last
  attachments span the chromosome; the second would make a cap on a
  component's span worth measuring

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
- On HPRC's real pggb chr22, 1.06% of the fine index's link rows span over
  1 Mb, 4.3% of the 50 bp coarse tier's and 9.8% of the 10 kb tier's, against
  93% of the 50 bp tier's on a synthetic 5 Mb graph. A 1 Mb window reads a mean
  1.2 MB from the 50 bp tier and 19 MB from the fine index; the tiers are
  heaviest at 10.5-13.6 Mb, at 4.3-5.8 MB a window
- The hosted E. coli config points its pggb track at the contig layout by hand
- Suggested next step: have `build` point a graph's track at the contig
  layout when its reference passes a node more than once, as that config
  does, and measure what the contig layout draws in LCR22 against the anchored
  one

**Ruled out**

- **File by pass:** one node row per pass in a format 3.
  [ADR 0008](adr/0008-index-keeps-its-placement.md) keeps the index's placement,
  and puts placement work into the walk files instead
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
