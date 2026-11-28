---
name: claims-and-page-truth
description: Live thread from 27 November. Two Opus implementers were mid-work when the session ran out of tokens, on unpushed branches; clustering fix and hover removals on `claims` branches, genomes.jbrowse.org page fixes on jb2hubs `page-truth`. Nothing from them is reviewed, pushed, released or deployed. Next is to check their work, build the owner's approval page, and only then release and deploy.
---

# Claims fixes and the pangenome page: handoff, 27 November

## State

- **Released and done this session:** bandage-core 15.1.0, plugin 10.15.0 (`latest/` rehosted), BandageJS demo, ggbandage, jb2hubs pin. See `2026-11-24-landing.md`, last section.
- **Not deployed:** genomes.jbrowse.org. It waits on the owner's approval page.
- **Two implementers were running when the session ended.** They cannot be resumed from another session; read their branches and evidence folders instead. Heads when this was written (both may have moved since, all clean):
  - graph-fold `claims`, `~/src/graph-fold-claims`, c633b5f
  - bandage-core `claims`, `~/src/bandage-core-claims`, 589be8e
  - plugin `claims`, `~/src/jbpgv-claims`, 98a74891 (branched from `unstated-axis`, now main)
  - jb2hubs `page-truth`, `~/src/jb2hubs-page-truth`, 4bdeaa53
  - ada folders: `~/work/walks8-gates/agents/claims-fixes/`, `agents/jb2hubs-page-truth/`
  - a consumer may hold an uncommitted or last-commit `file:` pin to a packed tarball; swap it before anything lands

## What each was asked to do

- **Claims fixes** (`todo/claims-inventory.md` has the plan, the classification and the clustering ruling):
  - graph-fold: clustering joins only sites with identical breakpoints, inserted length within the threshold, in two variants (A threshold only, B also within 5%); context bp out of "folded away"; event sentences removed, `ThreadEvent` kept as data
  - bandage-core: depth and width keys count haplotypes, exact depth (walks at least 1 bp), edge nodes print no length and an open range, "folded away" keeps its amount
  - plugin: hover event lines removed
  - proof owed: a test per fix that fails on old code, the seven-walk fixture (`stack.mjs`, reproduced on the cap), per-haplotype invariant checks with planted breaks, the sweep before and after, BEFORE/AFTER pairs in `~/src/walks8-evidence/sessions-20261127/claims-fixes/`
- **jb2hubs page truth** (`todo/jb2hubs-rows-and-lit-lanes-disagree.md`, `lane-label-names-a-haplotype-twice.md`, `hosted-views-that-draw-nothing.md`, `jb2hubs-sweep-and-deploy-core15.md`):
  - a row and its lit lane agree or the lane carries no count; GSTM1's rows true; one denominator; no repeated names; `compactKey: true`
  - proof owed: `check-pangenome-graphs` red on production and green on the branch, a VCF check of the 12 pages the audit skipped, BEFORE/AFTER pairs in `sessions-20261127/jb2hubs-page-truth/`
  - the website folds with clustering on (`pangenomeGraphLayout.worker.ts:15`), so it needs the new graph-fold too

## Next

- Check each branch against its brief yourself: run the fixture, read the diffs, look at every BEFORE/AFTER.
- One technical and one user-view Fable review of each batch. A planned second Fable read of the pangenome page's design (can rows named as deletions and lanes counted from folded walks be reconciled, or should one go) was not started.
- Pick clustering variant A or B from the pictures.
- One approval page for the owner, BEFORE/AFTER pairs: hover event lines gone, clustering at chr18:20,853,563, chr20:30,005,257, chr7:102,451,348 and chr15:23,213,108, depth and width keys, edge nodes, "folded away", and the genomes.jbrowse.org pages that change.
- After approval: graph-fold major, bandage-core, plugin, hosts, with the release gates; then jb2hubs sweep and deploy from ada.

## Evidence, all under `~/src/walks8-evidence/sessions-20261127/`

- `hosted-audit/` (brief, findings.jsonl, shots), `claims-classify/`, `claims-plan/`
- ada: `agents/fold-steer/` (clustering probes), `agents/claims-classify/`, `agents/hosted-audit-2/`

## Traps met today

