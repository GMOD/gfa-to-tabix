---
name: forms-row-label-width
description: Core JBrowse cuts every row label at 10 ems, so forms-track rows that differ after about 20 characters (MHC's "repl 3.77kb->48.1kb, …") look alike; widening it hides the left of the plot. The owner's call, in jbrowse-components.
metadata:
  repo: jbrowse-components
---

# Forms-track row labels are cut at 20 characters

- `packages/tree-sidebar/src/sidebar/rowLabelsBoxWidth.ts:22`,
  `ROW_LABEL_MAX_EMS = 10`, caps every row label; the plugin supplies only
  the text. The whole label is in a `<title>` on hover (`SvgRowLabels.tsx`)
- graph-walks 9.0.0's `formTag` names what tells alike rows apart, but at MHC
  that comes after the cut ("repl 3.77kb->48.1kb, ins 21.8kb, …" three
  ways). Over 638 windows the median label is 9 characters, the 90th
  percentile 19, the longest 63
- Labels lie over the plot's first stretch with no gutter, so a column wide
  enough for 63 characters (about 380 px) hides that much of every such
  track. Options: size to the longest label up to a bound and wrap past it,
  in core; or leave it, relying on hover
