---
name: fold-from-runs
description: graph-walks should read a window's walks as runs (a walk row's route choices, an abridged piece's blocks row) and hand graph-fold runs, so a folded every-haplotype window is built without minting steps or placeholders. At HLA class II the rows list every departure in about 1.2 s, where expanding and folding takes 28 s (cut 11.3 s, load 9.2 s, fold 7.6 s); a fold from runs is not yet timed. It replaces the cut-time floorBp idea.
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

## Plan (read-only Fable planner, 25 November)

Read from the code; nothing in it has been run yet.

- **The prototypes list departures; they do not fold.** The 1.2 s at HLA is read and scan time, 1.0 s of it detail units a fold does not need; tiles and blocks alone take 0.2 s. No fold from runs is timed.
- **Equality is reachable except for two identity fields.** `members` (unread on a node by any host) and `variation.walks`, which counts walks distinct by node name: the expanded cut names each placeholder after its walk, so it overcounts; runs merge alleles of one length at a site, so they undercount. The runs fold writes "on at least N distinct walks". Refuse unless the header states `revisited:i:0`; pick the backbone as `threadFoldInput` does.
- **De-risk first, no library change.** Cut each window with limits off, read every walk back as a chain, rebuild nodes and tracks with real reference nodes and one synthetic node per off-reference run, fold both with graph-fold 1.2.0 at 50, 236, 1,000 and 10,000 bp with clustering, and diff all but the two fields. Record time and peak memory of today's path on the whole chr9 and chr2 windows, and check the ada file's bytes against the hosted one.
- **graph-walks 9.3.0** (`src/walkRuns.ts`): `WalkReader.runs`/`runsRegion` returning per-fragment chains of reference stretches (start, bp, against, offBefore, loaded), lead and tail bp, and `before`/`after` ends from departure records; `fragmentRuns(cut)` as the oracle; `runDepartures`. No detail unit is read. Sweep every fixture: `runs()` deep-equals `fragmentRuns(cut())`. `scripts/runs-equality.ts` beside `blocks-equality.ts`.
- **graph-fold 1.3.0**: freeze 1.2.0's `fold.ts` under `test/` as an oracle; move the core to range anchors (`{from, to, reversed, at}`); add `foldRuns` and `foldRunsProblems`. Both front ends share the core, so only the frozen oracle catches a core fault.
- **bandage-core 14.9.0**: `foldThreadRuns(runs, belowBp, opts)` beside an untouched `foldThreads`; `WalkRunsTables` mirrored in `src/gfa/`. Hosts then switch: plugin `threadFoldCut.ts` and `RgfaTabixAdapter/walkReader.ts`, jb2hubs `pangenomeWalkCut.ts`. `cut()` keeps every refusal for every other path.
- **Open ends** (graph-fold 1.4.0, core 14.10.0), a visible change of its own: a departure whose far end lies past the window (HG01109 and HG02055 at chr6:32,486,357, 2,363 bp for 88,983 bp per the VCF) draws a branch of its true own bp with `open: true` and `beyond`, labelled "continues past the window", where today it says "walk ends inside the window". Not for a departure that jumps the whole window, nor a record with `missingBp` above 0.
- **Visible changes needing BEFORE/AFTER pairs:** the "at least" hover wording; windows a host refuses today that would draw (HLA class II, chr2:91.4-91.6 Mb, chr9:38.8-39.9 Mb, one chr14:19.2-19.7 Mb and one chr4:49.15-49.28 Mb window); the open ends at the probe window chr6:32,481,280-32,530,432 and HLA.
- **Mutants:** a run dropped; a block's strand flipped; a block's offset from the previous block; the bp at a piece join lost or counted twice; a record between pieces ignored; stretches merged across a hole; a contained walk not split off the window; a loaded tail clipped to `context`; two walks' names swapped. Control: `loaded` inverted fails runs equality and passes fold equality.
- **VCF:** `/mnt/sdb/cdiesh/vcfcheck/vcf/hprc-v2.1-mc-grch38.raw.vcf.gz` on ada (path from `landing-review/scripts/vcfq.py`), checker `~/src/walks8-evidence/a36cf6aa/verify/vcfcheck/vcfcheck.ts`. Per record and phased haplotype: AT reference nodes lie in the walk's stretches with the token's strand, others in none, and own bp less reference span equals allele less REF length. Report, not fail, branches that join alleles of different AT, with the same count from runs and from the expanded cut.
- The hosted GRCh38 file has no `#hole` line, so holes are checked on fixtures (`hole.R`, `holetile.R`, `refhole.R`).

## Restaged after a Fable direction review (25 November)

The review (read-only, from the notes and code) kept the goal and the checks and changed the order and size. These rulings replace the plan above where they differ.

