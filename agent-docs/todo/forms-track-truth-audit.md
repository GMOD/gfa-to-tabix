---
name: forms-track-truth-audit
description: The structural-forms track was outside the 23 November truth audit of hosted data. Two faults are known without it: structuralForms names "ref" a form with no decided site, and graph-walks 9.1.0 reads a chain wholly inside an inversion as walking the reference. A trial of reading orientation per contig made H-SMN all "ref", so it was dropped.
metadata:
  repo: graph-walks
---

# Audit the structural-forms track against the truth

The 23 November audit (`../handoffs/2026-11-23-hosted-audit.md`) shot the
graph track, walk rows and lanes, and not the forms track
(`WalkFormsAdapter`, graph-walks `structuralForms`).

Known faults:

- **"ref" for an undecided form.** `structuralForms` names "ref" a form that
  has no decided site in the window. When the haplotypes' merged site reaches
  past the window edge, every haplotype reads "ref", whatever it walks.
- **Inversion carriers read as the reference.** In a window wholly inside an
  inversion, graph-walks reads each chain on its own. A carrier's chain lies
  along GRCh38 the other way and has no flank, so it reads as walking the
  reference. Rows read the contig as a whole and show it as reversed, so the
  two views can disagree in one window.

A trial on graph-walks branch `export-orientation` read each contig the way
rows do. It fixed the inversion case and made H-SMN worse: all 378
haplotypes read "ref", where truth spans are 1.2-1.86 Mb against GRCh38's
1.0 Mb. The branch is unmerged. The forms diff on the audit windows is in the
evidence folder (`hostedaudit/`, under the rows-truth work).

To do:

- **Shoot the forms track** on the audit's 64 windows with
  `scripts-cap/shoot2.mjs`.
- **Judge its texts blind** against `truth/`, as the other views were judged.
- **Fix it so a form is named only from what its sites decide,** with
  "undecided" where none does. Do this before any change to orientation.
