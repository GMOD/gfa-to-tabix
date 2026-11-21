---
name: jb2hubs-forms-naming
description: graph-walks 9.0.0 names changes by 0 bp on a side and has no shift; jb2hubs stays on 8.x, keeps its own 50 bp changeKind, and needs exact lengths in its sidecar before it can follow.
metadata:
  repo: jb2hubs
---

# jb2hubs on graph-walks 9

graph-walks 9.0.0 and plugin 10.3.0 shipped the naming rule on 2026-11-20:
deletion only at 0 bp of the haplotype's own, insertion only at 0 bp of the
reference, anything else a replacement with both sizes; no shift; a
sub-50 bp departure joins only another such. jb2hubs pins `^8.0.2` and was
told what it needs (its session, 2026-11-20):

- it reads `shiftedBp` and `onlyShifts`, so it won't compile on 9
- `website/src/pangenome/pangenomeSvStates.ts` keeps its own `changeKind`
  with the 50 bp sides, and `pairShifts`; its sidecar rounds each state's
  change to two figures, so it can't tell 0 own bp from 446. Exact lengths
  in the sidecar mean a sidecar format change and a rebuild
- `plainName` / `replacedSides` in `pangenomePanels.ts` should print
  `refLength` and `altLength`
- `agent-docs/reference/PANGENOME_PAGES.md` documents the 5% and 50 bp rules
