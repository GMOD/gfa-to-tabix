---
name: lane-aligner-leftover-stretches
description: The lane aligner keeps one in-order chain per pair of walks, so in a collapsed copy-number array a stretch both walks step on the same nodes can get no ribbon; a prototype that also aligns each leftover stretch reports them, measured against minimap2 and the assemblies' bases, and waits on pictures and on the aligner's move into graph-walks.
metadata:
  repo: graph-walks
---

# Lanes drop shared stretches that lie off the main chain

Measured 2026-11-22 on the plugin at 10.4.3 and the hosted HPRC format 8
walk file, with the eight haplotypes of `demos/hprc_multiway`. Scripts and
tables are on ada in `~/work/synteny-extract-1122/`.

## What is true today

- **What the lanes report is right.** Every base a lane record calls a match
  is the same letter in the two assemblies' FASTAs, between two haplotypes
  and against hg38, on five chr1 windows (`pairs_check.tsv`). Against GRCh38
  the records agree base for base with the PAF `gfa_to_pairwise_paf.py` writes
  from the GFA, over 40 windows (`parity.jsonl`).
- **Outside repeats nothing is missing.** At CFH and two plain windows the
  lanes report every base that minimap2 matches and the graph holds on one
  node.
- **In a collapsed array a shared stretch can get no ribbon.** At amylase,
  about a sixth of the bases minimap2 matches between two haplotypes are
  stepped by both walks on the same node, and at least one of the two has no
  ribbon at all (`attribute2.tsv`, `same_base_no_ribbon`). `walkLanes.ts`
  takes the heaviest in-order chain of shared nodes, in one direction, and
  whatever lies off it shows as an insertion beside a deletion.
- **The rest of the gap to minimap2 is not the reader's.** The same table
  splits it: the other walk steps the node at another copy, the other walk
  never steps the node (the graph keeps identical bases on separate nodes),
  or the base fell outside the cut. `node_not_stepped` is about a third of
  minimap2's matches against GRCh38 at amylase and an eighth at the 1q21
  duplication. No reader of this graph can show those.

## The prototype

`leftover.mjs` keeps the main chain, then aligns each stretch of either walk
that no record covers to the whole of the other walk, in whichever direction
shares more. It cuts chains at gaps over 10 kb and drops a leftover piece
sharing under 1 kb.

- At amylase no base the two walks share on a node is left without a ribbon.
- At the other windows it reports the same bases as today.
- Against the PAF from the GFA it is identical in 127 of 128 lane-windows,
  the 17q21.31 and FLNA/EMD inversions among them, where today's aligner is
  identical in 116 (`parity-proto.jsonl`).
- It needs no pair chaining: a stretch read the other way is a leftover
  aligned in reverse. Over the timed windows it spends less time in total
  than today's aligner, about twice as long on a plain window, since it tries
  both directions every time, and several times less where today's falls back
  to pair chaining (`time.jsonl`, `time-proto.jsonl`).
- Every check was shown to fail on a planted fault: records shifted one
  base, and insertions swapped with deletions.

## The pictures

Shot with the plugin's `scripts/shoot-figures.mjs` on a clone at v10.4.3
(`plugin/`, with three lanes figures added), eight lanes in a fixed order,
at amylase, CFH and FLNA/EMD: `shots/before`, `shots/after` (both aligners
replaced), `shots/pairs-only` and `shots/pairs-only-10k` (the aligner between
two haplotypes replaced, the one against the reference left as it is).

- **Before, at amylase,** the bands between lanes of one structure are blank
  across the array, though both lanes draw sequence there.
- **Replacing only the aligner between two haplotypes** fills those bands,
  and leaves every lane's place, range and header as they were. Where one
  stretch of a lane matches two stretches of its neighbour, one the other
  way round, a blue ribbon lies over a salmon one. A thin blue line runs from
  the edge of a lane's gap in two bands.
- **Replacing the aligner against the reference too is worse.** JBrowse fits
  each lane to its records against the reference, so four lanes shrink, lose
  the ribbons on their right flank, and take a "110 kb inversion" label where
  they said "94 kb deletion, 94 kb insertion".
- CFH is the same file in every variant, and FLNA/EMD the same to the eye.
- A floor of 10 kb in place of 1 kb changes neither the amylase picture nor
  the share of minimap2's matches reported.

## What is left

- The owner's call on the amylase picture, before any of it lands.
- Land it in graph-walks, for records between two haplotypes only, after the
  move of the aligner out of gbz-base (`handoffs/2026-11-21-ada-next.md`), so
  the plugin, BandageJS and the R readers get the same records.
- Skip the second direction where the walk shares little the other way, as
  today's `turnedBases` test does.
- Find what draws the thin blue line at a lane's gap, in the records or in
  JBrowse's display.
- Test a window with an inversion between two haplotypes against minimap2;
  none of the five windows had one.
- Run it on a pggb graph, where collapsed repeats are the rule.
- Say in the lanes' limits that identical sequence the graph keeps on
  separate nodes draws as an insertion beside a deletion.