- ada's `~/.cache/puppeteer` vanished; `node node_modules/puppeteer/install.mjs` in the plugin checkout restores Chrome.
- ada's shell is zsh; `lib.sh` helpers need `bash -c`.
- `~/.claude2` hit its monthly spend limit on 27 November (weekly reset 2 December); this session ran on `~/.claude`.
- Leftover merged worktrees to remove once the `claims` branches no longer need them: `~/src/BandageJS-unstated-axis`, `~/src/jb2plugins/jbrowse-plugin-graphgenomeviewer-unstated-axis`.

## jb2hubs `page-truth` reported (head 17859a5c, unpushed, unreviewed, its claims not yet checked by anyone)

The session hit its usage limit as this arrived. What the implementer says:

- A row is lit only where exactly one thread holds its haplotypes and no others (`litThreads`, `pangenomeWalkCut.ts:72`); the cut holds only placed haplotypes; graph shares are off (`nodeShares: false`); `compactKey: true`.
- GSTM1's cause was not the VCF states: `@gmod/gfa-tabix` joins departures under 50 bp apart and marks a join only by net length (`esm/structuralForms.js:68`, `:110-111`), so 82 haplotypes with the deletion and the insertion 20 bp on read as GRCh38's structure. Now a "realigned" row (15% / 66% / 18%, lanes 70, 305, 82).
- `check-pangenome-graphs`, extended: 18 of 18 ok on the branch, 18 of 18 fail on production. Suite 905 of 905, typecheck and lint 0.
- **Worse, to decide before it lands:**
  - 23 of 73 drawn rows light nothing when clicked, and the page does not say why;
  - LPA opens on its whole 130 kb window as an unlit 50-node tangle, undoing "LPA per row" without a decision;
  - shares on loops and deletion arcs are gone, including the arc share approved on 25 November; one denominator needs bandage-core to leave GRCh38's own walk out of its shares;
  - RHD's reference row is lit by default and not when clicked;
  - AMY1 still opens with no graph (145 nodes against a 60-node limit).
- **VCF check of the 12 pages:** many agree; the page undercounts at FCGR, MNS, PGA, KIR (missing haplotypes sit in "other forms" or are unplaced, so "N of M aligned here" undercounts); KIR 28.3 kb and 48.3 kb insertions, LPA's KIV-2 changes and AMY1's duplications disagree both ways. Not fixed.
- For bandage-core, not done: `threadLayers` skipping a pick it holds, `threadLabel` dropping repeats, `pickLabel` keeping `#1`.
- BEFORE, AFTER and MAIN (`origin/main` on a dev server) for all 18 pages: `~/src/walks8-evidence/sessions-20261127/jb2hubs-page-truth/<page>/`, with `pairs.jsonl` and `findings.jsonl`.

## Claims fixes reported (unpushed; ada refused connections before the last runs)

- **Heads:** graph-fold `claims` 263b0c5, bandage-core `claims` 9c7895f, plugin `claims` 98a74891. No `file:` pin is committed; the pins are uncommitted on ada.
- **Clustering:** only sites with identical breakpoints join, inserted lengths under the threshold apart (variant A, the default); `clusterTolerance` given adds a share bound (variant B). The seven-walk fixture draws `a c d f` on the branch (rerun here).
- **Implementer's cluster check** over the 480 sweep windows, each walk against its own plain fold: released 5,148 branches and 67 red windows, cap 5,792 and 57, A 5,500 and 0, B 6,417 and 0, unclustered 11,987. Before any fix 1,656 clustered alleles in 36 of 477 windows were moved by the threshold or more, the worst 3,233 bp.
- **Also built:** `outerBp` out of "folded away"; event sentences and `ThreadEvent.text` gone; depth counts haplotypes that walk at least 1 bp (0 of 3,469 interior nodes disagree); link passes count a haplotype once; width keys say haplotypes; edge nodes print "GRCh38 chr4, to 100,323,689".
- **Run on ada:** graph-fold lint, format, typecheck, 296 tests, build and pack all 0. bandage-core lint, typecheck and suite 0 at 589be8e; format failed on one test file, fixed in 9c7895f, not rerun.
- **Not run:** the plugin's full suite, typecheck and lint (related tests 243 of 244, the one failure fixed and not rerun); the sweep with the five new templates and the open-range matcher; the three planted breaks on the new stack; the chr15 and "folded away" picture retakes.
- **Pictures:** `~/src/walks8-evidence/sessions-20261127/claims-fixes/` (BEFORE, AFTER, AFTER-B). Looked at chr18 and chr7: depth 92 becomes 88 at chr18, keys read haplotypes, and both are somewhat busier (chr18 284 to 347 nodes, chr7 45 to 60; the "206-216 kb" box becomes four). A and B draw alike at chr7 and chr20.
- **Left red by design or not in the batch:** edge name, edge depth and "Edge:" link ends against a wider read; website shares; "nodes folded into it" in a deeper read of the cut route.
- **ada:** the ssh master died and one reconnect on 27 November was refused. No further ssh until the owner says it is up.

