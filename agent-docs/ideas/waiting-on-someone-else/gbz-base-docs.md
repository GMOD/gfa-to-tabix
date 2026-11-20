---
name: gbz-base-docs
description: When bandage-core drops gbz-base, gfa-to-tabix's README and docs/comparison.md must stop saying the viewers read gbz-base; the plugin's GbzBaseSyntenyAdapter stays while the paper cites it.
metadata:
  repo: gfa-to-tabix
---

# Docs after gbz-base leaves bandage-core

The owner decided (2026-11-18) to remove gbz-base support from bandage-core,
BandageJS and the plugin's `GbzBaseSyntenyAdapter`, in a later major release.
bandage-core still has `gbzCut.ts`, `gbzJoin.ts` and `gbzWindow.ts`. When that
release ships, change `docs/comparison.md`'s "Read by" row and any README line
that says a viewer reads gbz-base. The paper's supplementary table on gbz
requests measures gbz-base in the plugin, so the plugin's adapter waits on the
paper.
