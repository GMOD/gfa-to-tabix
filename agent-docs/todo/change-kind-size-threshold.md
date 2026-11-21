---
name: change-kind-size-threshold
description: graph-walks' changeKind calls a change a deletion or insertion when one side is under 50 bp, where the rule is that one side is 0 bp and anything else is "A replaced by B"; the forms track and jb2hubs' wording follow it.
metadata:
  repo: graph-walks, jb2hubs, jbrowse-plugin-graphgenomeviewer
---

# A change is named by a size threshold

- `changeKind` (graph-walks `src/structuralForms.ts`, `STRUCTURAL_BP = 50`)
  returns `insertion` where the reference side is under 50 bp and `deletion`
  where the haplotype's side is. It dates from 2026-10-21, before the rule
  that a deletion has 0 bp of the haplotype's own and an insertion 0 bp of
  the reference, with no threshold
- It names the marks of `structuralForms`, which the plugin's forms track
  writes out as `<DEL>` and `<INS>` (`WalkFormsAdapter/formRows.ts`), so
  "86 kb replaced by 12 bp" is called a deletion. jb2hubs keeps a copy of the
  rule with the same constant (`pangenomeSvStates.ts`)
- To change: 0 bp on a side, not under 50; count on the hosted chr22 windows
  how many marks change kind; show the forms track before and after; then a
  graph-walks release and re-pins