## Fable review of jb2hubs `page-truth`: do not land as it stands

Read-only review as a technical reader and a first-time visitor; it had no ada, so it checked against the hosted walk file (GSTM1, RHD, KIR), ran no tests, and did not view every BEFORE and MAIN picture. Three citations checked here (`litThreads`, `PLACED_SLACK`, the "drawn, not lit" note).

- **Keep:** the cut restricted to placed haplotypes, `compactKey`, GSTM1's three rows (70, 305 and 82 are true of the walks), graph shares off for now.
- **Redo the lighting.** Lighting only an exact row-thread match leaves 33 of 83 row clicks with no lit lane and gets worse under identical-breakpoint clustering (PGA's 172 lane splits to 122 and 50). Ruling to build: split each folded thread by row membership in page code, one path per (thread, row) with the intersection as its members and count. Every drawable row then lights its own carriers on each route they take, and lane counts sum to the row (HBA 29 + 1, KIR's deletion 28 + 6). Unprototyped: lane stacking where a row fans over many threads, and whether `figureSvg` takes split paths.
- **Required with it:**
  - HLA, KIR and LPA per row by an explicit rule, not by `FOLDED_NODE_LIMIT`;
  - "realigned" replaced by what the walk does ("18.4 kb deletion, 18.4 kb insertion", both marks drawn); the rule tests length only (`pangenomeWalkForms.ts:96-107`, `:183-199`), and a joined departure with net change over 10% and under the floor still reads as GRCh38's structure;
  - land with or after the graph-fold change, and re-sweep;
  - alt text "lit: none" on unlit graphs (`PangenomeGraph.tsx:87`);
  - `check-pangenome-graphs` fails on a drawable row that lights nothing, an opening view with no lit row, and lit members that differ from the row's carriers; each proven by a planted break.
- **False on production today, untouched by the branch:** KIR's "29.6 kb deletion, 7%" holds 6 haplotypes that skip 31.3 kb, since `PLACED_SLACK` (`pangenomePanels.ts:402`) merges changes within 10% and names the row by the lead's size. Likely the same at PGA, LPA, AMY1 and HLA, not verified. Name merged rows by a size range or do not merge across breakpoints.
- **Can follow:** `pageKind` calls a replacement with one side under 50 bp a deletion or insertion (`pangenomeWalkForms.ts:51-69`), against the 0 bp wording rule; the netted-join fix belongs in gfa-tabix, after which `joinedDepartures` goes; shares back on one denominator once core counts haplotypes; "depth 2 to 462" given a unit or dropped; AMY1 needs its own view; the VCF matcher fails RHD, where the page is right.
- **Pages that should not ship as on the branch:** HBA, HP, FCGR, KIR, MNS, LPA; AMY1 unchanged and still broken.
- Blocked: the rework needs ada for tests and renders.

## Reviews of the claims batch and a direction check, 27 November

- **Claims fixes finished on ada:** graph-fold 263b0c5, bandage-core 9c7895f, plugin a44f7e40, all CI 0; tarballs and manifest in `ada:~/work/walks8-gates/agents/claims-fixes/pack/` (a consumer needs a pnpm override for graph-fold, whose version is still 1.3.0). The sweep's `clamp` plant is no longer caught, since no host prints the length it corrupts.
- **User-view Fable review: ship with two changes** (both confirmed in `claims-fixes/hover-event-lines/AFTER.json`):
  - "0 haplotypes" in the thickness key, from exact depth on something drawn;
  - a box labelled "74.5-75.2 kb" has a hover headed "74,532 bp" over two haplotypes.
  - Also: "GRCh38 chr4, to 100,323,689" reads as a typo; at chr7 one thick "206-216 kb" arc becomes four thin ones and the common alternative no longer reads; "268 kb" twice at chr15; hover jargon to cut ("(rank 0)", "depth 88.0", node ids as the title, "reference nodes folded into it", "and 58 more threads").
