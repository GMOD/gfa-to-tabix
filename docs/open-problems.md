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
- The harness counts as lost every node of a kept haplotype that the index
  draws and the walk view doesn't, so its losses are an upper bound. With
  graph-walks 4b064ec, of the nodes it counts lost, the share the haplotype
  carries on a stretch before
  or after the window, which the index draws only because it files a whole
  component under one interval, is 49% on Minigraph-Cactus chr22, 5% on pggb
  chr22 and 12% on pggb chrY. At Minigraph-Cactus chr22 18.45 Mb the 3,061
  nodes are a 32 kb insertion before the window, and the haplotypes carry a
  deletion across it
- Five things stand in the way:
  - **A detour spanning the window:** in a window inside a haplotype's
    replaced stretch, graph-walks draws nothing for the haplotype. `walkCut`'s
    `detourSpan` keeps only a run with a step on the window, and the cut
    never fetches the chunk holding the detour's far side. Such stretches
    hold 33% of the counted losses on Minigraph-Cactus chr22, 10% on pggb
    chr22 and 29% on pggb chrY
  - **A deletion across the window:** `--walks` writes no skip row in a chunk
    where the path has a piece (`walks.rs` `write_skips`,
    [ADR 0006](adr/0006-walks-skip-rows.md)), on the assumption that the
    reader draws the piece. The reader keeps only steps on the window and its
    context, so a deletion over 18,433,383-18,487,047 on Minigraph-Cactus
    chr22 shows nowhere, and a jump inside one piece never gets a skip row
  - **Haplotypes jumping between repeat copies:** see the next section
  - **Zoomed out:** the coarse tier, alleles and bubbles exist only for the
    index
  - **Carriers:** a walk-drawn graph colours no node by its samples, so the
    hosted `ecoli_pggb_carriage` track has no walk-file source
- graph-walks 4b064ec places a node at the reference's pass over the window.
  With it, no window leaves a reference node undrawn, against 3, 1 and 7
  windows on pggb chr22, pggb chrY and pggb chr22 on CHM13 with 4.4. The
  windows that lose nothing move by at most one per stratum: 85 and 71 of
  100, 71 of 80 and 59 of 100 on Minigraph-Cactus chr22, pggb chr22, pggb
  chrY and pggb chr22 on CHM13, against 85, 72, 71 and 59
  (`docs/placement/*-placement-fix*`). The plugin still installs graph-walks
  4.4, so hosted tracks keep the old placement until a release
- Suggested next steps: in graph-walks, draw a detour that spans the window
  and follow it to its far side; in `--walks`, write skip rows by the
  stretch a path jumps rather than by the chunks it has pieces in; count only
  nodes the haplotype carries on the window in the harness; then rerun
  `docs/placement/scripts`

## Haplotypes jumping between repeat copies

- On pggb, most of the nodes the harness counts lost lie outside every chunk
  the walk cut reads, and outside those its skip rows name: 86% on chr22 and
  71% on chrY. A haplotype's jump to a paralog filed them there. A row marking
  a crossing without reference steps would sit in the window's chunk and
  draw none of them
- A jump the other way stretches a cut: when a kept haplotype steps from the
  window to a distant copy and rejoins the reference there, `walkCut`
  stretches the drawn reference out to the rejoin. At CHM13 chr22 11.45 Mb,
  HG00133#1's jump to 11,279,936 pulls in 178 kb, and the window draws 32,731
  nodes against the index's 8,718
- graph-walks 4.4 already drew 12,735 nodes against the index's 6,079 at
  GRCh38 chr22 21.28 Mb. Its placement fix raises that to 22,953 and adds
  windows such as CHM13 11.45 Mb
- With every haplotype kept, the fix moves which windows exceed graph-walks'
  budget, from 7 to 6 on CHM13 chr22. Two are new, at 12.88 Mb and 19.11 Mb,
  and ask for 9.4 and 9.6 kb instead of 10
