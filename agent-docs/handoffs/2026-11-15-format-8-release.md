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
- **S5 committed.** graph-walks `step-pass` f4ee6e3 (on d20d416) in ~/src/graph-walks-s5; bandage-core `s5-premise` 2a56505 (on d19c255) in ~/src/bandage-core-s5. Touched tests and typecheck pass on both, except bandage-core's known `typecheck/graphWalks.ts` identity check against the old tarball. An independent review of both commits is running. The two commits cherry-pick cleanly onto bandage-core `release-fixes` 76e0324 (scratch branch `s5-on-rel`, worktree under the session scratchpad), tests pass there too.
- **graph-walks main is at d20d416** (fast-forwarded on the review's verdict). `provenance` was rebased onto `step-pass`: 24f095d in ~/src/graph-walks-provenance, so the chain is main d20d416 -> step-pass f4ee6e3 -> provenance 24f095d. An agent is adding the review's README scope and exceptions, the `-f8` file names, the gapnan twin fixture and the rejoining-steps test on top of `provenance`.
- **gfa-to-tabix main is at 9e46a46**: `provenance` rebased and fast-forwarded. Its checkers fail the hosted files until those are rebuilt with the header.
- **Plugin typecheck errors are the hand-linked node_modules**: the three errors in `GbzBaseSyntenyAdapter.ts` are gbz-base 7.4.1 in the plugin against 7.4.0 under bandage-core-rel's node_modules, two copies of one class. Nothing to fix in code; recheck on the clean install.
- **bandage-core's SVG figure and node lengths**: `src/figure.ts` never passes `labelledNodeLengths` into the label layout, so ggbandage's figures lack node and placeholder lengths. A drawing change; do it after S5 lands, with BEFORE/AFTER pairs shown first.
- **ada was unreachable** at the start of this session (timeout, then refused: the ada key is not in the agent and fail2ban likely banned the retries). The chr22 review chains, the hosted-file rebuild, the acceptance runs and the VCF drawing check all wait on it. The drawing checker (`~/src/walks8-evidence/a36cf6aa/drawcheck/src/drawcheck.ts`) takes `--walks --vcf --windows --out --build --source`; it can run locally once the VCF slice is copied from ada.