- **Technical Fable review of the three branches:** running when this was written.
- **Direction check (Fable, high effort): change course in part.**
  - Sound and to keep: the plugin's graph at 8 haplotypes, walk rows, identical-breakpoint clustering (variant A), exact depth, sentences gone.
  - The cause of the false labels is structural: 67 templates, 49 resting on data the reader did not read; several tolerances that state two things as one (`cluster.ts`, `PLACED_SLACK`, `SHIFT_TOLERANCE` twice, `STRUCTURAL_BP` twice); a page number with four sources. Cure: one grouping function for every lane, row, width and count; no tolerance moves geometry; no denominators; no event names from our own derivations; a hover of length, stated span and haplotype count.
  - The fold is right for a named handful of haplotypes and wrong for the whole cohort at complex loci, where the unit is the site, collapsed and openable.
  - It says to stop the per-(thread, row) lighting rework and rebuild the example pages on one derivation, rows being the graph's own routes. The earlier page review rejected rows derived from threads (they change with window and threshold, and must exist where no graph draws). The two reviews disagree; this is the owner's call.
  - Proposed order: one release train (variant A, event lines out, haplotype depth, edge nodes, hover cut to facts) on one approval page; a removal-only page deploy; the lanes button; a site-collapse prototype at chr18, chr7, chr15, LPA and KIR; stale handoffs deleted and the hover-nicety, pggb, lanes and swatch todos parked.
- **Asked of the owner:** page rebuild or lighting rework; interim removal-only deploy; AMY1, LPA, KIR and HLA leading with walk rows; one openable mark per site as a new mark; one approval page per release train; the forms track hidden until its audit.

## Technical review of the claims branches: accept with named changes

Heads reviewed: graph-fold 263b0c5, bandage-core 9c7895f, plugin a44f7e40. Its scripts and inputs: `/tmp/claude-1001/-home-cdiesh-src-gfa-to-tabix/7ea69ed4-ab31-44d5-846c-1901d01123ad/scratchpad/techreview/` (scratch, may be cleared). All of the below was sent to the implementer, with the user-view fixes and the hover cut to facts.

- **Sound:** clustering cannot move a walk's reference route (0 failures on 15,000 fuzz inputs under a stricter comparison than the repo's; five cluster mutants go red); `outerBp` is counted once; depth never counts a haplotype with no step on the node.
- **To change:**
  - four bandage-core mutants pass all 2,083 tests (a hidden skip inside a walked node, link passes per thread, `clippedBp` on reference nodes, the key's zero entry);
  - `foldProblems` does not guard `outerBp`;
  - `leave` calls `hold`, so a node's members grow with the read's context;
  - a sub-threshold `beyond` end still makes "folded away" depend on context;
  - a short run at the read's end is drawn in a narrow read and dropped in a wide one (`chain.ts:109-125`); ruling: it says nothing, dropped like an inner one;
  - an edge node's name and its "Edge:" link ends say nothing on the read's side;
  - one count per node: hover names, link counts and `labelledNodeShares` use the haplotypes that walk it;
  - setting descriptions still speak of passes;
  - `clusterTolerance` and variant B removed (A is chosen); the `clamp` plant retargeted at the insertion node's length;
  - the sweep as run is not committed, and `printed.mjs` rebuilds the plugin hover instead of calling it.
- **At release:** graph-fold 2.0.0, bandage-core 16.0.0 on `^2.0.0`, plugin on `^16.0.0` rebased on 10.15.0. jb2hubs takes the new core only with `nodeShares: false` or after shares use depth. Tube maps: `todo/tube-maps-read-removed-graph-fold-api.md`.

## Rulings after the owner said to arbitrate, 27 November

- Variant A; the hover cut to facts; one approval page per release; AMY1 leads with walk rows; the forms track stays visible, with the netted-join fault first in graph-walks' queue and its audit after; a site-collapse mark is prototyped at chr18, chr7, chr15, LPA and KIR; hover-nicety, pggb, lanes and swatch todos parked, the lanes button built.
- The example pages' design (reworked lighting against rows rebuilt as the graph's routes) goes to a fresh Fable decider once the lighting rework's pictures exist; that also settles LPA, KIR and HLA and what an interim deploy carries.
- To the owner only as one artifact with examples: the fold release (chr7 loses its thick arc), the pages once decided, the site-collapse mark.


