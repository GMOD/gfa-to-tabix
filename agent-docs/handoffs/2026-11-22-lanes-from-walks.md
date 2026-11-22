---
name: 2026-11-22-lanes-from-walks
description: A laptop session measured how well walk files supply JBrowse's haplotype lanes, found the aligner between two haplotypes loses ribbons where a walk steps a node twice, decided a replacement after two Fable reviews, and found the lanes' headers at amylase at odds with the sequence; what is settled, what is queued and with whom, and what nobody has picked up.
---

# Haplotype lanes from walk files, 2026-11-22

The owner asked whether multi-way synteny can be read straight from the
graph's walk file, at a locus and genome-wide, and then whether what it
returns is right. This file points at where each answer is; delete it when
the aligner change lands.

## Where everything is

- **Evidence:** ada, `~/work/synteny-extract-1122/`. The laptop's
  `~/src/walks8-evidence/sessions-20261122/lanes/` has the scripts and
  pictures only.
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
- **A laptop session:** `todo/lanes-headers-and-fit-at-inversions.md`, on the
  jbrowse-components branch `lanes-fit-at-inversions`, unpushed; the owner
  opens the PR. The ada session is told not to act on it.

## Before the aligner change lands

Every check is a gate in `todo/lane-aligner-leftover-stretches.md`; none is
done.

## Filed since

- **A fragment ending at its last step on the reference** is graph-walks'
  design, not a fault in `cut`; the lanes adapter drops what the cut says
  lies past it: `todo/lanes-say-what-lies-between-fragments.md`.
- **Ribbons against the reference:** `todo/lanes-ribbons-against-reference.md`.
- **Whether lanes should be offered at loci like amylase:**
  `ideas/waiting-on-a-call/lanes-at-collapsed-loci.md`.
- **Lanes in a browser:** added to the ada session's query-time item.
- **A stacked `LinearSyntenyView` from a walk file** stays in the
  coarse-table idea; it was read from the code and not run.
- **The comment in `walkLanes.ts`** goes away with the aligner change; if
  that stalls, fix the comment.

## Cleaning up

- `~/work/synteny-extract-1122/` is about 0.8 GB. Keep it until the aligner
  change lands, since `coverage.mjs` and the pictures are its gates.
- `hprc_multiway_gfa.pif.gz` there is a copy of the hosted file and can go
  at any time.
