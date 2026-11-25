---
name: release-tooling
description: Where the tools of the format 8 release live (the drawing gate, the known-failures pin, the reshoot harness, the packed tarballs, the backups, the writer's real-data check), the release gates, and what running them taught; paths as of 2026-11-19, not rechecked on ada since unless a line says so.
---

# Tools of the format 8 release

Taken from the release log on 2026-11-20. The log itself is in git history:
`git show 6e2b433:agent-docs/handoffs/2026-11-17-d655-next.md`. The gates,
pins, writer check and the hook and `pnpm dep` lines were added on
2026-11-25 from the 2026-10-30 to 11-14 session handoffs.

## Release gates

Set on 2026-11-05, after libraries went out before any consumer had
compiled against them and the ports found two graph-walks bugs within the
hour:

- No library release until every consumer is green against the exact
  versions to be released, all pinned alike
- A local run of the repo's whole CI job before any tag
- graph-walks' `pnpm release-check`, with `WALKS=<path or url>`, clean on
  the file to be hosted
- The hosted swap in one pass, after the upload is audited from its URL

## The drawing gate

- `~/src/walks8-evidence/fab8f323/drawcheck-merged/ada-gates.sh <core commit> <baseline>`
  runs on ada under `~/work/walks8-gates/` and reads a clone of bandage-core
  by hash (`BANDAGE_CORE=`), with `PLUGIN=` and `PLUGIN_REPO=` for the sheet
- `SLOTS`, `SITES_SLOTS` and `LINKS_SLOTS` set how many drawings run at
  once; with `sites` first in `JOBS` a run takes about four hours
- A run outlives the session that started it: `--collect <commit> <stamp>`
  fetches a finished one, and results land under the full commit name in
  `runs/`
- Look at the contact sheet whole (`runs/<commit>/sheet/index.html`); a
  green gate is bookkeeping
- The raw `vg deconstruct` VCF sliced to the gate's 66 Minigraph-Cactus
  windows (`drawcheck-merged/windows.tsv`) is read as
  `$HOME/src/walks8-evidence/gate-inputs/drawcheck-slice.raw.vcf.gz`
  (`.tbi` beside it; `MC_VCF=` overrides). The laptop holds that copy,
  checked 2026-11-25; on 2026-11-14 the slice was also on ada at
  `/mnt/sdb/cdiesh/vcfcheck/drawcheck-slice.raw.vcf.gz`, not rechecked

## Comparing a run with the last accepted one

- `~/src/walks8-evidence/release-20261118/known_failures.py check <runs dir> <commit> pin-6ae5b1b.json`
  exits 1 on a regression against the pinned gate rows and planted rows
- A planted fault going from caught to no-op does not fail it, so diff the
  label rows and planted label rows by hand after a label change
- Byte-compare the new sheet with the last one; a shot that differs needs a
  reason

## Before a core change joins a candidate

- Pack it (`pnpm pack` from a frozen install) and run the plugin's suite
  installed from the tarball, not from a linked checkout: a0e4d0a passed
  core's suite and failed two plugin tests
- Tarballs are kept in `~/src/vendor/walks8-pack/`; the manifest of what was
  approved is `release-20261118/manifest.tsv`, and bundles of every branch
  of the candidate are in `release-20261118/backup/`

## Pinning unreleased packages by `file:`

- pnpm writes a `file:` path relative to the lockfile, so a lockfile
  written in a deeper worktree breaks `pnpm install` in the main checkout
- After a port lands from a worktree, run `pnpm install` in the main
  checkout before trusting its tests: its `node_modules` can still hold the
  old package
- A tarball packed while its package pins another by `file:` carries that
  pin: on 2026-11-07 bandage-core's listed graph-walks as a `file:`
  devDependency. Swap it before publishing

## The writer's real-data check

- `docs/walks-container/writer/scripts/release-check.sh` builds MC chr22
  and pggb chrY on ada from a git bundle of the commit to check, compares
  bytes with the previous build and runs the file checks; its header gives
  the bundle step and the call, and `release.done` says PASSED or FAILED
- `docs/walks-container/writer/scripts/genome-check.sh` runs the
  step-for-step rebuild of a genome-wide file against its GFA
- On 2026-11-07 ada had `~/work/release/launch.sh`, which clones
  `~/work/release/writer.bundle`'s main and starts the check detached, and
  `kill.sh` beside it to stop a run. Neither is in the repo; not rechecked

## Pictures

- BEFORE and AFTER shots in jbrowse.org's JBrowse with a local plugin build:
  `~/src/walks8-evidence/briefs-d655/reshoot-tools/` (`bundles.tsv` names
  each build, `jobs.mjs` the shots, `shoot.sh '<job regex>'` runs them,
  `compose2.py` writes the page)
- Draw ggbandage's gallery on the laptop: ada's R graphics stack seams
  gradient ramps

## Pushing

- BandageJS's pre-push hook is local (`.git/hooks/pre-push`, not in the
  repo) and runs bare `pnpm deploy`, which is pnpm's own workspace command
  (`pnpm help deploy`), not the repo's `deploy` script that builds and
  syncs jbrowse.org/demos/bandagejs; that one is `pnpm run deploy`. On
  2026-11-05 the hook failed, so branch pushes used `--no-verify`
- The plugin's pre-push hook (`.githooks/pre-push`) runs `format:check`,
  `typecheck`, `typecheck:tests` and `lint`. On 2026-11-05, typechecking
  through it against an overlaid core needed
  `pnpm_config_verify_deps_before_run=false`; not rerun
- jbrowse-plugin-list's `pnpm dep` updates the plugins, then commits,
  pushes, uploads and invalidates in one step
- The plugin's `pnpm version` pushes the branch it runs on
- jb2hubs' website build needs `NODE_OPTIONS=--max-old-space-size=8192`, and
  its `deploy.sh` needs the `myserver` ssh alias, which ada has

## ada

- One shared ssh master, few connections; if it drops, a new login needs the
  owner (`ssh -fN -o ControlPersist=yes ada`)
- Wait for a job with `ssh ada "tail --pid=<pid> -f /dev/null"`, not a
  sleep loop
