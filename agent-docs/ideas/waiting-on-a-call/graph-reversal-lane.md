---
name: graph-reversal-lane
description: A thin lane beside a reference node that some haplotypes walk backwards, as an end-state way to show reversal in the graph track. Built on bandage-core owner-asks-thin (0024e41) and rejected for now, because blind deciders read it as a second copy drawn at one walk, and BandageJS drew some of its heads the wrong way. The graph track ships with no mark on the node.
metadata:
  repo: bandage-core
---

# A reversal lane beside the reference

On 25 November the graph track dropped its backward arrowheads on reference nodes. The owner read them as "the reference goes backwards" and asked for the reversal to be shown as a separate path. Two blind Fable deciders compared three drawings: heads on the node, a thin lane beside it, and no mark. The criteria were written before the lane was drawn. The deciders split between the lane and no mark, and by the criteria's rule the smaller change, no mark, shipped.

- Criteria, letters and both verdicts: `~/src/walks8-evidence/sessions-20261122/hostedaudit/reviews/reversal-criteria-20261125.md`.
- Pictures: `hostedaudit/after-graph/pairs-v10/{both,thin-lane,no-lane}/`.
- Code: bandage-core `owner-asks` bdd05e2 (the lane whose width split the node's band) and `owner-asks-thin` 0024e41 (one fixed width); plugin `owner-asks-thin` bed01388.

## What a lane must do to win

From the deciders:

- Use a mark that cannot be read as sequence. A thin rainbow stroke is the track's mark for sequence one haplotype walks, so the lane read as a second copy at a count of 1, where 8 of 9 invert at SV-inv-10k-100k.
- State the count truly, without making the node's thickness key false. The split lane made it false.
- Draw one run per reversed stretch, not a piece per node. Pieces broke at every join and read as dashes at H-SMN.
- Draw every head on a stretch the same way. In BandageJS, 3 of 11 heads at R1M-06 and at least 2 at H-SMN pointed with the reference. The cause is not found.
- Draw no rings round short nodes, no stubs through junctions, and push no labels aside.

## Meanwhile

- Walk rows draw a reversed stretch with chevrons.
- The node hover names the haplotypes that walk it backwards.
- Threading a haplotype shows its route.