- pggb chrY's skip rows don't tell deletions from hops between copies
- Suggested next steps: count the jumps with an end on a node the reference
  passes more than once, which needs only the graph; measure a cap on how far
  a rejoin stretches the reference, on repeat and ordinary windows alike;
  then score jumps against impg's alignments, as ADR 0001 scores placement

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
- Anchored on CHM13, the same pggb chr22 files 2,383 node rows and about 5,150
  link rows under CHM13 0-51.3 Mb, so 92 of 100 windows read 30-42 MB: a
  median 0.9 s in control windows and 12.4 s on the short arm, against 0.58 MB
  a window on GRCh38. The build moved 4 components, one of 1,412,443 nodes
  over 0-51.3 Mb
- jbrowse-components' `build_ecoli_pangenome_graph.sh` copies a contig-layout
  file under the anchored name for the hosted E. coli pggb track
- Suggested next steps: trace which components the CHM13 rows belong to; have
  `build` point a graph's track at the contig layout when its reference
  passes a node more than once, and measure what the contig layout draws in
  LCR22 against the anchored one

**Ruled out**

- **File a wide link under its reference end only:** links fall from 2.84 to
  0.17 MB, but each cut gets a median 367 nodes with no link, so "every link
  with a node under the region" no longer holds
- **Fix the reader only:** the wide rows overlap the window, so every reader
  has to fetch them. A @gmod/tabix change that starts each chunk at the linear
  index ([tabix-js#158](https://github.com/GMOD/tabix-js/pull/158)) saves
  nothing on these files
- [ADR 0008](adr/0008-index-keeps-its-placement.md) rejects filing by pass, and
  [ADR 0005](adr/0005-giant-components.md) capping a link's interval

## Stubs for a component over `--max-component`

- The JBrowse plugin draws a moved component as faded dead-end nodes where it
  joins the reference ([ADR 0005](adr/0005-giant-components.md))
- A reader can't fetch the component with one more query, because its nodes
  sit on whichever haplotype contig placed each one, and pggb chrY's three
  giants spread over 823 contigs
- Expanding them buys little on the graphs measured: pggb chrY's three giants
  are satellite tangles no budget could draw, and `--max-component` already
  draws mid-size components whole
- Suggested next step, once a graph needs a moved component drawn: file the
  moved components' rows under a sibling sequence, such as
  `GRCh38#0#chrY~moved`, which a window query never names, as walk files file
  their detail records, so a reader expands a stub by querying the same
  window there

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
- Suggested next step: have graph-walks accept a target tag named `TB` beside
  `SB`, so a later format can rename it, type both `Z`, and write the shorter
  of the bitmask and a list, measured again at HPRC's 470 assemblies

## Walk files: references and abridging

- Given `--refs HG002`, the tool treats each of the sample's haplotypes as its
  own reference. It writes `ref` rows for HG002#2 and no walk for it in
  HG002#1's chunks. A node both haplotypes pass counts as passed twice, which
  turns off the rules for nodes passed once
- If the tool took `--refs HG002#1`, the file name would need a spelling
  without `#`, which starts a URL fragment. The plugin's `walkFileSample` reads
  the sample from the text after the file name's last dot, so `HG002.1` reads
  as sample `1`
- Suggested next step: have the plugin read `#reference` from a walk file's
  header, then have `--refs` take `HG002#1` and name the file `HG002.1`
- [ADR 0004](adr/0004-abridged-detours.md)'s abridging hasn't been timed in
  the JBrowse plugin, nor counted on Minigraph-Cactus at 1.4's weighting. Its
  recall needs no rescoring: by construction it loses at most the 0.5% of
  pairs left with no kept piece. Suggested next step: time one abridged pggb
  chr22 window in the plugin

## Alleles on two reference samples

- `alleles` drops the sample from a sequence's name, so GRCh38's and CHM13's
  `chr1` would share one, and `--reference` refuses a list naming two PanSN
  samples
- Suggested next step: keep the sample in the name when the graph's reference
  spans more than one, and check the allele track draws it

## gfatools crashes

- gfatools 0.5-r296 segfaults on `tests/data/alleles.gfa` and on most tiny
  random rGFAs, so `build` writes no bubble file for them and says so
- Suggested next step: find whether a newer gfatools fixes it, and report it
  upstream if not
