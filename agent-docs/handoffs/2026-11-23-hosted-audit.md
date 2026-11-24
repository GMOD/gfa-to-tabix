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

## Fix branches (unpushed), state at the end of the 23 November session

Nothing is pushed, landed or released. The owner said on 23 November "do whatever you think is best and land when ready". Landing on the repos' mains is authorized once the steps below are done; publishing to npm or changing the hosted demo is a separate step the owner hears about first.

Reviews are in `reviews/` of the evidence folder. `arbitration-20261123.md` records seven drawing calls two independent deciders settled at the owner's request. `final-reviews-20261123.md` records the three landing reviews; every fix they asked for is committed except where listed below. The owner's page of the calls is artifact 2t9QAkePeNm1Wrgg8owruR.

The owner's steer, also in memory (walk-rows-vs-lanes): keep walk rows small, since the lanes show the same haplotypes and often look better; neither may overpromise; a graph track needs a one-button way into the lanes (todo graph-track-lanes-button); 400 haplotypes need a cohort view (idea cohort-overview-then-lanes).

### Landing order

Walk rows first, then graph track (the two core branches merge cleanly with each other), then lanes in jbrowse-components. The plugin, BandageJS and ggbandage branches pin a published bandage-core, so they land with the core release.

### Walk rows, branch `rows-truth`

- Worktrees `~/src/bandage-core-rowstruth` (f6e619d), `~/src/jbrowse-plugin-graphgenomeviewer-rowstruth` (c2c89ce6), `~/src/BandageJS-rowstruth` (79e08f5b), `~/src/ggbandage-rowstruth` (ac670ed). All clean, not rebased, no backup branches yet.
- Built: rows start at the left; one `//` per trip; chevrons only over reversed sequence; a one-line readout tested by mutation; swatch-only key; docs and figure regenerated.
- Left:
  - ggbandage draws the one line: the work is in `git stash@{0}` of the ggbandage worktree, untested; it still needs `test-figure.R`, roxygen and man pages, and then `BREAK_TEXT` removed from core.
  - Check the 4fa1187 message's claim that pggb NA20806#1 reads "675 kb · // 3.4 kb" on a figure.
  - Backup branches, then rebase core onto 14.5.0 (conflict in `src/figure.ts`: keep both the name-gutter move and main's `laneReach`), and the three hosts onto their mains.
  - Once on the rebased heads: core suite, typecheck, lint, format; plugin tests and tsc with core installed from `pnpm pack` (clean that way on the graph branch); BandageJS; ggbandage.
  - Reshoot H-8p23, R1M-06, R1M-05, H-SMN, H-MAPT and both pggb windows into `after-rows/pairs-v5/`.
- Evidence: `after-rows/pairs-v4/`, `after-rows/v6-r4-20261123/`; ada `~/work/walks8-gates/agents/rows-r4/`.

### Graph track, branch `graph-truth`

- Worktrees `~/src/bandage-core-graphtruth` (5a4c231), `~/src/ggv-graph-truth` (e9413cdc), `~/src/BandageJS-graphtruth` (431d78bb), `~/src/ggbandage-graphtruth` (13bb551). All clean and rebased onto their mains; backups `graph-truth-pre-rebase` in each.
- Built: a skip too short to arch draws as a plain link, keyed "link"; the foot hover gives a number only when every walk through the link skips the same stretch; heads judged by reversed bp; grow-only key fit in the plugin and BandageJS.
- The rebase onto 14.5.0 dropped `busiestEdge` and `edgeWidthFactor` and added `passes` on folded links in `threadFold.ts`, since a folded graph's links counted threads while its nodes counted walks. This has had no independent review.
- Suites on the rebased heads are green, and the plugin tsc is clean with core installed from a packed tarball.
- Left:
  - Reshoot on the rebased build into `after-graph/pairs-v8/` and `rgfa-identity-v8/`: on ada start `node serve.mjs 8661` in `~/work/walks8-gates/agents/graph-truth4/after/`, then `after/run8.sh` under the lock. Three shots exist in `after/v8/shots`, unlooked at.
  - Show the rGFA track identical to what review 3 accepted, or that main's 14.5.0 alone accounts for any difference.
  - After walk rows land, rebase onto the new main and rerun the core suite.
  - ggbandage lands only with the bundle bump.
- Evidence: `after-graph/pairs-v7/` and earlier; ada `~/work/walks8-gates/agents/graph-truth4/` (`r8/` holds the rebased copies, `logs/s8/` the suite logs).

### Lanes, jbrowse-components branch `lanes-truth-l1-l5`

- Worktree `~/src/jbc-lanes-truth`, head 6d323f93ea, 27 commits on current origin/main, squashed; backup `lanes-truth-pre-squash` (dd152eb5df).
- Built: the tandem-copy chip removed; the key as one row of the fixed lane marks, with data-dependent colour scales in main's floating legend; one squeeze tolerance on every rung; pins and hides reattach to the nearest piece; the no-haplotype line shown only when the held fetch is current, nothing is placed and no fetch failed.
- Left, all on 6d323f93ea:
  - Full suite, typecheck, `pnpm check-format`, `pnpm lint`, `pnpm lint:eslint`.
  - Rebuild jbrowse-web on ada, reshoot the `pairs-v4` windows plus H-TSPY into `after-lanes/pairs-v5/`, undrawn checker, text diff against v4, and look at the pictures, including the key at a narrow pane.
  - `typeDocs.generated.json` is stale at the two commits before the key commit and right at the head.
- "13 kb deletion" and "114 kb deletion" where the VCF has a replacement wait on the held `lanes-splitter-pin`.
- Evidence: `after-lanes/pairs-v4/`, `after-lanes/after-v4c-20261123/`; ada `~/work/lanes-truth-v3/` (`r4probe/scripts/run5.sh`, `shoot4.mjs`).

### Rules every brief carries

- Builds, tests and shots on ada only; heavy steps under `flock ~/work/ada-heavy.lock`.
- Scripts in a per-agent scratch folder; rsync with both paths written out, no `--delete`.
- The session that did this work ran its implementers as subagents of session f12e5cb1 under `~/.claude`; their transcripts are in `~/.claude/projects/-home-cdiesh-src-gfa-to-tabix/f12e5cb1-2c77-441e-a4c6-192185bf74b8/subagents/`. Start fresh agents rather than waking that session.

## ada

The paper session's timing runs wait behind `~/work/scratch/drawclock-2026-11-23/gate.sh`. Nothing heavy runs on ada until its `gate.log` says "done".

## Owed to other sessions

- **Paper session:** the response letter's gfa-to-tabix claims were checked. The hosted anchored file is byte-identical to a rebuild with current code, and its one moved component is 22,501 nodes under chr1:2,650,330-2,776,935. The paper session is running its own draw-clock timings.
