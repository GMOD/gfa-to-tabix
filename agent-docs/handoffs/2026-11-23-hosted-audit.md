---
name: 2026-11-23-hosted-audit
description: The truth audit of what the released readers draw on the hosted HPRC graph is done, and it found false marks in all three views. This records where the evidence is, the verified faults grouped by cause, the plans, and the three fix branches being built. Nothing lands until the owner has seen before-and-after pictures.
---
# Hosted-data truth audit and its fixes

This continues the 22 November synthesis handoff's audit item.

## Evidence

The evidence is in `~/src/walks8-evidence/sessions-20261122/hostedaudit/`; the ada copy is `~/work/walks8-gates/agents/hostedaudit/`.

- **Windows:** `windows.tsv` holds 64 windows fixed before any picture was seen (seed 20261123): 30 random, 20 with a structural variant a drawn haplotype carries, and 14 hard loci.
- **Readers audited:** store plugin 10.6.0 with bandage-core 14.4.1 and graph-walks 9.1.0, and the public demo's jbrowse-components 349a1d14da.
- **Pictures:** `sheets2/` and `screen2/`. The first set, `sheets/`, has 118 blank panes: `page.screenshot({fullPage: true})` intermittently captures the view pane as white in headless Chrome. `scripts-cap/shoot2.mjs` captures with `captureBeyondViewport: false` and accepts a shot only when it has ink in the track area.
- **Truth:** `truth/` holds the vg-deconstruct VCF per window and a cut straight from the GBZ per haplotype.
- **Blind verdicts:** `claims*/` holds what readers took from the screens, hashed before they opened the truth. `judgments/` judges the texts and `judgments2/` the drawings.
- **Gate flags:** `triage/verdicts.jsonl` holds every gate flag and disputed readout with a verdict and a code cause. The gate run of the remaining windows in `ext2/` is still going on ada.
- **Faults:** `FAULTS.md` lists the verified faults, L1–L5 (lanes), R1–R5 (walk rows) and G1–G7 (graph track), each with windows and causes.

## What the audit settled

- **False marks in all three views.**
  - **Worst:** lanes leave a haplotype's further pieces blank. Four lanes at a 54 kb insertion read as lost sequence.
  - **Rows:** stop at the first pass and paint reversed walks forward, which hides the 8p23.1 inversion.
  - **Graph track:** the thickness of skip arcs and of nodes doesn't follow walk counts.
- **The drawing gates were right not to flag crossings.** The false-crossing flags are sub-pixel folds and loops.
- **Lane tags verified true at graph level:** "33 kb insertion" at C4 and "94 kb deletion" at amylase.
- **Repeats:** on this Minigraph-Cactus graph every haplotype walks each node at TSPY at most once. Extra copies sit on nodes GRCh38 does not walk, so a walk count gives nothing there.
- **CFH, the paper's figure locus, is clean in all three views.**

## Fix branches being built (unpushed)

- **Lanes, L1–L5:** jbrowse-components and plugin worktree branches.
  - L1: draw every piece as its own row, and stop splitting one walk at a large insertion.
  - L2: drop frame numbers from headers.
  - L3: draw mismatch tiles only when a pixel wide, with a key entry.
  - L4: a haplotype sequence bar with a dashed join across a deletion.
  - L5: rework the unlanded 56cc94c330 without the "complex" kind.
- **Walk rows, R1–R5:** bandage-core and graph-walks worktree branches.
  - Every pass is drawn.
  - Orientation from step strands, with chevrons and "of which N reversed".
  - True row-end texts.
  - Own scale stated plainly, with each bar starting at its walk's place.
- **Graph track, G1–G7:** bandage-core and plugin worktree branches.
  - One linear thickness scale, in walk passes, for nodes and links.
  - The graph cut expands detail records, timed first.
  - Skips through tiny nodes get a route.
  - Arches replace loop-shaped skips.
  - The fold works by bp.
  - Strand heads on reversed nodes.
  - An empty-window key note.

Each branch gets BEFORE/AFTER shots of the audit windows in `after-lanes/`, `after-rows/` and `after-graph/`. The owner sees them before any landing or release.

## ada

The paper session's timing runs wait behind `~/work/scratch/drawclock-2026-11-23/gate.sh`. Nothing heavy runs on ada until its `gate.log` says "done".

## Owed to other sessions

- **Paper session:** the response letter's gfa-to-tabix claims were checked. The hosted anchored file is byte-identical to a rebuild with current code, and its one moved component is 22,501 nodes under chr1:2,650,330-2,776,935. The paper session is running its own draw-clock timings.
