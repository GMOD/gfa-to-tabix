---
name: cohort-overview-then-lanes
description: With 463 HPRC haplotypes the lanes cannot show a cohort (all lanes are refused at 1 Mb) and exact-walk grouping will not compress because SNPs make nearly every walk its own class. Proposal: walk rows stay as the all-haplotype overview, sectioned by own length across the window, and a section opens 8 of its haplotypes as lanes. Waits on timings of walk rows for all haplotypes and on class counts per window.
---

# Seeing diversity across hundreds of haplotypes

Raised by the owner on 2026-11-23 together with graph-track-lanes-button. Read-only investigation; nothing measured or built.

## What exists

- **Walk rows** draw every haplotype on one shared bp scale, reading runs rather than steps. This is the one thing the lanes cannot do, and the reason to keep walk rows small rather than retire them.
- **Lanes** have "Order lanes by structure" and a lane picker, no grouping or count.
- **Structural forms** (`WalkFormsAdapter`) group all haplotypes by changes over a window, but name an undecided form "ref" and misread chains inside an inversion (forms-track-truth-audit); a cut at the MHC takes 8 s.
- **Whole-file counts:** graph-walks `reader.counts` counts haplotypes per node and link; no reader calls it, so graph-track thickness is carriage among the loaded walks only.

## Proposal

- Section and sort walk rows by own length across the window in stated bins ("81-82 kb · 83 haplotypes"), with incomplete and reversed-carrying rows apart. Every bar is still one real haplotype, so nothing claims identity.
- A section header opens 8 of its haplotypes as lanes, titled "8 of 83".
- Alternative: one lane per structural form with a member count, after the forms audit.

## Numbers it waits on

- Walk rows for all 463 haplotypes at 10 kb, 100 kb, 1 Mb and 4 Mb in a browser: time, bytes, refusals.
- Per audit window: exact walk classes against length bins against forms.
- `formsCut` and `counts` timings.