## Where the session stopped (out of tokens), 27 November: read this first

- **Nothing from today's branches is pushed, released or deployed.** Worktrees when this was written:
  - `~/src/graph-fold-claims` d7672df fix!, 0 uncommitted files
  - `~/src/bandage-core-claims` 1a356e4 A fo, 0 uncommitted files
  - `~/src/jbpgv-claims` 1e80f684 wip, 0 uncommitted files
  - `~/src/jb2hubs-page-truth` 5f81c6cb23e3, 0 uncommitted files
- **Two agents were still running and may have died mid-task:**
  - the claims implementer, on the combined list (user-view fixes, hover cut to facts, technical-review changes). bandage-core and the plugin may hold wip commits and uncommitted edits; read the diffs before trusting them, and rerun full suites on ada.
  - a Fable decider on the example-page design. If it left no verdict, rerun it: its brief is to choose between production, the reworked lighting, and rows rebuilt as the graph's own routes with walk rows leading at copy-number loci, per page, from the pictures.
- **jb2hubs `page-truth` rework (5f81c6cb), implementer's account, pictures looked at for HBA, LPA, KIR:**
  - each folded thread is split by row (`splitByRows`, `pangenomeWalkCut.ts`), so a row lights its own haplotypes on every route (HBA 29 + 1, KIR 28 + 6); no "realigned" (GSTM1 "18.4 kb deletion, 18.4 kb insertion"); merged rows named by range; HLA, KIR and LPA per row by a `graphPerRow` flag; AMY1 opens with a graph
  - suite 905 of 905, typecheck and lint 0; `check-pangenome-graphs` 18 of 18 on the branch, fails on production, three planted breaks red; built on the tarballs in `ada:~/work/walks8-gates/agents/claims-fixes/pack/` by an uncommitted override
  - still bad: LPA is a tangle with 18 lane counts in the key and row names like "6.05-20.7 kb → 88.4-104 kb +2 more"; AMY1's row of 179 lights lanes of 179 and 131 (a haplotype on two routes counts on both); carriers undercounted against the VCF at FCGR, MNS, PGA and KIR, since some sit in "other forms"; shares gone; bandage-core cannot leave a lifted lane out of the key
  - evidence: `~/src/walks8-evidence/sessions-20261127/jb2hubs-page-truth/` (`AFTER*` is the rework, `AFTER-exact*` the superseded rule)
