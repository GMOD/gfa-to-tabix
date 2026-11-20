---
name: graph-walks-release-98cb1ff
description: graph-walks main is two commits past 8.0.1, among them the cut of every haplotype in under half the time (98cb1ff); release them and move the readers' pins.
metadata:
  repo: graph-walks
---

# Release graph-walks past 8.0.1

- 98cb1ff: a cut of every haplotype in under half the time, same tables
- 3c324d0: tests for node ids that share a memo slot
- Run release-check on both hosted `-f8` genome URLs before tagging, as for
  8.0.1, then move bandage-core, BandageJS, ggbandage, jb2hubs, the plugin,
  tube map and ggtubemap, each a fast-forward after its CI
