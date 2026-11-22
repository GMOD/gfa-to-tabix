---
name: lane-aligner-leftover-stretches
description: Decided 2026-11-22 after a Fable review: lanes between two haplotypes take an aligner that keeps the main chain and then aligns each leftover stretch, in place of the pair-chaining branch, which at amylase leaves bands blank between walks that step the same nodes; lanes against the reference stay as they are; the gates it must pass are listed.
metadata:
  repo: graph-walks
---

# Lanes between two haplotypes leave shared nodes without a ribbon

Measured 2026-11-22 on the plugin at 10.4.3 and the hosted HPRC format 8
walk file, with the eight haplotypes of `demos/hprc_multiway`, and reviewed
the same day by a Fable session that read the scripts and the pictures.
Everything is on ada in `~/work/synteny-extract-1122/`.

## What is true today

- **What the lanes report is right.** Every `=` run pairs the same node at
  the same offset in both walks, and where a FASTA was at hand (five of the
  eight haplotypes at amylase, seven at 1q21) the bases are the same letters
  (`pairs_check.tsv`). Against GRCh38 the records lie on the diagonals of the
  PAF `gfa_to_pairwise_paf.py` writes from the same GFA, over 320
  lane-windows (`parity.jsonl`); that checks the reader, not the sequence.
- **Away from amylase nothing the graph shares is left out.** At CFH, a 1q21
  duplication and two plain windows, every base on a node both walks step
  has a ribbon.
- **At amylase about a sixth of it has none.** `coverage.mjs` counts, from
  the walks alone, the bases of each walk on nodes the other also steps, and
  how many a record covers.
- **Half the shortfall is the pair-chaining branch.** `lanePairAligner`
  sends a pair that shares 100 bp each way to pair chaining, which leaves
  out every node a walk steps twice. Seven of the 35 fragment pairs at
  amylase take it, each comes back as one forward record, and the
  subsequence alone would have reported more for every one (`branch.mjs`).
  The two bands that are blank in `shots/before/lanes_amylase.png` are both
  such pairs. Why chaining returns no reverse record there is not known.
- **The rest is the single chain.** The subsequence keeps one in-order chain
  in one direction, so a second pass over a node, or a stretch read the
  other way, gets no ribbon.

## The decision

- **Lanes between two haplotypes take the leftover aligner,** `leftover.mjs`
  with one floor of 10 kb: the heaviest in-order chain, then each stretch of
  either walk that no record covers, aligned to the whole of the other walk
  in whichever direction shares more. It replaces the subsequence, the pair
  chaining and the rule that switches between them.
  - On `coverage.mjs` it ribbons nearly every shared base at amylase and all
    of them elsewhere, and no pair gets less than today.
  - CFH draws as the identical file and FLNA/EMD the same to the eye
    (`shots/pairs-only-10k`).
  - A floor of 1 kb in place of 10 kb changes neither picture nor share.
- **Lanes against the reference stay as they are.** With complete records
  JBrowse ends four lanes at their first reversed piece and drops the
  ribbons on their right flank (`shots/after`). The published PAF-fed lanes
  track does the same at amylase (`shots/pif`), so the fault is the
  display's: `todo/lanes-headers-and-fit-at-inversions.md`.
- Dropping pair chaining alone was the smaller move and was not taken: it
  recovers half the shortfall and loses the FLNA/EMD inversion between
  lanes.

## Gates, before it lands

- Land after the aligner's move out of gbz-base into graph-walks, as its own
  change; the move itself stays a pure move.
- `coverage.mjs` as a test: no pair below today's aligner on any window,
  and it must fail with the leftover records dropped (it does:
  `DROP=leftover`).
- Explain or fix two things the review found: the stretch of HG00128's
  pairs still without a ribbon, and that the records depend on which walk is
  the query.
- Run haplotype pairs at KIV-2, C4, 17q21.31, 8p23.1 and over a chr22 sweep,
  and on a pggb graph. Stop if a collapsed array fans ribbons past reading,
  or record counts grow out of proportion.
- Before and after pictures of amylase, KIV-2, C4 and FLNA/EMD, looked at.
  No lane may change its place, range or header, and no band may lose a
  ribbon.
- Time it in the real reader. In Node it is about twice as slow as today on
  a plain window, since it tries both directions every time; skip the second
  direction where little is shared the other way, as today's `turnedBases`
  test does.

## Known and accepted

- Where one walk steps a run of nodes twice, some shared bases carry two
  ribbons, about a twentieth of them at amylase by the review's count, and a
  blue one can lie over a salmon one. That is what the walks hold.
- The thin blue line in two bands of the amylase picture is, by the review's
  reading of the records and of `cutAtOpenings` in JBrowse's display, a
  reverse record cut where HG01960's lane opens its gap: 1,596 bp left of
  the gap draw as a hairline. It is data. The display was not run to
  confirm it.
- The minimap2 comparison (`attribute2.tsv`) ran on excised stretches,
  primaries only, for the pairs with a FASTA. Its percentages are not to be
  quoted; the graph-only counts are.