- **Profile before rewriting graph-fold.** A compact graph (real reference nodes plus one synthetic node per run) still holds about 8.4-8.8 M steps at HLA (20,882 reference nodes, a median of 20,883 steps per haplotype), so it removes cut and load time but not the 7.6 s fold. `foldWindow` parses and builds objects per step. Profile `foldGraph` 1.2.0 on the compact HLA graph the de-risk script builds; move the core to range anchors only if step count, not per-step overhead, is what costs.
- **First release set:** graph-walks' runs reader plus bandage-core `foldThreadRuns` on the existing `foldGraph`, with open ends in the same set. No host stops refusing HLA, KIR or LPA before open ends ships: today's HLA fold says "walk starts inside the window" for 388 of 464 haplotypes, and only HG01109 and HG02055 are confirmed against the VCF as departures from outside. Every start or end said to be inside the window is checked against the walk's own contig before that release.
- **Drop the distinct-walk count** from graph-fold's variation line rather than writing "at least": the expanded cut overcounts it and runs undercount it.
- **The pericentromeric tiles** (chr9:38.8-39.9 Mb, chr2:91.4-91.6 Mb, chr4:49.1-49.4 Mb, chr14:19.2-19.7 Mb) stay equality stress tests and honest refusals; nobody asked to draw them.
- **Measure the equal-length merge on the expanded cut** at HLA, KIR and LPA before folds from runs draw with shares, since runs carry no node identity to measure it later.
- **One relation, not a fourth reading.** State how the runs reader relates to graph-walks' `Departure` (`walkDepartures.ts`) and `WalkRun`, and gate them against each other or derive one from the other.

## De-risk result (25-26 November, ada `~/work/walks8-gates/agents/runs-derisk/`)

- **Equal.** graph-fold 1.2.0 folds the steps cut and a runs rebuild (real reference nodes, one synthetic node per run named by site and bp) to the same nodes, tracks, branches and walks in all 247 comparisons, outside `members` and `variation.walks`. Windows: HLA, KIR, LPA, the probe window, chr9 tiles 38,993,920 and 39,780,352, chr2 tiles 91,357,184 and 91,422,720 (the last one partly: V8 dies at ada's `vm.max_map_count` near 16-19 GB of heap). Both presets, host and expanded cuts, 50/236/1,000/10,000 bp, clustering on and off. One run's bp +1 and one stretch's strand flipped each failed every row. The ada file matches the hosted bytes.
- **The rewrite is needed.** The compact input still holds 8.19 M steps at HLA (against 9.33 M) because every walk steps every reference node, and folds in the same time (2.76 s against 2.59 s at 236 bp). Profile shares: the per-anchor loop 27%, `parseStep` and prefix sums 17%, GC 16%, building anchors 12%, `lengthOf` 9%, `whyUnfoldable` 7.5%, `absorb` (feeds `members` only) 6.6%, the distinct-walk join 6%. Nearly all scales with steps, most of them reference steps: range anchors are the fix.
- **Timings, browser preset.** HLA: host cut 10.0 s plus fold 5.7 s; expanded cut 5.6 s plus fold 2.9 s (expanding is cheaper than placeholders); runs readback 1.5 s plus fold 2.7 s. Whole chr2:91.4-91.6 Mb: 119.5 M steps, 199 s, 26 GB; whole chr9:38.8-39.9 Mb: 105.2 M steps, 226 s, 28 GB; the runs fold of each still takes about 60 s.
- **A fourth identity rule.** `fold.ts` line 842: a walk with no step on the reference makes each of its steps a branch node named after the input node. Runs would make one node of its bp. No window reached it; the runs front end needs a stated rule there, checked against the VCF.
- **`variation.walks`** counts fewer from runs, as predicted (HLA host 445 against 409), so dropping it stands.

## Libraries built (26 November), not released

- **graph-walks `walk-runs`** (`~/src/graph-walks-runs`, d805e79): `WalkReader.runs`/`runsRegion`, `fragmentRuns`, `runDepartures`, `END_KINDS` (`beyond`, `elsewhere`, `edge`, `ends`; `edge` means the file cannot tell whether the walk carries on, so nothing is claimed). Equal to `fragmentRuns(cut())` in 6,980 fixture cuts and 12 hosted cuts; ten mutants fail. HLA 1.0 s against a 7.7 s cut; KIR and LPA 0.1-0.15 s. `walkDepartures` and `runDepartures` share `chainCrossings`.
- **graph-fold `fold-runs`** (`~/src/graph-fold-runs`, 48ee1f3): frozen 1.2.0 oracle; `foldRuns`; range anchors; open ends behind `ends`; the distinct-walk count dropped; a walk with no reference step folds to one `off:<walk>:<bp>` node. Equal to the oracle on the six hosted windows at every threshold, outside those allowances. Fold at HLA 2.5 s to 0.6 s. Two Fable reviews applied. `pnpm prove`'s regenerated pictures (only the dropped count's text differs) are not committed.
- **Open ends at HLA, 236 bp:** "walk starts inside the window" 388 to 0, now three open branches (24 kb deletion, 189 haplotypes; 927-935 bp for 3.9 kb, 173; 86 kb deletion, 26). The probe window's 153 "walk ends inside the window" go to 0. HG01109 and HG02055 agree with the VCF record at 32,486,309 as an 86,048 bp jump plus 713 bp of sub-threshold skips. This is a visible change: BEFORE/AFTER pairs first.
- **Left out:** a haplotype whose departure spans the whole window has no fragment and drops out of the window's haplotype count without a word (graph-walks); departures landing inside the window are not drawn (README states it); 3 of 3,000 random tangled graphs fail `foldProblems` under 1.2.0 too.
