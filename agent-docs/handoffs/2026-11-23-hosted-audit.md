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

## Fix branches (unpushed), state at the end of 23 November

Nothing is pushed, landed or released. Each branch set goes through implementer, then an independent Fable review, then BEFORE/AFTER pairs on an owner review page with landing tick boxes. Reviews and rulings are in `reviews/` of the evidence folder; `reviews/arbitration-20261123.md` records seven drawing calls two independent deciders settled at the owner's request, and the lanes and walk-rows passes below are building those rulings. The owner's page of the calls is artifact 2t9QAkePeNm1Wrgg8owruR. Related: todo graph-track-lanes-button and idea cohort-overview-then-lanes.

- **Graph track**, branch `graph-truth` in `~/src/bandage-core-graphtruth`, `~/src/ggv-graph-truth`, `~/src/BandageJS-graphtruth`, `~/src/ggbandage-graphtruth`.
  - Heads: core 072aa22, plugin ac8b92e1, BandageJS bd15f8f0, ggbandage 4db94a5, all clean, suites green (the plugin typecheck exits 1 only on three duplicate `gbz-base` errors from the local link).
  - Review 4's faults are fixed and the arbitrated rulings are in: a skip too short to arch draws as a plain link, keyed "link"; the foot hover gives a number only when every walk through the link skips the same stretch.
  - Not yet done: an independent review of everything after 2c0a066; the plugin's grow-only key fit seen in a browser; heads with two rank-0 references.
  - Pairs: `after-graph/pairs-v7/` (earlier rounds in v4 to v6). ggbandage lands only with the bundle bump, the plugin with the core release and pin.
- **Lanes**, jbrowse-components branch `lanes-truth-l1-l5` in `~/src/jbc-lanes-truth`.
  - Head bef619994a, 32 commits on main, clean. Full suite green apart from three tables tests fixed test-only in the head commit (tables folder rerun green); typecheck green on the head. origin/main has moved 2 commits since the rebase, none in the lanes folders.
  - `reviews/lanes-truth-review3.md` faults are fixed and the arbitrated rulings are built: the tandem-copy chip is removed, the key is one row above the lanes listing only drawn marks, one squeeze tolerance on every rung, pins and hidden lanes reattach after a reload, and a window with no haplotype sequence says so.
  - Not yet done: an independent review of this pass; a full suite run on the exact head after the next rebase; squashing 7e4657cf53 and 70fbba9fdb, which later commits undo. Ordinary insertion chips can appear or not with how far the fetch reaches, never with a false size. A bar's end does not say whether the fetch or the contig ended.
  - "13 kb deletion" and "114 kb deletion" where the VCF has a replacement wait on the held `lanes-splitter-pin`.
  - Pairs: `after-lanes/pairs-v4/` (before, round 3, after); shots in `after-lanes/after-v4c-20261123/`.
- **Walk rows**, branch `rows-truth` in `~/src/bandage-core-rowstruth`, `~/src/jbrowse-plugin-graphgenomeviewer-rowstruth`, `~/src/BandageJS-rowstruth`, `~/src/ggbandage-rowstruth`.
  - Heads: core ffa1a12, plugin c2c89ce6, BandageJS 79e08f5b, ggbandage ac670ed, all clean, suites green at those heads (plugin in a clean worktree; its tsc shows the same three `gbz-base` errors as its base).
  - `reviews/rows-truth-review3.md` faults are fixed and the arbitrated minimum is built: rows start at the left, one `//` per trip, chevrons only over reversed sequence, a one-line readout, a swatch-only key. The owner wants walk rows kept small beside the lanes.
  - Not yet done: an independent review of this pass; the chevron key entry still shows where no chevron is drawn; the reversed-flag check reads the code's own tables; ggbandage still prints the sentence readouts, since a figure has no hover; core main moved to 14.5.0 and the rebase conflicts in `src/figure.ts`.
  - Pairs: `after-rows/pairs-v4/`; shots and logs in `after-rows/v6-r4-20261123/`.

### What is left

- All three implementer passes are finished; nothing is pushed, landed or released.
- One independent Fable review per branch set of the passes made after its last review (graph after 2c0a066, lanes after 7fb25d5197, rows after 10a01bb), then the owner sees the before-and-after pairs before any landing.
- The plugin typecheck shown green without the local core link.
- Rules every brief carries: builds, tests and shots on ada only; heavy steps under `flock ~/work/ada-heavy.lock`; scripts in a per-agent scratch folder; rsync with both paths written out, no `--delete`.

## ada

The paper session's timing runs wait behind `~/work/scratch/drawclock-2026-11-23/gate.sh`. Nothing heavy runs on ada until its `gate.log` says "done".

## Owed to other sessions

- **Paper session:** the response letter's gfa-to-tabix claims were checked. The hosted anchored file is byte-identical to a rebuild with current code, and its one moved component is 22,501 nodes under chr1:2,650,330-2,776,935. The paper session is running its own draw-clock timings.
