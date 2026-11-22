---
name: 2026-11-22-lanes-from-walks
description: A laptop session measured how well walk files supply JBrowse's haplotype lanes, found the aligner between two haplotypes loses ribbons where a walk steps a node twice, decided a replacement after two Fable reviews, and found the lanes' headers at amylase at odds with the sequence; what is settled, what is queued and with whom, and what nobody has picked up.
---

# Haplotype lanes from walk files, 2026-11-22

The owner asked whether multi-way synteny can be read straight from the
graph's walk file, at a locus and genome-wide, and then whether what it
returns is right. This file points at where each answer is; delete it when
the aligner change lands and the items under "Nobody has picked up" are
filed or done.

## Where everything is

- **Evidence:** ada, `~/work/synteny-extract-1122/`.
  - Scripts and outputs of the first pass at the top level; `laptop-copy/`
    holds the same scripts as they ran, and the page's HTML.
  - `why-amylase/` is the second Fable review's sweep and traces.
  - `shots/` has every screenshot: `before`, `pairs-only`, `pairs-only-10k`,
    `after`, `pif`.
  - `plugin/` is a clone at v10.4.3 with `scripts/shoot-figures.mjs`
    patched to shoot the lanes, and `walkLanes.ts` left in the
    lanes-between-haplotypes-only state with a 10 kb floor. It is scratch.
- **Write-ups:** `todo/lane-aligner-leftover-stretches.md`,
  `todo/lanes-headers-and-fit-at-inversions.md`,
  `ideas/waiting-on-someone-else/lanes-coarse-table.md`.
- **The page shown to the owner:**
  `https://claude.ai/artifact/D8dnSNrUE2imJDaQY81gQu`, private to the
  account of the config that published it.
- **Nothing released was changed.** No commit went to graph-walks, the
  plugin, bandage-core or jbrowse-components.

## What is settled

- **Lanes at a locus already ship.** The plugin's `WalkTabixSyntenyAdapter`
  feeds JBrowse's `MultiWaySyntenyDisplay`. In Node on ada, eight lanes
  answer every window to 5 Mb, forty to 1 Mb, and all 463 to about 100 kb
  (`time.jsonl`). No browser timing was taken.
- **What a lane record calls a match is right:** the same node at the same
  offset in both walks, the same letters where a FASTA was at hand, and on
  the diagonals of the PAF written from the GFA.
- **The share of shared nodes that get a ribbon is the number to quote,**
  from the walks alone (`coverage.mjs`, `why-amylase/sweep.mjs`). The
  minimap2 percentages of the first pass are withdrawn.
- **Where it falls short, and why,** is in the aligner todo: about twenty of
  some 9,600 windows, every one with a walk that steps a node twice.
- **Decided, after two Fable reviews:** lanes between two haplotypes take
  the leftover aligner in place of pair chaining; lanes against the
  reference stay; the coarse table waits on the overview-tier study.

## Queued, and with whom

- **The ada session** (`2026-11-21-ada-next.md`): move the aligner out of
  gbz-base into graph-walks as a pure move, then the leftover aligner as its
  own change, behind the gates in the todo.
- **The owner:** `todo/lanes-headers-and-fit-at-inversions.md`. It is all in
  jbrowse-components, and the ada session is told not to act on it.

## Before the aligner change lands

These are in the todo's gates or follow from the second review; none is
done.

- Re-run GSTT1 with floors of 1 kb and 10 kb. The second review reported
  seven pairs that get less than today at 10 kb; the first pass did not
  repeat it.
- Explain the stretch of HG00128's pairs the prototype still leaves without
  a ribbon, and why its records depend on which walk is the query.
- Run it at the sweep's lowest windows and at wide windows over SMN and
  8p23.1, and on a pggb graph. No pggb graph has been tried at all.
- Shoot before and after at amylase, SMN, TBC1D3 and FLNA/EMD and look at
  them. About a twentieth of the shared bases at amylase carry two ribbons,
  so a blue ribbon lies over a salmon one; whether that reads at SMN is not
  known.
- Run the display to confirm what draws the thin blue line at amylase. The
  first review read it off the records and `cutAtOpenings`.
- Skip the second direction where little is shared the other way, then time
  it in the real reader.
- Check that the plugin's `cutOptions()` equals the browser preset the
  scripts cut with.

## Nobody has picked up

- **graph-walks' `cut` ends a fragment at its last step on the reference.**
  The second review found 30 kb of HG00097's walk at amylase in the file
  and not in the fragment (`trimmedAfter`), which the lane then heads as
  part of an insertion. Not verified by the laptop session and not filed.
- **The comment in `walkLanes.ts`** that counting singly visited nodes
  "misses no inversion it could draw" is wrong. It goes away with the
  aligner change; if that stalls, fix the comment.
- **A stacked `LinearSyntenyView` from a walk file** gets records only on a
  level whose upper row is the reference, by reading the code; it was not
  run. It is noted in the coarse-table idea and nowhere else.
- **Ribbons against the reference in the lanes display.** A walk-fed lanes
  track always draws neighbour against neighbour, with no setting for each
  lane against hg38. The paper session wanted that for Figure 5 and was
  told it is a jbrowse-components change.
- **Lanes in a browser.** The ada session's query-time item times the graph
  track, not the lanes.
- **Whether lanes should be offered at loci like amylase,** where the graph
  keeps identical sequence on separate nodes. The first review called them
  not a sound reading there. The tutorial's part 3 reads amylase from
  walk rows; nothing in the lanes points there.

## Cleaning up

- `~/work/synteny-extract-1122/` is about 0.8 GB. Keep it until the aligner
  change lands, since `coverage.mjs` and the pictures are its gates.
- `hprc_multiway_gfa.pif.gz` there is a copy of the hosted file and can go
  at any time.
