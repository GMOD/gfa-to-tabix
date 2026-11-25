---
name: fold-from-runs
description: graph-walks should read a window's walks as runs (a walk row's route choices, an abridged piece's blocks row) and hand graph-fold runs, so a folded every-haplotype window is built without minting steps or placeholders. At HLA class II the rows give every departure in about 1.2 s, where expanding and folding takes 28 s. It replaces the cut-time floorBp idea.
metadata:
  repo: graph-walks
---

# A fold read from runs

## Why

On 25 November, three Fable reviews of the HLA placeholder problem (`docs/issues-log.md`, 2026-11-25) found:

- The steps come from how graph-walks builds a cut, not from the file. A walk row is a start plus route choices. An abridged piece's blocks row is a chain of reference stretches with the runs between them, each with its own bp and the reference it skips.
- graph-fold reads steps back as runs and detours by own length and reference replaced (its README, "The rule"). It names an off-reference node by site and bp (`fold.ts`, around line 751), so it needs no node identity.

## What to build

- A graph-walks call that returns a window's walks as runs, without steps: leave, rejoin, own bp, inverted bp, and whether a run is loaded.
- A runs input to graph-fold.
- Adoption in bandage-core, so a folded every-haplotype window uses this path.

## Measured so far (scripts, not this design)

| Window | Rows read | Time | Departures left at a 1 kb floor |
|---|---|---|---|
| HLA 90 kb | tiles and blocks | 0.18-0.21 s | |
| HLA 90 kb | plus detail units | 1.1-1.2 s | 2,349 |
| KIR 90 kb | | | 162 |
| LPA 130 kb | | | 275 |

- Expanding and folding the same HLA window takes 28 s today.
- Scripts and outputs are on ada: `~/work/scratch/need-review-20261125/rowfold.mjs` and `~/work/agents/routes-review-4ac9/` (`classes.mjs`, `hla.txt`).

## Must hold

- The fold from runs equals the fold of the fully expanded cut on HLA class II, KIR, LPA and the worst GRCh38 tiles (chr9:38.8-39.9 Mb, chr2:91.4-91.6 Mb). Prove it against the VCF too.
- A broken-reader mutant (a run dropped, a strand flipped) fails that equality.
- Check piece joins, departure records between pieces, holes and contained edges explicitly.
- graph-fold's unchecked merge of equal-length alleles (`fold-leftovers.md`) stays as it is; do not widen it.

## Not this

- No format change, no writer change, no new hosted file.
- A coarse per-tile unit would hold the blocks rows filtered, saving about 1 MB of fetch at HLA. Reopen it only if this route leaves a measured residual, and then as a side file derived from the hosted bytes.
