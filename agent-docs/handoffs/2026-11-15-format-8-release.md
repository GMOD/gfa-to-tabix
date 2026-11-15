# Handoff, 2026-11-15: walk format 8 release, third session

Session 22a29087 took over both lanes from a36cf6aa and 3210c7a1, then hit the usage limit. Nothing is pushed, tagged, published or uploaded. Everything below is local or on ada.

The gate list and release order are unchanged: `docs/handoff/2026-11-14-format-8-release.md`. Its "State on 2026-11-15" section says the same as this file in less detail.

## Subagent reports are the agents' own, mid-run

The two reviews below were stopped before finishing. Their figures come from their progress files, which I read but did not re-run. Re-check anything you act on.

## Decided

- **The walk header names its graph, and no writer or version.** `#walks` gains `graph:Z:` (the index's hash) and `leftout:i:`. Format number stays 8. The owner ruled out a version stamp: it would change every file's bytes at each writer release and force a re-upload on sync.
  - gfa-to-tabix branch `provenance`, head 8fe5434, in ~/src/gfa-to-tabix-provenance. Three commits above 8a965ac; main has since gained two handoff commits, so rebase before fast-forwarding. Not merged, because main's checkers then fail the hosted files until they are rebuilt.
  - graph-walks branch `provenance`, head ae6e0ff, in ~/src/graph-walks-provenance, on d20d416.
  - ADR 0015 on that branch has one marked line to fill after the whole-genome byte check.
  - Checked by me: the writer diff, the shared `GraphHash`, the spec text, and that `scripts/walks-header-diff.py` exits 0 on a header-only change and 1 when rows differ.

## Landed locally

- **Drawing fixes.** bandage-core `release-fixes` 76e0324 (~/src/bandage-core-rel), plugin `release-fixes` 8fbe392 (~/src/jb2plugins/jbrowse-plugin-graphgenomeviewer-rel). Screenshots I looked at are in ~/src/walks8-evidence/22a29087/drawing-pics/. Retake at the final heads anyway.
  - Hosts must follow: `bubbles/bubbleLabel`, `labelledNodeLengths` for `nodeLengthLabels`, `depthKey` for `depthRange`.
  - Open: 3 plugin typecheck errors in `GbzBaseSyntenyAdapter.ts` (hand-linked node_modules); bandage-core's SVG figure writes no node or placeholder lengths.

## graph-walks review (Fable, stopped mid-run)

Progress file: ~/src/walks8-evidence/22a29087/gw-review/PROGRESS.txt, with REVIEW*.txt, scripts and fixtures beside it. Remote work: ada ~/work/review-gw7/.

- **d20d416 is needed and holds.** On the chr22 abridged/unabridged pair, every haplotype, first 350 of 372 windows: steps, links, places, departures and `breakAt` equal. At 031ab8f, `breakAt` differs for 346 departures in 22 windows.
- **One difference at both heads.** A gap's `before`/`after` is NaN in the abridged cut where the twin states a position. Fixture `fx/gapnan.R.gfa`; the repo's own twin test fails once that pair is added. README lines 410-414 claim equality without this exception.
- **Tests miss the place of a departure's rejoining steps.** Two mutants survive.
- **Provisional verdict:** merge d20d416; tag after the README states scope and exceptions and two tests are added. No reader change needed so far.
- **Jobs may still be running on ada** as chained scripts (A/chainA.sh onward, log A/chr22-run.log): the rest of chr22, controls, planted breaks. Check `ssh ada` for them before starting anything heavy there.

## S5 premise check (Fable, stopped mid-run)

Progress file: ~/src/walks8-evidence/22a29087/s5-premise/PROGRESS.txt. Scratch with checkers: session scratch `s5-premise/` (may be gone).

- **The stated pass does not reach bandage-core.** graph-walks knows each step's pass (`walkChunk.ts:437`, fragments' `refStarts`) and `WalkGraph.tables()` drops it (`walkRows.ts:1169-1200`).
- **Fix needs no format change:** one array, `walks.refStarts`, on the tables; bandage-core reads it and keeps 895a573's guess only for sources that state none.
- **Written but uncommitted** in ~/src/graph-walks-s5 (branch `step-pass` off d20d416) and ~/src/bandage-core-s5 (branch `s5-premise`, on d19c255). Both trees are mid-edit.
- **Its counts:** pggb chrY, 533 windows, 8,343 rows: 9da2502 1,437 mismatches, 895a573 430, d19c255 401, its change 0. HPRC, 504 windows: 0 for all, every readout identical. A final recheck was still running.
- This adds a field to graph-walks 7's tables, so it goes in before the tag.

