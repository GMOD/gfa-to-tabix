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
