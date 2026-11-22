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
- **Nearly everywhere nothing the graph shares is left out.** `coverage.mjs`
  counts, from the walks alone, the bases of each walk on nodes the other
  also steps, and how many a record covers. A second Fable review swept
  every chromosome in 300 kb windows (`why-amylase/genome.windows.jsonl`):
  all but about a hundred of some 9,600 measured windows are at 100%, and
  about twenty are under 99%.
- **The low windows are where a walk steps a node twice.** Every window
  with such a walk is below 100%, and no window at 100% has one. Amylase is
  the ninth lowest, at about five sixths; SMN, TBC1D3, `chr14:19.2M` and
  `chr22:18.6M` are lower. 300 kb windows understate it: SMN and 8p23.1 are
  lower in wider ones.
- **At amylase four haplotypes walk a hairpin:** some 48 kb forward, a 16 kb
  loop, then the same 48 kb back in reverse. HG00128 walks a stretch twice
  forward.
- **Half the shortfall is the pair-chaining branch.** `lanePairAligner`
  sends a pair to gbz-base's pair chaining when it shares 100 bp each way on
  nodes stepped once; the loop is such a share. The chainer's `repeatSteps`
  then masks every step between the first and last visit of a twice-stepped
  node, which is both arms and the loop, so no reverse seed is left and one
  forward record of the flanks comes back (`why-amylase/trace.mjs`). Seven
  of the 35 fragment pairs at amylase take the branch, and the subsequence
  alone would have reported more for every one (`branch.mjs`). The two bands
  that are blank in `shots/before/lanes_amylase.png` are both such pairs.
  Across the genome the branch loses more ribbon than it gains.
- **The comment in `walkLanes.ts` is wrong** that counting singly visited
  nodes "misses no inversion it could draw": the chainer leaves out more
  than the nodes stepped twice. The same mask is why `anchorAligner` gives
  no record for HG00128's reversed 29 kb.
- **The rest is the single chain.** The subsequence keeps one in-order chain
  in one direction, so a stretch shared only the other way round, a return
  pass, or a stretch out of order gets no ribbon. With one ribbon a base,
  the return and second passes cannot be ribboned at all.

## The decision

- **Lanes between two haplotypes take the leftover aligner,** `leftover.mjs`:
  the heaviest in-order chain, then each stretch of
  either walk that no record covers, aligned to the whole of the other walk
  in whichever direction shares more. It replaces the subsequence, the pair
  chaining and the rule that switches between them.
  - On `coverage.mjs` it ribbons nearly every shared base at amylase and all
    of them elsewhere, and no pair gets less than today.
  - CFH draws as the identical file and FLNA/EMD the same to the eye
    (`shots/pairs-only-10k`).
  - Its floor is 1 kb. At amylase 10 kb draws the same picture, but the
    second review found seven pairs at GSTT1 that get less than today with
    10 kb and not with 1 kb.
  - The second review ran it at the low windows too: it brings TBC1D3 and
    SMN to the mid and high nineties (`why-amylase/variants.mjs`).
- **Lanes against the reference stay as they are.** With complete records
  JBrowse ends four lanes at their first reversed piece and drops the
  ribbons on their right flank (`shots/after`). The published PAF-fed lanes
  track does the same at amylase (`shots/pif`), so the fault is the
  display's: `todo/lanes-headers-and-fit-at-inversions.md`.
- Two smaller moves were not taken. Dropping pair chaining recovers half
  the shortfall at amylase and loses the FLNA/EMD inversion between lanes.
  Keeping the subsequence and adding the chainer's other-strand records
  never does worse than the subsequence and keeps FLNA/EMD, but stops at the
  same half at amylase and keeps gbz-base's chainer.

## Gates, before it lands

- Land after the aligner's move out of gbz-base into graph-walks, as its own
  change; the move itself stays a pure move.
- `coverage.mjs` as a test: no pair below today's aligner on any window,
  and it must fail with the leftover records dropped (it does:
  `DROP=leftover`).
- Explain or fix two things the review found: the stretch of HG00128's
  pairs still without a ribbon, and that the records depend on which walk is
  the query.
- Run haplotype pairs over the second review's sweep, at its lowest windows
  (`chr14:19.2M`, SMN, `chr22:18.6M`, TBC1D3, `chr16:28.5M`, `chr1:144.3M`)
  and wide windows at SMN and 8p23.1, and on a pggb graph. The 1q21 window
  first measured has no walk stepping a node twice, so it tested nothing. Stop if a collapsed array fans ribbons past reading,
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