## Two independent designs

- **From the requirement alone, then shown our spec:** freeze format 8 as it is. ~/src/walks8-evidence/22a29087/blind-design/ (DESIGN.txt, COMPARE.txt).
- **Allowed to read pangyplot:** keep the bubble hierarchy as a later layer, not the file layout. ~/src/walks8-evidence/22a29087/blind-design-bubbles/DESIGN.txt. Not shown our spec; its pangyplot claims are unchecked.

## Not started

- Rebuild both genome files with the header, byte check, re-upload under the `-f8` names, sha256 and release-check from both URLs.
- ADR 0012 acceptance runs.
- VCF drawing check: source ~/src/walks8-evidence/a36cf6aa/drawcheck/src/, never run; VCF slice for its 66 windows at ada /mnt/sdb/cdiesh/vcfcheck/drawcheck-slice.raw.vcf.gz.
- Reshoot, blind layout judge, integration pass, ggbandage node lengths, core-next branches, gfa-to-tabix CI pin and rehearsal, jb2hubs, release notes, parity audit.

## Next, in order

- Read both progress files; finish or re-run the two reviews' last steps.
- graph-walks: merge d20d416, then `step-pass` once committed and reviewed, then `provenance`; fix the README's scope, exceptions and hosted file name; add the two tests; version commit at the head; repack.
- gfa-to-tabix: rebase and merge `provenance`; rebuild and re-host.
- Then the gates above.

## Where things are

- Dead agents' briefs: ~/src/walks8-evidence/22a29087/briefs/.
- Earlier sessions' scratch: ~/src/walks8-evidence/a36cf6aa/ and 3210c7a1/.
- Release page: https://claude.ai/artifact/PFkwJvV1eSiHnGG4REsH1s

## Fourth session, in progress

Picks up from the state above. Nothing is pushed, tagged, published or uploaded.

- **Format 8 stays as it is, confirmed.** Both independent designs say so: the one made from the requirement alone ("Freeze format 8 as it is", `~/src/walks8-evidence/22a29087/blind-design/COMPARE.txt`, verdict and the "I would insist on" section: nothing) and the one allowed to read pangyplot (decision in PART 2.5 of its DESIGN.txt: do not build the layout around the hierarchy; keep it as a later layer). The second's list of what a base layout needs for that layer is met or deferrable: stable node ids (the GFA's), own coordinates at reference anchors (fragStart, hapOffset), layers a reader may ignore (the additions rule), a deterministic build (an acceptance gate), and every link of a loaded node, which the node and link index holds and the walk file does not; that last one is reader-side work for a later collapse feature, not a row change.
- **S5 final tallies**, rechecked with the final `truth.py` (copied to `~/src/walks8-evidence/22a29087/s5-premise/out/`): pggb chrY 8,343 rows, new reader plus new bandage-core 0 mismatches; d19c255 415, 895a573 444, 9da2502 1,535. HPRC 4,536 rows: 0 for every build. Planted faults still fail (177 and 4,276 on HPRC; 14, 3,152 and 1,215 on pggb).
- **S5 committed.** graph-walks `step-pass` f4ee6e3 (on d20d416) in ~/src/graph-walks-s5; bandage-core `s5-premise` 2a56505 (on d19c255) in ~/src/bandage-core-s5. Touched tests and typecheck pass on both, except bandage-core's known `typecheck/graphWalks.ts` identity check against the old tarball. An independent Fable review of both commits said: land, with one required change, which is done. Its findings (probe and cut scripts copied to `~/src/walks8-evidence/22a29087/s5-review/`):
  - the new `onReference` was untested: a reverted definition passed every test but misreads a lone-flank walk as ending at the window. Fixed by a test in 534052d, which I confirmed fails on that mutant and passes on the code.
  - `graphPieces` fell back silently to the nearest-pass guess for every walk when one host-built path had `refStarts` of the wrong length. Now it throws; tested in the same commit.
  - a step stated at a reference pass the cut does not show counts as the walk's own bases in the readout. Correct by the cut's rule, but "elsewhere on the reference" would be truer wording. A follow-up, not a landing condition.
  - `WalkVisit.onReference` changed meaning for `walkRowLinks` carriers, so a BEFORE/AFTER pair on a pggb chrY repeat window is owed before release (standing rule). None taken yet.
  - the reviewer reran the cut on `copies.R` at both heads itself: old code drew node 3 of U#1#u at the reference's first pass, 12 bp from where the file puts it; new code at the stated pass.
