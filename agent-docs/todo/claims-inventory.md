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
- the read's own cap: `lead:`/`tail:` stubs and "sequence off the reference ... 1 kb", which state the cut's context. graph-fold 1.2.0 can draw them (`fold.ts` around lines 675 and 831), but a scan of 71 windows with plugin 10.12.0's own path found none, since its cut starts and ends each walk on the reference; only the unreleased contained runs read drew them, and graph-fold ccb66af removes them;
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

## Planned and reviewed, 27 November

- Plan (Fable planner) and its 67-row inventory: `~/src/walks8-evidence/sessions-20261127/claims-plan/` (`plan.md`, `inventory.jsonl`). A fresh Fable review accepted it with changes; its probes are on ada in `agents/claims-review/`.
- The review's corrections, checked in code:
  - "N folded away" is not sound: at cut ends the read's own lead and tail bp are absorbed into it (graph-fold `fold.ts` around 1015-1022 and 1104-1111, `variationOf` around 160-171), up to about 1 kb.
  - The "n of m" denominator counts the reference and leaves out departing haplotypes (`runs.ts:168`, `fold.ts:1357`).
  - Node depth and link passes count pieces under a key that says walks (bandage-core `threadFold.ts:386-392`).
  - "In place of" ignores link sides (`referenceSpan.ts:22-28`), so a `join:` node can print a span that nothing replaced.
  - The inversion call is a window vote (`fold.ts:666-669`).
- Both Fable reads recommend removing the plugin hover's graph-fold event lines (and with them every graph-fold sentence), shipping depth-as-haplotypes in the same release, and keeping `ThreadEvent` as data.
- Amended order:
  - a sweep over all three fold routes (contained runs, the website's cut fold, the plugin's cut-fold fallback), red on the released stack;
  - an owner page with BEFORE/AFTER pairs for the hover lines, `lead:`/`tail:` nodes, "folded away" and the website's shares;
  - one graph-fold major plus the core hover fixes;
  - VCF checks on printed strings;
  - shares;
  - mark checks from figure data;
  - host and structural-forms text;
  - gate wiring.
- In progress: the sweep, gfa-to-tabix branch `claims-sweep`.