- **Next, in order:** finish and verify the claims branches; one technical and one user-view re-review of the changed parts; one approval artifact for the owner with BEFORE/AFTER examples (fold release with chr7's lost thick arc, the pages as decided, a site-collapse prototype); then graph-fold 2.0.0, bandage-core 16.0.0, the plugin, the hosts, and the genomes.jbrowse.org deploy.
- The owner has said to arbitrate design calls by independent review and bring only what truly needs them, as an artifact with examples.

## The example-page design is decided (Fable decider, 27 November); not yet built or shown to the owner

- **Ruling:** a mixture on the reworked lighting. Rows stay groups of haplotypes read from the walks; the split lighting stays; every haplotype count leaves the graph, so the row is the only key and the only number. Rows are not rebuilt as fold routes (the fold splits rows on differences nobody can see: PGA 92 and 19 over a 1 bp breakpoint, HP 242 and 3, HBA 29 and 1). Per-row graphs go everywhere.
- **Rule for a graph page, all three:** its whole window draws as one folded graph; "other forms" holds 10% or less; at least one non-reference row lights something the reference row does not. Otherwise a walk-rows page.
  - Graph pages: CFHR, UGT2B17, PRSS, GSTM1, CYP2D6, C4, HBA, FCGR, RHD, HP, PGA, GSTT1.
  - Walk rows of a fixed named panel, no event rows, shares or folded graph: AMY1, LPA, KIR, HLA, FLNA. KIR's and MNS's whole-window fold was not tested.
  - MNS withdrawn.
- **Before it ships, in order:**
  - lane-count lines out of the key (a bandage-core option, or the page's own key); "depth" and "links" lines out; shares stay off;
  - a row prints its haplotype count beside its share;
  - `pageKind` deleted: "deletion" and "insertion" only where every member's other side is 0 bp, no merging across that line (GSTT1's "37.2 kb deletion" is 37,159 bp for 6 bp);
  - KIR's deletion stated as its two skips;
  - HP's 3 explained, and the check fails where the reference row lights off the reference route;
  - rows that cannot draw are not clickable;
  - "other forms" becomes "other combinations", the count column "haplotypes with exactly these";
  - the cited-allele box counts from the same members (GSTM1's says 390 beside rows of 305 and 82);
  - the walk-rows pages; then `graphPerRow` and the per-row cut go.
- **Interim deploy:** nothing before the new fold is released. Then the twelve graph pages with the first four changes; KIR, HLA and FLNA map-only; AMY1, LPA and MNS off the example list until their pages exist. The owner sees the pairs first.
- **Its confidence:** 85% that LPA and AMY1 must not be folded-graph pages, 75% on the row as the only count, 60% on KIR, HLA, FLNA and MNS, with no picture of those as they would ship. Row counts checked against the hosted walk file for eight pages (`jb2hubs-page-truth/groups.out`).

## Claims branches finished after the reviews (implementer's account, not yet re-reviewed or checked by anyone)

This replaces the "may have died mid-task" note above for the claims implementer. Nothing pushed, no `file:` pin committed.

- **Heads, one commit each, full CI 0 on ada:** graph-fold 16bd317 (270 tests), bandage-core 72f47c2 (2,085), plugin bf918fba rebased on 10.15.0 (1,272); sweep committed on `claims-sweep` 0c8a9d9. Tarballs `gf-16bd317.tgz` and `bc-72f47c224.tgz` with `manifest.tsv` in `ada:~/work/walks8-gates/agents/claims-fixes/pack/`; jb2hubs `page-truth` was shot on the older pair and needs a re-sweep.
- **Done:** variant A only; members and "folded away" no longer depend on context; `foldProblems` guards `outerBp`; hover strings from core (`foldedNodeTitle`, `foldedNodeLines`, `nodeLengthText`): range or length and span, "88 haplotypes", names by sample#haplotype, "and N more haplotypes"; one count per node; link ends on a fold are places on the reference; no key entry reads 0 (that was a stale bundle in the first shot); edge node "ends at 100,323,689; continues past the left edge".
- **Refused, with reason:** dropping a short run at the read's end erases a real inversion with short flanks, and the reviewer's own input still disagrees between reads with it. Reverted. The window dependence at `chain.ts:109-125` stays open.
- **Left as is:** the key footnote "2 skips under 916 bp not drawn" is bandage-core's zoom-level fold of simple sites, a real second threshold. "about 1.9 kb of smaller differences not drawn, in each" is a haplotype's total over its whole route in the read, not at the hovered node, and the wording does not say so.
- **Not rerun on the final heads:** the sweep's planted breaks (run once on the previous build: cut, length, range and new-string all caught). Sweep still red: edge depth on the cut route 162, edge link ends 346, website shares; unexpected: edge titles 10 and 81, 9 edge depths.
- **chr7 and chr15, from data:** chr7's old "206-216 kb" branch of 139 haplotypes shares both breakpoints (102,503,825-102,520,471); variant A splits it by inserted length alone, and 215,001 and 215,057 land in different boxes 56 bp apart. So one band per site labelled with its true range would be exact there. chr15's two "268 kb" arms differ by 7 bp in the left breakpoint.
- **Release versions:** graph-fold 2.0.0; bandage-core 16.0.0 on `^2.0.0` (`walkKeyEntry` loses its fourth parameter, `nodeEndLabel` gains a side); plugin on `^16.0.0`; ggbandage needs a bundle rebuild.
- Pictures: `claims-fixes/<item>/` with `AFTER` new and `AFTER-1` the first round.

## 28 November: re-reviews done, one implementer on the fold release, one on the pages

- **User-view Fable re-review of the final pictures: not fit to ship as is.** Must change: the hover's "N haplotypes: X of smaller differences not drawn, in each" lines (a thread's whole-read total, larger than the node at chr18, and lines that do not add up to the header); the key's two thresholds ("shorter than 439 bp" beside "2 skips under 916 bp"). chr7 is correct but uninformative (four hairlines for 139 haplotypes); chr15 still repeats "268 kb".
- **Technical Fable re-review** (`ada:~/work/walks8-gates/agents/claims-rereview/`): must change "opposite to" not cut to `walkedBy` (`foldedHover.ts`, 11 nodes), "inserted after" where carriers skip reference (631 of 1,993 heads, from `flankingSpan`), the sweep never run on the final heads and red outside `expected-red.tsv`. The short-run refusal is right; it gives a narrower rule (a run is short only when both its ends were read; an edge run never dropped, its inversion marked open). Also link counts, `labelledNodeShares`, three surviving mutants, graph-fold tests skipping without the git-ignored `data/`.
- **Site-collapse planned (Fable, probes in `ada:~/work/walks8-gates/agents/site-collapse-plan/`):** arms with identical leave and rejoin bases join at any inserted length; one band, union thickness, true range label, openable; 0 of 2,598 walks moved. chr7 back to one band of 138; chr15 repeats gone, 7 bp pair kept; chr18 243 to 112 nodes, still busy (a `minRouteHaplotypes` floor is a later separate item). Optional fields, `sites: 'collapsed'` default subject to the owner's page.
- **Running:** an Opus implementer on all of the above plus site-collapse (graph-fold and plugin `claims`, bandage-core `claims2` in `~/src/bandage-core-claims2`, ada `agents/fold-release/`, pictures to `walks8-evidence/sessions-20261128/fold-release/`); an Opus implementer on the decided page changes (jb2hubs `page-truth`, ada `agents/jb2hubs-pages/`, pictures to `sessions-20261128/jb2hubs-pages/`), which may add a key option commit on bandage-core `claims`.
- **Next:** check both, one owner approval artifact (fold release with chr7 lost and restored, the pages, site-collapse default), then the releases and deploy.
- **Direction review (Fable, probes in `ada:~/work/walks8-gates/agents/direction-review/`):** keep the fold and site-collapse for ordinary loci; at chr18 and LPA the fold is the wrong unit (one overlap group, 106 of 194 arms open at chr18; LPA a tandem repeat anchored at different copies), and the answer is the lanes button plus the panel graph, not another collapse rule. Rulings sent to the implementers: site-collapse draws a site as its arms bundled at their own thickness (a range label alone misleads at chr7:102,489,801 "12.5-99.6 kb", LPA "5.5-111 kb"), union-count guard, collapsed by default, no `minRouteHaplotypes` floor; one release train with site-collapse in graph-fold 2.0.0; pages leave off-reference length labels off the page graph (or share one size function) and delete what tolerances they can; the hard sites go on the owner's page. Next after these: the lanes button (`todo/graph-track-lanes-button.md`), then a probe of whether same-length members walk the same nodes.
- **Owner ruling, 28 November:** no walk lanes or walk rows shown to users. Individual walks belong only in a true multiway synteny display, and the walk-lanes default is bad. The lanes button is dropped, along with its todo. The page builder stops the walk-rows pages: AMY1, LPA, KIR, HLA, FLNA and MNS come off the example list, and the `walkRows` path and the pages' links into the walk-lanes track are removed. Loci the fold can't carry (chr18, LPA, AMY1) have no answer yet. It must come from the graph side or a true multiway synteny design.
- **Synteny plan (Fable, pictures in `walks8-evidence/sessions-20261128/synteny-plan/`):** the owner wants individual walks only as a true multiway synteny rendering: alignment ribbons between adjacent rows and gene models per row. The walk-fed MultiWaySyntenyDisplay already does this at KIR, LPA and chr7, with `laneRibbons: 'neighbours'` and lanes about 120 px tall. Per-haplotype genes are each assembly's own CAT annotation. AMY1 is broken: the gbz-base `lanePairAligner` drops multi-pass nodes and reversed runs (4 pairs at 28-45% coverage). An Opus implementer is building step 1 on plugin `synteny-neighbours` (`~/src/jbpgv-synteny`, ada `agents/synteny-step1/`): our own aligner (primary chain plus secondary records, coverage invariant), `neighbours` as the default, lane chips against hg38 removed. jb2hubs `LANE_HEIGHT_PX` 40 to about 110 comes after the page builder finishes. Later: a "walk not loaded here" mark, ordering by neighbour likeness, one scale across rows, GENCODE on the reference lane, collapsing identical walks.
