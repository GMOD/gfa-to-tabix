---
name: lanes-say-what-lies-between-fragments
description: The plugin's lanes adapter makes records from a cut's fragments alone, so a walk's own off-reference sequence past a fragment's last reference step, and a stretch Minigraph-Cactus clipped, both reach the display as a bare jump in the haplotype's coordinates; the cut already states what lies there and the adapter drops it.
metadata:
  repo: jbrowse-plugin-graphgenomeviewer
---

# Lanes do not say what lies between a walk's fragments

At `chr1:103,500,000-103,800,000` HG00097.1's lane is headed "49 kb
insertion" where its walk is in two fragments 49 kb apart. A review on
2026-11-22 read the GFA's W lines: 19 kb is clipped by Minigraph-Cactus and
30 kb is in the walk file past the first fragment's last step on the
reference.

## What is true

- **graph-walks ends a fragment at its last step on the reference by
  design.** Its README's "Fragments" says so, `trimmedAfter` counts the bp of
  the run past it, and ADR 0001 was written about this haplotype at this
  locus. The handoff of 2026-11-22 listed it as a possible fault in `cut`;
  it is not one.
- **The cut states the stretch.** `gaps` gives, between two fragments, the
  segments of the walk's contig in order: `steps` the cut attached to a
  departure, `read` steps it kept out, `own` sequence of a record it did not
  read, and `unread` pieces.
- **The adapter drops it.** `WalkTabixSyntenyAdapter.anchorFeatures` reads
  `graph`, `fragments` and `departures`, and uses a departure only for a
  haplotype with no step in the window. The display sees two records on one
  contig with a 49 kb jump.

- **The same holds between two records of one fragment.** With records read
  from each step's stored place, HG00128.1 at amylase has 116 kb of its own
  steps (haplotype 103,993,742-104,109,516) between a forward record and a
  reversed one. No record covers them, and the display, seeing a turn with
  no reference side, states nothing.

## What to do

- Decide what a lane shows between fragments: the 30 kb the graph holds is
  sequence of the haplotype off the reference, and the 19 kb is in the
  assembly and not in the graph.
- Pass it through, as records or a record field the display can head
  without calling a clipped stretch an insertion.
  `todo/lanes-headers-and-fit-at-inversions.md` has the display's side.
