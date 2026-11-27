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
