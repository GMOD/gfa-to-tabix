---
name: lane-aligner-leftover-stretches
description: Decided 2026-11-22 after a Fable review: lanes between two haplotypes take an aligner that keeps the main chain and then aligns each leftover stretch, in place of the pair-chaining branch, which at amylase leaves bands blank between walks that step the same nodes; lanes against the reference stay as they are. Its gates were run the same day: it passes on Minigraph-Cactus windows and fails on pggb chrY at TSPY, and what it must fix first is listed.
metadata:
  repo: graph-walks
---

# Lanes between two haplotypes leave shared nodes without a ribbon

Measured 2026-11-22 on the plugin at 10.4.3 and the hosted HPRC format 8
walk file, with the eight haplotypes of `demos/hprc_multiway`, and reviewed
the same day by a Fable session that read the scripts and the pictures.
Everything is on ada in `~/work/synteny-extract-1122/`; the laptop's
`~/src/walks8-evidence/sessions-20261122/lanes/` has the scripts and
pictures, without `steps.jsonl` and the sweep's outputs.

## What is true today

- **What the lanes report is right.** Every `=` run pairs the same node at
  the same offset in both walks, and where a FASTA was at hand (five of the
  eight haplotypes at amylase, seven at 1q21) the bases are the same letters
  (`pairs_check.tsv`). Against GRCh38 the records lie on the diagonals of the
  PAF `gfa_to_pairwise_paf.py` writes from the same GFA, over 320
  lane-windows (`parity.jsonl`); that checks the reader, not the sequence.
- **Counted with eight haplotypes,** 26 of the sweep's windows have a walk
  that steps a node twice. The reference never does on this graph.
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

## Reviews, 2026-11-22: held for the owner

The owner asked whether this is the wrong thing to build. Three reviews
answered, two by Fable, one a fact-check; their text is in
`~/src/walks8-evidence/sessions-20261122/takeover/reviews/`.

- **Both Fable reviews say not to land the leftover aligner as specified.**
  Each gate failure below is a missing clause of a rule nobody wrote down:
  no fixed point, no tie rule, no scale rule, no rule for a node stepped
  many times. "No pair gets less than today" is a regression test and not
  an invariant.
- **What the graph determines** is same node, same offset: exact, and
  many-to-many where a walk steps a node more than once, empty where the
  same sequence sits on separate nodes. A one-to-one pairing exists only
  where every shared node is stepped once by each walk.
- **One review would keep ribbons between two haplotypes** under a stated
  invariant: sound, complete, symmetric, and above a stated pass count one
  band giving each walk's passes in place of per-copy ribbons. Where nodes
  are stepped once the maximal colinear runs give that with no chain
  search. Not built.
- **The other would stop them:** neither session's record shows the owner
  asking for ribbons between two haplotypes, and Figure 5 was blocked by
  them.
- **Both put ribbons against the reference first:**
  `todo/lanes-ribbons-against-reference.md`.
- Prior art reads the same way: `odgi untangle` reports a best match
  against a reference with a score and a copy count, and `halSynteny` takes
  the heaviest chain and repeats, as this prototype does.
- Until the owner rules, neither this change nor the aligner's move out of
  gbz-base into graph-walks should start.

## Gates, run 2026-11-22

A laptop session ran every gate on ada, in
`~/work/synteny-extract-1122/gates-1122/` (`gate*.jsonl`, `trace*.jsonl`,
`time*.jsonl`, `shots-1122/`). The prototype as written does not land: it
fails on a pggb graph, and two faults need fixing first.

- **Minigraph-Cactus windows pass.** At the sweep's six lowest windows and
  wide windows over SMN and 8p23.1, no pair gets less than today, and
  coverage goes from as low as a sixth to nearly all (`gate.windows.jsonl`).
  No base carries more than three ribbons.
- **The floor is 1 kb.** At GSTT1 (`chr22:23,950,000-24,050,000`) 10 kb
  leaves seven pairs below today, all HG01109 against another haplotype,
  each short a 2.2 kb stretch shared the other way round.
- **pggb chrY fails at TSPY** (`chrY:9,300,000-9,600,000`, five haplotypes of
  `~/work/gfaidx-compare/out/pggbY.GRCh38.walks.gz`). One walk steps a node
  over a thousand times. A base carries up to 19 ribbons, one pair gets 81
  records where today gives 1, and 337 fragment pairs get less than today,
  each by under 1 kb: the prototype cuts its main chain at 10 kb gaps and
  drops short pieces, where today keeps one sparse record. A plain chrY
  window is unchanged, and P1/DAZ loses one 334 bp inversion.
- **HG00128's bare stretch is the single leftover pass.** A leftover run is
  aligned once, in one direction, as one chain, so a second stretch in the
  same run that pairs the other way, or out of order, is never looked at.
  Repeating the passes until one adds no record closes it
  (`leftover-gates.mjs`, `rounds: 8`).
- **Records depend on which walk is the query** because gbz-base's LCS
  breaks a tie between equal chains by which walk it sweeps; six pairs at
  amylase and fourteen at the wide SMN window differ. Rounds narrow it and
  do not remove it.
- **Time** is back to today's once each fragment's handles, offsets and node
  sets are built once and not per pair. Skipping the second direction alone
  saves nothing. Timed in Node only.
- **Pictures** at amylase, SMN and TBC1D3: no lane changes place, range or
  header and no band loses a ribbon. Three blank bands at SMN fill in. At
  TBC1D3 a blue fan lies across a salmon one and no single ribbon can be
  followed.
- **`cutOptions()`** equals the browser preset, apart from the slot names
  in the zoom-in message.
- **`coverage.mjs` cannot fail on its first five windows:** with
  `DROP=leftover` it still counts no pair below today there, and only the
  percentage falls. It does fail at GSTT1, `chr22:18.6M`, TBC1D3, the wide
  SMN window and 8p23.1.

## What the change must do before it lands

- Land after the aligner's move out of gbz-base into graph-walks, as its own
  change; the move itself stays a pure move.
- Repeat the leftover passes until one adds no record, under a cap.
- Give the same records whichever lane is the query: a fixed order by walk
  name with records mirrored was worked out from the code and not built.
- Keep the 1 kb floor, and decide what happens below it: sub-1 kb
  inversions and main-chain pieces under 100 bp are lost against today on
  pggb.
- Bound what a collapsed array may fan out to, in ribbons on one base and
  records for one pair, so TSPY draws no worse than today. Refusing pggb
  is not the answer.
- Build each fragment's tables once, and skip the second direction where
  `turnedBases` shows it can share no more.
- Take the test's windows from those where `DROP=leftover` fails, and add a
  pggb window.
- Time it in a browser, and run the display at amylase to confirm what
  draws the thin blue line; neither was done.

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