- **S5 is on bandage-core `release-fixes`**: 927d87d (the former d19c255, reworded), d572d20 and 5e92e48 on 76e0324 in ~/src/bandage-core-rel. graph-walks was repacked from main 2e30e0f into `~/src/vendor/walks8-pack/jbrowse-graph-walks-7.0.0.tgz` and installed (lockfile checksum committed on `release-fixes`); bandage-core-rel's typecheck is clean and the touched tests pass. The full bandage-core suite then passed once on release-fixes a99b476: 99 files, 1013 tests, 9 skipped. bandage-core 14.0.0 was repacked from a99b476 into `~/src/vendor/walks8-pack/jbrowse-bandage-core-14.0.0.tgz` (sha256 52995e67...) beside the graph-walks tarball (15026b67...), for the consumer refresh. The two commits cherry-pick cleanly onto bandage-core `release-fixes` 76e0324 (scratch branch `s5-on-rel`, worktree under the session scratchpad), tests pass there too.
- **The graph-walks review's remaining runs finished on ada and all hold** (summaries copied to `~/src/walks8-evidence/22a29087/gw-review/ada/out/`, the big .jsonl stay on ada under ~/work/review-gw7/out/). At d20d416 on all 372 chr22 windows, every haplotype: 3.1 billion values compared, 12.1 million off-reference rows on the rule with 0 wrong, breakAt a function with 0 exceptions, and the only differences are the stated NaN gap breakpoints (355 values in 53 windows) and fragment order. Planted place, breakAt and step breaks are each caught in 8 of 9 probe windows. The controls at 16b4f72 and 402ce92 show 39,816 wrong placements of 129,294 on the same 90 windows, so the check fails on the old readers. Links recomputed from fragments, departures and breakAt: 198,496 checked, 0 missing, 0 unwalked. The unexpanded cut differs from the whole file only in what abridging withholds, with 0 wrong placements. Suite, typecheck and lint pass at d20d416 on ada; the equality harness gives 0 differences at both heads over 16 windows and 384 pairs of cuts. Verdict stands: d20d416 merged, the README now states the scope and exceptions.
- **graph-walks main was fast-forwarded to d20d416** on that verdict. `provenance` was rebased onto `step-pass`: 24f095d in ~/src/graph-walks-provenance, so the chain is main d20d416 -> step-pass f4ee6e3 -> provenance 24f095d. The review's follow-ups are done on top of it, `provenance` head 2e30e0f: fixtures gapnan.R and secondline.R with their twins (0d38fc8, built lines in `test_data/build.sh`, every old fixture rebuilt byte for byte with the header writer), the twin test holding gapnan but for the NaN breakpoint and a test stating those values (e713710), a test placing a departure's rejoining steps that both Finding 2 mutants fail (5fcdd68), the README's twin scope, exceptions, fragment order and moving places (0d85db1), and the `-f8` hosted names (2e30e0f). Full suite 731 pass, typecheck, lint and format clean. I reread the README diff and reran the reader tests; the mutant and perturbation results are the agent's.
- **gfa-to-tabix main is at 9e46a46**: `provenance` rebased and fast-forwarded. Its checkers fail the hosted files until those are rebuilt with the header.
- **Plugin typecheck errors are the hand-linked node_modules**: the three errors in `GbzBaseSyntenyAdapter.ts` are gbz-base 7.4.1 in the plugin against 7.4.0 under bandage-core-rel's node_modules, two copies of one class. Nothing to fix in code; recheck on the clean install.
- **bandage-core's SVG figure now writes lengths, on a side branch awaiting the owner's look.** `svg-lengths` eab3e4d in ~/src/bandage-core-svglen (on a99b476): `figureSvg` places labels with the hosts' `layoutLabels` fed `labelledNodeLengths`, a `nodeLengths` figure setting defaulting off, documented in docs/figures.md; a test reads the SVG text and fails on a99b476. Suite 1014 pass, typecheck and format clean. Pictures in `~/src/walks8-evidence/22a29087/svg-lengths/` (BEFORE, AFTER lengths-off, AFTER lengths-on per case). I looked at the fixture, blocks force and drawnedge force pairs: AFTER differs only by the labels; with lengths off only placeholders are labelled. Two things to weigh before merging: with lengths on, the label budget takes the biggest nodes first, so small placeholders lose their label; and on drawnedge force the placeholder lies under the reference run, so its "600 bp" reads as that run's length. Not merged.
  - Still open for ggbandage: it draws from `figureData` tables, which carry no placed labels and no placeholder flag, so it gets nothing from this. Needs a labels table in `figureData` and drawing in ggbandage. Wait for the consumer refresh to finish in ggbandage-format8 first.
  - Lint on `release-fixes` had four `no-shadow` errors from the S5 tests, missed because the earlier runs linted single files; fixed on `release-fixes` at the head after a99b476.
