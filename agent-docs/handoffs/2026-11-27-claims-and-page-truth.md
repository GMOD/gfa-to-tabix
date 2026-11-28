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

