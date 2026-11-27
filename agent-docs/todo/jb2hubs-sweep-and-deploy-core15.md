---
name: jb2hubs-sweep-and-deploy-core15
description: jb2hubs main pins bandage-core 15.0.0 (d8d1841e), but the website was neither swept with check-pangenome-graphs nor deployed, since another session had unreviewed work on main; genomes.jbrowse.org still runs an older core, whose figure keys print the folded-length range labels 15.0.0 removes (inferred from its code, not seen).
metadata:
  repo: jb2hubs
---

# Sweep and deploy jb2hubs on bandage-core 15.0.0

- Pinned on 27 November (`d8d1841e`); typecheck, type-aware lint and tests
  pass in its Lint run. The run fails only on oxfmt over other sessions'
  agent-docs markdown, as it has since 25 November.
- Still owed, by jb2hubs' own handoff `pangenome-page-trim.md` ("When the core
  release ships"): `compactKey: true` in the worker's `SPEC`, then
  `pnpm check-pangenome-graphs` on a dev server and on production, then
  `pnpm run deploy` (from ada, which has the `myserver` alias).
- A deploy ships everything on jb2hubs main, so agree it with whichever
  session owns the newest commits there.
