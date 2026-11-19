# Open problems

Each section is a problem measured but not yet decided, with the fix it
suggests. A fix that gets built gets an ADR in [adr/](adr/); this page holds
nothing decided.

## Regions where haplotypes leave the reference's order

- Every hard window measured lies where a stretch of reference doesn't match
  about the same stretch of each haplotype: segmental duplications (LCR22,
  chrY's Yp11 and Yq11), hypervariable loci (IGL), satellites and tandem
  arrays (pericentromeres, Yq12, CHM13's short arm), and pggb's collapsed
  repeats. Off them, the walk view loses nothing in 43-47 of 50 arm windows
  and 10 of 10 control windows; in segmental duplications it loses nothing in
  14-19 of 30, and on CHM13's short arm in 0 of 10
- Under 10 kb of reference there, a haplotype can carry 30-200 kb of its own
  sequence, jump to a paralog megabases away, or pass a merged repeat many
  times, so no file layout makes a complete view both small and faithful. The
  index draws too much there; graph-walks before its crossing fix drew too
  little, and after it draws 13,000-80,000 nodes in some LCR22A windows,
  taking 3-15 s
- Download size is not what limits it: walk-view windows there read 0.3-2 MB
  and index windows 2-3 MB on GRCh38. Layout and drawing time and
  readability are
- Suggested next steps, in order:
  1. **Fold long alleles:** draw an allele in full when it's short, and a
     long one as a labelled bar, its length and where it leaves and rejoins
     the reference, which expands on request. graph-walks' crossing cap,
     65,536 bp by default, is the first part; the plugin's expand-on-click,
     fetching the folded piece from walk files' chunks or detail records, is
     the second
  2. **Switch coordinates:** in a segmental duplication, offer the locus from
     a haplotype that carries it, through walk files built for that
     reference or `--layout contig`
  3. **Pair with an alignment view:** show the copies as a dot plot or
     synteny view, which JBrowse already draws, beside the graph

## Walk files in place of the index for path graphs

These measurements were taken on walk format 5 and graph-walks 4, whose
`skip` rows walk format 6 replaces with departure records
([ADR 0009](adr/0009-departure-records.md)).

- [ADR 0008](adr/0008-index-keeps-its-placement.md) keeps the index's
  placement and its role for path graphs. Its measurement, graph-walks' own
  cuts over 80 to 100 windows per graph, is the baseline here
  ([docs/placement/](placement/))
- On GRCh38's chr22, off segmental duplications, a graph track drawing from
  walk files loses nothing a user needs and reads about a third of the bytes
- The harness counts as lost every node of a kept haplotype that the index
  draws and the walk view doesn't, so its losses are an upper bound. With
  graph-walks 4b064ec, of the nodes it counts lost, the share the haplotype
  carries on a stretch before or after the window, which the index draws
  only because it files a whole
  component under one interval, is 49% on Minigraph-Cactus chr22, 5% on pggb
  chr22 and 12% on pggb chrY. At Minigraph-Cactus chr22 18.45 Mb the 3,061
  nodes are a 32 kb insertion before the window, and the haplotypes carry a
  deletion across it
- graph-walks 4.5.0 closes two gaps 4.4 had, in the reader alone:
  - **A detour spanning the window:** a kept haplotype that leaves the
    reference before the window and rejoins after it keeps the steps
    between, and the reader fetches the far side within its 4-chunk follow
    reach. A crossing over `crossingBp`, 65,536 bp off the reference by
    default, comes back as a skip carrying `offBp`, `offSteps` and `chunks`
  - **A deletion across the window:** a direct jump across it comes back as a
    skip, though `--walks` writes no skip row in a chunk where the path has a
    piece ([ADR 0006](adr/0006-walks-skip-rows.md))
  - With 8 haplotypes, lost allele nodes fall from 6,180 to 2,150 on
    Minigraph-Cactus chr22, 6,217 to 3,941 on pggb chr22 and 10,699 to 8,160
    on pggb chrY; windows that lose nothing stay at 85, 71, 72 and 59. Every
    window draws all its reference nodes, against 3, 1 and 7 that didn't on
    pggb chr22, pggb chrY and CHM13 with 4.4
- Four things still stand in the way:
  - **The viewer:** bandage-core draws a skip only for a haplotype with no
    walk in the cut, and draws every skip as a deletion, so a capped crossing
    and a jump beside a fragment don't show
    (`src/layout/walkRowRuns.ts:723-777`). The plugin also installs
    graph-walks 4.4 until its next release
  - **Haplotypes jumping between repeat copies:** see the next section
  - **Zoomed out:** the coarse tier, alleles and bubbles exist only for the
    index
  - **Carriers:** a walk-drawn graph colours no node by its samples, so the
    hosted `ecoli_pggb_carriage` track has no walk-file source
- Suggested next steps: release the plugin on graph-walks 4.5.0; draw skips
  beside a walk and capped crossings as folded bars in bandage-core; count
  only nodes a haplotype carries on the window in the harness, then rerun
  `docs/placement/scripts`

## Haplotypes jumping between repeat copies

Measured on walk format 5; format 6 records each jump as a departure with
its ends' chunks ([ADR 0009](adr/0009-departure-records.md)).

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

## Placement of steps on nodes the reference passes more than once

- [ADR 0009](adr/0009-departure-records.md) records every departure
  exactly, and on pggb what it records under [ADR 0001](adr/0001-step-placement.md)'s
  nearest-pass rule is mostly the rule: on chrY 97% of records have an end
  on a node the reference passes more than once, 87% carry 0 own bp, one
  haplotype has up to 2,065 records over one 64 kb window, and only 35.9%
  of pieces land within 10 kb of where Minigraph-Cactus places the same
  contig position (35.6% in Yp11 and Yq11); on chr22 a window can read
  73 MB of departure rows in the spike's format, and 32.9 MB in 2,491,246
  rows in the port's. Measured in [docs/departures/](departures/)
- No one publishes a rule for this: `odgi untangle` votes per segment with
  no continuity term and ties identical copies, vg deconstruct assigns
  alleles by a 10 kb context vote, and HPRC release 2 ships no projection
  of its pggb graphs, only the wfmash all-vs-1 alignments
- Those alignments are themselves ambiguous in repeats: 73.5% of chrY's
  lifted blocks overlap another block of the same contig, since wfmash maps
  every segment of an array to its best copy. `primary.py` chains each
  contig's blocks into one co-linear projection first
- Three placements were built on pggb chrY and chr22 and scored by
  agreement with Minigraph-Cactus's placement of the same contigs
  (`agree.py`, 10 kb), an independent projection:

| | nearest pass | alignment-guided, raw blocks | alignment-guided, primary projection |
|---|---|---|---|
| chrY pieces agreeing with MC, Yp11/Yq11 / elsewhere | 35.6% / 50.5% | 71.1% / 77.3% | 86.5% / 99.4% |
| chrY departures, rows | 572,051, 1,616,957 | 81,978, 146,299 | 35,911, 53,775 |
| chrY rows per 64 kb window, median / p95 / max | 114 / 24,018 / 173,312 | 58 / 391 / 23,650 | 91 / 265 / 1,937 |
| chr22 pieces agreeing with MC, 2.8-26.7 Mb / elsewhere | 38.1% / 88.7% | | 95.9% / 99.9% |
| chr22 departures, rows | 12,458,636, 36,505,261 | | 303,171, 722,740 |
| chr22 departure query bytes p95 / max | 6.2 MB / 73 MB | | 389 KB / 1.4 MB |
| chr22 file over format 5 | +32.6% | | +17.8% |

- The departure rows above are the spike's format, and its chrY maximum
  under the primary projection, 1,937, was an audit error: the spike's own
  file holds 19,933 rows in its densest window. The 2026-11-03 rebuild of
  the simplified format 6 gives, on chrY, 425,836 records in 1,224,800
  rows under nearest pass (p95 / max per window 18,037 / 104,479) and
  30,329 in 43,415 under the projection (265 / 18,562); on chr22,
  5,333,737 in 17,434,823 under nearest pass and 177,475 in 452,672 under
  the projection (1,070 / 71,905, at most 988 KB a departure read).
  [Results](departures/results/rebuild/README.md)
- Caveats from a review on 2026-11-01. Until these are fixed and the
  scores rerun, don't quote the agreement figures as the gap between the
  two placements:
  - The agreement rows count pieces. Nearest pass hops between copies and
    makes 922,159 scored pieces on chr22 to the projection's 253,591. By
    bp outside the repeats, ADR 0001's placement score is 93.53% for
    nearest pass and 93.22% for the projection
    (`chr22.adr0001-scores.txt`)
  - `agree.py` extrapolates an MC position forward only. That is wrong on
    reverse-strand contigs past 5 kb from an anchor, and it hits nearest
    pass's mid-chunk pieces more than the projection's
  - The "2.8-26.7 Mb" stratum is chrY's Yp11/Yq11 bounds reused on chr22,
    with a hole at 10-11 Mb, not chr22's repeats
  - The precision gain under ADR 0001's criteria is scored against the
    alignments that guided the projection. The chrY primary build scores
    61% bp placement against its own guide, likely because the scorer ran
    with a lookback of 1 chunk where the header's maxnode implies 16
  - `agree.py`'s departure lines count rows, not records.
    `walks-truth.py`'s "lost elsewhere" counts every strict miss, including
    bases in no piece
  - MC also picks one copy per contig in repeats, so agreeing with it there
    isn't proof that either placement is right. The UCSC hg38-to-hs1 chain,
    scored on the graph's CHM13 path, would be a more independent check

- Under ADR 0001's own criteria on chr22 (the raw lift as truth), the
  primary projection takes piece precision from 32.8% to 93.9% and pieces
  per pair from 17.9 to 1.05 outside the repeats, with strict recall
  98.9% to 97.9%; in LCR22A precision goes 22.5% to 98.0% and strict recall
  93.5% to 71.5%. The recall lost is sequence the raw alignments place at
  several copies, which nearest pass shows at every copy by hopping and
  the projection at one. Which a browser should show there is the open
  choice. The 95.9% agreement with MC is over the whole 2.8-26.7 Mb
  stratum, not LCR22A
- The projection places 45% of chr22's steps on reference nodes off the
  reference, as own sequence, where the contig's alignment does not cover
  them (the chr22 community holds sequence of other acrocentric
  chromosomes); an off step costs more to encode, hence +17.8%
- A chaining rule inside the writer (`--chain` in the spike: stay on one
  copy, pay a penalty per jump, place a step off R when keeping it would
  force a hop and back) is exact on the fixtures and did not finish chrY
  in two hours; it needs a formulation linear in passes before it can be
  compared
- Working plan, not a closed choice: show one copy, by alignment-guided
  placement as an optional `--alignments` input recorded in the header
  with the alignment's name and checksum, nearest pass as the fallback,
  and a viewer that says where a step is one of several copies, lists the
  reference's other passes and offers the graph view. Before adopting it,
  check that every path rebuilds from its rows under that placement; the
  chaining spike was checked, the alignment-guided one was not
- Showing every copy stays open: the HPRC pggb team may weigh in. ADR
  0009 holds one placement per file, so other copies could come later as a
  second file, under a header tag naming its rule
- The question is not pggb's alone. [Counted on 2026-11-08: in the
  CHM13-referenced HPRC v2.1 Minigraph-Cactus graph, CHM13 passes each of
  its 90,761,410 nodes exactly once, and the 11-07 format 7 build of it has
  `revisited:i:0` and 3.74 M departure lines; the figures below came from
  another file, likely CHM13 as a haplotype of the GRCh38-referenced graph,
  and are not reproduced.] In the genome-wide Minigraph-Cactus
  graph CHM13 passes 209,578 nodes more than once, and the format 6 file on
  CHM13 holds 5.5 M departure records in 42.7 M rows against the GRCh38
  file's 1.8 M in 2.1 M: 32.4 M of the rows are on chr9, where 2.2 M
  records, 96% with no own bp and 81% switching strand, hop between copies
  held 1 to 100 Mb apart, three quarters of them 10 to 100 Mb, so a 64 kb
  window between 38 and 80 Mb reads up to 1.7 M rows, 22 MB compressed,
  and graph-walks 5 refuses it, as it does a window at 13.5 Mb of chr14,
  where 4.2 M rows lie in one Mb. Measured in
  [results/minimal](departures/results/minimal/README.md#where-the-chm13-files-rows-are).
  Decided 2026-11-05: the hs1 files come from HPRC v2.1's
  CHM13-referenced graph, which HPRC publishes, and this file is not
  hosted ([results](departures/results/arbitration/README.md)). The hops
  are haplotypes alternating between the collapsed copies every few
  hundred bp, which a placement rule for repeats could still reduce for
  pggb, where no graph on the reference's own copies exists
- To ask the pggb authors: whether they would publish `odgi untangle`
  projections of release 2 against GRCh38 and CHM13; whether a
  chain-based single-copy projection is what they would endorse for a
  browser; and how they would want sequence shown that matches several
  copies
- **Unmeasured candidate: odgi position's path-Jaccard rule.** `odgi
  position --jaccard-context N` lifts a query step onto a reference that
  passes its node more than once by walking up to N bp (default 10,000)
  along the query and along each candidate pass, and taking the pass whose
  surrounding node set has the highest Jaccard overlap with the query's
  (`src/algorithms/path_jaccard.hpp` in the odgi checkout under
  ~/src/vendor). It needs only the graph, as nearest pass does, where the
  projection above needs an alignment input. Nobody here has measured it.
  Criteria, written before any measurement, for it to replace nearest
  pass as the writer's rule on pggb graphs: scored by `agree.py` with its
  caveats above fixed, its agreement with Minigraph-Cactus's placement on
  pggb chrY and chr22 must reach the alignment-guided projection's figures
  within 5 points in every stratum, with no stratum below nearest pass;
  its departure records on chr22 must fall by at least half from nearest
  pass's; every path must rebuild from its rows; and build time must stay
  within twice nearest pass's. Measure it as a third column of the spike
  only when someone asks for pggb walk tracks, per ADR 0011. This is a
  placement rule, so adopting it is a format change under the ADR's gate

### Placing nothing there instead, measured and rejected on 2026-11-06

The proposal to place a step only on a node its reference passes once,
which would have been walk format 8
([proposal](walks-container/reshape/proposal.md), with its data), was
measured on pggb chrY and reviewed four ways
([reviews](walks-container/reshape/reviews/)). It leaves MC rows
byte-identical, and on pggb it does not make the picture true:
- **The records spanning a repeat are still hops between copies.** The
  nodes a collapsed repeat's copies pass once are copy-specific variants,
  so at chrY:23.6 Mb 2,693 of 2,760 records join ends over 1 Mb apart.
  HG002#1 alone has 561 such records between 21.9 and 26.3 Mb, and a
  reader draws them as alternating 3.5 Mb losses and duplications. Format 7
  draws the same hops, plus rows the rule placed
- **Attach fetches double.** A 1 kb window costs a median 1,070 KB
  against format 7's 589 KB
- **Other costs:** the pass count is per reference sample, so a diploid
  reference or a node on two chromosomes loses its steps. Five chrY
  contigs disappear without a tally, and graph-walks re-places the
  unplaced steps at whichever copy's tile it read

Two fixes would make the picture true, and both add to format 7 rather
than replace it. Take one up only when someone asks for pggb walk tracks:
- **A table of collapsed runs per reference sequence, plus each record's
  own bp on reference nodes.** A viewer can then fold a hop between copies
  of one family into "present, copy unresolved" and draw the reference's
  copy structure ([biologist review](walks-container/reshape/reviews/biologist.md))
- **Placement from an alignment of each haplotype to the reference,**
  which agrees with MC 86.5–99.4% of the time. It needs the pass fields
  format 7 keeps

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

- **A node the reference passes once, walked inside another copy.** On
  pggb chrY a 1 bp node the reference passes once, at 9,394,014, is walked
  by seven of eight haplotypes inside the TSPY copy near 9,482,842. The
  file states the single pass, so a reader that follows it draws an
  88.8 kb skip there, in the graph and the rows alike
  ([the drawing check's rows](walks-container/pggbY/once-passed-node.tsv),
  on the file [pggbY](walks-container/pggbY/notes.md) builds). The graph
  holds no fact that picks the copy; a later tag could say that a
  once-passed node's place is borrowed where its neighbours lie elsewhere

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

## A path that crosses onto another reference sequence

```
W  R  0  chrA  0  30  >1>2>3
W  R  0  chrB  0  22  >5>6>7
W  T  1  c     0  30  >1>2>6>7
W  B  1  c     0  32  >1>2>6>3
```

- T steps from chrA's node 2 onto chrB's node 6 and stays there. It has a
  piece in each sequence's tiles and no departure record, since a record
  lies between two steps on one sequence
  ([departure](walks-format.md#departure)), and neither piece's row says
  that another follows on a different sequence
- A reader of chrA therefore sees T end at node 2, as a contig that ends
  there does. graph-walks 6.2 returns T's fragment with no departure, no
  gap and nothing trimmed, and the link from node 2 to node 6 comes back
  from a cut of neither sequence
- walks-format.md used to say a line with no later step and no record
  inside the drawn stretch ends there. It now says what a reader can
  know, that the line has no later step on that sequence, and that
  nothing in the sequence's units tells a line that ends from one that
  goes on elsewhere ([Reading a window](walks-format.md#reading-a-window)).
  The file is unchanged
- B crosses and comes back, so it has a record on chrA: 2 bp of its own
  between adjacent steps, with `ownTiles` `.`. The 2 bp are chrB's node 6,
  which the record can't say, and an attach fetch reads no tile for them
- In the hosted GRCh38 file, 49 of the 51,257 lines with walk rows have
  pieces on more than one sequence, crossing 1,454 times, every time
  between unplaced or unlocalized scaffolds and never onto a chromosome
  ([count](walks-container/writer/results/hosted.cross-sequence-grch38.txt),
  from `walks-container/writer/scripts/cross-sequence.py`).
  Minigraph-Cactus assigns each contig to one reference chromosome before
  it builds that chromosome's graph, so its graphs hold no path between
  chromosomes. A pggb community of several chromosomes, or any graph with
  a translocation, would
- No hosted file shows this on a chromosome, so by
  [ADR 0011](adr/0011-format-7-is-frozen.md) nothing changes now
- Suggested next step, once a graph with such paths is to be hosted: a tag
  on a piece's walk row giving the sequence, position and strand of the
  step before it or after it in its W line, where that step is on another
  sequence of the reference. Format 7 lets a reader ignore a tag it
  doesn't know ([Header](walks-format.md#header)), so the format number
  would stay; it is still an addition to the format, to be measured and
  decided under ADR 0011's rules

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

## Departure records and attach fetches on pggb

- Under walk format 7 ([ADR 0010](adr/0010-walks-unit-table.md)) a 1 kb
  window on HPRC's pggb chrY reads a median 70 KB of tiles and departure
  records, and 389 KB once graph-walks attaches the own steps departure
  records leave out (p90 1,358 KB); on MC chr22 the same is 29 and 30 KB
  ([evidence](walks-container/arbA/results/res4/))
- The attach fetches read whole tiles elsewhere on the chromosome, one per
  record whose leave piece lies outside the window. On pggb most come from
  haplotypes hopping between collapsed-repeat copies, so every container
  measured pays them
- The reader review estimated carrying a record's own steps inline when
  they are 4 kb or less at about 0.1 MB compressed on MC chr22, an
  estimate, not a build ([reader](walks-container/reviews/reader.md)); not
  measured on pggb
- Suggested next step: measure inline own steps under a size cap on pggb
  chrY against the attach fetches they replace

## pggb chrY in walk format 8

- HPRC release 2's pggb chrY was built in format 8 on 2026-11-12 for
  GRCh38 and CHM13 at the default options
  ([notes](walks-container/pggbY/notes.md), counts for
  [GRCh38](walks-container/pggbY/stats.GRCh38.json) and
  [CHM13](walks-container/pggbY/stats.CHM13.json)). All six file checkers
  and `walks-truth.py rebuild` pass on both files, and `spec8.py`, the
  reader written from the spec alone, disagrees nowhere
- The rules no hosted file exercises fire throughout: 81% and 95% of the
  reference's steps lie on nodes it passes more than once, and a walk
  row's `k` reaches 3,346 and 3,756 where the fixtures reach 7. No row
  needed a change
- **What a reader gets,** graph-walks 676a0dd over 1 kb windows
  ([four haplotypes on GRCh38](walks-container/pggbY/four.GRCh38.log),
  [on CHM13](walks-container/pggbY/four.CHM13.log), every haplotype on
  [GRCh38](walks-container/pggbY/win1.GRCh38.cuts.txt) and
  [CHM13](walks-container/pggbY/win.CHM13.cuts.txt)): off the satellites
  a cut of four haplotypes is a few range requests. GRCh38's densest
  tile is refused at the default budgets with every haplotype, and
  CHM13's Yq12 windows are refused even for four: the attach fetches or
  the departure read pass the reader's budgets
- **`blocks` units outgrow [ADR 0012](adr/0012-abridged-blocks.md)'s
  limits here,** which were set for the hosted graphs: 3.5% and 5.7% of
  the file, the largest 2.58 MB, and a unit can be several times its
  tile
- **An unloaded cut differs from the loaded one where a run off R holds
  a node the reference passes elsewhere.** At GRCh38 20.15 Mb a
  haplotype's 1 bp step inside a run is on a node passed 17 times; the
  loaded cut keeps that node and its links 95 kb away, the unloaded cut
  shows a 1 bp run. The page says a run can hold another tile's
  reference node ([blocks](walks-format.md#blocks)); it can't happen
  where `revisited` is 0
- graph-walks' equality harness, not its reader, read a `+` leave as the
  node's right end, which is wrong where the reference passes the node
  reversed ([revref.gfa](walks-container/pggbY/revref.gfa)). graph-walks
  cbca728 reads the strand from the tile's `ref` rows, and sets the
  difference above aside by name where `revisited` is above 0
- With both mended, ten links still differed over seven GRCh38 windows,
  at 11.56 and 20.08 Mb: each joined two reference nodes, only the loaded
  cut held it, and no fragment or departure of either cut walked it.
  That was graph-walks cbca728 on the file built before `hapBp`, and has
  not been run again
- **The cause, traced on the files gfa-to-tabix 5.0.0 built**
  ([outputs](walks-container/accept-5.0.0/)): a detail unit holds every
  moved piece of one W line in its tile, and a cut that expanded the walk
  linked each route of the unit, whichever of its pieces it built. A
  piece it stated as bp alone so gave it links between reference nodes
  that other walks' steps kept, and the cut that expands nothing held
  none of them. graph-walks 8e3d397 shows it on Minigraph-Cactus too: 6
  links in 1 of 1,000 windows of HPRC v2.1's CHM13 file, at chr1
  16.39 Mb ([probe](walks-container/accept-5.0.0/probe-why.ts)), none
  in 1,000 of its GRCh38 file, and 660 over 24 windows of pggb chrY on
  CHM13
- graph-walks 0350375 links the routes of
  the pieces a cut builds and no other. Both genome files then differ
  nowhere over the same 1,000 windows each, and pggb chrY in 4 links
  over 2 of its 24 windows
- Those 4 are the first difference above where no step shows it: a piece
  the cut builds takes a route through a node the reference passes
  elsewhere, on steps the cut trims off its fragment
  ([probe](walks-container/accept-5.0.0/probe-pggb.ts)). It can't happen
  where `revisited` is 0
- One pggb window differs otherwise, and is untraced: at CHM13 chrY
  28.84 Mb the loaded cut walks links with an end off the reference
  7,298 times and the unloaded one 7,294
- Suggested next step, when someone asks for pggb walk tracks: measure
  inline own steps under a size cap on the Yq12 windows, as
  [the section above](#departure-records-and-attach-fetches-on-pggb)
  proposes. A unit kind holding them is a later addition a format 8
  reader skips
- Suggested next step for the links: decide whether a cut should list
  the reference's links and those its returned steps walk, and no
  other. That would end the 4 above, and the links with an end off the
  reference that a cut walks nowhere, which the harness sets aside in
  both cuts. It would also drop links from cuts of tiles nothing is
  abridged in, so measure it on bandage-core's views first

## Alleles on two reference samples

- `alleles` drops the sample from a sequence's name, so GRCh38's and CHM13's
  `chr1` would share one, and `--reference` refuses a list naming two PanSN
  samples
- Suggested next step: keep the sample in the name when the graph's reference
  spans more than one, and check the allele track draws it

## Alleles that leave one sequence for another

- Since 8db395f an allele's walk stops only at the backbone of the sequence
  it entered from, so an allele whose only exit is onto another sequence
  gets no row. 7a505f0 had kept those exits because dropping them loses
  alleles minigraph graphs hold; before it, the row ran from the entry's
  coordinate to the exit's, though the two lie on different sequences
- How many alleles this drops on a minigraph rGFA is unmeasured
- Suggested next step: count them on HPRC's minigraph graph, and if they
  matter, write them as breakends once the allele track can draw one

## gfatools crashes

- gfatools 0.5-r296 segfaults on `tests/data/alleles.gfa` and on most tiny
  random rGFAs, so `build` writes no bubble file for them and says so
- Suggested next step: find whether a newer gfatools fixes it, and report it
  upstream if not

## An abridged row narrower than its piece

- An `abridged` row's `start end` is the span of the piece's first and
  last steps on R, and graph-walks keeps an abridged piece where that
  span overlaps the drawn stretch (`walkRows.ts` `abridgedSpan`). A piece
  that doubles back past either end is missed by a window over that part:
  over ref `>1>2>3`, 6 bp nodes, the piece `>9>8>2<1>3>7>8` has a walk row
  at 0-18 and, abridged, a row at 6-18, so a window over node 1 drops it
- The hosted files show it: 1,279 of 74,053 abridged rows on GRCh38 and
  469 of 65,396 on CHM13 miss part of their piece, a median of about
  13 kb, at most 63 kb. Each detail unit's `start end`, which the table
  lists, covers its pieces in every row, and is wider than the piece in
  the 3,312 and 3,194 rows whose unit holds several pieces of one line,
  by up to a tile. MC chr22 alone has none
  ([counts](walks-container/writer/results/hosted.abridged-span.txt),
  from `abridged-span.py`)
- Two blinded deciders, given these counts and
  [criteria written first](walks-container/writer/results/abridged-span-criteria.md),
  both ruled for a reader change alone: graph-walks keeps an abridged
  piece where its detail unit's extent overlaps the drawn stretch, and
  hands that extent to the consumer, since bandage-core places the block
  from its two end steps (`walkRowRuns.ts`), which lie off the window in
  exactly these cases. No row's meaning changes and no hosted file is
  rebuilt; "What a cut returns" would name the detail extent. Both
  rejected recording alone (it fails the misses criterion) and a writer
  change (no ADR 0011 trigger)
- **What a user sees,** checked by cutting the hosted GRCh38 file with
  graph-walks 6.2 at chr2:91,409,000-91,410,000, every haplotype kept:
  336 of 463 haplotypes come back with no fragment, only departure records
  spanning the window, such as NA18565#2's from 90.40 to 91.41 Mb, and
  expanding its abridged piece puts 98 of its steps in the window.
  bandage-core draws such a haplotype as a row of departures alone,
  "no step on GRCh38 across …" (`departureText`), which is false, and the
  plugin offers no expand on it. The plugin expands abridged walks itself
  when 64 or fewer haplotypes are named (`EXPAND_NAMED_MAX`), so the
  default view of four is not hit; the view of every haplotype is. The
  missed stretches total 297 kb of GRCh38 and 395 kb of CHM13, mostly by
  centromeres (chr2:91.41 Mb holds 843 of GRCh38's 1,279 pieces). A third
  blinded reviewer ruled to fix it now
- Two more blinded reviews traced abridged pieces from file to screen:
  the drop is one of several false statements the view makes about an
  unloaded piece, from a block where it has no step to sizes off by
  orders of magnitude. [ADR 0012](adr/0012-abridged-blocks.md) decides
  the fix, a `blocks` unit per abridged tile added to walk format 7, after
  two deciders split and a third cross-examined them; the failure cases,
  tests and order are in the [handoff](handoff/2026-11-11-abridged-pieces.md).
  The build, the hosted rebuild and the releases are still to come

## Walk files name no writer

- A walk file names its graph in `graph:Z:`, the hash the node and link
  index states, and counts the lines it leaves out in `leftout:i:`
  ([ADR 0015](adr/0015-walk-files-name-their-graph.md)). No host or viewer
  compares a walk file's `graph:Z:` with its index's yet, so a walk file
  beside an index of another graph is drawn without a word. A directory
  from another build is refused where its line 1 differs from the data's
  `#walks` line or its `bytes:i:` from the data's length
  ([The directory](walks-format.md#the-directory)); a reader that can't
  learn the length, behind a server that hides Content-Range, falls back
  on its `#unit` check of the first unit it reads
- Nor does it name its writer: no tool or version is in the file. That
  was left out on purpose: a version stamp changes every file's bytes at
  each writer release, even one that changes no row, so every hosted file
  would be uploaded again on a sync. A walk file's bytes depend only on
  the GFA and the options it was written with
- Suggested next step, once a consumer reads a walk file beside an index
  of the same graph: compare the two `graph:Z:` values and say so when
  they differ. A writer's name and version can still come later as tags,
  under the spec's rule for additions, if a need for them outweighs
  uploading every file again

## The index and walk files disagree on a node's strand

- On a plain GFA the index turns a node to read forward along the first
  path that places it (`place::flip`), and its rows don't say which nodes
  it turned; walk files keep the GFA's strands. The plugin draws the fine
  tier from one or the other, never both, so nothing shows it yet
- Suggested next step, before any reader draws walks over index nodes:
  either mark a turned node on its row, or have the reader orient by the
  walk file's `ref` rows

## The release binary is slower than a cargo build

- The Linux binary the README's quick start downloads is built for
  `x86_64-unknown-linux-musl`, static, with musl's allocator. On pggb
  chrY it indexes in 99-105 s, where the same code built with cargo
  against glibc takes 65-68 s on the same machine, and peaks 70 MB lower
  ([measured](placement/pggb-chrY-build.txt)). The paper's 1.7 minutes
  is the release binary's
- `--walks` sorts and encodes on every core, where musl's allocator
  contends more; it hasn't been timed on the release binary
- Suggested next step: time the release binary against a cargo build on
  `--walks` for MC chr22, then build the musl target with another
  allocator, such as mimalloc, and keep it only if it closes most of the
  gap on both

## Memory grows with where a reference line starts

- The writer allocates an entry per tile of each reference sequence from
  0 (`Chunks` in `src/walks.rs`), whether a line covers it or not, so a
  reference line starting near 2^46 aborts under a 4 GB memory cap at the
  default tile ([big-refstart-2e46.gfa](walks-container/dialect/big-refstart-2e46.gfa)),
  and one ending at 2^53 builds only with a tile large enough to keep
  the count below 2^32
  ([line-end-2e53.gfa](walks-container/dialect/line-end-2e53.gfa))
- No real assembly has such a coordinate; a W line's start is whatever
  its writer put there. The coordinates themselves are settled: 5.0.0
  refuses a line that starts or ends past 2^53, and a reference whose
  last tile does ([walks-format.md](walks-format.md#tiles-and-pieces),
  [line-end-past-2e53.gfa](walks-container/dialect/line-end-past-2e53.gfa)),
  where it used to write positions a reader holding numbers as doubles
  read wrong and panicked on a start near 2^63
- Suggested next step, if a graph with such a line turns up: hold entries
  only for tiles a reference line reaches

## No check recomputes placement where the reference passes a node twice

- A file with a step put on the other copy of a node the reference
  passes twice, and its detail, `abridged` and `blocks` rows all agreeing
  with that, passes all six file checkers
  ([review](walks-container/abridged/reviews.md#format-8-from-the-spec-alone)).
  The build's own check and the tests catch a writer that does it; a
  file checker can't without placing the step itself
- The page doesn't pin the rule tightly enough to place a step from it:
  what the nearest pass is predicted from for a step against the
  reference, and the order a stay evaluates its steps in
- It can't happen where `revisited` is 0, so not on a Minigraph-Cactus
  file, and no hosted walk file has a revisited node
- Suggested next step, when someone hosts a pggb walk file: state those
  two rules exactly, then recompute each such step's pass from the GFA
  in `walks-truth.py rebuild`. The page now calls the rule this writer's
  policy and what readers rely on the format
  ([the next section](#the-writers-policy-has-no-name-in-the-file)), so
  such a file is a format 8 file with another placement, not a broken
  one; the check would then be of gfa-to-tabix, not of the format

## The writer's policy has no name in the file

- walks-format.md made the placement rule part of format 8, though a
  reader takes every position from the rows and of the `#walks` line
  reads `format`, `tile` and `revisited` alone. It now lists what a
  reader relies on as the format, and calls pass choice, `stay`, the
  abridge budgets and the order of a tile's detail records this writer's
  policy ([What a reader relies on](walks-format.md#what-a-reader-relies-on),
  [ADR 0013](adr/0013-abridged-hapbp.md)). No byte changed
- Still mixed: claims7.md lists the format's invariants and this
  writer's choices in one table, and the file checkers fail a file for
  either, so a file from another placement would fail checks of the
  policy. The pyramid's bin sizes are stated as the format, though a
  reader selects departure units by extent
- A file doesn't say which policy wrote it: `stay`, `abridge` and
  `abridgebytes` are there, the placement rule's name isn't
- Suggested next step, when pggb placement work starts: name the policy
  in a `#walks` tag, split the claims table and the checkers' claims
  into format and policy, and rule on the bin sizes. A tag is an
  addition a reader ignores, so it can follow the paper's freeze

## Starts a name or a column states that are not starts

[ADR 0014](adr/0014-p-line-names.md) decided how a P line's name is read
([Path names](walks-format.md#path-names)). These are what it leaves.

- **vg's phase blocks.** For haplotypes from a VCF-phased GBWT, vg
  numbers a contig's phase blocks 0, 1, 2 and writes that counter in the
  fourth field of a P line's name and in a W line's start column, and the
  tool reads both as starts. Blocks whose stretches then overlap are
  refused, with a message that names the cause
  ([vg-vcf-phased-p.gfa](walks-container/dialect/vg-vcf-phased-p.gfa),
  [vg-vcf-phased-w.gfa](walks-container/dialect/vg-vcf-phased-w.gfa)). A block alone, or
  blocks that don't collide, are placed at their counter: `S1#0#chr1#2`
  of 70 bp is written from 2 where it lies at 50. The same field is a
  start for a haplotype clipped out of a Minigraph-Cactus GBZ, and no
  line says which it is
- **A 1-based range.** `name:start-end` is read where `end − start` is
  the line's bp, as `odgi extract` writes it. A region name cut 1-based
  and inclusive, as the 12 paths of odgi's test graph `DRB1-3123.gfa`
  are, stays in the name whole, from 0, so such a graph is drawn in its
  own coordinates and not its chromosome's
- **A cut that runs past its piece.** Beneath a `:a-b` a bracket's end
  is not read, so `X#0[100-114]:6-16` is `X#0` from 106 though the cut
  ends past the piece it names
  ([p-colon-past-bracket.gfa](walks-container/dialect/p-colon-past-bracket.gfa)). odgi can't
  write one; a hand-made name can
- **A W line's `*` start,** which GFA allows, is refused: it states no
  offset ([w-star-start.gfa](walks-container/dialect/w-star-start.gfa))
- **A P line with `;` jumps,** GFA 1.2's, is refused: no step after a
  jump has an offset
  ([p-jump-semicolon.gfa](walks-container/dialect/p-jump-semicolon.gfa))
- Suggested next step, when someone brings a VCF-phased graph: find what,
  if anything, in vg's graph tells a counted block from a clipped
  fragment, since its P and W lines don't. After the paper's freeze the
  reading can accept more, and can't re-mean what it reads today

## Inputs the writer accepts and shouldn't

- Segment names `01` and `002` are read as nodes 1 and 2, so a line
  stepping on `1` steps on `01`
  ([s-leading-zero.gfa](walks-container/dialect/s-leading-zero.gfa))
- A GFA with no paths is refused as `--refs R matches no path's sample;
  have: ` with nothing after it ([no-paths.gfa](walks-container/dialect/no-paths.gfa))
- The node and link index doesn't read a W line's end column, so it
  builds a graph `--walks` refuses for one
  ([w-end-wrong.gfa](walks-container/dialect/w-end-wrong.gfa))
- Suggested next step: refuse segment names with a leading zero, naming
  the line; say that the GFA has no paths; check a W line's end in the
  index. Each refuses a GFA accepted today and changes no file it still
  accepts

## One table per sequence

- A sequence's detail and blocks units are found only through its one
  table, so a reader opening a sequence reads every unit's entry, and
  splitting the table later is a new format
- [ADR 0011](adr/0011-format-7-is-frozen.md) measured a split of the
  detail units' entries into a table of their own, which would have cut
  the open of GRCh38's chr9 from 192 to 69 KiB
  ([measured](walks-container/reshape/report.md)), and declined it
- Known and accepted: nothing to do unless a consumer's open time on a
  genome file says otherwise
- **A unit kind with a unit per tile grows the table every reader
  fetches at open,** whether or not the reader knows the kind. With three
  such kinds added to a chr22 build, a links, a counts and a sites unit
  per tile, the table grew from 46,338 to 84,628 bytes
  ([the format study](walks-container/format-study/writeup.txt), its
  complete adjacency section). The additions rule allows a kind one unit
  to a sequence with an index of its own, and a file beside the walk
  file; nothing measures either

## Every link of a loaded node, and a bubble layer

- A walk-file cut lists the links its kept walks take and no other, so it
  cannot give a loaded node's complete adjacency, and no reader rule
  recovers it: in a test graph cut with every haplotype loaded, a node
  reads as a clean insertion bubble while the GFA holds five more links at
  loaded nodes, one no path walks, one only a left-out line walks, and
  three shown paths walk from pieces filed in another tile, the
  reference's own `2+>3+` among them, with no trace in the window ([g4.gfa](walks-container/freeze-review/g4/g4.gfa),
  [its cuts](walks-container/freeze-review/g4/cuts.txt))
- The node and link index holds every link of a path-visited node but is
  not built for whole-genome graphs
- So a bubble or chain layer that verifies superbubbles on the loaded
  subgraph needs a writer-built addition first: a tag on `nodes` rows, a
  `links` unit kind, or a side file. Each is legal under the additions
  rule and none changes a row. A site table built from the walks alone is
  exact today
- A unit kind in a table carries its sequence and integer `start end`, so a
  later unit about no sequence has to be a separate file

## A dropped 0 bp segment states a link the GFA lacks

- The writer drops steps on 0 bp segments, so a cut of a GFA with `1>2`
  and `2>3`, 2 of 0 bp, lists the link `1+>3+`, which the GFA lacks, and
  nothing in the file marks that steps were dropped
  ([zero.gfa](walks-container/freeze-review/zero/zero.gfa),
  [its cut](walks-container/freeze-review/zero/cut.txt))
- A header count of dropped steps is a legal later addition. Neither
  hosted chromosome set has such a segment

## GFA tags neither file keeps

- The writer reads `SN`, `SO`, `SR` and `LN` from S lines
  ([gfa.rs](../src/gfa.rs)) and keeps no other tag. It drops an S line's
  depth (`DP`, `RC`, `KC`, `FC`), colours and annotations, an L line's tags
  and overlap, a P or W line's tags, and the H lines. A walk file keeps a
  node's id, length and reference passes, and its bases with `--sequences`.
  The node and link index keeps a node's interval, rank and `SB` bits
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
- Suggested fix, a later addition under the additions rule that changes no
  row: a unit kind of per-node tag rows in each tile, keyed by node id and
  carrying the S line's tags as written; or a side file keyed by node id
  ([pairing](#pairing-a-side-file-with-a-walk-file) is unsettled). Link
  tags could go in the `links` unit kind that
  [complete adjacency](#every-link-of-a-loaded-node-and-a-bubble-layer)
  suggests. A tag on a `nodes` row would need a list aligned with the row's
  nodes. The index has a row per node, where a tag would sit naturally, but
  whether its readers ignore an unknown tag is not checked. Nothing has
  been measured on a graph that has such tags

## Pairing a side file with a walk file

- `graph:Z:` names the GFA's segments, not the walk file: two `--refs` of
  one GFA share it, and a side file naming pieces depends on `tile`,
  `stay` and the abridging budgets as well
- A side file can copy the whole `#walks` line it was built against, and
  must also name the reference sample: two `--refs` files of one GFA and
  options can state the same `#walks` line, which names no reference
  ([Header](walks-format.md#header)). A hash of the paths could come later
  as a tag
- **What a side file would pair by is not settled.** The page says the
  same walk file is the same bytes
  ([Header](walks-format.md#header)), and no rule says how a second file
  names those bytes. The rule a prototype wrote copies the directory's
  line 1, whose `bytes:i:` is the one field that told two files of the
  same segments and options apart, 676 against 643, and `bytes:i:`
  follows the compressor: the same rows compressed again would not pair,
  and other rows of the same length would
  ([the format study](walks-container/format-study/writeup.txt), its
  pairing section, and
  [the review of its text](walks-container/format-study/review-spec.txt)).
  A hash of the directory, which holds every table's offset and length,
  was proposed by two reviews and measured by none

## Two pggb costs no addition removes

- A satellite record's detail unit is fetched whole or not at all, and a
  departure record is filed in every bin of its cover, so a window inside
  a long record pays for it at every zoom. A paged detail kind or a coarser
  layer can bypass either; neither removes it

## A reader does not yet refuse a gapped table

- A table's entries tile the bytes from the end of the table before it to
  its own offset, so a table that leaves out a unit's entry leaves a gap a
  reader can tell, and a reader may refuse it
  ([What a reader relies on](walks-format.md#what-a-reader-relies-on)).
  graph-walks, at main 4b14ee3 before 7.0.0, does not check the tiling:
  it reads such a table as a sequence without that unit, so a window over
  the unit draws nothing there and says nothing. verify7 fails such a
  file ([entry-dropped](departures/scripts/broken/cases.tsv))
- Suggested next step: a graph-walks release whose table read refuses a
  gap or an overlap, with a test on entry-dropped's bytes

## A once-passed node in a file with revisited nodes

- The format promises that no route interior holds a node the reference
  passes once only of a file that states `revisited:i:0`
  ([What a reader relies on](walks-format.md#what-a-reader-relies-on),
  [ADR 0016](adr/0016-format-8-is-frozen.md)). Of a file with revisited
  nodes it promises nothing: a window's rows can lack a line that steps a
  once-passed reference node in it, and a reader cannot tell from the
  file whether they do
- gfa-to-tabix keeps the rule on every file it writes, pggb chrY among
  them
  ([whole-file runs](walks-container/accept-5.0.0/whole-file/README.md)),
  but the header names no writer, so a reader of a file with revisited
  nodes that says "N of M haplotypes step this node" of a once-passed
  node says it on the writer's word
- The rule is not plainly right there. pggb chrY's 1 bp node at
  9,394,014, which the reference passes once, is walked by seven of
  eight haplotypes inside the TSPY copy near 9,482,842
  ([Collapsed repeats in pggb graphs](#collapsed-repeats-in-pggb-graphs)).
  Kept on R, as this writer keeps it, each of those walks reads as an
  88.8 kb skip; filed off R with its neighbours, the node's own tile
  would lack the seven lines. No file states which the writer did for a
  given node, and no pggb file is hosted

## Links only left-out lines walk

- A line with no step on a node of the reference has no rows in that
  reference's file, so a link that only such lines walk is in no row, and
  no reading of the file recovers it. A wider or expanded cut finds the
  links that the file's own lines walk from pieces filed elsewhere, at a
  cost; it never finds these
- On a chr22 build of the hosted Minigraph-Cactus graph they are 32,347
  of 4,737,114 links, and at chr22:11,816,742-11,846,742 a cut with every
  piece expanded lacks 4,122 of them at nodes it loaded; a chr6 build has
  none; pggb chrY has 1,700,646
  ([the format study](walks-container/format-study/writeup.txt), its
  complete adjacency section, and
  [its records](walks-container/format-study/records.jsonl))
- No reader's view was shown to differ for them: 150 random 1 kb windows
  of chr22 hold none, and the one decomposition tried gives the same site
  intervals without them
  ([Every link of a loaded node, and a bubble layer](#every-link-of-a-loaded-node-and-a-bubble-layer))

## Counts off the reference, and whether left-out lines count

- From a window's rows a reader can say "N of M haplotypes step this
  node" of a reference node, in a file that states `revisited:i:0`. Of a
  node off the reference it can say "at least N" and no more: the node
  can be listed by a tile it did not read, megabases away, and no row
  names the tiles that list a node. On a chr22 build 2,972 nodes off the
  reference are listed by tiles over 1 Mb apart
  ([the format study](walks-container/format-study/writeup.txt))
- A stored count has no settled meaning yet. The prototype counted the
  haplotypes with a line in the file, so it left out the left-out lines,
  which visit 50,890 nodes of that build; whether any count differs with
  them counted was not computed, and a count without them is not the
  graph's

## M is the haplotypes the file holds

- `#haplotype` lists the haplotypes with rows in the file, not the
  graph's. pggb chrY's graph holds lines of 151 haplotypes, the
  reference's among them, and its GRCh38 file lists 136 beside the
  reference
  ([the list of its path lines](walks-container/format-study/pggbY.paths.tsv),
  from [the routes review](walks-container/format-study/review-routes.txt)).
  So the M a reader can state is the haplotypes the file holds, and "N of
  M haplotypes step this node" is of those
- Where the reference sample has several haplotypes, `#reference` names
  the sample and no header line lists its haplotypes, so M is not
  derivable from the header at all
  ([the review of the study's text](walks-container/format-study/review-spec.txt))

## Which haplotypes the left-out lines belong to

- `leftout:i:` counts the lines a file leaves out and names none of
  them. A reader cannot say which haplotypes have lines outside the file,
  nor whether a haplotype it lists is whole there

## A reference of one haplotype of a sample can't be written

- Format 8 admits a file whose reference is one haplotype of its
  `#reference` sample, the sample's other paths in walk rows
  ([Terms](walks-format.md#terms),
  [ADR 0017](adr/0017-format-8-tags-numbers-lines-and-names.md)), and
  graph-walks reads one. gfa-to-tabix can't write it: `--refs` takes
  samples and makes every path of each a reference sequence, and
  `--refs 'HG002#1'` is refused. The checks make their file by building
  the other haplotype under a stand-in sample and renaming it
  ([check-walks.sh](../scripts/check-walks.sh))
- This is writer support, not a format question. Suggested next step,
  when someone wants a diploid sample drawn against one of its own
  haplotypes: let `--refs` take `sample#haplotype`, with the file name
  and the `#reference` line still the sample's

## Checkers that hold a file to more, or less, than the format

- No checker holds a file to the page and nothing else. `claims7.py`
  and `spec8.py` fail files that break this writer's policy and no
  invariant (`costliest-not-first`, and for `claims7.py`
  `revisited-as-interior` and, where the `#walks` line states a budget
  above 0, `budget-bytes-over`, `budget-steps-over` and
  `budget-put-back`, though the budgets bind no row), and `verify7.py`
  holds a file with revisited
  nodes to the once-passed rule this writer keeps and the format does
  not promise there, where `spec8.py` passes it
  ([cases.tsv](departures/scripts/broken/cases.tsv),
  `other-sequence-as-interior-revisited`)
- Under `--seq`, `claims7.py` reads the fourth column of every row of
  the sequences it was not given, whatever kind of unit holds the row
  (`row_elsewhere`), so a later unit kind's row there whose fourth
  column were `ref` or `nodes` would count toward its `SQ:Z:` claim. The
  page now says a later kind takes no row kind word of its own, which
  keeps the two apart; the script still does not skip such a unit as the
  page says a reader does. Read from the code, not run
- On a file with no `tile:i:`, `claims7.py`, `audit7.py` and
  `walks-truth.py rebuild` end in a traceback, which `broken.sh` counts
  as passing the file; `verify7.py` and `spec8.py` fail it
  (`tile-missing`). On `tile:i:0` `claims7.py` and `spec8.py` end in one
  and `verify7.py` fails it (`tile-zero`), and on a name holding a
  carriage return `audit7.py` and `walks-truth.py rebuild` do, reading
  the line as two, where `verify7.py` and `spec8.py` fail it (`name-cr`)
- Of the sentences [ADR 0017](adr/0017-format-8-tags-numbers-lines-and-names.md)
  added, `spec8.py` checks the names, the one `#reference` line and the
  `bytes` tag. It does not check how a number is written, an empty
  field, the lines of a unit of a later kind, an empty departure bin or
  a coordinate above 2^53, and passes the planted files for each
  ([matrix.txt](walks-container/spec-sentences/matrix.txt)); `verify7.py`
  holds a file to them, and `claims7.py` to a piece's end
- `walks-truth.py rebuild` passes a file whose route interior holds a
  once-passed node, since the steps it rebuilds are the line's whatever
  their filing

## Concepts beyond GFA

- Walk format 8 asks its readers, and through them its users, to learn
  concepts a GFA doesn't have, and adding formats and concepts has a cost
  of its own: to users, to other implementers and to a paper that must
  explain them. Each concept falls in one of four classes:
  - **Restated GFA:** node ids, lengths, bases, each line's steps.
    `walks-truth.py rebuild` shows the lines come back step for step
  - **Derived from GFA and one reference, with no choice involved:**
    reference positions, `passes`, `revisited`, departures, `#hole`,
    `leftout`. Anyone can recompute them, but readers must learn what they
    mean
  - **Writer policy, bytes that follow a choice or budget of the
    writer:** where a step lies on a node the reference passes more than
    once (`stay`, the nearest pass), abridging and its budgets, the tile
    size, departure bins
  - **Packaging:** units, the directory, `#entry` tables, routes as runs
    shared by haplotypes. This is what lets a window take a few byte
    ranges where gfaidx takes hundreds ([comparison](comparison.md))
- The spec separates exact from chosen
  ([Exact and chosen](walks-format.md#exact-and-chosen)). No review has yet
  asked, of each policy and packaging concept, whether it earns its place
  against the simplest alternative, and whether readers should show it to
  users at all. gfaidx-viz, for one, shows paths, links and the reference,
  and none of departures, abridged blocks or placement choices
- Suggested next step: an inventory of every concept, each with its class,
  the measurement it rests on, the simplest alternative and whether users
  meet it, against a minimal design derived from the requirements alone.
  What it would drop or merge is a format change, decided under ADR 0011
  before the freeze

## The README doesn't say what gfa-to-tabix is

- A newcomer reading [README.md](../README.md) meets two outputs, two kinds
  of input, `build` and its track config, and `--walks` before learning
  what problem the tool solves. Its one schematic,
  [walks-tile.svg](figures/walks-tile.svg), shows how a walk file is laid
  out in tiles, which is packaging, not purpose, in more detail than a
  newcomer needs
- Suggested next step: say first, in a few sentences and one figure with
  concrete labels, that a pangenome graph is too big for a browser to load,
  and that gfa-to-tabix writes files a browser can fetch one region of from
  any web host. Use the fewest concepts that do it, taken from the
  inventory above, and move the tile schematic to
  [walks-format.md](walks-format.md)
