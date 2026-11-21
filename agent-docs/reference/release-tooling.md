---
name: release-tooling
description: Where the tools of the format 8 release live (the drawing gate, the known-failures pin, the reshoot harness, the packed tarballs, the backups) and what running them taught; paths as of 2026-11-19, not rechecked on ada since.
---

# Tools of the format 8 release

Taken from the release log on 2026-11-20. The log itself is in git history:
`git show 6e2b433:agent-docs/handoffs/2026-11-17-d655-next.md`.

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

## Pictures

- BEFORE and AFTER shots in jbrowse.org's JBrowse with a local plugin build:
  `~/src/walks8-evidence/briefs-d655/reshoot-tools/` (`bundles.tsv` names
  each build, `jobs.mjs` the shots, `shoot.sh '<job regex>'` runs them,
  `compose2.py` writes the page)
- Draw ggbandage's gallery on the laptop: ada's R graphics stack seams
  gradient ramps

## Pushing

- BandageJS's pre-push hook deploys jbrowse.org/demos/bandagejs
- The plugin's `pnpm version` pushes the branch it runs on
- jb2hubs' website build needs `NODE_OPTIONS=--max-old-space-size=8192`, and
  its `deploy.sh` needs the `myserver` ssh alias, which ada has

## ada

- One shared ssh master, few connections; if it drops, a new login needs the
  owner (`ssh -fN -o ControlPersist=yes ada`)
- Wait for a job with `ssh ada "tail --pid=<pid> -f /dev/null"`, not a
  sleep loop
