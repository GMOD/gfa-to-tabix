---
name: walk-row-axis-from-unstated-start
description: Walk rows give every row an axis of {contig, start - stepStart}, so a W line with "*" coordinates gets a row hover of ctg2:1-2,100 in BandageJS, places genes on the row, and opens that span in JBrowse; GFA text only, since walk files always state coordinates.
metadata:
  repo: bandage-core
---

# Walk-row axes from an unstated start

- Found by the second technical Fable review of the stated-spans change on 26 November. The behaviour predates that change.
- Code: `walkRowRuns.ts` around line 1290 builds the axis. `walkRows` returns `{contig: 'ctg2', start: 0}` for `W h2 1 ctg2 * * >a>i2>c`.
- The axis feeds:
  - BandageJS `src/describe.ts:156`, which prints the row hover;
  - gene placement, in BandageJS `src/genes.ts:206` and plugin `walkRowViews.ts:97`;
  - BandageJS `src/jbrowse.ts:246`, which opens the location in JBrowse.
- Apply the stated-spans rule: give a row no contig axis when its start is not stated.
- Unify the three definitions of "stated" while there:
  - core hover needs the range to equal the extent;
  - BandageJS node details need each record's end minus start to equal its own bp;
  - the plugin band needs only `end` defined.
