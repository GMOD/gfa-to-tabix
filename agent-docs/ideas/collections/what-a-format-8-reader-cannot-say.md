---
name: what-a-format-8-reader-cannot-say
description: Five things a reader of a format 8 walk file cannot say, each a limit of the frozen format with a later addition that would let it - steps dropped on 0 bp segments, links only left-out lines walk, haplotype counts off the reference, M against the graph's haplotypes, and which haplotypes the left-out lines belong to. ADR 0016 left each for later; none is shown to change a view on a hosted file.
metadata:
  repo: gfa-to-tabix
---

# What a format 8 reader cannot say

Each is a fact of the graph that no reading of a format 8 file recovers.
An addition under the page's rule
([Later additions](../../../docs/walks-format.md#later-additions)) could
state it without changing a row; ADR 0016 weighed the counts and links
ones and added nothing
([The candidates](../../../docs/adr/0016-format-8-is-frozen.md#the-candidates)).

## A dropped 0 bp segment states a link the GFA lacks

- The writer drops steps on 0 bp segments
  ([Reading the GFA](../../../docs/walks-writer.md#reading-the-gfa)), so a
  cut of a GFA with `1>2` and `2>3`, 2 of 0 bp, lists the link `1+>3+`,
  which the GFA lacks, and nothing in the file marks that steps were
  dropped ([zero.gfa](../../../docs/walks-container/freeze-review/zero/zero.gfa),
  [its cut](../../../docs/walks-container/freeze-review/zero/cut.txt))
- A header count of dropped steps is a legal later addition
- Neither hosted chromosome set has such a segment; ADR 0011 counted none
  among MC chr22's 3,122,495 segments or pggb chrY's 4,122,486
- Waits on a hosted graph with a 0 bp segment

## Links only left-out lines walk

- A line with no step on a node of the reference has no rows in that
  reference's file, so a link that only such lines walk is in no row, and
  no reading of the file recovers it. A wider or expanded cut finds the
  links that the file's own lines walk from pieces filed elsewhere, at a
  cost; it never finds these
- On a chr22 build of the hosted Minigraph-Cactus graph they are 32,347 of
  4,737,114 links, and at chr22:11,816,742-11,846,742 a cut with every
  piece expanded lacks 4,122 of them at nodes it loaded; a chr6 build has
  none; pggb chrY has 1,700,646
  ([the format study](../../../docs/walks-container/format-study/writeup.txt),
  its complete adjacency section, and
  [its records](../../../docs/walks-container/format-study/records.jsonl))
- No reader's view was shown to differ for them: 150 random 1 kb windows
  of chr22 hold none, and the one decomposition tried gives the same site
  intervals without them. A `links` unit would carry them
  (`../waiting-on-a-call/complete-adjacency-for-a-bubble-layer.md`)
- Waits on a view shown to differ for them

## Counts off the reference, and whether left-out lines count

- From a window's rows a reader can say "N of M haplotypes step this node"
  of a reference node, in a file that states `revisited:i:0`
  ([What a reader relies on](../../../docs/walks-format.md#what-a-reader-relies-on)).
  Of a node off the reference it can say "at least N" and no more: the
  node can be listed by a tile it did not read, megabases away, and no row
  names the tiles that list a node. On a chr22 build 2,972 nodes off the
  reference are listed by tiles over 1 Mb apart
  ([the format study](../../../docs/walks-container/format-study/writeup.txt))
- A stored count has no settled meaning yet. The prototype counted the
  haplotypes with a line in the file, so it left out the left-out lines,
  which visit 50,890 nodes of that build; whether any count differs with
  them counted was not computed, and a count without them is not the
  graph's
- ADR 0016's reviews on a `counts` unit or tag: later; reader only; later
- Waits on a call on what a stored count means

## M is the haplotypes the file holds

- `#haplotype` lists the haplotypes with rows in the file, not the
  graph's. pggb chrY's graph holds lines of 151 haplotypes, the
  reference's among them, and its GRCh38 file lists 136 beside the
  reference
  ([the list of its path lines](../../../docs/walks-container/format-study/pggbY.paths.tsv),
  from [the routes review](../../../docs/walks-container/format-study/review-routes.txt)).
  So the M a reader can state is the haplotypes the file holds, and "N of
  M haplotypes step this node" is of those; the format page says the count
  is of the lines the file holds
- Where the reference sample has several haplotypes, `#reference` names
  the sample and no header line lists its haplotypes, so M is not
  derivable from the header at all
  ([the review of the study's text](../../../docs/walks-container/format-study/review-spec.txt))
- Nothing proposed

## Which haplotypes the left-out lines belong to

- `leftout:i:` counts the lines a file leaves out and names none of them
  ([ADR 0015](../../../docs/adr/0015-walk-files-name-their-graph.md)). A
  reader cannot say which haplotypes have lines outside the file, nor
  whether a haplotype it lists is whole there
- Nothing proposed