- **Consumer refresh on the final tarballs, all green**, committed on each `format8` branch (nothing pushed): BandageJS 922f1bf7 (checksums; node lengths through bandage-core's `labelledNodeLengths` with a test that a placeholder is labelled with lengths off; 210 tests, typecheck, lint, format clean); ggbandage 73dbac3 (rebundled; `docs/gallery.md` left as the gallery script writes it, a stale-check failure that was already on main; R CMD check 0/0/1 with only the new-submission note, 308 tests); sequenceTubeMap 0f835b4 (checksum; 755 tests on the second run, the first hit a pre-existing race between its two server test files sharing `uploads/`, not fixed); ggtubemap b33bff9 in ~/src/gmod/ggtubemap-format8 (rebundled; R CMD check OK, 120 tests). Plugin `release-fixes` 8fbe392 unchanged: 1000 tests, lint clean, typecheck only the three gbz-base duplicate errors. Its `node_modules/@jbrowse/graph-walks` hand link pointed at an older install, so I repointed it at bandage-core-rel's copy of the final tarball and reran typecheck and the suite through node directly (`pnpm <script>` there triggers an install that wipes the hand links). Agent numbers above are the agent's; I checked the commits and clean trees.
- **ada was unreachable** at the start of this session (timeout, then refused: the ada key is not in the agent and fail2ban likely banned the retries). The chr22 review chains, the hosted-file rebuild, the acceptance runs and the VCF drawing check all wait on it. The drawing checker (`~/src/walks8-evidence/a36cf6aa/drawcheck/src/drawcheck.ts`) takes `--walks --vcf --windows --out --build --source`; it can run locally once the VCF slice is copied from ada.
