---
name: forms-name-their-carriers
description: graph-walks gives each structural form its members, but the plugin's forms track keeps only their count; a form row could name its carriers and open them in the graph.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# Forms that name their carriers

- graph-walks' `structuralForms` gives each form `members: string[]`, the
  haplotypes that take it (`src/structuralForms.ts`)
- The plugin's forms track uses only `members.length`, for the row's label
  and its `haplotypes` count (`src/WalkFormsAdapter/formRows.ts`); checked
  on 2026-11-25 at plugin 10.9.0
- The idea, from 2026-11-02: a form row names its carriers and opens the
  graph view with them as the shown haplotypes. GSTM1 is the figure it was
  meant for
- The forms track's own correctness comes first:
  `../../todo/forms-track-truth-audit.md`
