---
name: claims-inventory
description: List every sentence and mark the fold and the graph readers can show, each with the condition in the data that makes it true and a checker that fails when it is not, run over a randomized genome-wide window sweep against the VCF. Anything without a provable condition is removed. Next after the fold-from-runs release.
metadata:
  repo: graph-fold
---

# A claims inventory for the readers

## Why

On 26 November the owner, after the final truth review of the fold from runs: "its very concerning in an existential way that readers have so much trouble with false labels. what hope do we have for 'correctness'". They agreed to this plan.

Nearly every false label found that week sat at a boundary of what the reader read:

- the window's edge: "walk starts inside the window" for 388 of 464 haplotypes at HLA class II;
- the read's own cap: `lead:`/`tail:` stubs and "sequence off the reference ... 1 kb", which state the cut's context. These are in released graph-fold 1.2.0 (`fold.ts` around lines 675 and 831), not only in the new runs path;
- a contig's end: "walk ends inside the window" where the haplotype carries on in another contig;
- placeholders and abridged pieces, in earlier rounds.

Inside the window, the drawings agree with the VCF (774 of 776 HLA carriers, 306 of 306 at the probe window). Claims have been found one picture at a time, by reviewers. The memory note "prove format invariants" names the cause: repeated corner cases mean no claim was stated.

## What to build

- **An inventory:** every sentence template and mark kind graph-fold and bandage-core can produce (events, branch labels, hover lines, key lines, length and share labels, stubs, arrowheads, refusal messages). For each one:
  - the condition in the walk data or the VCF that makes it true;
  - which hosts show it (plugin hover, key, jb2hubs, figure export), so dead text is known as dead.
- **One rule for boundaries:** a claim that depends on data the reader did not read says nothing. graph-walks' `edge` end kind is the first case.
- **A checker per claim,** run over a randomized genome-wide sample of windows (not the showcase loci), against the raw vg-deconstruct VCF and the walk data. Each checker must fail on a planted break.
- **Removal:** any claim without a provable condition, and any dead text, is removed rather than reworded.

## Order

After the fold-from-runs release (`fold-from-runs.md`). Plan it with one read-only Fable planner, review the plan with a fresh Fable, then implement with Opus.
